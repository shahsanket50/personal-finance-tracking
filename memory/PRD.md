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
- **Theming**: CSS custom properties with 5 themes (light default)

## What's Implemented
- [x] Google OAuth login/signup (Emergent Auth)
- [x] Protected routes - all API endpoints require auth
- [x] Multi-tenant data isolation (user_id on all collections)
- [x] **5 Themes**: Light (default), Dark, Forest, Ocean, Sand - persisted in localStorage
- [x] Theme picker in **Settings page** (moved from sidebar — Mar 2026)
- [x] Dashboard with summary cards + Export Backup button
- [x] Accounts CRUD with start balance + email filter per account
- [x] **Account-level email sync** with Sync Email button per account card (Mar 2026)
- [x] **Sync History dialog** per account showing logs (Mar 2026)
- [x] Transactions CRUD with balance updates
- [x] Categories (10 defaults per user + custom) with color coding
- [x] Upload page supporting PDF and CSV
- [x] Analytics page with category breakdown pie chart and monthly trend bar chart
- [x] Dynamic Parser Builder with 4 auto-detection strategies
- [x] AI-powered transaction categorization (Gemini 2.5 Flash)
- [x] Local JSON backup/export + restore/import
- [x] Settings page with Email Auto-Scan (IMAP), Backup/Restore, Theme Picker, APK Download
- [x] Email inbox scanning with duplicate detection
- [x] Transfer creation and auto-detection
- [x] **Enhanced auto-detect transfers** with ±1 day tolerance + confidence scoring (Mar 2026)
- [x] PWA setup (manifest.json, service worker, icons)
- [x] **APK download link** in Settings (Coming Soon badge) (Mar 2026)

## Themes
| Theme | Preview Color | Style |
|-------|--------------|-------|
| Light | #F9F8F6 | Clean cream/white with green accents |
| Dark | #111111 | Deep black with muted green |
| Forest | #1a2a1a | Deep green forest palette |
| Ocean | #EEF4F8 | Light blue-grey with teal accents |
| Sand | #F5F0E8 | Warm beige with golden accents |

## Future/Backlog
- Native APK generation via Capacitor (P2)
- CSV parsing support (P2)
- Month/Financial Year filters on Analytics page (P2)
- Google Drive API sync (needs separate OAuth with drive.file scope) (P3)
- CSV/Excel export (P3)
- Scheduled background email sync (P3)
- Smart AI dashboard insights (P3)
