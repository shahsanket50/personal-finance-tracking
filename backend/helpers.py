import logging
import re
from datetime import datetime, timezone
from database import db
from models import (
    Category, Company, AccountGroup, Ledger,
    DEFAULT_CATEGORIES, DEFAULT_ACCOUNT_GROUPS,
)

logger = logging.getLogger(__name__)


async def init_default_categories(user_id: str):
    for cat_data in DEFAULT_CATEGORIES:
        existing = await db.categories.find_one({"name": cat_data["name"], "is_default": True, "user_id": user_id})
        if not existing:
            cat = Category(**cat_data, user_id=user_id)
            doc = cat.model_dump()
            doc['created_at'] = doc['created_at'].isoformat()
            await db.categories.insert_one(doc)


async def init_default_company_and_coa(user_id: str):
    """Initialize a default company and Chart of Accounts for a user"""
    existing = await db.companies.find_one({"user_id": user_id}, {"_id": 0})
    if existing:
        return existing["id"]

    company = Company(user_id=user_id, name="My Business")
    doc = company.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.companies.insert_one(doc)
    company_id = company.id

    group_map = {}
    for g in DEFAULT_ACCOUNT_GROUPS:
        parent_id = group_map.get(g["parent"]) if g["parent"] else None
        grp = AccountGroup(
            user_id=user_id, company_id=company_id,
            name=g["name"], parent_id=parent_id,
            nature=g["nature"], is_default=True, sort_order=g["sort"]
        )
        await db.account_groups.insert_one(grp.model_dump())
        group_map[g["name"]] = grp.id

    defaults = [
        ("Cash", "Cash-in-Hand", 0, "dr"),
        ("Profit & Loss A/c", "Direct Income", 0, "cr"),
    ]
    for name, group_name, bal, bal_type in defaults:
        gid = group_map.get(group_name)
        if gid:
            ledger = Ledger(user_id=user_id, company_id=company_id, name=name, group_id=gid, opening_balance=bal, opening_type=bal_type)
            doc = ledger.model_dump()
            doc['created_at'] = doc['created_at'].isoformat()
            await db.ledgers.insert_one(doc)

    return company_id


def is_subject_before_date(subject: str, cutoff_date) -> bool:
    """Check if an email subject contains a statement period that's before the cutoff date."""
    MONTH_MAP = {
        'jan': 1, 'january': 1, 'feb': 2, 'february': 2, 'mar': 3, 'march': 3,
        'apr': 4, 'april': 4, 'may': 5, 'jun': 6, 'june': 6,
        'jul': 7, 'july': 7, 'aug': 8, 'august': 8, 'sep': 9, 'september': 9,
        'oct': 10, 'october': 10, 'nov': 11, 'november': 11, 'dec': 12, 'december': 12,
    }
    subject_lower = subject.lower()

    match = re.search(r'(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)[- /]?(20\d{2})', subject_lower)
    if match:
        month = MONTH_MAP.get(match.group(1))
        year = int(match.group(2))
        if month and year:
            try:
                statement_date = datetime(year, month, 1)
                if statement_date < cutoff_date:
                    return True
            except Exception:
                pass

    match = re.search(r'(20\d{2})[- /](0[1-9]|1[0-2])', subject_lower)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        try:
            statement_date = datetime(year, month, 1)
            if statement_date < cutoff_date:
                return True
        except Exception:
            pass

    match = re.search(r'(0[1-9]|1[0-2])[- /](20\d{2})', subject_lower)
    if match:
        month = int(match.group(1))
        year = int(match.group(2))
        try:
            statement_date = datetime(year, month, 1)
            if statement_date < cutoff_date:
                return True
        except Exception:
            pass

    return False


