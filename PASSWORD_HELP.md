# 🔒 Your PDF is Password Protected!

## What This Means

Your HDFC Diners statement PDF (`0036XXXXXXXXXX06_22-03-2026_389.pdf`) is encrypted with a password. This is very common with bank statements for security.

## How to Find Your PDF Password

HDFC typically uses one of these passwords:

### Most Common:
1. **Last 4 digits of your card number** (e.g., 3006, 4567)
2. **Your Date of Birth** in DDMMYYYY format (e.g., 15031990)

### Less Common:
3. **First 4 letters of surname + DOB** (e.g., SANK3011)
4. **PAN number** (without spaces)
5. **Customer ID**

## How to Upload with Password

I've updated the app to support password-protected PDFs!

### Option 1: Web Debugger (Recommended)

1. Open: `https://money-insights-82.preview.emergentagent.com/debug.html`
2. Select "HDFC Diners Credit Card"
3. **Enter your password** (try last 4 digits first)
4. Upload PDF
5. See if it works!

### Option 2: Upload Page

1. Go to Upload page in the app
2. Select your account
3. Select "HDFC Diners Credit Card"
4. **Enter PDF password** in the new password field
5. Upload!

## Still Can't Find Password?

### Method 1: Check HDFC Email
When HDFC emails you the statement, they usually mention the password in the email body.

### Method 2: HDFC NetBanking
1. Login to HDFC NetBanking
2. Go to "Statements"
3. The password is usually shown when you download

### Method 3: Call HDFC Customer Care
They can tell you what password format they use for PDFs.

### Method 4: Remove Password (Easiest!)

If you have Adobe Acrobat or online tools:

1. **Online Tool** (free):
   - Go to: https://www.ilovepdf.com/unlock_pdf
   - Upload your PDF
   - Enter the password
   - Download unlocked PDF
   - Upload to MoneyInsights

2. **Adobe Acrobat**:
   - Open PDF
   - Enter password
   - File → Properties → Security → No Security
   - Save as new PDF

### Method 5: Use CSV Instead

If PDF is too complex:

1. Login to HDFC DiNers portal
2. Download statement as **Excel/CSV** (usually password-free!)
3. Convert to format:
   ```csv
   date,description,amount,type
   2025-01-15,Restaurant,850.50,debit
   2025-01-16,Payment,5000.00,credit
   ```
4. Upload via Upload page - 100% works!

## Test Your Password

Try these passwords in order:

```
1. XXXX  (replace with last 4 digits of card)
2. DDMMYYYY (your date of birth)
3. Check your HDFC email
```

## Next Steps

1. **Find your password** using methods above
2. **Open debug page**: https://money-insights-82.preview.emergentagent.com/debug.html
3. **Enter password** and upload
4. **Share screenshot** of results - I'll help parse the transactions!

The app is now ready to handle password-protected PDFs. Just need the correct password! 🚀
