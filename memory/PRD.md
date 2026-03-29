# MoneyInsights - Personal Finance Tracker

## Problem Statement
Track personal finances across 4-5 credit cards, 2-3 bank accounts, investments, and cash transactions. Upload bank/credit card statements (PDF/CSV) and analyze spending trends, categories, and investment patterns.

## Core Requirements
- Browser-based app (React + FastAPI + MongoDB)
- No authentication for MVP
- PDF & CSV statement upload with auto-parsing
- Dynamic "Parser Builder" - users upload sample PDF + password, system learns patterns per account
- Custom categories and account management
- Analytics with category breakdown and monthly trends
- Auto-identification of transfers between accounts

## Architecture
- **Frontend**: React, TailwindCSS, Shadcn UI, Phosphor Icons v2
- **Backend**: FastAPI, pdfplumber (PDF extraction), Motor (async MongoDB)
- **Database**: MongoDB

## What's Implemented (as of Mar 29, 2026)
- [x] Dashboard with summary cards (balance, income, expenses, net savings)
- [x] Accounts CRUD with start balance tracking
- [x] Transactions CRUD with balance updates
- [x] Categories (10 defaults + custom) with color coding
- [x] Upload page supporting PDF and CSV
- [x] Analytics page with category breakdown pie chart and monthly trend bar chart
- [x] Dynamic Parser Builder with auto-detection of 4 strategies:
  - `slice_credit`: Slice credit card format (description ₹amount + date)
  - `hdfc_bank`: HDFC bank statement (multi-page, DD/MM/YY, closing balance tracking)
  - `credit_card`: HDFC Diners/generic credit card (DD/MM/YYYY| description C amount)
  - `generic`: Common regex patterns fallback
- [x] Parser saves detected strategy + password per account for future uploads
- [x] Transfer creation between accounts
- [x] Transfer auto-detection (matching dates/amounts/opposite types)
- [x] Debug PDF endpoint for testing
- [x] CSV import support
- [x] Duplicate transaction detection on upload
- [x] Idempotent default category initialization

## Tested PDF Formats
- **Slice Credit Card**: 24 transactions detected (no password)
- **HDFC Bank Statement**: 296 transactions detected (no password, multi-page)
- **HDFC Diners Credit Card**: 46 transactions detected (password: SANK3011)

## Key API Endpoints
- `POST /api/init` - Initialize default categories (idempotent)
- `POST /api/accounts` / `GET /api/accounts` - Account CRUD
- `POST /api/build-parser` - Upload sample PDF, auto-detect best parsing strategy
- `POST /api/save-parser-pattern` - Save strategy + password per account
- `POST /api/upload-statement` - Parse and import transactions from PDF
- `POST /api/import-csv` - Import from CSV
- `POST /api/debug-pdf` - Test PDF parsing without importing
- `GET /api/analytics/summary` - Dashboard analytics with date filters
- `POST /api/transfers` / `POST /api/detect-transfers` - Transfer management

## Upcoming Tasks (P1)
- Month/Financial Year filters on Analytics page
- Transfer auto-identification improvements

## Future/Backlog (P2)
- AI-powered auto-categorization of transactions
- CSV parsing from more banks
- PWA support
- Export functionality

## DB Schema
- `accounts`: {id, name, account_type, start_balance, current_balance, pdf_password, custom_parser, created_at}
- `transactions`: {id, account_id, date, description, amount, transaction_type, category_id, is_transfer, transfer_pair_id, notes, created_at}
- `categories`: {id, name, category_type, color, is_default, created_at}
