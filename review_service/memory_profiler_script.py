from memory_profiler import profile
from flask import Flask
from app import (
    submit_review,
    update_review,
    delete_review,
    flag_review,
    moderate_review,
    get_product_reviews,
    get_customer_reviews,
    get_flagged_reviews,
    get_review_details,
)
from flask_jwt_extended import create_access_token, JWTManager

# Mocking Flask Application for Test Requests
app = Flask(__name__)

# Configure Flask for Testing
app.config['TESTING'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Talineslim0303$@localhost/review_service'
app.config['JWT_SECRET_KEY'] = 'test_secret'
jwt = JWTManager(app)

@profile
def test_submit_review():
    with app.test_request_context():
        token = create_access_token(identity=1)
        with app.test_client() as client:
            response = client.post(
                '/reviews',
                json={"customer_id": 1, "product_id": 1, "rating": 5, "comment": "Great product!"},
                headers={"Authorization": f"Bearer {token}"},
            )
            print(response.json)


@profile
def test_update_review():
    with app.test_request_context():
        token = create_access_token(identity=1)
        with app.test_client() as client:
            response = client.put(
                '/reviews/1',
                json={"rating": 4, "comment": "Updated review comment"},
                headers={"Authorization": f"Bearer {token}"},
            )
            print(response.json)


@profile
def test_delete_review():
    with app.test_request_context():
        token = create_access_token(identity=1)
        with app.test_client() as client:
            response = client.delete(
                '/reviews/1',
                headers={"Authorization": f"Bearer {token}"},
            )
            print(response.json)


@profile
def test_flag_review():
    with app.test_request_context():
        token = create_access_token(identity=1)
        with app.test_client() as client:
            response = client.post(
                '/reviews/1/flag',
                headers={"Authorization": f"Bearer {token}"},
            )
            print(response.json)


@profile
def test_moderate_review():
    with app.test_request_context():
        token = create_access_token(identity=1, additional_claims={"is_admin": True})
        with app.test_client() as client:
            response = client.post(
                '/reviews/1/moderate',
                json={"approve": True},
                headers={"Authorization": f"Bearer {token}"},
            )
            print(response.json)


@profile
def test_get_product_reviews():
    with app.test_request_context():
        with app.test_client() as client:
            response = client.get('/reviews/product/1')
            print(response.json)


@profile
def test_get_customer_reviews():
    with app.test_request_context():
        token = create_access_token(identity=1)
        with app.test_client() as client:
            response = client.get(
                '/reviews/customer/1',
                headers={"Authorization": f"Bearer {token}"},
            )
            print(response.json)


@profile
def test_get_flagged_reviews():
    with app.test_request_context():
        token = create_access_token(identity=1, additional_claims={"is_admin": True})
        with app.test_client() as client:
            response = client.get(
                '/reviews/flagged',
                headers={"Authorization": f"Bearer {token}"},
            )
            print(response.json)


@profile
def test_get_review_details():
    with app.test_request_context():
        token = create_access_token(identity=1)
        with app.test_client() as client:
            response = client.get(
                '/reviews/1',
                headers={"Authorization": f"Bearer {token}"},
            )
            print(response.json)


if __name__ == '__main__':
    test_submit_review()
    test_update_review()
    test_delete_review()
    test_flag_review()
    test_moderate_review()
    test_get_product_reviews()
    test_get_customer_reviews()
    test_get_flagged_reviews()
    test_get_review_details()
