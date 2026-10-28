import os
import re
import re

from flask import Flask, flash, redirect, render_template, request, url_for
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from models import Organization, Product, User, db

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-me")
database_url = os.environ.get("DATABASE_URL", "sqlite:///stockflow.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to continue."
login_manager.login_message_category = "warning"

with app.app_context():
    db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@app.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        org_name = request.form.get("org_name", "").strip()

        error = None
        if not EMAIL_PATTERN.match(email):
            error = "Please enter a valid email address."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        elif password != confirm_password:
            error = "Passwords do not match."
        elif not org_name:
            error = "Organization name is required."
        elif User.query.filter_by(email=email).first():
            error = "An account with this email already exists."

        if error:
            flash(error, "danger")
            return render_template("signup.html", email=email, org_name=org_name)

        # Create the organization first, then the user linked to it
        org = Organization(name=org_name)
        db.session.add(org)
        db.session.flush()  # gives org.id without committing yet

        user = User(email=email, organization_id=org.id)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash("Account created. Welcome to StockFlow!", "success")
        return redirect(url_for("dashboard"))

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "danger")
        return render_template("login.html", email=email)

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    org_id = current_user.organization_id

    total_products = Product.query.filter_by(organization_id=org_id).count()
    total_quantity = (
        db.session.query(db.func.coalesce(db.func.sum(Product.quantity_on_hand), 0))
        .filter(Product.organization_id == org_id)
        .scalar()
    )

    all_products = (
        Product.query.filter_by(organization_id=org_id)
        .order_by(Product.quantity_on_hand)
        .all()
    )
    low_stock_items = [p for p in all_products if p.is_low_stock]

    return render_template(
        "dashboard.html",
        total_products=total_products,
        total_quantity=total_quantity,
        low_stock_items=low_stock_items,
        default_threshold=current_user.organization.default_low_stock_threshold,
    )
# ---------------------- Product helpers ----------------------

def get_product_or_404(product_id):
    # Only returns the product if it belongs to the logged-in user's organization
    return Product.query.filter_by(
        id=product_id, organization_id=current_user.organization_id
    ).first_or_404()


def sku_exists(sku, exclude_id=None):
    query = Product.query.filter_by(
        organization_id=current_user.organization_id, sku=sku
    )
    if exclude_id is not None:
        query = query.filter(Product.id != exclude_id)
    return query.first() is not None


def parse_product_form(form):
    errors = []
    name = form.get("name", "").strip()
    sku = form.get("sku", "").strip()
    description = form.get("description", "").strip() or None

    if not name:
        errors.append("Name is required.")
    if not sku:
        errors.append("SKU is required.")

    def to_int(field, label, required=False):
        value = form.get(field, "").strip()
        if value == "":
            if required:
                errors.append(f"{label} is required.")
            return None
        try:
            number = int(value)
        except ValueError:
            errors.append(f"{label} must be a whole number.")
            return None
        if number < 0:
            errors.append(f"{label} cannot be negative.")
            return None
        return number

    def to_float(field, label):
        value = form.get(field, "").strip()
        if value == "":
            return None
        try:
            number = float(value)
        except ValueError:
            errors.append(f"{label} must be a number.")
            return None
        if number < 0:
            errors.append(f"{label} cannot be negative.")
            return None
        return number

    data = {
        "name": name,
        "sku": sku,
        "description": description,
        "quantity_on_hand": to_int("quantity_on_hand", "Quantity", required=True),
        "cost_price": to_float("cost_price", "Cost price"),
        "selling_price": to_float("selling_price", "Selling price"),
        "low_stock_threshold": to_int("low_stock_threshold", "Low stock threshold"),
    }
    return data, errors


def product_to_form(product):
    def clean(value):
        return "" if value is None else value

    return {
        "name": product.name,
        "sku": product.sku,
        "description": clean(product.description),
        "quantity_on_hand": product.quantity_on_hand,
        "cost_price": clean(product.cost_price),
        "selling_price": clean(product.selling_price),
        "low_stock_threshold": clean(product.low_stock_threshold),
    }


# ---------------------- Product routes ----------------------

@app.route("/products")
@login_required
def product_list():
    q = request.args.get("q", "").strip()
    query = Product.query.filter_by(organization_id=current_user.organization_id)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Product.name.ilike(like), Product.sku.ilike(like)))
    items = query.order_by(Product.name).all()
    return render_template("products.html", products=items, q=q)


@app.route("/products/new", methods=["GET", "POST"])
@login_required
def product_new():
    if request.method == "POST":
        data, errors = parse_product_form(request.form)
        if not errors and sku_exists(data["sku"]):
            errors.append("This SKU already exists in your organization.")

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template("product_form.html", product=None, form=request.form)

        product = Product(
            organization_id=current_user.organization_id,
            last_updated_by=current_user.id,
            **data,
        )
        db.session.add(product)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("This SKU already exists in your organization.", "danger")
            return render_template("product_form.html", product=None, form=request.form)

        flash("Product created.", "success")
        return redirect(url_for("product_list"))

    return render_template("product_form.html", product=None, form={})


@app.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
def product_edit(product_id):
    product = get_product_or_404(product_id)

    if request.method == "POST":
        data, errors = parse_product_form(request.form)
        if not errors and sku_exists(data["sku"], exclude_id=product.id):
            errors.append("This SKU already exists in your organization.")

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template("product_form.html", product=product, form=request.form)

        for field, value in data.items():
            setattr(product, field, value)
        product.last_updated_by = current_user.id
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("This SKU already exists in your organization.", "danger")
            return render_template("product_form.html", product=product, form=request.form)

        flash("Product updated.", "success")
        return redirect(url_for("product_list"))

    return render_template("product_form.html", product=product, form=product_to_form(product))


@app.route("/products/<int:product_id>/delete", methods=["POST"])
@login_required
def product_delete(product_id):
    product = get_product_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash("Product deleted.", "info")
    return redirect(url_for("product_list"))


@app.route("/products/<int:product_id>/adjust", methods=["POST"])
@login_required
def product_adjust(product_id):
    product = get_product_or_404(product_id)
    try:
        change = int(request.form.get("change", "").strip())
    except ValueError:
        flash("Enter a whole number like 5 or -3 to adjust stock.", "danger")
        return redirect(url_for("product_list"))

    new_quantity = product.quantity_on_hand + change
    if new_quantity < 0:
        flash("Stock cannot go below 0.", "danger")
        return redirect(url_for("product_list"))

    product.quantity_on_hand = new_quantity
    product.last_updated_by = current_user.id
    db.session.commit()
    flash(f"Stock updated for {product.name}: now {new_quantity}.", "success")
    return redirect(url_for("product_list"))

@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    org = current_user.organization

    if request.method == "POST":
        value = request.form.get("default_low_stock_threshold", "").strip()
        try:
            threshold = int(value)
        except ValueError:
            flash("Default low stock threshold must be a whole number.", "danger")
            return render_template("settings.html", org=org, value=value)

        if threshold < 0:
            flash("Default low stock threshold cannot be negative.", "danger")
            return render_template("settings.html", org=org, value=value)

        org.default_low_stock_threshold = threshold
        db.session.commit()
        flash("Settings saved.", "success")
        return redirect(url_for("settings"))

    return render_template("settings.html", org=org, value=org.default_low_stock_threshold)

@app.errorhandler(404)
def not_found(error):
    return render_template("404.html"), 404

if __name__ == "__main__":
    app.run(debug=True)