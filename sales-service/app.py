from flask import Flask, request, jsonify
from models import db, Good, Inventory, Customer, Sale

app = Flask(__name__)

# Configurations
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Talineslim0303$@localhost/sales_service'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Display available goods
@app.route('/sales/goods', methods=['GET'])
def display_available_goods():
    goods = Good.query.join(Inventory).filter(Inventory.stock_count > 0).all()
    return jsonify([
        {"name": g.name, "price": g.price_per_item}
        for g in goods
    ]), 200

# Get good details
@app.route('/sales/goods/<int:good_id>', methods=['GET'])
def get_good_details(good_id):
    good = Good.query.get(good_id)
    if not good:
        return jsonify({"error": "Good not found"}), 404
    return jsonify({
        "name": good.name,
        "category": good.category,
        "price_per_item": good.price_per_item,
        "description": good.description,
        "stock_count": good.inventory.stock_count if good.inventory else 0
    }), 200

# Make a sale
@app.route('/sales', methods=['POST'])
def make_sale():
    data = request.get_json()
    username = data['username']
    good_name = data['good_name']
    quantity = data.get('quantity', 1)

    # Get customer and good details
    customer = Customer.query.filter_by(username=username).first()
    good = Good.query.filter_by(name=good_name).first()

    if not customer:
        return jsonify({"error": "Customer not found"}), 404
    if not good or not good.inventory or good.inventory.stock_count < quantity:
        return jsonify({"error": "Good not available or insufficient stock"}), 400

    total_price = quantity * good.price_per_item
    if customer.wallet_balance < total_price:
        return jsonify({"error": "Insufficient funds"}), 400

    # Process the sale
    customer.wallet_balance -= total_price
    good.inventory.stock_count -= quantity

    # Record the sale
    sale = Sale(
        customer_id=customer.id,
        good_id=good.id,
        quantity=quantity,
        total_price=total_price
    )
    db.session.add(sale)
    db.session.commit()

    return jsonify({
        "message": "Sale successful",
        "customer_balance": customer.wallet_balance,
        "remaining_stock": good.inventory.stock_count
    }), 200

# Get customer's purchase history
@app.route('/sales/history/<string:username>', methods=['GET'])
def get_purchase_history(username):
    customer = Customer.query.filter_by(username=username).first()
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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Ensure tables are created
    app.run(debug=True)
 
