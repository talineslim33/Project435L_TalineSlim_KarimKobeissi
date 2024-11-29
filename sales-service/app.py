from flask import Flask, request, jsonify
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity, get_jwt
)
from marshmallow import Schema, fields, ValidationError, validate
from models import db, Good, Inventory, Customer, Sale, Wishlist, Notification
import bleach
import sys
import os

# Add parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import config  # Import config after adding parent directory

app = Flask(__name__)

# Configurations
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Talineslim0303$@localhost/sales_service'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = config.JWT_SECRET_KEY
app.config['JWT_ALGORITHM'] = config.JWT_ALGORITHM

db.init_app(app)
jwt = JWTManager(app)

# Marshmallow Schemas for Validation
class SaleSchema(Schema):
    username = fields.Str(required=True, validate=validate.Length(min=4, max=20))
    good_name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    quantity = fields.Int(required=False, validate=validate.Range(min=1))

sale_schema = SaleSchema()

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

# Display available goods
@app.route('/sales/goods', methods=['GET'])
@jwt_required(optional=True)
def display_available_goods():
    claims = get_jwt()
    is_admin = claims.get('is_admin', False) if claims else False
    goods = Good.query.join(Inventory).filter(Inventory.stock_count > 0).all()
    return jsonify([
        {"name": g.name, "price": g.price_per_item} if is_admin else {"name": g.name}
        for g in goods
    ]), 200

# Get good details
@app.route('/sales/goods/<int:good_id>', methods=['GET'])
@jwt_required(optional=True)
def get_good_details(good_id):
    claims = get_jwt()
    is_admin = claims.get('is_admin', False) if claims else False

    good = Good.query.get(good_id)
    if not good:
        return jsonify({"error": "Good not found"}), 404

    response_data = {
        "name": good.name,
        "price_per_item": good.price_per_item
    }
    if is_admin:
        response_data.update({
            "category": good.category,
            "description": good.description,
            "stock_count": good.inventory.stock_count if good.inventory else 0
        })

    return jsonify(response_data), 200

# Make a sale (Authenticated users only)
@app.route('/sales', methods=['POST'])
@jwt_required()
def make_sale():
    current_user_id = get_jwt_identity()

    try:
        # Load and validate input data using Marshmallow
        data = sale_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(err.messages), 400

    # Sanitize input
    data = sanitize_input(data)

    # Get customer and good details
    customer = Customer.query.get(current_user_id)
    good = Good.query.filter_by(name=data['good_name']).first()

    if not customer:
        return jsonify({"error": "Customer not found"}), 404
    if not good or not good.inventory or good.inventory.stock_count < data['quantity']:
        return jsonify({"error": "Good not available or insufficient stock"}), 400

    total_price = data['quantity'] * good.price_per_item
    if customer.wallet_balance < total_price:
        return jsonify({"error": "Insufficient funds"}), 400

    # Process the sale
    customer.wallet_balance -= total_price
    good.inventory.stock_count -= data['quantity']

    # Record the sale
    sale = Sale(
        customer_id=customer.id,
        good_id=good.id,
        quantity=data['quantity'],
        total_price=total_price
    )
    db.session.add(sale)
    db.session.commit()

    return jsonify({
        "message": "Sale successful",
        "customer_balance": customer.wallet_balance,
        "remaining_stock": good.inventory.stock_count
    }), 200

# Get customer's purchase history (Authenticated users only)
@app.route('/sales/history', methods=['GET'])
@jwt_required()
def get_purchase_history():
    current_user_id = get_jwt_identity()
    customer = Customer.query.get(current_user_id)
    if not customer:
        return jsonify({"error": "Customer not found"}), 404

    sales = Sale.query.filter_by(customer_id=customer.id).all()
    return jsonify([
        {
            "good_name": sale.good.name,
            "quantity": sale.quantity,
            "total_price": sale.total_price,
            "timestamp": sale.timestamp
        }
        for sale in sales
    ]), 200

# Get all purchase histories (Admin only)
@app.route('/sales/history/all', methods=['GET'])
@jwt_required()
def get_all_purchase_histories():
    claims = get_jwt()
    if not claims.get('is_admin', False):
        return jsonify({"error": "Unauthorized action"}), 403

    sales = Sale.query.all()
    return jsonify([
        {
            "customer_id": sale.customer_id,
            "good_name": sale.good.name,
            "quantity": sale.quantity,
            "total_price": sale.total_price,
            "timestamp": sale.timestamp
        }
        for sale in sales
    ]), 200

@app.route('/wishlist', methods=['POST'])
@jwt_required()
def add_to_wishlist():
    current_user_id = get_jwt_identity()
    data = request.get_json()

    # Extract good_id from request data
    good_id = data.get('good_id')

    # Validate that the good exists
    good = Good.query.get(good_id)
    if not good:
        return jsonify({"error": "Good not found"}), 404

    # Check if already in wishlist
    if Wishlist.query.filter_by(customer_id=current_user_id, good_id=good_id).first():
        return jsonify({"message": "Item already in wishlist"}), 400

    # Add to wishlist
    new_wishlist_item = Wishlist(customer_id=current_user_id, good_id=good_id)
    db.session.add(new_wishlist_item)
    db.session.commit()
    return jsonify({"message": "Item added to wishlist successfully"}), 201

