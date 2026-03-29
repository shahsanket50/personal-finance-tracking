from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException, Query, Request, Depends
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import pdfplumber
import io
import re
import httpx
from collections import defaultdict
from pdf_parsers_simple import get_simple_parser

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# ─── Auth Models ──────────────────────────────────────────────────────
class User(BaseModel):
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserSession(BaseModel):
    user_id: str
    session_token: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ─── Auth Helper ──────────────────────────────────────────────────────
async def get_current_user(request: Request) -> Dict:
    """Extract and validate session from cookie or Authorization header"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            session_token = auth_header[7:]

    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session_doc = await db.user_sessions.find_one(
        {"session_token": session_token}, {"_id": 0}
    )
    if not session_doc:
        raise HTTPException(status_code=401, detail="Invalid session")

    expires_at = session_doc["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")

    user_doc = await db.users.find_one(
        {"user_id": session_doc["user_id"]}, {"_id": 0}
    )
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")

    return user_doc


# ─── Auth Endpoints ───────────────────────────────────────────────────
EMERGENT_AUTH_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"

@api_router.post("/auth/session")
async def exchange_session(request: Request):
    """Exchange session_id from Emergent Auth for a session_token"""
    body = await request.json()
    session_id = body.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")

    async with httpx.AsyncClient() as hc:
        resp = await hc.get(
            EMERGENT_AUTH_URL,
            headers={"X-Session-ID": session_id}
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid session_id")
        auth_data = resp.json()

    email = auth_data["email"]
    name = auth_data.get("name", "")
    picture = auth_data.get("picture", "")
    session_token = auth_data["session_token"]

    # Upsert user
    existing_user = await db.users.find_one({"email": email}, {"_id": 0})
    if existing_user:
        user_id = existing_user["user_id"]
        await db.users.update_one(
            {"email": email},
            {"$set": {"name": name, "picture": picture}}
        )
    else:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        user_doc = {
            "user_id": user_id,
            "email": email,
            "name": name,
            "picture": picture,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.users.insert_one(user_doc)
        # Initialize default categories for new user
        await _init_default_categories(user_id)

    # Store session
    session_doc = {
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.user_sessions.insert_one(session_doc)

    response = JSONResponse(content={
        "user_id": user_id,
        "email": email,
        "name": name,
        "picture": picture
    })
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=7 * 24 * 3600
    )
    return response

@api_router.get("/auth/me")
async def get_me(user: Dict = Depends(get_current_user)):
    """Get current authenticated user"""
    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "name": user["name"],
        "picture": user.get("picture", "")
    }

@api_router.post("/auth/logout")
async def logout(request: Request):
    session_token = request.cookies.get("session_token")
    if session_token:
        await db.user_sessions.delete_one({"session_token": session_token})
    response = JSONResponse(content={"message": "Logged out"})
    response.delete_cookie(key="session_token", path="/", samesite="none", secure=True)
    return response

# OAuth callback - redirect from Google Auth back to frontend
@app.get("/auth/callback")
async def auth_callback(request: Request):
    session_id = request.query_params.get("session_id", "")
    from starlette.responses import RedirectResponse
    frontend_url = "https://money-insights-82.preview.emergentagent.com"
    return RedirectResponse(url=f"{frontend_url}/auth/callback?session_id={session_id}")

# Models
class Account(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    name: str
    account_type: str  # credit_card, bank, investment, cash
    start_balance: float = 0.0
    current_balance: float = 0.0
    pdf_password: Optional[str] = None
    custom_parser: Optional[Dict] = None
    email_filter: Optional[str] = None  # Filter text for email auto-detection
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AccountCreate(BaseModel):
    name: str
    account_type: str
    start_balance: float = 0.0
    pdf_password: Optional[str] = None
    custom_parser: Optional[Dict] = None
    email_filter: Optional[str] = None

class Category(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    name: str
    category_type: str  # income, expense
    color: str = "#5C745A"
    is_default: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CategoryCreate(BaseModel):
    name: str
    category_type: str
    color: str = "#5C745A"

class Transaction(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    account_id: str
    date: str
    description: str
    amount: float
    transaction_type: str  # credit, debit
    category_id: Optional[str] = None
    is_transfer: bool = False
    transfer_pair_id: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TransactionCreate(BaseModel):
    account_id: str
    date: str
    description: str
    amount: float
    transaction_type: str
    category_id: Optional[str] = None
    notes: Optional[str] = None

class TransferCreate(BaseModel):
    from_account_id: str
    to_account_id: str
    amount: float
    date: str
    description: str = "Transfer"

# Default categories
DEFAULT_CATEGORIES = [
    {"name": "Salary", "category_type": "income", "color": "#5C745A", "is_default": True},
    {"name": "Investment Returns", "category_type": "income", "color": "#5C745A", "is_default": True},
    {"name": "Food & Dining", "category_type": "expense", "color": "#C06B52", "is_default": True},
    {"name": "Shopping", "category_type": "expense", "color": "#C06B52", "is_default": True},
    {"name": "Transportation", "category_type": "expense", "color": "#D4A373", "is_default": True},
    {"name": "Bills & Utilities", "category_type": "expense", "color": "#D4A373", "is_default": True},
    {"name": "Entertainment", "category_type": "expense", "color": "#7CA1A6", "is_default": True},
    {"name": "Healthcare", "category_type": "expense", "color": "#D4A373", "is_default": True},
    {"name": "Transfer", "category_type": "expense", "color": "#78716C", "is_default": True},
    {"name": "Other", "category_type": "expense", "color": "#A8A29E", "is_default": True},
]

# Helper to init default categories for a user
async def _init_default_categories(user_id: str):
    for cat_data in DEFAULT_CATEGORIES:
        existing = await db.categories.find_one({"name": cat_data["name"], "is_default": True, "user_id": user_id})
        if not existing:
            cat = Category(**cat_data, user_id=user_id)
            doc = cat.model_dump()
            doc['created_at'] = doc['created_at'].isoformat()
            await db.categories.insert_one(doc)

# Initialize default categories (called automatically on first login)
@api_router.post("/init")
async def initialize_defaults(user: Dict = Depends(get_current_user)):
    await _init_default_categories(user["user_id"])
    return {"message": "Defaults initialized"}

# Account endpoints
@api_router.post("/accounts", response_model=Account)
async def create_account(account: AccountCreate, user: Dict = Depends(get_current_user)):
    acc = Account(**account.model_dump(), user_id=user["user_id"], current_balance=account.start_balance)
    doc = acc.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.accounts.insert_one(doc)
    return acc

@api_router.get("/accounts", response_model=List[Account])
async def get_accounts(user: Dict = Depends(get_current_user)):
    accounts = await db.accounts.find({"user_id": user["user_id"]}, {"_id": 0}).to_list(1000)
    for acc in accounts:
        if isinstance(acc.get('created_at'), str):
            acc['created_at'] = datetime.fromisoformat(acc['created_at'])
    return accounts

@api_router.put("/accounts/{account_id}", response_model=Account)
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

@api_router.delete("/accounts/{account_id}")
async def delete_account(account_id: str, user: Dict = Depends(get_current_user)):
    result = await db.accounts.delete_one({"id": account_id, "user_id": user["user_id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Account not found")
    await db.transactions.delete_many({"account_id": account_id, "user_id": user["user_id"]})
    return {"message": "Account deleted"}

# Category endpoints
@api_router.post("/categories", response_model=Category)
async def create_category(category: CategoryCreate, user: Dict = Depends(get_current_user)):
    cat = Category(**category.model_dump(), user_id=user["user_id"])
    doc = cat.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.categories.insert_one(doc)
    return cat

@api_router.get("/categories", response_model=List[Category])
async def get_categories(user: Dict = Depends(get_current_user)):
    categories = await db.categories.find({"user_id": user["user_id"]}, {"_id": 0}).to_list(1000)
    for cat in categories:
        if isinstance(cat.get('created_at'), str):
            cat['created_at'] = datetime.fromisoformat(cat['created_at'])
    return categories

@api_router.put("/categories/{category_id}", response_model=Category)
async def update_category(category_id: str, category: CategoryCreate, user: Dict = Depends(get_current_user)):
    update_data = category.model_dump()
    result = await db.categories.find_one_and_update(
        {"id": category_id, "user_id": user["user_id"]},
        {"$set": update_data},
        return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Category not found")
    if '_id' in result:
        del result['_id']
    if isinstance(result.get('created_at'), str):
        result['created_at'] = datetime.fromisoformat(result['created_at'])
    return Category(**result)

@api_router.delete("/categories/{category_id}")
async def delete_category(category_id: str, user: Dict = Depends(get_current_user)):
    cat = await db.categories.find_one({"id": category_id, "user_id": user["user_id"]})
    if cat and cat.get('is_default'):
        raise HTTPException(status_code=400, detail="Cannot delete default category")
    result = await db.categories.delete_one({"id": category_id, "user_id": user["user_id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"message": "Category deleted"}

# Transaction endpoints
@api_router.post("/transactions", response_model=Transaction)
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

    return txn

@api_router.get("/transactions", response_model=List[Transaction])
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

@api_router.put("/transactions/{transaction_id}", response_model=Transaction)
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

@api_router.delete("/transactions/{transaction_id}")
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
    return {"message": "Transaction deleted"}

# Transfer endpoints
@api_router.post("/transfers")
async def create_transfer(transfer: TransferCreate, user: Dict = Depends(get_current_user)):
    transfer_id = str(uuid.uuid4())
    uid = user["user_id"]

    transfer_cat = await db.categories.find_one({"name": "Transfer", "user_id": uid})
    transfer_cat_id = transfer_cat['id'] if transfer_cat else None

    debit_txn = Transaction(
        user_id=uid,
        account_id=transfer.from_account_id,
        date=transfer.date,
        description=f"{transfer.description} (to account)",
        amount=transfer.amount,
        transaction_type="debit",
        category_id=transfer_cat_id,
        is_transfer=True,
        transfer_pair_id=transfer_id
    )
    credit_txn = Transaction(
        user_id=uid,
        account_id=transfer.to_account_id,
        date=transfer.date,
        description=f"{transfer.description} (from account)",
        amount=transfer.amount,
        transaction_type="credit",
        category_id=transfer_cat_id,
        is_transfer=True,
        transfer_pair_id=transfer_id
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

# Auto-detect transfers
@api_router.post("/detect-transfers")
async def detect_transfers(user: Dict = Depends(get_current_user)):
    all_txns = await db.transactions.find(
        {"is_transfer": False, "user_id": user["user_id"]}, {"_id": 0}
    ).to_list(10000)
    
    matched_pairs = []
    processed_ids = set()
    
    # Group by date and amount
    for i, txn1 in enumerate(all_txns):
        if txn1['id'] in processed_ids:
            continue
            
        for txn2 in all_txns[i+1:]:
            if txn2['id'] in processed_ids:
                continue
                
            # Check if amounts match and types are opposite
            if (abs(txn1['amount'] - txn2['amount']) < 0.01 and
                txn1['transaction_type'] != txn2['transaction_type'] and
                txn1['date'] == txn2['date'] and
                txn1['account_id'] != txn2['account_id']):
                
                matched_pairs.append({
                    "txn1": txn1,
                    "txn2": txn2,
                    "amount": txn1['amount'],
                    "date": txn1['date']
                })
                processed_ids.add(txn1['id'])
                processed_ids.add(txn2['id'])
                break
    
    return {"potential_transfers": matched_pairs, "count": len(matched_pairs)}

# Mark transactions as transfer
@api_router.post("/mark-as-transfer")
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

# Analytics endpoints
@api_router.get("/analytics/summary")
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
    
    # Calculate totals
    total_income = sum(t['amount'] for t in transactions if t['transaction_type'] == 'credit' and not t.get('is_transfer', False))
    total_expense = sum(t['amount'] for t in transactions if t['transaction_type'] == 'debit' and not t.get('is_transfer', False))
    
    # Category breakdown
    category_map = {c['id']: c for c in categories}
    category_spending = defaultdict(float)
    
    for txn in transactions:
        if txn.get('category_id') and not txn.get('is_transfer', False):
            category_spending[txn['category_id']] += txn['amount']
    
    category_breakdown = [
        {
            "category": category_map[cat_id]['name'],
            "amount": amount,
            "color": category_map[cat_id].get('color', '#5C745A'),
            "type": category_map[cat_id]['category_type']
        }
        for cat_id, amount in category_spending.items()
        if cat_id in category_map
    ]
    
    # Monthly trend
    monthly_data = defaultdict(lambda: {"income": 0, "expense": 0})
    for txn in transactions:
        if not txn.get('is_transfer', False):
            month_key = txn['date'][:7]  # YYYY-MM
            if txn['transaction_type'] == 'credit':
                monthly_data[month_key]['income'] += txn['amount']
            else:
                monthly_data[month_key]['expense'] += txn['amount']
    
    monthly_trend = [
        {"month": month, "income": data['income'], "expense": data['expense']}
        for month, data in sorted(monthly_data.items())
    ]
    
    # Account balances
    account_balances = [
        {
            "name": acc['name'],
            "balance": acc['current_balance'],
            "type": acc['account_type']
        }
        for acc in accounts
    ]
    
    return {
        "total_income": total_income,
        "total_expense": total_expense,
        "net_savings": total_income - total_expense,
        "category_breakdown": category_breakdown,
        "monthly_trend": monthly_trend,
        "account_balances": account_balances
    }

# PDF Upload endpoint
@api_router.post("/upload-statement")
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
                user_id=uid,
                account_id=account_id,
                date=txn_data['date'],
                description=txn_data['description'],
                amount=txn_data['amount'],
                transaction_type=txn_data['type']
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
            imported_count += 1
        
        return {
            "message": f"Successfully imported {imported_count} transactions",
            "imported_count": imported_count,
            "total_found": len(parsed_transactions),
            "duplicates_skipped": len(parsed_transactions) - imported_count
        }
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

# Parser Builder endpoints
@api_router.post("/build-parser")
async def build_parser(
    file: UploadFile = File(...),
    account_id: str = Query(...),
    password: str = Query(default=""),
    user: Dict = Depends(get_current_user)
):
    """Extract text from PDF and auto-detect the best parsing strategy"""
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

@api_router.post("/save-parser-pattern")
async def save_parser_pattern(
    account_id: str = Query(...),
    password: str = Query(default=""),
    strategy: str = Query(default=""),
    user: Dict = Depends(get_current_user)
):
    """Save the detected parser strategy and password for an account"""
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

@api_router.post("/test-parser-pattern")
async def test_parser_pattern(
    file: UploadFile = File(...),
    account_id: str = Query(...),
    pattern: str = Query(...),
    password: str = Query(default=""),
    user: Dict = Depends(get_current_user)
):
    """Test a custom regex pattern"""
    try:
        contents = await file.read()
        account = await db.accounts.find_one({"id": account_id, "user_id": user["user_id"]})
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        import json
        test_pattern = json.loads(pattern)
        parser = get_simple_parser(account['name'], test_pattern)
        transactions = parser.parse(contents, password or None)
        
        return {
            "transactions_found": len(transactions),
            "transactions": transactions[:20]
        }
    except Exception as e:
        return {"error": str(e), "transactions_found": 0}

# Debug endpoint for PDF text extraction
@api_router.post("/debug-pdf")
async def debug_pdf_upload(
    file: UploadFile = File(...),
    password: str = Query(default="", description="PDF password if protected")
):
    """Debug endpoint to see extracted text and parsed transactions without importing"""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        contents = await file.read()
        
        # Get parser
        parser = get_simple_parser("Debug Account")
        
        # Extract text
        extracted_text = parser.extract_text(contents, password or None)
        
        # Parse transactions
        parsed_transactions = parser.parse(contents, password or None)
        
        return {
            "filename": file.filename,
            "file_size": len(contents),
            "parser_used": parser.__class__.__name__,
            "text_length": len(extracted_text),
            "text_preview": extracted_text[:1000],
            "text_full": extracted_text,
            "transactions_found": len(parsed_transactions),
            "transactions": parsed_transactions[:10],  # First 10 only
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

# CSV Import endpoint
@api_router.post("/import-csv")
async def import_csv(
    file: UploadFile = File(...),
    account_id: str = Query(...),
    user: Dict = Depends(get_current_user)
):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")
    
    try:
        contents = await file.read()
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
                    user_id=uid,
                    account_id=account_id,
                    date=date.strip(),
                    description=description.strip(),
                    amount=float(amount.strip()),
                    transaction_type=txn_type.strip().lower()
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
                imported_count += 1
        
        return {"message": f"Imported {imported_count} transactions"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error importing CSV: {str(e)}")

# ─── AI Categorization Endpoint ───────────────────────────────────────
@api_router.post("/ai-categorize")
async def ai_categorize_transactions(
    transaction_ids: List[str] = [],
    user: Dict = Depends(get_current_user)
):
    """Use AI to auto-categorize uncategorized transactions"""
    uid = user["user_id"]

    query = {"user_id": uid, "category_id": None, "is_transfer": False}
    if transaction_ids:
        query["id"] = {"$in": transaction_ids}

    txns = await db.transactions.find(query, {"_id": 0}).to_list(500)
    if not txns:
        return {"message": "No uncategorized transactions found", "categorized_count": 0}

    categories = await db.categories.find({"user_id": uid}, {"_id": 0}).to_list(100)
    category_names = [c['name'] for c in categories if c['name'] != 'Transfer']
    category_map = {c['name'].lower(): c['id'] for c in categories}

    descriptions = [{"id": t["id"], "desc": t["description"], "amount": t["amount"], "type": t["transaction_type"]} for t in txns[:100]]

    prompt = f"""Categorize the following financial transactions into one of these categories: {', '.join(category_names)}.

