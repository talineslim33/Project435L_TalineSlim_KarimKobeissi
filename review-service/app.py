import time
from flask import Flask, request, jsonify
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity, get_jwt
)
from marshmallow import Schema, fields, ValidationError, validate
from models import db, Review
import bleach
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

# Rate limiting configurations
RATE_LIMIT_WINDOW = 60  # in seconds (1 minute window)
MAX_REQUESTS_PER_WINDOW = 10  # maximum requests per IP per window

rate_limit_data = {}

db.init_app(app)
jwt = JWTManager(app)

# Marshmallow Schemas for Validation
class ReviewSchema(Schema):
    customer_id = fields.Int(required=True, validate=lambda x: x > 0)
    product_id = fields.Int(required=True, validate=lambda x: x > 0)
    rating = fields.Int(required=True, validate=validate.Range(min=1, max=5))
    comment = fields.Str(required=True, validate=validate.Length(max=500))

review_schema = ReviewSchema()

# Helper function for sanitizing input
def sanitize_input(data):
    if isinstance(data, str):
        return bleach.clean(data)
    elif isinstance(data, dict):
        return {k: sanitize_input(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_input(v) for v in data]
    else:
        return data

# Rate limiting decorator
def rate_limiter(func):
    def wrapper(*args, **kwargs):
        ip_address = request.remote_addr
        current_time = time.time()

        # Check if the IP is in the rate limit data
        if ip_address in rate_limit_data:
            request_count, last_request_time = rate_limit_data[ip_address]

            # If the window has expired, reset the count and timestamp
            if current_time - last_request_time > RATE_LIMIT_WINDOW:
                rate_limit_data[ip_address] = [1, current_time]
            else:
                # If within the window, increase the count
                if request_count >= MAX_REQUESTS_PER_WINDOW:
                    return jsonify({'error': 'Too many requests. Please try again later.'}), 429
                else:
                    rate_limit_data[ip_address][0] += 1
        else:
            # If the IP is new, set up initial request count and timestamp
            rate_limit_data[ip_address] = [1, current_time]

        return func(*args, **kwargs)

    return wrapper

# Submit a Review (Authenticated Users Only)
@app.route('/reviews', methods=['POST'])
@jwt_required()
@rate_limiter
def submit_review():
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
@rate_limiter
def update_review(review_id):
    current_user_id = get_jwt_identity()
    review = Review.query.get(review_id)

    if not review:
        return jsonify({"error": "Review not found"}), 404

    # Users can only update their own reviews
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
@rate_limiter
def delete_review(review_id):
    current_user_id = get_jwt_identity()
    review = Review.query.get(review_id)

    if not review:
        return jsonify({"error": "Review not found"}), 404

    # Users can only delete their own reviews
    if review.customer_id != int(current_user_id):
        return jsonify({"error": "Unauthorized action"}), 403

    db.session.delete(review)
    db.session.commit()
    return jsonify({"message": "Review deleted successfully"}), 200

# Flag a Review for Moderation (Authenticated Users Only)
@app.route('/reviews/<int:review_id>/flag', methods=['POST'])
@jwt_required()
@rate_limiter
def flag_review(review_id):
    review = Review.query.get(review_id)

    if not review:
        return jsonify({"error": "Review not found"}), 404

    # Allow any authenticated user to flag reviews
    review.flagged = True
    db.session.commit()
    return jsonify({"message": "Review flagged for moderation"}), 200

# Moderate a Review (Admins Only)
@app.route('/reviews/<int:review_id>/moderate', methods=['POST'])
@jwt_required()
@rate_limiter
def moderate_review(review_id):
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
@rate_limiter
def get_product_reviews(product_id):
    reviews = Review.query.filter_by(product_id=product_id).all()
    return jsonify([
        {"id": r.id, "rating": r.rating, "comment": r.comment, "timestamp": r.timestamp, "customer_id": r.customer_id}
        for r in reviews
    ]), 200

# Get All Reviews for a Customer (Authenticated Users Only)
@app.route('/reviews/customer/<int:customer_id>', methods=['GET'])
@jwt_required()
@rate_limiter
def get_customer_reviews(customer_id):
    current_user_id = get_jwt_identity()

    # Users can only view their own reviews
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
@rate_limiter
def get_flagged_reviews():
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
@rate_limiter
def get_review_details(review_id):
    review = Review.query.get(review_id)
    if not review:
        return jsonify({"error": "Review not found"}), 404

    current_user_id = get_jwt_identity()
    claims = get_jwt()
    
    # Users can only view their own reviews, Admins can view any review
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
    with app.app_context():
        db.create_all()
    app.run(debug=True)
