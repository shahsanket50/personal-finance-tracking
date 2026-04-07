from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, List, Optional
from datetime import datetime
import uuid
from database import db
from models import Transaction, TransactionCreate, TransferCreate
from auth import get_current_user
from bridge import transaction_to_voucher

router = APIRouter(prefix="/api")


@router.post("/transactions", response_model=Transaction)
async def create_transaction(transaction: TransactionCreate, user: Dict = Depends(get_current_user)):
    txn = Transaction(**transaction.model_dump(), user_id=user["user_id"])
    doc = txn.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.transactions.insert_one(doc)

    account = await db.accounts.find_one({"id": transaction.account_id, "user_id": user["user_id"]})
    if account:
        balance_change = transaction.amount if transaction.transaction_type == "credit" else -transaction.amount
        await db.accounts.update_one(
            {"id": transaction.account_id},
            {"$set": {"current_balance": account['current_balance'] + balance_change}}
        )
        category = None
        if txn.category_id:
            category = await db.categories.find_one({"id": txn.category_id, "user_id": user["user_id"]}, {"_id": 0})
        try:
            await transaction_to_voucher(user["user_id"], txn, account, category)
        except Exception:
            pass

    return txn


@router.get("/transactions", response_model=List[Transaction])
async def get_transactions(
    account_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user: Dict = Depends(get_current_user)
):
    query = {"user_id": user["user_id"]}
    if account_id:
        query["account_id"] = account_id
    if start_date and end_date:
        query["date"] = {"$gte": start_date, "$lte": end_date}

    transactions = await db.transactions.find(query, {"_id": 0}).sort("date", -1).to_list(10000)
    for txn in transactions:
        if isinstance(txn.get('created_at'), str):
            txn['created_at'] = datetime.fromisoformat(txn['created_at'])
    return transactions


@router.put("/transactions/{transaction_id}", response_model=Transaction)
async def update_transaction(transaction_id: str, transaction: TransactionCreate, user: Dict = Depends(get_current_user)):
    old_txn = await db.transactions.find_one({"id": transaction_id, "user_id": user["user_id"]})
    if not old_txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    old_balance_change = old_txn['amount'] if old_txn['transaction_type'] == "credit" else -old_txn['amount']
    account = await db.accounts.find_one({"id": old_txn['account_id']})
    if account:
        await db.accounts.update_one(
            {"id": old_txn['account_id']},
            {"$set": {"current_balance": account['current_balance'] - old_balance_change}}
        )

    update_data = transaction.model_dump()
    result = await db.transactions.find_one_and_update(
        {"id": transaction_id, "user_id": user["user_id"]},
        {"$set": update_data},
        return_document=True
    )

    new_balance_change = transaction.amount if transaction.transaction_type == "credit" else -transaction.amount
    account = await db.accounts.find_one({"id": transaction.account_id})
    if account:
        await db.accounts.update_one(
            {"id": transaction.account_id},
            {"$set": {"current_balance": account['current_balance'] + new_balance_change}}
        )

    if '_id' in result:
        del result['_id']
    if isinstance(result.get('created_at'), str):
        result['created_at'] = datetime.fromisoformat(result['created_at'])
    return Transaction(**result)


@router.delete("/transactions/{transaction_id}")
async def delete_transaction(transaction_id: str, user: Dict = Depends(get_current_user)):
    txn = await db.transactions.find_one({"id": transaction_id, "user_id": user["user_id"]})
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    balance_change = txn['amount'] if txn['transaction_type'] == "credit" else -txn['amount']
    account = await db.accounts.find_one({"id": txn['account_id']})
    if account:
        await db.accounts.update_one(
            {"id": txn['account_id']},
            {"$set": {"current_balance": account['current_balance'] - balance_change}}
        )

    await db.transactions.delete_one({"id": transaction_id})
    linked_voucher = await db.vouchers.find_one({"user_id": user["user_id"], "linked_transaction_id": transaction_id})
    if linked_voucher:
        await db.vouchers.delete_one({"id": linked_voucher["id"], "user_id": user["user_id"]})
    return {"message": "Transaction deleted"}


