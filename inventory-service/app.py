from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, get_jwt
from models import db, Good, Inventory
import bleach
import sys
import os

# Add parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import config  # Import config after adding parent directory

app = Flask(__name__)

# Configurations
app.config['JWT_SECRET_KEY'] = config.JWT_SECRET_KEY
app.config['JWT_ALGORITHM'] = config.JWT_ALGORITHM
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URI', 'postgresql://postgres:Talineslim0303$@localhost/inventory_service'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
jwt = JWTManager(app)


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

# Add a new good and its inventory (Admin only)
@app.route('/goods', methods=['POST'])
@jwt_required()
def add_good():
    claims = get_jwt()
    if not claims.get('is_admin', False):
        return jsonify({"error": "Unauthorized action"}), 403

    data = request.get_json()

    # Sanitize input
    data = sanitize_input(data)

    # Create a new good
    new_good = Good(
        name=data['name'],
        category=data['category'],
        price_per_item=data['price_per_item'],
        description=data.get('description', '')
    )
    # Create inventory for the good
    new_inventory = Inventory(stock_count=data['stock_count'], good=new_good)
    db.session.add(new_good)
    db.session.add(new_inventory)
    db.session.commit()
    return jsonify({
        "message": "Good and inventory added successfully!",
        "good_id": new_good.id,
        "stock_count": new_inventory.stock_count
    }), 201

# Deduct stock from inventory (Admin only)
@app.route('/goods/<int:good_id>/inventory/deduct', methods=['POST'])
@jwt_required()
def deduct_stock(good_id):
    claims = get_jwt()
    if not claims.get('is_admin', False):
        return jsonify({"error": "Unauthorized action"}), 403

    good = Good.query.get(good_id)
    if not good or not good.inventory:
        return jsonify({"error": "Good or inventory not found"}), 404

    data = request.get_json()

    # Sanitize input
    data = sanitize_input(data)

    quantity_to_deduct = data.get('quantity', 1)

    if good.inventory.stock_count < quantity_to_deduct:
        return jsonify({"error": "Insufficient stock"}), 400

    good.inventory.stock_count -= quantity_to_deduct
    db.session.commit()
    return jsonify({
        "message": f"{quantity_to_deduct} items deducted from stock",
        "remaining_stock": good.inventory.stock_count
    }), 200

# Update fields of a good (Admin only)
@app.route('/goods/<int:good_id>', methods=['PUT'])
@jwt_required()
def update_good(good_id):
    claims = get_jwt()
    if not claims.get('is_admin', False):
        return jsonify({"error": "Unauthorized action"}), 403

    good = Good.query.get(good_id)
    if not good:
        return jsonify({"error": "Good not found"}), 404

    data = request.get_json()

    # Sanitize input
    data = sanitize_input(data)

    # Update fields in the Good model
    for key, value in data.items():
        if hasattr(good, key):
            setattr(good, key, value)

    # Update inventory stock count if provided
    if 'stock_count' in data:
        if good.inventory:
            good.inventory.stock_count = data['stock_count']
        else:
            # Create inventory if it doesn't exist
            new_inventory = Inventory(stock_count=data['stock_count'], good=good)
            db.session.add(new_inventory)

    db.session.commit()
    return jsonify({
        "message": "Good and inventory updated successfully",
        "updated_good": {
            "id": good.id,
            "name": good.name,
            "category": good.category,
            "price_per_item": good.price_per_item,
            "description": good.description,
            "stock_count": good.inventory.stock_count if good.inventory else 0
        }
    }), 200

# Get all goods with inventory details
@app.route('/goods', methods=['GET'])
@jwt_required(optional=True)
def get_all_goods():
    claims = get_jwt()
    is_admin = claims.get('is_admin', False) if claims else False

    goods = Good.query.all()
    return jsonify([{
        "id": g.id,
        "name": g.name,
        "category": g.category,
        "price_per_item": g.price_per_item,
        "description": g.description,
        "stock_count": g.inventory.stock_count if is_admin and g.inventory else None
    } for g in goods]), 200

# Get a specific good with inventory details
@app.route('/goods/<int:good_id>', methods=['GET'])
@jwt_required(optional=True)
def get_good(good_id):
    claims = get_jwt()
    is_admin = claims.get('is_admin', False) if claims else False

    good = Good.query.get(good_id)
    if not good:
        return jsonify({"error": "Good not found"}), 404
    return jsonify({
        "id": good.id,
        "name": good.name,
        "category": good.category,
        "price_per_item": good.price_per_item,
        "description": good.description,
        "stock_count": good.inventory.stock_count if is_admin and good.inventory else None
    }), 200

# Delete a Good (Admin only)
@app.route('/goods/<int:good_id>', methods=['DELETE'])
@jwt_required()
def delete_good(good_id):
    claims = get_jwt()
    if not claims.get('is_admin', False):
        return jsonify({"error": "Unauthorized action"}), 403

    # Retrieve the good from the database
    good = Good.query.get(good_id)

    # Check if the good exists
    if not good:
        return jsonify({"error": "Good not found"}), 404

    # Delete the good and its associated inventory (if exists)
    if good.inventory:
        db.session.delete(good.inventory)

    db.session.delete(good)
    db.session.commit()

    return jsonify({"message": "Good deleted successfully"}), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Ensure tables are created
    app.run(debug=True)
