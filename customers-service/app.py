import secrets
import re
from decimal import Decimal, InvalidOperation
from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity, get_jwt
)
from flask_sqlalchemy import SQLAlchemy
from marshmallow import Schema, fields, ValidationError, validates, validate
# from flask_talisman import Talisman  # Uncomment if used
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import sys
import os

# Add the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import config
from models import db, Customer  # Ensure 'Customer' model includes 'is_admin' field

app = Flask(__name__)

app.config['JWT_SECRET_KEY'] = config.JWT_SECRET_KEY
app.config['JWT_ALGORITHM'] = config.JWT_ALGORITHM
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URI', 'postgresql://postgres:Talineslim0303$@localhost/customers_service'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize Extensions
db.init_app(app)
jwt = JWTManager(app)
limiter = Limiter(key_func=get_remote_address)
limiter.init_app(app)


# Uncomment if enforcing HTTPS in production
# if os.environ.get('FLASK_ENV') == 'production':
#     Talisman(app, content_security_policy=None)

# Password Validation Function
def validate_password(password):
    if (len(password) < 8 or
        not re.search(r'[A-Z]', password) or
        not re.search(r'[a-z]', password) or
        not re.search(r'[0-9]', password) or
        not re.search(r'[\W_]', password)):
        raise ValidationError(
            "Password must be at least 8 characters long and include uppercase, lowercase, number, and special character."
        )

# Username Validation Function
def validate_username(username):
    if not re.match(r'^\w{4,20}$', username):
        raise ValidationError(
            "Username must be 4-20 characters long and contain only letters, numbers, and underscores."
        )

# Marshmallow Schemas
class CustomerSchema(Schema):
    full_name = fields.Str(
        required=True,
        validate=validate.Length(max=100)
    )
    username = fields.Str(
        required=True,
        validate=validate_username
    )
    password = fields.Str(
        required=True,
        load_only=True,
        validate=validate_password
    )
    age = fields.Int(
        required=True,
        validate=lambda x: 0 < x < 150
    )
    address = fields.Str(
        required=True,
        validate=validate.Length(max=200)
    )
    gender = fields.Str(
        required=True,
        validate=validate.OneOf(["Male", "Female", "Other"])
    )
    marital_status = fields.Str(
        required=True,
        validate=validate.OneOf(["Single", "Married", "Divorced", "Widowed"])
    )
    # We do not allow 'is_admin' to be set via registration
    # is_admin = fields.Boolean(dump_only=True)

class UpdateCustomerSchema(Schema):
    username = fields.Str(validate=validate.Length(min=4, max=20))  # Fixed username field to be included in updates
    full_name = fields.Str(validate=validate.Length(max=100))
    age = fields.Int(validate=lambda x: 0 < x < 150)
    address = fields.Str(validate=validate.Length(max=200))
    gender = fields.Str(validate=validate.OneOf(["Male", "Female", "Other"]))
    marital_status = fields.Str(validate=validate.OneOf(["Single", "Married", "Divorced", "Widowed"]))

class LoginSchema(Schema):
    username = fields.Str(required=True, validate=validate_username)
    password = fields.Str(required=True, load_only=True)

customer_schema = CustomerSchema()
update_customer_schema = UpdateCustomerSchema()
login_schema = LoginSchema()

# Register a customer
@app.route('/customers/register', methods=['POST'])
def register_customer():
    try:
        data = customer_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(err.messages), 400

    # Check if username is already taken
    if Customer.query.filter_by(username=data['username']).first():
        return jsonify({"error": "Username already taken"}), 400

    hashed_password = generate_password_hash(data['password'])
    new_customer = Customer(
        full_name=data['full_name'],
        username=data['username'],
        password_hash=hashed_password,
        age=data['age'],
        address=data['address'],
        gender=data['gender'],
        marital_status=data['marital_status'],
        is_admin=False  # Regular users cannot set 'is_admin' flag
    )
    db.session.add(new_customer)
    db.session.commit()

    access_token = create_access_token(identity=str(new_customer.id))

    return jsonify({"message": "Customer registered successfully!", "access_token": access_token}), 201


