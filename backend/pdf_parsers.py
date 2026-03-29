import re
from datetime import datetime
from typing import List, Dict, Optional
import pdfplumber
import io

class BankStatementParser:
    """Base class for bank statement parsers"""
    
    def __init__(self, account_name: str):
        self.account_name = account_name
    
    def parse(self, pdf_blob: bytes, password: str = None) -> List[Dict]:
        """Parse PDF and return list of transactions"""
        raise NotImplementedError("Subclasses must implement parse method")
    
    def extract_text(self, pdf_blob: bytes, password: str = None) -> str:
        """Extract text from PDF using pdfplumber"""
        text_content = ""
        pdf_file = io.BytesIO(pdf_blob)
        
        # Try without password first, then with common passwords if provided
        passwords_to_try = [''] if not password else ['', password]
        
        last_error = None
        for pwd in passwords_to_try:
            try:
                with pdfplumber.open(pdf_file, password=pwd) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text_content += page_text + "\n"
                return text_content
            except Exception as e:
                last_error = e
                pdf_file.seek(0)  # Reset for next attempt
                continue
        
        # If all attempts failed, raise the last error
        if 'PDFPasswordIncorrect' in str(last_error.__class__.__name__):
            raise Exception("PDF is password protected. Please provide the password (usually DOB as DDMMYYYY or last 4 digits of card)")
        raise last_error
    
    def normalize_date(self, date_str: str, date_format: str) -> str:
        """Convert date string to YYYY-MM-DD format"""
        try:
            dt = datetime.strptime(date_str, date_format)
            return dt.strftime('%Y-%m-%d')
        except Exception as e:
            print(f"Error parsing date {date_str}: {e}")
            return date_str

class HDFCDinersParser(BankStatementParser):
    """Parser for HDFC Diners Credit Card statements"""
    
    def parse(self, pdf_blob: bytes, password: str = None) -> List[Dict]:
        text = self.extract_text(pdf_blob, password)
        
        if not text or not text.strip():
            print("No text extracted from PDF")
            return []
        
        transactions = []
        
        # New pattern for HDFC Diners format:
        # 24/02/2026| 08:28 URBANCLAPNOIDA + 5 C 244.00 l
        # Pattern breakdown:
        # - Date: DD/MM/YYYY
        # - Pipe separator: |
        # - Time (optional): HH:MM
        # - Description: merchant name
        # - Indicators: + or - symbols, numbers
        # - C: charge indicator
        # - Amount: with or without comma
        # - End marker: l or other
        
        # Match lines with date| format
        pattern = re.compile(
            r'(\d{2}/\d{2}/\d{4})\|'  # Date with pipe
            r'\s*(?:\d{2}:\d{2}\s+)?'  # Optional time
            r'(.+?)'  # Description
            r'\s+C\s+'  # C indicator (charge)
            r'([\d,]+\.?\d*)'  # Amount with optional decimals
            r'\s*l?'  # Optional l at end
        )
        
        for match in pattern.finditer(text):
            date_str = match.group(1)
            description = match.group(2).strip()
            amount_str = match.group(3).replace(',', '')
            
            # Normalize date
            normalized_date = self.normalize_date(date_str, '%d/%m/%Y')
            
            # Parse amount
            try:
                amount = float(amount_str)
            except:
                continue
            
            # Determine if it's a credit (payment/refund) or debit (charge)
            # In HDFC Diners, most transactions are debits (charges)
            # Credits are usually marked as "PAYMENT" or have specific indicators
            is_credit = any(keyword in description.upper() for keyword in [
                'PAYMENT', 'CREDIT', 'REFUND', 'REVERSAL', 'CASHBACK'
            ])
            
            transaction_type = 'credit' if is_credit else 'debit'
            
            # Clean up description - remove extra symbols and numbers at end
            # Remove patterns like "+ 5", "- 40 +", etc.
            description = re.sub(r'\s+[+-]\s*\d+\s*[+-]?\s*$', '', description)
            description = description.strip()
            
            transactions.append({
                'date': normalized_date,
                'description': description,
                'amount': amount,
                'type': transaction_type,
                'account': self.account_name
            })
        
        print(f"HDFC Diners: Parsed {len(transactions)} transactions")
        return transactions

