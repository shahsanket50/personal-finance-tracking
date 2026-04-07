"""
Iteration 13: Testing Reports Enhancement
- Cash Flow endpoint (new)
- P&L with group-wise subtotals
- Balance Sheet with grouped items
- FY-aware date defaults
- Regression tests for existing endpoints
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
AUTH_HEADER = {"Authorization": "Bearer test_session_7e4ac6df60e1455f93f1cc93d93a2e84"}

class TestCashFlowEndpoint:
    """New Cash Flow Statement endpoint tests"""
    
    def test_cash_flow_without_dates(self):
        """GET /api/cash-flow returns operating/investing/financing sections"""
        response = requests.get(f"{BASE_URL}/api/cash-flow", headers=AUTH_HEADER)
        assert response.status_code == 200
        
        data = response.json()
        # Verify structure
        assert "operating" in data
        assert "investing" in data
        assert "financing" in data
        assert "net_cash_change" in data
        assert "opening_cash" in data
        assert "closing_cash" in data
        
        # Verify operating section structure
        assert "items" in data["operating"]
        assert "total" in data["operating"]
        assert isinstance(data["operating"]["items"], list)
        
        # Verify investing section structure
        assert "items" in data["investing"]
        assert "total" in data["investing"]
        
        # Verify financing section structure
        assert "items" in data["financing"]
        assert "total" in data["financing"]
        
        print(f"Cash Flow: Operating={data['operating']['total']}, Investing={data['investing']['total']}, Financing={data['financing']['total']}")
        print(f"Net Change={data['net_cash_change']}, Opening={data['opening_cash']}, Closing={data['closing_cash']}")
    
    def test_cash_flow_with_date_filters(self):
        """GET /api/cash-flow with FY 2024-25 date range"""
        response = requests.get(
            f"{BASE_URL}/api/cash-flow?start_date=2024-04-01&end_date=2025-03-31",
            headers=AUTH_HEADER
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "operating" in data
        assert "net_cash_change" in data
        
        # Verify items have required fields
        if data["operating"]["items"]:
            item = data["operating"]["items"][0]
            assert "ledger_name" in item
            assert "group_name" in item
            assert "nature" in item
            assert "amount" in item
        
        print(f"FY 2024-25 Cash Flow: Net Change={data['net_cash_change']}")
    
    def test_cash_flow_requires_auth(self):
        """GET /api/cash-flow returns 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/cash-flow")
        assert response.status_code == 401


class TestProfitLossEndpoint:
    """P&L endpoint with group-wise subtotals"""
    
    def test_profit_loss_returns_grouped_data(self):
        """GET /api/profit-loss returns income/expenses with group_name"""
        response = requests.get(
            f"{BASE_URL}/api/profit-loss?start_date=2024-04-01&end_date=2025-03-31",
            headers=AUTH_HEADER
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "income" in data
        assert "expenses" in data
        assert "total_income" in data
        assert "total_expenses" in data
        assert "net_profit" in data
        
        # Verify items have group_name for grouping
        if data["income"]:
            assert "group_name" in data["income"][0]
            assert "ledger_name" in data["income"][0]
            assert "amount" in data["income"][0]
        
        if data["expenses"]:
            assert "group_name" in data["expenses"][0]
            # Check for Indirect Expenses group
            expense_groups = set(e["group_name"] for e in data["expenses"])
            print(f"Expense groups found: {expense_groups}")
        
        print(f"P&L: Income={data['total_income']}, Expenses={data['total_expenses']}, Net={data['net_profit']}")


class TestBalanceSheetEndpoint:
    """Balance Sheet endpoint with grouped items"""
    
    def test_balance_sheet_returns_grouped_data(self):
        """GET /api/balance-sheet returns assets/liabilities with group_name"""
        response = requests.get(
            f"{BASE_URL}/api/balance-sheet?as_of_date=2025-03-31",
            headers=AUTH_HEADER
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "assets" in data
        assert "liabilities" in data
        assert "total_assets" in data
        assert "total_liabilities" in data
        assert "is_balanced" in data
        
        # Verify items have group_name for grouping
        if data["assets"]:
            assert "group_name" in data["assets"][0]
            asset_groups = set(a["group_name"] for a in data["assets"])
            print(f"Asset groups found: {asset_groups}")
        
        if data["liabilities"]:
            assert "group_name" in data["liabilities"][0]
        
        print(f"Balance Sheet: Assets={data['total_assets']}, Liabilities={data['total_liabilities']}, Balanced={data['is_balanced']}")


class TestFinancialYearsEndpoint:
    """FY endpoint for date defaults"""
    
    def test_financial_years_returns_fy_list(self):
        """GET /api/financial-years returns years with start/end dates"""
        response = requests.get(f"{BASE_URL}/api/financial-years", headers=AUTH_HEADER)
        assert response.status_code == 200
        
        data = response.json()
        assert "years" in data
        assert "current_fy" in data
        assert isinstance(data["years"], list)
        
        if data["years"]:
            fy = data["years"][0]
            assert "label" in fy
            assert "start" in fy
            assert "end" in fy
            # Verify date format
            assert len(fy["start"]) == 10  # YYYY-MM-DD
            assert len(fy["end"]) == 10
        
        print(f"Financial Years: {[y['label'] for y in data['years']]}")
        print(f"Current FY: {data['current_fy']}")


class TestRegressionEndpoints:
    """Regression tests for existing endpoints"""
    
    def test_auth_me(self):
        """GET /api/auth/me returns user data"""
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "email" in data
    
    def test_accounts(self):
        """GET /api/accounts returns accounts list"""
        response = requests.get(f"{BASE_URL}/api/accounts", headers=AUTH_HEADER)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_categories(self):
        """GET /api/categories returns categories list"""
        response = requests.get(f"{BASE_URL}/api/categories", headers=AUTH_HEADER)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_transactions(self):
        """GET /api/transactions returns transactions list"""
        response = requests.get(f"{BASE_URL}/api/transactions", headers=AUTH_HEADER)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_vouchers(self):
        """GET /api/vouchers returns vouchers list"""
        response = requests.get(f"{BASE_URL}/api/vouchers", headers=AUTH_HEADER)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_trial_balance(self):
        """GET /api/trial-balance returns balanced trial balance"""
        response = requests.get(
            f"{BASE_URL}/api/trial-balance?start_date=2024-04-01&end_date=2025-03-31",
            headers=AUTH_HEADER
        )
        assert response.status_code == 200
        data = response.json()
        assert "rows" in data
        assert "total_debit" in data
        assert "total_credit" in data
        assert "is_balanced" in data
    
    def test_daybook(self):
        """GET /api/daybook returns daybook entries"""
        response = requests.get(f"{BASE_URL}/api/daybook", headers=AUTH_HEADER)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_company(self):
        """GET /api/company returns company info"""
        response = requests.get(f"{BASE_URL}/api/company", headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data or "name" in data
    
    def test_account_groups(self):
        """GET /api/account-groups returns account groups"""
        response = requests.get(f"{BASE_URL}/api/account-groups", headers=AUTH_HEADER)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_ledgers(self):
        """GET /api/ledgers returns ledgers list"""
        response = requests.get(f"{BASE_URL}/api/ledgers", headers=AUTH_HEADER)
        assert response.status_code == 200
        assert isinstance(response.json(), list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