async def ai_categorize_batch(uid: str, txns: list, categories: list) -> int:
    """Categorize a batch of transactions using AI. Returns count categorized.
    Processes in chunks of 80 to avoid hitting LLM context limits."""
    import os
    import uuid

    if not txns or not categories:
        return 0

    category_map = {c['name'].lower().strip(): c['id'] for c in categories}

    income_cats = ', '.join([c['name'] for c in categories if c['category_type'] == 'income'])
    expense_cats = ', '.join([c['name'] for c in categories if c['category_type'] == 'expense' and c['name'] != 'Transfer'])

    from emergentintegrations.llm.chat import LlmChat, UserMessage
    import json as json_mod

    total_categorized = 0
    chunk_size = 80

    for start in range(0, len(txns), chunk_size):
        chunk = txns[start:start + chunk_size]
        descriptions = [{"id": t["id"], "desc": t["description"], "amount": t["amount"], "type": t["transaction_type"]} for t in chunk]

        prompt = f"""You are an expert Indian personal finance categorizer. Categorize each transaction into EXACTLY ONE of these categories:

INCOME categories: {income_cats}
EXPENSE categories: {expense_cats}

RULES:
1. For CREDIT (income) transactions, always pick from INCOME categories
2. For DEBIT (expense) transactions, always pick from EXPENSE categories
3. Match based on description keywords — e.g. "Swiggy"/"Zomato" = "Food Delivery", "Amazon"/"Flipkart" = varies by context, "IRCTC" = "Public Transport", "Netflix"/"Hotstar" = "Subscriptions / OTT"
4. Indian bank descriptions often have codes like "UPI/", "NEFT/", "IMPS/" — look past these to the merchant/payee name
5. If genuinely uncertain, use "Other / Miscellaneous"
6. Category name must EXACTLY match one from the list above (case-insensitive)

Return ONLY a valid JSON array. No markdown, no explanation. Each object: {{"id": "<transaction_id>", "category": "<exact_category_name>"}}

Transactions to categorize:
{descriptions}"""

        try:
            chat = LlmChat(
                api_key=os.environ.get("EMERGENT_LLM_KEY", ""),
                session_id=f"categorize_{uid}_{uuid.uuid4().hex[:8]}",
                system_message="You are a financial transaction categorizer for Indian bank/credit card statements. Return only valid JSON arrays. No markdown formatting."
            )
            chat.with_model("gemini", "gemini-2.5-flash")

            response = await chat.send_message(UserMessage(text=prompt))

            json_text = response.strip()
            if "```json" in json_text:
                json_text = json_text.split("```json")[1].split("```")[0].strip()
            elif "```" in json_text:
                json_text = json_text.split("```")[1].split("```")[0].strip()

            categorizations = json_mod.loads(json_text)

            for item in categorizations:
                txn_id = item.get("id")
                cat_name = item.get("category", "").lower().strip()
                cat_id = category_map.get(cat_name)
                if not cat_id:
                    for k, v in category_map.items():
                        if cat_name in k or k in cat_name:
                            cat_id = v
                            break
                if txn_id and cat_id:
                    result = await db.transactions.update_one(
                        {"id": txn_id, "user_id": uid},
                        {"$set": {"category_id": cat_id}}
                    )
                    if result.modified_count > 0:
                        total_categorized += 1
        except Exception as e:
            logger.warning(f"AI categorize chunk {start}-{start+chunk_size} failed: {e}")
            continue

    return total_categorized


async def log_sync(user_id, account_id, account_name, status, imported, skipped, error=None, files=None, filter_used=None, emails_matched=0):
    await db.sync_history.insert_one({
        "user_id": user_id,
        "account_id": account_id,
        "account_name": account_name,
        "status": status,
        "imported": imported,
        "skipped": skipped,
        "error": error,
        "files": files or [],
        "filter_used": filter_used,
        "emails_matched": emails_matched,
        "synced_at": datetime.now(timezone.utc).isoformat()
    })


async def imap_connect_and_search(email_config, account):
    """Connect to IMAP, search emails matching account filters. Returns (mail_conn, message_ids, sync_since_date, error_msg)"""
    import imaplib

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
        error_msg = str(e)
        if error_msg.startswith("b'") or error_msg.startswith('b"'):
            error_msg = error_msg[2:-1]
        if "Application-specific password" in error_msg or "app password" in error_msg.lower():
            error_msg = "Gmail requires an App Password for IMAP access. Generate one at myaccount.google.com/apppasswords (2FA must be enabled)."
        elif "authentication failed" in error_msg.lower() or "invalid credentials" in error_msg.lower():
            error_msg = "Login failed. Check your email address and App Password in Settings."
        return None, [], None, error_msg

    sync_since_date = None
    if email_config.get("sync_since"):
        try:
            sync_since_date = datetime.strptime(email_config["sync_since"], "%Y-%m-%d")
        except Exception:
            pass

    filter_text = account["email_filter"]
    from_filter = account.get("email_from_filter", "")
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
    return mail, message_ids, sync_since_date, None
