"""
Review Management Service

This Flask application provides a RESTful API for managing product reviews. It includes
features for submitting, updating, deleting, flagging, and moderating reviews. Users can
also retrieve reviews for products or customers, with appropriate role-based access control.

Features:
- Submit and manage product reviews (Authenticated users only).
- Flag reviews for moderation (Authenticated users only).
- Moderate flagged reviews (Admins only).
- Retrieve reviews for products or customers.
- View flagged reviews (Admins only).

Modules:
- Flask: Core framework for the application.
- Flask-JWT-Extended: For token-based authentication.
- SQLAlchemy: ORM for database interactions.
- Marshmallow: Input validation and serialization.
- Bleach: Input sanitization to prevent XSS attacks.

"""

from flask import Flask, request, jsonify
from models import db, Review
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity, get_jwt
)
import bleach
from marshmallow import Schema, fields, ValidationError, validate
import sys
import os

# Add parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import config  # Import config after adding parent directory

app = Flask(__name__)

# Configurations
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Talineslim0303$@localhost/reviews_service'
app.config['JWT_SECRET_KEY'] = config.JWT_SECRET_KEY
app.config['JWT_ALGORITHM'] = config.JWT_ALGORITHM

db.init_app(app)
jwt = JWTManager(app)

class ReviewSchema(Schema):
    """
    Schema for validating review data.

    Attributes:
        customer_id (fields.Int): ID of the customer submitting the review.
        product_id (fields.Int): ID of the product being reviewed.
        rating (fields.Int): Rating given to the product (1 to 5).
        comment (fields.Str): Optional comment for the review (max 500 characters).
    """
    customer_id = fields.Int(required=True, validate=lambda x: x > 0)
    product_id = fields.Int(required=True, validate=lambda x: x > 0)
    rating = fields.Int(required=True, validate=validate.Range(min=1, max=5))
    comment = fields.Str(required=True, validate=validate.Length(max=500))

review_schema = ReviewSchema()

