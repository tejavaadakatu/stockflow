# StockFlow MVP

A minimal multi-tenant SaaS inventory management app built with Python (Flask).

## Features
- Signup and login with email and password (passwords are hashed)
- Each signup creates its own organization; all data is scoped by organization
- Product CRUD: name, SKU (unique per organization), description, quantity, cost price, selling price, low stock threshold
- Search products by name or SKU
- Quick "adjust stock" control (+/- N units) with last updated by and timestamps
- Dashboard: total products, total quantity, low stock table
- Settings: default low stock threshold per organization

## Tech stack
Flask, Flask-SQLAlchemy, Flask-Login, SQLite, Jinja templates, Bootstrap 5

## How to run
```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000 and sign up.

## Run the tests
```
python tests.py
```
The tests check login protection, tenant isolation, SKU rules and per-organization settings.

## Design decisions
- Every product query filters by the logged-in user's organization, so one tenant can never read or change another tenant's data (returns 404).
- A database unique constraint on (organization, SKU) enforces SKU uniqueness per organization.
- The low stock rule is: quantity on hand <= product threshold, or the organization default if the product threshold is empty.
- Hard delete with a confirm dialog is used for products (allowed by the PRD).

## Known limitations (out of scope for the MVP)
- No password reset, roles or multiple users per organization
- No CSRF protection yet (next step: Flask-WTF)
- SQLite is used for simplicity; PostgreSQL would be used in production
- No stock movement history