from flask import Flask, request, jsonify
from models import db, Review

app = Flask(__name__)

# Configurations
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Talineslim0303$@localhost/reviews_service'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Submit a Review
@app.route('/reviews', methods=['POST'])
def submit_review():
    data = request.get_json()
    new_review = Review(
        customer_id=data['customer_id'],
        product_id=data['product_id'],
        rating=data['rating'],
        comment=data['comment']
    )
    db.session.add(new_review)
    db.session.commit()
    return jsonify({"message": "Review submitted successfully!", "review_id": new_review.id}), 201

# Update a Review
@app.route('/reviews/<int:review_id>', methods=['PUT'])
def update_review(review_id):
    review = Review.query.get(review_id)
    if not review:
        return jsonify({"error": "Review not found"}), 404

    data = request.get_json()
    if 'rating' in data:
        review.rating = data['rating']
    if 'comment' in data:
        review.comment = data['comment']
    db.session.commit()
    return jsonify({"message": "Review updated successfully"}), 200

# Delete a Review
@app.route('/reviews/<int:review_id>', methods=['DELETE'])
def delete_review(review_id):
    review = Review.query.get(review_id)
    if not review:
        return jsonify({"error": "Review not found"}), 404

    db.session.delete(review)
    db.session.commit()
    return jsonify({"message": "Review deleted successfully"}), 200

# Get All Reviews for a Product
@app.route('/reviews/product/<int:product_id>', methods=['GET'])
def get_product_reviews(product_id):
    reviews = Review.query.filter_by(product_id=product_id).all()
    return jsonify([
        {"id": r.id, "rating": r.rating, "comment": r.comment, "timestamp": r.timestamp, "customer_id": r.customer_id}
        for r in reviews
    ]), 200

# Get All Reviews for a Customer
@app.route('/reviews/customer/<int:customer_id>', methods=['GET'])
def get_customer_reviews(customer_id):
    reviews = Review.query.filter_by(customer_id=customer_id).all()
    return jsonify([
        {"id": r.id, "product_id": r.product_id, "rating": r.rating, "comment": r.comment, "timestamp": r.timestamp}
        for r in reviews
    ]), 200

# Moderate a Review
@app.route('/reviews/<int:review_id>/moderate', methods=['POST'])
def moderate_review(review_id):
    review = Review.query.get(review_id)
    if not review:
        return jsonify({"error": "Review not found"}), 404

    data = request.get_json()
    if 'flagged' in data:
        review.flagged = data['flagged']
    if 'moderated' in data:
        review.moderated = data['moderated']
    db.session.commit()
    return jsonify({"message": "Review moderation updated successfully"}), 200

# Get Review Details
@app.route('/reviews/<int:review_id>', methods=['GET'])
def get_review_details(review_id):
    review = Review.query.get(review_id)
    if not review:
        return jsonify({"error": "Review not found"}), 404

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
 
