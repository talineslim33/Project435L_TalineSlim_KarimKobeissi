from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, Customer

app = Flask(__name__)

# Configurations
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Talineslim0303$@localhost/customers_service'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Register a customer
@app.route('/customers', methods=['POST'])
def register_customer():
    data = request.get_json()
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
        marital_status=data['marital_status']
    )
    db.session.add(new_customer)
    db.session.commit()
    return jsonify({"message": "Customer registered successfully!"}), 201


# Update customer
@app.route('/update-customer/<int:customer_id>', methods=['PUT'])
def update_customer(customer_id):
    customer = Customer.query.get(customer_id)
    if not customer:
        return jsonify({"error": "Customer not found"}), 404

    data = request.get_json()

    # Check if the username is being updated
    if 'username' in data and data['username'] != customer.username:
        # Check if the new username is already taken
        if Customer.query.filter_by(username=data['username']).first():
            return jsonify({"error": "Username already taken"}), 400

    # Update fields
    for key, value in data.items():
        if hasattr(customer, key):
            setattr(customer, key, value)

    db.session.commit()
    return jsonify({"message": "Customer updated successfully"}), 200

# Delete customer
@app.route('/customers/<int:customer_id>', methods=['DELETE'])
def delete_customer(customer_id):
    customer = Customer.query.get(customer_id)
    if not customer:
        return jsonify({"error": "Customer not found"}), 404
    db.session.delete(customer)
    db.session.commit()
    return jsonify({"message": "Customer deleted successfully"}), 200


# Get all customers
@app.route('/customers', methods=['GET'])
def get_all_customers():
    customers = Customer.query.all()
    return jsonify([
        {
            "id": c.id,
            "full_name": c.full_name,
            "username": c.username,
            "age": c.age,
            "address": c.address,
            "gender": c.gender,
            "marital_status": c.marital_status,
            "wallet_balance": c.wallet_balance
        }
        for c in customers
    ]), 200

# Get customer by username
@app.route('/customers/<string:username>', methods=['GET'])
def get_customer_by_username(username):
    customer = Customer.query.filter_by(username=username).first()
    if not customer:
        return jsonify({"error": "Customer not found"}), 404
    return jsonify({
        "id": customer.id,
        "full_name": customer.full_name,
        "username": customer.username,
        "age": customer.age,
        "address": customer.address,
        "gender": customer.gender,
        "marital_status": customer.marital_status,
        "wallet_balance": customer.wallet_balance
    }), 200

# Charge customer
@app.route('/customers/<int:customer_id>/wallet/charge', methods=['POST'])
def charge_wallet(customer_id):
    customer = Customer.query.get(customer_id)
    if not customer:
        return jsonify({"error": "Customer not found"}), 404

    amount = request.json.get('amount', 0)
    customer.wallet_balance += amount
    db.session.commit()
    return jsonify({"message": f"${amount} added to wallet"}), 200

# Deduct money from customer's wallet
@app.route('/customers/<int:customer_id>/wallet/deduct', methods=['POST'])
def deduct_wallet(customer_id):
    customer = Customer.query.get(customer_id)
    if not customer:
        return jsonify({"error": "Customer not found"}), 404

    amount = request.json.get('amount', 0)
    if customer.wallet_balance < amount:
        return jsonify({"error": "Insufficient funds"}), 400

    customer.wallet_balance -= amount
    db.session.commit()
    return jsonify({"message": f"${amount} deducted from wallet"}), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Ensure tables are created
    app.run(debug=True)
