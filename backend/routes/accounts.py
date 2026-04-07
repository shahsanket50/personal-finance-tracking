from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, List
from datetime import datetime
from database import db
from models import Account, AccountCreate
from auth import get_current_user

router = APIRouter(prefix="/api")


@router.post("/accounts", response_model=Account)
async def create_account(account: AccountCreate, user: Dict = Depends(get_current_user)):
    acc = Account(**account.model_dump(), user_id=user["user_id"], current_balance=account.start_balance)
    doc = acc.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.accounts.insert_one(doc)
    return acc


@router.get("/accounts", response_model=List[Account])
async def get_accounts(user: Dict = Depends(get_current_user)):
    accounts = await db.accounts.find({"user_id": user["user_id"]}, {"_id": 0}).to_list(1000)
    for acc in accounts:
        if isinstance(acc.get('created_at'), str):
            acc['created_at'] = datetime.fromisoformat(acc['created_at'])
    return accounts


@router.put("/accounts/{account_id}", response_model=Account)
async def update_account(account_id: str, account: AccountCreate, user: Dict = Depends(get_current_user)):
    update_data = account.model_dump()
    result = await db.accounts.find_one_and_update(
        {"id": account_id, "user_id": user["user_id"]},
        {"$set": update_data},
        return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Account not found")
    if '_id' in result:
        del result['_id']
    if isinstance(result.get('created_at'), str):
        result['created_at'] = datetime.fromisoformat(result['created_at'])
    return Account(**result)


@router.delete("/accounts/{account_id}")
async def delete_account(account_id: str, user: Dict = Depends(get_current_user)):
    uid = user["user_id"]
    result = await db.accounts.delete_one({"id": account_id, "user_id": uid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Account not found")
    txn_result = await db.transactions.delete_many({"account_id": account_id, "user_id": uid})
    await db.sync_history.delete_many({"account_id": account_id, "user_id": uid})
    await db.processed_emails.delete_many({"account_id": account_id, "user_id": uid})
    return {"message": f"Account deleted along with {txn_result.deleted_count} transactions"}
