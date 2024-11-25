import pytest
from app import app, db
from models import Good, Inventory

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
            db.create_all()  # Create tables
            yield client
            db.session.remove()
            db.drop_all()  # Drop tables after tests


def test_add_good(client):
    """Test adding a new good and its inventory."""
    response = client.post('/goods', json={
        "name": "Laptop",
        "category": "Electronics",
        "price_per_item": 1500.00,
        "description": "High-end gaming laptop",
        "stock_count": 10
    })
    assert response.status_code == 201
    data = response.get_json()
    assert "message" in data
    assert "good_id" in data
    assert data["message"] == "Good and inventory added successfully!"
    assert data["stock_count"] == 10


def test_get_all_goods(client):
    """Test retrieving all goods with inventory details."""
    client.post('/goods', json={
        "name": "Laptop",
        "category": "Electronics",
        "price_per_item": 1500.00,
        "description": "High-end gaming laptop",
        "stock_count": 10
    })
    client.post('/goods', json={
        "name": "Phone",
        "category": "Electronics",
        "price_per_item": 800.00,
        "description": "Latest smartphone",
        "stock_count": 20
    })
    response = client.get('/goods')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 2
    assert data[0]["name"] == "Laptop"
    assert data[1]["name"] == "Phone"


def test_get_good(client):
    """Test retrieving a specific good with inventory details."""
    response = client.post('/goods', json={
        "name": "Laptop",
        "category": "Electronics",
        "price_per_item": 1500.00,
        "description": "High-end gaming laptop",
        "stock_count": 10
    })
    good_id = response.get_json()["good_id"]
    response = client.get(f'/goods/{good_id}')
    assert response.status_code == 200
    data = response.get_json()
    assert data["name"] == "Laptop"
    assert data["stock_count"] == 10


def test_update_good(client):
    """Test updating an existing good and its inventory."""
    response = client.post('/goods', json={
        "name": "Laptop",
        "category": "Electronics",
        "price_per_item": 1500.00,
        "description": "High-end gaming laptop",
        "stock_count": 10
    })
    good_id = response.get_json()["good_id"]
    response = client.put(f'/goods/{good_id}', json={
        "price_per_item": 1400.00,
        "description": "Updated description",
        "stock_count": 5
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data["updated_good"]["price_per_item"] == 1400.00
    assert data["updated_good"]["description"] == "Updated description"
    assert data["updated_good"]["stock_count"] == 5


def test_deduct_stock(client):
    """Test deducting stock from a good's inventory."""
    response = client.post('/goods', json={
        "name": "Laptop",
        "category": "Electronics",
        "price_per_item": 1500.00,
        "description": "High-end gaming laptop",
        "stock_count": 10
    })
    good_id = response.get_json()["good_id"]
    response = client.post(f'/goods/{good_id}/inventory/deduct', json={"quantity": 5})
    assert response.status_code == 200
    data = response.get_json()
    assert data["remaining_stock"] == 5


def test_deduct_stock_insufficient(client):
    """Test attempting to deduct more stock than available."""
    response = client.post('/goods', json={
        "name": "Laptop",
        "category": "Electronics",
        "price_per_item": 1500.00,
        "description": "High-end gaming laptop",
        "stock_count": 10
    })
    good_id = response.get_json()["good_id"]
    response = client.post(f'/goods/{good_id}/inventory/deduct', json={"quantity": 15})
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "Insufficient stock"


def test_get_good_not_found(client):
    """Test retrieving a non-existent good."""
    response = client.get('/goods/999')
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "Good not found"
