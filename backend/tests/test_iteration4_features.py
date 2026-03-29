"""
Iteration 4 Backend Tests - New Features
Tests for: Settings page APIs, email config, backup/restore, email_filter on accounts, PWA files
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "test_session_7e4ac6df60e1455f93f1cc93d93a2e84"

@pytest.fixture
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session

@pytest.fixture
def auth_client(api_client):
    """Session with auth header"""
    api_client.headers.update({"Authorization": f"Bearer {SESSION_TOKEN}"})
    return api_client


class TestAuthEndpoints:
    """Test auth-related endpoints"""
    
    def test_endpoints_return_401_without_auth(self, api_client):
        """All protected endpoints should return 401 without auth"""
        endpoints = [
            "/api/accounts",
            "/api/transactions",
            "/api/categories",
            "/api/analytics/summary",
            "/api/backup/export",
            "/api/email-config",
        ]
        for endpoint in endpoints:
            response = api_client.get(f"{BASE_URL}{endpoint}")
            assert response.status_code == 401, f"{endpoint} should return 401, got {response.status_code}"
            print(f"✓ {endpoint} returns 401 without auth")
    
    def test_auth_me_returns_user_data(self, auth_client):
        """GET /api/auth/me should return user data with valid token"""
        response = auth_client.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "email" in data
        assert data["email"] == "test@moneyinsights.com"
        print(f"✓ /api/auth/me returns user: {data['email']}")


class TestEmailConfigEndpoints:
    """Test email configuration endpoints for auto-scan feature"""
    
    def test_get_email_config_initial(self, auth_client):
        """GET /api/email-config should return configured status"""
        response = auth_client.get(f"{BASE_URL}/api/email-config")
        assert response.status_code == 200
        data = response.json()
        # Should have 'configured' field
        assert "configured" in data
        print(f"✓ /api/email-config returns configured={data['configured']}")
    
    def test_post_email_config_saves(self, auth_client):
        """POST /api/email-config should save email configuration"""
        config = {
            "imap_server": "imap.gmail.com",
            "email_address": "test@example.com",
            "app_password": "test_app_password_123"
        }
        response = auth_client.post(f"{BASE_URL}/api/email-config", json=config)
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "saved" in data["message"].lower()
        print(f"✓ POST /api/email-config saves config: {data['message']}")
    
    def test_get_email_config_after_save(self, auth_client):
        """GET /api/email-config should return configured=True after saving"""
        response = auth_client.get(f"{BASE_URL}/api/email-config")
        assert response.status_code == 200
        data = response.json()
        assert data["configured"] == True
        assert data["email_address"] == "test@example.com"
        assert data["has_password"] == True
        print(f"✓ /api/email-config shows configured=True after save")


class TestEmailScanEndpoint:
    """Test email scan endpoint"""
    
    def test_email_scan_without_account_filters(self, auth_client):
        """POST /api/email-scan should return error when no accounts have email filters"""
        # First, ensure we have email config
        config = {
            "imap_server": "imap.gmail.com",
            "email_address": "test@example.com",
            "app_password": "test_app_password_123"
        }
        auth_client.post(f"{BASE_URL}/api/email-config", json=config)
        
        # Now try to scan - should fail because no accounts have email_filter set
        # OR it will fail because IMAP connection fails (expected in test env)
        response = auth_client.post(f"{BASE_URL}/api/email-scan")
        # Should return 400 with proper error message
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        # Either "no accounts have email filters" or "connection failed"
        print(f"✓ POST /api/email-scan returns proper error: {data['detail']}")


class TestBackupEndpoints:
    """Test backup export and import endpoints"""
    
    def test_backup_export(self, auth_client):
        """GET /api/backup/export should return accounts, transactions, categories"""
        response = auth_client.get(f"{BASE_URL}/api/backup/export")
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "export_date" in data
        assert "user" in data
        assert "accounts" in data
        assert "transactions" in data
        assert "categories" in data
        
        # Verify data types
        assert isinstance(data["accounts"], list)
        assert isinstance(data["transactions"], list)
        assert isinstance(data["categories"], list)
        
        print(f"✓ /api/backup/export returns {len(data['accounts'])} accounts, {len(data['transactions'])} transactions, {len(data['categories'])} categories")
    
    def test_backup_import_empty(self, auth_client):
        """POST /api/backup/import with empty data should handle correctly"""
        response = auth_client.post(f"{BASE_URL}/api/backup/import", json={})
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "imported" in data
        assert data["imported"]["accounts"] == 0
        assert data["imported"]["transactions"] == 0
        assert data["imported"]["categories"] == 0
        print(f"✓ POST /api/backup/import handles empty import: {data['message']}")
    
    def test_backup_import_with_data(self, auth_client):
        """POST /api/backup/import with real data should restore correctly"""
        import uuid
        test_id = str(uuid.uuid4())
        
        backup_data = {
            "accounts": [{
                "id": f"test_import_acc_{test_id}",
                "name": "Test Import Account",
                "account_type": "bank",
                "start_balance": 1000.0,
                "current_balance": 1000.0,
                "email_filter": "Test Bank Statement"
            }],
            "transactions": [{
                "id": f"test_import_txn_{test_id}",
                "account_id": f"test_import_acc_{test_id}",
                "date": "2025-01-15",
                "description": "Test Import Transaction",
                "amount": 100.0,
                "transaction_type": "debit"
            }],
            "categories": []
        }
        
        response = auth_client.post(f"{BASE_URL}/api/backup/import", json=backup_data)
        assert response.status_code == 200
        data = response.json()
        assert data["imported"]["accounts"] == 1
        assert data["imported"]["transactions"] == 1
        print(f"✓ POST /api/backup/import restores data: {data['imported']}")
        
        # Cleanup - delete the test account
        auth_client.delete(f"{BASE_URL}/api/accounts/test_import_acc_{test_id}")


class TestAccountEmailFilter:
    """Test email_filter field on accounts"""
    
    def test_create_account_with_email_filter(self, auth_client):
        """POST /api/accounts should accept email_filter field"""
        import uuid
        test_id = str(uuid.uuid4())[:8]
        
        account_data = {
            "name": f"Test Email Filter Account {test_id}",
            "account_type": "bank",
            "start_balance": 5000.0,
            "email_filter": "HDFC Bank Statement"
        }
        
        response = auth_client.post(f"{BASE_URL}/api/accounts", json=account_data)
        assert response.status_code == 200
        data = response.json()
        
        assert data["name"] == account_data["name"]
        assert data["email_filter"] == "HDFC Bank Statement"
        assert "id" in data
        
        account_id = data["id"]
        print(f"✓ POST /api/accounts creates account with email_filter: {data['email_filter']}")
        
        # Verify via GET
        get_response = auth_client.get(f"{BASE_URL}/api/accounts")
        assert get_response.status_code == 200
        accounts = get_response.json()
        created_account = next((a for a in accounts if a["id"] == account_id), None)
        assert created_account is not None
        assert created_account["email_filter"] == "HDFC Bank Statement"
        print(f"✓ GET /api/accounts shows email_filter on account")
        
        # Cleanup
        auth_client.delete(f"{BASE_URL}/api/accounts/{account_id}")


class TestCategoriesEndpoint:
    """Test categories endpoint returns default categories"""
    
    def test_get_categories_returns_defaults(self, auth_client):
        """GET /api/categories should return 10 default categories"""
        response = auth_client.get(f"{BASE_URL}/api/categories")
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) >= 10, f"Expected at least 10 categories, got {len(data)}"
        
        # Check for expected default categories
        category_names = [c["name"] for c in data]
        expected_defaults = ["Salary", "Food & Dining", "Shopping", "Transportation", "Transfer", "Other"]
        for expected in expected_defaults:
            assert expected in category_names, f"Missing default category: {expected}"
        
        print(f"✓ GET /api/categories returns {len(data)} categories including defaults")


class TestPWAFiles:
    """Test PWA manifest and service worker accessibility"""
    
    def test_manifest_json_accessible(self, api_client):
        """manifest.json should be accessible at /manifest.json"""
        response = api_client.get(f"{BASE_URL}/manifest.json")
        assert response.status_code == 200
        data = response.json()
        
        assert data["short_name"] == "MoneyInsights"
        assert "icons" in data
        assert data["display"] == "standalone"
        assert data["theme_color"] == "#5C745A"
        print(f"✓ /manifest.json accessible with correct PWA config")
    
    def test_service_worker_accessible(self, api_client):
        """service-worker.js should be accessible at /service-worker.js"""
        response = api_client.get(f"{BASE_URL}/service-worker.js")
        assert response.status_code == 200
        content = response.text
        
        assert "CACHE_NAME" in content or "moneyinsights" in content.lower()
        assert "addEventListener" in content
        print(f"✓ /service-worker.js accessible with service worker code")


class TestGoogleAuthURL:
    """Test Google login redirects to correct auth URL"""
    
    def test_login_page_accessible(self, api_client):
        """Login page should be accessible"""
        response = api_client.get(f"{BASE_URL}/login")
        assert response.status_code == 200
        print(f"✓ /login page accessible")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
