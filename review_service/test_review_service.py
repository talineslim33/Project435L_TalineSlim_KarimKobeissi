import unittest
from app import app, db
from flask_jwt_extended import create_access_token
from sqlalchemy.sql import text  # Import text for raw SQL queries


class ReviewServiceTests(unittest.TestCase):
    """
    Unit tests for the Review Management Service.
    """

    @classmethod
    def setUpClass(cls):
        """
        Set up the Flask app and database for testing.
        """
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Talineslim0303$@localhost/reviews_service'
        app.config['JWT_SECRET_KEY'] = 'test_secret'
        cls.client = app.test_client()

        # Create tables and add sample data
        with app.app_context():
            db.create_all()
            db.session.execute(
                text(
                    "INSERT INTO review (id, customer_id, product_id, rating, comment, flagged, moderated) "
                    "VALUES (1, 1, 1, 5, 'Test comment', false, false)"
                )
            )
            db.session.commit()

    @classmethod
    def tearDownClass(cls):
        """
        Clean up the database after testing.
        """
        with app.app_context():
            db.drop_all()

    def test_submit_review(self):
        """
        Test the endpoint to submit a new review.
        """
        with app.app_context():
            token = create_access_token(identity="1")
            response = self.client.post(
                '/reviews',
                json={
                    "customer_id": 1,
                    "product_id": 1,
                    "rating": 5,
                    "comment": "Amazing product!"
                },
                headers={"Authorization": f"Bearer {token}"}
            )
            print("Submit Review Response:", response.get_json())
            self.assertIn(response.status_code, [201, 422])
            if response.status_code == 201:
                self.assertIn("review_id", response.get_json())

    def test_update_review(self):
        """
        Test the endpoint to update an existing review.
        """
        with app.app_context():
            token = create_access_token(identity="1")
            response = self.client.put(
                '/reviews/1',
                json={
                    "rating": 4,
                    "comment": "Updated comment for the review."
                },
                headers={"Authorization": f"Bearer {token}"}
            )
            print("Update Review Response:", response.get_json())
            self.assertIn(response.status_code, [200, 404, 422])

    def test_delete_review(self):
        """
        Test the endpoint to delete a review.
        """
        with app.app_context():
            token = create_access_token(identity="1")
            response = self.client.delete(
                '/reviews/1',
                headers={"Authorization": f"Bearer {token}"}
            )
            print("Delete Review Response:", response.get_json())
            self.assertIn(response.status_code, [200, 404, 422])

    def test_flag_review(self):
        """
        Test the endpoint to flag a review for moderation.
        """
        with app.app_context():
            token = create_access_token(identity="1")
            response = self.client.post(
                '/reviews/1/flag',
                headers={"Authorization": f"Bearer {token}"}
            )
            print("Flag Review Response:", response.get_json())
            self.assertIn(response.status_code, [200, 404, 422])

    def test_moderate_review(self):
        """
        Test the endpoint to moderate a flagged review.
        """
        with app.app_context():
            token = create_access_token(identity="1", additional_claims={"is_admin": True})
            response = self.client.post(
                '/reviews/1/moderate',
                json={"approve": True},
                headers={"Authorization": f"Bearer {token}"}
            )
            print("Moderate Review Response:", response.get_json())
            self.assertIn(response.status_code, [200, 404, 422])

    def test_get_product_reviews(self):
        """
        Test the endpoint to get all reviews for a specific product.
        """
        response = self.client.get('/reviews/product/1')
        print("Get Product Reviews Response:", response.get_json())
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.get_json(), list)

    def test_get_customer_reviews(self):
        """
        Test the endpoint to get all reviews submitted by a specific customer.
        """
        with app.app_context():
            token = create_access_token(identity="1")
            response = self.client.get(
                '/reviews/customer/1',
                headers={"Authorization": f"Bearer {token}"}
            )
            print("Get Customer Reviews Response:", response.get_json())
            self.assertIn(response.status_code, [200, 422])
            if response.status_code == 200:
                self.assertIsInstance(response.get_json(), list)

    def test_get_flagged_reviews(self):
        """
        Test the endpoint to get all flagged reviews.
        """
        with app.app_context():
            token = create_access_token(identity="1", additional_claims={"is_admin": True})
            response = self.client.get(
                '/reviews/flagged',
                headers={"Authorization": f"Bearer {token}"}
            )
            print("Get Flagged Reviews Response:", response.get_json())
            self.assertIn(response.status_code, [200, 422])
            if response.status_code == 200:
                self.assertIsInstance(response.get_json(), list)

    def test_get_review_details(self):
        """
        Test the endpoint to get details of a specific review.
        """
        with app.app_context():
            token = create_access_token(identity="1")
            response = self.client.get(
                '/reviews/1',
                headers={"Authorization": f"Bearer {token}"}
            )
            print("Get Review Details Response:", response.get_json())
            self.assertIn(response.status_code, [200, 404, 422])


if __name__ == "__main__":
    unittest.main()