@app.route('/wishlist/<int:wishlist_id>', methods=['DELETE'])
@jwt_required()
def remove_from_wishlist(wishlist_id):
    current_user_id = get_jwt_identity()

    wishlist_item = Wishlist.query.filter_by(id=wishlist_id, customer_id=current_user_id).first()

    if not wishlist_item:
        return jsonify({"error": "Item not found in wishlist"}), 404

    db.session.delete(wishlist_item)
    db.session.commit()
    return jsonify({"message": "Item removed from wishlist"}), 200


@app.route('/wishlist', methods=['GET'])
@jwt_required()
def get_wishlist():
    current_user_id = get_jwt_identity()

    # Get all wishlist items for the customer
    wishlist_items = Wishlist.query.filter_by(customer_id=current_user_id).all()
    return jsonify([
        {
            "good_id": item.good_id,
            "name": item.good.name,
            "category": item.good.category,
            "price": item.good.price_per_item,
            "description": item.good.description
        } for item in wishlist_items
    ]), 200


@app.route('/wishlist/<int:good_id>', methods=['GET'])
@jwt_required()
def is_in_wishlist(good_id):
    current_user_id = get_jwt_identity()

    # Check if the good is in the wishlist
    wishlist_item = Wishlist.query.filter_by(customer_id=current_user_id, good_id=good_id).first()
    if wishlist_item:
        return jsonify({"in_wishlist": True}), 200
    else:
        return jsonify({"in_wishlist": False}), 404


from collections import Counter

def get_recommendations_for_customer(customer_id):
    customer_purchases = Sale.query.filter_by(customer_id=customer_id).all()
    purchased_goods_ids = {sale.good_id for sale in customer_purchases}

    similar_customers = Sale.query.filter(Sale.good_id.in_(purchased_goods_ids)).all()
    similar_customer_ids = {sale.customer_id for sale in similar_customers if sale.customer_id != customer_id}

    # Get goods purchased by similar customers, excluding goods already purchased by the current customer
    recommendations = []
    for customer in similar_customer_ids:
        customer_sales = Sale.query.filter_by(customer_id=customer).all()
        recommendations.extend([sale.good_id for sale in customer_sales if sale.good_id not in purchased_goods_ids])

    # Count the frequency of each recommended good and return the top recommended items
    recommended_good_ids = [good_id for good_id in recommendations]
    most_common_goods = Counter(recommended_good_ids).most_common(5)  # Get top 5 recommendations

    # Fetch good details for recommendations
    recommended_goods = Good.query.filter(Good.id.in_([good[0] for good in most_common_goods])).all()

    return [
        {
            "id": good.id,
            "name": good.name,
            "price": good.price_per_item,
            "category": good.category,
            "description": good.description
        }
        for good in recommended_goods
    ]

@app.route('/sales/recommendations', methods=['GET'])
@jwt_required()
def get_recommendations():
    # Get the current user's ID from JWT
    current_user_id = get_jwt_identity()
    
    # Get recommendations for the user
    recommendations = get_recommendations_for_customer(current_user_id)
    
    # Return the list of recommended goods
    return jsonify(recommendations), 200

def add_expiry_notification():
    # Get goods that are about to expire in the next 3 days
    soon_to_expire_goods = Good.query.filter(Good.expiry_date <= datetime.now() + timedelta(days=3)).all()

    # Add notifications for all customers who have these goods in their cart or wish list
    for good in soon_to_expire_goods:
        customers = Customer.query.join(Wishlist).filter(Wishlist.good_id == good.id).all()

        for customer in customers:
            # Create a notification
            notification = Notification(
                customer_id=customer.id,
                message=f"The item '{good.name}' in your wishlist will expire soon. Grab it before it's gone!",
                type='expiry_warning',
                good_id=good.id
            )
            db.session.add(notification)

    # Commit to save notifications to the database
    db.session.commit()
    
    
@app.route('/notifications', methods=['GET'])
@jwt_required()
def get_notifications():
    current_user_id = get_jwt_identity()

    # Fetch notifications for the current user
    notifications = Notification.query.filter_by(customer_id=current_user_id).order_by(Notification.created_at.desc()).all()

    # Mark unread notifications as read
    for notification in notifications:
        if notification.status == 'unread':
            notification.status = 'read'

    db.session.commit()

    # Return notifications as JSON
    return jsonify([
        {
            "message": notification.message,
            "type": notification.type,
            "created_at": notification.created_at,
            "status": notification.status,
            "good_id": notification.good_id
        } for notification in notifications
    ]), 200


if __name__ == '__main__':
    with app.app_context():
        db.create_all()  
    app.run(debug=True)
