import logging
import os
from datetime import datetime
import boto3
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from typing import Dict
from database import db
from models import Transaction
from auth import get_current_user
from helpers import init_default_categories, ai_categorize_batch
from bridge import transaction_to_voucher
from pdf_parsers_simple import get_simple_parser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


@router.post("/upload-statement")
async def upload_statement(
    file: UploadFile = File(...),
    account_id: str = Query(...),
    password: str = Query(default="", description="PDF password if protected"),
    user: Dict = Depends(get_current_user)
):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    try:
        contents = await file.read()
        logger.info(f"Processing PDF: {file.filename}, Size: {len(contents)} bytes")

        s3_bucket = os.environ.get("AWS_S3_BUCKET")
        if s3_bucket:
            try:
                s3_client = boto3.client("s3")
                s3_key = f"uploads/{user['user_id']}/{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{file.filename}"
                s3_client.put_object(Bucket=s3_bucket, Key=s3_key, Body=contents)
                logger.info(f"Uploaded {file.filename} to s3://{s3_bucket}/{s3_key}")
            except Exception as s3_err:
                logger.warning(f"S3 upload failed (non-fatal): {s3_err}")

        account = await db.accounts.find_one({"id": account_id, "user_id": user["user_id"]})
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        account_name = account['name']
        if not password and account.get('pdf_password'):
            password = account['pdf_password']

        custom_pattern = account.get('custom_parser')
        parser = get_simple_parser(account_name, custom_pattern)
        parsed_transactions = parser.parse(contents, password or None)
        logger.info(f"Parsed {len(parsed_transactions)} transactions")

        if not parsed_transactions:
            return {
                "message": "No transactions found in PDF",
                "imported_count": 0,
                "note": f"Unable to parse transactions for {account_name}. Try configuring a parser via Parser Builder."
            }

        imported_count = 0
        uid = user["user_id"]
        for txn_data in parsed_transactions:
            existing = await db.transactions.find_one({
                "account_id": account_id, "user_id": uid,
                "date": txn_data['date'], "description": txn_data['description'],
                "amount": txn_data['amount']
            })
            if existing:
                continue

            txn = Transaction(
                user_id=uid, account_id=account_id,
                date=txn_data['date'], description=txn_data['description'],
                amount=txn_data['amount'], transaction_type=txn_data['type']
            )
            doc = txn.model_dump()
            doc['created_at'] = doc['created_at'].isoformat()
            await db.transactions.insert_one(doc)

            balance_change = txn_data['amount'] if txn_data['type'] == "credit" else -txn_data['amount']
            await db.accounts.update_one(
                {"id": account_id},
                {"$set": {"current_balance": account['current_balance'] + balance_change}}
            )
            account['current_balance'] += balance_change
            try:
                await transaction_to_voucher(uid, txn, account, None)
            except Exception:
                pass
            imported_count += 1

        categorized_count = 0
        if imported_count > 0:
            try:
                cats = await db.categories.find({"user_id": uid}, {"_id": 0}).to_list(200)
                if len(cats) == 0:
                    await init_default_categories(uid)
                    cats = await db.categories.find({"user_id": uid}, {"_id": 0}).to_list(200)
                uncat = await db.transactions.find(
                    {"user_id": uid, "account_id": account_id, "category_id": None, "is_transfer": False},
                    {"_id": 0}
                ).to_list(5000)
                if uncat:
                    categorized_count = await ai_categorize_batch(uid, uncat, cats)
            except Exception as e:
                logger.warning(f"Auto-categorization after upload failed: {e}")

        return {
            "message": f"Successfully imported {imported_count} transactions" + (f", auto-categorized {categorized_count}" if categorized_count > 0 else ""),
            "imported_count": imported_count,
            "categorized_count": categorized_count,
            "total_found": len(parsed_transactions),
            "duplicates_skipped": len(parsed_transactions) - imported_count
        }
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error processing PDF: {error_msg}")
        status = 400 if "password" in error_msg.lower() else 500
        raise HTTPException(status_code=status, detail=f"Error processing PDF: {error_msg}")


@router.post("/build-parser")
async def build_parser(
    file: UploadFile = File(...),
    account_id: str = Query(...),
    password: str = Query(default=""),
    user: Dict = Depends(get_current_user)
):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    try:
        contents = await file.read()
        account = await db.accounts.find_one({"id": account_id, "user_id": user["user_id"]})
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        parser = get_simple_parser(account['name'])
        text = parser.extract_text(contents, password or None)
        detection = parser.detect_best_strategy(contents, password or None)
        return {
            "text": text,
            "text_length": len(text),
            "lines": text.split('\n')[:100],
            "transactions_found": len(detection['transactions']),
            "sample_transactions": detection['transactions'][:20],
            "detected_strategy": detection['strategy'],
            "all_strategies": detection['all_results']
        }
    except Exception as e:
        logger.error(f"Error in parser builder: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save-parser-pattern")
