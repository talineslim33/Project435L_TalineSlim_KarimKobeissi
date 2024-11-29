from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Good Model
class Good(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    price_per_item = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(255))

    # One-to-One relationship with Inventory
    inventory = db.relationship("Inventory", back_populates="good", uselist=False)

# Inventory Model
class Inventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    stock_count = db.Column(db.Integer, nullable=False, default=0)

    # Foreign key to link with Good
    good_id = db.Column(db.Integer, db.ForeignKey('good.id', ondelete='CASCADE'), nullable=False)
    good = db.relationship("Good", back_populates="inventory")
 
