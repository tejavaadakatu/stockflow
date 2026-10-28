# StockFlow MVP

A minimal multi-tenant SaaS inventory management app built with Python (Flask).

## Live Demo
[https://YOUR-APP-LINK.onrender.com](https://stockflow-1-u3xl.onrender.com)

> **Note:** The app is hosted on Render's free tier. After a period of inactivity the service sleeps, so the **first load can take up to 50 seconds**. The free demo database expires on **28 November 2026**. After that date, please run the app locally (see below).

You can sign up with any email and password. Each signup creates a separate organization with its own data.

## Features
- Signup and login with email and password (passwords are hashed)
- Each signup creates its own organization; all data is scoped by organization
- Product CRUD: name, SKU (unique per organization), description, quantity, cost price, selling price, low stock threshold
- Search products by name or SKU
- Quick "adjust stock" control (+/- N units) with last updated by and timestamps
- Dashboard: total products, total quantity, low stock table
- Settings: default low stock threshold per organization

## Tech stack
Flask, Flask-SQLAlchemy, Flask-Login, Jinja templates, Bootstrap 5, Gunicorn
- Database: SQLite for local development, PostgreSQL in production (Render)
- Hosting: Render (web service + managed PostgreSQL)

## How to run locally
```
git clone https://github.com/tejavaadakatu/stockflow.git
cd stockflow
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000 and sign up.

On macOS/Linux, activate the environment with `source venv/bin/activate` instead.

By default the app uses a local SQLite database, so no extra setup is needed. To use a different database or secret key, set the environment variables below before running.

## Environment variables
| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Secret used to sign sessions. Use a long random value in production. |
| `DATABASE_URL` | Database connection string. If not set, local SQLite is used. |

Generate a secret key with:
```
python -c "import secrets; print(secrets.token_hex(32))"
```

## Deployment (Render)
1. Create a PostgreSQL database on Render.
2. Create a Web Service connected to this GitHub repo.
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn app:app`
3. Add the environment variables `SECRET_KEY` and `DATABASE_URL` (use the database's Internal Database URL).
4. Deploy. Render redeploys automatically on every push to `main`.

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
- Configuration (secret key, database URL) comes from environment variables, so no secrets are stored in the repository.

## Known limitations (out of scope for the MVP)
- No password reset, roles or multiple users per organization
- No CSRF protection yet (next step: Flask-WTF)
- The free Render database is temporary (expires after 30 days) and the free web service sleeps when idle
- No stock movement history
