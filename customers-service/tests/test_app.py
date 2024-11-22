import pytest
from app import app, db
from models import Customer
import os
import sys

# Append the parent directory to PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@pytest.fixture
def client():
    """Fixture for setting up the test client and in-memory database."""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'  # In-memory SQLite for testing
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    with app.test_client() as client:
        with app.app_context():
            db.create_all()  # Create tables before tests
            yield client
            db.session.remove()  # Clear the session after tests
            db.drop_all()  # Drop all tables after tests


def test_register_customer(client):
    """Test registering a new customer."""
    response = client.post('/customers', json={
        "full_name": "John Doe",
        "username": "johndoe",
        "password": "password123",
        "age": 30,
        "address": "123 Elm Street",
        "gender": "Male",
        "marital_status": "Single"
    })
    assert response.status_code == 201, f"Failed: {response.data}"
    assert b"Customer registered successfully!" in response.data


def test_register_existing_username(client):
    """Test registering a customer with an existing username."""
    client.post('/customers', json={
        "full_name": "John Doe",
        "username": "johndoe",
        "password": "password123",
        "age": 30,
        "address": "123 Elm Street",
        "gender": "Male",
        "marital_status": "Single"
    })
    response = client.post('/customers', json={
        "full_name": "Jane Doe",
        "username": "johndoe",
        "password": "password456",
        "age": 25,
        "address": "456 Oak Avenue",
        "gender": "Female",
        "marital_status": "Married"
    })
    assert response.status_code == 400, f"Failed: {response.data}"
    assert b"Username already taken" in response.data


def test_get_all_customers(client):
    """Test retrieving all customers."""
    client.post('/customers', json={
        "full_name": "John Doe",
        "username": "johndoe",
        "password": "password123",
        "age": 30,
        "address": "123 Elm Street",
        "gender": "Male",
        "marital_status": "Single"
    })
    response = client.get('/customers')
    assert response.status_code == 200, f"Failed: {response.data}"
    data = response.get_json()
    assert len(data) == 1
    assert data[0]['username'] == 'johndoe'


def test_update_customer(client):
    """Test updating an existing customer."""
    response = client.post('/customers', json={
        "full_name": "John Doe",
        "username": "johndoe",
        "password": "password123",
        "age": 30,
        "address": "123 Elm Street",
        "gender": "Male",
        "marital_status": "Single"
    })
    customer_id = response.get_json()['id']
    update_response = client.put(f'/update-customer/{customer_id}', json={
        "address": "789 Maple Lane",
        "age": 35
    })
    assert update_response.status_code == 200, f"Failed: {update_response.data}"
    assert b"Customer updated successfully" in update_response.data


def test_delete_customer(client):
    """Test deleting a customer."""
    response = client.post('/customers', json={
        "full_name": "John Doe",
        "username": "johndoe",
        "password": "password123",
        "age": 30,
        "address": "123 Elm Street",
        "gender": "Male",
        "marital_status": "Single"
    })
    customer_id = response.get_json()['id']
    delete_response = client.delete(f'/customers/{customer_id}')
    assert delete_response.status_code == 200, f"Failed: {delete_response.data}"
    assert b"Customer deleted successfully" in delete_response.data


def test_charge_wallet(client):
    """Test charging a customer's wallet."""
    response = client.post('/customers', json={
        "full_name": "John Doe",
        "username": "johndoe",
        "password": "password123",
        "age": 30,
        "address": "123 Elm Street",
        "gender": "Male",
        "marital_status": "Single"
    })
    customer_id = response.get_json()['id']
    charge_response = client.post(f'/customers/{customer_id}/wallet/charge', json={"amount": 50})
    assert charge_response.status_code == 200, f"Failed: {charge_response.data}"
    assert b"$50 added to wallet" in charge_response.data


def test_deduct_wallet(client):
    """Test deducting from a customer's wallet."""
    response = client.post('/customers', json={
        "full_name": "John Doe",
        "username": "johndoe",
        "password": "password123",
        "age": 30,
        "address": "123 Elm Street",
        "gender": "Male",
        "marital_status": "Single"
    })
    customer_id = response.get_json()['id']
    client.post(f'/customers/{customer_id}/wallet/charge', json={"amount": 100})
    deduct_response = client.post(f'/customers/{customer_id}/wallet/deduct', json={"amount": 50})
    assert deduct_response.status_code == 200, f"Failed: {deduct_response.data}"
    assert b"$50 deducted from wallet" in deduct_response.data


def test_deduct_wallet_insufficient_funds(client):
    """Test attempting to deduct more than the wallet balance."""
    response = client.post('/customers', json={
        "full_name": "John Doe",
        "username": "johndoe",
        "password": "password123",
        "age": 30,
        "address": "123 Elm Street",
        "gender": "Male",
        "marital_status": "Single"
    })
    customer_id = response.get_json()['id']
    deduct_response = client.post(f'/customers/{customer_id}/wallet/deduct', json={"amount": 50})
    assert deduct_response.status_code == 400, f"Failed: {deduct_response.data}"
    assert b"Insufficient funds" in deduct_response.data
