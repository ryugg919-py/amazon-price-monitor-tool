from pathlib import Path


from src import db, paths
from src.main import run_job, Target
from src.settings import ScraperSettings


def test_run_job_integration(monkeypatch, tmp_path):
    db_path = tmp_path / "test.sqlite"
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    # Redirect paths for test isolation
    monkeypatch.setattr(db, "DB_PATH", db_path)
    monkeypatch.setattr(paths, "REPORT_DIR", reports_dir, raising=False)

    dummy_prices = [100.0, 120.0]

    def fake_fetch_price(url, selector, market="amazon_us", scraper_settings=None, debug_html_dir=None, site_name=None, product_code=None, asin=None):
        return dummy_prices.pop(0), "USD"

    monkeypatch.setattr("src.main.fetch_price", fake_fetch_price)
    target = Target(
        code="TEST-1",
        asin="B0TEST1234",
        market="amazon_us",
        enabled=True,
        url="https://www.amazon.com/dp/B0TEST1234",
        name="Test Product",
        category="Test",
        price_selector="#price",
        selector="#price",
    )

    def fake_load_targets_and_settings():
        from src import price_logic

        notify_settings = price_logic.NotifySettings()
        return [target], notify_settings

    monkeypatch.setattr("src.main.load_targets_and_settings", fake_load_targets_and_settings)

    # First run: seed data
    run_job(
        send_notifications=False,
        upload_images=False,
        print_report=False,
        scraper_settings=ScraperSettings(),
    )

    # Second run: creates a diff
    result = run_job(
        send_notifications=False,
        upload_images=False,
        print_report=False,
        scraper_settings=ScraperSettings(),
    )

    assert result["errors"] == []
    assert result["stats_rows"]  # stats should be present
    assert result["diff_rows"]  # diff should be detected on second run
    assert Path(reports_dir).exists()