def sanitize_input(data):
    """
    Sanitizes input to prevent XSS attacks.

    Args:
        data (str | dict | list): Input data to sanitize.

    Returns:
        Sanitized input in the same format as provided.
    """
    if isinstance(data, str):
        return bleach.clean(data)
    elif isinstance(data, dict):
        return {k: sanitize_input(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_input(v) for v in data]
    else:
        return data

# Submit a Review (Authenticated Users Only)
@app.route('/reviews', methods=['POST'])
@jwt_required()
def submit_review():
    """
    Submits a new review for a product.

    Authenticated users can submit reviews for products they have purchased.

    Returns:
        Response: JSON response containing a success message and review ID,
        or an error message if validation fails.
    """
    current_user_id = get_jwt_identity()

    try:
        data = review_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(err.messages), 400

    data = sanitize_input(data)
    if data['customer_id'] != int(current_user_id):
        return jsonify({"error": "Unauthorized action"}), 403

    new_review = Review(
        customer_id=data['customer_id'],
        product_id=data['product_id'],
        rating=data['rating'],
        comment=data['comment'],
        flagged=False,
        moderated=False
    )
    db.session.add(new_review)
    db.session.commit()
    return jsonify({"message": "Review submitted successfully!", "review_id": new_review.id}), 201

# Update a Review (Authenticated Users Only)
@app.route('/reviews/<int:review_id>', methods=['PUT'])
@jwt_required()
def update_review(review_id):
    """
    Updates an existing review.

    Users can only update their own reviews.

    Args:
        review_id (int): ID of the review to update.

    Returns:
        Response: JSON response containing success message, or an error message
        if unauthorized or invalid data.
    """
    current_user_id = get_jwt_identity()
    review = Review.query.get(review_id)

    if not review:
        return jsonify({"error": "Review not found"}), 404

    if review.customer_id != int(current_user_id):
        return jsonify({"error": "Unauthorized action"}), 403

    try:
        data = review_schema.load(request.get_json(), partial=True)
    except ValidationError as err:
        return jsonify(err.messages), 400

    data = sanitize_input(data)

    if 'rating' in data:
        review.rating = data['rating']
    if 'comment' in data:
        review.comment = data['comment']

    db.session.commit()
    return jsonify({"message": "Review updated successfully"}), 200

# Delete a Review (Authenticated Users Only)
@app.route('/reviews/<int:review_id>', methods=['DELETE'])
@jwt_required()
def delete_review(review_id):
    """
    Deletes a review.

    Users can only delete their own reviews.

    Args:
        review_id (int): ID of the review to delete.

    Returns:
        Response: JSON response containing success message, or an error message
        if unauthorized or review not found.
    """
    current_user_id = get_jwt_identity()
    review = Review.query.get(review_id)

    if not review:
        return jsonify({"error": "Review not found"}), 404

    if review.customer_id != int(current_user_id):
        return jsonify({"error": "Unauthorized action"}), 403

    db.session.delete(review)
    db.session.commit()
    return jsonify({"message": "Review deleted successfully"}), 200

# Flag a Review for Moderation (Authenticated Users Only)
@app.route('/reviews/<int:review_id>/flag', methods=['POST'])
@jwt_required()
def flag_review(review_id):
    """
    Flags a review for moderation.

    Any authenticated user can flag a review.

    Args:
        review_id (int): ID of the review to flag.

    Returns:
        Response: JSON response containing a success message, or an error
        message if review not found.
    """
    review = Review.query.get(review_id)

    if not review:
        return jsonify({"error": "Review not found"}), 404

    review.flagged = True
    db.session.commit()
    return jsonify({"message": "Review flagged for moderation"}), 200
# Moderate a Review (Admins Only)
@app.route('/reviews/<int:review_id>/moderate', methods=['POST'])
@jwt_required()
def moderate_review(review_id):
    """
    Moderates a flagged review.

    Admin-only endpoint. Allows admins to approve or reject flagged reviews.

    Args:
        review_id (int): ID of the review to moderate.

    Returns:
        Response: JSON response containing a success message if the moderation
        action is completed, or an error message if unauthorized or review not found.
    """
    claims = get_jwt()
    if not claims.get('is_admin', False):
        return jsonify({"error": "Unauthorized action"}), 403

    review = Review.query.get(review_id)
    if not review:
        return jsonify({"error": "Review not found"}), 404

    data = request.get_json()

    if 'approve' in data and data['approve']:
        review.moderated = True
        review.flagged = False
        db.session.commit()
        return jsonify({"message": "Review approved."}), 200

    if 'reject' in data and data['reject']:
        review.comment = "[Removed due to inappropriate content]"
        review.moderated = True
        review.flagged = False
        db.session.commit()
        return jsonify({"message": "Review rejected as inappropriate."}), 200

    return jsonify({"error": "Invalid moderation action"}), 400

# Get All Reviews for a Product (No Authentication Required)
@app.route('/reviews/product/<int:product_id>', methods=['GET'])
def get_product_reviews(product_id):
    """
    Retrieves all reviews for a specific product.

    Public endpoint. No authentication required.

    Args:
        product_id (int): ID of the product to retrieve reviews for.

    Returns:
        Response: JSON response containing a list of reviews for the product.
    """
    reviews = Review.query.filter_by(product_id=product_id).all()
    return jsonify([
        {"id": r.id, "rating": r.rating, "comment": r.comment, "timestamp": r.timestamp, "customer_id": r.customer_id}
        for r in reviews
    ]), 200

# Get All Reviews for a Customer (Authenticated Users Only)
@app.route('/reviews/customer/<int:customer_id>', methods=['GET'])
@jwt_required()
def get_customer_reviews(customer_id):
    """
    Retrieves all reviews submitted by a specific customer.

    Authenticated users can only view their own reviews.

    Args:
        customer_id (int): ID of the customer whose reviews are being requested.

    Returns:
        Response: JSON response containing a list of the customer's reviews,
        or an error message if unauthorized.
    """
    current_user_id = get_jwt_identity()

    if customer_id != int(current_user_id):
        return jsonify({"error": "Unauthorized action"}), 403

    reviews = Review.query.filter_by(customer_id=customer_id).all()
    return jsonify([
        {"id": r.id, "product_id": r.product_id, "rating": r.rating, "comment": r.comment, "timestamp": r.timestamp}
        for r in reviews
    ]), 200

# Get All Flagged Reviews (Admins Only)
@app.route('/reviews/flagged', methods=['GET'])
@jwt_required()
def get_flagged_reviews():
    """
    Retrieves all flagged reviews pending moderation.

    Admin-only endpoint.

    Returns:
        Response: JSON response containing a list of flagged reviews, or an error
        message if unauthorized.
    """
    claims = get_jwt()
    if not claims.get('is_admin', False):
        return jsonify({"error": "Unauthorized action"}), 403

    flagged_reviews = Review.query.filter_by(flagged=True, moderated=False).all()
    return jsonify([
        {
            "id": r.id,
            "customer_id": r.customer_id,
            "product_id": r.product_id,
            "rating": r.rating,
            "comment": r.comment,
            "timestamp": r.timestamp
        }
        for r in flagged_reviews
    ]), 200

# Get Review Details (Authenticated Users Only)
@app.route('/reviews/<int:review_id>', methods=['GET'])
@jwt_required()
def get_review_details(review_id):
    """
    Retrieves details of a specific review.

    Authenticated users can only view their own reviews, while admins can view any review.

    Args:
        review_id (int): ID of the review to retrieve.

    Returns:
        Response: JSON response containing the review details, or an error message
        if unauthorized or review not found.
    """
    review = Review.query.get(review_id)
    if not review:
        return jsonify({"error": "Review not found"}), 404

    current_user_id = get_jwt_identity()
    claims = get_jwt()

    if review.customer_id != int(current_user_id) and not claims.get('is_admin', False):
        return jsonify({"error": "Unauthorized action"}), 403

    return jsonify({
        "id": review.id,
        "customer_id": review.customer_id,
        "product_id": review.product_id,
        "rating": review.rating,
        "comment": review.comment,
        "timestamp": review.timestamp,
        "moderated": review.moderated,
        "flagged": review.flagged
    }), 200


if __name__ == '__main__':
    """
    Entry point for running the Flask application.

    Ensures the database tables are created before starting the server.
    """
    import cProfile
    import pstats
    with app.app_context():
        db.create_all()
    profiler = cProfile.Profile()
    profiler.enable()
    app.run(debug=True)
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.strip_dirs()
    stats.sort_stats('time')  # Sort by time
    stats.print_stats(30)    # Print top 30 results

