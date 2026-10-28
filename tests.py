import os

# Use a temporary in-memory database so your real data is never touched
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app import app  # noqa: E402
from models import Organization, Product  # noqa: E402

app.config["TESTING"] = True


def signup(client, email, org_name):
    return client.post(
        "/signup",
        data={
            "email": email,
            "password": "secret1",
            "confirm_password": "secret1",
            "org_name": org_name,
        },
        follow_redirects=True,
    )


def add_product(client, name, sku, quantity="10"):
    return client.post(
        "/products/new",
        data={"name": name, "sku": sku, "quantity_on_hand": quantity},
        follow_redirects=True,
    )


def run():
    # 1. Anonymous users cannot open protected pages
    anon = app.test_client()
    response = anon.get("/dashboard")
    assert response.status_code == 302 and "/login" in response.headers["Location"]
    print("PASS: anonymous user is redirected to login")

    # Two separate users in two separate organizations
    client_a = app.test_client()
    client_b = app.test_client()
    signup(client_a, "a@test.com", "Org A")
    signup(client_b, "b@test.com", "Org B")

    add_product(client_a, "Pen", "PEN-01")
    with app.app_context():
        pen_id = Product.query.filter_by(sku="PEN-01").first().id

    # 2. Org B cannot see Org A's products
    response = client_b.get("/products")
    assert b"PEN-01" not in response.data
    print("PASS: Org B cannot see Org A's products")

    # 3. Org B cannot open, change or delete Org A's product
    assert client_b.get(f"/products/{pen_id}/edit").status_code == 404
    assert client_b.post(f"/products/{pen_id}/delete").status_code == 404
    assert client_b.post(f"/products/{pen_id}/adjust", data={"change": "5"}).status_code == 404
    with app.app_context():
        pen = Product.query.get(pen_id)
        assert pen is not None and pen.quantity_on_hand == 10
    print("PASS: Org B cannot edit, delete or adjust Org A's product")

    # 4. The same SKU is allowed in a different organization
    add_product(client_b, "Pen", "PEN-01")
    with app.app_context():
        assert Product.query.filter_by(sku="PEN-01").count() == 2
    print("PASS: same SKU is allowed in different organizations")

    # 5. A duplicate SKU inside the same organization is rejected
    response = add_product(client_a, "Pen Copy", "PEN-01")
    assert b"already exists" in response.data
    with app.app_context():
        org_a = Organization.query.filter_by(name="Org A").first()
        assert Product.query.filter_by(organization_id=org_a.id, sku="PEN-01").count() == 1
    print("PASS: duplicate SKU in the same organization is rejected")

    # 6. Settings are separate for each organization
    client_a.post("/settings", data={"default_low_stock_threshold": "20"})
    with app.app_context():
        org_a = Organization.query.filter_by(name="Org A").first()
        org_b = Organization.query.filter_by(name="Org B").first()
        assert org_a.default_low_stock_threshold == 20
        assert org_b.default_low_stock_threshold == 5
    print("PASS: settings are separate per organization")

    print("\nAll tests passed.")


if __name__ == "__main__":
    run()