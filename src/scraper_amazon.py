"""
HTML fetch & price parse helpers (Amazon-focused).
"""

from __future__ import annotations

import logging
import re
import time
from typing import Optional, Tuple

import requests
from bs4 import BeautifulSoup

from pathlib import Path
from .settings import ScraperSettings, load_settings

logger = logging.getLogger(__name__)

_SETTINGS = load_settings()["scraper"]

# Default market configuration (can be extended if new regions are added)
DEFAULT_MARKET_CONFIG = {
    "amazon_us": {
        "base_url": "https://www.amazon.com/dp",
        "price_selector": "#corePriceDisplay_desktop_feature_div span.a-price-whole",
        "accept_language": "en-US,en;q=0.9",
    },
}

DEFAULT_HEADERS = {
    "User-Agent": _SETTINGS.user_agent,
    "Accept-Language": DEFAULT_MARKET_CONFIG["amazon_us"]["accept_language"],
}

# Known price containers for Amazon US
AMAZON_US_PRICE_CONTAINERS = {
    "core": "#corePriceDisplay_desktop_feature_div .a-price-whole",
    "apex": "#apex_desktop .a-price-whole",
    "ppd": "#ppd .a-price-whole",
}

def build_amazon_us_urls(asin: str) -> list[str]:
    primary = f"https://www.amazon.com/dp/{asin}?th=1&language=en_US&currency=USD"
    fallback = f"https://www.amazon.com/dp/{asin}"
    return [primary, fallback]


class ScrapingError(Exception):
    """Raised when scraping/parsing fails."""


def fetch_html(
    url: str,
    *,
    timeout: Optional[int] = None,
    max_retries: Optional[int] = None,
    sleep_sec: Optional[float] = None,
    headers: Optional[dict] = None,
    scraper_settings: Optional[ScraperSettings] = None,
) -> str:
    """Fetch HTML from URL with simple retry."""
    settings = scraper_settings or _SETTINGS
    effective_timeout = timeout if timeout is not None else settings.timeout
    effective_retries = max_retries if max_retries is not None else settings.max_retries
    effective_sleep = sleep_sec if sleep_sec is not None else settings.sleep_sec

    if headers is None:
        headers = DEFAULT_HEADERS

    last_exc: Optional[Exception] = None

    for attempt in range(1, effective_retries + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=effective_timeout)
            resp.raise_for_status()

            if resp.apparent_encoding:
                resp.encoding = resp.apparent_encoding

            logger.info("Fetched HTML from %s (status=%s)", url, resp.status_code)
            return resp.text

        except requests.RequestException as e:
            last_exc = e
            logger.warning(
                "Failed to fetch %s (attempt %d/%d): %s",
                url,
                attempt,
                effective_retries,
                e,
            )
            if attempt < effective_retries:
                time.sleep(effective_sleep)

    raise ScrapingError(f"Failed to fetch HTML from {url}") from last_exc


def _candidate_selectors(css_selector: Optional[str], market: str) -> list[str]:
    selectors: list[str] = []
    # If no selector provided, use default roaming list
    if not css_selector:
        if market == "amazon_us":
            selectors.extend(
                [
                    DEFAULT_MARKET_CONFIG["amazon_us"]["price_selector"],
                    "#corePriceDisplay_desktop_feature_div span.a-price span.a-offscreen",
                    "#corePriceDisplay_desktop_feature_div span.a-offscreen",
                    "#apex_desktop span.a-price span.a-offscreen",
                    "#ppd span.a-price span.a-offscreen",
                    "#ppd span.a-offscreen",
                    "span.a-price span.a-offscreen",
                ]
            )
        else:
            if DEFAULT_MARKET_CONFIG.get(market, {}).get("price_selector"):
                selectors.append(DEFAULT_MARKET_CONFIG[market]["price_selector"])
        return list(dict.fromkeys(selectors))

    # If selector provided, keep within the same container when recognized
    if market == "amazon_us":
        sel_lower = css_selector
        if "corePriceDisplay_desktop_feature_div" in sel_lower:
            selectors.extend(
                [
                    css_selector,
                    AMAZON_US_PRICE_CONTAINERS["core"],
                    "#corePriceDisplay_desktop_feature_div span.a-price span.a-offscreen",
                ]
            )
        elif "apex_desktop" in sel_lower:
            selectors.extend(
                [
                    css_selector,
                    AMAZON_US_PRICE_CONTAINERS["apex"],
                    "#apex_desktop span.a-price span.a-offscreen",
                ]
            )
        elif "#ppd" in sel_lower or "ppd " in sel_lower or " ppd" in sel_lower:
            selectors.extend(
                [
                    css_selector,
                    AMAZON_US_PRICE_CONTAINERS["ppd"],
                    "#ppd span.a-price span.a-offscreen",
                ]
            )
        else:
            # Unknown container: try provided selector first, then fallback roam
            selectors.append(css_selector)
            selectors.extend(_candidate_selectors(None, market))
    else:
        selectors.append(css_selector)

    return list(dict.fromkeys(selectors))  # remove duplicates, keep order


def _looks_like_price(text: str) -> bool:
    """Heuristic for fallback spans: requires currency symbol + number."""
    text = text.strip()
    if not re.search(r"[\$€¥£]", text):
        return False
    return bool(re.search(r"\d[\d,]*(\.\d+)?", text))


def _looks_like_rating(text: str) -> bool:
    t = text.lower()
    return "rating" in t or "ratings" in t


