from flask import Flask, request, jsonify
from models import db, Good, Inventory

app = Flask(__name__)

# Configurations
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Talineslim0303$@localhost/inventory_service'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Add a new good and its inventory
@app.route('/goods', methods=['POST'])
def add_good():
    data = request.get_json()
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
    return jsonify({"message": "Good and inventory added successfully!", "good_id": new_good.id}), 201

# Deduct stock from inventory
@app.route('/goods/<int:good_id>/inventory/deduct', methods=['POST'])
def deduct_stock(good_id):
    good = Good.query.get(good_id)
    if not good or not good.inventory:
        return jsonify({"error": "Good or inventory not found"}), 404

    data = request.get_json()
    quantity_to_deduct = data.get('quantity', 1)

    if good.inventory.stock_count < quantity_to_deduct:
        return jsonify({"error": "Insufficient stock"}), 400

    good.inventory.stock_count -= quantity_to_deduct
    db.session.commit()
    return jsonify({
        "message": f"{quantity_to_deduct} items deducted from stock",
        "remaining_stock": good.inventory.stock_count
    }), 200

# Update fields of a good
@app.route('/goods/<int:good_id>', methods=['PUT'])
def update_good(good_id):
    good = Good.query.get(good_id)
    if not good:
        return jsonify({"error": "Good not found"}), 404

    data = request.get_json()

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
def get_all_goods():
    goods = Good.query.all()
    return jsonify([
        {
            "id": g.id,
            "name": g.name,
            "category": g.category,
            "price_per_item": g.price_per_item,
            "description": g.description,
            "stock_count": g.inventory.stock_count if g.inventory else 0
        }
        for g in goods
    ]), 200

# Get a specific good with inventory details
@app.route('/goods/<int:good_id>', methods=['GET'])
def get_good(good_id):
    good = Good.query.get(good_id)
    if not good:
        return jsonify({"error": "Good not found"}), 404
    return jsonify({
        "id": good.id,
        "name": good.name,
        "category": good.category,
        "price_per_item": good.price_per_item,
        "description": good.description,
        "stock_count": good.inventory.stock_count if good.inventory else 0
    }), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Ensure tables are created
    app.run(debug=True)
 
