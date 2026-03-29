# MoneyInsights - Personal Finance Tracker

A comprehensive web application to track your finances across multiple accounts, cards, and investments with intelligent PDF parsing and analytics.

## Features

### ✅ Implemented

#### 1. **Multi-Account Management**
- Create and manage multiple accounts (Bank, Credit Card, Investment, Cash)
- Set starting balances for each account
- Track current balance with automatic updates
- Edit and delete accounts

#### 2. **Smart Transaction Management**
- Add transactions manually with categorization
- Upload PDF statements from multiple banks
- Import CSV files
- Edit and delete transactions
- Automatic balance updates

#### 3. **Transfer Detection & Management**
- Create transfers between accounts
- Auto-detect potential transfers (matching amount, date, opposite types)
- Mark detected transactions as transfers
- Transfers excluded from income/expense analytics

#### 4. **Custom Category System**
- Default categories for income and expenses
- Create custom categories with colors
- Edit existing categories
- Protected default categories

#### 5. **PDF Statement Parsing**
Supported banks with intelligent parsing:
- **HDFC Diners Credit Card** - Extracts transactions from Domestic Transactions section
- **HDFC Bank** - Parses account statements
- **Slice Card** - Handles pipe-separated format
- **Kotak Bank** - Parses VDP transactions
- **SBI Bank** - Extracts To/By format transactions
- **Generic Parser** - Auto-detects common formats

Features:
- Automatic duplicate detection
- Date normalization to YYYY-MM-DD
- Credit/Debit type detection
- Amount parsing with comma handling

#### 6. **Advanced Analytics**
- Period filtering (This Month, Last Month, This FY, Last FY, Custom Range)
- Total income, expenses, and net savings
- Savings rate calculation
- Income and expense breakdown (pie charts)
- Monthly trend analysis (line charts)
- Top 5 expense categories (bar chart)
- Account balance overview

#### 7. **Beautiful UI/UX**
- Organic & Earthy design theme
- Glassmorphism header
- Responsive grid layouts
- Hover animations and transitions
- Manrope font for headings, IBM Plex Sans for body
- Color-coded transactions (Green for income, Terracotta for expenses)

## Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **MongoDB** - Document database with Motor (async driver)
- **pdfplumber** - PDF text extraction
- **Pydantic** - Data validation

### Frontend
- **React 19** - UI framework
- **React Router** - Navigation
- **Shadcn/UI** - Component library
- **Recharts** - Data visualization
- **Phosphor Icons** - Icon library
- **Tailwind CSS** - Styling
- **Sonner** - Toast notifications

## Getting Started

### Prerequisites
- The app is already running in your Emergent environment
- Backend: `http://0.0.0.0:8001`
- Frontend: Available at your preview URL

### First Time Setup

1. **Create Accounts**
   - Go to "Accounts" page
   - Click "Add Account"
   - Enter account name, type, and starting balance
   - Create accounts for all your credit cards, bank accounts, investments, and cash

2. **Upload Statements**
   - Go to "Upload" page
   - Select the account
   - Choose bank type from dropdown
   - Upload PDF statement or CSV file
   - System will automatically parse and import transactions

3. **Manage Transfers**
   - Go to "Transactions" page
   - Click "Detect Transfers" to find potential transfers
   - Review and mark matching transactions as transfers
   - Or manually create transfers between accounts

4. **Analyze Data**
   - Go to "Analytics" page
   - Select period (Month, FY, or Custom)
   - View charts and insights

## PDF Parsing

### How to Add Your Bank

The PDF parsing system is extensible. To add a new bank:

1. Open `/app/backend/pdf_parsers.py`
2. Create a new parser class inheriting from `BankStatementParser`
3. Implement the `parse()` method
4. Add the bank to the `get_parser()` factory function
5. Update the frontend dropdown in `/app/frontend/src/pages/Upload.js`

### Example Parser Structure

```python
class YourBankParser(BankStatementParser):
    def parse(self, pdf_blob: bytes) -> List[Dict]:
        text = self.extract_text(pdf_blob)
        transactions = []
        
        # Your parsing logic here
        # Use regex to extract: date, description, amount, type
        
        return transactions
```

### Testing Your Parser

You can test your parser using the test script:

```bash
cd /app/backend
python test_pdf_parser.py
```

## CSV Import Format

For CSV imports, use this format:

```csv
date,description,amount,type
2025-01-15,Grocery Store,2500.50,debit
2025-01-16,Salary Deposit,50000.00,credit
```

- **date**: YYYY-MM-DD format
- **description**: Transaction description
- **amount**: Numeric value (positive)
- **type**: Either "credit" or "debit"

## API Endpoints

