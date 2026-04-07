from fastapi import APIRouter, Depends
from typing import Dict, Optional
from collections import defaultdict
from database import db
from auth import get_current_user

router = APIRouter(prefix="/api")


@router.get("/analytics/summary")
async def get_analytics_summary(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user: Dict = Depends(get_current_user)
):
    uid = user["user_id"]
    query = {"user_id": uid}
    if start_date and end_date:
        query["date"] = {"$gte": start_date, "$lte": end_date}

    transactions = await db.transactions.find(query, {"_id": 0}).to_list(10000)
    categories = await db.categories.find({"user_id": uid}, {"_id": 0}).to_list(1000)
    accounts = await db.accounts.find({"user_id": uid}, {"_id": 0}).to_list(1000)

    total_income = sum(t['amount'] for t in transactions if t['transaction_type'] == 'credit' and not t.get('is_transfer', False))
    total_expense = sum(t['amount'] for t in transactions if t['transaction_type'] == 'debit' and not t.get('is_transfer', False))

    category_map = {c['id']: c for c in categories}
    category_spending = defaultdict(float)

    for txn in transactions:
        if txn.get('category_id') and not txn.get('is_transfer', False):
            category_spending[txn['category_id']] += txn['amount']

    category_breakdown = [
        {
            "category": category_map[cat_id]['name'],
            "name": category_map[cat_id]['name'],
            "amount": amount,
            "color": category_map[cat_id].get('color', '#5C745A'),
            "type": category_map[cat_id]['category_type']
        }
        for cat_id, amount in category_spending.items()
        if cat_id in category_map
    ]

    uncategorized_debit = sum(t['amount'] for t in transactions if t['transaction_type'] == 'debit' and not t.get('is_transfer') and not t.get('category_id'))
    uncategorized_credit = sum(t['amount'] for t in transactions if t['transaction_type'] == 'credit' and not t.get('is_transfer') and not t.get('category_id'))

    if uncategorized_debit > 0:
        existing_other = next((c for c in category_breakdown if c['category'] == 'Other' and c['type'] == 'expense'), None)
        if existing_other:
            existing_other['amount'] += uncategorized_debit
        else:
            category_breakdown.append({"category": "Other", "name": "Other", "amount": uncategorized_debit, "color": "#9E9E9E", "type": "expense"})
    if uncategorized_credit > 0:
        existing_other_inc = next((c for c in category_breakdown if c['category'] == 'Other Income' and c['type'] == 'income'), None)
        if existing_other_inc:
            existing_other_inc['amount'] += uncategorized_credit
        else:
            category_breakdown.append({"category": "Other Income", "name": "Other Income", "amount": uncategorized_credit, "color": "#8BC34A", "type": "income"})

    monthly_data = defaultdict(lambda: {"income": 0, "expense": 0})
    for txn in transactions:
        if not txn.get('is_transfer', False):
            month_key = txn['date'][:7]
            if txn['transaction_type'] == 'credit':
                monthly_data[month_key]['income'] += txn['amount']
            else:
                monthly_data[month_key]['expense'] += txn['amount']

    monthly_trend = [
        {"month": month, "income": data['income'], "expense": data['expense']}
        for month, data in sorted(monthly_data.items())
    ]

    daily_data = defaultdict(lambda: {"income": 0, "expense": 0})
    for txn in transactions:
        if not txn.get('is_transfer', False):
            day_key = txn['date']
            if txn['transaction_type'] == 'credit':
                daily_data[day_key]['income'] += txn['amount']
            else:
                daily_data[day_key]['expense'] += txn['amount']

    daily_trend = [
        {"day": day, "income": data['income'], "expense": data['expense']}
        for day, data in sorted(daily_data.items())
    ]

    account_map = {a['id']: a for a in accounts}
    account_period = defaultdict(lambda: {"credits": 0, "debits": 0})
    for txn in transactions:
        if not txn.get('is_transfer', False):
            aid = txn.get('account_id')
            if txn['transaction_type'] == 'credit':
                account_period[aid]['credits'] += txn['amount']
            else:
                account_period[aid]['debits'] += txn['amount']

    account_summary = [
        {
            "name": account_map[aid]['name'] if aid in account_map else 'Unknown',
            "balance": account_map[aid]['current_balance'] if aid in account_map else 0,
            "type": account_map[aid]['account_type'] if aid in account_map else 'other',
            "credits": data['credits'],
            "debits": data['debits']
        }
        for aid, data in account_period.items()
    ]

    creditor_totals = defaultdict(float)
    debitor_totals = defaultdict(float)
    for txn in transactions:
        if txn.get('is_transfer', False):
            continue
        desc = txn.get('description', '').strip()
        if not desc:
            continue
        if txn['transaction_type'] == 'credit':
            creditor_totals[desc] += txn['amount']
        else:
            debitor_totals[desc] += txn['amount']

    top_creditors = sorted([{"description": d, "amount": a} for d, a in creditor_totals.items()], key=lambda x: -x['amount'])[:10]
    top_debitors = sorted([{"description": d, "amount": a} for d, a in debitor_totals.items()], key=lambda x: -x['amount'])[:10]

    return {
        "total_income": total_income,
        "total_expense": total_expense,
        "net_savings": total_income - total_expense,
        "category_breakdown": category_breakdown,
        "monthly_trend": monthly_trend,
        "daily_trend": daily_trend,
        "account_summary": account_summary,
        "top_creditors": top_creditors,
        "top_debitors": top_debitors,
        "account_balances": [{"name": a['name'], "balance": a['current_balance'], "type": a['account_type']} for a in accounts]
    }
