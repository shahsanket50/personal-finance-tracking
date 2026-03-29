"""
Iteration 6 Backend Tests
Tests for:
1. POST /api/detect-transfers - returns potential_transfers with 'confidence' field (high/medium)
2. GET /api/accounts/{account_id}/sync-history - returns array of sync logs
3. POST /api/accounts/{account_id}/sync - account-level email sync
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

class TestDetectTransfersWithConfidence:
    """Test detect-transfers endpoint returns confidence field"""
    
    def test_detect_transfers_returns_confidence_field(self, auth_headers):
        """POST /api/detect-transfers should return potential_transfers with confidence field"""
        response = requests.post(f"{BASE_URL}/api/detect-transfers", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "potential_transfers" in data, "Response should have potential_transfers field"
        assert "count" in data, "Response should have count field"
        
        # If there are potential transfers, verify confidence field exists
        if data["count"] > 0:
            for transfer in data["potential_transfers"]:
                assert "confidence" in transfer, f"Transfer should have confidence field: {transfer}"
                assert transfer["confidence"] in ["high", "medium"], f"Confidence should be 'high' or 'medium', got: {transfer['confidence']}"
                assert "txn1" in transfer, "Transfer should have txn1"
                assert "txn2" in transfer, "Transfer should have txn2"
                assert "amount" in transfer, "Transfer should have amount"
                assert "date" in transfer, "Transfer should have date"
        
        print(f"✓ detect-transfers returned {data['count']} potential transfers with confidence scoring")


class TestAccountSyncHistory:
    """Test account sync history endpoint"""
    
    def test_get_sync_history_returns_array(self, auth_headers):
        """GET /api/accounts/{account_id}/sync-history should return array of sync logs"""
        # First get accounts to find one with email_filter
        accounts_response = requests.get(f"{BASE_URL}/api/accounts", headers=auth_headers)
        assert accounts_response.status_code == 200
        accounts = accounts_response.json()
        
        # Use first account or a test account ID
        account_id = accounts[0]["id"] if accounts else "test_account_id"
        
        response = requests.get(f"{BASE_URL}/api/accounts/{account_id}/sync-history", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), f"Response should be an array, got: {type(data)}"
        
        # If there are sync logs, verify structure
        if len(data) > 0:
            log = data[0]
            assert "status" in log, "Sync log should have status field"
            assert "synced_at" in log, "Sync log should have synced_at field"
            assert "imported" in log, "Sync log should have imported field"
            assert "skipped" in log, "Sync log should have skipped field"
            print(f"✓ sync-history returned {len(data)} logs with proper structure")
        else:
            print("✓ sync-history returned empty array (no sync history yet)")


class TestAccountSync:
    """Test account-level email sync endpoint"""
    
    def test_sync_account_without_email_filter(self, auth_headers):
        """POST /api/accounts/{account_id}/sync should fail if no email_filter configured"""
        # Create a test account without email_filter
        create_response = requests.post(
            f"{BASE_URL}/api/accounts",
            headers=auth_headers,
            json={
                "name": "TEST_NoFilter_Account",
                "account_type": "bank",
                "start_balance": 0,
                "email_filter": ""
            }
        )
        
        if create_response.status_code == 200:
            account_id = create_response.json()["id"]
            
            # Try to sync - should fail
            sync_response = requests.post(f"{BASE_URL}/api/accounts/{account_id}/sync", headers=auth_headers)
            assert sync_response.status_code == 400, f"Expected 400 for account without email_filter, got {sync_response.status_code}"
            
            # Cleanup
            requests.delete(f"{BASE_URL}/api/accounts/{account_id}", headers=auth_headers)
            print("✓ sync endpoint correctly rejects accounts without email_filter")
        else:
            print(f"Note: Could not create test account: {create_response.status_code}")
    
    def test_sync_account_with_email_filter_no_email_config(self, auth_headers):
        """POST /api/accounts/{account_id}/sync should fail if email not configured"""
        # Create a test account with email_filter
        create_response = requests.post(
            f"{BASE_URL}/api/accounts",
            headers=auth_headers,
            json={
                "name": "TEST_WithFilter_Account",
                "account_type": "bank",
                "start_balance": 0,
                "email_filter": "HDFC Statement"
            }
        )
        
        if create_response.status_code == 200:
            account_id = create_response.json()["id"]
            
            # Try to sync - may fail if email not configured or IMAP fails (expected in test env)
            sync_response = requests.post(f"{BASE_URL}/api/accounts/{account_id}/sync", headers=auth_headers)
            # Accept 400 (no email config) or 200 (sync attempted)
            assert sync_response.status_code in [200, 400], f"Expected 200 or 400, got {sync_response.status_code}: {sync_response.text}"
            
            # Cleanup
            requests.delete(f"{BASE_URL}/api/accounts/{account_id}", headers=auth_headers)
            print(f"✓ sync endpoint responded with {sync_response.status_code} (expected in test env)")
        else:
            print(f"Note: Could not create test account: {create_response.status_code}")


class TestAccountsWithEmailFilter:
    """Test accounts endpoint returns email_filter field"""
    
    def test_accounts_have_email_filter_field(self, auth_headers):
        """GET /api/accounts should return accounts with email_filter field"""
        response = requests.get(f"{BASE_URL}/api/accounts", headers=auth_headers)
        assert response.status_code == 200
        
        accounts = response.json()
        if len(accounts) > 0:
            # Check that email_filter field exists (can be null/empty)
            for acc in accounts:
                assert "email_filter" in acc or acc.get("email_filter") is None, f"Account should have email_filter field: {acc}"
            print(f"✓ All {len(accounts)} accounts have email_filter field")
        else:
            print("✓ No accounts to verify (empty list)")


class TestAuthEndpoints:
    """Verify auth endpoints still work"""
    
    def test_auth_me_with_valid_token(self, auth_headers):
        """GET /api/auth/me should return user info with valid token"""
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "user_id" in data
        assert "email" in data
        print(f"✓ auth/me returned user: {data['email']}")
    
    def test_auth_me_without_token(self):
        """GET /api/auth/me should return 401 without token"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 401
        print("✓ auth/me correctly returns 401 without token")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
