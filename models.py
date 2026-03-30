from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id                = db.Column(db.Integer, primary_key=True)
    email             = db.Column(db.String(120), unique=True, nullable=False)
    password_hash     = db.Column(db.String(256), nullable=False)
    organization_name = db.Column(db.String(150), nullable=False)
    role              = db.Column(db.String(20),  nullable=False) # 'donor' or 'charity'
    phone             = db.Column(db.String(30),  nullable=True)
    address           = db.Column(db.String(255), nullable=True)
    license_num       = db.Column(db.String(100), nullable=True)
    reg_num           = db.Column(db.String(100), nullable=True)
    created_at        = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    donations           = db.relationship("Donation", backref="donor", lazy=True, foreign_keys="Donation.donor_id")
    charity_requests    = db.relationship("DonationRequest", backref="charity", lazy=True, foreign_keys="DonationRequest.charity_id")
    broadcasts          = db.relationship("CharityBroadcast", backref="charity_user", lazy=True, foreign_keys="CharityBroadcast.charity_id")
    broadcast_responses = db.relationship("BroadcastResponse", backref="restaurant_user", lazy=True, foreign_keys="BroadcastResponse.donor_id")


class Donation(db.Model):
    __tablename__ = "donations"

    id              = db.Column(db.Integer, primary_key=True)
    donor_id        = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    food_name       = db.Column(db.String(150), nullable=False, default="Surplus Food")
    food_category   = db.Column(db.String(50),  nullable=False)
    quantity        = db.Column(db.Integer,     nullable=False)
    unit            = db.Column(db.String(20),  nullable=False, default="items")
    pickup_deadline = db.Column(db.String(20),  nullable=False)
    notes           = db.Column(db.Text,        nullable=True)
    status          = db.Column(db.String(20),  default="active") # active | pending | completed
    created_at      = db.Column(db.DateTime,    default=datetime.utcnow)

    requests = db.relationship("DonationRequest", backref="donation", lazy=True, cascade="all, delete-orphan")

    @property
    def category_label(self):
        mapping = {"perishable": "Perishable", "produce": "Produce", "non-perishable": "Non-Perishable"}
        return mapping.get(self.food_category, self.food_category.title())

    @property
    def time_ago(self):
        delta = datetime.utcnow() - self.created_at
        if delta.days > 0: return f"{delta.days}d ago"
        mins = delta.seconds // 60
        if mins >= 60: return f"{mins // 60}h ago"
        return f"{max(mins, 1)}m ago"


class DonationRequest(db.Model):
    __tablename__ = "donation_requests"

    id          = db.Column(db.Integer, primary_key=True)
    donation_id = db.Column(db.Integer, db.ForeignKey("donations.id"), nullable=False)
    charity_id  = db.Column(db.Integer, db.ForeignKey("users.id"),     nullable=False)
    message     = db.Column(db.Text,    nullable=True)
    status      = db.Column(db.String(20), default="pending") # pending | accepted | declined
    created_at  = db.Column(db.DateTime,   default=datetime.utcnow)

    @property
    def time_ago(self):
        delta = datetime.utcnow() - self.created_at
        if delta.days > 0: return f"{delta.days}d ago"
        mins = delta.seconds // 60
        if mins >= 60: return f"{mins // 60}h ago"
        return f"{max(mins, 1)}m ago"


class CharityBroadcast(db.Model):
    """A food need posted by a charity — visible to all restaurants."""
    __tablename__ = "charity_broadcasts"

    id            = db.Column(db.Integer, primary_key=True)
    charity_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    food_name     = db.Column(db.String(150), nullable=False)
    food_category = db.Column(db.String(50),  nullable=False)
    quantity      = db.Column(db.Integer,     nullable=False)
    unit          = db.Column(db.String(20),  nullable=False, default="items")
    needed_by     = db.Column(db.String(20),  nullable=False)
    notes         = db.Column(db.Text,        nullable=True)
    status        = db.Column(db.String(20),  default="open")   # open | fulfilled | closed
    created_at    = db.Column(db.DateTime,    default=datetime.utcnow)

    responses = db.relationship("BroadcastResponse", backref="broadcast", lazy=True, cascade="all, delete-orphan")

    @property
    def category_label(self):
        mapping = {"perishable": "Perishable", "produce": "Produce", "non-perishable": "Non-Perishable"}
        return mapping.get(self.food_category, self.food_category.title())

    @property
    def time_ago(self):
        delta = datetime.utcnow() - self.created_at
        if delta.days > 0: return f"{delta.days}d ago"
        mins = delta.seconds // 60
        if mins >= 60: return f"{mins // 60}h ago"
        return f"{max(mins, 1)}m ago"


class BroadcastResponse(db.Model):
    """A restaurant's offer to fulfill a CharityBroadcast."""
    __tablename__ = "broadcast_responses"

    id           = db.Column(db.Integer, primary_key=True)
    broadcast_id = db.Column(db.Integer, db.ForeignKey("charity_broadcasts.id"), nullable=False)
    donor_id     = db.Column(db.Integer, db.ForeignKey("users.id"),              nullable=False)
    message      = db.Column(db.Text,    nullable=True)
    status       = db.Column(db.String(20), default="pending")  # pending | accepted | declined
    created_at   = db.Column(db.DateTime,   default=datetime.utcnow)

    @property
    def time_ago(self):
        delta = datetime.utcnow() - self.created_at
        if delta.days > 0: return f"{delta.days}d ago"
        mins = delta.seconds // 60
        if mins >= 60: return f"{mins // 60}h ago"
        return f"{max(mins, 1)}m ago"
