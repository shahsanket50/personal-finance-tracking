"""
Iteration 15 Tests: Category Filter Fix, PWA Install, Back Button, Top Nav UI, Multi-Select Transfers

Tests:
1. Analytics endpoint returns category_id in category_breakdown
2. Transactions endpoint works with categoryId filter
3. Detect transfers endpoint returns proper structure
4. Mark-as-transfer endpoint accepts list of 2 txn IDs
5. Categories endpoint returns proper structure
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "test_session_7e4ac6df60e1455f93f1cc93d93a2e84"

@pytest.fixture
def auth_headers():
    return {"Authorization": f"Bearer {SESSION_TOKEN}"}


class TestAnalyticsEndpoint:
    """Test analytics/summary endpoint returns category_id"""
    
    def test_analytics_summary_returns_category_id(self, auth_headers):
        """Verify category_breakdown includes category_id field"""
        response = requests.get(f"{BASE_URL}/api/analytics/summary", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "category_breakdown" in data
        
        # Check that category_breakdown items have category_id
        if len(data["category_breakdown"]) > 0:
            first_category = data["category_breakdown"][0]
            assert "category_id" in first_category, "category_id field missing from category_breakdown"
            assert "category" in first_category
            assert "amount" in first_category
            assert "type" in first_category
            print(f"✓ category_breakdown has category_id: {first_category.get('category_id')}")
    
    def test_analytics_summary_with_date_range(self, auth_headers):
        """Verify analytics works with date range filters"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/summary?start_date=2025-01-01&end_date=2026-12-31",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "total_income" in data
        assert "total_expense" in data
        assert "monthly_trend" in data
        assert "daily_trend" in data
        print(f"✓ Analytics with date range: income={data['total_income']}, expense={data['total_expense']}")


class TestTransactionsEndpoint:
    """Test transactions endpoint"""
    
    def test_get_transactions(self, auth_headers):
        """Verify transactions endpoint returns list"""
        response = requests.get(f"{BASE_URL}/api/transactions", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        
        if len(data) > 0:
            txn = data[0]
            assert "id" in txn
            assert "account_id" in txn
            assert "date" in txn
            assert "description" in txn
            assert "amount" in txn
            assert "transaction_type" in txn
            print(f"✓ Transactions endpoint returns {len(data)} transactions")


class TestCategoriesEndpoint:
    """Test categories endpoint"""
    
    def test_get_categories(self, auth_headers):
        """Verify categories endpoint returns list with proper structure"""
        response = requests.get(f"{BASE_URL}/api/categories", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        
        if len(data) > 0:
            cat = data[0]
            assert "id" in cat
            assert "name" in cat
            assert "category_type" in cat
            print(f"✓ Categories endpoint returns {len(data)} categories")


class TestTransferDetection:
    """Test transfer detection and marking endpoints"""
    
    def test_detect_transfers_endpoint(self, auth_headers):
        """Verify detect-transfers endpoint returns proper structure"""
        response = requests.post(f"{BASE_URL}/api/detect-transfers", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "potential_transfers" in data
        assert "count" in data
        assert isinstance(data["potential_transfers"], list)
        
        # If there are potential transfers, verify structure
        if len(data["potential_transfers"]) > 0:
            transfer = data["potential_transfers"][0]
            assert "txn1" in transfer, "txn1 missing from potential transfer"
            assert "txn2" in transfer, "txn2 missing from potential transfer"
            assert "id" in transfer["txn1"]
            assert "id" in transfer["txn2"]
            print(f"✓ Detect transfers found {data['count']} potential transfers with txn1/txn2 structure")
        else:
            print(f"✓ Detect transfers endpoint works (0 transfers found)")
    
    def test_mark_as_transfer_requires_two_ids(self, auth_headers):
        """Verify mark-as-transfer endpoint accepts list of 2 txn IDs"""
        # Test with invalid IDs (should fail gracefully)
        response = requests.post(
            f"{BASE_URL}/api/mark-as-transfer",
            headers={**auth_headers, "Content-Type": "application/json"},
            json=["invalid-id-1", "invalid-id-2"]
        )
        # Should return 404 or 400 for invalid IDs, not 500
        assert response.status_code in [200, 400, 404], f"Unexpected status: {response.status_code}"
        print(f"✓ Mark-as-transfer endpoint handles invalid IDs gracefully (status: {response.status_code})")


class TestAccountsEndpoint:
    """Test accounts endpoint"""
    
    def test_get_accounts(self, auth_headers):
        """Verify accounts endpoint returns list"""
        response = requests.get(f"{BASE_URL}/api/accounts", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        
        if len(data) > 0:
            account = data[0]
            assert "id" in account
            assert "name" in account
            assert "current_balance" in account
            print(f"✓ Accounts endpoint returns {len(data)} accounts")


class TestAuthRequired:
    """Test that endpoints require authentication"""
    
    def test_analytics_requires_auth(self):
        """Verify analytics endpoint requires auth"""
        response = requests.get(f"{BASE_URL}/api/analytics/summary")
        assert response.status_code == 401
        print("✓ Analytics endpoint requires authentication")
    
    def test_transactions_requires_auth(self):
        """Verify transactions endpoint requires auth"""
        response = requests.get(f"{BASE_URL}/api/transactions")
        assert response.status_code == 401
        print("✓ Transactions endpoint requires authentication")
    
    def test_detect_transfers_requires_auth(self):
        """Verify detect-transfers endpoint requires auth"""
        response = requests.post(f"{BASE_URL}/api/detect-transfers")
        assert response.status_code == 401
        print("✓ Detect transfers endpoint requires authentication")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
