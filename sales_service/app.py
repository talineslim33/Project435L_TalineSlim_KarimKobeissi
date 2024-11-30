"""
Sales and Wishlist Management Service

This Flask application provides a RESTful API for managing sales, wishlists, notifications,
and recommendations for an e-commerce platform. It supports user interactions such as
purchasing goods, managing wishlists, receiving notifications, and viewing product recommendations.

Features:
- Display available goods with stock information (Admin view).
- Retrieve detailed information about goods.
- Purchase goods with wallet balance validation.
- Manage wishlists (add, remove, view, and check items).
- Get personalized product recommendations.
- Notify users of goods about to expire in their wishlist.
- View purchase history (customer-specific and admin-only).
- Receive notifications for wishlist items.

Modules:
- Flask: Core framework for the application.
- Flask-JWT-Extended: For token-based authentication.
- SQLAlchemy: ORM for database interactions.
- Marshmallow: Input validation and serialization.
- Bleach: Input sanitization to prevent XSS attacks.

"""
from functools import wraps
from line_profiler import LineProfiler
from memory_profiler import profile
profiler = LineProfiler()

def profile_line(func):
    # Check if the function has been wrapped and access the original if needed
    unwrapped_func = getattr(func, "__wrapped__", func)
    profiler.add_function(unwrapped_func)  # Add the unwrapped function to the profiler

    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        with open("line_profiler_results.txt", "w") as f:
            profiler.print_stats(stream=f)  # Write profiling stats to a file
        return result

    return wrapper
from flask import Flask, request, jsonify
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity, get_jwt
)
from marshmallow import Schema, fields, ValidationError, validate
from models import db, Good, Inventory, Customer, Sale, Wishlist, Notification
import bleach
import sys
import os
from collections import Counter
from datetime import datetime, timedelta

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

class SaleSchema(Schema):
    """
    Schema for validating sales data.

    Attributes:
        username (fields.Str): Customer's username.
        good_name (fields.Str): Name of the good being purchased.
        quantity (fields.Int): Quantity of the good being purchased.
    """
    username = fields.Str(required=True, validate=validate.Length(min=4, max=20))
    good_name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    quantity = fields.Int(required=False, validate=validate.Range(min=1))

sale_schema = SaleSchema()

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

# Display available goods
@app.route('/sales/goods', methods=['GET'])
@jwt_required(optional=True)
@profile_line
@profile
def display_available_goods():
    """
    Displays all goods with stock information.

    Returns:
        Response: JSON response with available goods. Admins see stock and price details.
    """
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
@profile_line
@profile
def get_good_details(good_id):
    """
    Retrieves detailed information about a specific good.

    Args:
        good_id (int): ID of the good to retrieve.

    Returns:
        Response: JSON response with good details. Admins see full details, while users see limited details.
    """
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
@profile_line
@profile
def make_sale():
    """
    Processes a sale for a customer.

    Args:
        None (data is provided in the request body).

    Returns:
        Response: JSON response with sale confirmation, updated wallet balance, and remaining stock.
    """
    current_user_id = get_jwt_identity()

    try:
        data = sale_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(err.messages), 400

    data = sanitize_input(data)

    customer = Customer.query.get(current_user_id)
    good = Good.query.filter_by(name=data['good_name']).first()

    if not customer:
        return jsonify({"error": "Customer not found"}), 404
    if not good or not good.inventory or good.inventory.stock_count < data['quantity']:
        return jsonify({"error": "Good not available or insufficient stock"}), 400

    total_price = data['quantity'] * good.price_per_item
    if customer.wallet_balance < total_price:
        return jsonify({"error": "Insufficient funds"}), 400

    customer.wallet_balance -= total_price
    good.inventory.stock_count -= data['quantity']

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
@profile_line
@profile
def get_purchase_history():
    """
    Retrieves purchase history for the authenticated customer.

    Returns:
        Response: JSON response with a list of purchase history.
    """
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
@profile_line
@profile
def get_all_purchase_histories():
    """
    Retrieves all purchase histories.

    Admin-only endpoint.

    Returns:
        Response: JSON response with a list of all sales, including customer, product, and purchase details.
    """
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

# Add an item to the wishlist
@app.route('/wishlist', methods=['POST'])
@jwt_required()
@profile_line
@profile
def add_to_wishlist():
    """
    Adds an item to the customer's wishlist.

    Args:
        None (data is provided in the request body).

    Returns:
        Response: JSON response confirming addition or an error message if the item already exists.
    """
    current_user_id = get_jwt_identity()
    data = request.get_json()

    good_id = data.get('good_id')

    good = Good.query.get(good_id)
    if not good:
        return jsonify({"error": "Good not found"}), 404

    if Wishlist.query.filter_by(customer_id=current_user_id, good_id=good_id).first():
        return jsonify({"message": "Item already in wishlist"}), 400

    new_wishlist_item = Wishlist(customer_id=current_user_id, good_id=good_id)
    db.session.add(new_wishlist_item)
    db.session.commit()
    return jsonify({"message": "Item added to wishlist successfully"}), 201

