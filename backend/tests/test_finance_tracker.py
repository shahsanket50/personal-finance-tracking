"""
Finance Tracker API Tests
Tests for: Accounts, Categories, Transactions, PDF Parsing, Analytics
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://money-insights-82.preview.emergentagent.com').rstrip('/')
API_URL = f"{BASE_URL}/api"

# Test data tracking for cleanup
created_accounts = []
created_categories = []
created_transactions = []


class TestHealthAndInit:
    """Basic health and initialization tests"""
    
    def test_api_accessible(self):
        """Test that API is accessible"""
        response = requests.get(f"{API_URL}/accounts")
        assert response.status_code == 200, f"API not accessible: {response.text}"
        print(f"API accessible, found {len(response.json())} accounts")
    
    def test_init_default_categories(self):
        """Test POST /api/init - initialize default categories"""
        response = requests.post(f"{API_URL}/init")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print(f"Init response: {data['message']}")


class TestAccountsCRUD:
    """Account CRUD operations tests"""
    
    def test_create_account(self):
        """Test POST /api/accounts - create a new test account"""
        payload = {
            "name": "TEST_HDFC_Savings",
            "account_type": "bank",
            "start_balance": 10000.0
        }
        response = requests.post(f"{API_URL}/accounts", json=payload)
        assert response.status_code == 200, f"Failed to create account: {response.text}"
        
        data = response.json()
        assert data["name"] == payload["name"]
        assert data["account_type"] == payload["account_type"]
        assert data["start_balance"] == payload["start_balance"]
        assert data["current_balance"] == payload["start_balance"]
        assert "id" in data
        
        created_accounts.append(data["id"])
        print(f"Created account: {data['name']} with ID: {data['id']}")
        return data
    
    def test_get_accounts(self):
        """Test GET /api/accounts - list all accounts"""
        response = requests.get(f"{API_URL}/accounts")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} accounts")
        
        # Verify structure of accounts
        if data:
            acc = data[0]
            assert "id" in acc
            assert "name" in acc
            assert "account_type" in acc
            assert "current_balance" in acc
    
    def test_update_account(self):
        """Test PUT /api/accounts/{id} - update account"""
        # First create an account
        create_payload = {
            "name": "TEST_Update_Account",
            "account_type": "bank",
            "start_balance": 5000.0
        }
        create_response = requests.post(f"{API_URL}/accounts", json=create_payload)
        assert create_response.status_code == 200
        account_id = create_response.json()["id"]
        created_accounts.append(account_id)
        
        # Update the account
        update_payload = {
            "name": "TEST_Updated_Account",
            "account_type": "credit_card",
            "start_balance": 5000.0
        }
        update_response = requests.put(f"{API_URL}/accounts/{account_id}", json=update_payload)
        assert update_response.status_code == 200
        
        updated_data = update_response.json()
        assert updated_data["name"] == "TEST_Updated_Account"
        assert updated_data["account_type"] == "credit_card"
        print(f"Updated account: {updated_data['name']}")
    
    def test_delete_account(self):
        """Test DELETE /api/accounts/{id} - delete account"""
        # First create an account to delete
        create_payload = {
            "name": "TEST_Delete_Account",
            "account_type": "cash",
            "start_balance": 1000.0
        }
        create_response = requests.post(f"{API_URL}/accounts", json=create_payload)
        assert create_response.status_code == 200
        account_id = create_response.json()["id"]
        
        # Delete the account
        delete_response = requests.delete(f"{API_URL}/accounts/{account_id}")
        assert delete_response.status_code == 200
        
        # Verify deletion
        get_response = requests.get(f"{API_URL}/accounts")
        accounts = get_response.json()
        account_ids = [a["id"] for a in accounts]
        assert account_id not in account_ids
        print(f"Deleted account: {account_id}")


class TestCategoriesCRUD:
    """Category CRUD operations tests"""
    
    def test_get_categories(self):
        """Test GET /api/categories - list categories"""
        response = requests.get(f"{API_URL}/categories")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} categories")
        
        # Check for default categories
        category_names = [c["name"] for c in data]
        expected_defaults = ["Salary", "Food & Dining", "Shopping", "Transfer"]
        for expected in expected_defaults:
            if expected in category_names:
                print(f"Found default category: {expected}")
    
    def test_create_category(self):
        """Test POST /api/categories - create custom category"""
        payload = {
            "name": "TEST_Coffee",
            "category_type": "expense",
            "color": "#7CA1A6"
        }
        response = requests.post(f"{API_URL}/categories", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == payload["name"]
        assert data["category_type"] == payload["category_type"]
        assert data["color"] == payload["color"]
        assert "id" in data
        
        created_categories.append(data["id"])
        print(f"Created category: {data['name']}")
    
    def test_cannot_delete_default_category(self):
        """Test that default categories cannot be deleted"""
        # Get categories and find a default one
        response = requests.get(f"{API_URL}/categories")
        categories = response.json()
        
        default_cat = next((c for c in categories if c.get("is_default")), None)
        if default_cat:
            delete_response = requests.delete(f"{API_URL}/categories/{default_cat['id']}")
            assert delete_response.status_code == 400
            print(f"Correctly prevented deletion of default category: {default_cat['name']}")


class TestTransactionsCRUD:
    """Transaction CRUD operations tests"""
    
    @pytest.fixture(autouse=True)
    def setup_account(self):
        """Create a test account for transactions"""
        payload = {
            "name": "TEST_Transaction_Account",
            "account_type": "bank",
            "start_balance": 50000.0
        }
        response = requests.post(f"{API_URL}/accounts", json=payload)
        if response.status_code == 200:
            self.account_id = response.json()["id"]
            created_accounts.append(self.account_id)
        else:
            # Use existing account
            accounts = requests.get(f"{API_URL}/accounts").json()
            self.account_id = accounts[0]["id"] if accounts else None
    
    def test_create_transaction(self):
        """Test POST /api/transactions - create transaction"""
        if not self.account_id:
            pytest.skip("No account available")
        
        payload = {
            "account_id": self.account_id,
            "date": "2026-01-15",
            "description": "TEST_Grocery Shopping",
            "amount": 2500.50,
            "transaction_type": "debit"
        }
        response = requests.post(f"{API_URL}/transactions", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["description"] == payload["description"]
        assert data["amount"] == payload["amount"]
        assert data["transaction_type"] == payload["transaction_type"]
        assert "id" in data
        
        created_transactions.append(data["id"])
        print(f"Created transaction: {data['description']}")
    
    def test_get_transactions(self):
        """Test GET /api/transactions - list transactions"""
        response = requests.get(f"{API_URL}/transactions")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} transactions")
    
    def test_transaction_updates_balance(self):
        """Test that creating a transaction updates account balance"""
        if not self.account_id:
            pytest.skip("No account available")
        
        # Get initial balance
        acc_response = requests.get(f"{API_URL}/accounts")
        accounts = acc_response.json()
        account = next((a for a in accounts if a["id"] == self.account_id), None)
        if not account:
            pytest.skip("Account not found")
        
        initial_balance = account["current_balance"]
        
        # Create a debit transaction
        payload = {
            "account_id": self.account_id,
            "date": "2026-01-16",
            "description": "TEST_Balance_Check",
            "amount": 1000.0,
            "transaction_type": "debit"
        }
        response = requests.post(f"{API_URL}/transactions", json=payload)
        assert response.status_code == 200
        created_transactions.append(response.json()["id"])
        
        # Check updated balance
        acc_response = requests.get(f"{API_URL}/accounts")
        accounts = acc_response.json()
        account = next((a for a in accounts if a["id"] == self.account_id), None)
        
        expected_balance = initial_balance - 1000.0
        assert account["current_balance"] == expected_balance, f"Expected {expected_balance}, got {account['current_balance']}"
        print(f"Balance correctly updated: {initial_balance} -> {account['current_balance']}")


class TestPDFParsing:
    """PDF parsing and debug endpoint tests"""
    
    def test_debug_pdf_slice_credit(self):
        """Test POST /api/debug-pdf with slice credit card PDF (no password)"""
        pdf_path = "/tmp/test_pdfs/slice_credit_dec2025.pdf"
        if not os.path.exists(pdf_path):
            pytest.skip(f"Test PDF not found: {pdf_path}")
        
        with open(pdf_path, "rb") as f:
            files = {"file": ("slice_credit_dec2025.pdf", f, "application/pdf")}
            response = requests.post(f"{API_URL}/debug-pdf", files=files)
        
        assert response.status_code == 200, f"Debug PDF failed: {response.text}"
        data = response.json()
        
        assert "transactions_found" in data
        assert "text_length" in data
        print(f"Slice Credit PDF: Found {data['transactions_found']} transactions, text length: {data['text_length']}")
        
        if data["transactions_found"] > 0:
            print(f"Sample transaction: {data['transactions'][0]}")
    
    def test_debug_pdf_hdfc_bank(self):
        """Test POST /api/debug-pdf with HDFC bank statement (no password)"""
        pdf_path = "/tmp/test_pdfs/hdfc_bank.pdf"
        if not os.path.exists(pdf_path):
            pytest.skip(f"Test PDF not found: {pdf_path}")
        
        with open(pdf_path, "rb") as f:
            files = {"file": ("hdfc_bank.pdf", f, "application/pdf")}
            response = requests.post(f"{API_URL}/debug-pdf", files=files)
        
        assert response.status_code == 200, f"Debug PDF failed: {response.text}"
        data = response.json()
        
        assert "transactions_found" in data
        print(f"HDFC Bank PDF: Found {data['transactions_found']} transactions")
        
        # Expected ~296 transactions based on context
        if data["transactions_found"] > 0:
            print(f"Sample transaction: {data['transactions'][0]}")
    
    def test_debug_pdf_axis_bank_with_password(self):
        """Test POST /api/debug-pdf with Axis bank (password protected)"""
        pdf_path = "/tmp/test_pdfs/axis_bank.pdf"
        if not os.path.exists(pdf_path):
            pytest.skip(f"Test PDF not found: {pdf_path}")
        
        with open(pdf_path, "rb") as f:
            files = {"file": ("axis_bank.pdf", f, "application/pdf")}
            response = requests.post(f"{API_URL}/debug-pdf?password=SANK3011", files=files)
        
        assert response.status_code == 200, f"Debug PDF failed: {response.text}"
        data = response.json()
        
        assert "transactions_found" in data
        print(f"Axis Bank PDF (password protected): Found {data['transactions_found']} transactions")
        
        # Expected ~46 transactions based on context
        if data["transactions_found"] > 0:
            print(f"Sample transaction: {data['transactions'][0]}")


class TestParserBuilder:
    """Parser builder endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup_account(self):
        """Create a test account for parser builder"""
        payload = {
            "name": "TEST_Parser_Account",
            "account_type": "credit_card",
            "start_balance": 0.0
        }
        response = requests.post(f"{API_URL}/accounts", json=payload)
        if response.status_code == 200:
            self.account_id = response.json()["id"]
            created_accounts.append(self.account_id)
        else:
            accounts = requests.get(f"{API_URL}/accounts").json()
            self.account_id = accounts[0]["id"] if accounts else None
    
    def test_build_parser_auto_detection(self):
        """Test POST /api/build-parser - auto-detect parsing strategy"""
        if not self.account_id:
            pytest.skip("No account available")
        
        pdf_path = "/tmp/test_pdfs/slice_credit_dec2025.pdf"
        if not os.path.exists(pdf_path):
            pytest.skip(f"Test PDF not found: {pdf_path}")
        
        with open(pdf_path, "rb") as f:
            files = {"file": ("slice_credit_dec2025.pdf", f, "application/pdf")}
            response = requests.post(
                f"{API_URL}/build-parser?account_id={self.account_id}",
                files=files
            )
        
        assert response.status_code == 200, f"Build parser failed: {response.text}"
        data = response.json()
        
        assert "detected_strategy" in data
        assert "all_strategies" in data
        assert "transactions_found" in data
        
        print(f"Detected strategy: {data['detected_strategy']}")
        print(f"All strategies: {data['all_strategies']}")
        print(f"Transactions found: {data['transactions_found']}")
    
    def test_save_parser_pattern(self):
        """Test POST /api/save-parser-pattern - save parser config"""
        if not self.account_id:
            pytest.skip("No account available")
        
        response = requests.post(
            f"{API_URL}/save-parser-pattern?account_id={self.account_id}&strategy=slice_credit&password=test123"
        )
        
        assert response.status_code == 200, f"Save parser failed: {response.text}"
        data = response.json()
        
        assert "message" in data
        print(f"Save parser response: {data['message']}")
        
        # Verify the account was updated
        acc_response = requests.get(f"{API_URL}/accounts")
        accounts = acc_response.json()
        account = next((a for a in accounts if a["id"] == self.account_id), None)
        
        if account:
            assert account.get("custom_parser") is not None or account.get("pdf_password") is not None
            print(f"Account updated with parser config")


