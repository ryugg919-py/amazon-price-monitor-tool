from pathlib import Path

import pytest

from src.scraper_amazon import (
    AMAZON_US_PRICE_CONTAINERS,
    ScrapingError,
    _candidate_selectors,
    build_amazon_us_urls,
    fetch_price,
    parse_price_from_html,
)
from src.settings import ScraperSettings


def test_parse_price_from_html_fallback_selector():
    html = """
    <html>
      <body>
        <span class="a-price"><span class="a-offscreen">$123.45</span></span>
      </body>
    </html>
    """
    price, currency = parse_price_from_html(html, "#missing-selector", market="amazon_us")
    assert price == pytest.approx(123.45)
    assert currency == "USD"


def test_parse_price_from_html_raises_when_no_matches():
    html = "<html><body><div>No price here</div></body></html>"
    with pytest.raises(ScrapingError):
        parse_price_from_html(html, "#missing", market="amazon_us")


def test_parse_price_skips_ratings_in_fallback():
    html = """
    <html><body>
      <span class="a-offscreen">23,405 ratings</span>
      <span class="a-offscreen">$199.99</span>
    </body></html>
    """
    price, currency = parse_price_from_html(html, "#missing", market="amazon_us")
    assert price == pytest.approx(199.99)
    assert currency == "USD"


def test_parse_price_raises_when_only_ratings():
    html = """
    <html><body>
      <span class="a-offscreen">14,042 ratings</span>
    </body></html>
    """
    with pytest.raises(ScrapingError):
        parse_price_from_html(html, "#missing", market="amazon_us")


def test_parse_price_from_a_price_whole_and_fraction():
    html = """
    <div id="corePriceDisplay_desktop_feature_div">
      <span class="a-price">
        <span class="a-price-whole">229</span>
        <span class="a-price-decimal">.</span>
        <span class="a-price-fraction">99</span>
      </span>
    </div>
    """
    price, currency = parse_price_from_html(html, "#corePriceDisplay_desktop_feature_div span.a-price-whole", market="amazon_us")
    assert price == pytest.approx(229.99)
    assert currency in {"UNKNOWN", "USD"}


def test_fetch_price_dumps_html_on_failure(monkeypatch, tmp_path):
    # Force parse failure by returning HTML with only ratings
    html = "<span class='a-offscreen'>12,345 ratings</span>"

    def fake_fetch_html(url, timeout=None, max_retries=None, sleep_sec=None, headers=None, scraper_settings=None):
        return html

    monkeypatch.setattr("src.scraper_amazon.fetch_html", fake_fetch_html)

    settings = ScraperSettings(debug_html_dir=str(tmp_path))
    with pytest.raises(ScrapingError):
        fetch_price(
            "http://example.com",
            "#price",
            market="amazon_us",
            scraper_settings=settings,
            debug_html_dir=settings.debug_html_dir,
            site_name="amazon_us",
            product_code="TEST-ASIN",
        )

    dumped_files = list(Path(tmp_path).glob("amazon_us_TEST-ASIN_*.html"))
    assert dumped_files
    assert dumped_files[0].read_text(encoding="utf-8") == html


def test_candidate_selectors_respects_fixed_core_container():
    selectors = _candidate_selectors(
        AMAZON_US_PRICE_CONTAINERS["core"],
        "amazon_us",
    )
    assert all("corePriceDisplay_desktop_feature_div" in s for s in selectors)
    assert not any("apex_desktop" in s for s in selectors)
    assert not any("#ppd" in s for s in selectors)


def test_candidate_selectors_respects_fixed_apex_container():
    selectors = _candidate_selectors(
        AMAZON_US_PRICE_CONTAINERS["apex"],
        "amazon_us",
    )
    assert all("apex_desktop" in s for s in selectors)
    assert not any("corePriceDisplay_desktop_feature_div" in s for s in selectors)
    assert not any("#ppd" in s for s in selectors)


def test_candidate_selectors_auto_mode_has_fallbacks():
    selectors = _candidate_selectors("#missing-selector", "amazon_us")
    assert any("corePriceDisplay_desktop_feature_div" in s for s in selectors)
    assert any("apex_desktop" in s for s in selectors)
    assert any("#ppd" in s for s in selectors)


def test_build_amazon_us_urls():
    urls = build_amazon_us_urls("B00TEST123")
    assert urls == [
        "https://www.amazon.com/dp/B00TEST123?th=1&language=en_US&currency=USD",
        "https://www.amazon.com/dp/B00TEST123",
    ]


def test_currency_detection_usd():
    html = "<span class='a-price'><span class='a-offscreen'>$15.76</span></span>"
    price, currency = parse_price_from_html(html, ".a-offscreen")
    assert price == pytest.approx(15.76)
    assert currency == "USD"


def test_currency_detection_jpy():
    html = "<span class='a-price'><span class='a-offscreen'>\u00a53,980</span></span>"
    price, currency = parse_price_from_html(html, ".a-offscreen")
    assert price == pytest.approx(3980.0)
    assert currency == "JPY"


def test_force_usd_rejects_jpy(monkeypatch):
    html_usd = "<span class='a-price'><span class='a-offscreen'>$10.00</span></span>"
    html_jpy = "<span class='a-price'><span class='a-offscreen'>￥1,000</span></span>"

    calls = []

    def fake_fetch_html(url, timeout=None, max_retries=None, sleep_sec=None, headers=None, scraper_settings=None):
        calls.append(url)
        if "currency=USD" in url:
            return html_jpy  # primary returns JPY -> rejected when force_usd
        return html_usd  # fallback returns USD

    monkeypatch.setattr("src.scraper_amazon.fetch_html", fake_fetch_html)

    settings = ScraperSettings(debug_html_dir=None, force_usd=True)
    price, currency = fetch_price(
        "http://example.com",
        "#price",
        market="amazon_us",
        scraper_settings=settings,
        debug_html_dir=None,
        site_name="amazon_us",
        product_code="TEST-ASIN",
        asin="TEST-ASIN",
    )
    assert price == pytest.approx(10.0)
    assert currency == "USD"
    assert len(calls) == 2


def test_force_usd_allows_non_usd_when_disabled(monkeypatch):
    html_jpy = "<span class='a-price'><span class='a-offscreen'>\u00a51,000</span></span>"

    def fake_fetch_html(url, timeout=None, max_retries=None, sleep_sec=None, headers=None, scraper_settings=None):
        return html_jpy

    monkeypatch.setattr("src.scraper_amazon.fetch_html", fake_fetch_html)

    settings = ScraperSettings(debug_html_dir=None, force_usd=False)
    price, currency = fetch_price(
        "http://example.com",
        ".a-offscreen",
        market="amazon_us",
        scraper_settings=settings,
        debug_html_dir=None,
        site_name="amazon_us",
        product_code="TEST-ASIN",
        asin="TEST-ASIN",
    )
    assert price == pytest.approx(1000.0)
    assert currency == "JPY"
