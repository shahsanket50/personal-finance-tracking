"""
Iteration 12: Backend Refactoring Verification Tests
=====================================================
Tests to verify all endpoints work correctly after splitting server.py into modular route files.
The monolithic server.py (2873 lines) was split into:
- database.py, models.py, auth.py, bridge.py, helpers.py
- 10 route files under routes/: auth_routes.py, accounts.py, categories.py, transactions.py,
  analytics.py, accounting.py, upload.py, ai.py, backup.py, email_sync.py
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
AUTH_HEADER = {"Authorization": "Bearer test_session_7e4ac6df60e1455f93f1cc93d93a2e84"}


class TestAuthRoutes:
    """Tests for /api/auth/* endpoints (auth_routes.py)"""
    
    def test_get_auth_me(self):
        """GET /api/auth/me - returns user data"""
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "user_id" in data
        assert "email" in data
        assert "name" in data
        assert data["email"] == "test@moneyinsights.com"
        print(f"✓ GET /api/auth/me - user_id: {data['user_id']}, email: {data['email']}")
    
    def test_auth_me_requires_auth(self):
        """GET /api/auth/me - returns 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 401
        print("✓ GET /api/auth/me - correctly returns 401 without auth")


class TestAccountsRoutes:
    """Tests for /api/accounts/* endpoints (accounts.py)"""
    
    def test_get_accounts(self):
        """GET /api/accounts - returns accounts list"""
        response = requests.get(f"{BASE_URL}/api/accounts", headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1, "Expected at least 1 account"
        # Verify account structure
        account = data[0]
        assert "id" in account
        assert "name" in account
        assert "account_type" in account
        assert "current_balance" in account
        print(f"✓ GET /api/accounts - returned {len(data)} accounts")


class TestCategoriesRoutes:
    """Tests for /api/categories/* endpoints (categories.py)"""
    
    def test_get_categories(self):
        """GET /api/categories - returns categories (48+ defaults)"""
        response = requests.get(f"{BASE_URL}/api/categories", headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 48, f"Expected at least 48 categories, got {len(data)}"
        # Verify category structure
        category = data[0]
        assert "id" in category
        assert "name" in category
        assert "category_type" in category
        assert "color" in category
        print(f"✓ GET /api/categories - returned {len(data)} categories")


class TestTransactionsRoutes:
    """Tests for /api/transactions/* endpoints (transactions.py)"""
    
    def test_get_transactions(self):
        """GET /api/transactions - returns transactions"""
        response = requests.get(f"{BASE_URL}/api/transactions", headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Verify transaction structure if any exist
        if len(data) > 0:
            txn = data[0]
            assert "id" in txn
            assert "account_id" in txn
            assert "date" in txn
            assert "description" in txn
            assert "amount" in txn
            assert "transaction_type" in txn
        print(f"✓ GET /api/transactions - returned {len(data)} transactions")
    
    def test_create_transaction(self):
        """POST /api/transactions - create a new transaction (should auto-bridge to voucher)"""
        # Get first account
        accounts_resp = requests.get(f"{BASE_URL}/api/accounts", headers=AUTH_HEADER)
        accounts = accounts_resp.json()
        account_id = accounts[0]["id"]
        
        payload = {
            "account_id": account_id,
            "date": "2026-01-15",
            "description": "TEST_Iteration12_Transaction",
            "amount": 50.00,
            "transaction_type": "debit",
            "category_id": None
        }
        response = requests.post(f"{BASE_URL}/api/transactions", headers=AUTH_HEADER, json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["description"] == "TEST_Iteration12_Transaction"
        assert data["amount"] == 50.00
        print(f"✓ POST /api/transactions - created transaction id: {data['id']}")
        return data["id"]


class TestAnalyticsRoutes:
    """Tests for /api/analytics/* endpoints (analytics.py)"""
    
    def test_get_analytics_summary(self):
        """GET /api/analytics/summary - returns analytics data with income/expense/trends"""
        response = requests.get(f"{BASE_URL}/api/analytics/summary", headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        # Verify analytics structure
        assert "total_income" in data
        assert "total_expense" in data
        assert "net_savings" in data
        assert "category_breakdown" in data
        assert "monthly_trend" in data
        assert "daily_trend" in data
        assert "account_summary" in data
        print(f"✓ GET /api/analytics/summary - income: {data['total_income']}, expense: {data['total_expense']}")


class TestAccountingRoutes:
    """Tests for /api/* accounting endpoints (accounting.py)"""
    
    def test_get_vouchers(self):
        """GET /api/vouchers - returns vouchers list"""
        response = requests.get(f"{BASE_URL}/api/vouchers", headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            voucher = data[0]
            assert "id" in voucher
            assert "voucher_number" in voucher
            assert "voucher_type" in voucher
            assert "date" in voucher
            assert "entries" in voucher
        print(f"✓ GET /api/vouchers - returned {len(data)} vouchers")
    
    def test_get_trial_balance(self):
        """GET /api/trial-balance - returns trial balance with is_balanced"""
        response = requests.get(f"{BASE_URL}/api/trial-balance", headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        assert "rows" in data
        assert "total_debit" in data
        assert "total_credit" in data
        assert "is_balanced" in data
        print(f"✓ GET /api/trial-balance - Dr: {data['total_debit']}, Cr: {data['total_credit']}, balanced: {data['is_balanced']}")
    
    def test_get_profit_loss(self):
        """GET /api/profit-loss - returns P&L statement"""
        response = requests.get(f"{BASE_URL}/api/profit-loss", headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        assert "income" in data
        assert "expenses" in data
        assert "total_income" in data
        assert "total_expenses" in data
        assert "net_profit" in data
        print(f"✓ GET /api/profit-loss - income: {data['total_income']}, expenses: {data['total_expenses']}, net_profit: {data['net_profit']}")
    
    def test_get_balance_sheet(self):
        """GET /api/balance-sheet - returns balance sheet"""
        response = requests.get(f"{BASE_URL}/api/balance-sheet", headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        assert "assets" in data
        assert "liabilities" in data
        assert "total_assets" in data
        assert "total_liabilities" in data
        assert "is_balanced" in data
        print(f"✓ GET /api/balance-sheet - assets: {data['total_assets']}, liabilities: {data['total_liabilities']}, balanced: {data['is_balanced']}")
    
    def test_get_daybook(self):
        """GET /api/daybook - returns daybook entries"""
        response = requests.get(f"{BASE_URL}/api/daybook", headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            entry = data[0]
            assert "voucher_number" in entry
            assert "entries" in entry
            # Verify ledger_name is enriched in entries
            if entry["entries"]:
                assert "ledger_name" in entry["entries"][0]
        print(f"✓ GET /api/daybook - returned {len(data)} entries")
    
    def test_get_company(self):
        """GET /api/company - returns company info"""
        response = requests.get(f"{BASE_URL}/api/company", headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "name" in data
        assert "user_id" in data
        assert "fy_start_month" in data
        print(f"✓ GET /api/company - name: {data['name']}, fy_start: {data['fy_start_month']}")
    
    def test_get_financial_years(self):
        """GET /api/financial-years - returns FY list"""
        response = requests.get(f"{BASE_URL}/api/financial-years", headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        assert "years" in data
        assert "current_fy" in data
        assert isinstance(data["years"], list)
        if len(data["years"]) > 0:
            fy = data["years"][0]
            assert "label" in fy
            assert "start" in fy
            assert "end" in fy
        print(f"✓ GET /api/financial-years - current_fy: {data['current_fy']}, years: {len(data['years'])}")
    
    def test_get_account_groups(self):
        """GET /api/account-groups - returns chart of accounts groups"""
        response = requests.get(f"{BASE_URL}/api/account-groups", headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 20, f"Expected at least 20 account groups, got {len(data)}"
        if len(data) > 0:
            group = data[0]
            assert "id" in group
            assert "name" in group
            assert "nature" in group
        print(f"✓ GET /api/account-groups - returned {len(data)} groups")
    
    def test_get_ledgers(self):
        """GET /api/ledgers - returns ledgers"""
        response = requests.get(f"{BASE_URL}/api/ledgers", headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            ledger = data[0]
            assert "id" in ledger
            assert "name" in ledger
            assert "group_id" in ledger
        print(f"✓ GET /api/ledgers - returned {len(data)} ledgers")


class TestAuthRequired:
    """Tests to verify all endpoints require authentication"""
    
    @pytest.mark.parametrize("endpoint", [
        "/api/accounts",
        "/api/categories",
        "/api/transactions",
        "/api/analytics/summary",
        "/api/vouchers",
        "/api/trial-balance",
        "/api/profit-loss",
        "/api/balance-sheet",
        "/api/daybook",
        "/api/company",
        "/api/financial-years",
        "/api/account-groups",
        "/api/ledgers",
    ])
    def test_endpoint_requires_auth(self, endpoint):
        """All endpoints should return 401 without auth"""
        response = requests.get(f"{BASE_URL}{endpoint}")
        assert response.status_code == 401, f"{endpoint} should return 401 without auth, got {response.status_code}"
        print(f"✓ {endpoint} - correctly returns 401 without auth")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
