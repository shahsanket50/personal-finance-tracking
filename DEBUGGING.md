# Debugging PDF Upload Issues

## Quick Debugging Steps

### Step 1: Check Backend Logs (Real-time)

```bash
# Watch backend logs in real-time
tail -f /var/log/supervisor/backend.err.log
```

Then upload your PDF and watch for:
- "Processing PDF" messages
- Parser name being used
- Number of transactions found
- Any error messages

### Step 2: Use the Debug Script

Upload your PDF file to the container first, then run:

```bash
# Basic usage
cd /app/backend
python debug_pdf.py /path/to/your/diners_statement.pdf hdfc_diners
```

**What it does:**
- Extracts all text from PDF
- Shows first 1000 characters
- Attempts to parse transactions
- Saves full output to `/tmp/extracted_text.txt`
- Saves parsed data to `/tmp/parsed_transactions.json`

### Step 3: Review Extracted Text

```bash
# View the extracted text
cat /tmp/extracted_text.txt

# Or view just the first part
head -n 50 /tmp/extracted_text.txt
```

**Look for:**
- Is text extracted correctly?
- Are there section markers like "Domestic Transactions"?
- What's the date format? (DD/MM/YYYY, DD-MM-YYYY, etc.)
- How are amounts formatted? (1,234.56 or 1234.56)
- Is there "Cr" or "Dr" suffix for credit/debit?

### Step 4: Check Parsed Output

```bash
# View parsed transactions
cat /tmp/parsed_transactions.json
```

## Common Issues & Solutions

### Issue 1: "No transactions found"

**Possible causes:**
1. Wrong bank type selected
2. Section markers don't match
3. Date format different
4. PDF is scanned image (not text-based)

**Solution:**
```bash
# Run debug script
python debug_pdf.py your_file.pdf hdfc_diners

# Check /tmp/extracted_text.txt
cat /tmp/extracted_text.txt | head -n 100

# Look for the transaction section
cat /tmp/extracted_text.txt | grep -A 5 "Domestic"
```

### Issue 2: "Transactions parsed but amounts wrong"

**Solution:**
The amount regex might need adjustment. Check the pattern in the extracted text:

```bash
# Find lines with amounts
cat /tmp/extracted_text.txt | grep -E "[0-9]{1,3},[0-9]{3}\.[0-9]{2}"
```

If amounts don't have commas or have different format, we need to update the regex.

### Issue 3: "Dates not recognized"

**Solution:**
Check date format in extracted text:

```bash
# Look for date patterns
cat /tmp/extracted_text.txt | grep -E "[0-9]{2}/[0-9]{2}/[0-9]{4}"
```

If dates are in different format (like DD-MM-YYYY), we need to update the parser.

### Issue 4: "PDF is blank/garbled"

**This means PDF is image-based, not text-based**

Options:
1. Download statement as Excel/CSV from bank
2. Use OCR (requires additional setup)
3. Manually add transactions

## Uploading PDF to Debug

If your PDF is on your local machine, you need to upload it to the container:

### Option 1: Use the Web UI
Just try uploading through the Upload page - the enhanced error messages will help!

### Option 2: Manual Upload for Debugging

You can use the code editor's file upload feature:
1. Open the Emergent code editor
2. Navigate to `/tmp/` folder
3. Upload your PDF there
4. Run debug script: `python /app/backend/debug_pdf.py /tmp/your_file.pdf hdfc_diners`

## Detailed Debug Process

### 1. Test PDF Text Extraction

```bash
cd /app/backend
python3 << 'EOF'
import pdfplumber
import sys

with open('/tmp/your_statement.pdf', 'rb') as f:
    with pdfplumber.open(f) as pdf:
        print(f"Pages: {len(pdf.pages)}")
        for i, page in enumerate(pdf.pages):
            print(f"\n=== Page {i+1} ===")
            text = page.extract_text()
            print(text[:500] if text else "[No text extracted]")
EOF
```

### 2. Test Regex Patterns

```bash
python3 << 'EOF'
import re

# Your transaction line from extracted text
line = "15/01/2024 SWIGGY FOOD ORDER 850.50"

# Test date pattern
date_regex = re.compile(r'^(\d{2}/\d{2}/\d{4})')
match = date_regex.match(line)
if match:
    print(f"Date found: {match.group(1)}")
else:
    print("Date NOT matched")

# Test amount pattern
amount_regex = re.compile(r'(\d{1,3}(?:,\d{3})*\.\d{2})(\s*Cr)?$')
match = amount_regex.search(line)
if match:
    print(f"Amount found: {match.group(1)}")
    print(f"Type: {'Credit' if match.group(2) else 'Debit'}")
else:
    print("Amount NOT matched")
EOF
```

### 3. Test Full Parser

```bash
cd /app/backend
python3 << 'EOF'
import sys
sys.path.insert(0, '/app/backend')

from pdf_parsers import HDFCDinersParser

with open('/tmp/your_statement.pdf', 'rb') as f:
    content = f.read()

parser = HDFCDinersParser("Test Account")
transactions = parser.parse(content)

print(f"Found {len(transactions)} transactions")
for txn in transactions[:5]:  # Show first 5
    print(txn)
EOF
```

## Getting Help

If you're still stuck, share the following:

1. **Output of debug script:**
```bash
python debug_pdf.py your_file.pdf hdfc_diners > /tmp/debug_output.txt 2>&1
cat /tmp/debug_output.txt
```

2. **First 50 lines of extracted text:**
```bash
head -n 50 /tmp/extracted_text.txt
```

3. **Sample transaction lines** (manually type 2-3 lines as they appear in your statement)

4. **Bank type and statement period**

With this info, I can quickly adjust the parser for your specific format!

## Quick Fixes You Can Try

### Fix 1: Try Different Bank Types

Maybe the format is slightly different:
```bash
# Try generic parser
python debug_pdf.py your_file.pdf generic

# Try HDFC bank parser (not Diners)
python debug_pdf.py your_file.pdf hdfc
```

### Fix 2: Adjust HDFC Diners Parser

If you see the section marker is different, edit `/app/backend/pdf_parsers.py`:

Find line ~54:
```python
if 'Domestic Transactions' in line:
```

Change to match your PDF:
```python
if 'Transaction Details' in line:  # or whatever your PDF says
```

### Fix 3: Adjust Amount Pattern

If amounts don't have commas (e.g., 850.50 instead of 8,50.50):

Find line ~71:
```python
amount_regex = re.compile(r'(\d{1,3}(?:,\d{3})*\.\d{2})(\s*Cr)?$')
```

Change to:
```python
amount_regex = re.compile(r'(\d+\.\d{2})(\s*Cr)?$')
```

Then restart backend:
```bash
sudo supervisorctl restart backend
```

## Live Debugging Session

For real-time debugging:

```bash
# Terminal 1: Watch logs
tail -f /var/log/supervisor/backend.err.log

# Terminal 2: Test upload
curl -X POST \
  "${REACT_APP_BACKEND_URL}/api/upload-statement?account_id=YOUR_ACCOUNT_ID&bank_name=hdfc_diners" \
  -F "file=@/tmp/your_statement.pdf"
```

Watch Terminal 1 for detailed logs!

## Emergency Workaround: CSV Export

If PDF parsing is too complex, most banks let you download CSV:

1. Log into your bank portal
2. Download statement as CSV/Excel
3. Convert to required format:
   ```csv
   date,description,amount,type
   2025-01-15,Grocery,850.50,debit
   2025-01-16,Salary,50000.00,credit
   ```
4. Upload via the Upload page

This is 100% reliable and often faster than fixing PDF parsing!
