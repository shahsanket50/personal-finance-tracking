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
    email_from_filter: Optional[str] = None  # Filter by sender email address
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AccountCreate(BaseModel):
    name: str
    account_type: str
    start_balance: float = 0.0
    pdf_password: Optional[str] = None
    custom_parser: Optional[Dict] = None
    email_filter: Optional[str] = None
    email_from_filter: Optional[str] = None  # Filter by sender email address

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

# Default categories — comprehensive Indian personal finance set
DEFAULT_CATEGORIES = [
    # ── Income (10) ──
    {"name": "Salary", "category_type": "income", "color": "#5C745A", "is_default": True},
    {"name": "Freelance / Consulting", "category_type": "income", "color": "#6B8E6B", "is_default": True},
    {"name": "Business Income", "category_type": "income", "color": "#5A8B8E", "is_default": True},
    {"name": "Investment Returns", "category_type": "income", "color": "#7CA1A6", "is_default": True},
    {"name": "Dividends", "category_type": "income", "color": "#5C745A", "is_default": True},
    {"name": "Interest Income", "category_type": "income", "color": "#6B8E6B", "is_default": True},
    {"name": "Rental Income", "category_type": "income", "color": "#5A8B8E", "is_default": True},
    {"name": "Cashback / Rewards", "category_type": "income", "color": "#D4A373", "is_default": True},
    {"name": "Gifts Received", "category_type": "income", "color": "#C07A84", "is_default": True},
    {"name": "Refunds", "category_type": "income", "color": "#7CA1A6", "is_default": True},
    # ── Expense — Food & Daily (5) ──
    {"name": "Groceries", "category_type": "expense", "color": "#C06B52", "is_default": True},
    {"name": "Dining Out / Restaurants", "category_type": "expense", "color": "#A35943", "is_default": True},
    {"name": "Food Delivery", "category_type": "expense", "color": "#C06B52", "is_default": True},
    {"name": "Coffee & Beverages", "category_type": "expense", "color": "#8B6E5A", "is_default": True},
    {"name": "Snacks & Quick Bites", "category_type": "expense", "color": "#D4A373", "is_default": True},
    # ── Expense — Housing & Utilities (5) ──
    {"name": "Rent", "category_type": "expense", "color": "#D4A373", "is_default": True},
    {"name": "Electricity", "category_type": "expense", "color": "#D4A373", "is_default": True},
    {"name": "Water & Gas", "category_type": "expense", "color": "#A67C5A", "is_default": True},
    {"name": "Internet & WiFi", "category_type": "expense", "color": "#7CA1A6", "is_default": True},
    {"name": "Mobile Recharge", "category_type": "expense", "color": "#7CA1A6", "is_default": True},
    # ── Expense — Transport (4) ──
    {"name": "Fuel / Petrol", "category_type": "expense", "color": "#D4A373", "is_default": True},
    {"name": "Cab / Auto / Uber", "category_type": "expense", "color": "#A67C5A", "is_default": True},
    {"name": "Public Transport", "category_type": "expense", "color": "#8B6E5A", "is_default": True},
    {"name": "Parking & Tolls", "category_type": "expense", "color": "#78716C", "is_default": True},
    # ── Expense — Shopping & Lifestyle (4) ──
    {"name": "Clothing & Apparel", "category_type": "expense", "color": "#C06B52", "is_default": True},
    {"name": "Electronics & Gadgets", "category_type": "expense", "color": "#7A6BC0", "is_default": True},
    {"name": "Home & Furniture", "category_type": "expense", "color": "#A67C5A", "is_default": True},
    {"name": "Personal Care & Grooming", "category_type": "expense", "color": "#C07A84", "is_default": True},
    # ── Expense — Health & Insurance (3) ──
    {"name": "Medical / Doctor", "category_type": "expense", "color": "#C06B52", "is_default": True},
    {"name": "Pharmacy / Medicine", "category_type": "expense", "color": "#A35943", "is_default": True},
    {"name": "Insurance Premium", "category_type": "expense", "color": "#7CA1A6", "is_default": True},
    # ── Expense — Education & Kids (2) ──
    {"name": "Education & Courses", "category_type": "expense", "color": "#5C745A", "is_default": True},
    {"name": "Books & Stationery", "category_type": "expense", "color": "#6B8E6B", "is_default": True},
    # ── Expense — Entertainment & Leisure (3) ──
    {"name": "Entertainment / Movies", "category_type": "expense", "color": "#7CA1A6", "is_default": True},
    {"name": "Subscriptions / OTT", "category_type": "expense", "color": "#5A8B8E", "is_default": True},
    {"name": "Travel & Holidays", "category_type": "expense", "color": "#D4A373", "is_default": True},
    # ── Expense — Financial (5) ──
    {"name": "EMI / Loan Repayment", "category_type": "expense", "color": "#C06B52", "is_default": True},
    {"name": "Credit Card Payment", "category_type": "expense", "color": "#A35943", "is_default": True},
    {"name": "Bank Charges / Fees", "category_type": "expense", "color": "#78716C", "is_default": True},
    {"name": "Investment / SIP", "category_type": "expense", "color": "#5C745A", "is_default": True},
    {"name": "Tax Payment", "category_type": "expense", "color": "#C06B52", "is_default": True},
    # ── Expense — Household & Services (3) ──
    {"name": "Domestic Help / Maid", "category_type": "expense", "color": "#A67C5A", "is_default": True},
    {"name": "Maintenance / Society", "category_type": "expense", "color": "#D4A373", "is_default": True},
    {"name": "Repairs & Services", "category_type": "expense", "color": "#8B6E5A", "is_default": True},
    # ── Expense — Social & Misc (4) ──
    {"name": "Gifts & Donations", "category_type": "expense", "color": "#C07A84", "is_default": True},
    {"name": "Charity / Temple", "category_type": "expense", "color": "#7A6BC0", "is_default": True},
    {"name": "Transfer", "category_type": "expense", "color": "#78716C", "is_default": True},
    {"name": "Other / Miscellaneous", "category_type": "expense", "color": "#A8A29E", "is_default": True},
]

