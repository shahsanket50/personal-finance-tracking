from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, List, Optional
from datetime import datetime, timezone
from collections import defaultdict
from database import db
from models import (
    CompanyCreate, AccountGroup, Ledger, LedgerCreate,
    Voucher, VoucherCreate, Transaction,
)
from auth import get_current_user
from helpers import init_default_company_and_coa
from bridge import voucher_to_transaction, transaction_to_voucher

router = APIRouter(prefix="/api")


# ─── Company ──────────────────────────────────────────────────────────
@router.get("/company")
async def get_company(user: Dict = Depends(get_current_user)):
    company_id = await init_default_company_and_coa(user["user_id"])
    company = await db.companies.find_one({"id": company_id, "user_id": user["user_id"]}, {"_id": 0})
    return company


@router.put("/company")
async def update_company(data: CompanyCreate, user: Dict = Depends(get_current_user)):
    company = await db.companies.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    await db.companies.update_one(
        {"id": company["id"], "user_id": user["user_id"]},
        {"$set": data.model_dump()}
    )
    return {"message": "Company updated"}


@router.get("/financial-years")
async def get_financial_years(user: Dict = Depends(get_current_user)):
    uid = user["user_id"]
    company = await db.companies.find_one({"user_id": uid}, {"_id": 0})
    if not company:
        return {"years": [], "current_fy": None}
    fy_start = company.get("fy_start_month", 4)

    pipeline = [
        {"$match": {"user_id": uid}},
        {"$group": {"_id": None, "min_date": {"$min": "$date"}, "max_date": {"$max": "$date"}}}
    ]
    result = await db.vouchers.aggregate(pipeline).to_list(1)

    txn_pipeline = [
        {"$match": {"user_id": uid}},
        {"$group": {"_id": None, "min_date": {"$min": "$date"}, "max_date": {"$max": "$date"}}}
    ]
    txn_result = await db.transactions.aggregate(txn_pipeline).to_list(1)

    all_min_dates = []
    all_max_dates = []
    if result and result[0].get("min_date"):
        all_min_dates.append(result[0]["min_date"])
        all_max_dates.append(result[0]["max_date"])
    if txn_result and txn_result[0].get("min_date"):
        all_min_dates.append(txn_result[0]["min_date"])
        all_max_dates.append(txn_result[0]["max_date"])

    if not all_min_dates:
        now = datetime.now(timezone.utc)
        current_year = now.year if now.month >= fy_start else now.year - 1
        return {
            "years": [{"label": f"FY {current_year}-{str(current_year+1)[-2:]}", "start": f"{current_year}-{fy_start:02d}-01", "end": f"{current_year+1}-{fy_start-1:02d}-{28 if fy_start-1 == 2 else 31 if fy_start-1 in [1,3,5,7,8,10,12] else 30}"}],
            "current_fy": f"FY {current_year}-{str(current_year+1)[-2:]}"
        }

    min_date_str = min(all_min_dates)
    max_date_str = max(all_max_dates)

    from datetime import date as date_type
    try:
        min_d = date_type.fromisoformat(min_date_str[:10])
        max_d = date_type.fromisoformat(max_date_str[:10])
    except Exception:
        now = datetime.now(timezone.utc)
        min_d = date_type(now.year, 1, 1)
        max_d = date_type(now.year, 12, 31)

    min_fy = min_d.year if min_d.month >= fy_start else min_d.year - 1
    max_fy = max_d.year if max_d.month >= fy_start else max_d.year - 1
    now = datetime.now(timezone.utc)
    current_fy_year = now.year if now.month >= fy_start else now.year - 1
    max_fy = max(max_fy, current_fy_year)

    years = []
    for y in range(max_fy, min_fy - 1, -1):
        last_month = fy_start - 1 if fy_start > 1 else 12
        last_day = 28 if last_month == 2 else 31 if last_month in [1, 3, 5, 7, 8, 10, 12] else 30
        end_year = y + 1 if fy_start > 1 else y
        years.append({
            "label": f"FY {y}-{str(y+1)[-2:]}",
            "start": f"{y}-{fy_start:02d}-01",
            "end": f"{end_year}-{last_month:02d}-{last_day:02d}"
        })

    return {
        "years": years,
        "current_fy": f"FY {current_fy_year}-{str(current_fy_year+1)[-2:]}"
    }


