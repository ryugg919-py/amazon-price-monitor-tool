from datetime import datetime

from src import db


def test_failed_scrape_is_persisted(tmp_path):
    db_path = tmp_path / "failed.sqlite"
    db.init_db(db_path)

    with db.connect(db_path) as conn:
        db.store_price(
            conn,
            site_name="amazon_us",
            product_code="FAIL-1",
            product_name="Failing Product",
            category="Test",
            price=None,
            status="failed",
            error="CSS selector did not match any element",
            scraped_at=datetime(2025, 1, 1, 12, 0, 0),
        )
        db.store_price(
            conn,
            site_name="amazon_us",
            product_code="FAIL-1",
            product_name="Failing Product",
            category="Test",
            price=100.0,
            status="ok",
            error=None,
            scraped_at=datetime(2025, 1, 2, 12, 0, 0),
        )
        conn.commit()

    history = db.load_all_history(db_path)
    assert not history.empty
    latest = db.load_latest_prices(db_path)
    assert latest.iloc[0]["status"] == "ok"

    stats = db.load_price_history(db_path=db_path)
    assert not stats.empty
