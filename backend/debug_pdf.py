#!/usr/bin/env python3
"""
PDF Parser Debugger
Usage: python debug_pdf.py <path_to_pdf> <bank_type>
Example: python debug_pdf.py ~/diners_statement.pdf hdfc_diners
"""

import sys
sys.path.insert(0, '/app/backend')

from pdf_parsers import get_parser
import json

def debug_pdf(pdf_path, bank_type='hdfc_diners'):
    print("="*80)
    print(f"PDF Parser Debugger")
    print("="*80)
    print(f"File: {pdf_path}")
    print(f"Bank Type: {bank_type}")
    print("="*80)
    
    # Read PDF file
    try:
        with open(pdf_path, 'rb') as f:
            pdf_content = f.read()
        print(f"✅ PDF file loaded successfully ({len(pdf_content)} bytes)")
    except Exception as e:
        print(f"❌ Error reading PDF: {e}")
        return
    
    # Get parser
    parser = get_parser(bank_type, "Test Account")
    print(f"✅ Using parser: {parser.__class__.__name__}")
    print("="*80)
    
    # Extract text first
    print("\n📄 STEP 1: Extracting text from PDF...")
    print("-"*80)
    try:
        text = parser.extract_text(pdf_content)
        print(f"✅ Text extracted: {len(text)} characters")
        print("\n📝 First 1000 characters:")
        print("-"*80)
        print(text[:1000])
        print("-"*80)
        
        # Save full text to file for review
        with open('/tmp/extracted_text.txt', 'w') as f:
            f.write(text)
        print("\n✅ Full text saved to: /tmp/extracted_text.txt")
        
    except Exception as e:
        print(f"❌ Error extracting text: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Parse transactions
    print("\n💰 STEP 2: Parsing transactions...")
    print("-"*80)
    try:
        transactions = parser.parse(pdf_content)
        print(f"✅ Found {len(transactions)} transactions\n")
        
        if transactions:
            print("📊 Transaction Details:")
            print("-"*80)
            for i, txn in enumerate(transactions, 1):
                print(f"\n{i}. Date: {txn['date']}")
                print(f"   Description: {txn['description']}")
                print(f"   Amount: ₹{txn['amount']}")
                print(f"   Type: {txn['type']}")
                print(f"   Account: {txn['account']}")
            
            # Save to JSON
            with open('/tmp/parsed_transactions.json', 'w') as f:
                json.dump(transactions, f, indent=2)
            print("\n✅ Transactions saved to: /tmp/parsed_transactions.json")
        else:
            print("⚠️  No transactions found!")
            print("\nPossible reasons:")
            print("1. PDF format doesn't match the expected pattern")
            print("2. Section markers not found (e.g., 'Domestic Transactions')")
            print("3. Date format is different than expected")
            print("4. Amount format is not being recognized")
            
    except Exception as e:
        print(f"❌ Error parsing transactions: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n" + "="*80)
    print("Debugging complete!")
    print("="*80)
    print("\nFiles created:")
    print("  /tmp/extracted_text.txt - Full PDF text content")
    print("  /tmp/parsed_transactions.json - Parsed transaction data")
    print("\nNext steps:")
    print("  1. Review /tmp/extracted_text.txt to see what was extracted")
    print("  2. Check if section markers match your PDF")
    print("  3. Verify date and amount formats")
    print("  4. Share the extracted text if you need help adjusting the parser")
    print("="*80)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_pdf.py <path_to_pdf> [bank_type]")
        print("\nSupported bank types:")
        print("  - hdfc_diners (default)")
        print("  - hdfc")
        print("  - slice")
        print("  - kotak")
        print("  - sbi")
        print("  - generic")
        print("\nExample:")
        print("  python debug_pdf.py ~/Downloads/diners_statement.pdf hdfc_diners")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    bank_type = sys.argv[2] if len(sys.argv) > 2 else 'hdfc_diners'
    
    debug_pdf(pdf_path, bank_type)
