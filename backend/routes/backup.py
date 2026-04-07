from fastapi import APIRouter, Depends, Request
from typing import Dict
from datetime import datetime, timezone
from database import db
from auth import get_current_user

router = APIRouter(prefix="/api")


@router.get("/backup/export")
async def export_backup(user: Dict = Depends(get_current_user)):
    uid = user["user_id"]
    accounts = await db.accounts.find({"user_id": uid}, {"_id": 0}).to_list(1000)
    transactions = await db.transactions.find({"user_id": uid}, {"_id": 0}).to_list(50000)
    categories = await db.categories.find({"user_id": uid}, {"_id": 0}).to_list(100)

    return {
        "export_date": datetime.now(timezone.utc).isoformat(),
        "user": {"email": user["email"], "name": user["name"]},
        "accounts": accounts,
        "transactions": transactions,
        "categories": categories
    }


@router.post("/backup/import")
async def import_backup(request: Request, user: Dict = Depends(get_current_user)):
    uid = user["user_id"]
    body = await request.json()

    imported = {"accounts": 0, "transactions": 0, "categories": 0}

    for acc in body.get("accounts", []):
        existing = await db.accounts.find_one({"id": acc["id"], "user_id": uid})
        if not existing:
            acc["user_id"] = uid
            await db.accounts.insert_one(acc)
            imported["accounts"] += 1

    for cat in body.get("categories", []):
        existing = await db.categories.find_one({"id": cat["id"], "user_id": uid})
        if not existing:
            cat["user_id"] = uid
            await db.categories.insert_one(cat)
            imported["categories"] += 1

    for txn in body.get("transactions", []):
        existing = await db.transactions.find_one({"id": txn["id"], "user_id": uid})
        if not existing:
            txn["user_id"] = uid
            await db.transactions.insert_one(txn)
            imported["transactions"] += 1

    return {"message": "Backup restored", "imported": imported}


@router.post("/reset-all-data")
async def reset_all_data(user: Dict = Depends(get_current_user)):
    uid = user["user_id"]
    deleted = {}
    deleted["transactions"] = (await db.transactions.delete_many({"user_id": uid})).deleted_count
    deleted["accounts"] = (await db.accounts.delete_many({"user_id": uid})).deleted_count
    deleted["categories"] = (await db.categories.delete_many({"user_id": uid})).deleted_count
    deleted["sync_history"] = (await db.sync_history.delete_many({"user_id": uid})).deleted_count
    deleted["processed_emails"] = (await db.processed_emails.delete_many({"user_id": uid})).deleted_count
    deleted["vouchers"] = (await db.vouchers.delete_many({"user_id": uid})).deleted_count
    deleted["ledgers"] = (await db.ledgers.delete_many({"user_id": uid})).deleted_count
    deleted["account_groups"] = (await db.account_groups.delete_many({"user_id": uid})).deleted_count
    deleted["companies"] = (await db.companies.delete_many({"user_id": uid})).deleted_count
    return {"message": "All data has been reset", "deleted": deleted}
