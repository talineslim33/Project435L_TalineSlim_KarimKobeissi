import unittest
import json
import requests
from app import app, db  # Import the app and db directly
from models import Sale, Wishlist, Notification
from flask_jwt_extended import create_access_token
from flask import url_for

class SalesServiceIntegrationTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()

        # Base URLs for other services
        self.customer_service_url = 'http://localhost:5001'  # Adjust ports as needed
        self.inventory_service_url = 'http://localhost:5002'

        # Create test data in customer_service
        self.create_customer_service_test_data()

        # Obtain JWT tokens
        self.user_token = self.login_customer('testuser', 'TestPass123!')
        self.admin_token = self.login_customer('adminuser', 'AdminPass123!')

        # Now that we have the admin token, create test data in inventory_service
        self.create_inventory_service_test_data()

    def tearDown(self):
        # Clean up sales_service database
        with self.app.app_context():
            # Remove test data created during tests
            # Deleting test sales, wishlists, and notifications
            Sale.query.delete()
            Wishlist.query.delete()
            Notification.query.delete()
            db.session.commit()

        # Optionally, clean up customer_service and inventory_service data
        # This depends on whether your APIs support data deletion

    def create_customer_service_test_data(self):
        # Register a regular customer
        customer_data = {
            'full_name': 'Test User',
            'username': 'testuser',
            'password': 'TestPass123!',
            'age': 30,
            'address': '123 Test Street',
            'gender': 'Other',
            'marital_status': 'Single'
        }
        response = requests.post(
            f'{self.customer_service_url}/customers/register',
            json=customer_data
        )
        # If the user already exists, ignore the error
        if response.status_code not in [201, 400]:
            assert False, 'Failed to create test customer'

        # Register an admin user
        admin_data = {
            'full_name': 'Admin User',
            'username': 'adminuser',
            'password': 'AdminPass123!',
            'age': 35,
            'address': '456 Admin Road',
            'gender': 'Other',
            'marital_status': 'Single'
        }
        response = requests.post(
            f'{self.customer_service_url}/admin/register',
            json=admin_data
        )
        if response.status_code not in [201, 400]:
            assert False, 'Failed to create admin user'

    def create_inventory_service_test_data(self):
        # Use the admin token obtained earlier
        admin_token = self.admin_token

        headers = {'Authorization': f'Bearer {admin_token}'}
        good_data = {
            'name': 'Test Good 1',
            'category': 'Test Category',
            'price_per_item': 50.00,
            'description': 'A test good',
            'stock_count': 10
        }
        response = requests.post(
            f'{self.inventory_service_url}/goods',
            headers=headers,
            json=good_data
        )
        if response.status_code not in [201, 400]:
            print(f"Response status code: {response.status_code}")
            print(f"Response body: {response.text}")
            assert False, 'Failed to create test good'


    def login_customer(self, username, password):
        login_data = {
            'username': username,
            'password': password
        }
        response = requests.post(
            f'{self.customer_service_url}/customers/login',
            json=login_data
        )
        if response.status_code != 200:
            assert False, f'Failed to login user {username}'
        return response.json()['access_token']

    def test_make_sale_success(self):
        # Make a sale as a customer
        headers = {'Authorization': f'Bearer {self.user_token}'}
        sale_data = {
            'good_name': 'Test Good 1',
            'quantity': 2
        }
        response = self.client.post('/sales', headers=headers, json=sale_data)
        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['message'], 'Sale successful')
        # Remaining stock and customer balance might vary if tests are re-run
        # So we check for the existence of keys instead
        self.assertIn('remaining_stock', data)
        self.assertIn('customer_balance', data)

    def test_make_sale_insufficient_stock(self):
        # Attempt to purchase more goods than are in stock
        headers = {'Authorization': f'Bearer {self.user_token}'}
        sale_data = {
            'good_name': 'Test Good 1',
            'quantity': 1000  # Assuming stock is less than this
        }
        response = self.client.post('/sales', headers=headers, json=sale_data)
        data = response.get_json()
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Good not available or insufficient stock')

    def test_make_sale_insufficient_funds(self):
        # Reduce user's wallet balance to simulate insufficient funds
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        customer_id = self.get_customer_id('testuser')
        deduct_data = {'amount': 950.00}
        response = requests.post(
            f'{self.customer_service_url}/customers/{customer_id}/wallet/deduct',
            headers=headers,
            json=deduct_data
        )
        if response.status_code != 200:
            print(f"Response status code: {response.status_code}")
            print(f"Response body: {response.text}")
            assert False, 'Failed to deduct customer wallet balance'


    def test_get_purchase_history(self):
        # Make a sale first
        self.test_make_sale_success()

        # Get purchase history
        headers = {'Authorization': f'Bearer {self.user_token}'}
        response = self.client.get('/sales/history', headers=headers)
        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(data), 1)
        self.assertEqual(data[0]['good_name'], 'Test Good 1')

    def test_get_all_purchase_histories_admin(self):
        # Make a sale first
        self.test_make_sale_success()

        # Admin retrieves all purchase histories
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        response = self.client.get('/sales/history/all', headers=headers)
        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(data), 1)
        self.assertEqual(data[0]['good_name'], 'Test Good 1')

    def test_get_all_purchase_histories_non_admin(self):
        # Non-admin user attempts to retrieve all purchase histories
        headers = {'Authorization': f'Bearer {self.user_token}'}
        response = self.client.get('/sales/history/all', headers=headers)
        data = response.get_json()
        self.assertEqual(response.status_code, 403)
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Unauthorized action')

    def test_add_to_wishlist(self):
        # Add an item to the wishlist
        headers = {'Authorization': f'Bearer {self.user_token}'}
        good_id = self.get_good_id('Test Good 1')
        wishlist_data = {'good_id': good_id}
        response = self.client.post('/wishlist', headers=headers, json=wishlist_data)
        data = response.get_json()
        self.assertIn(response.status_code, [201, 400])
        self.assertIn('message', data)

    def test_remove_from_wishlist(self):
        # Add and then remove an item from the wishlist
        self.test_add_to_wishlist()

        # Get wishlist items
        headers = {'Authorization': f'Bearer {self.user_token}'}
        response = self.client.get('/wishlist', headers=headers)
        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(data), 1)
        wishlist_item_id = data[0]['good_id']

        # Remove item from wishlist
        response = self.client.delete(f'/wishlist/{wishlist_item_id}', headers=headers)
        data = response.get_json()
        self.assertIn(response.status_code, [200, 404])
        self.assertIn('message', data)

    def test_get_wishlist(self):
        # Add an item to the wishlist
        self.test_add_to_wishlist()

        # Get wishlist items
        headers = {'Authorization': f'Bearer {self.user_token}'}
        response = self.client.get('/wishlist', headers=headers)
        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'Test Good 1')

    def test_is_in_wishlist(self):
        # Add an item to the wishlist
        self.test_add_to_wishlist()

        # Check if item is in wishlist
        good_id = self.get_good_id('Test Good 1')
        headers = {'Authorization': f'Bearer {self.user_token}'}
        response = self.client.get(f'/wishlist/{good_id}', headers=headers)
        data = response.get_json()
        self.assertIn(response.status_code, [200, 404])
        if response.status_code == 200:
            self.assertTrue(data['in_wishlist'])
        else:
            self.assertFalse(data['in_wishlist'])

    def test_get_notifications(self):
        # For testing purposes, we can add a notification manually
        with self.app.app_context():
            notification = Notification(
                customer_id=self.get_customer_id('testuser'),
                message='Test notification',
                type='info',
                status='unread'
            )
            notification.good_id = self.get_good_id('Test Good 1')
            db.session.add(notification)
            db.session.commit()


        # Retrieve notifications
        headers = {'Authorization': f'Bearer {self.user_token}'}
        response = self.client.get('/notifications', headers=headers)
        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(data), 1)
        self.assertEqual(data[0]['message'], 'Test notification')

    def test_get_recommendations(self):
        # Assuming recommendations are based on purchase history
        # Make a sale first
        self.test_make_sale_success()

        # Get recommendations
        headers = {'Authorization': f'Bearer {self.user_token}'}
        response = self.client.get('/sales/recommendations', headers=headers)
        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        # Recommendations might be empty if there's not enough data
        self.assertIsInstance(data, list)

    # Helper methods
    def get_customer_id(self, username):
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        response = requests.get(
            f'{self.customer_service_url}/customers/username/{username}',
            headers=headers
        )
        if response.status_code == 200:
            return response.json()['id']
        else:
            return None

    def get_good_id(self, good_name):
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        response = requests.get(
            f'{self.inventory_service_url}/goods',
            headers=headers
        )
        if response.status_code == 200:
            goods = response.json()
            for good in goods:
                if good['name'] == good_name:
                    return good['id']
        return None

if __name__ == '__main__':
    unittest.main()
