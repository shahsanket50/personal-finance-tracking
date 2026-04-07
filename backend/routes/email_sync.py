import logging
import hashlib
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict
from datetime import datetime, timezone
from email.header import decode_header
from database import db
from models import Transaction, EmailConfigModel
from auth import get_current_user
from helpers import (
    init_default_categories, ai_categorize_batch,
    is_subject_before_date, imap_connect_and_search, log_sync,
)
from bridge import transaction_to_voucher
from pdf_parsers_simple import get_simple_parser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


@router.post("/email-config")
async def save_email_config(config: EmailConfigModel, user: Dict = Depends(get_current_user)):
    uid = user["user_id"]
    doc = {
        "user_id": uid,
        "imap_server": config.imap_server,
        "email_address": config.email_address,
        "app_password": config.app_password,
        "sync_since": config.sync_since,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    await db.email_configs.update_one(
        {"user_id": uid},
        {"$set": doc},
        upsert=True
    )
    return {"message": "Email configuration saved"}


@router.get("/email-config")
async def get_email_config(user: Dict = Depends(get_current_user)):
    config = await db.email_configs.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not config:
        return {"configured": False}
    return {
        "configured": True,
        "imap_server": config["imap_server"],
        "email_address": config["email_address"],
        "has_password": bool(config.get("app_password")),
        "sync_since": config.get("sync_since", "")
    }


@router.post("/email-scan")
async def scan_email_for_statements(user: Dict = Depends(get_current_user)):
    import imaplib
    import email as email_lib

    uid = user["user_id"]

    email_config = await db.email_configs.find_one({"user_id": uid}, {"_id": 0})
    if not email_config or not email_config.get("app_password"):
        raise HTTPException(status_code=400, detail="Email not configured. Go to Settings to set up email scanning.")

    sync_since_date = None
    if email_config.get("sync_since"):
        try:
            sync_since_date = datetime.strptime(email_config["sync_since"], "%Y-%m-%d")
        except Exception:
            pass

    accounts = await db.accounts.find({"user_id": uid}, {"_id": 0}).to_list(100)
    accounts_with_filters = [a for a in accounts if a.get("email_filter")]
    if not accounts_with_filters:
        raise HTTPException(status_code=400, detail="No accounts have email filters configured. Edit an account and add an email filter keyword.")

    try:
        mail = imaplib.IMAP4_SSL(email_config["imap_server"])
        mail.login(email_config["email_address"], email_config["app_password"])
        try:
            status, _ = mail.select('"[Gmail]/All Mail"')
            if status != 'OK':
                mail.select("INBOX")
        except Exception:
            mail.select("INBOX")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Email connection failed: {str(e)}")

    total_imported = 0
    total_skipped = 0
    results = []

    try:
        for account in accounts_with_filters:
            filter_text = account["email_filter"]
            from_filter = account.get("email_from_filter", "")
            account_id = account["id"]
            account_name = account["name"]
            from_criteria = f' FROM "{from_filter}"' if from_filter else ''

            _, msg_nums = mail.search(None, f'(SUBJECT "{filter_text}"{from_criteria})')
            if not msg_nums[0]:
                _, msg_nums = mail.search(None, f'(BODY "{filter_text}"{from_criteria})')
            if not msg_nums[0] and len(filter_text.split()) > 2:
                words = [w for w in filter_text.split() if len(w) > 3][:4]
                if words:
                    criteria = ' '.join(f'SUBJECT "{w}"' for w in words)
                    _, msg_nums = mail.search(None, f'({criteria}{from_criteria})')

            message_ids = msg_nums[0].split() if msg_nums[0] else []

            for msg_num in message_ids:
                _, msg_data = mail.fetch(msg_num, "(RFC822)")
                email_message = email_lib.message_from_bytes(msg_data[0][1])

                message_id = email_message.get("Message-ID", "")
                email_hash = hashlib.md5(f"{message_id}_{account_id}".encode()).hexdigest()

                if sync_since_date:
                    skip = False
                    try:
                        from email.utils import parsedate_to_datetime
                        email_dt = parsedate_to_datetime(str(email_message.get("Date", "")))
                        if email_dt.replace(tzinfo=None) < sync_since_date:
                            skip = True
                    except Exception:
                        pass
                    if not skip:
                        raw_subj = email_message.get("Subject", "")
                        decoded_parts = decode_header(raw_subj)
                        subj_str = ""
                        for sp, enc in decoded_parts:
                            subj_str += sp.decode(enc or "utf-8", errors="replace") if isinstance(sp, bytes) else str(sp)
                        skip = is_subject_before_date(subj_str, sync_since_date)
                    if skip:
                        continue

                already_processed = await db.processed_emails.find_one({
                    "email_hash": email_hash, "user_id": uid
                })
                if already_processed:
                    total_skipped += 1
                    continue

                for part in email_message.walk():
                    if part.get_content_type() == "application/pdf":
                        filename = part.get_filename() or "statement.pdf"
                        pdf_data = part.get_payload(decode=True)
                        if not pdf_data:
                            continue

                        password = account.get("pdf_password", "")
                        custom_pattern = account.get("custom_parser")
                        parser = get_simple_parser(account_name, custom_pattern)

                        try:
                            parsed_txns = parser.parse(pdf_data, password or None)
                        except Exception:
                            parsed_txns = []

                        imported_count = 0
                        for txn_data in parsed_txns:
                            existing = await db.transactions.find_one({
                                "account_id": account_id, "user_id": uid,
                                "date": txn_data["date"],
                                "description": txn_data["description"],
                                "amount": txn_data["amount"]
                            })
                            if existing:
                                continue

                            txn = Transaction(
                                user_id=uid, account_id=account_id,
                                date=txn_data["date"], description=txn_data["description"],
                                amount=txn_data["amount"], transaction_type=txn_data["type"]
                            )
                            doc = txn.model_dump()
                            doc["created_at"] = doc["created_at"].isoformat()
                            await db.transactions.insert_one(doc)
                            try:
                                account_obj = await db.accounts.find_one({"id": account_id, "user_id": uid}, {"_id": 0})
                                if account_obj:
                                    await transaction_to_voucher(uid, txn, account_obj, None)
                            except Exception:
                                pass
                            imported_count += 1

                        if imported_count > 0:
                            total_imported += imported_count

                        results.append({
                            "account": account_name,
                            "file": filename,
                            "found": len(parsed_txns),
                            "imported": imported_count
                        })

                await db.processed_emails.insert_one({
                    "email_hash": email_hash,
                    "user_id": uid,
                    "account_id": account_id,
                    "message_id": message_id,
                    "processed_at": datetime.now(timezone.utc).isoformat()
                })
    finally:
        mail.logout()

    categorized_count = 0
    if total_imported > 0:
        try:
            categories = await db.categories.find({"user_id": uid}, {"_id": 0}).to_list(200)
            if len(categories) == 0:
                await init_default_categories(uid)
                categories = await db.categories.find({"user_id": uid}, {"_id": 0}).to_list(200)
            uncategorized = await db.transactions.find(
                {"user_id": uid, "category_id": None, "is_transfer": False},
                {"_id": 0}
            ).to_list(5000)
            if uncategorized:
                categorized_count = await ai_categorize_batch(uid, uncategorized, categories)
        except Exception as e:
            logger.warning(f"Auto-categorization after email-scan failed: {e}")

    return {
        "message": f"Scan complete. Imported {total_imported} transactions, skipped {total_skipped} already-processed emails." + (f" Auto-categorized {categorized_count}." if categorized_count > 0 else ""),
        "total_imported": total_imported,
        "total_skipped": total_skipped,
        "categorized_count": categorized_count,
        "details": results
    }


@router.post("/accounts/{account_id}/sync-preview")
async def sync_account_preview(account_id: str, user: Dict = Depends(get_current_user)):
    import email as email_lib
    from email.utils import parsedate_to_datetime

    uid = user["user_id"]
    account = await db.accounts.find_one({"id": account_id, "user_id": uid}, {"_id": 0})
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if not account.get("email_filter"):
        raise HTTPException(status_code=400, detail="No email filter configured for this account.")

    email_config = await db.email_configs.find_one({"user_id": uid}, {"_id": 0})
    if not email_config or not email_config.get("app_password"):
        raise HTTPException(status_code=400, detail="Email not configured in Settings.")

    mail, message_ids, sync_since_date, error = await imap_connect_and_search(email_config, account)
    if error:
        raise HTTPException(status_code=400, detail=f"Email connection failed: {error}")

    previews = []
    total_imap_results = len(message_ids)
    skipped_by_date = 0
    try:
        for msg_num in message_ids:
            _, msg_data = mail.fetch(msg_num, "(RFC822)")
            email_message = email_lib.message_from_bytes(msg_data[0][1])
            message_id = email_message.get("Message-ID", "")
            email_hash = hashlib.md5(f"{message_id}_{account_id}".encode()).hexdigest()

            raw_subject = email_message.get("Subject", "")
            decoded_parts = decode_header(raw_subject)
            subject = ""
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    subject += part.decode(encoding or "utf-8", errors="replace")
                else:
                    subject += str(part)

            from_addr = email_message.get("From", "")
            email_date = email_message.get("Date", "")

            if sync_since_date:
                skip = False
                try:
                    email_dt = parsedate_to_datetime(email_date)
                    if email_dt.replace(tzinfo=None) < sync_since_date:
                        skip = True
                except Exception:
                    pass
                if not skip:
                    skip = is_subject_before_date(subject, sync_since_date)
                if skip:
                    skipped_by_date += 1
                    continue

            already_processed = await db.processed_emails.find_one({"email_hash": email_hash, "user_id": uid})

            pdfs = []
            for part in email_message.walk():
                if part.get_content_type() == "application/pdf":
                    filename = part.get_filename() or "statement.pdf"
                    pdf_data = part.get_payload(decode=True)
                    size_kb = round(len(pdf_data) / 1024, 1) if pdf_data else 0

                    txn_count = 0
                    parse_status = "unknown"
                    if pdf_data:
                        password = account.get("pdf_password", "")
                        custom_pattern = account.get("custom_parser")
                        parser = get_simple_parser(account["name"], custom_pattern)
                        try:
                            parsed = parser.parse(pdf_data, password or None)
                            txn_count = len(parsed)
                            parse_status = "ok" if txn_count > 0 else "empty"
                        except Exception as pe:
                            err_lower = str(pe).lower()
                            if "password" in err_lower or "encrypt" in err_lower or "decrypt" in err_lower:
                                parse_status = "password_error"
                            else:
                                parse_status = "parse_error"

                    pdfs.append({
                        "filename": filename,
                        "size_kb": size_kb,
                        "transactions_found": txn_count,
                        "parse_status": parse_status
                    })

            previews.append({
                "subject": subject[:120],
                "from": from_addr[:80],
                "date": str(email_date)[:30],
                "already_synced": bool(already_processed),
                "pdfs": pdfs,
                "total_transactions": sum(p["transactions_found"] for p in pdfs)
            })
    finally:
        mail.logout()

    total_emails = len(previews)
    new_emails = sum(1 for p in previews if not p["already_synced"])
    total_pdfs = sum(len(p["pdfs"]) for p in previews)
    total_txns = sum(p["total_transactions"] for p in previews if not p["already_synced"])
    password_errors = sum(1 for p in previews for pdf in p["pdfs"] if pdf["parse_status"] == "password_error")

    return {
        "account_name": account["name"],
        "filter_used": account["email_filter"],
        "from_filter": account.get("email_from_filter", ""),
        "sync_since": email_config.get("sync_since", ""),
        "summary": {
            "total_imap_results": total_imap_results,
            "skipped_by_date_filter": skipped_by_date,
            "total_emails": total_emails,
            "new_emails": new_emails,
            "already_synced": total_emails - new_emails,
            "total_pdfs": total_pdfs,
            "total_transactions": total_txns,
            "password_errors": password_errors
        },
        "emails": previews
    }


@router.post("/accounts/{account_id}/sync")
async def sync_account_email(account_id: str, user: Dict = Depends(get_current_user)):
    import email as email_lib

    uid = user["user_id"]
    account = await db.accounts.find_one({"id": account_id, "user_id": uid}, {"_id": 0})
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if not account.get("email_filter"):
        raise HTTPException(status_code=400, detail="No email filter configured for this account. Edit the account to add one.")

    email_config = await db.email_configs.find_one({"user_id": uid}, {"_id": 0})
    if not email_config or not email_config.get("app_password"):
        raise HTTPException(status_code=400, detail="Email not configured. Go to Settings to set up email scanning.")

    mail, message_ids, sync_since_date, error = await imap_connect_and_search(email_config, account)
    if error:
        await log_sync(uid, account_id, account["name"], "failed", 0, 0, error)
        raise HTTPException(status_code=400, detail=f"Email connection failed: {error}")

    total_imported = 0
    total_skipped = 0
    files_found = []
    emails_matched = len(message_ids)

    try:
        for msg_num in message_ids:
            _, msg_data = mail.fetch(msg_num, "(RFC822)")
            email_message = email_lib.message_from_bytes(msg_data[0][1])
            message_id = email_message.get("Message-ID", "")
            email_hash = hashlib.md5(f"{message_id}_{account_id}".encode()).hexdigest()
            subject = str(email_message.get("Subject", ""))
            email_date = str(email_message.get("Date", ""))

            if sync_since_date:
                skip = False
                try:
                    from email.utils import parsedate_to_datetime
                    email_dt = parsedate_to_datetime(email_date)
                    if email_dt.replace(tzinfo=None) < sync_since_date:
                        skip = True
                except Exception:
                    pass
                if not skip:
                    decoded_subj_parts = decode_header(subject)
                    subj_text = ""
                    for sp, enc in decoded_subj_parts:
                        subj_text += sp.decode(enc or "utf-8", errors="replace") if isinstance(sp, bytes) else str(sp)
                    skip = is_subject_before_date(subj_text, sync_since_date)
                if skip:
                    continue

            already_processed = await db.processed_emails.find_one({"email_hash": email_hash, "user_id": uid})
            if already_processed:
                total_skipped += 1
                continue

            email_had_success = False
            for part in email_message.walk():
                if part.get_content_type() == "application/pdf":
                    filename = part.get_filename() or "statement.pdf"
                    pdf_data = part.get_payload(decode=True)
                    if not pdf_data:
                        continue

                    password = account.get("pdf_password", "")
                    custom_pattern = account.get("custom_parser")
                    parser = get_simple_parser(account["name"], custom_pattern)

                    parse_error = None
                    try:
                        parsed_txns = parser.parse(pdf_data, password or None)
                    except Exception as parse_ex:
                        parsed_txns = []
                        parse_error = str(parse_ex)

                    imported_count = 0
                    duplicate_count = 0
                    for txn_data in parsed_txns:
                        existing = await db.transactions.find_one({
                            "account_id": account_id, "user_id": uid,
                            "date": txn_data["date"], "description": txn_data["description"],
                            "amount": txn_data["amount"]
                        })
                        if existing:
                            duplicate_count += 1
                            continue
                        txn = Transaction(
                            user_id=uid, account_id=account_id,
                            date=txn_data["date"], description=txn_data["description"],
                            amount=txn_data["amount"], transaction_type=txn_data["type"]
                        )
                        doc = txn.model_dump()
                        doc["created_at"] = doc["created_at"].isoformat()
                        await db.transactions.insert_one(doc)
                        try:
                            account_obj = await db.accounts.find_one({"id": account_id, "user_id": uid}, {"_id": 0})
                            if account_obj:
                                await transaction_to_voucher(uid, txn, account_obj, None)
                        except Exception:
                            pass
                        imported_count += 1

                    total_imported += imported_count

                    if parse_error:
                        err_lower = parse_error.lower()
                        if "password" in err_lower or "encrypt" in err_lower or "decrypt" in err_lower:
                            file_status = "password_error"
                        else:
                            file_status = "parse_error"
                    elif len(parsed_txns) == 0:
                        file_status = "no_transactions"
                    elif imported_count > 0:
                        file_status = "imported"
                        email_had_success = True
                    else:
                        file_status = "all_duplicates"
                        email_had_success = True

                    files_found.append({
                        "filename": filename,
                        "subject": subject[:80],
                        "email_date": email_date[:30],
                        "transactions_found": len(parsed_txns),
                        "transactions_imported": imported_count,
                        "duplicates": duplicate_count,
                        "status": file_status,
                        "error": parse_error[:120] if parse_error else None
                    })

            if email_had_success:
                await db.processed_emails.insert_one({
                    "email_hash": email_hash, "user_id": uid,
                    "account_id": account_id, "message_id": message_id,
                    "processed_at": datetime.now(timezone.utc).isoformat()
                })
    finally:
        mail.logout()

    filter_text = account["email_filter"]
    password_errors = sum(1 for f in files_found if f.get("status") == "password_error")
    parse_errors = sum(1 for f in files_found if f.get("status") == "parse_error")
    no_txn_files = sum(1 for f in files_found if f.get("status") == "no_transactions")
    dup_files = sum(1 for f in files_found if f.get("status") == "all_duplicates")
    imported_files = sum(1 for f in files_found if f.get("status") == "imported")
    total_pdfs = len(files_found)

    if emails_matched == 0:
        msg = f"No emails found matching filter \"{filter_text}\". Try adjusting the email filter keyword."
        status = "no_match"
    elif total_pdfs == 0 and total_skipped > 0:
        msg = f"All {total_skipped} matching emails were already synced."
        status = "up_to_date"
    elif total_pdfs == 0:
        msg = f"Found {emails_matched} emails but none contained PDF attachments."
        status = "no_pdfs"
    elif password_errors > 0 and total_imported == 0:
        msg = f"Found {total_pdfs} PDFs but couldn't open them — wrong or missing PDF password. Update the password on this account and re-sync."
        status = "password_error"
    elif parse_errors > 0 and total_imported == 0:
        msg = f"Found {total_pdfs} PDFs but couldn't extract transactions. Check if a custom parser is configured for this account."
        status = "parse_error"
    elif total_imported == 0 and dup_files > 0:
        msg = f"Found {total_pdfs} PDFs — all {sum(f.get('transactions_found', 0) for f in files_found)} transactions already exist. Nothing new to import."
        status = "all_duplicates"
    elif total_imported == 0 and no_txn_files > 0:
        msg = f"Found {total_pdfs} PDFs but no transactions could be extracted. The parser may not support this statement format."
        status = "no_transactions"
    else:
        parts = [f"Imported {total_imported} new transactions from {imported_files} PDFs."]
        if dup_files > 0:
            parts.append(f"{dup_files} PDFs had only existing transactions.")
        if password_errors > 0:
            parts.append(f"{password_errors} PDFs couldn't be opened (wrong password).")
        if total_skipped > 0:
            parts.append(f"{total_skipped} emails already synced.")
        msg = " ".join(parts)
        status = "success"

    await log_sync(uid, account_id, account["name"], status, total_imported, total_skipped, None, files_found, filter_text, emails_matched)

    categorized_count = 0
    if total_imported > 0:
        try:
            categories = await db.categories.find({"user_id": uid}, {"_id": 0}).to_list(200)
            if len(categories) == 0:
                await init_default_categories(uid)
                categories = await db.categories.find({"user_id": uid}, {"_id": 0}).to_list(200)
            uncategorized = await db.transactions.find(
                {"user_id": uid, "account_id": account_id, "category_id": None, "is_transfer": False},
                {"_id": 0}
            ).to_list(5000)
            if uncategorized:
                categorized_count = await ai_categorize_batch(uid, uncategorized, categories)
        except Exception as e:
            logger.warning(f"Auto-categorization after sync failed: {e}")

    return {
        "message": msg + (f" Auto-categorized {categorized_count} transactions." if categorized_count > 0 else ""),
        "status": status,
        "total_imported": total_imported,
        "total_skipped": total_skipped,
        "emails_matched": emails_matched,
        "categorized_count": categorized_count,
        "filter_used": filter_text,
        "files_found": files_found
    }


@router.get("/accounts/{account_id}/sync-history")
async def get_sync_history(account_id: str, user: Dict = Depends(get_current_user)):
    uid = user["user_id"]
    history = await db.sync_history.find(
        {"user_id": uid, "account_id": account_id}, {"_id": 0}
    ).sort("synced_at", -1).to_list(20)
    return history
