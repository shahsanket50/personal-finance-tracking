import re
from datetime import datetime
from typing import List, Dict, Optional
import pdfplumber
import io

class SimplePDFParser:
    """Simple, flexible PDF parser that uses regex patterns"""
    
    def __init__(self, account_name: str, custom_pattern: Dict = None):
        self.account_name = account_name
        self.custom_pattern = custom_pattern or {}
    
    def extract_text(self, pdf_blob: bytes, password: str = None) -> str:
        """Extract text from PDF"""
        text_content = ""
        pdf_file = io.BytesIO(pdf_blob)
        
        passwords_to_try = [''] if not password else ['', password]
        
        for pwd in passwords_to_try:
            try:
                with pdfplumber.open(pdf_file, password=pwd) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text_content += page_text + "\n"
                return text_content
            except Exception as e:
                pdf_file.seek(0)
                continue
        
        raise Exception("PDF is password protected or cannot be read")
    
    def parse(self, pdf_blob: bytes, password: str = None) -> List[Dict]:
        """Parse PDF using custom pattern or generic pattern"""
        text = self.extract_text(pdf_blob, password)
        
        if self.custom_pattern and 'regex' in self.custom_pattern:
            return self.parse_with_custom_pattern(text)
        else:
            return self.parse_generic(text)
    
    def parse_with_custom_pattern(self, text: str) -> List[Dict]:
        """Parse using saved custom regex pattern"""
        transactions = []
        pattern_str = self.custom_pattern.get('regex')
        
        if not pattern_str:
            return []
        
        try:
            pattern = re.compile(pattern_str, re.MULTILINE)
            
            for match in pattern.finditer(text):
                groups = match.groups()
                
                # Map groups based on saved configuration
                mapping = self.custom_pattern.get('mapping', {})
                
                date_str = groups[mapping.get('date', 0)]
                description = groups[mapping.get('description', 1)]
                amount_str = groups[mapping.get('amount', 2)].replace(',', '')
                
                # Normalize date
                date_format = self.custom_pattern.get('date_format', '%d/%m/%Y')
                try:
                    dt = datetime.strptime(date_str, date_format)
                    normalized_date = dt.strftime('%Y-%m-%d')
                except:
                    normalized_date = date_str
                
                # Determine type
                txn_type = 'debit'
                if mapping.get('type') is not None:
                    type_indicator = groups[mapping.get('type')]
                    credit_indicators = self.custom_pattern.get('credit_indicators', ['Cr', 'CREDIT', 'PAYMENT'])
                    txn_type = 'credit' if any(ind in type_indicator.upper() for ind in credit_indicators) else 'debit'
                else:
                    # Check description for credit keywords
                    if any(kw in description.upper() for kw in ['PAYMENT', 'CREDIT', 'REFUND', 'REVERSAL']):
                        txn_type = 'credit'
                
                transactions.append({
                    'date': normalized_date,
                    'description': description.strip(),
                    'amount': float(amount_str),
                    'type': txn_type,
                    'account': self.account_name
                })
        except Exception as e:
            print(f"Error parsing with custom pattern: {e}")
            return []
        
        return transactions
    
    def parse_generic(self, text: str) -> List[Dict]:
        """Generic parser - tries common patterns"""
        transactions = []
        
        # Try multiple common patterns
        patterns = [
            # Pattern 1: DD/MM/YYYY| ... C amount l (HDFC Diners style)
            r'(\d{2}/\d{2}/\d{4})\|\s*(?:\d{2}:\d{2}\s+)?(.+?)\s+C\s+([\d,]+\.?\d*)\s*l?',
            
            # Pattern 2: DD/MM/YYYY description amount Cr/Dr
            r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([\d,]+\.\d{2})\s*(Cr|Dr)?',
            
            # Pattern 3: DD-MM-YYYY|description|category|amount
            r'(\d{2}-\d{2}-\d{4})\|(.+?)\|(.+?)\|([\d,]+\.\d{2})',
            
            # Pattern 4: Date: DD Mon YYYY, Narration: XXX, Amount: XXX, Type: DR/CR
            r'Date:\s*(\d{1,2}\s+\w+\s+\d{4}),\s*Narration:\s*(.+?),\s*Amount:\s*([\d,]+\.\d{2}),\s*Type:\s*(DR|CR)',
        ]
        
        for pattern_str in patterns:
            pattern = re.compile(pattern_str, re.MULTILINE)
            matches = list(pattern.finditer(text))
            
            if matches and len(matches) > 2:  # If found multiple transactions
                for match in matches:
                    try:
                        groups = match.groups()
                        date_str = groups[0]
                        description = groups[1].strip()
                        amount_str = groups[2].replace(',', '')
                        
                        # Try different date formats
                        normalized_date = None
                        for fmt in ['%d/%m/%Y', '%d-%m-%Y', '%d %b %Y', '%d %B %Y']:
                            try:
                                dt = datetime.strptime(date_str, fmt)
                                normalized_date = dt.strftime('%Y-%m-%d')
                                break
                            except:
                                continue
                        
                        if not normalized_date:
                            continue
                        
                        # Determine type
                        txn_type = 'debit'
                        if len(groups) > 3 and groups[3]:
                            type_ind = groups[3].upper()
                            txn_type = 'credit' if type_ind in ['CR', 'CREDIT'] else 'debit'
                        elif any(kw in description.upper() for kw in ['PAYMENT', 'CREDIT', 'REFUND']):
                            txn_type = 'credit'
                        
                        # Clean description
                        description = re.sub(r'\s+[+-]\s*\d+\s*[+-]?\s*$', '', description).strip()
                        
                        transactions.append({
                            'date': normalized_date,
                            'description': description,
                            'amount': float(amount_str),
                            'type': txn_type,
                            'account': self.account_name
                        })
                    except Exception as e:
                        continue
                
                if transactions:
                    break
        
        return transactions

def get_simple_parser(account_name: str, custom_pattern: Dict = None):
    """Factory function to get parser"""
    return SimplePDFParser(account_name, custom_pattern)
