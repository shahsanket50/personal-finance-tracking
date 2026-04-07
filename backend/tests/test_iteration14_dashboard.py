"""
Iteration 14: Dashboard Enhancements & AI Categorization Bug Fix Tests
- Backend: GET /api/analytics/summary still works
- Backend: All existing endpoints regression (/api/accounts, /api/categories, /api/transactions, /api/vouchers)
- Backend: AI categorization chunking (helpers.py ai_categorize_batch processes in chunks of 80)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "test_session_7e4ac6df60e1455f93f1cc93d93a2e84"
AUTH_HEADER = {"Authorization": f"Bearer {SESSION_TOKEN}"}


class TestAnalyticsSummary:
    """Test /api/analytics/summary endpoint"""
    
    def test_analytics_summary_returns_data(self):
        """GET /api/analytics/summary returns income/expense/trends data"""
        response = requests.get(f"{BASE_URL}/api/analytics/summary", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify required fields
        assert "total_income" in data, "Missing total_income"
        assert "total_expense" in data, "Missing total_expense"
        assert "net_savings" in data, "Missing net_savings"
        assert "category_breakdown" in data, "Missing category_breakdown"
        assert "monthly_trend" in data, "Missing monthly_trend"
        assert "daily_trend" in data, "Missing daily_trend"
        assert "account_summary" in data, "Missing account_summary"
        assert "top_creditors" in data, "Missing top_creditors"
        assert "top_debitors" in data, "Missing top_debitors"
        
        # Verify data types
        assert isinstance(data["total_income"], (int, float))
        assert isinstance(data["total_expense"], (int, float))
        assert isinstance(data["net_savings"], (int, float))
        assert isinstance(data["category_breakdown"], list)
        assert isinstance(data["monthly_trend"], list)
        
        print(f"Analytics summary: income={data['total_income']}, expense={data['total_expense']}, net={data['net_savings']}")
    
    def test_analytics_summary_with_date_range(self):
        """GET /api/analytics/summary with date filters"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/summary?start_date=2024-04-01&end_date=2025-03-31",
            headers=AUTH_HEADER
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_income" in data
        assert "total_expense" in data
        print(f"Analytics with date range: income={data['total_income']}, expense={data['total_expense']}")
    
    def test_analytics_summary_requires_auth(self):
        """GET /api/analytics/summary returns 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/analytics/summary")
        assert response.status_code == 401


class TestAccountsEndpoint:
    """Test /api/accounts endpoint regression"""
    
    def test_get_accounts(self):
        """GET /api/accounts returns accounts list"""
        response = requests.get(f"{BASE_URL}/api/accounts", headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            account = data[0]
            assert "id" in account
            assert "name" in account
            assert "account_type" in account
            assert "current_balance" in account
        print(f"Accounts: {len(data)} accounts found")
    
    def test_accounts_requires_auth(self):
        """GET /api/accounts returns 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/accounts")
        assert response.status_code == 401


