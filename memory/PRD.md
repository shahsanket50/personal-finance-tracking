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

## What's Implemented

### Finance Tracker (View 1)
- [x] Google OAuth login/signup
- [x] Multi-tenant data isolation
- [x] 5 Themes: Light, Dark, Forest, Ocean, Sand
- [x] Merged Dashboard with analytics, period selector, charts, legends
- [x] Accounts CRUD with email filter, PDF password, parser config
- [x] Email sync with preview/dry-run + auto-categorization
- [x] Transaction CRUD with filters (type, search, account, category, date)
- [x] **48 default categories** (10 income + 38 expense — comprehensive Indian finance set)
- [x] Auto-restore missing default categories + orphaned reference cleanup
- [x] **Improved AI categorization** with Indian bank-aware prompt + fuzzy matching
- [x] Category badges with color dots in Transactions view
- [x] AI Categorize button shows uncategorized count badge
- [x] Upload page (PDF/CSV), Dynamic Parser Builder
- [x] Backup/Restore (JSON)
- [x] Settings — 3-tab layout: Finance Tracker / Accounting / Appearance & Data

### Accounting Engine (View 2 — Tally-like)
- [x] Company management (name, GSTIN, PAN, CIN) — in Settings > Accounting
- [x] **Financial Year selector** — auto-computed from transaction/voucher date ranges
- [x] Indian Standard Chart of Accounts (24 default groups)
- [x] Ledgers CRUD, Vouchers CRUD (8 types), double-entry validation
- [x] Trial Balance, Daybook, Ledger Statement
- [x] Profit & Loss Statement, Balance Sheet
- [x] Auto-Bridge: Transaction → Voucher (all creation flows)
- [x] Migration endpoint, Reset cleans accounting data

### Settings Page (3 Tabs)
- Tab 1 — **Finance Tracker**: Email config, Categories restore
- Tab 2 — **Accounting**: Company details, FY selector, Sync to Accounting
- Tab 3 — **Appearance & Data**: Themes, Backup/Restore, Mobile App, Danger Zone

## Key DB Collections
- `accounts`, `transactions`, `categories`, `sync_history`, `email_configs`, `processed_emails`
- `companies`, `account_groups`, `ledgers`, `vouchers`

## Future/Backlog
- CSV parsing support (P2)
- Native APK generation via Capacitor (P2)
- Google Drive API sync (P3)
- CSV/Excel export (P3)
- Smart AI dashboard insights (P3)
- GST Computation Report (P3)
