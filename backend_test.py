import requests
import sys
import json
from datetime import datetime, timedelta

class FinanceAppTester:
    def __init__(self, base_url="https://money-insights-82.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_data = {
            'account_ids': [],
            'category_ids': [],
            'transaction_ids': []
        }

    def run_test(self, name, method, endpoint, expected_status, data=None, params=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, params=params)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return True, response.json() if response.content else {}
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    print(f"Response: {response.json()}")
                except:
                    print(f"Response: {response.text}")

            return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_init_defaults(self):
        """Test initialization of default categories"""
        success, response = self.run_test(
            "Initialize Defaults",
            "POST",
            "init",
            200
        )
        return success

    def test_create_account(self, name, account_type, start_balance):
        """Test account creation"""
        success, response = self.run_test(
            f"Create Account - {name}",
            "POST",
            "accounts",
            200,
            data={
                "name": name,
                "account_type": account_type,
                "start_balance": start_balance
            }
        )
        if success and 'id' in response:
            self.test_data['account_ids'].append(response['id'])
            return response['id']
        return None

    def test_get_accounts(self):
        """Test getting all accounts"""
        success, response = self.run_test(
            "Get All Accounts",
            "GET",
            "accounts",
            200
        )
        return success, response

    def test_update_account(self, account_id, name, account_type, start_balance):
        """Test account update"""
        success, response = self.run_test(
            f"Update Account - {account_id}",
            "PUT",
            f"accounts/{account_id}",
            200,
            data={
                "name": name,
                "account_type": account_type,
                "start_balance": start_balance
            }
        )
        return success

    def test_get_categories(self):
        """Test getting all categories"""
        success, response = self.run_test(
            "Get All Categories",
            "GET",
            "categories",
            200
        )
        if success and isinstance(response, list):
            # Store category IDs for later use
            for cat in response:
                if 'id' in cat:
                    self.test_data['category_ids'].append(cat['id'])
        return success, response

    def test_create_category(self, name, category_type, color):
        """Test category creation"""
        success, response = self.run_test(
            f"Create Category - {name}",
            "POST",
            "categories",
            200,
            data={
                "name": name,
                "category_type": category_type,
                "color": color
            }
        )
        if success and 'id' in response:
            self.test_data['category_ids'].append(response['id'])
            return response['id']
        return None

    def test_update_category(self, category_id, name, category_type, color):
        """Test category update"""
        success, response = self.run_test(
            f"Update Category - {category_id}",
            "PUT",
            f"categories/{category_id}",
            200,
            data={
                "name": name,
                "category_type": category_type,
                "color": color
            }
        )
        return success

    def test_delete_default_category(self, category_id):
        """Test that default categories cannot be deleted"""
        success, response = self.run_test(
            "Delete Default Category (Should Fail)",
            "DELETE",
            f"categories/{category_id}",
            400  # Should fail with 400
        )
        return success

    def test_create_transaction(self, account_id, category_id, description, amount, txn_type, date):
        """Test transaction creation"""
        success, response = self.run_test(
            f"Create Transaction - {description}",
            "POST",
            "transactions",
            200,
            data={
                "account_id": account_id,
                "date": date,
                "description": description,
                "amount": amount,
                "transaction_type": txn_type,
                "category_id": category_id
            }
        )
        if success and 'id' in response:
            self.test_data['transaction_ids'].append(response['id'])
            return response['id']
        return None

    def test_get_transactions(self):
        """Test getting all transactions"""
        success, response = self.run_test(
            "Get All Transactions",
            "GET",
            "transactions",
            200
        )
        return success, response

    def test_update_transaction(self, transaction_id, account_id, category_id, description, amount, txn_type, date):
        """Test transaction update"""
        success, response = self.run_test(
            f"Update Transaction - {transaction_id}",
            "PUT",
            f"transactions/{transaction_id}",
            200,
            data={
                "account_id": account_id,
                "date": date,
                "description": description,
                "amount": amount,
                "transaction_type": txn_type,
                "category_id": category_id
            }
        )
        return success

    def test_create_transfer(self, from_account_id, to_account_id, amount, date):
        """Test transfer creation"""
        success, response = self.run_test(
            f"Create Transfer - {amount}",
            "POST",
            "transfers",
            200,
            data={
                "from_account_id": from_account_id,
                "to_account_id": to_account_id,
                "amount": amount,
                "date": date,
                "description": "Test Transfer"
            }
        )
        return success

    def test_detect_transfers(self):
        """Test transfer detection"""
        success, response = self.run_test(
            "Detect Transfers",
            "POST",
            "detect-transfers",
            200
        )
        return success, response

    def test_mark_as_transfer(self, txn_ids):
        """Test marking transactions as transfer"""
        success, response = self.run_test(
            "Mark as Transfer",
            "POST",
            "mark-as-transfer",
            200,
            data=txn_ids
        )
        return success

    def test_analytics_summary(self):
        """Test analytics summary"""
        success, response = self.run_test(
            "Analytics Summary",
            "GET",
            "analytics/summary",
            200
        )
        return success, response

    def test_analytics_with_date_filter(self, start_date, end_date):
        """Test analytics with date filter"""
        success, response = self.run_test(
            "Analytics with Date Filter",
            "GET",
            "analytics/summary",
            200,
            params={"start_date": start_date, "end_date": end_date}
        )
        return success, response

    def test_delete_transaction(self, transaction_id):
        """Test transaction deletion"""
        success, response = self.run_test(
            f"Delete Transaction - {transaction_id}",
            "DELETE",
            f"transactions/{transaction_id}",
            200
        )
        return success

    def test_delete_category(self, category_id):
        """Test category deletion"""
        success, response = self.run_test(
            f"Delete Category - {category_id}",
            "DELETE",
            f"categories/{category_id}",
            200
        )
        return success

    def test_delete_account(self, account_id):
        """Test account deletion"""
        success, response = self.run_test(
            f"Delete Account - {account_id}",
            "DELETE",
            f"accounts/{account_id}",
            200
        )
        return success