class HDFCBankParser(BankStatementParser):
    """Parser for HDFC Bank account statements"""
    
    def parse(self, pdf_blob: bytes, password: str = None) -> List[Dict]:
        text = self.extract_text(pdf_blob, password)
        transactions = []
        
        # Pattern: DD/MM/YY DESCRIPTION AMOUNT
        # Example: 15/01/24 UPI-AMAZON-PAY-BILL-PAYMENT 250.00
        pattern = re.compile(r'(\d{2}/\d{2}/\d{2})\s+(.+?)\s+(\d+\.\d{2})\s*(Cr|Dr)?$', re.MULTILINE)
        
        for match in pattern.finditer(text):
            date_str = match.group(1)
            description = match.group(2).strip()
            amount = float(match.group(3))
            txn_type = match.group(4)
            
            # Normalize date from DD/MM/YY to YYYY-MM-DD
            normalized_date = self.normalize_date(date_str, '%d/%m/%y')
            
            # Determine transaction type
            if 'SALARY' in description.upper() or 'CREDIT' in description.upper() or txn_type == 'Cr':
                transaction_type = 'credit'
            else:
                transaction_type = 'debit'
            
            transactions.append({
                'date': normalized_date,
                'description': description,
                'amount': amount,
                'type': transaction_type,
                'account': self.account_name
            })
        
        print(f"HDFC Bank: Parsed {len(transactions)} transactions")
        return transactions

class SliceBankParser(BankStatementParser):
    """Parser for Slice Bank statements"""
    
    def parse(self, pdf_blob: bytes, password: str = None) -> List[Dict]:
        text = self.extract_text(pdf_blob, password)
        transactions = []
        
        # Pattern: DD-MM-YYYY|Description|Category|Amount
        # Example: 12-01-2024|Zomato|Food|850.50
        pattern = re.compile(r'(\d{2}-\d{2}-\d{4})\|(.*?)\|(.*?)\|(\d+\.\d{2})', re.MULTILINE)
        
        for match in pattern.finditer(text):
            date_str = match.group(1)
            description = match.group(2).strip()
            category = match.group(3).strip()
            amount = float(match.group(4))
            
            # Normalize date from DD-MM-YYYY to YYYY-MM-DD
            normalized_date = self.normalize_date(date_str, '%d-%m-%Y')
            
            # Determine transaction type
            if 'REPAYMENT' in description.upper() or category.upper() == 'INCOME':
                transaction_type = 'credit'
            else:
                transaction_type = 'debit'
            
            transactions.append({
                'date': normalized_date,
                'description': f"{description} ({category})",
                'amount': amount,
                'type': transaction_type,
                'account': self.account_name
            })
        
        print(f"Slice Bank: Parsed {len(transactions)} transactions")
        return transactions

class KotakBankParser(BankStatementParser):
    """Parser for Kotak Bank statements"""
    
    def parse(self, pdf_blob: bytes, password: str = None) -> List[Dict]:
        text = self.extract_text(pdf_blob, password)
        transactions = []
        
        # Pattern: Date: DD Mon YYYY, Narration: XXX, Amount: XXX, Type: DR/CR
        pattern = re.compile(r'Date:\s*(\d{1,2}\s+\w+\s+\d{4}),\s*Narration:\s*(.+?),\s*Amount:\s*(\d+\.\d{2}),\s*Type:\s*(DR|CR)', re.MULTILINE)
        
        for match in pattern.finditer(text):
            date_str = match.group(1)
            description = match.group(2).strip()
            amount = float(match.group(3))
            txn_type = match.group(4)
            
            # Normalize date from "DD Mon YYYY" to YYYY-MM-DD
            normalized_date = self.normalize_date(date_str, '%d %b %Y')
            
            transaction_type = 'credit' if txn_type == 'CR' else 'debit'
            
            transactions.append({
                'date': normalized_date,
                'description': description,
                'amount': amount,
                'type': transaction_type,
                'account': self.account_name
            })
        
        print(f"Kotak Bank: Parsed {len(transactions)} transactions")
        return transactions

