# MoneyInsights - Personal Finance Tracker

## Problem Statement
Track personal finances across 4-5 credit cards, 2-3 bank accounts, investments, and cash transactions. Upload bank/credit card statements (PDF/CSV) and analyze spending trends, categories, and investment patterns.

## Architecture
- **Frontend**: React, TailwindCSS, Shadcn UI, Phosphor Icons v2, Recharts
- **Backend**: FastAPI, pdfplumber (PDF extraction), Motor (async MongoDB)
- **Database**: MongoDB (multi-tenant with user_id)
- **Auth**: Emergent-managed Google OAuth (auth.emergentagent.com)
- **AI**: Gemini 2.5 Flash via emergentintegrations (LlmChat) — auto-categorization
- **Email**: IMAP with Google App Passwords, searches [Gmail]/All Mail
- **PWA**: manifest.json, service worker for install-to-homescreen
- **Theming**: CSS custom properties with 5 themes (light default)

## What's Implemented
- [x] Google OAuth login/signup (Emergent Auth)
- [x] Protected routes — all API endpoints require auth
- [x] Multi-tenant data isolation (user_id on all collections)
- [x] **5 Themes**: Light, Dark, Forest, Ocean, Sand — Theme Picker in Settings page
- [x] **Merged Dashboard**: Summary cards (Balance, Income, Expenses, Net Savings, Savings Rate) + Period selector (All Time, Month, FY, Custom) + Top Expenses bar chart + Expense Breakdown donut + Monthly Trend bar chart + Accounts overview
- [x] Analytics page removed — redirects to Dashboard
- [x] Accounts CRUD with start balance, email filter, PDF password per account
- [x] **Account-level email sync** with Sync Email button + sync history dialog
- [x] **Cascade delete account** — deletes transactions, sync history, processed emails with confirmation dialog
- [x] **Transaction filters**: Type pills (All/Credit/Debit), search, advanced filters (Account, Category inc. Uncategorized, Date From/To), clear filters
- [x] Transactions CRUD with balance updates
- [x] Categories (10 defaults per user + custom) with color coding
- [x] Upload page supporting PDF and CSV
- [x] Dynamic Parser Builder with 4 auto-detection strategies
- [x] **AI auto-categorization** — runs automatically after email sync imports new transactions
- [x] Manual AI categorize button on Transactions page
- [x] Local JSON backup/export + restore/import
- [x] Settings: Email Auto-Scan (IMAP), Backup/Restore, Theme Picker, APK Download, **Reset All Data (Danger Zone)**
- [x] Email inbox scanning with [Gmail]/All Mail, multi-strategy search, SINCE date filter
- [x] Transfer creation and enhanced auto-detection (±1 day, confidence scoring)
- [x] PWA setup (manifest.json, service worker, icons)

## Key DB Collections
- `users`: {email, google_id}
- `accounts`: {name, type, balance, parser_config, email_filter, pdf_password, user_id}
- `transactions`: {date, amount, description, type, category, account_id, user_id}
- `categories`: {name, category_type, color, user_id}
- `processed_emails`: {email_hash, account_id, user_id, status}
- `sync_history`: {account_id, user_id, status, imported, skipped, files, filter_used, emails_matched, timestamp}
- `email_configs`: {user_id, imap_server, email_address, app_password, sync_since}

## Future/Backlog
- CSV parsing support (P2)
- Native APK generation via Capacitor (P2)
- Google Drive API sync (P3)
- CSV/Excel export (P3)
- Scheduled background email sync (P3)
- Smart AI dashboard insights (P3)