def main():
    print("🚀 Starting Finance App Backend API Tests")
    print("=" * 50)
    
    tester = FinanceAppTester()
    
    # Test 1: Initialize defaults
    if not tester.test_init_defaults():
        print("❌ Failed to initialize defaults")
        return 1

    # Test 2: Get categories (should have defaults now)
    success, categories = tester.test_get_categories()
    if not success:
        print("❌ Failed to get categories")
        return 1

    # Find a default category for testing
    default_category = None
    expense_category = None
    income_category = None
    for cat in categories:
        if cat.get('is_default') and cat.get('category_type') == 'expense':
            default_category = cat['id']
            expense_category = cat['id']
        elif cat.get('category_type') == 'income':
            income_category = cat['id']
        if default_category and income_category:
            break

    # Test 3: Create custom category
    custom_category_id = tester.test_create_category("Test Category", "expense", "#FF5733")
    if not custom_category_id:
        print("❌ Failed to create custom category")
        return 1

    # Test 4: Update custom category
    if not tester.test_update_category(custom_category_id, "Updated Test Category", "expense", "#33FF57"):
        print("❌ Failed to update category")
        return 1

    # Test 5: Try to delete default category (should fail)
    if default_category and not tester.test_delete_default_category(default_category):
        print("❌ Default category deletion test failed")
        return 1

    # Test 6: Create accounts
    bank_account_id = tester.test_create_account("Test Bank Account", "bank", 10000.0)
    credit_card_id = tester.test_create_account("Test Credit Card", "credit_card", 0.0)
    if not bank_account_id or not credit_card_id:
        print("❌ Failed to create accounts")
        return 1

    # Test 7: Get accounts
    success, accounts = tester.test_get_accounts()
    if not success:
        print("❌ Failed to get accounts")
        return 1

    # Test 8: Update account
    if not tester.test_update_account(bank_account_id, "Updated Bank Account", "bank", 15000.0):
        print("❌ Failed to update account")
        return 1

    # Test 9: Create transactions
    today = datetime.now().strftime('%Y-%m-%d')
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    txn1_id = tester.test_create_transaction(
        bank_account_id, expense_category, "Test Expense", 500.0, "debit", today
    )
    txn2_id = tester.test_create_transaction(
        bank_account_id, income_category, "Test Income", 2000.0, "credit", today
    )
    
    if not txn1_id or not txn2_id:
        print("❌ Failed to create transactions")
        return 1

    # Test 10: Get transactions
    success, transactions = tester.test_get_transactions()
    if not success:
        print("❌ Failed to get transactions")
        return 1

    # Test 11: Update transaction
    if not tester.test_update_transaction(
        txn1_id, bank_account_id, expense_category, "Updated Test Expense", 750.0, "debit", today
    ):
        print("❌ Failed to update transaction")
        return 1

    # Test 12: Create transfer
    if not tester.test_create_transfer(bank_account_id, credit_card_id, 1000.0, today):
        print("❌ Failed to create transfer")
        return 1

    # Test 13: Create matching transactions for transfer detection
    match_txn1_id = tester.test_create_transaction(
        bank_account_id, expense_category, "Transfer Out", 300.0, "debit", yesterday
    )
    match_txn2_id = tester.test_create_transaction(
        credit_card_id, income_category, "Transfer In", 300.0, "credit", yesterday
    )

    # Test 14: Detect transfers
    success, detected = tester.test_detect_transfers()
    if not success:
        print("❌ Failed to detect transfers")
        return 1

    # Test 15: Mark as transfer (if we have matching transactions)
    if match_txn1_id and match_txn2_id:
        if not tester.test_mark_as_transfer([match_txn1_id, match_txn2_id]):
            print("❌ Failed to mark as transfer")
            return 1

    # Test 16: Analytics summary
    success, analytics = tester.test_analytics_summary()
    if not success:
        print("❌ Failed to get analytics summary")
        return 1

    # Test 17: Analytics with date filter
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    end_date = datetime.now().strftime('%Y-%m-%d')
    success, filtered_analytics = tester.test_analytics_with_date_filter(start_date, end_date)
    if not success:
        print("❌ Failed to get filtered analytics")
        return 1

    # Cleanup tests
    print("\n🧹 Running cleanup tests...")
    
    # Test 18: Delete transactions
    for txn_id in tester.test_data['transaction_ids']:
        if not tester.test_delete_transaction(txn_id):
            print(f"❌ Failed to delete transaction {txn_id}")

    # Test 19: Delete custom category
    if not tester.test_delete_category(custom_category_id):
        print("❌ Failed to delete custom category")

    # Test 20: Delete accounts
    for acc_id in tester.test_data['account_ids']:
        if not tester.test_delete_account(acc_id):
            print(f"❌ Failed to delete account {acc_id}")

    # Print results
    print("\n" + "=" * 50)
    print(f"📊 Tests completed: {tester.tests_passed}/{tester.tests_run}")
    print(f"Success rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All backend API tests passed!")
        return 0
    else:
        print("❌ Some backend API tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())