# CLAUDE.md — MoneyInsights Codebase Guide

## What is this?
A personal finance tracker with a built-in Tally-like double-entry accounting engine. Users upload bank/credit card statements (PDF/CSV) or sync via email, and the app auto-categorizes transactions using AI (Gemini). Every finance transaction automatically generates a corresponding accounting voucher (auto-bridge).

## Tech Stack
- **Frontend**: React 18, TailwindCSS, Shadcn UI, Phosphor Icons, Recharts
- **Backend**: Python FastAPI, Motor (async MongoDB), pdfplumber, pikepdf
- **Database**: MongoDB
- **Auth**: Emergent-managed Google OAuth
- **AI**: Gemini 2.5 Flash via `emergentintegrations` library

## Architecture

```
backend/
├── server.py              # App setup, middleware, router registration
├── database.py            # MongoDB client + db instance
├── models.py              # All Pydantic models + default data (categories, account groups)
├── auth.py                # get_current_user() session validator
├── bridge.py              # Auto-bridge: transaction <-> voucher sync
├── helpers.py             # Shared: AI categorizer, default init, IMAP helpers, date parsing
├── pdf_parsers_simple.py  # PDF parsing with pikepdf decryption + pdfplumber
├── routes/
│   ├── auth_routes.py     # POST /api/auth/session, GET /api/auth/me, POST /api/auth/logout
│   ├── accounts.py        # CRUD /api/accounts
│   ├── categories.py      # CRUD /api/categories, restore-defaults, fix-orphaned
│   ├── transactions.py    # CRUD /api/transactions, transfers, detect-transfers
│   ├── analytics.py       # GET /api/analytics/summary
│   ├── upload.py          # PDF/CSV upload, parser builder, debug-pdf
│   ├── accounting.py      # Company, groups, ledgers, vouchers, trial-balance, daybook, P&L, balance-sheet, ledger-statement, migrate
│   ├── ai.py              # POST /api/ai-categorize
│   ├── backup.py          # Export/import backup, reset-all-data
│   └── email_sync.py      # Email config, scan, per-account sync + preview, sync-history

frontend/src/
├── App.js                 # Routing, dual-view (Tracker vs Accounting), sidebar nav
├── contexts/
│   ├── AuthContext.js      # Google OAuth session management
│   └── ThemeContext.js     # 5 themes (light, dark, forest, ocean, sand)
├── pages/
│   ├── Dashboard.js        # Finance tracker dashboard with charts
│   ├── Accounts.js         # Account CRUD with email filter config
│   ├── Transactions.js     # Transaction list with category badges, AI categorize
│   ├── Upload.js           # PDF/CSV upload with result panels
│   ├── Categories.js       # Category management
│   ├── Settings.js         # 3-tab: Tracker / Accounting / Appearance
│   ├── AccountingDashboard.js
│   ├── ChartOfAccounts.js
│   ├── Vouchers.js
│   ├── Daybook.js
│   ├── TrialBalance.js
│   └── Reports.js          # P&L + Balance Sheet
```

## Key Concepts

### Auto-Bridge
Every transaction created in the Finance Tracker automatically generates a double-entry voucher in the Accounting engine (and vice versa for simple 2-leg vouchers). Logic is in `bridge.py`.

### AI Categorization
Centralized in `helpers.py:ai_categorize_batch()`. Uses a tuned prompt for Indian bank statements. Called from 5 import flows: PDF upload, CSV import, manual transaction, batch email scan, per-account email sync.

### Dual-View UI
`App.js` manages a `viewMode` state persisted in `sessionStorage`. The sidebar switches between Finance Tracker nav and Accounting nav. The `/settings` page preserves the active view context.

### PDF Parsing
`pdf_parsers_simple.py` uses `pikepdf` as the primary decryption layer (handles AES-256), then passes to `pdfplumber` for text extraction. Supports named parsers for HDFC, ICICI, etc.

## Database Collections
- `users`, `user_sessions` — Auth
- `accounts`, `transactions`, `categories` — Finance Tracker
- `companies`, `account_groups`, `ledgers`, `vouchers` — Accounting
- `email_configs`, `processed_emails`, `sync_history` — Email sync

## Environment Variables
- `MONGO_URL`, `DB_NAME` — MongoDB connection
- `EMERGENT_LLM_KEY` — Gemini AI for categorization
- `REACT_APP_BACKEND_URL` — Frontend API base URL

## Common Commands
```bash
# Backend logs
tail -f /var/log/supervisor/backend.err.log

# Restart services
sudo supervisorctl restart backend
sudo supervisorctl restart frontend

# Run backend tests
cd /app/backend && python -m pytest tests/

# API test
API_URL=$(grep REACT_APP_BACKEND_URL /app/frontend/.env | cut -d '=' -f2)
curl -s "$API_URL/api/auth/me" -H "Authorization: Bearer <token>"
```

## Conventions
- All API routes prefixed with `/api`
- All MongoDB queries exclude `_id` in projections
- Dates stored as ISO strings (`YYYY-MM-DD`)
- `created_at` converted to ISO string before MongoDB insert
- Category colors are hex codes used for UI badges