# ─── Account Groups (Chart of Accounts) ──────────────────────────────
@router.get("/account-groups")
async def get_account_groups(user: Dict = Depends(get_current_user)):
    await init_default_company_and_coa(user["user_id"])
    groups = await db.account_groups.find({"user_id": user["user_id"]}, {"_id": 0}).to_list(200)
    return groups


@router.post("/account-groups")
async def create_account_group(data: Dict, user: Dict = Depends(get_current_user)):
    company = await db.companies.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not company:
        raise HTTPException(status_code=400, detail="No company set up")
    grp = AccountGroup(
        user_id=user["user_id"], company_id=company["id"],
        name=data["name"], parent_id=data.get("parent_id"),
        nature=data["nature"], is_default=False, sort_order=99
    )
    await db.account_groups.insert_one(grp.model_dump())
    return {"id": grp.id, "message": "Group created"}


# ─── Ledgers ─────────────────────────────────────────────────────────
@router.get("/ledgers")
async def get_ledgers(user: Dict = Depends(get_current_user)):
    await init_default_company_and_coa(user["user_id"])
    ledgers = await db.ledgers.find({"user_id": user["user_id"]}, {"_id": 0}).to_list(500)
    return ledgers


@router.post("/ledgers")
async def create_ledger(data: LedgerCreate, user: Dict = Depends(get_current_user)):
    company = await db.companies.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not company:
        raise HTTPException(status_code=400, detail="No company set up")
    ledger = Ledger(**data.model_dump(), user_id=user["user_id"], company_id=company["id"])
    doc = ledger.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.ledgers.insert_one(doc)
    return {"id": ledger.id, "name": ledger.name, "message": "Ledger created"}


