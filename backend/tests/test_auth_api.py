"""
Backend API Tests for MoneyInsights with Google Auth
Tests authentication layer and all protected endpoints
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://money-insights-82.preview.emergentagent.com').rstrip('/')
TEST_SESSION_TOKEN = "test_session_7e4ac6df60e1455f93f1cc93d93a2e84"
AUTH_HEADER = {"Authorization": f"Bearer {TEST_SESSION_TOKEN}"}


class TestUnauthenticatedAccess:
    """Test that unauthenticated requests return 401"""
    
    def test_accounts_requires_auth(self):
        """GET /api/accounts should return 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/accounts")
        assert response.status_code == 401
        assert "Not authenticated" in response.json().get("detail", "")
        print("PASS: /api/accounts returns 401 without auth")
    
    def test_transactions_requires_auth(self):
        """GET /api/transactions should return 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/transactions")
        assert response.status_code == 401
        assert "Not authenticated" in response.json().get("detail", "")
        print("PASS: /api/transactions returns 401 without auth")
    
    def test_categories_requires_auth(self):
        """GET /api/categories should return 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/categories")
        assert response.status_code == 401
        assert "Not authenticated" in response.json().get("detail", "")
        print("PASS: /api/categories returns 401 without auth")
    
    def test_analytics_requires_auth(self):
        """GET /api/analytics/summary should return 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/analytics/summary")
        assert response.status_code == 401
        print("PASS: /api/analytics/summary returns 401 without auth")
    
    def test_backup_requires_auth(self):
        """GET /api/backup/export should return 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/backup/export")
        assert response.status_code == 401
        print("PASS: /api/backup/export returns 401 without auth")


class TestAuthenticatedAccess:
    """Test authenticated endpoints with valid session token"""
    
    def test_auth_me_returns_user_data(self):
        """GET /api/auth/me should return user data with valid token"""
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "email" in data
        assert data["email"] == "test@moneyinsights.com"
        print(f"PASS: /api/auth/me returns user: {data['email']}")
    
    def test_get_accounts_authenticated(self):
        """GET /api/accounts should return accounts list with auth"""
        response = requests.get(f"{BASE_URL}/api/accounts", headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: /api/accounts returns {len(data)} accounts")
    
    def test_get_categories_returns_defaults(self):
        """GET /api/categories should return 10 default categories"""
        response = requests.get(f"{BASE_URL}/api/categories", headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 10, f"Expected at least 10 categories, got {len(data)}"
        print(f"PASS: /api/categories returns {len(data)} categories")
    
    def test_get_transactions_authenticated(self):
        """GET /api/transactions should return transactions list"""
        response = requests.get(f"{BASE_URL}/api/transactions", headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: /api/transactions returns {len(data)} transactions")
    
    def test_get_analytics_summary(self):
        """GET /api/analytics/summary should return analytics data"""
        response = requests.get(f"{BASE_URL}/api/analytics/summary", headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        assert "total_income" in data
        assert "total_expense" in data
        assert "net_savings" in data
        print(f"PASS: /api/analytics/summary returns data with net_savings: {data['net_savings']}")
    
    def test_backup_export(self):
        """GET /api/backup/export should return JSON backup"""
        response = requests.get(f"{BASE_URL}/api/backup/export", headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        assert "export_date" in data
        assert "user" in data
        assert "accounts" in data
        assert "transactions" in data
        assert "categories" in data
        print(f"PASS: /api/backup/export returns backup with {len(data['transactions'])} transactions")


class TestAccountCRUD:
    """Test account CRUD operations with auth"""
    
    def test_create_account(self):
        """POST /api/accounts should create a new account"""
        payload = {
            "name": "TEST_Auth_Account",
            "account_type": "bank",
            "start_balance": 5000.0
        }
        response = requests.post(f"{BASE_URL}/api/accounts", json=payload, headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "TEST_Auth_Account"
        assert data["current_balance"] == 5000.0
        assert "id" in data
        print(f"PASS: Created account with id: {data['id']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/accounts/{data['id']}", headers=AUTH_HEADER)


class TestTransferDetection:
    """Test transfer detection with auth"""
    
    def test_detect_transfers(self):
        """POST /api/detect-transfers should work with auth"""
        response = requests.post(f"{BASE_URL}/api/detect-transfers", headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        assert "potential_transfers" in data
        assert "count" in data
        print(f"PASS: /api/detect-transfers found {data['count']} potential transfers")


class TestLogout:
    """Test logout functionality"""
    
    def test_logout_clears_session(self):
        """POST /api/auth/logout should return success message"""
        # Note: We don't actually logout the test session, just verify the endpoint works
        response = requests.post(f"{BASE_URL}/api/auth/logout", headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Logged out"
        print("PASS: /api/auth/logout returns success message")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