def _detect_currency(text: str) -> str:
    t = text.strip()
    if re.search(r"US?\$|\$", t):
        return "USD"
    if re.search(r"[¥￥]|JPY", t):
        return "JPY"
    return "UNKNOWN"


def parse_price_from_html(html: str, css_selector: str, *, market: str = "amazon_us") -> Tuple[float, str]:
    """Parse a numeric price from HTML by trying multiple selectors."""
    soup = BeautifulSoup(html, "html.parser")
    selectors = _candidate_selectors(css_selector, market)

    for sel in selectors:
        el = soup.select_one(sel)
        logger.debug("[%s] Trying selector %s", market, sel)
        if el is None:
            continue
        text = el.get_text(strip=True)
        logger.debug("[%s] Selector %s produced text: %r", market, sel, text)
        if _looks_like_rating(text):
            logger.debug("[%s] Skipping rating-like text from selector %s", market, sel)
            continue

        # Handle structured price spans (a-price / a-price-whole)
        price_container = (
            el.find_parent(class_="a-price")
            or (el if ("a-price" in el.get("class", []) or "a-price-whole" in el.get("class", [])) else None)
        )
        if price_container is not None:
            whole = price_container.select_one(".a-price-whole")
            fraction = price_container.select_one(".a-price-fraction")
            if whole is None and "a-price-whole" in (price_container.get("class", []) or []):
                whole = price_container
                if fraction is None:
                    fraction = price_container.find_next_sibling(class_="a-price-fraction")
            if whole is None and "a-price-whole" in sel:
                whole = el
            if whole:
                whole_txt = whole.get_text(strip=True).replace(",", "")
                frac_txt = fraction.get_text(strip=True) if fraction else ""
                if frac_txt and frac_txt.startswith("."):
                    frac_txt = frac_txt[1:]
                frac_txt = frac_txt.replace(",", "")
                num_str = whole_txt
                if frac_txt:
                    num_str = f"{whole_txt}.{frac_txt}"
                try:
                    price_val = float(num_str)
                    if sel != css_selector:
                        logger.info("[%s] Fallback selector used: %s", market, sel)
                    currency = _detect_currency(text)
                    return price_val, currency
                except ValueError:
                    # fall through to generic handling below
                    pass

        # Generic path requiring currency symbol
        if not _looks_like_price(text):
            continue
        m = re.search(r"[\d,]+(?:\.\d+)?", text)
        if not m:
            continue
            num_str = m.group(0).replace(",", "")
            try:
                price_val = float(num_str)
                if sel != css_selector:
                    logger.info("[%s] Fallback selector used: %s", market, sel)
                currency = _detect_currency(text)
                return price_val, currency
            except ValueError:
                continue

    # Heuristic fallback limited to price-looking spans only
    spans = soup.select("span.a-offscreen")
    for candidate in spans:
        text = candidate.get_text(strip=True)
        logger.debug("[%s] Heuristic candidate text: %r", market, text)
        if _looks_like_rating(text):
            logger.debug("[%s] Skipping rating-like heuristic text", market)
            continue
        if not _looks_like_price(text):
            continue
        m = re.search(r"[\d,]+(?:\.\d+)?", text)
        if not m:
            continue
        num_str = m.group(0).replace(",", "")
        try:
            price_val = float(num_str)
            currency = _detect_currency(text)
            return price_val, currency
        except ValueError:
            continue

    raise ScrapingError(
        f"Price not visible in HTML (maybe gated: sign-in or add-to-cart). Tried selectors: {selectors}"
    )


def fetch_price(
    url: str,
    css_selector: str,
    *,
    market: str = "amazon_us",
    scraper_settings: Optional[ScraperSettings] = None,
    debug_html_dir: str | None = None,
    site_name: str | None = None,
    product_code: str | None = None,
    asin: str | None = None,
) -> Tuple[float, str]:
    """Fetch page HTML then parse price."""
    settings = scraper_settings or _SETTINGS
    urls = [url]
    if market == "amazon_us" and asin:
        urls = build_amazon_us_urls(asin)

    last_exc: Optional[Exception] = None

    for idx, candidate_url in enumerate(urls):
        html = fetch_html(
            candidate_url,
            timeout=settings.timeout,
            max_retries=settings.max_retries,
            sleep_sec=settings.sleep_sec,
            headers={
                "User-Agent": settings.user_agent,
                "Accept-Language": DEFAULT_MARKET_CONFIG["amazon_us"]["accept_language"],
            },
            scraper_settings=settings,
        )
        try:
            price, currency = parse_price_from_html(html, css_selector, market=market)
            if settings.force_usd and market == "amazon_us" and currency != "USD":
                raise ScrapingError(f"Non-USD price detected ({currency})")
            logger.debug("Parsed price %.2f %s from %s", price, currency, candidate_url)
            return price, currency
        except ScrapingError as exc:
            last_exc = exc
            if debug_html_dir:
                try:
                    dump_dir = Path(debug_html_dir)
                    dump_dir.mkdir(parents=True, exist_ok=True)
                    filename = f"{site_name or market}_{product_code or 'unknown'}_{idx}.html"
                    (dump_dir / filename).write_text(html, encoding="utf-8")
                    logger.info("Saved debug HTML to %s", dump_dir / filename)
                except Exception as dump_exc:  # pragma: no cover - best effort
                    logger.warning("Failed to save debug HTML: %s", dump_exc)
            logger.info("Failed to parse price from %s: %s", candidate_url, exc)
            continue

    raise last_exc if last_exc is not None else ScrapingError("Failed to parse price from all URLs")
