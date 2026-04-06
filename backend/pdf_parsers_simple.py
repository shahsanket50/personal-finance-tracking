import re
from datetime import datetime
from typing import List, Dict, Optional
import pdfplumber
import io
import logging

logger = logging.getLogger(__name__)


def _decrypt_pdf_bytes(pdf_blob: bytes, password: str) -> bytes:
    """Decrypt a password-protected PDF using pikepdf, return decrypted bytes."""
    try:
        import pikepdf
        input_file = io.BytesIO(pdf_blob)
        pdf = pikepdf.open(input_file, password=password)
        output = io.BytesIO()
        pdf.save(output)
        pdf.close()
        return output.getvalue()
    except Exception:
        return None


class SimplePDFParser:
    """Smart PDF parser that tries multiple strategies to extract transactions"""

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
            except Exception:
                pdf_file.seek(0)
                continue

        # Fallback: use pikepdf to decrypt, then re-open with pdfplumber
        if password:
            decrypted = _decrypt_pdf_bytes(pdf_blob, password)
            if decrypted:
                try:
                    with pdfplumber.open(io.BytesIO(decrypted)) as pdf:
                        for page in pdf.pages:
                            page_text = page.extract_text()
                            if page_text:
                                text_content += page_text + "\n"
                    return text_content
                except Exception as e:
                    logger.warning(f"pikepdf decrypted but pdfplumber failed: {e}")
            else:
                raise Exception(f"Invalid password for this PDF. Please check and re-enter the correct password.")

        raise Exception("PDF is password protected or cannot be read. Please provide the correct password.")

    def extract_tables(self, pdf_blob: bytes, password: str = None) -> List:
        """Extract tables from PDF using pdfplumber"""
        all_tables = []
        pdf_file = io.BytesIO(pdf_blob)
        passwords_to_try = [''] if not password else ['', password]

        for pwd in passwords_to_try:
            try:
                with pdfplumber.open(pdf_file, password=pwd) as pdf:
                    for page in pdf.pages:
                        tables = page.extract_tables()
                        if tables:
                            all_tables.extend(tables)
                return all_tables
            except Exception:
                pdf_file.seek(0)
                continue

        # Fallback: pikepdf decrypt
        if password:
            decrypted = _decrypt_pdf_bytes(pdf_blob, password)
            if decrypted:
                try:
                    with pdfplumber.open(io.BytesIO(decrypted)) as pdf:
                        for page in pdf.pages:
                            tables = page.extract_tables()
                            if tables:
                                all_tables.extend(tables)
                    return all_tables
                except Exception:
                    pass
        return []

    def parse(self, pdf_blob: bytes, password: str = None) -> List[Dict]:
        """Parse PDF using the best available strategy"""
        # If custom pattern saved, use it
        if self.custom_pattern and self.custom_pattern.get('strategy'):
            return self._parse_with_strategy(pdf_blob, password, self.custom_pattern['strategy'])

        if self.custom_pattern and self.custom_pattern.get('regex'):
            text = self.extract_text(pdf_blob, password)
            return self.parse_with_custom_regex(text)

        # Auto-detect: try all strategies, pick the best
        return self.auto_detect_and_parse(pdf_blob, password)

    def auto_detect_and_parse(self, pdf_blob: bytes, password: str = None) -> List[Dict]:
        """Try all parsing strategies and return the one with most results"""
        text = self.extract_text(pdf_blob, password)
        results = {}

        # Strategy 1: Slice credit card format
        txns = self.parse_slice_credit(text)
        if txns:
            results['slice_credit'] = txns
            logger.info(f"slice_credit strategy found {len(txns)} transactions")

        # Strategy 2: HDFC bank statement (line-by-line with DD/MM/YY)
        txns = self.parse_hdfc_bank_text(text)
        if txns:
            results['hdfc_bank'] = txns
            logger.info(f"hdfc_bank strategy found {len(txns)} transactions")

        # Strategy 3: Credit card with DD/MM/YYYY format (HDFC Diners etc)
        txns = self.parse_credit_card_statement(text)
        if txns:
            results['credit_card'] = txns
            logger.info(f"credit_card strategy found {len(txns)} transactions")

        # Strategy 4: Generic multi-pattern
        txns = self.parse_generic(text)
        if txns:
            results['generic'] = txns
            logger.info(f"generic strategy found {len(txns)} transactions")

        if not results:
            return []

        # Return the strategy with most transactions
        best_strategy = max(results.keys(), key=lambda k: len(results[k]))
        logger.info(f"Best strategy: {best_strategy} with {len(results[best_strategy])} transactions")
        return results[best_strategy]

    def detect_best_strategy(self, pdf_blob: bytes, password: str = None) -> Dict:
        """Detect best strategy and return it along with results"""
        text = self.extract_text(pdf_blob, password)
        results = {}

        strategies = [
            ('slice_credit', self.parse_slice_credit),
            ('hdfc_bank', self.parse_hdfc_bank_text),
            ('credit_card', self.parse_credit_card_statement),
            ('generic', self.parse_generic),
        ]

        for name, fn in strategies:
            txns = fn(text)
            if txns:
                results[name] = txns

        if not results:
            return {'strategy': None, 'transactions': [], 'all_results': {}}

        best = max(results.keys(), key=lambda k: len(results[k]))
        return {
            'strategy': best,
            'transactions': results[best],
            'all_results': {k: len(v) for k, v in results.items()}
        }

    def _parse_with_strategy(self, pdf_blob: bytes, password: str, strategy: str) -> List[Dict]:
        """Parse using a specific named strategy"""
        text = self.extract_text(pdf_blob, password)
        strategy_map = {
            'slice_credit': self.parse_slice_credit,
            'hdfc_bank': self.parse_hdfc_bank_text,
            'credit_card': self.parse_credit_card_statement,
            'generic': self.parse_generic,
        }
        fn = strategy_map.get(strategy, self.parse_generic)
        return fn(text)

    # ─── Strategy: Slice Credit Card ─────────────────────────────────
    def parse_slice_credit(self, text: str) -> List[Dict]:
        """
        Parse Slice credit card format:
        Description ₹amount
        X                       (single letter avatar)
        DD Mon 'YY • UPI
        """
        transactions = []
        lines = text.split('\n')

        # Match: description ₹amount
        amount_pattern = re.compile(r'^(.+?)\s+[₹Rs.]*\s*([\d,]+(?:\.\d{1,2})?)\s*$')
        # Match: DD Mon 'YY or D Mon 'YY
        date_pattern = re.compile(r"^(\d{1,2}\s+\w{3}\s+['\u2019]?\d{2})\s*[•·]?\s*(.*)$")

        i = 0
        while i < len(lines):
            line = lines[i].strip()
            am = amount_pattern.match(line)

            if am:
                desc = am.group(1).strip()
                amount_str = am.group(2).replace(',', '')

                # Skip summary lines
                if desc.lower() in ['spends', 'refunds & repayments', 'interest', 'surcharge',
                                     'total amount due', 'min amount due', 'igst', 'cgst', 'sgst']:
                    i += 1
                    continue

                # Look ahead for date line (1-2 lines ahead)
                date_str = None
                txn_type = 'debit'
                for offset in range(1, 4):
                    if i + offset < len(lines):
                        dl = lines[i + offset].strip()
                        dm = date_pattern.match(dl)
                        if dm:
                            date_str = dm.group(1).replace('\u2019', "'").replace('\u2018', "'")
                            i = i + offset + 1
                            break
                else:
                    i += 1
                    continue

                if not date_str:
                    i += 1
                    continue

                # Normalize date: "20 Dec '25" -> 2025-12-20
                normalized = self._parse_date_flexible(date_str)
                if not normalized:
                    i += 1
                    continue

                # Detect refunds
                if any(kw in desc.lower() for kw in ['refund', 'reversal', 'repayment', 'cashback']):
                    txn_type = 'credit'

                transactions.append({
                    'date': normalized,
                    'description': desc,
                    'amount': float(amount_str),
                    'type': txn_type,
                    'account': self.account_name
                })
            else:
                i += 1

        return transactions

    # ─── Strategy: HDFC Bank Statement ────────────────────────────────
    def parse_hdfc_bank_text(self, text: str) -> List[Dict]:
        """
        Parse HDFC bank statement format (multi-page):
        DD/MM/YY Narration RefNo DD/MM/YY Amount(s) ClosingBalance
        Continuation lines...
        """
        transactions = []
        lines = text.split('\n')

        # Skip lines: headers, footers, metadata
        skip_patterns = [
            'PageNo', 'Statementofaccount', 'AccountBranch', 'Address',
            'City', 'State', 'Email', 'CustID', 'AccountNo', 'AccountStatus',
            'JOINTHOLDERS', 'BranchCode', 'Nomination', 'StatementFrom',
            'Date Narration', 'Closingbalance', 'Contentsofthis',
            'StateaccountbranchGSTN', 'HDFCBankGSTIN', 'OpeningBalance',
            'HDFCBANKLIMITED', 'RTGS/NEFT', 'ProductCode', 'A/COpenDate',
            'ODLimit', 'Currency', 'Phoneno', 'MICR',
        ]

        txn_start = re.compile(r'^(\d{2}/\d{2}/\d{2})\s+(.+)')
        prev_closing = None

        current_txn = None
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # Skip known header/footer lines
            clean = stripped.replace(' ', '')
            if any(skip in clean for skip in skip_patterns):
                # Finalize pending txn before skipping
                if current_txn:
                    self._finalize_hdfc_txn_v2(current_txn, transactions, prev_closing)
                    if transactions:
                        prev_closing = transactions[-1].get('_closing')
                    current_txn = None
                continue

            m = txn_start.match(stripped)
            if m:
                # Save previous transaction
                if current_txn:
                    self._finalize_hdfc_txn_v2(current_txn, transactions, prev_closing)
                    if transactions:
                        prev_closing = transactions[-1].get('_closing')

                current_txn = {
                    'date_str': m.group(1),
                    'full_line': m.group(2),
                    'continuation': []
                }
            elif current_txn:
                current_txn['continuation'].append(stripped)

        # Finalize last transaction
        if current_txn:
            self._finalize_hdfc_txn_v2(current_txn, transactions, prev_closing)

        # Remove internal _closing field
        for t in transactions:
            t.pop('_closing', None)

        return transactions

    def _finalize_hdfc_txn_v2(self, txn_data: Dict, transactions: List, prev_closing: float):
        """Process a collected HDFC bank transaction with closing balance tracking"""
        full_text = txn_data['full_line']
        date_str = txn_data['date_str']

        # Combine all text for this transaction
        all_text = full_text
        for cont in txn_data.get('continuation', []):
            all_text += ' ' + cont

        # Extract all amounts from the full text
        amounts = re.findall(r'[\d,]+\.\d{2}', all_text)
        if len(amounts) < 2:
            return

        # Last amount is always the closing balance
        closing_balance = float(amounts[-1].replace(',', ''))
        txn_amount = float(amounts[-2].replace(',', ''))

        # Extract narration: everything before the ref number
        ref_match = re.search(r'\d{13,}', full_text)
        if ref_match:
            narration = full_text[:ref_match.start()].strip()
        else:
            # Fallback: remove amounts from text
            narration = re.sub(r'\d{2}/\d{2}/\d{2}', '', all_text)
            narration = re.sub(r'[\d,]+\.\d{2}', '', narration).strip()

        # Clean narration
        narration = re.sub(r'\s+', ' ', narration).strip()[:200]

        # Determine debit/credit using closing balance change
        txn_type = 'debit'
        if prev_closing is not None:
            if closing_balance > prev_closing:
                txn_type = 'credit'
        else:
            # First transaction: check keywords
            credit_keywords = ['NEFT CR', 'SALARY', 'INT.PD', 'DEPOSIT', 'BY TRANSFER',
                               'BY CLG', 'IMPS CR', 'ACH CR', 'RTGS CR']
            if any(kw in narration.upper() for kw in credit_keywords):
                txn_type = 'credit'

        normalized = self._parse_date_flexible(date_str)
        if not normalized:
            return

        transactions.append({
            'date': normalized,
            'description': narration,
            'amount': txn_amount,
            'type': txn_type,
            'account': self.account_name,
            '_closing': closing_balance
        })

    # ─── Strategy: Credit Card Statement (HDFC Diners style) ──────────
    def parse_credit_card_statement(self, text: str) -> List[Dict]:
        """
        Parse credit card statements with various formats:
        - DD/MM/YYYY| HH:MM description C amount l  (HDFC Diners)
        - DD/MM/YYYY description amount Cr/Dr
        """
        transactions = []

        patterns = [
            # HDFC Diners: 22/02/2026| 22:10 EMI MAKEMYTRIP... C 27,082.00 l
            r'(\d{2}/\d{2}/\d{4})\|?\s+(?:\d{2}:\d{2}\s+)?(.+?)\s+C\s+([\d,]+\.\d{2})\s*l?',
            # General: DD/MM/YYYY description amount Cr/Dr
            r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([\d,]+\.\d{2})\s*(Cr|Dr|CR|DR)',
            # With pipe separator
            r'(\d{2}/\d{2}/\d{4})\|(.+?)\|([\d,]+\.\d{2})\s*(Cr|Dr)?',
        ]

        for pattern_str in patterns:
            matches = list(re.finditer(pattern_str, text, re.MULTILINE))
            if len(matches) >= 3:
                for match in matches:
                    groups = match.groups()
                    date_str = groups[0]
                    description = groups[1].strip()
                    amount_str = groups[2].replace(',', '')
                    type_ind = groups[3] if len(groups) > 3 and groups[3] else None

                    normalized = self._parse_date_flexible(date_str)
                    if not normalized:
                        continue

                    # Clean description: remove reward points like "+ 900", "- 40 +"
                    description = re.sub(r'\s*[+-]\s*\d+\s*[+-]?\s*$', '', description).strip()
                    description = re.sub(r'\s+', ' ', description).strip()

                    txn_type = 'debit'
                    if type_ind and type_ind.upper() in ['CR', 'CREDIT']:
                        txn_type = 'credit'
                    elif any(kw in description.upper() for kw in ['PAYMENT RECEIVED', 'CREDIT', 'REFUND', 'REVERSAL', 'CASHBACK']):
                        txn_type = 'credit'

                    transactions.append({
                        'date': normalized,
                        'description': description[:200],
                        'amount': float(amount_str),
                        'type': txn_type,
                        'account': self.account_name
                    })

                if transactions:
                    break

        return transactions

    # ─── Strategy: Generic patterns ────────────────────────────────────
    def parse_generic(self, text: str) -> List[Dict]:
        """Generic parser - tries common patterns"""
        transactions = []

        patterns = [
            # DD/MM/YYYY description amount Cr/Dr
            (r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([\d,]+\.\d{2})\s*(Cr|Dr)?', '%d/%m/%Y'),
            # DD-MM-YYYY description amount
            (r'(\d{2}-\d{2}-\d{4})\s+(.+?)\s+([\d,]+\.\d{2})\s*(Cr|Dr)?', '%d-%m-%Y'),
            # DD Mon YYYY description amount
            (r'(\d{1,2}\s+\w{3}\s+\d{4})\s+(.+?)\s+([\d,]+\.\d{2})\s*(Cr|Dr)?', '%d %b %Y'),
        ]

        for pattern_str, date_fmt in patterns:
            matches = list(re.finditer(pattern_str, text, re.MULTILINE))

            if matches and len(matches) >= 3:
                for match in matches:
                    groups = match.groups()
                    date_str = groups[0]
                    description = groups[1].strip()
                    amount_str = groups[2].replace(',', '')

                    normalized = self._parse_date_flexible(date_str)
                    if not normalized:
                        continue

                    txn_type = 'debit'
                    if len(groups) > 3 and groups[3]:
                        type_ind = groups[3].upper()
                        txn_type = 'credit' if type_ind in ['CR', 'CREDIT'] else 'debit'
                    elif any(kw in description.upper() for kw in ['PAYMENT', 'CREDIT', 'REFUND']):
                        txn_type = 'credit'

                    description = re.sub(r'\s+', ' ', description).strip()[:200]

                    transactions.append({
                        'date': normalized,
                        'description': description,
                        'amount': float(amount_str),
                        'type': txn_type,
                        'account': self.account_name
                    })

                if transactions:
                    break

        return transactions

    # ─── Custom regex (user-defined) ───────────────────────────────────
    def parse_with_custom_regex(self, text: str) -> List[Dict]:
        """Parse using saved custom regex pattern"""
        transactions = []
        pattern_str = self.custom_pattern.get('regex')
        if not pattern_str:
            return []

        try:
            pattern = re.compile(pattern_str, re.MULTILINE)
            mapping = self.custom_pattern.get('mapping', {})

            for match in pattern.finditer(text):
                groups = match.groups()
                date_str = groups[mapping.get('date', 0)]
                description = groups[mapping.get('description', 1)]
                amount_str = groups[mapping.get('amount', 2)].replace(',', '')

                date_format = self.custom_pattern.get('date_format', '%d/%m/%Y')
                try:
                    dt = datetime.strptime(date_str, date_format)
                    normalized_date = dt.strftime('%Y-%m-%d')
                except Exception:
                    normalized_date = date_str

                txn_type = 'debit'
                if mapping.get('type') is not None:
                    type_indicator = groups[mapping.get('type')]
                    credit_indicators = self.custom_pattern.get('credit_indicators', ['Cr', 'CREDIT', 'PAYMENT'])
                    txn_type = 'credit' if any(ind.upper() in type_indicator.upper() for ind in credit_indicators) else 'debit'

                transactions.append({
                    'date': normalized_date,
                    'description': description.strip(),
                    'amount': float(amount_str),
                    'type': txn_type,
                    'account': self.account_name
                })
        except Exception as e:
            logger.error(f"Error parsing with custom regex: {e}")
            return []

        return transactions

    # ─── Date parsing helper ────────────────────────────────────────────
    def _parse_date_flexible(self, date_str: str) -> Optional[str]:
        """Parse various date formats and return YYYY-MM-DD"""
        date_str = date_str.strip().replace("'", "").replace("\u2019", "").replace("\u2018", "")

        formats = [
            '%d/%m/%Y',     # 01/04/2024
            '%d-%m-%Y',     # 01-04-2024
            '%d/%m/%y',     # 01/04/24
            '%d-%m-%y',     # 01-04-24
            '%d %b %y',     # 20 Dec 25
            '%d %b %Y',     # 20 Dec 2025
            '%d %B %Y',     # 20 December 2025
            '%d %B %y',     # 20 December 25
            '%Y-%m-%d',     # 2024-04-01
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                # Handle 2-digit year: if year < 100, add 2000
                if dt.year < 100:
                    dt = dt.replace(year=dt.year + 2000)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue

        return None


def get_simple_parser(account_name: str, custom_pattern: Dict = None):
    """Factory function to get parser"""
    return SimplePDFParser(account_name, custom_pattern)
