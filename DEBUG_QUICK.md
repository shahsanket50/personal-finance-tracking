# 🔧 Quick Debugging Guide for PDF Upload Issues

## 🚀 3 Ways to Debug

### Method 1: Web-Based Debugger (Easiest!) ⭐

**Access:** `https://money-insights-82.preview.emergentagent.com/debug.html`

**Steps:**
1. Open the debug page in your browser
2. Select your bank type (HDFC Diners, etc.)
3. Upload your PDF
4. Click "Debug PDF"
5. See:
   - Extracted text from PDF
   - All parsed transactions
   - Any errors

**Perfect for:** Quick testing without command line access

---

### Method 2: Backend Logs (Real-time)

```bash
# Open terminal and run:
tail -f /var/log/supervisor/backend.err.log
```

Then upload your PDF through the regular Upload page.

**You'll see:**
- "Processing PDF: [filename]" 
- "Using parser: HDFCDinersParser"
- "Parsed X transactions"
- Any errors or warnings

**Perfect for:** Seeing what's happening in real-time

---

### Method 3: Debug Script (Most Detailed)

```bash
cd /app/backend
python debug_pdf.py /path/to/your/statement.pdf hdfc_diners
```

**Outputs:**
- `/tmp/extracted_text.txt` - Full PDF text
- `/tmp/parsed_transactions.json` - Parsed data
- Console output with step-by-step details

**Perfect for:** Deep debugging and understanding parser behavior

---

## 🐞 Common Issues

### Issue: "No transactions found"

**Quick Fix:**
1. Try web debugger to see extracted text
2. Check if "Domestic Transactions" section exists
3. Try different bank type (Generic, HDFC, etc.)

**Common causes:**
- Wrong bank type selected
- Different section headers in your PDF
- Scanned PDF (image-based, not text)

---

### Issue: "Wrong amounts or dates"

**Quick Fix:**
1. Check extracted text format
2. Look at date format (DD/MM/YYYY vs DD-MM-YYYY)
3. Check amount format (1,234.56 vs 1234.56)

**Solution:** May need to adjust parser regex patterns

---

### Issue: "Duplicate transactions"

This is **GOOD**! The system automatically skips duplicates when importing.

---

## 👥 Getting Help

If still stuck, share:

1. **Output from web debugger** (screenshot or copy text)
2. **First 20 lines** of your PDF statement (manually type or screenshot - hide sensitive info)
3. **Bank name** and statement type

With this info, I can quickly fix the parser! 🚀

---

## 🛠️ Emergency Workaround

If PDF parsing is too complex:

1. Download statement as **CSV or Excel** from your bank
2. Convert to this format:
   ```csv
   date,description,amount,type
   2025-01-15,Grocery Store,850.50,debit
   2025-01-16,Salary,50000.00,credit
   ```
3. Upload via Upload page - 100% reliable!

---

## ✅ Next Steps

1. **Try the web debugger first**: Open `/debug.html` and upload your PDF
2. **Share results** if it's not working
3. **I'll adjust the parser** for your specific format
4. **Test again** - should work perfectly!

The web debugger will show you exactly what's being extracted and parsed, making it super easy to identify issues! 🚀
