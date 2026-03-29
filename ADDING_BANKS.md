# Adding Your Custom Bank Parsers

This guide will help you integrate your remaining bank PDF parsers into the MoneyInsights application.

## Quick Start

### Step 1: Review Current Parser Structure

All parsers are located in `/app/backend/pdf_parsers.py`. Each parser:

1. Inherits from `BankStatementParser`
2. Implements a `parse(pdf_blob: bytes)` method
3. Returns a list of transaction dictionaries

### Step 2: Transaction Dictionary Format

Each transaction must have these fields:

```python
{
    'date': '2024-01-15',           # YYYY-MM-DD format
    'description': 'Amazon Purchase', # Transaction description
    'amount': 1250.50,              # Float value (always positive)
    'type': 'debit',                # 'credit' or 'debit'
    'account': 'Card Name'          # Account name (from self.account_name)
}
```

### Step 3: Create Your Parser

Add your parser class to `/app/backend/pdf_parsers.py`:

```python
class YourBankParser(BankStatementParser):
    """Parser for Your Bank statements"""
    
    def parse(self, pdf_blob: bytes) -> List[Dict]:
        # Step 1: Extract text from PDF
        text = self.extract_text(pdf_blob)
        transactions = []
        
        # Step 2: Define your regex pattern
        # Example: Date Description Amount Type
        pattern = re.compile(r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+(\d+\.\d{2})\s+(Dr|Cr)', re.MULTILINE)
        
        # Step 3: Extract transactions
        for match in pattern.finditer(text):
            date_str = match.group(1)
            description = match.group(2).strip()
            amount = float(match.group(3))
            txn_type = match.group(4)
            
            # Step 4: Normalize date
            normalized_date = self.normalize_date(date_str, '%d/%m/%Y')
            
            # Step 5: Determine transaction type
            transaction_type = 'credit' if txn_type == 'Cr' else 'debit'
            
            # Step 6: Create transaction dict
            transactions.append({
                'date': normalized_date,
                'description': description,
                'amount': amount,
                'type': transaction_type,
                'account': self.account_name
            })
        
        print(f"Your Bank: Parsed {len(transactions)} transactions")
        return transactions
```

### Step 4: Register Your Parser

Add your parser to the `get_parser()` function at the bottom of `pdf_parsers.py`:

```python
def get_parser(bank_name: str, account_name: str) -> BankStatementParser:
    """Factory function to get appropriate parser based on bank name"""
    bank_name_lower = bank_name.lower()
    
    # ... existing parsers ...
    
    elif 'yourbank' in bank_name_lower:  # Add your condition
        return YourBankParser(account_name)
    else:
        return GenericParser(account_name)
```

### Step 5: Update Frontend Dropdown

Edit `/app/frontend/src/pages/Upload.js` and add your bank to the Select options:

```jsx
<SelectContent>
  <SelectItem value="generic">Generic/Auto-detect</SelectItem>
  <SelectItem value="hdfc_diners">HDFC Diners Credit Card</SelectItem>
  <SelectItem value="hdfc">HDFC Bank</SelectItem>
  <SelectItem value="slice">Slice Card</SelectItem>
  <SelectItem value="kotak">Kotak Bank</SelectItem>
  <SelectItem value="sbi">SBI Bank</SelectItem>
  <SelectItem value="yourbank">Your Bank Name</SelectItem>  {/* Add this */}
</SelectContent>
```

Also update the supported banks list in the instructions section.

### Step 6: Test Your Parser

Create a test in `/app/backend/test_pdf_parser.py`:

```python
def test_your_bank():
    # Create or load a sample PDF
    with open('path/to/your/sample.pdf', 'rb') as f:
        pdf_content = f.read()
    
    parser = YourBankParser("Test Your Bank")
    transactions = parser.parse(pdf_content)
    
    print(f"Found {len(transactions)} transactions:")
    for txn in transactions:
        print(f"  {txn['date']} - {txn['description']} - ₹{txn['amount']} ({txn['type']})")

if __name__ == "__main__":
    test_your_bank()
```

Run the test:
```bash
cd /app/backend
python test_pdf_parser.py
```

### Step 7: Restart Backend

```bash
sudo supervisorctl restart backend
```

## Converting Your Google Apps Script Code

### Key Differences:

1. **PDF Text Extraction**
   - Google Apps Script: `CloudmersiveClient.pdfToText(pdfBlob)`
   - Python: `self.extract_text(pdf_blob)` (uses pdfplumber)

