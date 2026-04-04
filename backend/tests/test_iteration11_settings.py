"""
Iteration 11 Tests: Settings Refactor, Category Expansion, FY Endpoints, AI Categorization
Tests for:
1. Settings page 3 tabs (Finance Tracker, Accounting, Appearance & Data)
2. Company details form in Settings Accounting tab
3. Financial Year endpoint and FY list
4. Categories restore-defaults endpoint
5. AI categorize endpoint with prompt_used in response
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
AUTH_HEADER = {"Authorization": "Bearer test_session_7e4ac6df60e1455f93f1cc93d93a2e84"}


class TestCategoriesEndpoints:
    """Test categories CRUD and restore-defaults"""
    
    def test_get_categories_returns_list(self):
        """GET /api/categories returns categories list"""
        response = requests.get(f"{BASE_URL}/api/categories", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        assert len(data) > 0, "Should have at least some categories"
        
        # Check category structure
        cat = data[0]
        assert "id" in cat, "Category should have id"
        assert "name" in cat, "Category should have name"
        assert "category_type" in cat, "Category should have category_type"
        assert "color" in cat, "Category should have color"
        assert "is_default" in cat, "Category should have is_default"
        print(f"✓ GET /api/categories returned {len(data)} categories")
    
    def test_categories_auto_restore_if_empty(self):
        """GET /api/categories auto-restores defaults if empty (tested via count)"""
        response = requests.get(f"{BASE_URL}/api/categories", headers=AUTH_HEADER)
        assert response.status_code == 200
        
        data = response.json()
        # After restore-defaults, should have ~48+ categories
        # The test user already has categories, so just verify count > 10
        assert len(data) >= 10, f"Should have at least 10 categories, got {len(data)}"
        print(f"✓ Categories count: {len(data)} (includes defaults)")
    
    def test_restore_defaults_endpoint(self):
        """POST /api/categories/restore-defaults restores missing default categories"""
        response = requests.post(f"{BASE_URL}/api/categories/restore-defaults", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response should have message"
        assert "restored" in data, "Response should have restored count"
        assert isinstance(data["restored"], int), "restored should be an integer"
        print(f"✓ POST /api/categories/restore-defaults: {data['message']}")
    
    def test_categories_have_expanded_defaults(self):
        """Verify expanded default categories exist (40-50 range)"""
        response = requests.get(f"{BASE_URL}/api/categories", headers=AUTH_HEADER)
        assert response.status_code == 200
        
        data = response.json()
        default_cats = [c for c in data if c.get("is_default")]
        
        # Check for some of the new expanded categories
        cat_names = [c["name"] for c in data]
        expected_new_cats = [
            "Groceries", "Dining Out / Restaurants", "Food Delivery",
            "Rent", "Electricity", "Internet & WiFi",
            "Fuel / Petrol", "Cab / Auto / Uber",
            "EMI / Loan Repayment", "Subscriptions / OTT"
        ]
        
        found_new = [c for c in expected_new_cats if c in cat_names]
        print(f"✓ Found {len(found_new)}/{len(expected_new_cats)} expanded default categories")
        assert len(found_new) >= 5, f"Should have at least 5 of the new expanded categories, found {len(found_new)}"


class TestFinancialYearsEndpoint:
    """Test financial years endpoint"""
    
    def test_get_financial_years(self):
        """GET /api/financial-years returns FY list with current FY"""
        response = requests.get(f"{BASE_URL}/api/financial-years", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "years" in data, "Response should have years list"
        assert "current_fy" in data, "Response should have current_fy"
        
        # Verify years structure
        assert isinstance(data["years"], list), "years should be a list"
        if len(data["years"]) > 0:
            fy = data["years"][0]
            assert "label" in fy, "FY should have label"
            assert "start" in fy, "FY should have start date"
            assert "end" in fy, "FY should have end date"
            # Label format: "FY 2025-26"
            assert fy["label"].startswith("FY "), f"FY label should start with 'FY ', got {fy['label']}"
        
        # Verify current_fy format
        assert data["current_fy"].startswith("FY "), f"current_fy should start with 'FY ', got {data['current_fy']}"
        print(f"✓ GET /api/financial-years: {len(data['years'])} years, current: {data['current_fy']}")
    
    def test_financial_years_computed_from_data(self):
        """FY list is computed from voucher/transaction date ranges"""
        response = requests.get(f"{BASE_URL}/api/financial-years", headers=AUTH_HEADER)
        assert response.status_code == 200
        
        data = response.json()
        # Should have at least current FY
        assert len(data["years"]) >= 1, "Should have at least current FY"
        
        # Verify date format (YYYY-MM-DD)
        if len(data["years"]) > 0:
            fy = data["years"][0]
            import re
            date_pattern = r"^\d{4}-\d{2}-\d{2}$"
            assert re.match(date_pattern, fy["start"]), f"Start date should be YYYY-MM-DD, got {fy['start']}"
            assert re.match(date_pattern, fy["end"]), f"End date should be YYYY-MM-DD, got {fy['end']}"
        print(f"✓ FY dates are in correct format")


class TestCompanyEndpoints:
    """Test company CRUD endpoints"""
    
    def test_get_company(self):
        """GET /api/company returns company details"""
        response = requests.get(f"{BASE_URL}/api/company", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "id" in data, "Company should have id"
        assert "name" in data, "Company should have name"
        assert "user_id" in data, "Company should have user_id"
        assert "fy_start_month" in data, "Company should have fy_start_month"
        print(f"✓ GET /api/company: {data['name']}")
    
    def test_update_company(self):
        """PUT /api/company updates company details"""
        # First get current company
        get_response = requests.get(f"{BASE_URL}/api/company", headers=AUTH_HEADER)
        assert get_response.status_code == 200
        original = get_response.json()
        
        # Update with test data
        update_data = {
            "name": "TEST_Company_Iter11",
            "address": "TEST 123 Test Street",
            "gstin": "22AAAAA0000A1Z5",
            "pan": "AAAAA0000A",
            "cin": "U12345MH2020PTC123456",
            "fy_start_month": 4
        }
        
        response = requests.put(f"{BASE_URL}/api/company", headers=AUTH_HEADER, json=update_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify update persisted
        verify_response = requests.get(f"{BASE_URL}/api/company", headers=AUTH_HEADER)
        assert verify_response.status_code == 200
        updated = verify_response.json()
        
        assert updated["name"] == update_data["name"], f"Name not updated: {updated['name']}"
        assert updated["address"] == update_data["address"], f"Address not updated: {updated['address']}"
        assert updated["gstin"] == update_data["gstin"], f"GSTIN not updated: {updated['gstin']}"
        assert updated["pan"] == update_data["pan"], f"PAN not updated: {updated['pan']}"
        print(f"✓ PUT /api/company: Updated to {updated['name']}")
        
        # Restore original
        restore_data = {
            "name": original.get("name", "My Business"),
            "address": original.get("address", ""),
            "gstin": original.get("gstin", ""),
            "pan": original.get("pan", ""),
            "cin": original.get("cin", ""),
            "fy_start_month": original.get("fy_start_month", 4)
        }
        requests.put(f"{BASE_URL}/api/company", headers=AUTH_HEADER, json=restore_data)


class TestAICategorizeEndpoint:
    """Test AI categorization endpoint"""
    
    def test_ai_categorize_returns_prompt_used(self):
        """POST /api/ai-categorize returns prompt_used in response"""
        # This endpoint requires uncategorized transactions to work
        # We'll test that it returns the expected structure
        response = requests.post(f"{BASE_URL}/api/ai-categorize", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response should have message"
        assert "categorized_count" in data, "Response should have categorized_count"
        
        # If there were transactions to categorize, prompt_used should be present
        # If no uncategorized transactions, it returns early without prompt_used
        if data.get("total_uncategorized", 0) > 0:
            assert "prompt_used" in data, "Response should have prompt_used when transactions exist"
            assert len(data["prompt_used"]) > 0, "prompt_used should not be empty"
            print(f"✓ POST /api/ai-categorize: {data['message']}, prompt_used present")
        else:
            print(f"✓ POST /api/ai-categorize: {data['message']} (no uncategorized transactions)")
    
    def test_ai_categorize_with_empty_transaction_ids(self):
        """POST /api/ai-categorize with empty transaction_ids processes all uncategorized"""
        response = requests.post(
            f"{BASE_URL}/api/ai-categorize",
            headers=AUTH_HEADER,
            params={"transaction_ids": []}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ POST /api/ai-categorize with empty transaction_ids works")


class TestAuthRequired:
    """Test that all endpoints require authentication"""
    
    def test_categories_requires_auth(self):
        """GET /api/categories requires authentication"""
        response = requests.get(f"{BASE_URL}/api/categories")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ GET /api/categories requires auth")
    
    def test_financial_years_requires_auth(self):
        """GET /api/financial-years requires authentication"""
        response = requests.get(f"{BASE_URL}/api/financial-years")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ GET /api/financial-years requires auth")
    
    def test_company_requires_auth(self):
        """GET /api/company requires authentication"""
        response = requests.get(f"{BASE_URL}/api/company")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ GET /api/company requires auth")
    
    def test_restore_defaults_requires_auth(self):
        """POST /api/categories/restore-defaults requires authentication"""
        response = requests.post(f"{BASE_URL}/api/categories/restore-defaults")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ POST /api/categories/restore-defaults requires auth")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
