import logging
from database import db
from models import Transaction, Voucher, Ledger

logger = logging.getLogger(__name__)


async def voucher_to_transaction(uid, voucher):
    """When a voucher is created in Accounting view, auto-create Finance Tracker transaction if applicable"""
    entries = voucher.entries if isinstance(voucher.entries, list) else []
    if len(entries) != 2:
        return

    for i, entry in enumerate(entries):
        ledger = await db.ledgers.find_one({"id": entry.get("ledger_id"), "user_id": uid}, {"_id": 0})
        if ledger and ledger.get("linked_account_id"):
            other = entries[1 - i]
            amount = entry.get("credit", 0) or entry.get("debit", 0)
            txn_type = "debit" if entry.get("credit", 0) > 0 else "credit"
            txn = Transaction(
                user_id=uid, account_id=ledger["linked_account_id"],
                date=voucher.date if isinstance(voucher.date, str) else voucher.date,
                description=voucher.narration or f"Voucher {voucher.voucher_number}",
                amount=amount, transaction_type=txn_type
            )
            other_ledger = await db.ledgers.find_one({"id": other.get("ledger_id"), "user_id": uid}, {"_id": 0})
            if other_ledger and other_ledger.get("linked_category_id"):
                txn.category_id = other_ledger["linked_category_id"]
            doc = txn.model_dump()
            doc['created_at'] = doc['created_at'].isoformat()
            await db.transactions.insert_one(doc)
            bal_change = -amount if txn_type == "debit" else amount
            await db.accounts.update_one({"id": ledger["linked_account_id"], "user_id": uid}, {"$inc": {"current_balance": bal_change}})
            await db.vouchers.update_one({"id": voucher.id}, {"$set": {"linked_transaction_id": txn.id}})
            return


async def transaction_to_voucher(uid, txn, account, category=None):
    """When a transaction is created in Finance Tracker, auto-create a voucher in Accounting"""
    company = await db.companies.find_one({"user_id": uid}, {"_id": 0})
    if not company:
        return

    account_ledger = await db.ledgers.find_one({"linked_account_id": account["id"], "user_id": uid}, {"_id": 0})
    if not account_ledger:
        bank_group = await db.account_groups.find_one({"user_id": uid, "name": "Bank Accounts"}, {"_id": 0})
        if account["account_type"] == "cash":
            bank_group = await db.account_groups.find_one({"user_id": uid, "name": "Cash-in-Hand"}, {"_id": 0})
        if not bank_group:
            return
        account_ledger = Ledger(
            user_id=uid, company_id=company["id"],
            name=account["name"], group_id=bank_group["id"],
            linked_account_id=account["id"]
        )
        doc = account_ledger.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        await db.ledgers.insert_one(doc)
        account_ledger = doc

    category_ledger = None
    if category:
        category_ledger = await db.ledgers.find_one({"linked_category_id": category["id"], "user_id": uid}, {"_id": 0})
        if not category_ledger:
            if category["category_type"] == "expense":
                cat_group = await db.account_groups.find_one({"user_id": uid, "name": "Indirect Expenses"}, {"_id": 0})
            else:
                cat_group = await db.account_groups.find_one({"user_id": uid, "name": "Direct Income"}, {"_id": 0})
            if cat_group:
                category_ledger = Ledger(
                    user_id=uid, company_id=company["id"],
                    name=category["name"], group_id=cat_group["id"],
                    linked_category_id=category["id"]
                )
                doc = category_ledger.model_dump()
                doc['created_at'] = doc['created_at'].isoformat()
                await db.ledgers.insert_one(doc)
                category_ledger = doc

    if not category_ledger:
        category_ledger = await db.ledgers.find_one({"user_id": uid, "name": "Suspense Account"}, {"_id": 0})
        if not category_ledger:
            misc_group = await db.account_groups.find_one({"user_id": uid, "name": "Indirect Expenses"}, {"_id": 0})
            if misc_group:
                category_ledger = Ledger(user_id=uid, company_id=company["id"], name="Suspense Account", group_id=misc_group["id"])
                doc = category_ledger.model_dump()
                doc['created_at'] = doc['created_at'].isoformat()
                await db.ledgers.insert_one(doc)
                category_ledger = doc
            else:
                return

    acc_lid = account_ledger["id"]
    cat_lid = category_ledger["id"]

    if txn.transaction_type == "debit":
        entries = [
            {"ledger_id": cat_lid, "debit": txn.amount, "credit": 0},
            {"ledger_id": acc_lid, "debit": 0, "credit": txn.amount}
        ]
        voucher_type = "payment"
    else:
        entries = [
            {"ledger_id": acc_lid, "debit": txn.amount, "credit": 0},
            {"ledger_id": cat_lid, "debit": 0, "credit": txn.amount}
        ]
        voucher_type = "receipt"

    count = await db.vouchers.count_documents({"user_id": uid, "voucher_type": voucher_type})
    prefix = "PMT" if voucher_type == "payment" else "RCT"

    voucher = Voucher(
        user_id=uid, company_id=company["id"],
        voucher_number=f"{prefix}-{count + 1:04d}",
        voucher_type=voucher_type, date=txn.date,
        narration=txn.description, entries=entries,
        linked_transaction_id=txn.id
    )
    doc = voucher.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.vouchers.insert_one(doc)
