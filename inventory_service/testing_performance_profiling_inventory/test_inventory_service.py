import unittest
import requests  # To call the customer_service
from app import app, db
from flask import json


class TestInventoryService(unittest.TestCase):

    def setUp(self):
        """Set up the test client and database."""
        self.app = app.test_client()
        self.app.testing = True
        with app.app_context():
            db.create_all()

    def tearDown(self):
        """Tear down the database."""
        with app.app_context():
            db.drop_all()

    def register_admin(self):
        """Helper method to register or log in an admin user."""
        username = 'adminuser'
        response = requests.post('http://localhost:5001/admin/register', json={
            'full_name': 'Admin User',
            'username': username,
            'password': 'AdminPass123!',
            'age': 35,
            'address': '123 Admin St',
            'gender': 'Male',
            'marital_status': 'Single'
        })
        if response.status_code == 400 and "Username already taken" in response.text:
            # Login instead
            response = requests.post('http://localhost:5001/customers/login', json={
                'username': username,
                'password': 'AdminPass123!'
            })
        self.assertEqual(response.status_code, 200, "Failed to register or log in admin in customer_service.")
        token = response.json().get('access_token')
        self.assertIsNotNone(token, "Admin registration/login failed to return a token.")
        return token



    def test_add_good(self):
        """Test adding a new good with inventory details."""
        admin_token = self.register_admin()

        # Add a new good
        response = self.app.post('/goods', json={
            'name': 'Laptop',
            'category': 'Electronics',
            'price_per_item': 1000.00,
            'description': 'A high-end gaming laptop',
            'stock_count': 50
        }, headers={'Authorization': f'Bearer {admin_token}'})
        self.assertEqual(response.status_code, 201)

    def test_get_all_goods(self):
        """Test retrieving all goods."""
        admin_token = self.register_admin()

        # Add a good
        self.app.post('/goods', json={
            'name': 'Laptop',
            'category': 'Electronics',
            'price_per_item': 1000.00,
            'description': 'A high-end gaming laptop',
            'stock_count': 50
        }, headers={'Authorization': f'Bearer {admin_token}'})

        # Fetch goods
        response = self.app.get('/goods')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(len(data) > 0)

    def test_get_good(self):
        """Test retrieving a specific good by ID."""
        admin_token = self.register_admin()

        # Add a good
        self.app.post('/goods', json={
            'name': 'Laptop',
            'category': 'Electronics',
            'price_per_item': 1000.00,
            'description': 'A high-end gaming laptop',
            'stock_count': 50
        }, headers={'Authorization': f'Bearer {admin_token}'})

        # Fetch the good by ID
        response = self.app.get('/goods/1')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['name'], 'Laptop')

    def test_update_good(self):
        """Test updating a good's details."""
        admin_token = self.register_admin()

        # Add a good
        self.app.post('/goods', json={
            'name': 'Laptop',
            'category': 'Electronics',
            'price_per_item': 1000.00,
            'description': 'A high-end gaming laptop',
            'stock_count': 50
        }, headers={'Authorization': f'Bearer {admin_token}'})

        # Update the good
        response = self.app.put('/goods/1', json={
            'name': 'Gaming Laptop',
            'price_per_item': 1200.00
        }, headers={'Authorization': f'Bearer {admin_token}'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['updated_good']['name'], 'Gaming Laptop')

    def test_deduct_stock(self):
        """Test deducting stock from inventory."""
        admin_token = self.register_admin()

        # Add a good
        self.app.post('/goods', json={
            'name': 'Laptop',
            'category': 'Electronics',
            'price_per_item': 1000.00,
            'description': 'A high-end gaming laptop',
            'stock_count': 50
        }, headers={'Authorization': f'Bearer {admin_token}'})

        # Deduct stock
        response = self.app.post('/goods/1/inventory/deduct', json={
            'quantity': 10
        }, headers={'Authorization': f'Bearer {admin_token}'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['remaining_stock'], 40)

    def test_delete_good(self):
        """Test deleting a good."""
        admin_token = self.register_admin()

        # Add a good
        self.app.post('/goods', json={
            'name': 'Laptop',
            'category': 'Electronics',
            'price_per_item': 1000.00,
            'description': 'A high-end gaming laptop',
            'stock_count': 50
        }, headers={'Authorization': f'Bearer {admin_token}'})

        # Delete the good
        response = self.app.delete('/goods/1', headers={
            'Authorization': f'Bearer {admin_token}'})
        self.assertEqual(response.status_code, 200)

    def test_unauthorized_access(self):
        """Test unauthorized access to an admin-only endpoint."""
        # Attempt to add a good without a token
        response = self.app.post('/goods', json={
            'name': 'Laptop',
            'category': 'Electronics',
            'price_per_item': 1000.00,
            'description': 'A high-end gaming laptop',
            'stock_count': 50
        })
        self.assertIn(response.status_code, [401, 403])


    def test_invalid_deduction(self):
        """Test attempting to deduct more stock than available."""
        admin_token = self.register_admin()

        # Add a good
        self.app.post('/goods', json={
            'name': 'Laptop',
            'category': 'Electronics',
            'price_per_item': 1000.00,
            'description': 'A high-end gaming laptop',
            'stock_count': 50
        }, headers={'Authorization': f'Bearer {admin_token}'})

        # Attempt to deduct more stock than available
        response = self.app.post('/goods/1/inventory/deduct', json={
            'quantity': 100
        }, headers={'Authorization': f'Bearer {admin_token}'})
        self.assertEqual(response.status_code, 400)


if __name__ == '__main__':
    unittest.main()