@router.put("/ledgers/{ledger_id}")
async def update_ledger(ledger_id: str, data: LedgerCreate, user: Dict = Depends(get_current_user)):
    result = await db.ledgers.update_one(
        {"id": ledger_id, "user_id": user["user_id"]},
        {"$set": data.model_dump()}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Ledger not found")
    return {"message": "Ledger updated"}


@router.delete("/ledgers/{ledger_id}")
async def delete_ledger(ledger_id: str, user: Dict = Depends(get_current_user)):
    has_vouchers = await db.vouchers.find_one({"user_id": user["user_id"], "entries.ledger_id": ledger_id})
    if has_vouchers:
        raise HTTPException(status_code=400, detail="Cannot delete ledger with existing voucher entries")
    result = await db.ledgers.delete_one({"id": ledger_id, "user_id": user["user_id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Ledger not found")
    return {"message": "Ledger deleted"}


# ─── Vouchers ────────────────────────────────────────────────────────
@router.get("/vouchers")
async def get_vouchers(
    voucher_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user: Dict = Depends(get_current_user)
):
    query = {"user_id": user["user_id"]}
    if voucher_type:
        query["voucher_type"] = voucher_type
    if start_date:
        query["date"] = query.get("date", {})
        query["date"]["$gte"] = start_date
    if end_date:
        query.setdefault("date", {})
        query["date"]["$lte"] = end_date
    vouchers = await db.vouchers.find(query, {"_id": 0}).sort("date", -1).to_list(1000)
    return vouchers


@router.post("/vouchers")
async def create_voucher(data: VoucherCreate, user: Dict = Depends(get_current_user)):
    uid = user["user_id"]
    company = await db.companies.find_one({"user_id": uid}, {"_id": 0})
    if not company:
        raise HTTPException(status_code=400, detail="No company set up")

    total_debit = sum(e.debit for e in data.entries)
    total_credit = sum(e.credit for e in data.entries)
    if abs(total_debit - total_credit) > 0.01:
        raise HTTPException(status_code=400, detail=f"Voucher not balanced: Dr {total_debit} != Cr {total_credit}")

    count = await db.vouchers.count_documents({"user_id": uid, "voucher_type": data.voucher_type})
    type_prefix = {"payment": "PMT", "receipt": "RCT", "journal": "JRN", "contra": "CNT",
                   "sales": "SAL", "purchase": "PUR", "credit_note": "CN", "debit_note": "DN"}
    prefix = type_prefix.get(data.voucher_type, "VCH")
    voucher_number = f"{prefix}-{count + 1:04d}"

    entries_dicts = [e.model_dump() for e in data.entries]
    voucher = Voucher(
        user_id=uid, company_id=company["id"],
        voucher_number=voucher_number, voucher_type=data.voucher_type,
        date=data.date, narration=data.narration, reference=data.reference,
        entries=entries_dicts
    )
    doc = voucher.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.vouchers.insert_one(doc)

    await voucher_to_transaction(uid, voucher)

    return {"id": voucher.id, "voucher_number": voucher_number, "message": "Voucher created"}


@router.delete("/vouchers/{voucher_id}")
async def delete_voucher(voucher_id: str, user: Dict = Depends(get_current_user)):
    voucher = await db.vouchers.find_one({"id": voucher_id, "user_id": user["user_id"]}, {"_id": 0})
    if not voucher:
        raise HTTPException(status_code=404, detail="Voucher not found")
    await db.vouchers.delete_one({"id": voucher_id, "user_id": user["user_id"]})
    if voucher.get("linked_transaction_id"):
        await db.transactions.delete_one({"id": voucher["linked_transaction_id"], "user_id": user["user_id"]})
    return {"message": "Voucher deleted"}


# ─── Trial Balance ───────────────────────────────────────────────────
@router.get("/trial-balance")
async def get_trial_balance(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user: Dict = Depends(get_current_user)
):
    uid = user["user_id"]
    await init_default_company_and_coa(uid)

    ledgers = await db.ledgers.find({"user_id": uid}, {"_id": 0}).to_list(500)
    groups = await db.account_groups.find({"user_id": uid}, {"_id": 0}).to_list(200)
    group_map = {g["id"]: g for g in groups}

    vquery = {"user_id": uid, "is_posted": True}
    if start_date or end_date:
        vquery["date"] = {}
        if start_date:
            vquery["date"]["$gte"] = start_date
        if end_date:
            vquery["date"]["$lte"] = end_date
    vouchers = await db.vouchers.find(vquery, {"_id": 0}).to_list(10000)

    ledger_totals = defaultdict(lambda: {"debit": 0.0, "credit": 0.0})
    for v in vouchers:
        for entry in v.get("entries", []):
            lid = entry.get("ledger_id")
            ledger_totals[lid]["debit"] += entry.get("debit", 0)
            ledger_totals[lid]["credit"] += entry.get("credit", 0)

    rows = []
    total_dr = 0.0
    total_cr = 0.0
    for ledger in ledgers:
        lid = ledger["id"]
        totals = ledger_totals.get(lid, {"debit": 0, "credit": 0})
        opening = ledger.get("opening_balance", 0)
        if ledger.get("opening_type") == "dr":
            totals["debit"] += opening
        else:
            totals["credit"] += opening

        net = totals["debit"] - totals["credit"]
        closing_dr = net if net > 0 else 0
        closing_cr = abs(net) if net < 0 else 0

        if closing_dr > 0.01 or closing_cr > 0.01:
            group = group_map.get(ledger.get("group_id"), {})
            rows.append({
                "ledger_id": lid,
                "ledger_name": ledger["name"],
                "group_name": group.get("name", ""),
                "nature": group.get("nature", ""),
                "debit": round(closing_dr, 2),
                "credit": round(closing_cr, 2),
            })
            total_dr += closing_dr
            total_cr += closing_cr

    rows.sort(key=lambda r: (r["nature"], r["group_name"], r["ledger_name"]))

    return {
        "rows": rows,
        "total_debit": round(total_dr, 2),
        "total_credit": round(total_cr, 2),
        "is_balanced": abs(total_dr - total_cr) < 0.01
    }


# ─── Daybook ─────────────────────────────────────────────────────────
@router.get("/daybook")
async def get_daybook(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user: Dict = Depends(get_current_user)
):
    uid = user["user_id"]
    query = {"user_id": uid}
    if start_date or end_date:
        query["date"] = {}
        if start_date:
            query["date"]["$gte"] = start_date
        if end_date:
            query["date"]["$lte"] = end_date
    vouchers = await db.vouchers.find(query, {"_id": 0}).sort("date", -1).to_list(500)

    ledger_ids = set()
    for v in vouchers:
        for e in v.get("entries", []):
            ledger_ids.add(e.get("ledger_id"))
    ledgers = await db.ledgers.find({"user_id": uid, "id": {"$in": list(ledger_ids)}}, {"_id": 0}).to_list(500)
    ledger_map = {l["id"]: l["name"] for l in ledgers}

    for v in vouchers:
        for e in v.get("entries", []):
            e["ledger_name"] = ledger_map.get(e.get("ledger_id"), "Unknown")

    return vouchers


# ─── Profit & Loss ───────────────────────────────────────────────────
@router.get("/profit-loss")
async def get_profit_loss(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user: Dict = Depends(get_current_user)
):
    uid = user["user_id"]
    await init_default_company_and_coa(uid)

    ledgers = await db.ledgers.find({"user_id": uid}, {"_id": 0}).to_list(500)
    groups = await db.account_groups.find({"user_id": uid}, {"_id": 0}).to_list(200)
    group_map = {g["id"]: g for g in groups}

    vquery = {"user_id": uid, "is_posted": True}
    if start_date or end_date:
        vquery["date"] = {}
        if start_date:
            vquery["date"]["$gte"] = start_date
        if end_date:
            vquery["date"]["$lte"] = end_date
    vouchers = await db.vouchers.find(vquery, {"_id": 0}).to_list(10000)

    ledger_totals = defaultdict(lambda: {"debit": 0.0, "credit": 0.0})
    for v in vouchers:
        for entry in v.get("entries", []):
            lid = entry.get("ledger_id")
            ledger_totals[lid]["debit"] += entry.get("debit", 0)
            ledger_totals[lid]["credit"] += entry.get("credit", 0)

    income_items = []
    expense_items = []
    total_income = 0.0
    total_expense = 0.0

    for ledger in ledgers:
        lid = ledger["id"]
        group = group_map.get(ledger.get("group_id"), {})
        nature = group.get("nature", "")
        totals = ledger_totals.get(lid, {"debit": 0, "credit": 0})
        net = totals["credit"] - totals["debit"]

        if nature == "income" and abs(net) > 0.01:
            income_items.append({"ledger_name": ledger["name"], "group_name": group.get("name", ""), "amount": round(net, 2)})
            total_income += net
        elif nature == "expense" and abs(totals["debit"] - totals["credit"]) > 0.01:
            net_exp = totals["debit"] - totals["credit"]
            expense_items.append({"ledger_name": ledger["name"], "group_name": group.get("name", ""), "amount": round(net_exp, 2)})
            total_expense += net_exp

    return {
        "income": income_items,
        "expenses": expense_items,
        "total_income": round(total_income, 2),
        "total_expenses": round(total_expense, 2),
        "net_profit": round(total_income - total_expense, 2)
    }


# ─── Balance Sheet ────────────────────────────────────────────────────
@router.get("/balance-sheet")
async def get_balance_sheet(
    as_of_date: Optional[str] = None,
    user: Dict = Depends(get_current_user)
):
    uid = user["user_id"]
    await init_default_company_and_coa(uid)

    ledgers = await db.ledgers.find({"user_id": uid}, {"_id": 0}).to_list(500)
    groups = await db.account_groups.find({"user_id": uid}, {"_id": 0}).to_list(200)
    group_map = {g["id"]: g for g in groups}

    vquery = {"user_id": uid, "is_posted": True}
    if as_of_date:
        vquery["date"] = {"$lte": as_of_date}
    vouchers = await db.vouchers.find(vquery, {"_id": 0}).to_list(10000)

    ledger_totals = defaultdict(lambda: {"debit": 0.0, "credit": 0.0})
    for v in vouchers:
        for entry in v.get("entries", []):
            lid = entry.get("ledger_id")
            ledger_totals[lid]["debit"] += entry.get("debit", 0)
            ledger_totals[lid]["credit"] += entry.get("credit", 0)

    assets = []
    liabilities = []
    total_assets = 0.0
    total_liabilities = 0.0

    for ledger in ledgers:
        lid = ledger["id"]
        group = group_map.get(ledger.get("group_id"), {})
        nature = group.get("nature", "")
        totals = ledger_totals.get(lid, {"debit": 0, "credit": 0})
        opening = ledger.get("opening_balance", 0)
        if ledger.get("opening_type") == "dr":
            totals["debit"] += opening
        else:
            totals["credit"] += opening
        net = totals["debit"] - totals["credit"]

        if nature == "asset" and abs(net) > 0.01:
            assets.append({"ledger_name": ledger["name"], "group_name": group.get("name", ""), "amount": round(net, 2)})
            total_assets += net
        elif nature == "liability" and abs(net) > 0.01:
            liabilities.append({"ledger_name": ledger["name"], "group_name": group.get("name", ""), "amount": round(abs(net), 2)})
            total_liabilities += abs(net)

    income_total = 0.0
    expense_total = 0.0
    for ledger in ledgers:
        lid = ledger["id"]
        group = group_map.get(ledger.get("group_id"), {})
        nature = group.get("nature", "")
        totals = ledger_totals.get(lid, {"debit": 0, "credit": 0})
        if nature == "income":
            income_total += totals["credit"] - totals["debit"]
        elif nature == "expense":
            expense_total += totals["debit"] - totals["credit"]
    net_profit = income_total - expense_total
    if abs(net_profit) > 0.01:
        liabilities.append({"ledger_name": "Net Profit (Current Year)", "group_name": "Capital Account", "amount": round(net_profit, 2)})
        total_liabilities += net_profit

    return {
        "assets": assets,
        "liabilities": liabilities,
        "total_assets": round(total_assets, 2),
        "total_liabilities": round(total_liabilities, 2),
        "is_balanced": abs(total_assets - total_liabilities) < 0.01
    }


# ─── Ledger Statement ────────────────────────────────────────────────
@router.get("/ledger-statement/{ledger_id}")
async def get_ledger_statement(
    ledger_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user: Dict = Depends(get_current_user)
):
    uid = user["user_id"]
    ledger = await db.ledgers.find_one({"id": ledger_id, "user_id": uid}, {"_id": 0})
    if not ledger:
        raise HTTPException(status_code=404, detail="Ledger not found")

    vquery = {"user_id": uid, "entries.ledger_id": ledger_id, "is_posted": True}
    if start_date or end_date:
        vquery["date"] = {}
        if start_date:
            vquery["date"]["$gte"] = start_date
        if end_date:
            vquery["date"]["$lte"] = end_date
    vouchers = await db.vouchers.find(vquery, {"_id": 0}).sort("date", 1).to_list(5000)

    entries = []
    running = ledger.get("opening_balance", 0) * (1 if ledger.get("opening_type") == "dr" else -1)

    for v in vouchers:
        for e in v.get("entries", []):
            if e.get("ledger_id") == ledger_id:
                dr = e.get("debit", 0)
                cr = e.get("credit", 0)
                running += dr - cr
                entries.append({
                    "date": v["date"],
                    "voucher_number": v["voucher_number"],
                    "voucher_type": v["voucher_type"],
                    "narration": v.get("narration", ""),
                    "debit": dr,
                    "credit": cr,
                    "balance": round(running, 2)
                })

    return {
        "ledger_name": ledger["name"],
        "opening_balance": ledger.get("opening_balance", 0),
        "opening_type": ledger.get("opening_type", "dr"),
        "entries": entries,
        "closing_balance": round(running, 2)
    }


# ─── Migrate transactions to vouchers ────────────────────────────────
@router.post("/migrate-to-accounting")
async def migrate_transactions_to_vouchers(user: Dict = Depends(get_current_user)):
    uid = user["user_id"]
    await init_default_company_and_coa(uid)

    all_txns = await db.transactions.find({"user_id": uid}, {"_id": 0}).to_list(10000)
    linked_txn_ids = set()
    existing_vouchers = await db.vouchers.find({"user_id": uid, "linked_transaction_id": {"$ne": None}}, {"_id": 0, "linked_transaction_id": 1}).to_list(10000)
    for v in existing_vouchers:
        if v.get("linked_transaction_id"):
            linked_txn_ids.add(v["linked_transaction_id"])

    unlinked = [t for t in all_txns if t["id"] not in linked_txn_ids and not t.get("is_transfer")]
    migrated = 0

    for txn_data in unlinked:
        account = await db.accounts.find_one({"id": txn_data["account_id"], "user_id": uid}, {"_id": 0})
        if not account:
            continue
        category = None
        if txn_data.get("category_id"):
            category = await db.categories.find_one({"id": txn_data["category_id"], "user_id": uid}, {"_id": 0})

        txn_obj = Transaction(**{k: txn_data[k] for k in ["user_id", "account_id", "date", "description", "amount", "transaction_type"] if k in txn_data})
        txn_obj.id = txn_data["id"]
        txn_obj.category_id = txn_data.get("category_id")
        await transaction_to_voucher(uid, txn_obj, account, category)
        migrated += 1

    return {"message": f"Migrated {migrated} transactions to accounting vouchers", "migrated": migrated}