@router.post("/transfers")
async def create_transfer(transfer: TransferCreate, user: Dict = Depends(get_current_user)):
    transfer_id = str(uuid.uuid4())
    uid = user["user_id"]

    transfer_cat = await db.categories.find_one({"name": "Transfer", "user_id": uid})
    transfer_cat_id = transfer_cat['id'] if transfer_cat else None

    debit_txn = Transaction(
        user_id=uid, account_id=transfer.from_account_id,
        date=transfer.date,
        description=f"{transfer.description} (to account)",
        amount=transfer.amount, transaction_type="debit",
        category_id=transfer_cat_id, is_transfer=True, transfer_pair_id=transfer_id
    )
    credit_txn = Transaction(
        user_id=uid, account_id=transfer.to_account_id,
        date=transfer.date,
        description=f"{transfer.description} (from account)",
        amount=transfer.amount, transaction_type="credit",
        category_id=transfer_cat_id, is_transfer=True, transfer_pair_id=transfer_id
    )

    for txn in [debit_txn, credit_txn]:
        doc = txn.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        await db.transactions.insert_one(doc)

    from_account = await db.accounts.find_one({"id": transfer.from_account_id, "user_id": uid})
    if from_account:
        await db.accounts.update_one(
            {"id": transfer.from_account_id},
            {"$set": {"current_balance": from_account['current_balance'] - transfer.amount}}
        )
    to_account = await db.accounts.find_one({"id": transfer.to_account_id, "user_id": uid})
    if to_account:
        await db.accounts.update_one(
            {"id": transfer.to_account_id},
            {"$set": {"current_balance": to_account['current_balance'] + transfer.amount}}
        )

    return {"message": "Transfer created", "transfer_id": transfer_id}


@router.post("/detect-transfers")
async def detect_transfers(user: Dict = Depends(get_current_user)):
    all_txns = await db.transactions.find(
        {"is_transfer": False, "user_id": user["user_id"]}, {"_id": 0}
    ).to_list(10000)

    matched_pairs = []
    processed_ids = set()

    def date_close(d1, d2):
        try:
            from datetime import datetime as dt
            p1 = dt.strptime(d1, "%Y-%m-%d") if isinstance(d1, str) else d1
            p2 = dt.strptime(d2, "%Y-%m-%d") if isinstance(d2, str) else d2
            return abs((p1 - p2).days) <= 1
        except Exception:
            return d1 == d2

    transfer_keywords = ["transfer", "neft", "imps", "upi", "rtgs", "fund transfer", "self transfer", "a/c"]

    def has_transfer_hint(desc):
        if not desc:
            return False
        lower = desc.lower()
        return any(kw in lower for kw in transfer_keywords)

    for i, txn1 in enumerate(all_txns):
        if txn1['id'] in processed_ids:
            continue
        best_match = None
        best_score = 0
        for txn2 in all_txns[i+1:]:
            if txn2['id'] in processed_ids:
                continue
            if (abs(txn1['amount'] - txn2['amount']) < 0.01 and
                txn1['transaction_type'] != txn2['transaction_type'] and
                txn1['account_id'] != txn2['account_id'] and
                date_close(txn1['date'], txn2['date'])):
                score = 1
                if txn1['date'] == txn2['date']:
                    score += 2
                if has_transfer_hint(txn1.get('description', '')):
                    score += 1
                if has_transfer_hint(txn2.get('description', '')):
                    score += 1
                if score > best_score:
                    best_score = score
                    best_match = txn2
        if best_match:
            confidence = "high" if best_score >= 3 else "medium"
            matched_pairs.append({
                "txn1": txn1, "txn2": best_match,
                "amount": txn1['amount'], "date": txn1['date'],
                "confidence": confidence
            })
            processed_ids.add(txn1['id'])
            processed_ids.add(best_match['id'])

    return {"potential_transfers": matched_pairs, "count": len(matched_pairs)}


@router.post("/mark-as-transfer")
async def mark_as_transfer(txn_ids: List[str], user: Dict = Depends(get_current_user)):
    if len(txn_ids) != 2:
        raise HTTPException(status_code=400, detail="Need exactly 2 transaction IDs")

    transfer_id = str(uuid.uuid4())
    transfer_cat = await db.categories.find_one({"name": "Transfer", "user_id": user["user_id"]})
    transfer_cat_id = transfer_cat['id'] if transfer_cat else None

    for txn_id in txn_ids:
        await db.transactions.update_one(
            {"id": txn_id, "user_id": user["user_id"]},
            {"$set": {"is_transfer": True, "transfer_pair_id": transfer_id, "category_id": transfer_cat_id}}
        )

    return {"message": "Transactions marked as transfer"}