# Register an admin user
@app.route('/admin/register', methods=['POST'])
def register_admin():
    try:
        data = customer_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(err.messages), 400

    # Check if username is already taken
    if Customer.query.filter_by(username=data['username']).first():
        return jsonify({"error": "Username already taken"}), 400

    hashed_password = generate_password_hash(data['password'])
    new_admin = Customer(
        full_name=data['full_name'],
        username=data['username'],
        password_hash=hashed_password,
        age=data['age'],
        address=data['address'],
        gender=data['gender'],
        marital_status=data['marital_status'],
        is_admin=True  # Set as admin
    )
    db.session.add(new_admin)
    db.session.commit()

    access_token = create_access_token(identity=str(new_admin.id))

    return jsonify({"message": "Admin registered successfully!", "access_token": access_token}), 201

@app.route('/customers/login', methods=['POST'])
@limiter.limit("5 per minute")
def login_customer():
    try:
        data = login_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({"error": "Invalid username or password"}), 401

    customer = Customer.query.filter_by(username=data['username']).first()

    # Validate username and password
    if not customer or not check_password_hash(customer.password_hash, data['password']):
        return jsonify({"error": "Invalid credentials"}), 401

    # Generate a JWT token
    access_token = create_access_token(
        identity=str(customer.id),
        additional_claims={
            "username": customer.username,
            "is_admin": customer.is_admin
        }
    )
    return jsonify({"message": "Login successful!", "access_token": access_token}), 200

# Get the current logged-in customer
@app.route('/customers/me', methods=['GET'])
@jwt_required()
def get_current_user():
    current_user_id = get_jwt_identity()
    customer = Customer.query.get(current_user_id)
    if not customer:
        return jsonify({"error": "Customer not found"}), 404

    return jsonify({
        "id": customer.id,
        "username": customer.username,
        "full_name": customer.full_name,
        "age": customer.age,
        "address": customer.address,
        "gender": customer.gender,
        "marital_status": customer.marital_status,
        "wallet_balance": str(customer.wallet_balance)
    }), 200

# Get all customers (admin only)
@app.route('/customers', methods=['GET'])
@jwt_required()
def get_all_customers():
    claims = get_jwt()
    if not claims.get('is_admin', False):
        return jsonify({"error": "Unauthorized action"}), 403

    # Implement pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    customers_query = Customer.query

    # Apply pagination
    pagination = customers_query.paginate(page=page, per_page=per_page, error_out=False)
    customers = pagination.items

    # Serialize customer data
    customers_data = []
    for customer in customers:
        customers_data.append({
            "id": customer.id,
            "username": customer.username,
            "full_name": customer.full_name,
            "age": customer.age,
            "address": customer.address,
            "gender": customer.gender,
            "marital_status": customer.marital_status,
            "wallet_balance": str(customer.wallet_balance)
        })

    response = {
        "total_customers": pagination.total,
        "total_pages": pagination.pages,
        "current_page": pagination.page,
        "customers": customers_data
    }

    return jsonify(response), 200

# Get customer by username (admin only)
@app.route('/customers/username/<string:username>', methods=['GET'])
@jwt_required()
def get_customer_by_username(username):
    claims = get_jwt()
    if not claims.get('is_admin', False):
        return jsonify({"error": "Unauthorized action"}), 403

    customer = Customer.query.filter_by(username=username).first()
    if not customer:
        return jsonify({"error": "Customer not found"}), 404

    # Serialize customer data
    customer_data = {
        "id": customer.id,
        "username": customer.username,
        "full_name": customer.full_name,
        "age": customer.age,
        "address": customer.address,
        "gender": customer.gender,
        "marital_status": customer.marital_status,
        "wallet_balance": str(customer.wallet_balance)
    }

    return jsonify(customer_data), 200