# ═══════════════════════════════════════════════════════════════════════
# ACCOUNTING ENGINE — Double-entry bookkeeping (Tally-like)
# ═══════════════════════════════════════════════════════════════════════

class Company(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    name: str
    address: str = ""
    gstin: str = ""
    pan: str = ""
    cin: str = ""
    fy_start_month: int = 4  # April (Indian FY)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CompanyCreate(BaseModel):
    name: str
    address: str = ""
    gstin: str = ""
    pan: str = ""
    cin: str = ""
    fy_start_month: int = 4

class AccountGroup(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    company_id: str = ""
    name: str
    parent_id: Optional[str] = None
    nature: str  # asset, liability, income, expense
    is_default: bool = True
    sort_order: int = 0

class Ledger(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    company_id: str = ""
    name: str
    group_id: str
    opening_balance: float = 0.0
    opening_type: str = "dr"  # dr or cr
    address: str = ""
    gstin: str = ""
    linked_account_id: Optional[str] = None  # Bridge to Finance Tracker account
    linked_category_id: Optional[str] = None  # Bridge to Finance Tracker category
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class LedgerCreate(BaseModel):
    name: str
    group_id: str
    opening_balance: float = 0.0
    opening_type: str = "dr"
    address: str = ""
    gstin: str = ""

class VoucherEntry(BaseModel):
    ledger_id: str
    debit: float = 0.0
    credit: float = 0.0

class Voucher(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    company_id: str = ""
    voucher_number: str = ""
    voucher_type: str  # payment, receipt, journal, contra, sales, purchase, credit_note, debit_note
    date: str
    narration: str = ""
    reference: str = ""
    entries: List[Dict] = []
    linked_transaction_id: Optional[str] = None  # Bridge to Finance Tracker
    is_posted: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class VoucherCreate(BaseModel):
    voucher_type: str
    date: str
    narration: str = ""
    reference: str = ""
    entries: List[VoucherEntry]

# Indian Standard Chart of Accounts (Tally-compatible)
DEFAULT_ACCOUNT_GROUPS = [
    # Primary groups
    {"name": "Capital Account", "parent": None, "nature": "liability", "sort": 1},
    {"name": "Loans (Liability)", "parent": None, "nature": "liability", "sort": 2},
    {"name": "Current Liabilities", "parent": None, "nature": "liability", "sort": 3},
    {"name": "Fixed Assets", "parent": None, "nature": "asset", "sort": 4},
    {"name": "Investments", "parent": None, "nature": "asset", "sort": 5},
    {"name": "Current Assets", "parent": None, "nature": "asset", "sort": 6},
    {"name": "Direct Income", "parent": None, "nature": "income", "sort": 7},
    {"name": "Indirect Income", "parent": None, "nature": "income", "sort": 8},
    {"name": "Direct Expenses", "parent": None, "nature": "expense", "sort": 9},
    {"name": "Indirect Expenses", "parent": None, "nature": "expense", "sort": 10},
    # Sub-groups under Current Assets
    {"name": "Bank Accounts", "parent": "Current Assets", "nature": "asset", "sort": 1},
    {"name": "Cash-in-Hand", "parent": "Current Assets", "nature": "asset", "sort": 2},
    {"name": "Sundry Debtors", "parent": "Current Assets", "nature": "asset", "sort": 3},
    {"name": "Deposits (Asset)", "parent": "Current Assets", "nature": "asset", "sort": 4},
    {"name": "Stock-in-Hand", "parent": "Current Assets", "nature": "asset", "sort": 5},
    {"name": "Loans & Advances (Asset)", "parent": "Current Assets", "nature": "asset", "sort": 6},
    # Sub-groups under Current Liabilities
    {"name": "Sundry Creditors", "parent": "Current Liabilities", "nature": "liability", "sort": 1},
    {"name": "Duties & Taxes", "parent": "Current Liabilities", "nature": "liability", "sort": 2},
    {"name": "Provisions", "parent": "Current Liabilities", "nature": "liability", "sort": 3},
    # Sub-groups under Loans (Liability)
    {"name": "Bank OD A/c", "parent": "Loans (Liability)", "nature": "liability", "sort": 1},
    {"name": "Secured Loans", "parent": "Loans (Liability)", "nature": "liability", "sort": 2},
    {"name": "Unsecured Loans", "parent": "Loans (Liability)", "nature": "liability", "sort": 3},
    # Sub-groups under Direct/Indirect
    {"name": "Sales Account", "parent": "Direct Income", "nature": "income", "sort": 1},
    {"name": "Purchase Account", "parent": "Direct Expenses", "nature": "expense", "sort": 1},
]

async def _init_default_company_and_coa(user_id: str):
    """Initialize a default company and Chart of Accounts for a user"""
    existing = await db.companies.find_one({"user_id": user_id}, {"_id": 0})
    if existing:
        return existing["id"]
    
    company = Company(user_id=user_id, name="My Business")
    doc = company.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.companies.insert_one(doc)
    company_id = company.id
    
    # Create account groups
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
    
    # Create default ledgers
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
    uid = user["user_id"]
    result = await db.accounts.delete_one({"id": account_id, "user_id": uid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Account not found")
    txn_result = await db.transactions.delete_many({"account_id": account_id, "user_id": uid})
    await db.sync_history.delete_many({"account_id": account_id, "user_id": uid})
    await db.processed_emails.delete_many({"account_id": account_id, "user_id": uid})
    return {"message": f"Account deleted along with {txn_result.deleted_count} transactions"}

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
    # Auto-restore defaults if no categories exist
    if len(categories) == 0:
        await _init_default_categories(user["user_id"])
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

@api_router.post("/categories/restore-defaults")
async def restore_default_categories(user: Dict = Depends(get_current_user)):
    """Re-create all missing default categories"""
    uid = user["user_id"]
    restored = 0
    for cat_data in DEFAULT_CATEGORIES:
        existing = await db.categories.find_one({"name": cat_data["name"], "is_default": True, "user_id": uid})
        if not existing:
            cat = Category(**cat_data, user_id=uid)
            doc = cat.model_dump()
            doc['created_at'] = doc['created_at'].isoformat()
            await db.categories.insert_one(doc)
            restored += 1
    # Clean up orphaned category references in transactions
    valid_cat_ids = set()
    async for c in db.categories.find({"user_id": uid}, {"id": 1, "_id": 0}):
        valid_cat_ids.add(c["id"])
    orphaned = await db.transactions.update_many(
        {"user_id": uid, "category_id": {"$ne": None, "$nin": list(valid_cat_ids)}},
        {"$set": {"category_id": None}}
    )
    return {"message": f"Restored {restored} default categories, cleared {orphaned.modified_count} orphaned references", "restored": restored, "orphaned_cleared": orphaned.modified_count}

@api_router.post("/categories/fix-orphaned")
async def fix_orphaned_categories(user: Dict = Depends(get_current_user)):
    """Clear category_id from transactions that reference deleted categories"""
    uid = user["user_id"]
    valid_cat_ids = set()
    async for c in db.categories.find({"user_id": uid}, {"id": 1, "_id": 0}):
        valid_cat_ids.add(c["id"])
    result = await db.transactions.update_many(
        {"user_id": uid, "category_id": {"$ne": None, "$nin": list(valid_cat_ids)}},
        {"$set": {"category_id": None}}
    )
    return {"message": f"Cleared {result.modified_count} orphaned category references", "cleared": result.modified_count}

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
        # Auto-bridge: create accounting voucher
        category = None
        if txn.category_id:
            category = await db.categories.find_one({"id": txn.category_id, "user_id": user["user_id"]}, {"_id": 0})
        try:
            await _transaction_to_voucher(user["user_id"], txn, account, category)
        except Exception:
            pass

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
    # Auto-bridge: delete linked voucher
    linked_voucher = await db.vouchers.find_one({"user_id": user["user_id"], "linked_transaction_id": transaction_id})
    if linked_voucher:
        await db.vouchers.delete_one({"id": linked_voucher["id"], "user_id": user["user_id"]})
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

    def date_close(d1, d2):
        """Check if dates are within 1 day of each other"""
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

    # Sort by confidence: exact date match first, then ±1 day
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
                "txn1": txn1,
                "txn2": best_match,
                "amount": txn1['amount'],
                "date": txn1['date'],
                "confidence": confidence
            })
            processed_ids.add(txn1['id'])
            processed_ids.add(best_match['id'])
    
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
            "name": category_map[cat_id]['name'],
            "amount": amount,
            "color": category_map[cat_id].get('color', '#5C745A'),
            "type": category_map[cat_id]['category_type']
        }
        for cat_id, amount in category_spending.items()
        if cat_id in category_map
    ]
    
    # Uncategorized spending — merge into existing "Other" if present
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

    # Daily trend (useful for single-month view)
    daily_data = defaultdict(lambda: {"income": 0, "expense": 0})
    for txn in transactions:
        if not txn.get('is_transfer', False):
            day_key = txn['date']  # YYYY-MM-DD
            if txn['transaction_type'] == 'credit':
                daily_data[day_key]['income'] += txn['amount']
            else:
                daily_data[day_key]['expense'] += txn['amount']

    daily_trend = [
        {"day": day, "income": data['income'], "expense": data['expense']}
        for day, data in sorted(daily_data.items())
    ]
    
    # Per-account credit/debit for selected period
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

    # Top creditors and debitors (by description, excluding transfers)
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
            # Auto-bridge: create accounting voucher
            try:
                await _transaction_to_voucher(uid, txn, account, None)
            except Exception:
                pass
            imported_count += 1
        
        # Auto-categorize newly imported transactions
        categorized_count = 0
        if imported_count > 0:
            try:
                cats = await db.categories.find({"user_id": uid}, {"_id": 0}).to_list(200)
                if len(cats) == 0:
                    await _init_default_categories(uid)
                    cats = await db.categories.find({"user_id": uid}, {"_id": 0}).to_list(200)
                uncat = await db.transactions.find(
                    {"user_id": uid, "account_id": account_id, "category_id": None, "is_transfer": False},
                    {"_id": 0}
                ).to_list(500)
                if uncat:
                    categorized_count = await _ai_categorize_batch(uid, uncat, cats)
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
                    # Auto-bridge: create accounting voucher
                    try:
                        await _transaction_to_voucher(uid, txn, account, None)
                    except Exception:
                        pass
                imported_count += 1
        
        # Auto-categorize newly imported transactions
        categorized_count = 0
        if imported_count > 0:
            try:
                cats = await db.categories.find({"user_id": uid}, {"_id": 0}).to_list(200)
                if len(cats) == 0:
                    await _init_default_categories(uid)
                    cats = await db.categories.find({"user_id": uid}, {"_id": 0}).to_list(200)
                uncat = await db.transactions.find(
                    {"user_id": uid, "account_id": account_id, "category_id": None, "is_transfer": False},
                    {"_id": 0}
                ).to_list(500)
                if uncat:
                    categorized_count = await _ai_categorize_batch(uid, uncat, cats)
            except Exception as e:
                logger.warning(f"Auto-categorization after CSV import failed: {e}")

        return {"message": f"Imported {imported_count} transactions" + (f", auto-categorized {categorized_count}" if categorized_count > 0 else "")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error importing CSV: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════
# ACCOUNTING API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════

# ─── Company ──────────────────────────────────────────────────────────
@api_router.get("/company")
async def get_company(user: Dict = Depends(get_current_user)):
    company_id = await _init_default_company_and_coa(user["user_id"])
    company = await db.companies.find_one({"id": company_id, "user_id": user["user_id"]}, {"_id": 0})
    return company

@api_router.put("/company")
async def update_company(data: CompanyCreate, user: Dict = Depends(get_current_user)):
    company = await db.companies.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    await db.companies.update_one(
        {"id": company["id"], "user_id": user["user_id"]},
        {"$set": data.model_dump()}
    )
    return {"message": "Company updated"}

@api_router.get("/financial-years")
async def get_financial_years(user: Dict = Depends(get_current_user)):
    """Get list of financial years that have voucher data"""
    uid = user["user_id"]
    company = await db.companies.find_one({"user_id": uid}, {"_id": 0})
    if not company:
        return {"years": [], "current_fy": None}
    fy_start = company.get("fy_start_month", 4)
    
    # Find min and max voucher dates
    pipeline = [
        {"$match": {"user_id": uid}},
        {"$group": {"_id": None, "min_date": {"$min": "$date"}, "max_date": {"$max": "$date"}}}
    ]
    result = await db.vouchers.aggregate(pipeline).to_list(1)
    
    # Also check transaction dates
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
        # No data, return current FY
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
        last_day = 28 if last_month == 2 else 31 if last_month in [1,3,5,7,8,10,12] else 30
        end_year = y + 1 if fy_start > 1 else y
        years.append({
            "label": f"FY {y}-{str(y+1)[-2:]}",

# ─── Account Groups (Chart of Accounts) ──────────────────────────────
            "start": f"{y}-{fy_start:02d}-01",
            "end": f"{end_year}-{last_month:02d}-{last_day:02d}"
        })
    
    return {
        "years": years,
        "current_fy": f"FY {current_fy_year}-{str(current_fy_year+1)[-2:]}"
    }
@api_router.get("/account-groups")
async def get_account_groups(user: Dict = Depends(get_current_user)):
    await _init_default_company_and_coa(user["user_id"])
    groups = await db.account_groups.find({"user_id": user["user_id"]}, {"_id": 0}).to_list(200)
    return groups

@api_router.post("/account-groups")
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
@api_router.get("/ledgers")
async def get_ledgers(user: Dict = Depends(get_current_user)):
    await _init_default_company_and_coa(user["user_id"])
    ledgers = await db.ledgers.find({"user_id": user["user_id"]}, {"_id": 0}).to_list(500)
    return ledgers

@api_router.post("/ledgers")
async def create_ledger(data: LedgerCreate, user: Dict = Depends(get_current_user)):
    company = await db.companies.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not company:
        raise HTTPException(status_code=400, detail="No company set up")
    ledger = Ledger(**data.model_dump(), user_id=user["user_id"], company_id=company["id"])
    doc = ledger.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.ledgers.insert_one(doc)
    return {"id": ledger.id, "name": ledger.name, "message": "Ledger created"}

@api_router.put("/ledgers/{ledger_id}")
async def update_ledger(ledger_id: str, data: LedgerCreate, user: Dict = Depends(get_current_user)):
    result = await db.ledgers.update_one(
        {"id": ledger_id, "user_id": user["user_id"]},
        {"$set": data.model_dump()}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Ledger not found")
    return {"message": "Ledger updated"}

@api_router.delete("/ledgers/{ledger_id}")
async def delete_ledger(ledger_id: str, user: Dict = Depends(get_current_user)):
    # Check if any vouchers reference this ledger
    has_vouchers = await db.vouchers.find_one({"user_id": user["user_id"], "entries.ledger_id": ledger_id})
    if has_vouchers:
        raise HTTPException(status_code=400, detail="Cannot delete ledger with existing voucher entries")
    result = await db.ledgers.delete_one({"id": ledger_id, "user_id": user["user_id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Ledger not found")
    return {"message": "Ledger deleted"}

# ─── Vouchers ────────────────────────────────────────────────────────
@api_router.get("/vouchers")
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

@api_router.post("/vouchers")
async def create_voucher(data: VoucherCreate, user: Dict = Depends(get_current_user)):
    uid = user["user_id"]
    company = await db.companies.find_one({"user_id": uid}, {"_id": 0})
    if not company:
        raise HTTPException(status_code=400, detail="No company set up")
    
    # Validate debit == credit
    total_debit = sum(e.debit for e in data.entries)
    total_credit = sum(e.credit for e in data.entries)
    if abs(total_debit - total_credit) > 0.01:
        raise HTTPException(status_code=400, detail=f"Voucher not balanced: Dr {total_debit} != Cr {total_credit}")
    
    # Auto voucher number
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
    
    # Auto-bridge: create Finance Tracker transaction if voucher involves a bank/cash ledger
    await _voucher_to_transaction(uid, voucher)
    
    return {"id": voucher.id, "voucher_number": voucher_number, "message": "Voucher created"}

@api_router.delete("/vouchers/{voucher_id}")
async def delete_voucher(voucher_id: str, user: Dict = Depends(get_current_user)):
    voucher = await db.vouchers.find_one({"id": voucher_id, "user_id": user["user_id"]}, {"_id": 0})
    if not voucher:
        raise HTTPException(status_code=404, detail="Voucher not found")
    await db.vouchers.delete_one({"id": voucher_id, "user_id": user["user_id"]})
    # Also remove linked transaction if any
    if voucher.get("linked_transaction_id"):
        await db.transactions.delete_one({"id": voucher["linked_transaction_id"], "user_id": user["user_id"]})
    return {"message": "Voucher deleted"}

# ─── Trial Balance ───────────────────────────────────────────────────
@api_router.get("/trial-balance")
async def get_trial_balance(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user: Dict = Depends(get_current_user)
):
    uid = user["user_id"]
    await _init_default_company_and_coa(uid)
    
    # Get all ledgers
    ledgers = await db.ledgers.find({"user_id": uid}, {"_id": 0}).to_list(500)
    groups = await db.account_groups.find({"user_id": uid}, {"_id": 0}).to_list(200)
    group_map = {g["id"]: g for g in groups}
    
    # Get all vouchers in date range
    vquery = {"user_id": uid, "is_posted": True}
    if start_date or end_date:
        vquery["date"] = {}
        if start_date:
            vquery["date"]["$gte"] = start_date
        if end_date:
            vquery["date"]["$lte"] = end_date
    vouchers = await db.vouchers.find(vquery, {"_id": 0}).to_list(10000)
    
    # Compute balances per ledger
    ledger_totals = defaultdict(lambda: {"debit": 0.0, "credit": 0.0})
    for v in vouchers:
        for entry in v.get("entries", []):
            lid = entry.get("ledger_id")
            ledger_totals[lid]["debit"] += entry.get("debit", 0)
            ledger_totals[lid]["credit"] += entry.get("credit", 0)
    
    # Build trial balance rows
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
@api_router.get("/daybook")
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
    
    # Enrich with ledger names
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

# ─── Profit & Loss Statement ─────────────────────────────────────────
@api_router.get("/profit-loss")
async def get_profit_loss(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user: Dict = Depends(get_current_user)
):
    uid = user["user_id"]
    await _init_default_company_and_coa(uid)
    
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
@api_router.get("/balance-sheet")
async def get_balance_sheet(
    as_of_date: Optional[str] = None,
    user: Dict = Depends(get_current_user)
):
    uid = user["user_id"]
    await _init_default_company_and_coa(uid)
    
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
    
    # Add net profit/loss to liabilities side (retained earnings)
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

# ─── Bridge: Auto-sync between Finance Tracker <-> Accounting ────────
async def _voucher_to_transaction(uid, voucher):
    """When a voucher is created in Accounting view, auto-create Finance Tracker transaction if applicable"""
    entries = voucher.entries if isinstance(voucher.entries, list) else []
    if len(entries) != 2:
        return  # Only bridge simple 2-leg vouchers
    
    # Find which ledger is a bank/cash account (linked to Finance Tracker account)
    for i, entry in enumerate(entries):
        ledger = await db.ledgers.find_one({"id": entry.get("ledger_id", entry.get("ledger_id")), "user_id": uid}, {"_id": 0})
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
            # Try to find linked category from the other ledger
            other_ledger = await db.ledgers.find_one({"id": other.get("ledger_id"), "user_id": uid}, {"_id": 0})
            if other_ledger and other_ledger.get("linked_category_id"):
                txn.category_id = other_ledger["linked_category_id"]
            doc = txn.model_dump()
            doc['created_at'] = doc['created_at'].isoformat()
            await db.transactions.insert_one(doc)
            # Update account balance
            bal_change = -amount if txn_type == "debit" else amount
            await db.accounts.update_one({"id": ledger["linked_account_id"], "user_id": uid}, {"$inc": {"current_balance": bal_change}})
            # Link voucher to transaction
            await db.vouchers.update_one({"id": voucher.id}, {"$set": {"linked_transaction_id": txn.id}})
            return

async def _transaction_to_voucher(uid, txn, account, category=None):
    """When a transaction is created in Finance Tracker, auto-create a voucher in Accounting"""
    company = await db.companies.find_one({"user_id": uid}, {"_id": 0})
    if not company:
        return
    
    # Find or create ledger for the account
    account_ledger = await db.ledgers.find_one({"linked_account_id": account["id"], "user_id": uid}, {"_id": 0})
    if not account_ledger:
        # Auto-create a ledger for this bank/cash account
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
    
    # Find or create ledger for the category
    category_ledger = None
    if category:
        category_ledger = await db.ledgers.find_one({"linked_category_id": category["id"], "user_id": uid}, {"_id": 0})
        if not category_ledger:
            # Map category type to group
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
        # Use a generic "Suspense" or "Miscellaneous" ledger
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

    # Build voucher entries (double-entry)
    acc_lid = account_ledger["id"]
    cat_lid = category_ledger["id"]
    
    if txn.transaction_type == "debit":
        # Money going out: Debit expense, Credit bank
        entries = [
            {"ledger_id": cat_lid, "debit": txn.amount, "credit": 0},
            {"ledger_id": acc_lid, "debit": 0, "credit": txn.amount}
        ]
        voucher_type = "payment"
    else:
        # Money coming in: Debit bank, Credit income
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

# ─── Migrate existing transactions to vouchers ───────────────────────
@api_router.post("/migrate-to-accounting")
async def migrate_transactions_to_vouchers(user: Dict = Depends(get_current_user)):
    uid = user["user_id"]
    await _init_default_company_and_coa(uid)
    
    # Get all transactions that don't have a linked voucher
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
        
        # Create a Transaction-like object for the bridge function
        txn_obj = Transaction(**{k: txn_data[k] for k in ["user_id", "account_id", "date", "description", "amount", "transaction_type"] if k in txn_data})
        txn_obj.id = txn_data["id"]
        txn_obj.category_id = txn_data.get("category_id")
        await _transaction_to_voucher(uid, txn_obj, account, category)
        migrated += 1
    
    return {"message": f"Migrated {migrated} transactions to accounting vouchers", "migrated": migrated}

# ─── Ledger Statement ────────────────────────────────────────────────
@api_router.get("/ledger-statement/{ledger_id}")
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


# ─── AI Categorization Endpoint ───────────────────────────────────────
# ─── Shared AI Categorization Helper ──────────────────────────────────
async def _ai_categorize_batch(uid: str, txns: list, categories: list) -> int:
    """Categorize a batch of transactions using AI. Returns count categorized."""
    if not txns or not categories:
        return 0

    category_names = [c['name'] for c in categories if c['name'] != 'Transfer']
    category_map = {c['name'].lower().strip(): c['id'] for c in categories}

    income_cats = ', '.join([c['name'] for c in categories if c['category_type'] == 'income'])
    expense_cats = ', '.join([c['name'] for c in categories if c['category_type'] == 'expense' and c['name'] != 'Transfer'])

    descriptions = [{"id": t["id"], "desc": t["description"], "amount": t["amount"], "type": t["transaction_type"]} for t in txns[:100]]

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

    from emergentintegrations.llm.chat import LlmChat, UserMessage
    import json as json_mod

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

    categorized_count = 0
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
                categorized_count += 1

    return categorized_count

@api_router.post("/ai-categorize")
async def ai_categorize_transactions(
    transaction_ids: List[str] = [],
    user: Dict = Depends(get_current_user)
):
    """Use AI to auto-categorize uncategorized transactions"""
    uid = user["user_id"]

    categories = await db.categories.find({"user_id": uid}, {"_id": 0}).to_list(200)
    if len(categories) == 0:
        await _init_default_categories(uid)
        categories = await db.categories.find({"user_id": uid}, {"_id": 0}).to_list(200)

    query = {"user_id": uid, "category_id": None, "is_transfer": False}
    if transaction_ids:
        query["id"] = {"$in": transaction_ids}

    txns = await db.transactions.find(query, {"_id": 0}).to_list(500)
    if not txns:
        return {"message": "No uncategorized transactions found", "categorized_count": 0}

    try:
        categorized_count = await _ai_categorize_batch(uid, txns, categories)
        return {
            "message": f"Categorized {categorized_count} of {len(txns)} transactions",
            "categorized_count": categorized_count,
            "total_uncategorized": len(txns),
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

# ─── Backup Import/Restore ──────────────────────────────────────────
@api_router.post("/backup/import")
async def import_backup(request: Request, user: Dict = Depends(get_current_user)):
    """Restore user data from a JSON backup"""
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

# ─── Data Cleanup ────────────────────────────────────────────────────
@api_router.post("/reset-all-data")
async def reset_all_data(user: Dict = Depends(get_current_user)):
    """Delete ALL user data (accounts, transactions, categories, sync history). Keeps email config and user."""
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


# ─── Email Config & Scanner ──────────────────────────────────────────
class EmailConfigModel(BaseModel):
    imap_server: str = "imap.gmail.com"
    email_address: str
    app_password: str
    sync_since: Optional[str] = None  # ISO date string like "2024-01-01"

@api_router.post("/email-config")
async def save_email_config(config: EmailConfigModel, user: Dict = Depends(get_current_user)):
    """Save IMAP email configuration for auto-scanning"""
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

@api_router.get("/email-config")
async def get_email_config(user: Dict = Depends(get_current_user)):
    """Get saved email configuration"""
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

@api_router.post("/email-scan")
async def scan_email_for_statements(user: Dict = Depends(get_current_user)):
    """Scan email inbox for bank statement PDFs and auto-import"""
    import imaplib
    import email as email_lib
    from email.header import decode_header
    import hashlib

    uid = user["user_id"]

    email_config = await db.email_configs.find_one({"user_id": uid}, {"_id": 0})
    if not email_config or not email_config.get("app_password"):
        raise HTTPException(status_code=400, detail="Email not configured. Go to Settings to set up email scanning.")

    # Parse sync_since for post-fetch filtering
    sync_since_date = None
    if email_config.get("sync_since"):
        try:
            from datetime import datetime as dt
            sync_since_date = dt.strptime(email_config["sync_since"], "%Y-%m-%d")
        except Exception:
            pass

    accounts = await db.accounts.find({"user_id": uid}, {"_id": 0}).to_list(100)
    accounts_with_filters = [a for a in accounts if a.get("email_filter")]
    if not accounts_with_filters:
        raise HTTPException(status_code=400, detail="No accounts have email filters configured. Edit an account and add an email filter keyword.")

    try:
        mail = imaplib.IMAP4_SSL(email_config["imap_server"])
        mail.login(email_config["email_address"], email_config["app_password"])
        # Try [Gmail]/All Mail first (searches all labels/folders), fallback to INBOX
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

            # Search WITHOUT SINCE — Gmail IMAP SINCE is unreliable with compound queries
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

                # Post-fetch date filtering
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
                        skip = _is_subject_before_date(subj_str, sync_since_date)
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
                                user_id=uid,
                                account_id=account_id,
                                date=txn_data["date"],
                                description=txn_data["description"],
                                amount=txn_data["amount"],
                                transaction_type=txn_data["type"]
                            )
                            doc = txn.model_dump()
                            doc["created_at"] = doc["created_at"].isoformat()
                            await db.transactions.insert_one(doc)
                            # Auto-bridge: create accounting voucher
                            try:
                                account_obj = await db.accounts.find_one({"id": account_id, "user_id": uid}, {"_id": 0})
                                if account_obj:
                                    await _transaction_to_voucher(uid, txn, account_obj, None)
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

    # Auto-categorize all newly imported uncategorized transactions
    categorized_count = 0
    if total_imported > 0:
        try:
            categories = await db.categories.find({"user_id": uid}, {"_id": 0}).to_list(200)
            if len(categories) == 0:
                await _init_default_categories(uid)
                categories = await db.categories.find({"user_id": uid}, {"_id": 0}).to_list(200)
            uncategorized = await db.transactions.find(
                {"user_id": uid, "category_id": None, "is_transfer": False},
                {"_id": 0}
            ).to_list(500)
            if uncategorized:
                categorized_count = await _ai_categorize_batch(uid, uncategorized, categories)
        except Exception as e:
            logger.warning(f"Auto-categorization after email-scan failed: {e}")

    return {
        "message": f"Scan complete. Imported {total_imported} transactions, skipped {total_skipped} already-processed emails." + (f" Auto-categorized {categorized_count}." if categorized_count > 0 else ""),
        "total_imported": total_imported,
        "total_skipped": total_skipped,
        "categorized_count": categorized_count,
        "details": results
    }

# ─── Statement Date Extraction from Subject ──────────────────────────
def _is_subject_before_date(subject: str, cutoff_date) -> bool:
    """Check if an email subject contains a statement period that's before the cutoff date.
    Matches patterns like: 'Oct-2022', 'Mar 2025', 'October 2022', '03-2024', '2023-04'
    """
    import re
    from datetime import datetime as dt

    MONTH_MAP = {
        'jan': 1, 'january': 1, 'feb': 2, 'february': 2, 'mar': 3, 'march': 3,
        'apr': 4, 'april': 4, 'may': 5, 'jun': 6, 'june': 6,
        'jul': 7, 'july': 7, 'aug': 8, 'august': 8, 'sep': 9, 'september': 9,
        'oct': 10, 'october': 10, 'nov': 11, 'november': 11, 'dec': 12, 'december': 12,
    }
    subject_lower = subject.lower()

    # Pattern 1: "Oct-2022", "Mar 2025", "October-2024", "Sep 2023"
    match = re.search(r'(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)[- /]?(20\d{2})', subject_lower)
    if match:
        month = MONTH_MAP.get(match.group(1))
        year = int(match.group(2))
        if month and year:
            try:
                statement_date = dt(year, month, 1)
                if statement_date < cutoff_date:
                    return True
            except Exception:
                pass

    # Pattern 2: "2022-10", "2024-03" (ISO-ish)
    match = re.search(r'(20\d{2})[- /](0[1-9]|1[0-2])', subject_lower)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        try:
            statement_date = dt(year, month, 1)
            if statement_date < cutoff_date:
                return True
        except Exception:
            pass

    # Pattern 3: "03-2024", "12/2023"
    match = re.search(r'(0[1-9]|1[0-2])[- /](20\d{2})', subject_lower)
    if match:
        month = int(match.group(1))
        year = int(match.group(2))
        try:
            statement_date = dt(year, month, 1)
            if statement_date < cutoff_date:
                return True
        except Exception:
            pass

    return False

# ─── Shared IMAP Helper ──────────────────────────────────────────────
async def _imap_connect_and_search(email_config, account):
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

    # Parse sync_since date for post-fetch filtering (NOT in IMAP query — Gmail ignores SINCE with compound queries)
    sync_since_date = None
    if email_config.get("sync_since"):
        try:
            from datetime import datetime as dt
            sync_since_date = dt.strptime(email_config["sync_since"], "%Y-%m-%d")
        except Exception:
            pass

    filter_text = account["email_filter"]
    from_filter = account.get("email_from_filter", "")
    from_criteria = f' FROM "{from_filter}"' if from_filter else ''

    # Search WITHOUT SINCE — Gmail IMAP doesn't reliably combine SINCE with SUBJECT+FROM
    # We'll filter by date after fetching email headers instead
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


# ─── Account Email Sync Preview ──────────────────────────────────────
@api_router.post("/accounts/{account_id}/sync-preview")
async def sync_account_preview(account_id: str, user: Dict = Depends(get_current_user)):
    """Preview what would be synced — shows matching emails and PDF details without importing"""
    import email as email_lib
    from email.header import decode_header
    import hashlib

    uid = user["user_id"]
    account = await db.accounts.find_one({"id": account_id, "user_id": uid}, {"_id": 0})
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if not account.get("email_filter"):
        raise HTTPException(status_code=400, detail="No email filter configured for this account.")

    email_config = await db.email_configs.find_one({"user_id": uid}, {"_id": 0})
    if not email_config or not email_config.get("app_password"):
        raise HTTPException(status_code=400, detail="Email not configured in Settings.")

    mail, message_ids, sync_since_date, error = await _imap_connect_and_search(email_config, account)
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

            # Decode subject
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

            # Post-fetch date filtering (since Gmail IMAP SINCE is unreliable)
            if sync_since_date:
                skip = False
                # 1) Check email received date
                try:
                    from email.utils import parsedate_to_datetime
                    email_dt = parsedate_to_datetime(email_date)
                    if email_dt.replace(tzinfo=None) < sync_since_date:
                        skip = True
                except Exception:
                    pass
                # 2) Also check statement period from subject (e.g. "Statement for Oct-2022", "Mar-2025")
                if not skip:
                    skip = _is_subject_before_date(subject, sync_since_date)
                if skip:
                    skipped_by_date += 1
                    continue

            # Check if already processed
            already_processed = await db.processed_emails.find_one({"email_hash": email_hash, "user_id": uid})

            # Find PDF attachments
            pdfs = []
            for part in email_message.walk():
                if part.get_content_type() == "application/pdf":
                    filename = part.get_filename() or "statement.pdf"
                    pdf_data = part.get_payload(decode=True)
                    size_kb = round(len(pdf_data) / 1024, 1) if pdf_data else 0

                    # Try to parse for transaction count (dry run)
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

    # Summary
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


# ─── Account-level Email Sync ────────────────────────────────────────
@api_router.post("/accounts/{account_id}/sync")
async def sync_account_email(account_id: str, user: Dict = Depends(get_current_user)):
    """Sync email statements for a specific account"""
    import imaplib
    import email as email_lib
    import hashlib

    uid = user["user_id"]
    account = await db.accounts.find_one({"id": account_id, "user_id": uid}, {"_id": 0})
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    if not account.get("email_filter"):
        raise HTTPException(status_code=400, detail="No email filter configured for this account. Edit the account to add one.")

    email_config = await db.email_configs.find_one({"user_id": uid}, {"_id": 0})
    if not email_config or not email_config.get("app_password"):
        raise HTTPException(status_code=400, detail="Email not configured. Go to Settings to set up email scanning.")

    mail, message_ids, sync_since_date, error = await _imap_connect_and_search(email_config, account)
    if error:
        await _log_sync(uid, account_id, account["name"], "failed", 0, 0, error)
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

            # Post-fetch date filtering (Gmail IMAP SINCE is unreliable with compound queries)
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
                    skip = _is_subject_before_date(subj_text, sync_since_date)
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
                        # Auto-bridge: create accounting voucher
                        try:
                            account_obj = await db.accounts.find_one({"id": account_id, "user_id": uid}, {"_id": 0})
                            if account_obj:
                                await _transaction_to_voucher(uid, txn, account_obj, None)
                        except Exception:
                            pass
                        imported_count += 1

                    total_imported += imported_count

                    # Determine per-file status
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

            # Only mark as processed if parsing succeeded
            # Failed PDFs (wrong password / parse error) should be retryable
            if email_had_success:
                await db.processed_emails.insert_one({
                    "email_hash": email_hash, "user_id": uid,
                    "account_id": account_id, "message_id": message_id,
                    "processed_at": datetime.now(timezone.utc).isoformat()
                })
    finally:
        mail.logout()

    # Build informative message
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

    await _log_sync(uid, account_id, account["name"], status, total_imported, total_skipped, None, files_found, filter_text, emails_matched)

    # Auto-categorize newly imported transactions
    categorized_count = 0
    if total_imported > 0:
        try:
            categories = await db.categories.find({"user_id": uid}, {"_id": 0}).to_list(200)
            if len(categories) == 0:
                await _init_default_categories(uid)
                categories = await db.categories.find({"user_id": uid}, {"_id": 0}).to_list(200)
            uncategorized = await db.transactions.find(
                {"user_id": uid, "account_id": account_id, "category_id": None, "is_transfer": False},
                {"_id": 0}
            ).to_list(500)
            if uncategorized:
                categorized_count = await _ai_categorize_batch(uid, uncategorized, categories)
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

async def _log_sync(user_id, account_id, account_name, status, imported, skipped, error=None, files=None, filter_used=None, emails_matched=0):
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

@api_router.get("/accounts/{account_id}/sync-history")
async def get_sync_history(account_id: str, user: Dict = Depends(get_current_user)):
    """Get sync history for an account"""
    uid = user["user_id"]
    history = await db.sync_history.find(
        {"user_id": uid, "account_id": account_id}, {"_id": 0}
    ).sort("synced_at", -1).to_list(20)
    return history

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
