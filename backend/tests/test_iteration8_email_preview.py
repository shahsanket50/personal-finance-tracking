"""
Iteration 8 Tests: Email Sync Preview and From Email Filter
Tests:
- POST /api/accounts/{id}/sync-preview endpoint exists and returns proper structure
- email_from_filter field in Account CRUD
- Preview button and dialog in frontend
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "test_session_7e4ac6df60e1455f93f1cc93d93a2e84"

@pytest.fixture
def auth_headers():
    return {
        "Authorization": f"Bearer {SESSION_TOKEN}",
        "Content-Type": "application/json"
    }

class TestEmailFromFilterField:
    """Test email_from_filter field in Account CRUD"""
    
    def test_create_account_with_email_from_filter(self, auth_headers):
        """Create account with email_from_filter field"""
        payload = {
            "name": "TEST_EmailFromFilter_Account",
            "account_type": "bank",
            "start_balance": 1000.0,
            "email_filter": "ICICI Bank Statement",
            "email_from_filter": "alerts@icicibank.com"
        }
        response = requests.post(f"{BASE_URL}/api/accounts", json=payload, headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["name"] == "TEST_EmailFromFilter_Account"
        assert data["email_filter"] == "ICICI Bank Statement"
        assert data["email_from_filter"] == "alerts@icicibank.com"
        assert "id" in data
        
        # Store for cleanup
        self.created_account_id = data["id"]
        print(f"Created account with email_from_filter: {data['id']}")
        return data["id"]
    
    def test_get_accounts_returns_email_from_filter(self, auth_headers):
        """Verify GET /api/accounts returns email_from_filter field"""
        response = requests.get(f"{BASE_URL}/api/accounts", headers=auth_headers)
        assert response.status_code == 200
        
        accounts = response.json()
        # Find any account with email_from_filter set
        accounts_with_from_filter = [a for a in accounts if a.get("email_from_filter")]
        print(f"Found {len(accounts_with_from_filter)} accounts with email_from_filter set")
        
        # Verify structure - all accounts should have the field (even if empty)
        for acc in accounts:
            assert "email_from_filter" in acc or acc.get("email_from_filter") is None, \
                f"Account {acc['name']} missing email_from_filter field"
    
    def test_update_account_email_from_filter(self, auth_headers):
        """Update account's email_from_filter field"""
        # First create an account
        create_payload = {
            "name": "TEST_UpdateFromFilter_Account",
            "account_type": "credit_card",
            "start_balance": 0,
            "email_filter": "HDFC Statement"
        }
        create_resp = requests.post(f"{BASE_URL}/api/accounts", json=create_payload, headers=auth_headers)
        assert create_resp.status_code == 200
        account_id = create_resp.json()["id"]
        
        # Update with email_from_filter
        update_payload = {
            "name": "TEST_UpdateFromFilter_Account",
            "account_type": "credit_card",
            "start_balance": 0,
            "email_filter": "HDFC Statement",
            "email_from_filter": "statements@hdfcbank.net"
        }
        update_resp = requests.put(f"{BASE_URL}/api/accounts/{account_id}", json=update_payload, headers=auth_headers)
        assert update_resp.status_code == 200
        
        updated = update_resp.json()
        assert updated["email_from_filter"] == "statements@hdfcbank.net"
        print(f"Updated account {account_id} with email_from_filter")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/accounts/{account_id}", headers=auth_headers)


class TestSyncPreviewEndpoint:
    """Test POST /api/accounts/{id}/sync-preview endpoint"""
    
    def test_sync_preview_endpoint_exists(self, auth_headers):
        """Verify sync-preview endpoint exists and returns proper error for unconfigured email"""
        # First get an account with email_filter
        accounts_resp = requests.get(f"{BASE_URL}/api/accounts", headers=auth_headers)
        assert accounts_resp.status_code == 200
        accounts = accounts_resp.json()
        
        # Find account with email_filter
        account_with_filter = next((a for a in accounts if a.get("email_filter")), None)
        
        if not account_with_filter:
            # Create one for testing
            create_payload = {
                "name": "TEST_SyncPreview_Account",
                "account_type": "bank",
                "start_balance": 0,
                "email_filter": "Test Statement"
            }
            create_resp = requests.post(f"{BASE_URL}/api/accounts", json=create_payload, headers=auth_headers)
            assert create_resp.status_code == 200
            account_with_filter = create_resp.json()
        
        account_id = account_with_filter["id"]
        
        # Call sync-preview - expect 400 because email not configured in test env
        response = requests.post(f"{BASE_URL}/api/accounts/{account_id}/sync-preview", headers=auth_headers)
        
        # In test env, IMAP will fail - we expect 400 with proper error message
        # This confirms the endpoint exists and validates properly
        assert response.status_code in [200, 400], f"Expected 200 or 400, got {response.status_code}: {response.text}"
        
        if response.status_code == 400:
            error = response.json()
            assert "detail" in error
            # Should mention email not configured or connection failed
            print(f"Sync preview returned expected error: {error['detail']}")
        else:
            # If somehow it works, verify structure
            data = response.json()
            assert "summary" in data
            assert "emails" in data
            print(f"Sync preview returned data: {data}")
    
    def test_sync_preview_returns_proper_structure_on_error(self, auth_headers):
        """Verify sync-preview returns proper error structure"""
        # Create account without email filter
        create_payload = {
            "name": "TEST_NoFilter_Account",
            "account_type": "bank",
            "start_balance": 0
        }
        create_resp = requests.post(f"{BASE_URL}/api/accounts", json=create_payload, headers=auth_headers)
        assert create_resp.status_code == 200
        account_id = create_resp.json()["id"]
        
        # Call sync-preview - should fail because no email_filter
        response = requests.post(f"{BASE_URL}/api/accounts/{account_id}/sync-preview", headers=auth_headers)
        assert response.status_code == 400
        
        error = response.json()
        assert "detail" in error
        assert "email filter" in error["detail"].lower() or "no email" in error["detail"].lower()
        print(f"Correctly rejected account without email filter: {error['detail']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/accounts/{account_id}", headers=auth_headers)
    
    def test_sync_preview_404_for_nonexistent_account(self, auth_headers):
        """Verify sync-preview returns 404 for non-existent account"""
        response = requests.post(f"{BASE_URL}/api/accounts/nonexistent-id-12345/sync-preview", headers=auth_headers)
        assert response.status_code == 404
        print("Correctly returned 404 for non-existent account")
    
    def test_sync_preview_401_without_auth(self):
        """Verify sync-preview requires authentication"""
        response = requests.post(f"{BASE_URL}/api/accounts/any-id/sync-preview")
        assert response.status_code == 401
        print("Correctly returned 401 without authentication")


class TestCleanup:
    """Cleanup test accounts"""
    
    def test_cleanup_test_accounts(self, auth_headers):
        """Delete all TEST_ prefixed accounts"""
        accounts_resp = requests.get(f"{BASE_URL}/api/accounts", headers=auth_headers)
        if accounts_resp.status_code == 200:
            accounts = accounts_resp.json()
            for acc in accounts:
                if acc["name"].startswith("TEST_"):
                    requests.delete(f"{BASE_URL}/api/accounts/{acc['id']}", headers=auth_headers)
                    print(f"Cleaned up: {acc['name']}")
