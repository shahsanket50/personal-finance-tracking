from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict
from datetime import datetime, timezone
import uuid


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


# ─── Finance Tracker Models ──────────────────────────────────────────
class Account(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    name: str
    account_type: str
    start_balance: float = 0.0
    current_balance: float = 0.0
    pdf_password: Optional[str] = None
    custom_parser: Optional[Dict] = None
    email_filter: Optional[str] = None
    email_from_filter: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AccountCreate(BaseModel):
    name: str
    account_type: str
    start_balance: float = 0.0
    pdf_password: Optional[str] = None
    custom_parser: Optional[Dict] = None
    email_filter: Optional[str] = None
    email_from_filter: Optional[str] = None


class Category(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    name: str
    category_type: str
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
    transaction_type: str
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


# ─── Accounting Models ────────────────────────────────────────────────
class Company(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    name: str
    address: str = ""
    gstin: str = ""
    pan: str = ""
    cin: str = ""
    fy_start_month: int = 4
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
    nature: str
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
    opening_type: str = "dr"
    address: str = ""
    gstin: str = ""
    linked_account_id: Optional[str] = None
    linked_category_id: Optional[str] = None
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
    voucher_type: str
    date: str
    narration: str = ""
    reference: str = ""
    entries: List[Dict] = []
    linked_transaction_id: Optional[str] = None
    is_posted: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class VoucherCreate(BaseModel):
    voucher_type: str
    date: str
    narration: str = ""
    reference: str = ""
    entries: List[VoucherEntry]


class EmailConfigModel(BaseModel):
    imap_server: str = "imap.gmail.com"
    email_address: str
    app_password: str
    sync_since: Optional[str] = None


# ─── Default Data ─────────────────────────────────────────────────────
DEFAULT_CATEGORIES = [
    # Income (10)
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
    # Expense — Food & Daily (5)
    {"name": "Groceries", "category_type": "expense", "color": "#C06B52", "is_default": True},
    {"name": "Dining Out / Restaurants", "category_type": "expense", "color": "#A35943", "is_default": True},
    {"name": "Food Delivery", "category_type": "expense", "color": "#C06B52", "is_default": True},
    {"name": "Coffee & Beverages", "category_type": "expense", "color": "#8B6E5A", "is_default": True},
    {"name": "Snacks & Quick Bites", "category_type": "expense", "color": "#D4A373", "is_default": True},
    # Expense — Housing & Utilities (5)
    {"name": "Rent", "category_type": "expense", "color": "#D4A373", "is_default": True},
    {"name": "Electricity", "category_type": "expense", "color": "#D4A373", "is_default": True},
    {"name": "Water & Gas", "category_type": "expense", "color": "#A67C5A", "is_default": True},
    {"name": "Internet & WiFi", "category_type": "expense", "color": "#7CA1A6", "is_default": True},
    {"name": "Mobile Recharge", "category_type": "expense", "color": "#7CA1A6", "is_default": True},
    # Expense — Transport (4)
    {"name": "Fuel / Petrol", "category_type": "expense", "color": "#D4A373", "is_default": True},
    {"name": "Cab / Auto / Uber", "category_type": "expense", "color": "#A67C5A", "is_default": True},
    {"name": "Public Transport", "category_type": "expense", "color": "#8B6E5A", "is_default": True},
    {"name": "Parking & Tolls", "category_type": "expense", "color": "#78716C", "is_default": True},
    # Expense — Shopping & Lifestyle (4)
    {"name": "Clothing & Apparel", "category_type": "expense", "color": "#C06B52", "is_default": True},
    {"name": "Electronics & Gadgets", "category_type": "expense", "color": "#7A6BC0", "is_default": True},
    {"name": "Home & Furniture", "category_type": "expense", "color": "#A67C5A", "is_default": True},
    {"name": "Personal Care & Grooming", "category_type": "expense", "color": "#C07A84", "is_default": True},
    # Expense — Health & Insurance (3)
    {"name": "Medical / Doctor", "category_type": "expense", "color": "#C06B52", "is_default": True},
    {"name": "Pharmacy / Medicine", "category_type": "expense", "color": "#A35943", "is_default": True},
    {"name": "Insurance Premium", "category_type": "expense", "color": "#7CA1A6", "is_default": True},
    # Expense — Education & Kids (2)
    {"name": "Education & Courses", "category_type": "expense", "color": "#5C745A", "is_default": True},
    {"name": "Books & Stationery", "category_type": "expense", "color": "#6B8E6B", "is_default": True},
    # Expense — Entertainment & Leisure (3)
    {"name": "Entertainment / Movies", "category_type": "expense", "color": "#7CA1A6", "is_default": True},
    {"name": "Subscriptions / OTT", "category_type": "expense", "color": "#5A8B8E", "is_default": True},
    {"name": "Travel & Holidays", "category_type": "expense", "color": "#D4A373", "is_default": True},
    # Expense — Financial (5)
    {"name": "EMI / Loan Repayment", "category_type": "expense", "color": "#C06B52", "is_default": True},
    {"name": "Credit Card Payment", "category_type": "expense", "color": "#A35943", "is_default": True},
    {"name": "Bank Charges / Fees", "category_type": "expense", "color": "#78716C", "is_default": True},
    {"name": "Investment / SIP", "category_type": "expense", "color": "#5C745A", "is_default": True},
    {"name": "Tax Payment", "category_type": "expense", "color": "#C06B52", "is_default": True},
    # Expense — Household & Services (3)
    {"name": "Domestic Help / Maid", "category_type": "expense", "color": "#A67C5A", "is_default": True},
    {"name": "Maintenance / Society", "category_type": "expense", "color": "#D4A373", "is_default": True},
    {"name": "Repairs & Services", "category_type": "expense", "color": "#8B6E5A", "is_default": True},
    # Expense — Social & Misc (4)
    {"name": "Gifts & Donations", "category_type": "expense", "color": "#C07A84", "is_default": True},
    {"name": "Charity / Temple", "category_type": "expense", "color": "#7A6BC0", "is_default": True},
    {"name": "Transfer", "category_type": "expense", "color": "#78716C", "is_default": True},
    {"name": "Other / Miscellaneous", "category_type": "expense", "color": "#A8A29E", "is_default": True},
]

DEFAULT_ACCOUNT_GROUPS = [
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
    {"name": "Bank Accounts", "parent": "Current Assets", "nature": "asset", "sort": 1},
    {"name": "Cash-in-Hand", "parent": "Current Assets", "nature": "asset", "sort": 2},
    {"name": "Sundry Debtors", "parent": "Current Assets", "nature": "asset", "sort": 3},
    {"name": "Deposits (Asset)", "parent": "Current Assets", "nature": "asset", "sort": 4},
    {"name": "Stock-in-Hand", "parent": "Current Assets", "nature": "asset", "sort": 5},
    {"name": "Loans & Advances (Asset)", "parent": "Current Assets", "nature": "asset", "sort": 6},
    {"name": "Sundry Creditors", "parent": "Current Liabilities", "nature": "liability", "sort": 1},
    {"name": "Duties & Taxes", "parent": "Current Liabilities", "nature": "liability", "sort": 2},
    {"name": "Provisions", "parent": "Current Liabilities", "nature": "liability", "sort": 3},
    {"name": "Bank OD A/c", "parent": "Loans (Liability)", "nature": "liability", "sort": 1},
    {"name": "Secured Loans", "parent": "Loans (Liability)", "nature": "liability", "sort": 2},
    {"name": "Unsecured Loans", "parent": "Loans (Liability)", "nature": "liability", "sort": 3},
    {"name": "Sales Account", "parent": "Direct Income", "nature": "income", "sort": 1},
    {"name": "Purchase Account", "parent": "Direct Expenses", "nature": "expense", "sort": 1},
]
