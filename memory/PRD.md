# MoneyInsights - Personal Finance Tracker

## Problem Statement
Track personal finances across 4-5 credit cards, 2-3 bank accounts, investments, and cash transactions. Upload bank/credit card statements (PDF/CSV) and analyze spending trends, categories, and investment patterns.

## Architecture
- **Frontend**: React, TailwindCSS, Shadcn UI, Phosphor Icons v2
- **Backend**: FastAPI, pdfplumber (PDF extraction), Motor (async MongoDB)
- **Database**: MongoDB (multi-tenant with user_id)
- **Auth**: Emergent-managed Google OAuth (auth.emergentagent.com)
- **AI**: Gemini 2.5 Flash via emergentintegrations (LlmChat)
- **Email**: IMAP with Google App Passwords for inbox scanning
- **PWA**: manifest.json, service worker for install-to-homescreen

## What's Implemented
- [x] Google OAuth login/signup (Emergent Auth - auth.emergentagent.com)
- [x] Protected routes - all API endpoints require auth
- [x] Multi-tenant data isolation (user_id on all collections)
- [x] Dashboard with summary cards + Export Backup button
- [x] Accounts CRUD with start balance + email filter per account
- [x] Transactions CRUD with balance updates
- [x] Categories (10 defaults per user + custom) with color coding
- [x] Upload page supporting PDF and CSV
- [x] Analytics page with category breakdown pie chart and monthly trend bar chart
- [x] Dynamic Parser Builder with 4 auto-detection strategies (slice_credit, hdfc_bank, credit_card, generic)
- [x] AI-powered transaction categorization (Gemini 2.5 Flash)
- [x] Local JSON backup/export + restore/import
- [x] Settings page with Email Auto-Scan (IMAP) configuration
- [x] Email inbox scanning - auto-detect bank statement emails, download PDFs, parse & import
- [x] Email filter per account (keyword matching in email subjects)
- [x] Duplicate detection (email message ID tracking + transaction dedup)
- [x] Transfer creation and auto-detection
- [x] PWA setup (manifest.json, service worker, meta tags, icons)

## Key API Endpoints
### Auth
- `POST /api/auth/session` - Exchange OAuth session_id for app session
- `GET /api/auth/me` - Get current user
- `POST /api/auth/logout` - Logout

### Core
- `POST /api/accounts` / `GET /api/accounts` - Account CRUD (with email_filter)
- `POST /api/transactions` / `GET /api/transactions` - Transaction CRUD
- `POST /api/categories` / `GET /api/categories` - Category CRUD
- `GET /api/analytics/summary` - Dashboard analytics

### PDF Parsing
- `POST /api/build-parser` - Auto-detect parsing strategy for a PDF
- `POST /api/save-parser-pattern` - Save strategy + password per account
- `POST /api/upload-statement` - Parse and import transactions from PDF

### Email & AI
- `POST /api/email-config` / `GET /api/email-config` - IMAP email settings
- `POST /api/email-scan` - Scan inbox for bank statement emails
- `POST /api/ai-categorize` - AI auto-categorization (Gemini 2.5 Flash)

### Backup
- `GET /api/backup/export` - Export all user data as JSON
- `POST /api/backup/import` - Restore from JSON backup

## DB Schema
- `users`: {user_id, email, name, picture, created_at}
- `user_sessions`: {user_id, session_token, expires_at, created_at}
- `accounts`: {id, user_id, name, account_type, start_balance, current_balance, pdf_password, custom_parser, email_filter, created_at}
- `transactions`: {id, user_id, account_id, date, description, amount, transaction_type, category_id, is_transfer, transfer_pair_id, notes, created_at}
- `categories`: {id, user_id, name, category_type, color, is_default, created_at}
- `email_configs`: {user_id, imap_server, email_address, app_password, updated_at}
- `processed_emails`: {email_hash, user_id, account_id, message_id, processed_at}

## Future/Backlog
- Google Drive API sync (needs separate OAuth with drive.file scope)
- Month/Financial Year filters on Analytics page
- Capacitor APK wrapper for native Android/iOS apps
- CSV/Excel export
- Scheduled background email sync
- Smart AI dashboard insights ("You spent 40% more on dining this month")
