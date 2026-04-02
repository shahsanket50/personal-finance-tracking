# MoneyInsights - Personal Finance Tracker

## Problem Statement
Track personal finances across 4-5 credit cards, 2-3 bank accounts, investments, and cash transactions. Upload bank/credit card statements (PDF/CSV) and analyze spending trends, categories, and investment patterns.

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
- [x] Google OAuth login/signup
- [x] Protected routes — all API endpoints require auth
- [x] Multi-tenant data isolation
- [x] 5 Themes: Light, Dark, Forest, Ocean, Sand — picker in Settings
- [x] **Merged Dashboard**: Summary cards + Period selector (All/Month/FY/Custom) + Top Expenses bar + Expense Breakdown donut with legend + Monthly/Daily Trend + Top Spends + Top Income Sources + Accounts with credits/debits
- [x] Accounts CRUD with email filter, from-email filter, PDF password
- [x] **Sync Preview** — dry-run preview showing matched emails, PDFs, parse status
- [x] Account-level email sync with auto-categorization post-import
- [x] Sync History dialog per account
- [x] Cascade delete account (transactions, sync history, processed emails)
- [x] **Transaction filters**: Type pills, search, Account/Category/Date filters
- [x] Transactions CRUD with balance updates
- [x] Categories (defaults + custom) with color coding
- [x] Upload page (PDF/CSV)
- [x] Dynamic Parser Builder (4 auto-detection strategies)
- [x] AI auto-categorization (Gemini) — auto after sync, manual button
- [x] Backup/Restore (JSON)
- [x] Settings: Email Config (IMAP, sync_since date), Backup, Themes, APK, Reset All Data
- [x] Transfer creation + enhanced auto-detection (±1 day, confidence scoring)
- [x] PWA setup

## Key DB Collections
- `accounts`: {name, type, balance, parser_config, email_filter, email_from_filter, pdf_password, user_id}
- `transactions`: {date, amount, description, type, category, account_id, user_id, is_transfer}
- `categories`: {name, category_type, color, user_id}
- `sync_history`: {account_id, user_id, status, imported, skipped, files, filter_used, emails_matched}
- `email_configs`: {user_id, imap_server, email_address, app_password, sync_since}

## Future/Backlog
- CSV parsing support (P2)
- Native APK generation via Capacitor (P2)
- Google Drive API sync (P3)
- CSV/Excel export (P3)
- Scheduled background email sync (P3)
- Smart AI dashboard insights (P3)
