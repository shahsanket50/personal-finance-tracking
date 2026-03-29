# MoneyInsights - Personal Finance Tracker

## Problem Statement
Track personal finances across 4-5 credit cards, 2-3 bank accounts, investments, and cash transactions. Upload bank/credit card statements (PDF/CSV) and analyze spending trends, categories, and investment patterns.

## Core Requirements
- Browser-based app (React + FastAPI + MongoDB)
- Google OAuth authentication (mandatory)
- PDF & CSV statement upload with auto-parsing
- Dynamic "Parser Builder" - users upload sample PDF + password, system learns patterns per account
- Custom categories and account management
- Analytics with category breakdown and monthly trends
- AI-powered auto-categorization of transactions
- Data backup/export
- Auto-identification of transfers between accounts
- Auto-read email and download statements (upcoming)
- Sharable APK for Android/iOS (upcoming)

## Architecture
- **Frontend**: React, TailwindCSS, Shadcn UI, Phosphor Icons v2
- **Backend**: FastAPI, pdfplumber (PDF extraction), Motor (async MongoDB)
- **Database**: MongoDB (multi-tenant with user_id)
- **Auth**: Emergent-managed Google OAuth
- **AI**: Gemini 2.5 Flash via emergentintegrations (LlmChat)

## What's Implemented (as of Mar 29, 2026)
- [x] Google OAuth login/signup (Emergent Auth)
- [x] Protected routes - all API endpoints require auth
- [x] Dashboard with summary cards + Export Backup button
- [x] Accounts CRUD with start balance tracking
- [x] Transactions CRUD with balance updates
- [x] Categories (10 defaults per user + custom) with color coding
- [x] Upload page supporting PDF and CSV
- [x] Analytics page with category breakdown pie chart and monthly trend bar chart
- [x] Dynamic Parser Builder with 4 auto-detection strategies
- [x] AI-powered transaction categorization (Gemini 2.5 Flash)
- [x] Local JSON backup/export
- [x] Transfer creation and auto-detection
- [x] Duplicate transaction detection on upload
- [x] Multi-tenant data isolation (user_id on all collections)

## Key API Endpoints
- `POST /api/auth/session` - Exchange OAuth session_id for app session
- `GET /api/auth/me` - Get current user
- `POST /api/auth/logout` - Logout
- `GET /auth/callback` - OAuth redirect handler
- `POST /api/accounts` / `GET /api/accounts` - Account CRUD
- `POST /api/build-parser` - Upload sample PDF, auto-detect parsing strategy
- `POST /api/save-parser-pattern` - Save strategy + password per account
- `POST /api/upload-statement` - Parse and import transactions from PDF
- `POST /api/ai-categorize` - AI auto-categorization
- `GET /api/backup/export` - Export all user data as JSON
- `GET /api/analytics/summary` - Dashboard analytics
- `POST /api/transfers` / `POST /api/detect-transfers` - Transfer management

## Upcoming Tasks (P1)
- Google Drive backup sync
- Gmail auto-read and statement download
- Email filter configuration per account
- PWA / Capacitor APK setup

## Future/Backlog (P2)
- Month/Financial Year filters on Analytics page
- CSV parsing from more bank formats
- Export as CSV/Excel
- Scheduled background sync for email statements

## DB Schema
- `users`: {user_id, email, name, picture, created_at}
- `user_sessions`: {user_id, session_token, expires_at, created_at}
- `accounts`: {id, user_id, name, account_type, start_balance, current_balance, pdf_password, custom_parser, email_filter, created_at}
- `transactions`: {id, user_id, account_id, date, description, amount, transaction_type, category_id, is_transfer, transfer_pair_id, notes, created_at}
- `categories`: {id, user_id, name, category_type, color, is_default, created_at}
