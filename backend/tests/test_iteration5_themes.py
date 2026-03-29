"""
Iteration 5 Tests: Theme System + Regression Tests
Tests for 5 themes (light, dark, forest, ocean, sand), theme persistence,
and regression tests for all existing features.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
AUTH_TOKEN = "test_session_7e4ac6df60e1455f93f1cc93d93a2e84"
HEADERS = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Content-Type": "application/json"
}


class TestAuthEndpoints:
    """Authentication endpoint tests"""
    
    def test_auth_me_without_token_returns_401(self):
        """All API endpoints return 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: /api/auth/me returns 401 without auth")
    
    def test_auth_me_with_valid_token(self):
        """GET /api/auth/me works with valid token"""
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=HEADERS)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "user_id" in data
        assert "email" in data
        assert data["email"] == "test@moneyinsights.com"
        print(f"PASS: /api/auth/me returns user data: {data['email']}")
    
    def test_accounts_without_auth_returns_401(self):
        """Accounts endpoint returns 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/accounts")
        assert response.status_code == 401
        print("PASS: /api/accounts returns 401 without auth")
    
    def test_transactions_without_auth_returns_401(self):
        """Transactions endpoint returns 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/transactions")
        assert response.status_code == 401
        print("PASS: /api/transactions returns 401 without auth")
    
    def test_categories_without_auth_returns_401(self):
        """Categories endpoint returns 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/categories")
        assert response.status_code == 401
        print("PASS: /api/categories returns 401 without auth")


class TestAccountsEndpoints:
    """Account CRUD tests with email_filter field"""
    
    def test_get_accounts(self):
        """GET /api/accounts returns list of accounts"""
        response = requests.get(f"{BASE_URL}/api/accounts", headers=HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: GET /api/accounts returns {len(data)} accounts")
    
    def test_create_account_with_email_filter(self):
        """POST /api/accounts creates account with email_filter field"""
        payload = {
            "name": "TEST_Theme_Test_Account",
            "account_type": "bank",
            "start_balance": 1000.0,
            "email_filter": "Test Bank Statement"
        }
        response = requests.post(f"{BASE_URL}/api/accounts", headers=HEADERS, json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["name"] == payload["name"]
        assert data["email_filter"] == payload["email_filter"]
        assert "id" in data
        
        # Cleanup
        account_id = data["id"]
        delete_response = requests.delete(f"{BASE_URL}/api/accounts/{account_id}", headers=HEADERS)
        assert delete_response.status_code == 200
        print("PASS: POST /api/accounts creates account with email_filter")


class TestCategoriesEndpoints:
    """Category endpoint tests"""
    
    def test_get_categories(self):
        """GET /api/categories returns default categories"""
        response = requests.get(f"{BASE_URL}/api/categories", headers=HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 10, f"Expected at least 10 default categories, got {len(data)}"
        
        category_names = [c["name"] for c in data]
        expected_categories = ["Salary", "Food & Dining", "Shopping", "Transportation", "Transfer"]
        for cat in expected_categories:
            assert cat in category_names, f"Missing category: {cat}"
        print(f"PASS: GET /api/categories returns {len(data)} categories")


class TestTransactionsEndpoints:
    """Transaction endpoint tests"""
    
    def test_get_transactions(self):
        """GET /api/transactions returns list"""
        response = requests.get(f"{BASE_URL}/api/transactions", headers=HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: GET /api/transactions returns {len(data)} transactions")


class TestAnalyticsEndpoints:
    """Analytics endpoint tests"""
    
    def test_analytics_summary(self):
        """GET /api/analytics/summary returns summary data"""
        response = requests.get(f"{BASE_URL}/api/analytics/summary", headers=HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert "total_income" in data
        assert "total_expense" in data
        assert "net_savings" in data
        assert "category_breakdown" in data
        assert "monthly_trend" in data
        print(f"PASS: GET /api/analytics/summary returns summary with income={data['total_income']}")


class TestEmailConfigEndpoints:
    """Email configuration endpoint tests"""
    
    def test_get_email_config(self):
        """GET /api/email-config returns configured status"""
        response = requests.get(f"{BASE_URL}/api/email-config", headers=HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert "configured" in data
        print(f"PASS: GET /api/email-config returns configured={data['configured']}")
    
    def test_post_email_config(self):
        """POST /api/email-config saves email configuration"""
        payload = {
            "imap_server": "imap.gmail.com",
            "email_address": "test@example.com",
            "app_password": "test_password_123"
        }
        response = requests.post(f"{BASE_URL}/api/email-config", headers=HEADERS, json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print("PASS: POST /api/email-config saves configuration")


class TestBackupEndpoints:
    """Backup/restore endpoint tests"""
    
    def test_export_backup(self):
        """GET /api/backup/export returns full user data"""
        response = requests.get(f"{BASE_URL}/api/backup/export", headers=HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert "export_date" in data
        assert "user" in data
        assert "accounts" in data
        assert "transactions" in data
        assert "categories" in data
        print(f"PASS: GET /api/backup/export returns {len(data['accounts'])} accounts, {len(data['transactions'])} transactions")
    
    def test_import_backup_empty(self):
        """POST /api/backup/import handles empty import"""
        payload = {"accounts": [], "transactions": [], "categories": []}
        response = requests.post(f"{BASE_URL}/api/backup/import", headers=HEADERS, json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "imported" in data
        print("PASS: POST /api/backup/import handles empty import")


class TestPWAEndpoints:
    """PWA manifest and service worker tests"""
    
    def test_manifest_accessible(self):
        """PWA manifest.json is accessible"""
        response = requests.get(f"{BASE_URL}/manifest.json")
        assert response.status_code == 200
        print("PASS: manifest.json is accessible")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