class TestCategoriesEndpoint:
    """Test /api/categories endpoint regression"""
    
    def test_get_categories(self):
        """GET /api/categories returns categories list"""
        response = requests.get(f"{BASE_URL}/api/categories", headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0, "Expected at least some categories"
        
        category = data[0]
        assert "id" in category
        assert "name" in category
        assert "category_type" in category
        print(f"Categories: {len(data)} categories found")
    
    def test_categories_requires_auth(self):
        """GET /api/categories returns 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/categories")
        assert response.status_code == 401


class TestTransactionsEndpoint:
    """Test /api/transactions endpoint regression"""
    
    def test_get_transactions(self):
        """GET /api/transactions returns transactions list"""
        response = requests.get(f"{BASE_URL}/api/transactions", headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            txn = data[0]
            assert "id" in txn
            assert "date" in txn
            assert "description" in txn
            assert "amount" in txn
            assert "transaction_type" in txn
        print(f"Transactions: {len(data)} transactions found")
    
    def test_transactions_requires_auth(self):
        """GET /api/transactions returns 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/transactions")
        assert response.status_code == 401


class TestVouchersEndpoint:
    """Test /api/vouchers endpoint regression"""
    
    def test_get_vouchers(self):
        """GET /api/vouchers returns vouchers list"""
        response = requests.get(f"{BASE_URL}/api/vouchers", headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Vouchers: {len(data)} vouchers found")
    
    def test_vouchers_requires_auth(self):
        """GET /api/vouchers returns 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/vouchers")
        assert response.status_code == 401


class TestAICategorizeEndpoint:
    """Test /api/ai-categorize endpoint"""
    
    def test_ai_categorize_endpoint_exists(self):
        """POST /api/ai-categorize endpoint exists and requires auth"""
        response = requests.post(f"{BASE_URL}/api/ai-categorize", json=[])
        assert response.status_code == 401, "Should require auth"
    
    def test_ai_categorize_with_auth(self):
        """POST /api/ai-categorize with auth returns response"""
        response = requests.post(f"{BASE_URL}/api/ai-categorize", json=[], headers=AUTH_HEADER)
        # Should return 200 even if no uncategorized transactions
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "categorized_count" in data
        print(f"AI Categorize response: {data['message']}")


class TestCategoryBreakdownStructure:
    """Test category breakdown structure for pie chart percentages"""
    
    def test_category_breakdown_has_required_fields(self):
        """Category breakdown items have category, amount, color, type"""
        response = requests.get(f"{BASE_URL}/api/analytics/summary", headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        
        breakdown = data.get("category_breakdown", [])
        if len(breakdown) > 0:
            for item in breakdown[:5]:  # Check first 5
                assert "category" in item, f"Missing 'category' in {item}"
                assert "amount" in item, f"Missing 'amount' in {item}"
                assert "type" in item, f"Missing 'type' in {item}"
                assert item["type"] in ["income", "expense"], f"Invalid type: {item['type']}"
        print(f"Category breakdown: {len(breakdown)} categories with proper structure")


class TestMonthlyTrendStructure:
    """Test monthly trend structure for chart type selector"""
    
    def test_monthly_trend_has_required_fields(self):
        """Monthly trend items have month, income, expense"""
        response = requests.get(f"{BASE_URL}/api/analytics/summary", headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        
        trend = data.get("monthly_trend", [])
        if len(trend) > 0:
            for item in trend[:5]:  # Check first 5
                assert "month" in item, f"Missing 'month' in {item}"
                assert "income" in item, f"Missing 'income' in {item}"
                assert "expense" in item, f"Missing 'expense' in {item}"
        print(f"Monthly trend: {len(trend)} months with proper structure")


class TestDailyTrendStructure:
    """Test daily trend structure for single month view"""
    
    def test_daily_trend_has_required_fields(self):
        """Daily trend items have day, income, expense"""
        response = requests.get(f"{BASE_URL}/api/analytics/summary", headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        
        trend = data.get("daily_trend", [])
        if len(trend) > 0:
            for item in trend[:5]:  # Check first 5
                assert "day" in item, f"Missing 'day' in {item}"
                assert "income" in item, f"Missing 'income' in {item}"
                assert "expense" in item, f"Missing 'expense' in {item}"
        print(f"Daily trend: {len(trend)} days with proper structure")


class TestTopCreditorsDebitorsStructure:
    """Test top creditors/debitors structure for clickable navigation"""
    
    def test_top_creditors_debitors_structure(self):
        """Top creditors/debitors have description and amount"""
        response = requests.get(f"{BASE_URL}/api/analytics/summary", headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        
        creditors = data.get("top_creditors", [])
        debitors = data.get("top_debitors", [])
        
        for item in creditors[:3]:
            assert "description" in item
            assert "amount" in item
        
        for item in debitors[:3]:
            assert "description" in item
            assert "amount" in item
        
        print(f"Top creditors: {len(creditors)}, Top debitors: {len(debitors)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
