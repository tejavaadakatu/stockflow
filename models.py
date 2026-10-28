from datetime import datetime, timezone

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


def utc_now():
    return datetime.now(timezone.utc)


class Organization(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    # Settings feature (FR-7): default low stock threshold for this organization
    default_low_stock_threshold = db.Column(db.Integer, nullable=False, default=5)
    created_at = db.Column(db.DateTime, default=utc_now)

    users = db.relationship("User", backref="organization", lazy=True)
    products = db.relationship("Product", backref="organization", lazy=True)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    organization_id = db.Column(
        db.Integer, db.ForeignKey("organization.id"), nullable=False
    )
    created_at = db.Column(db.DateTime, default=utc_now)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey("organization.id"), nullable=False
    )
    name = db.Column(db.String(120), nullable=False)
    sku = db.Column(db.String(60), nullable=False)
    description = db.Column(db.Text)
    quantity_on_hand = db.Column(db.Integer, nullable=False, default=0)
    cost_price = db.Column(db.Float)
    selling_price = db.Column(db.Float)
    low_stock_threshold = db.Column(db.Integer)  # empty = use organization default
    last_updated_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    # SKU must be unique inside one organization (not across all organizations)
    __table_args__ = (
        db.UniqueConstraint("organization_id", "sku", name="uq_org_sku"),
    )

    @property
    def effective_threshold(self):
        if self.low_stock_threshold is not None:
            return self.low_stock_threshold
        return self.organization.default_low_stock_threshold

    @property
    def is_low_stock(self):
        return self.quantity_on_hand <= self.effective_threshold