import pytest
from models import db, Good, Inventory, Customer, Sale
from app import app


@pytest.fixture
def client():
    """Fixture for setting up the test client and in-memory database."""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'  # Use SQLite for testing
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            setup_database()
            yield client
        db.session.remove()
        db.drop_all()


def setup_database():
    # Add a test customer
    customer = Customer(
        username='testuser',
        full_name='Test User',
        password_hash='hashed_password',  # Add a valid hash
        age=30,
        address='123 Elm Street',
        gender='Male',
        marital_status='Single',
        wallet_balance=100.0
    )
    db.session.add(customer)

    # Add test goods
    good1 = Good(name='Item1', category='Category1', price_per_item=10.0, description='Test Item 1')
    db.session.add(good1)
    db.session.commit()

    # Add inventory for the goods
    inventory1 = Inventory(good_id=good1.id, stock_count=10)
    db.session.add(inventory1)
    db.session.commit()

    # Add a sale
    sale = Sale(
        customer_id=customer.id,
        good_id=good1.id,
        quantity=1,
        total_price=10.0
    )
    db.session.add(sale)
    db.session.commit()


def test_display_available_goods(client):
    response = client.get('/sales/goods')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1  # Only one item is in stock
    assert data[0]['name'] == 'Item1'
    assert data[0]['price'] == 10.0


def test_get_good_details(client):
    # Test valid good ID
    response = client.get('/sales/goods/1')
    assert response.status_code == 200
    data = response.get_json()
    assert data['name'] == 'Item1'
    assert data['stock_count'] == 10

    # Test invalid good ID
    response = client.get('/sales/goods/999')
    assert response.status_code == 404
    data = response.get_json()
    assert data['error'] == 'Good not found'


def test_make_sale_success(client):
    sale_data = {
        'username': 'testuser',
        'good_name': 'Item1',
        'quantity': 2
    }
    response = client.post('/sales', json=sale_data)
    assert response.status_code == 200
    data = response.get_json()
    assert data['message'] == 'Sale successful'
    assert data['customer_balance'] == 80.0  # 100 - (2 * 10)
    assert data['remaining_stock'] == 8  # 10 - 2


def test_make_sale_insufficient_stock(client):
    sale_data = {
        'username': 'testuser',
        'good_name': 'Item1',
        'quantity': 20  # Exceeds stock
    }
    response = client.post('/sales', json=sale_data)
    assert response.status_code == 400
    data = response.get_json()
    assert data['error'] == 'Good not available or insufficient stock'


def test_make_sale_insufficient_funds(client):
    sale_data = {
        'username': 'testuser',
        'good_name': 'Item1',
        'quantity': 15  # Total price will be 150, exceeds wallet balance
    }
    response = client.post('/sales', json=sale_data)
    assert response.status_code == 400
    data = response.get_json()
    assert data['error'] == 'Insufficient funds'


def test_make_sale_nonexistent_customer(client):
    sale_data = {
        'username': 'nonexistent_user',
        'good_name': 'Item1',
        'quantity': 1
    }
    response = client.post('/sales', json=sale_data)
    assert response.status_code == 404
    data = response.get_json()
    assert data['error'] == 'Customer not found'


def test_make_sale_nonexistent_good(client):
    sale_data = {
        'username': 'testuser',
        'good_name': 'Nonexistent Item',
        'quantity': 1
    }
    response = client.post('/sales', json=sale_data)
    assert response.status_code == 400
    data = response.get_json()
    assert data['error'] == 'Good not available or insufficient stock'


def test_get_purchase_history(client):
    # Make a sale first
    sale_data = {
        'username': 'testuser',
        'good_name': 'Item1',
        'quantity': 1
    }
    client.post('/sales', json=sale_data)

    response = client.get('/sales/history/testuser')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1
    sale_record = data[0]
    assert sale_record['quantity'] == 1
    assert sale_record['total_price'] == 10.0
    assert 'timestamp' in sale_record



def test_get_purchase_history_no_purchases(client):
    response = client.get('/sales/history/testuser')
    assert response.status_code == 200
    data = response.get_json()
    assert data == []


def test_get_purchase_history_nonexistent_customer(client):
    response = client.get('/sales/history/nonexistent_user')
    assert response.status_code == 404
    data = response.get_json()
    assert data['error'] == 'Customer not found'
