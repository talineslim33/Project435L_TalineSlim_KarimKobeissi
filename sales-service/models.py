from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Good Model (imported from previous services)
class Good(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    price_per_item = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(255))
    inventory = db.relationship("Inventory", back_populates="good", uselist=False)

# Inventory Model (imported from previous services)
class Inventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    stock_count = db.Column(db.Integer, nullable=False, default=0)
    good_id = db.Column(db.Integer, db.ForeignKey('good.id'), nullable=False)
    good = db.relationship("Good", back_populates="inventory")

# Customer Model (imported from previous services)
class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    wallet_balance = db.Column(db.Float, default=0.0)

# Sales Model for Historical Purchases
class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    good_id = db.Column(db.Integer, db.ForeignKey('good.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    total_price = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, server_default=db.func.now())

    # Relationships
    customer = db.relationship("Customer")
    good = db.relationship("Good")
