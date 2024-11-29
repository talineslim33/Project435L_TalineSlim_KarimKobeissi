import pytest
from app import app, db
from models import Review
import sys
import os

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
            db.create_all()
            yield client
            db.session.remove()
            db.drop_all()

def test_submit_review(client):
    """Test submitting a new review."""
    response = client.post('/reviews', json={
        "customer_id": 1,
        "product_id": 101,
        "rating": 4,
        "comment": "Great product!"
    })
    assert response.status_code == 201
    data = response.get_json()
    assert "review_id" in data

def test_update_review(client):
    """Test updating an existing review."""
    client.post('/reviews', json={
        "customer_id": 1,
        "product_id": 101,
        "rating": 4,
        "comment": "Great product!"
    })
    response = client.put('/reviews/1', json={
        "rating": 5,
        "comment": "Excellent product!"
    })
    assert response.status_code == 200
    assert b"Review updated successfully" in response.data

def test_delete_review(client):
    """Test deleting a review."""
    client.post('/reviews', json={
        "customer_id": 1,
        "product_id": 101,
        "rating": 4,
        "comment": "Great product!"
    })
    response = client.delete('/reviews/1')
    assert response.status_code == 200
    assert b"Review deleted successfully" in response.data

def test_get_product_reviews(client):
    """Test retrieving all reviews for a product."""
    client.post('/reviews', json={
        "customer_id": 1,
        "product_id": 101,
        "rating": 4,
        "comment": "Great product!"
    })
    client.post('/reviews', json={
        "customer_id": 2,
        "product_id": 101,
        "rating": 5,
        "comment": "Loved it!"
    })
    response = client.get('/reviews/product/101')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 2

def test_get_customer_reviews(client):
    """Test retrieving all reviews for a customer."""
    client.post('/reviews', json={
        "customer_id": 1,
        "product_id": 101,
        "rating": 4,
        "comment": "Great product!"
    })
    client.post('/reviews', json={
        "customer_id": 1,
        "product_id": 102,
        "rating": 3,
        "comment": "Average product."
    })
    response = client.get('/reviews/customer/1')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 2

def test_moderate_review(client):
    """Test moderating a review."""
    client.post('/reviews', json={
        "customer_id": 1,
        "product_id": 101,
        "rating": 4,
        "comment": "Great product!"
    })
    response = client.post('/reviews/1/moderate', json={
        "flagged": True,
        "moderated": True
    })
    assert response.status_code == 200
    assert b"Review moderation updated successfully" in response.data

def test_get_review_details(client):
    """Test retrieving review details."""
    client.post('/reviews', json={
        "customer_id": 1,
        "product_id": 101,
        "rating": 4,
        "comment": "Great product!"
    })
    response = client.get('/reviews/1')
    assert response.status_code == 200
    data = response.get_json()
    assert data["rating"] == 4
    assert data["comment"] == "Great product!"

def test_get_review_not_found(client):
    """Test retrieving a non-existent review."""
    response = client.get('/reviews/999')
    assert response.status_code == 404
    assert b"Review not found" in response.data
