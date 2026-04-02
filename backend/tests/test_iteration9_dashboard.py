"""
Iteration 9 Tests: Dashboard Analytics Enhancements
- daily_trend, account_summary, top_creditors, top_debitors fields in analytics/summary
- Date range filtering for analytics
- Transfer exclusion from top_creditors/top_debitors
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


class TestAnalyticsSummaryNewFields:
    """Test new fields in GET /api/analytics/summary"""
    
    def test_analytics_summary_returns_daily_trend(self, auth_headers):
        """Verify daily_trend field is present in analytics summary"""
        response = requests.get(f"{BASE_URL}/api/analytics/summary", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "daily_trend" in data, "daily_trend field missing from response"
        assert isinstance(data["daily_trend"], list), "daily_trend should be a list"
        
        # If there's data, verify structure
        if len(data["daily_trend"]) > 0:
            first_item = data["daily_trend"][0]
            assert "day" in first_item, "daily_trend item should have 'day' field"
            assert "income" in first_item, "daily_trend item should have 'income' field"
            assert "expense" in first_item, "daily_trend item should have 'expense' field"
            print(f"✓ daily_trend has {len(data['daily_trend'])} entries")
    
    def test_analytics_summary_returns_account_summary(self, auth_headers):
        """Verify account_summary field is present with credits/debits"""
        response = requests.get(f"{BASE_URL}/api/analytics/summary", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "account_summary" in data, "account_summary field missing from response"
        assert isinstance(data["account_summary"], list), "account_summary should be a list"
        
        # If there's data, verify structure
        if len(data["account_summary"]) > 0:
            first_item = data["account_summary"][0]
            assert "name" in first_item, "account_summary item should have 'name' field"
            assert "balance" in first_item, "account_summary item should have 'balance' field"
            assert "type" in first_item, "account_summary item should have 'type' field"
            assert "credits" in first_item, "account_summary item should have 'credits' field"
            assert "debits" in first_item, "account_summary item should have 'debits' field"
            print(f"✓ account_summary has {len(data['account_summary'])} accounts with credits/debits")
    
    def test_analytics_summary_returns_top_creditors(self, auth_headers):
        """Verify top_creditors field is present"""
        response = requests.get(f"{BASE_URL}/api/analytics/summary", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "top_creditors" in data, "top_creditors field missing from response"
        assert isinstance(data["top_creditors"], list), "top_creditors should be a list"
        
        # If there's data, verify structure
        if len(data["top_creditors"]) > 0:
            first_item = data["top_creditors"][0]
            assert "description" in first_item, "top_creditors item should have 'description' field"
            assert "amount" in first_item, "top_creditors item should have 'amount' field"
            print(f"✓ top_creditors has {len(data['top_creditors'])} entries")
    
    def test_analytics_summary_returns_top_debitors(self, auth_headers):
        """Verify top_debitors field is present"""
        response = requests.get(f"{BASE_URL}/api/analytics/summary", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "top_debitors" in data, "top_debitors field missing from response"
        assert isinstance(data["top_debitors"], list), "top_debitors should be a list"
        
        # If there's data, verify structure
        if len(data["top_debitors"]) > 0:
            first_item = data["top_debitors"][0]
            assert "description" in first_item, "top_debitors item should have 'description' field"
            assert "amount" in first_item, "top_debitors item should have 'amount' field"
            print(f"✓ top_debitors has {len(data['top_debitors'])} entries")


class TestAnalyticsDateRangeFiltering:
    """Test date range filtering for analytics"""
    
    def test_analytics_with_date_range_returns_filtered_data(self, auth_headers):
        """Verify analytics respects date range filters"""
        # Use a date range that has data (2024)
        response = requests.get(
            f"{BASE_URL}/api/analytics/summary?start_date=2024-04-01&end_date=2024-04-30",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        # Verify all required fields are present
        assert "total_income" in data
        assert "total_expense" in data
        assert "daily_trend" in data
        assert "account_summary" in data
        assert "top_creditors" in data
        assert "top_debitors" in data
        print(f"✓ Date range filter returns all required fields")
    
    def test_analytics_daily_trend_scoped_to_date_range(self, auth_headers):
        """Verify daily_trend is scoped to the date range"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/summary?start_date=2024-04-01&end_date=2024-04-30",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        daily_trend = data.get("daily_trend", [])
        
        # All days should be within April 2024
        for item in daily_trend:
            day = item.get("day", "")
            assert day.startswith("2024-04"), f"Day {day} is outside date range"
        
        print(f"✓ daily_trend scoped to date range ({len(daily_trend)} days)")
    
    def test_analytics_account_summary_scoped_to_date_range(self, auth_headers):
        """Verify account_summary credits/debits are scoped to date range"""
        # Get all-time data
        all_time_response = requests.get(f"{BASE_URL}/api/analytics/summary", headers=auth_headers)
        all_time_data = all_time_response.json()
        
        # Get filtered data
        filtered_response = requests.get(
            f"{BASE_URL}/api/analytics/summary?start_date=2024-04-01&end_date=2024-04-30",
            headers=auth_headers
        )
        filtered_data = filtered_response.json()
        
        # If there's data, filtered credits/debits should be <= all-time
        if len(all_time_data.get("account_summary", [])) > 0 and len(filtered_data.get("account_summary", [])) > 0:
            all_time_credits = sum(a.get("credits", 0) for a in all_time_data["account_summary"])
            filtered_credits = sum(a.get("credits", 0) for a in filtered_data["account_summary"])
            assert filtered_credits <= all_time_credits, "Filtered credits should be <= all-time credits"
            print(f"✓ account_summary credits scoped correctly (filtered: {filtered_credits}, all-time: {all_time_credits})")