class SBIBankParser(BankStatementParser):
    """Parser for SBI Bank statements"""
    
    def parse(self, pdf_blob: bytes, password: str = None) -> List[Dict]:
        text = self.extract_text(pdf_blob, password)
        transactions = []
        
        # Pattern: DD/MM/YYYY To/By/DESCRIPTION AMOUNT Dr/Cr
        pattern = re.compile(r'(\d{2}/\d{2}/\d{4})\s+(To|By)/(.+?)\s+(\d+\.\d{2})\s+(Dr|Cr)', re.MULTILINE)
        
        for match in pattern.finditer(text):
            date_str = match.group(1)
            direction = match.group(2)
            description = match.group(3).strip()
            amount = float(match.group(4))
            txn_type = match.group(5)
            
            # Normalize date from DD/MM/YYYY to YYYY-MM-DD
            normalized_date = self.normalize_date(date_str, '%d/%m/%Y')
            
            transaction_type = 'credit' if txn_type == 'Cr' or direction == 'By' else 'debit'
            
            transactions.append({
                'date': normalized_date,
                'description': description,
                'amount': amount,
                'type': transaction_type,
                'account': self.account_name
            })
        
        print(f"SBI Bank: Parsed {len(transactions)} transactions")
        return transactions

class GenericParser(BankStatementParser):
    """Generic parser for unknown statement formats"""
    
    def parse(self, pdf_blob: bytes, password: str = None) -> List[Dict]:
        text = self.extract_text(pdf_blob, password)
        transactions = []
        
        # Try multiple common date formats and patterns
        patterns = [
            # Pattern 1: Mon DD, YYYY - Description - Type - Category - $Amount
            re.compile(r'(\w+\s+\d{1,2},\s+\d{4})\s+-\s+(.+?)\s+-\s+(Income|Expense|Transfer)\s+-\s+(.+?)\s+-\s+\$?([\d,]+\.\d{2})', re.MULTILINE),
            # Pattern 2: DD/MM/YYYY Description Amount
            re.compile(r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([\d,]+\.\d{2})', re.MULTILINE),
            # Pattern 3: YYYY-MM-DD Description Amount
            re.compile(r'(\d{4}-\d{2}-\d{2})\s+(.+?)\s+([\d,]+\.\d{2})', re.MULTILINE),
        ]
        
        for pattern in patterns:
            matches = list(pattern.finditer(text))
            if matches:
                for match in matches:
                    try:
                        if len(match.groups()) >= 3:
                            date_str = match.group(1)
                            description = match.group(2).strip()
                            
                            # Try to parse date with multiple formats
                            normalized_date = None
                            for fmt in ['%b %d, %Y', '%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y']:
                                try:
                                    normalized_date = self.normalize_date(date_str, fmt)
                                    break
                                except:
                                    continue
                            
                            if not normalized_date:
                                continue
                            
                            # Determine type from description or explicit type field
                            if len(match.groups()) >= 5:
                                txn_type_str = match.group(3)
                                amount = float(match.group(5).replace(',', '').replace('$', ''))
                                transaction_type = 'credit' if txn_type_str == 'Income' else 'debit'
                            else:
                                amount = float(match.group(3).replace(',', '').replace('$', ''))
                                # Infer type from description
                                if any(word in description.upper() for word in ['SALARY', 'PAYCHECK', 'DEPOSIT', 'CREDIT', 'REFUND']):
                                    transaction_type = 'credit'
                                else:
                                    transaction_type = 'debit'
                            
                            transactions.append({
                                'date': normalized_date,
                                'description': description,
                                'amount': amount,
                                'type': transaction_type,
                                'account': self.account_name
                            })
                    except Exception as e:
                        print(f"Error parsing transaction: {e}")
                        continue
                
                if transactions:
                    break
        
        print(f"Generic Parser: Parsed {len(transactions)} transactions")
        return transactions

def get_parser(bank_name: str, account_name: str) -> BankStatementParser:
    """Factory function to get appropriate parser based on bank name"""
    bank_name_lower = bank_name.lower()
    
    if 'hdfc' in bank_name_lower and 'diners' in bank_name_lower:
        return HDFCDinersParser(account_name)
    elif 'hdfc' in bank_name_lower:
        return HDFCBankParser(account_name)
    elif 'slice' in bank_name_lower:
        return SliceBankParser(account_name)
    elif 'kotak' in bank_name_lower:
        return KotakBankParser(account_name)
    elif 'sbi' in bank_name_lower:
        return SBIBankParser(account_name)
    else:
        return GenericParser(account_name)