Return ONLY a JSON array with objects having "id" and "category" fields. No explanation.

Transactions:
{[{"id": d["id"], "description": d["desc"], "amount": d["amount"], "type": d["type"]} for d in descriptions]}"""

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        import json as json_mod

        chat = LlmChat(
            api_key=os.environ.get("EMERGENT_LLM_KEY", ""),
            session_id=f"categorize_{uid}_{uuid.uuid4().hex[:8]}",
            system_message="You are a financial transaction categorizer. Return only valid JSON."
        )
        chat.with_model("gemini", "gemini-2.5-flash")

        response = await chat.send_message(UserMessage(text=prompt))

        json_text = response.strip()
        if "```json" in json_text:
            json_text = json_text.split("```json")[1].split("```")[0].strip()
        elif "```" in json_text:
            json_text = json_text.split("```")[1].split("```")[0].strip()

        categorizations = json_mod.loads(json_text)

        categorized_count = 0
        for item in categorizations:
            txn_id = item.get("id")
            cat_name = item.get("category", "").lower()
            cat_id = category_map.get(cat_name)
            if txn_id and cat_id:
                result = await db.transactions.update_one(
                    {"id": txn_id, "user_id": uid},
                    {"$set": {"category_id": cat_id}}
                )
                if result.modified_count > 0:
                    categorized_count += 1

        return {
            "message": f"Categorized {categorized_count} of {len(txns)} transactions",
            "categorized_count": categorized_count,
            "total_uncategorized": len(txns)
        }
    except Exception as e:
        logger.error(f"AI categorization error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI categorization failed: {str(e)}")

# ─── Backup Endpoint ────────────────────────────────────────────────
@api_router.get("/backup/export")
async def export_backup(user: Dict = Depends(get_current_user)):
    """Export all user data as JSON for local backup"""
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

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["https://money-insights-82.preview.emergentagent.com", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
