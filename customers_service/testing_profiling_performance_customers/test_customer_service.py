import unittest
from app import app, db
from flask import json



class TestCustomerService(unittest.TestCase):

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

    def test_register_customer(self):
        """Test customer registration."""
        response = self.app.post('/customers/register', json={
            'full_name': 'John Doe',
            'username': 'johndoe',
            'password': 'Password123!',
            'age': 30,
            'address': '123 Main St',
            'gender': 'Male',
            'marital_status': 'Single'
        })
        self.assertEqual(response.status_code, 201)

    def test_login_customer(self):
        """Test customer login."""
        self.app.post('/customers/register', json={
            'full_name': 'John Doe',
            'username': 'johndoe',
            'password': 'Password123!',
            'age': 30,
            'address': '123 Main St',
            'gender': 'Male',
            'marital_status': 'Single'
        })
        response = self.app.post('/customers/login', json={
            'username': 'johndoe',
            'password': 'Password123!'
        })
        self.assertEqual(response.status_code, 200)

    def test_get_current_user(self):
        """Test fetching the current user's profile."""
        register = self.app.post('/customers/register', json={
            'full_name': 'Jane Doe',
            'username': 'janedoe',
            'password': 'Password123!',
            'age': 28,
            'address': '456 Elm St',
            'gender': 'Female',
            'marital_status': 'Married'
        })
        token = json.loads(register.data)['access_token']
        response = self.app.get('/customers/me', headers={
            'Authorization': f'Bearer {token}'
        })
        self.assertEqual(response.status_code, 200)

    def test_get_all_customers(self):
        """Test fetching all customers (admin-only)."""
        # Register admin
        admin_register = self.app.post('/admin/register', json={
            'full_name': 'Admin User',
            'username': 'adminuser',
            'password': 'AdminPass123!',
            'age': 35,
            'address': '789 Maple Ave',
            'gender': 'Male',
            'marital_status': 'Single'
        })
        self.assertEqual(admin_register.status_code, 201)

        # Login admin
        admin_login = self.app.post('/customers/login', json={
            'username': 'adminuser',
            'password': 'AdminPass123!'
        })
        self.assertEqual(admin_login.status_code, 200)

        # Extract token and check its validity
        admin_token = json.loads(admin_login.data)['access_token']
        self.assertIsNotNone(admin_token)

        # Fetch all customers
        response = self.app.get('/customers', headers={
            'Authorization': f'Bearer {admin_token}'
        })
        self.assertEqual(response.status_code, 200)


    def test_get_customer_by_username(self):
        """Test fetching a customer by username (admin-only)."""
        self.app.post('/admin/register', json={
            'full_name': 'Admin User',
            'username': 'adminuser',
            'password': 'AdminPass123!',
            'age': 35,
            'address': '789 Maple Ave',
            'gender': 'Male',
            'marital_status': 'Single'
        })
        self.app.post('/customers/register', json={
            'full_name': 'John Doe',
            'username': 'johndoe',
            'password': 'Password123!',
            'age': 30,
            'address': '123 Main St',
            'gender': 'Male',
            'marital_status': 'Single'
        })
        token = json.loads(self.app.post('/customers/login', json={
            'username': 'adminuser',
            'password': 'AdminPass123!'
        }).data)['access_token']
        response = self.app.get('/customers/username/johndoe', headers={
            'Authorization': f'Bearer {token}'
        })
        self.assertEqual(response.status_code, 200)

    def test_update_customer(self):
        """Test updating a customer's profile."""
        register = self.app.post('/customers/register', json={
            'full_name': 'Jane Doe',
            'username': 'janedoe',
            'password': 'Password123!',
            'age': 28,
            'address': '456 Elm St',
            'gender': 'Female',
            'marital_status': 'Married'
        })
        token = json.loads(register.data)['access_token']
        response = self.app.put('/customers/1', json={
            'full_name': 'Jane Smith',
            'address': '123 New Address'
        }, headers={
            'Authorization': f'Bearer {token}'
        })
        self.assertEqual(response.status_code, 200)

    def test_delete_customer(self):
        """Test deleting a customer's profile."""
        register = self.app.post('/customers/register', json={
            'full_name': 'Jane Doe',
            'username': 'janedoe',
            'password': 'Password123!',
            'age': 28,
            'address': '456 Elm St',
            'gender': 'Female',
            'marital_status': 'Married'
        })
        token = json.loads(register.data)['access_token']
        response = self.app.delete('/customers/1', headers={
            'Authorization': f'Bearer {token}'
        })
        self.assertEqual(response.status_code, 200)

    def test_charge_wallet(self):
        """Test charging a customer's wallet."""
        # Register and login customer
        register = self.app.post('/customers/register', json={
            'full_name': 'Jane Doe',
            'username': 'janedoe',
            'password': 'Password123!',
            'age': 28,
            'address': '456 Elm St',
            'gender': 'Female',
            'marital_status': 'Married'
        })
        token = json.loads(register.data)['access_token']
        
        response = self.app.post('/customers/1/wallet/charge', json={
            'amount': 50.00
        }, headers={
            'Authorization': f'Bearer {token}'
        })
        self.assertEqual(response.status_code, 200)


    def test_deduct_wallet(self):
        """Test deducting money from a customer's wallet."""
        register = self.app.post('/customers/register', json={
            'full_name': 'Jane Doe',
            'username': 'janedoe',
            'password': 'Password123!',
            'age': 28,
            'address': '456 Elm St',
            'gender': 'Female',
            'marital_status': 'Married'
        })
        token = json.loads(register.data)['access_token']
        self.app.post('/customers/1/wallet/charge', json={
            'amount': 50.00
        }, headers={
            'Authorization': f'Bearer {token}'
        })
        response = self.app.post('/customers/1/wallet/deduct', json={
            'amount': 20.00
        }, headers={
            'Authorization': f'Bearer {token}'
        })
        self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main()
