# MoneyInsights - Personal Finance & Accounting Platform

## Product Overview
A personal finance tracking application that analyzes day-to-day transactions across multiple accounts and cards via uploaded statements or email sync. Features a "Tally-like" accounting system alongside the personal finance tracker with a 2-view system (Finance Tracker View vs. Tally/Accounting View).

## Core Architecture
- **Frontend**: React 18, TailwindCSS, Shadcn UI, Phosphor Icons, Recharts
- **Backend**: Python FastAPI (modular routes), Motor (async MongoDB), pdfplumber, pikepdf
- **Database**: MongoDB
- **Auth**: Emergent-managed Google OAuth
- **AI**: Gemini 2.5 Flash via emergentintegrations
- **Mobile**: Capacitor 7 for Android APK

## Backend Structure (Refactored)
```
backend/
├── server.py              # 55 lines — App setup, middleware, router registration
├── database.py            # MongoDB client + db instance
├── models.py              # All Pydantic models + default data
├── auth.py                # get_current_user() session validator
├── bridge.py              # Auto-bridge: transaction ↔ voucher sync
├── helpers.py             # AI categorizer, default init, IMAP helpers
├── pdf_parsers_simple.py  # PDF parsing with pikepdf + pdfplumber
├── routes/
│   ├── auth_routes.py     # Auth (session, me, logout)
│   ├── accounts.py        # Accounts CRUD
│   ├── categories.py      # Categories CRUD + defaults
│   ├── transactions.py    # Transactions CRUD + transfers
│   ├── analytics.py       # Analytics summary
│   ├── upload.py          # PDF/CSV upload + parser builder
│   ├── accounting.py      # Company, groups, ledgers, vouchers, reports, cash flow
│   ├── ai.py              # AI categorization
│   ├── backup.py          # Backup/restore + reset
│   └── email_sync.py      # Email config + scan + per-account sync
```

## Implemented Features

### Finance Tracker View
- [x] Multi-account management (bank, credit card, cash, wallet)
- [x] Transaction CRUD with category badges
- [x] PDF statement upload with auto-parsing (HDFC, ICICI, etc.)
- [x] CSV import
- [x] Email sync (IMAP/Gmail) with statement period date filtering
- [x] AI auto-categorization (Gemini) across all 5 import flows
- [x] Transfer detection between accounts
- [x] Analytics dashboard (income/expense/category/monthly trends)
- [x] 50+ default categories (Indian context)
- [x] Backup/restore/reset

### Accounting (Tally) View
- [x] Company management with FY start month
- [x] Chart of Accounts (24 default groups, hierarchical)
- [x] Ledger CRUD with linked accounts/categories
- [x] Voucher CRUD (payment, receipt, journal, contra, sales, purchase)
- [x] Auto-bridge: finance transactions ↔ accounting vouchers
- [x] Trial Balance
- [x] Daybook (journal of all entries)
- [x] Profit & Loss Statement (with group-wise subtotals)
- [x] Balance Sheet (with group-wise subtotals)
- [x] Cash Flow Statement (Operating/Investing/Financing)
- [x] FY-aware date defaults across all reports
- [x] Ledger Statement
- [x] Migration tool (transactions → vouchers)

### Infrastructure
- [x] Dual-view UI with sessionStorage persistence
- [x] Theme system (5 themes)
- [x] Google OAuth authentication
- [x] Print-ready report layouts
- [x] Capacitor Android APK setup (build guide at frontend/APK_BUILD_GUIDE.md)
- [x] CLAUDE.md for codebase documentation

## P0 Issues
- None currently

## Remaining Backlog
- CSV parsing/export enhancements (P2)
- Google Drive sync & scheduled background sync (P3)
- GST Computation Report (P3)
- Actual APK build in Android Studio (setup done, needs local build)
