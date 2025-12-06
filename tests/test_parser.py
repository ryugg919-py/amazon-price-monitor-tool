from src.scraper_amazon import parse_price_from_html, ScrapingError


def test_parse_price_from_html_success():
    html = """
    <div id="price"><span class="a-price-whole">38,192</span></div>
    """
    price, currency = parse_price_from_html(html, "#price .a-price-whole")
    assert price == 38192.0
    assert currency == "UNKNOWN"  # no symbol


def test_parse_price_from_html_failure():
    html = "<div>no price here</div>"
    try:
        parse_price_from_html(html, ".missing")
    except ScrapingError:
        return
    assert False, "Expected ScrapingError"