# Update customer (admin or the user themselves)
@app.route('/customers/<int:customer_id>', methods=['PUT'])
@jwt_required()
def update_customer(customer_id):
    current_user_id = get_jwt_identity()
    claims = get_jwt()

    if not claims.get('is_admin', False) and int(current_user_id) != customer_id:
        return jsonify({"error": "Unauthorized action"}), 403

    customer = Customer.query.get(customer_id)
    if not customer:
        return jsonify({"error": "Customer not found"}), 404

    try:
        data = update_customer_schema.load(request.get_json(), partial=True)
    except ValidationError as err:
        return jsonify(err.messages), 400

    # Update allowed fields
    for key, value in data.items():
        setattr(customer, key, value)

    db.session.commit()
    return jsonify({"message": "Customer updated successfully"}), 200


# Delete customer (admin or the user themselves)
@app.route('/customers/<int:customer_id>', methods=['DELETE'])
@jwt_required()
def delete_customer(customer_id):
    current_user_id = get_jwt_identity()
    claims = get_jwt()

    # Ensure the logged-in user is deleting their own profile or is admin
    if not claims.get('is_admin', False) and int(current_user_id) != customer_id:
        return jsonify({"error": "Unauthorized action"}), 403

    customer = Customer.query.get(customer_id)
    if not customer:
        return jsonify({"error": "Customer not found"}), 404

    db.session.delete(customer)
    db.session.commit()
    return jsonify({"message": "Customer deleted successfully"}), 200

# Charge customer wallet (admin or the user themselves)
@app.route('/customers/<int:customer_id>/wallet/charge', methods=['POST'])
@jwt_required()
def charge_wallet(customer_id):
    current_user_id = get_jwt_identity()
    claims = get_jwt()

    # Ensure the logged-in user is updating their own wallet or is admin
    if not claims.get('is_admin', False) and int(current_user_id) != customer_id:
        return jsonify({"error": "Unauthorized action"}), 403

    customer = Customer.query.get(customer_id)
    if not customer:
        return jsonify({"error": "Customer not found"}), 404

    try:
        amount = request.json.get('amount', '0')
        amount = Decimal(amount)
        if amount <= 0:
            raise ValueError
    except (InvalidOperation, ValueError):
        return jsonify({"error": "Invalid amount"}), 400

    # Convert wallet_balance to Decimal before performing the addition
    customer.wallet_balance = Decimal(str(customer.wallet_balance)) + amount
    db.session.commit()
    return jsonify({"message": f"${amount} added to wallet"}), 200

# Deduct money from customer wallet (admin or the user themselves)
@app.route('/customers/<int:customer_id>/wallet/deduct', methods=['POST'])
@jwt_required()
def deduct_wallet(customer_id):
    current_user_id = get_jwt_identity()
    claims = get_jwt()

    # Ensure the logged-in user is updating their own wallet or is admin
    if not claims.get('is_admin', False) and int(current_user_id) != customer_id:
        return jsonify({"error": "Unauthorized action"}), 403

    customer = Customer.query.get(customer_id)
    if not customer:
        return jsonify({"error": "Customer not found"}), 404

    try:
        amount = request.json.get('amount', '0')
        amount = Decimal(amount)
        if amount <= 0:
            raise ValueError
    except (InvalidOperation, ValueError):
        return jsonify({"error": "Invalid amount"}), 400

    # Convert wallet_balance to Decimal before performing the subtraction
    wallet_balance_decimal = Decimal(str(customer.wallet_balance))
    if wallet_balance_decimal < amount:
        return jsonify({"error": "Insufficient funds"}), 400

    customer.wallet_balance = wallet_balance_decimal - amount
    db.session.commit()
    return jsonify({"message": f"${amount} deducted from wallet"}), 200


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=False, port=5001)  # Set debug to False and change the port to 5001 (or any other port you prefer)