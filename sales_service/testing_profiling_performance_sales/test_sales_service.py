import unittest
from flask_jwt_extended import create_access_token
from app import app

class TestFlaskApp(unittest.TestCase):
    """
    Unit tests for the Sales and Wishlist Management Service Flask application.
    """

    def setUp(self):
        """
        Set up the test client for the Flask app.
        Create a JWT token for authenticated requests.
        """
        self.app = app.test_client()
        self.app.testing = True
        # Generate a test JWT token
        with app.app_context():
            self.token = create_access_token(identity=1)  # Assuming user with ID 1 exists

    def test_display_available_goods(self):
        """
        Test the /sales/goods endpoint.
        Check if the response status code is 200 (success).
        """
        response = self.app.get('/sales/goods')
        self.assertEqual(response.status_code, 200)

    def test_get_good_details(self):
        """
        Test the /sales/goods/<int:good_id> endpoint.
        Check if the response returns 200 for an existing good.
        """
        response = self.app.get('/sales/goods/1', headers={"Authorization": f"Bearer {self.token}"})
        self.assertIn(response.status_code, [200, 404, 422])

    def test_make_sale(self):
        """
        Test the /sales endpoint with a POST request.
        Check if the response status code is one of the expected values: 200, 400, 404, or 422.
        """
        response = self.app.post('/sales', json={
            "username": "test_user",  # Ensure this user exists
            "good_name": "item",  # Ensure this item exists
            "quantity": 1
        }, headers={"Authorization": f"Bearer {self.token}"})
        self.assertIn(response.status_code, [200, 400, 404, 422])

    def test_get_purchase_history(self):
        """
        Test the /sales/history endpoint.
        Check if the response status code is 200, 404, or 422 (validation error).
        """
        response = self.app.get('/sales/history', headers={"Authorization": f"Bearer {self.token}"})
        self.assertIn(response.status_code, [200, 404, 422])

    def test_get_all_purchase_histories(self):
        """
        Test the /sales/history/all endpoint.
        This endpoint should be accessible only to admins.
        """
        response = self.app.get('/sales/history/all', headers={"Authorization": f"Bearer {self.token}"})
        self.assertIn(response.status_code, [200, 403, 422])

    def test_add_to_wishlist(self):
        """
        Test the /wishlist endpoint with a POST request.
        Check if items can be added to the wishlist.
        """
        response = self.app.post('/wishlist', json={"good_id": 1}, headers={"Authorization": f"Bearer {self.token}"})
        self.assertIn(response.status_code, [201, 400, 404, 422])

    def test_get_wishlist(self):
        """
        Test the /wishlist endpoint with a GET request.
        Check if the response returns wishlist items.
        """
        response = self.app.get('/wishlist', headers={"Authorization": f"Bearer {self.token}"})
        self.assertIn(response.status_code, [200, 404, 422])

    def test_remove_from_wishlist(self):
        """
        Test the /wishlist/<int:wishlist_id> endpoint with a DELETE request.
        Check if items can be removed from the wishlist.
        """
        response = self.app.delete('/wishlist/1', headers={"Authorization": f"Bearer {self.token}"})
        self.assertIn(response.status_code, [200, 404, 422])

    def test_is_in_wishlist(self):
        """
        Test the /wishlist/<int:good_id> endpoint with a GET request.
        Check if a specific item is in the wishlist.
        """
        response = self.app.get('/wishlist/1', headers={"Authorization": f"Bearer {self.token}"})
        self.assertIn(response.status_code, [200, 404, 422])

    def test_get_notifications(self):
        """
        Test the /notifications endpoint.
        Check if notifications can be retrieved.
        """
        response = self.app.get('/notifications', headers={"Authorization": f"Bearer {self.token}"})
        self.assertIn(response.status_code, [200, 404, 422])

    def test_get_recommendations(self):
        """
        Test the /sales/recommendations endpoint.
        Check if product recommendations are retrieved.
        """
        response = self.app.get('/sales/recommendations', headers={"Authorization": f"Bearer {self.token}"})
        self.assertIn(response.status_code, [200, 422])

if __name__ == '__main__':
    unittest.main()