# Remove an item from the wishlist
@app.route('/wishlist/<int:wishlist_id>', methods=['DELETE'])
@jwt_required()
@profile_line
@profile
def remove_from_wishlist(wishlist_id):
    """
    Removes an item from the customer's wishlist.

    Args:
        wishlist_id (int): ID of the wishlist item to remove.

    Returns:
        Response: JSON response confirming removal or an error message if the item is not found.
    """
    current_user_id = get_jwt_identity()

    wishlist_item = Wishlist.query.filter_by(id=wishlist_id, customer_id=current_user_id).first()

    if not wishlist_item:
        return jsonify({"error": "Item not found in wishlist"}), 404

    db.session.delete(wishlist_item)
    db.session.commit()
    return jsonify({"message": "Item removed from wishlist"}), 200

# Get all wishlist items
@app.route('/wishlist', methods=['GET'])
@jwt_required()
@profile_line
@profile
def get_wishlist():
    """
    Retrieves all items in the customer's wishlist.

    Returns:
        Response: JSON response with a list of wishlist items, including product details.
    """
    current_user_id = get_jwt_identity()

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

# Check if an item is in the wishlist
@app.route('/wishlist/<int:good_id>', methods=['GET'])
@jwt_required()
@profile_line
@profile
def is_in_wishlist(good_id):
    """
    Checks if a specific good is in the customer's wishlist.

    Args:
        good_id (int): ID of the good to check.

    Returns:
        Response: JSON response with `in_wishlist: True` if the item exists,
        or `in_wishlist: False` if it does not.
    """
    current_user_id = get_jwt_identity()

    wishlist_item = Wishlist.query.filter_by(customer_id=current_user_id, good_id=good_id).first()
    if wishlist_item:
        return jsonify({"in_wishlist": True}), 200
    else:
        return jsonify({"in_wishlist": False}), 404

# Get product recommendations
@app.route('/sales/recommendations', methods=['GET'])
@jwt_required()
@profile_line
@profile
def get_recommendations():
    """
    Provides personalized product recommendations for the customer.

    Returns:
        Response: JSON response with a list of recommended goods based on purchase patterns.
    """
    current_user_id = get_jwt_identity()
    recommendations = get_recommendations_for_customer(current_user_id)

    return jsonify(recommendations), 200

def get_recommendations_for_customer(customer_id):
    """
    Generates product recommendations for a given customer.

    Args:
        customer_id (int): ID of the customer to generate recommendations for.

    Returns:
        list: A list of recommended goods with their details.
    """
    customer_purchases = Sale.query.filter_by(customer_id=customer_id).all()
    purchased_goods_ids = {sale.good_id for sale in customer_purchases}

    similar_customers = Sale.query.filter(Sale.good_id.in_(purchased_goods_ids)).all()
    similar_customer_ids = {sale.customer_id for sale in similar_customers if sale.customer_id != customer_id}

    recommendations = []
    for customer in similar_customer_ids:
        customer_sales = Sale.query.filter_by(customer_id=customer).all()
        recommendations.extend([sale.good_id for sale in customer_sales if sale.good_id not in purchased_goods_ids])

    recommended_good_ids = [good_id for good_id in recommendations]
    most_common_goods = Counter(recommended_good_ids).most_common(5)

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

# Notifications
@app.route('/notifications', methods=['GET'])
@jwt_required()
@profile_line
@profile
def get_notifications():
    """
    Retrieves all notifications for the authenticated customer.

    Returns:
        Response: JSON response with a list of notifications, including type, message, and timestamps.
    """
    current_user_id = get_jwt_identity()

    notifications = Notification.query.filter_by(customer_id=current_user_id).order_by(Notification.created_at.desc()).all()

    for notification in notifications:
        if notification.status == 'unread':
            notification.status = 'read'

    db.session.commit()

    return jsonify([
        {
            "message": notification.message,
            "type": notification.type,
            "created_at": notification.created_at,
            "status": notification.status,
            "good_id": notification.good_id
        } for notification in notifications
    ]), 200

# Add expiry notifications
def add_expiry_notification():
    """
    Creates notifications for goods about to expire in the customer's wishlist.

    This function is executed periodically to notify customers about expiring goods.
    """
    soon_to_expire_goods = Good.query.filter(Good.expiry_date <= datetime.now() + timedelta(days=3)).all()

    for good in soon_to_expire_goods:
        customers = Customer.query.join(Wishlist).filter(Wishlist.good_id == good.id).all()

        for customer in customers:
            notification = Notification(
                customer_id=customer.id,
                message=f"The item '{good.name}' in your wishlist will expire soon. Grab it before it's gone!",
                type='expiry_warning',
                good_id=good.id
            )
            db.session.add(notification)

    db.session.commit()

if __name__ == '__main__':
    """
    Entry point for running the Flask application.

    Ensures the database tables are created before starting the server.
    """
    with app.app_context():
        db.create_all()
    app.run(debug=True)
