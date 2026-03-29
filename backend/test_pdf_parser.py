# Test PDF Parsing Script
import sys
sys.path.insert(0, '/app/backend')

from pdf_parsers import HDFCDinersParser, HDFCBankParser, SliceBankParser, KotakBankParser, SBIBankParser, GenericParser
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

def create_hdfc_diners_test_pdf():
    """Create a test PDF with HDFC Diners format"""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    
    # Add title
    c.drawString(100, 750, "HDFC Diners Club Credit Card Statement")
    c.drawString(100, 730, "Statement Period: January 2025")
    
    # Add Domestic Transactions section
    c.drawString(100, 700, "Domestic Transactions")
    
    # Add transactions
    y_pos = 670
    transactions = [
        "15/01/2024 SWIGGY FOOD ORDER 850.50",
        "16/01/2024 FLIPKART SHOPPING 2500.00",
        "17/01/2024 PAYMENT RECEIVED 5000.00 Cr",
        "18/01/2024 ZOMATO DELIVERY 450.75",
        "20/01/2024 AMAZON INDIA 1200.00",
    ]
    
    for txn in transactions:
        c.drawString(100, y_pos, txn)
        y_pos -= 20
    
    # Add end marker
    c.drawString(100, y_pos - 30, "Reward Points Summary")
    
    c.save()
    buffer.seek(0)
    return buffer.read()

def create_hdfc_bank_test_pdf():
    """Create a test PDF with HDFC Bank format"""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    
    c.drawString(100, 750, "HDFC Bank Account Statement")
    c.drawString(100, 730, "Account: XXXX-XXXX-1234")
    
    y_pos = 700
    transactions = [
        "15/01/24 UPI-AMAZON-PAY-BILL-PAYMENT 250.00",
        "16/01/24 SALARY CREDIT JAN 2024 75000.00",
        "17/01/24 IMPS-TRANSFER-TO-FRIEND 1000.00",
    ]
    
    for txn in transactions:
        c.drawString(100, y_pos, txn)
        y_pos -= 20
    
    c.save()
    buffer.seek(0)
    return buffer.read()

def test_parsers():
    print("Testing HDFC Diners Parser...")
    pdf_content = create_hdfc_diners_test_pdf()
    parser = HDFCDinersParser("Test HDFC Diners")
    transactions = parser.parse(pdf_content)
    print(f"Found {len(transactions)} transactions:")
    for txn in transactions:
        print(f"  {txn['date']} - {txn['description']} - ₹{txn['amount']} ({txn['type']})")
    print()
    
    print("Testing HDFC Bank Parser...")
    pdf_content = create_hdfc_bank_test_pdf()
    parser = HDFCBankParser("Test HDFC Bank")
    transactions = parser.parse(pdf_content)
    print(f"Found {len(transactions)} transactions:")
    for txn in transactions:
        print(f"  {txn['date']} - {txn['description']} - ₹{txn['amount']} ({txn['type']})")
    print()

if __name__ == "__main__":
    test_parsers()
