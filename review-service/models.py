from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Review Model
class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, nullable=False) 
    product_id = db.Column(db.Integer, nullable=False)  
    rating = db.Column(db.Float, nullable=False)
    comment = db.Column(db.String(500))
    timestamp = db.Column(db.DateTime, server_default=db.func.now())
    moderated = db.Column(db.Boolean, default=False)  # Tracks moderation status
    flagged = db.Column(db.Boolean, default=False)  # Tracks flagged status for inappropriate content
 