2. **File Handling**
   - GAS: `DriveApp.getFilesByName(filename)`
   - Python: Direct bytes object passed to `parse()`

3. **Regex**
   - GAS: `var dateRegex = /^(\d{2}\/\d{2}\/\d{4})/;`
   - Python: `date_regex = re.compile(r'^(\d{2}/\d{2}/\d{4})')`

4. **String Methods**
   - GAS: `text.indexOf('Domestic Transactions')`
   - Python: `'Domestic Transactions' in text`

5. **Array Methods**
   - GAS: `lines.slice(startIdx, endIdx)`
   - Python: `lines[start_idx:end_idx]`

### Example Conversion:

**Google Apps Script:**
```javascript
var dateMatch = dateRegex.exec(line);
if (dateMatch) {
  var date = dateMatch[1].split(' ')[0];
  var dateParts = date.split('/');
  var normalizedDate = dateParts[2] + '-' + dateParts[1] + '-' + dateParts[0];
}
```

**Python:**
```python
date_match = date_regex.match(line)
if date_match:
    date_str = date_match.group(1).split(' ')[0]
    normalized_date = self.normalize_date(date_str, '%d/%m/%Y')
```

## Common Patterns

### Pattern 1: Section-Based Parsing (HDFC Diners Style)

```python
# Find start and end markers
start_idx = -1
end_idx = len(lines)

for i, line in enumerate(lines):
    if 'Transaction Section' in line:
        start_idx = i + 1
    if start_idx != -1 and 'End Section' in line:
        end_idx = i
        break

txn_lines = lines[start_idx:end_idx]
```

### Pattern 2: Line-by-Line with State (HDFC Diners Style)

```python
current_transaction = None
transactions = []

for line in lines:
    if date_regex.match(line):
        # New transaction starts
        if current_transaction:
            transactions.append(current_transaction)
        current_transaction = {...}
    elif current_transaction:
        # Continue building current transaction
        current_transaction['description'] += ' ' + line
```

### Pattern 3: Single Line per Transaction

```python
pattern = re.compile(r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+(\d+\.\d{2})', re.MULTILINE)

for match in pattern.finditer(text):
    transactions.append({
        'date': normalize_date(match.group(1)),
        'description': match.group(2).strip(),
        'amount': float(match.group(3)),
        'type': determine_type(match.group(2)),
        'account': self.account_name
    })
```

### Pattern 4: Table-Like Format

```python
# Skip header, process rows
for line in lines[header_row+1:]:
    columns = line.split('|')  # or use fixed-width parsing
    if len(columns) >= 4:
        transactions.append({
            'date': normalize_date(columns[0].strip()),
            'description': columns[1].strip(),
            'amount': float(columns[2].strip()),
            'type': 'credit' if 'Cr' in columns[3] else 'debit',
            'account': self.account_name
        })
```

## Tips for Success

1. **Print Debug Info**: Use `print()` statements liberally during development
2. **Handle Edge Cases**: Empty amounts, missing dates, special characters
3. **Test with Multiple Statements**: Different months may have variations
4. **Amount Formats**: Handle both `1,234.56` and `1234.56`
5. **Date Formats**: Use `normalize_date()` helper for consistency
6. **Credit Detection**: Look for keywords like "CREDIT", "DEPOSIT", "Cr" suffix

## Example: Converting Your HDFC Diners Parser

Your original code is already well-structured! Here's how it maps:

**Your GAS Code:**
```javascript
function parseTransactionsFromHDFCDinersPDF(pdfBlob) {
  var text = CloudmersiveClient.pdfToText(pdfBlob);
  var lines = text.split('\n');
  // ... rest of your logic
}
```

**Already Converted in `pdf_parsers.py`:**
```python
class HDFCDinersParser(BankStatementParser):
    def parse(self, pdf_blob: bytes) -> List[Dict]:
        text = self.extract_text(pdf_blob)
        lines = text.split('\n')
        # ... same logic structure
```

The structure is identical! Just syntax differences.

## Need Help?

If you have a parser that's not working:

1. Share the PDF text extraction output
2. Provide sample transaction lines
3. Describe the expected format
4. I'll help you write the regex and parsing logic

## Next Steps

You mentioned you have "few more" parsers. Please share:

1. **Bank names** you want to add
2. **Sample transaction formats** from the PDFs
3. **Your existing GAS code** for those parsers

I'll help you convert them quickly!