async def save_parser_pattern(
    account_id: str = Query(...),
    password: str = Query(default=""),
    strategy: str = Query(default=""),
    user: Dict = Depends(get_current_user)
):
    update_data = {}
    if strategy:
        update_data["custom_parser"] = {"strategy": strategy}
    else:
        update_data["custom_parser"] = None
    if password:
        update_data["pdf_password"] = password
    result = await db.accounts.update_one(
        {"id": account_id, "user_id": user["user_id"]},
        {"$set": update_data}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"message": "Parser pattern saved successfully", "strategy": strategy}


@router.post("/test-parser-pattern")
async def test_parser_pattern(
    file: UploadFile = File(...),
    account_id: str = Query(...),
    pattern: str = Query(...),
    password: str = Query(default=""),
    user: Dict = Depends(get_current_user)
):
    try:
        contents = await file.read()
        account = await db.accounts.find_one({"id": account_id, "user_id": user["user_id"]})
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        import json
        test_pattern = json.loads(pattern)
        parser = get_simple_parser(account['name'], test_pattern)
        transactions = parser.parse(contents, password or None)
        return {"transactions_found": len(transactions), "transactions": transactions[:20]}
    except Exception as e:
        return {"error": str(e), "transactions_found": 0}


@router.post("/debug-pdf")
async def debug_pdf_upload(
    file: UploadFile = File(...),
    password: str = Query(default="", description="PDF password if protected")
):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    try:
        contents = await file.read()
        parser = get_simple_parser("Debug Account")
        extracted_text = parser.extract_text(contents, password or None)
        parsed_transactions = parser.parse(contents, password or None)
        return {
            "filename": file.filename,
            "file_size": len(contents),
            "parser_used": parser.__class__.__name__,
            "text_length": len(extracted_text),
            "text_preview": extracted_text[:1000],
            "text_full": extracted_text,
            "transactions_found": len(parsed_transactions),
            "transactions": parsed_transactions[:10],
            "all_transactions": parsed_transactions
        }
    except Exception as e:
        logger.error(f"Error debugging PDF: {str(e)}")
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "filename": file.filename
        }


@router.post("/import-csv")
async def import_csv(
    file: UploadFile = File(...),
    account_id: str = Query(...),
    user: Dict = Depends(get_current_user)
):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")
    try:
        contents = await file.read()

        s3_bucket = os.environ.get("AWS_S3_BUCKET")
        if s3_bucket:
            try:
                s3_client = boto3.client("s3")
                s3_key = f"uploads/{user['user_id']}/{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{file.filename}"
                s3_client.put_object(Bucket=s3_bucket, Key=s3_key, Body=contents)
                logger.info(f"Uploaded {file.filename} to s3://{s3_bucket}/{s3_key}")
            except Exception as s3_err:
                logger.warning(f"S3 upload failed (non-fatal): {s3_err}")

        csv_text = contents.decode('utf-8')
        lines = csv_text.strip().split('\n')
        if len(lines) < 2:
            raise HTTPException(status_code=400, detail="CSV file is empty or invalid")

        uid = user["user_id"]
        imported_count = 0
        for line in lines[1:]:
            parts = line.split(',', 3)
            if len(parts) >= 4:
                date, description, amount, txn_type = parts
                txn = Transaction(
                    user_id=uid, account_id=account_id,
                    date=date.strip(), description=description.strip(),
                    amount=float(amount.strip()), transaction_type=txn_type.strip().lower()
                )
                doc = txn.model_dump()
                doc['created_at'] = doc['created_at'].isoformat()
                await db.transactions.insert_one(doc)

                account = await db.accounts.find_one({"id": account_id})
                if account:
                    balance_change = float(amount.strip()) if txn_type.strip().lower() == "credit" else -float(amount.strip())
                    await db.accounts.update_one(
                        {"id": account_id},
                        {"$set": {"current_balance": account['current_balance'] + balance_change}}
                    )
                    try:
                        await transaction_to_voucher(uid, txn, account, None)
                    except Exception:
                        pass
                imported_count += 1

        categorized_count = 0
        if imported_count > 0:
            try:
                cats = await db.categories.find({"user_id": uid}, {"_id": 0}).to_list(200)
                if len(cats) == 0:
                    await init_default_categories(uid)
                    cats = await db.categories.find({"user_id": uid}, {"_id": 0}).to_list(200)
                uncat = await db.transactions.find(
                    {"user_id": uid, "account_id": account_id, "category_id": None, "is_transfer": False},
                    {"_id": 0}
                ).to_list(5000)
                if uncat:
                    categorized_count = await ai_categorize_batch(uid, uncat, cats)
            except Exception as e:
                logger.warning(f"Auto-categorization after CSV import failed: {e}")

        return {"message": f"Imported {imported_count} transactions" + (f", auto-categorized {categorized_count}" if categorized_count > 0 else "")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error importing CSV: {str(e)}")