class TestUploadStatement:
    """Statement upload and import tests"""
    
    @pytest.fixture(autouse=True)
    def setup_account(self):
        """Create a test account for uploads"""
        payload = {
            "name": "TEST_Upload_Account",
            "account_type": "credit_card",
            "start_balance": 0.0
        }
        response = requests.post(f"{API_URL}/accounts", json=payload)
        if response.status_code == 200:
            self.account_id = response.json()["id"]
            created_accounts.append(self.account_id)
        else:
            accounts = requests.get(f"{API_URL}/accounts").json()
            self.account_id = accounts[0]["id"] if accounts else None
    
    def test_upload_statement_pdf(self):
        """Test POST /api/upload-statement - upload PDF and import transactions"""
        if not self.account_id:
            pytest.skip("No account available")
        
        pdf_path = "/tmp/test_pdfs/slice_credit_dec2025.pdf"
        if not os.path.exists(pdf_path):
            pytest.skip(f"Test PDF not found: {pdf_path}")
        
        with open(pdf_path, "rb") as f:
            files = {"file": ("slice_credit_dec2025.pdf", f, "application/pdf")}
            response = requests.post(
                f"{API_URL}/upload-statement?account_id={self.account_id}",
                files=files
            )
        
        assert response.status_code == 200, f"Upload failed: {response.text}"
        data = response.json()
        
        assert "message" in data
        assert "imported_count" in data
        print(f"Upload response: {data['message']}")
        print(f"Imported: {data.get('imported_count', 0)} transactions")


