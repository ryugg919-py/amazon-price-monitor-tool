from datetime import datetime

from fastapi.testclient import TestClient

from src import db
from src.api_app import app


def seed_db(db_path):
    db.init_db(db_path)
    with db.connect(db_path) as conn:
        db.store_price(
            conn,
            site_name="Amazon_JP",
            product_code="API-1",
            product_name="API Product",
            category="Test",
            price=1234.0,
            status="ok",
            error=None,
            scraped_at=datetime(2025, 1, 1, 12, 0, 0),
        )
        conn.commit()


def test_latest_prices_endpoint(monkeypatch, tmp_path):
    tmp_db = tmp_path / "api.sqlite"
    monkeypatch.setattr(db, "DB_PATH", tmp_db)
    seed_db(tmp_db)

    client = TestClient(app)
    resp = client.get("/prices/latest")
    assert resp.status_code == 200

    data = resp.json()
    assert len(data) == 1
    assert data[0]["product_code"] == "API-1"
    assert data[0]["price"] == 1234.0


def test_root_dashboard_renders(monkeypatch, tmp_path):
    tmp_db = tmp_path / "api.sqlite"
    monkeypatch.setattr(db, "DB_PATH", tmp_db)
    seed_db(tmp_db)

    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "amazon-price-monitor-tool" in resp.text
