from datetime import datetime

from fastapi.testclient import TestClient

from src import db
from src.api_app import app
from src.main import Target
from src import price_logic


def test_dashboard_handles_missing_price_rows(monkeypatch, tmp_path):
    # Setup DB path
    tmp_db = tmp_path / "resilience.sqlite"
    monkeypatch.setattr(db, "DB_PATH", tmp_db)
    db.init_db(tmp_db)

    # Seed only one product with price
    with db.connect(tmp_db) as conn:
        db.store_price(
            conn,
            site_name="amazon_us",
            product_code="HAS-PRICE",
            product_name="Product With Price",
            category="Test",
            price=100.0,
            status="ok",
            error=None,
            scraped_at=datetime(2025, 1, 1, 12, 0, 0),
        )
        conn.commit()

    # Two targets: one with price, one without any rows
    targets = [
        Target(
            code="HAS-PRICE",
            asin="B0PRICE001",
            market="amazon_us",
            enabled=True,
            url="https://www.amazon.com/dp/B0PRICE001",
            name="Product With Price",
            category="Test",
            price_selector="#price",
            selector="#price",
        ),
        Target(
            code="NO-PRICE",
            asin="B0NOPRICE0",
            market="amazon_us",
            enabled=True,
            url="https://www.amazon.com/dp/B0NOPRICE0",
            name="Product No Price",
            category="Test",
            price_selector="#price",
            selector="#price",
        ),
    ]

    def fake_load_targets_and_settings():
        return targets, price_logic.NotifySettings()

    monkeypatch.setattr("src.api_app.load_targets_and_settings", fake_load_targets_and_settings)

    client = TestClient(app)

    # Root and dashboard should render 200
    assert client.get("/").status_code == 200
    assert client.get("/dashboard").status_code == 200

    # API products should return both targets, second with null price
    resp = client.get("/api/products")
    assert resp.status_code == 200
    data = resp.json()
    codes = {item["product_code"]: item for item in data}
    assert "HAS-PRICE" in codes and "NO-PRICE" in codes
    assert codes["HAS-PRICE"]["price"] == 100
    assert codes["NO-PRICE"]["price"] is None