class TestAnalytics:
    """Analytics endpoint tests"""
    
    def test_analytics_summary(self):
        """Test GET /api/analytics/summary - get analytics summary"""
        response = requests.get(f"{API_URL}/analytics/summary")
        assert response.status_code == 200
        
        data = response.json()
        assert "total_income" in data
        assert "total_expense" in data
        assert "net_savings" in data
        assert "category_breakdown" in data
        assert "monthly_trend" in data
        assert "account_balances" in data
        
        print(f"Analytics: Income={data['total_income']}, Expense={data['total_expense']}, Net={data['net_savings']}")
    
    def test_analytics_with_date_filter(self):
        """Test GET /api/analytics/summary with date filter"""
        response = requests.get(
            f"{API_URL}/analytics/summary?start_date=2026-01-01&end_date=2026-12-31"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "total_income" in data
        print(f"Filtered analytics: Income={data['total_income']}, Expense={data['total_expense']}")


class TestTransfers:
    """Transfer functionality tests"""
    
    @pytest.fixture(autouse=True)
    def setup_accounts(self):
        """Create two test accounts for transfers"""
        # Account 1
        payload1 = {
            "name": "TEST_Transfer_From",
            "account_type": "bank",
            "start_balance": 100000.0
        }
        response1 = requests.post(f"{API_URL}/accounts", json=payload1)
        if response1.status_code == 200:
            self.from_account_id = response1.json()["id"]
            created_accounts.append(self.from_account_id)
        
        # Account 2
        payload2 = {
            "name": "TEST_Transfer_To",
            "account_type": "bank",
            "start_balance": 50000.0
        }
        response2 = requests.post(f"{API_URL}/accounts", json=payload2)
        if response2.status_code == 200:
            self.to_account_id = response2.json()["id"]
            created_accounts.append(self.to_account_id)
    
    def test_create_transfer(self):
        """Test POST /api/transfers - create transfer between accounts"""
        if not hasattr(self, 'from_account_id') or not hasattr(self, 'to_account_id'):
            pytest.skip("Accounts not available")
        
        payload = {
            "from_account_id": self.from_account_id,
            "to_account_id": self.to_account_id,
            "amount": 10000.0,
            "date": "2026-01-20",
            "description": "TEST_Transfer"
        }
        response = requests.post(f"{API_URL}/transfers", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "transfer_id" in data
        print(f"Created transfer: {data['transfer_id']}")
        
        # Verify balances updated
        acc_response = requests.get(f"{API_URL}/accounts")
        accounts = acc_response.json()
        
        from_acc = next((a for a in accounts if a["id"] == self.from_account_id), None)
        to_acc = next((a for a in accounts if a["id"] == self.to_account_id), None)
        
        if from_acc and to_acc:
            assert from_acc["current_balance"] == 90000.0
            assert to_acc["current_balance"] == 60000.0
            print(f"Balances updated correctly: From={from_acc['current_balance']}, To={to_acc['current_balance']}")
    
    def test_detect_transfers(self):
        """Test POST /api/detect-transfers - detect potential transfers"""
        response = requests.post(f"{API_URL}/detect-transfers")
        assert response.status_code == 200
        
        data = response.json()
        assert "potential_transfers" in data
        assert "count" in data
        print(f"Detected {data['count']} potential transfers")


# Cleanup fixture
@pytest.fixture(scope="session", autouse=True)
def cleanup(request):
    """Cleanup test data after all tests"""
    def cleanup_data():
        print("\n--- Cleaning up test data ---")
        
        # Delete test transactions
        for txn_id in created_transactions:
            try:
                requests.delete(f"{API_URL}/transactions/{txn_id}")
            except:
                pass
        
        # Delete test categories
        for cat_id in created_categories:
            try:
                requests.delete(f"{API_URL}/categories/{cat_id}")
            except:
                pass
        
        # Delete test accounts
        for acc_id in created_accounts:
            try:
                requests.delete(f"{API_URL}/accounts/{acc_id}")
            except:
                pass
        
        print(f"Cleaned up: {len(created_accounts)} accounts, {len(created_categories)} categories, {len(created_transactions)} transactions")
    
    request.addfinalizer(cleanup_data)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
