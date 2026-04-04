# MoneyInsights - Personal Finance Tracker + Accounting Engine

## Problem Statement
Track personal finances across 4-5 credit cards, 2-3 bank accounts, investments, and cash transactions. Upload bank/credit card statements (PDF/CSV) and analyze spending trends, categories, and investment patterns.
Additionally, provide a Tally-like double-entry bookkeeping system with auto-bridge so users don't enter data twice.

## Architecture
- **Frontend**: React, TailwindCSS, Shadcn UI, Phosphor Icons v2, Recharts v3
- **Backend**: FastAPI, pdfplumber (PDF extraction), Motor (async MongoDB)
- **Database**: MongoDB (multi-tenant with user_id)
- **Auth**: Emergent-managed Google OAuth (auth.emergentagent.com)
- **AI**: Gemini 2.5 Flash via emergentintegrations (auto-categorization)
- **Email**: IMAP with Google App Passwords, [Gmail]/All Mail, FROM + SUBJECT + SINCE filters
- **PWA**: manifest.json, service worker
- **Theming**: CSS custom properties with 5 themes

## What's Implemented

### Finance Tracker (View 1)
- [x] Google OAuth login/signup
- [x] Protected routes — all API endpoints require auth
- [x] Multi-tenant data isolation
- [x] 5 Themes: Light, Dark, Forest, Ocean, Sand
- [x] Merged Dashboard with analytics, period selector, charts, legends
- [x] Accounts CRUD with email filter, PDF password, parser config
- [x] Sync Preview (dry-run) + Account email sync with auto-categorization
- [x] Sync History dialog per account
- [x] Transaction CRUD with filters (type, search, account, category, date)
- [x] Categories (defaults + custom) with color coding
- [x] Upload page (PDF/CSV)
- [x] Dynamic Parser Builder (4 auto-detection strategies)
- [x] AI auto-categorization (Gemini)
- [x] Backup/Restore (JSON)
- [x] Settings: Email Config, Backup, Themes, APK, Reset All Data
- [x] Transfer creation + enhanced auto-detection
- [x] PWA setup

### Accounting Engine (View 2 — Tally-like)
- [x] Company management (name, GSTIN, PAN, FY start)
- [x] Indian Standard Chart of Accounts (24 default groups)
- [x] Account Groups CRUD (hierarchical tree with nature: asset/liability/income/expense)
- [x] Ledgers CRUD (linked to groups, opening balance, linked_account_id/linked_category_id)
- [x] Vouchers CRUD (payment, receipt, journal, contra, sales, purchase, credit/debit note)
- [x] Double-entry validation (debit must equal credit)
- [x] Auto voucher numbering (PMT-0001, RCT-0001, etc.)
- [x] Trial Balance (date-filtered, balanced check)
- [x] Daybook (date-filtered journal of all entries with ledger names)
- [x] Ledger Statement (per-ledger transaction history with running balance)
- [x] Profit & Loss Statement (income vs expenses, net profit)
- [x] Balance Sheet (assets vs liabilities + net profit, balanced check)
- [x] **Auto-Bridge**: Transaction → Voucher (on create from all flows: manual, PDF, CSV, email sync)
- [x] **Auto-Bridge**: Voucher → Transaction (for bank/cash ledger vouchers)
- [x] Migration endpoint (convert historical transactions to vouchers)
- [x] Reset All Data cleans up accounting collections too

### Dual-View Frontend System
- [x] Sidebar navigation switches between Finance Tracker and Accounting views
- [x] "Switch to Accounting/Finance Tracker" toggle in sidebar
- [x] 6 Accounting pages: Dashboard, Chart of Accounts, Vouchers, Daybook, Trial Balance, Reports
- [x] Shared Settings page between both views

## Key DB Collections
### Finance Tracker
- `accounts`: {name, type, balance, parser_config, email_filter, pdf_password, user_id}
- `transactions`: {date, amount, description, type, category, account_id, user_id, is_transfer}
- `categories`: {name, category_type, color, user_id}
- `sync_history`, `email_configs`, `processed_emails`

### Accounting Engine
- `companies`: {name, address, gstin, pan, fy_start_month, user_id}
- `account_groups`: {name, parent_id, nature, is_default, sort_order, company_id, user_id}
- `ledgers`: {name, group_id, opening_balance, opening_type, linked_account_id, linked_category_id, company_id, user_id}
- `vouchers`: {voucher_number, voucher_type, date, narration, entries: [{ledger_id, debit, credit}], linked_transaction_id, company_id, user_id}

## Future/Backlog
- CSV parsing support (P2)
- Native APK generation via Capacitor (P2)
- Google Drive API sync (P3)
- CSV/Excel export (P3)
- Scheduled background email sync (P3)
- Smart AI dashboard insights (P3)