class TestTransferExclusion:
    """Test that transfers are excluded from top_creditors and top_debitors"""
    
    def test_top_creditors_excludes_transfers(self, auth_headers):
        """Verify top_creditors excludes transfer transactions"""
        response = requests.get(f"{BASE_URL}/api/analytics/summary", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        top_creditors = data.get("top_creditors", [])
        
        # Check that no transfer-related descriptions appear
        # (This is a heuristic check - transfers typically have "(from account)" in description)
        for creditor in top_creditors:
            desc = creditor.get("description", "").lower()
            # Transfer descriptions created by the app have "(from account)" or "(to account)"
            assert "(from account)" not in desc, f"Transfer found in top_creditors: {desc}"
        
        print(f"✓ top_creditors excludes transfers ({len(top_creditors)} entries)")
    
    def test_top_debitors_excludes_transfers(self, auth_headers):
        """Verify top_debitors excludes transfer transactions"""
        response = requests.get(f"{BASE_URL}/api/analytics/summary", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        top_debitors = data.get("top_debitors", [])
        
        # Check that no transfer-related descriptions appear
        for debitor in top_debitors:
            desc = debitor.get("description", "").lower()
            assert "(to account)" not in desc, f"Transfer found in top_debitors: {desc}"
        
        print(f"✓ top_debitors excludes transfers ({len(top_debitors)} entries)")


class TestAnalyticsResponseStructure:
    """Test overall analytics response structure"""
    
    def test_analytics_summary_all_fields_present(self, auth_headers):
        """Verify all expected fields are present in analytics summary"""
        response = requests.get(f"{BASE_URL}/api/analytics/summary", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        required_fields = [
            "total_income",
            "total_expense", 
            "net_savings",
            "category_breakdown",
            "monthly_trend",
            "daily_trend",
            "account_summary",
            "top_creditors",
            "top_debitors",
            "account_balances"
        ]
        
        for field in required_fields:
            assert field in data, f"Required field '{field}' missing from response"
        
        print(f"✓ All {len(required_fields)} required fields present in analytics summary")
    
    def test_analytics_requires_authentication(self):
        """Verify analytics endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/analytics/summary")
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print("✓ Analytics endpoint requires authentication")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