### Accounts
- `POST /api/accounts` - Create account
- `GET /api/accounts` - List all accounts
- `PUT /api/accounts/{id}` - Update account
- `DELETE /api/accounts/{id}` - Delete account

### Transactions
- `POST /api/transactions` - Create transaction
- `GET /api/transactions` - List transactions (with filters)
- `PUT /api/transactions/{id}` - Update transaction
- `DELETE /api/transactions/{id}` - Delete transaction

### Categories
- `POST /api/categories` - Create category
- `GET /api/categories` - List all categories
- `PUT /api/categories/{id}` - Update category
- `DELETE /api/categories/{id}` - Delete category

### Transfers
- `POST /api/transfers` - Create transfer
- `POST /api/detect-transfers` - Auto-detect transfers
- `POST /api/mark-as-transfer` - Mark transactions as transfer

### Upload
- `POST /api/upload-statement` - Upload PDF statement
- `POST /api/import-csv` - Import CSV file

### Analytics
- `GET /api/analytics/summary` - Get analytics summary (with date filters)

## File Structure

```
/app/
├── backend/
│   ├── server.py              # Main FastAPI application
│   ├── pdf_parsers.py         # PDF parsing logic for all banks
│   ├── test_pdf_parser.py     # Parser testing script
│   ├── requirements.txt       # Python dependencies
│   └── .env                   # Environment variables
├── frontend/
│   ├── src/
│   │   ├── App.js            # Main app component with navigation
│   │   ├── App.css           # Global styles
│   │   ├── pages/
│   │   │   ├── Dashboard.js   # Dashboard with summary cards
│   │   │   ├── Accounts.js    # Account management
│   │   │   ├── Transactions.js # Transaction list and transfers
│   │   │   ├── Categories.js  # Category management
│   │   │   ├── Upload.js      # File upload page
│   │   │   └── Analytics.js   # Analytics and charts
│   │   └── components/ui/     # Shadcn UI components
│   ├── package.json
│   └── .env
└── design_guidelines.json     # UI/UX design specifications
```

## Adding More Banks

You mentioned you have more bank parsers. Here's how to add them:

1. **Analyze the PDF format** - Look at the transaction section structure
2. **Identify patterns** - Date format, amount position, credit/debit indicators
3. **Create parser class** - Add to `pdf_parsers.py`
4. **Test with sample** - Use the test script
5. **Update UI** - Add option to Upload page dropdown

### Current Parsers Available:

1. **HDFCDinersParser** - For HDFC Diners Club Credit Card
   - Looks for "Domestic Transactions" section
   - Date format: DD/MM/YYYY
   - Amount with "Cr" suffix for credits

2. **HDFCBankParser** - For HDFC Bank accounts
   - Pattern: DD/MM/YY DESCRIPTION AMOUNT
   - Detects "SALARY", "CREDIT" keywords

3. **SliceBankParser** - For Slice cards
   - Format: DD-MM-YYYY|Description|Category|Amount
   - Pipe-separated values

4. **KotakBankParser** - For Kotak Bank
   - Format: Date: DD Mon YYYY, Narration: XXX, Amount: XXX, Type: DR/CR

5. **SBIBankParser** - For SBI Bank
   - Format: DD/MM/YYYY To/By/DESCRIPTION AMOUNT Dr/Cr

6. **GenericParser** - Fallback parser
   - Tries multiple date formats
   - Uses keyword matching for type detection

## Next Steps

### Potential Enhancements:

1. **More Banks** - Add your remaining bank parsers
2. **Budget Management** - Set budgets per category
3. **Recurring Transactions** - Auto-create monthly transactions
4. **Export Reports** - PDF/Excel export of analytics
5. **Authentication** - Add user login for multi-user support
6. **Mobile App** - PWA or React Native app
7. **AI Insights** - Add GPT integration for spending insights
8. **Receipt Upload** - OCR for receipt scanning
9. **Goals & Savings** - Track financial goals
10. **Investment Tracking** - Track portfolio returns

## Troubleshooting

### PDF Not Parsing Correctly

1. Check if the bank type is selected correctly
2. Try the Generic parser
3. View backend logs: `tail -f /var/log/supervisor/backend.err.log`
4. Export the transactions manually as CSV from your bank

### Transactions Not Showing

1. Check if the correct account is selected
2. Verify date range in analytics filters
3. Check MongoDB data: Use MongoDB shell to inspect `transactions` collection

### Balance Not Updating

1. Verify transaction type (credit/debit) is correct
2. Check if transaction was successfully created
3. Account balance updates automatically on transaction create/update/delete

## Support

For issues or questions:
1. Check backend logs for errors
2. Use browser console for frontend errors
3. Test API endpoints directly using curl
4. Review the PDF parser output in backend logs

## License

Built with Emergent AI - Your Finance Tracking Solution
