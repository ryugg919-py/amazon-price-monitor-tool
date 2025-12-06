from datetime import datetime

from src import db
import pandas as pd


def test_store_and_load_history(tmp_path):
    db_path = tmp_path / "test.sqlite"
    db.init_db(db_path)

    with db.connect(db_path) as conn:
        db.store_price(
            conn,
            site_name="Amazon_JP",
            product_code="TEST-1",
            product_name="Test Product",
            category="Test",
            price=1000.0,
            currency="USD",
            scraped_at=datetime(2025, 1, 1),
        )
        db.store_price(
            conn,
            site_name="Amazon_JP",
            product_code="TEST-1",
            product_name="Test Product",
            category="Test",
            price=1100.0,
            currency="USD",
            scraped_at=datetime(2025, 1, 2),
        )
        conn.commit()

    history = db.load_all_history(db_path)
    assert len(history) == 2
    assert history.iloc[0]["price"] == 1000.0
    assert history.iloc[1]["price"] == 1100.0
    assert "currency" in history.columns
    assert history["currency"].iloc[0] == "USD"


def test_load_price_history_filters_by_days(tmp_path):
    db_path = tmp_path / "test.sqlite"
    db.init_db(db_path)

    with db.connect(db_path) as conn:
        db.store_price(
            conn,
            site_name="Amazon_JP",
            product_code="TEST-1",
            product_name="Old",
            category="Test",
            price=900.0,
            currency="USD",
            scraped_at=datetime.now() - pd.Timedelta(days=40),
        )
        db.store_price(
            conn,
            site_name="Amazon_JP",
            product_code="TEST-1",
            product_name="New",
            category="Test",
            price=950.0,
            currency="USD",
            scraped_at=datetime.now(),
        )
        conn.commit()

    recent = db.load_price_history(days=30, db_path=db_path)
    assert len(recent) == 1
    assert recent.iloc[0]["price"] == 950.0
