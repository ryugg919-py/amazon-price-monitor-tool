"""
Manage targets.yml via CLI.
Subcommands:
  add   - interactive add (manual fields)
  auto  - interactive add with auto-inferred fields from URL
  list  - print configured products
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
import yaml

from src.scraper_amazon import AMAZON_US_PRICE_CONTAINERS


BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = BASE_DIR / "config"
TARGETS_PATH = CONFIG_DIR / "targets.yml"
DEFAULT_MARKET = "amazon_us"


@dataclass
class ProductConfig:
    code: str
    asin: str
    market: str = DEFAULT_MARKET
    enabled: bool = True
    name: str | None = None
    category: str | None = None
    selector: str | None = None


def load_targets_config(path: Path = TARGETS_PATH) -> Dict[str, Any]:
    """Load targets.yml, returning a minimal structure if missing."""
    if not path.exists():
        return {"settings": {}, "targets": []}

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    data.setdefault("settings", {})
    data.setdefault("targets", [])
    return data


def save_targets_config(data: Dict[str, Any], path: Path = TARGETS_PATH) -> None:
    """Save targets.yml."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)


def build_canonical_url(raw_url: str, site_name: str, asin: str) -> str:
    """
    Backwards-compatible helper to build a canonical Amazon URL
    from a site name and ASIN. Used by tests and CLI tools.
    """
    normalized = site_name.lower()
    if normalized in ("amazon_jp", "amazon jp"):
        return f"https://www.amazon.co.jp/dp/{asin}"
    if normalized in ("amazon_us", "amazon us", "amazon"):
        return f"https://www.amazon.com/dp/{asin}"
    return raw_url


def guess_asin_from_url(url: str) -> str:
    """Extract ASIN from /dp/ or /gp/product/ URLs."""
    m = re.search(r"/dp/([A-Z0-9]{8,12})", url) or re.search(r"/gp/product/([A-Z0-9]{8,12})", url)
    if m:
        return m.group(1)
    return ""


def fetch_amazon_title(url: str, timeout: int = 10) -> str:
    """
    Fetch HTML and extract <title>, stripping common Amazon suffixes.
    Simple helper kept for backward compatibility/tests.
    """
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    html = resp.text or ""

    m = re.search(r"<title>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    if not m:
        return ""

    title = m.group(1).strip()
    title = re.sub(r"\s*\|\s*Amazon\.[^|]+$", "", title, flags=re.IGNORECASE)
    return title.strip()


def confirm_with_default(prompt: str, default: Optional[str]) -> str:
    msg = f"{prompt} [{default}]: " if default else f"{prompt}: "
    val = input(msg).strip()
    return default if (not val and default is not None) else val


def add_product_interactive(auto_fetch: bool = False) -> None:
    print("=== Add product to targets.yml ===")
    print(f"Config path: {TARGETS_PATH}")
    print()

    url = input("Product page URL (e.g. https://www.amazon.com/dp/B0FP5R9BDZ): ").strip()
    if not url:
        print("URL is required. Aborting.")
        return

    guessed_asin = guess_asin_from_url(url)
    if guessed_asin:
        asin = guessed_asin
    else:
        asin = confirm_with_default("ASIN (e.g. B0FP5R9BDZ)", None)
        if not asin:
            print("ASIN is required. Aborting.")
            return

    code = asin
    market = DEFAULT_MARKET

    name = confirm_with_default("Product name", None)
    category = confirm_with_default("category", "Gadgets")
    selector: str | None = None

    if market == DEFAULT_MARKET:
        print("Choose price container for this product:")
        print("  [1] corePriceDisplay_desktop_feature_div  (typical desktop detail price)")
        print("  [2] apex_desktop                         (top-of-page price box)")
        print("  [3] ppd                                  (legacy price area)")
        print("  [Enter] Use default (auto)")
        choice = input("> ").strip()
        if choice == "1":
            selector = AMAZON_US_PRICE_CONTAINERS["core"]
        elif choice == "2":
            selector = AMAZON_US_PRICE_CONTAINERS["apex"]
        elif choice == "3":
            selector = AMAZON_US_PRICE_CONTAINERS["ppd"]
        else:
            selector = None
    else:
        selector = None

    product_config = ProductConfig(
        code=code,
        asin=asin,
        market=DEFAULT_MARKET,
        enabled=True,
        name=name or None,
        category=category or None,
        selector=selector or None,
    )

    config = load_targets_config()
    targets: List[Dict[str, Any]] = config.setdefault("targets", [])
    targets.append(
        {
            "code": product_config.code,
            "asin": product_config.asin,
            "market": product_config.market,
            "enabled": True,
            "name": product_config.name,
            "category": product_config.category,
            "selector": product_config.selector,
        }
    )

    save_targets_config(config)

    print("\n=== Added configuration ===")
    for k, v in product_config.__dict__.items():
        print(f"{k}: {v}")
    print("\nSaved to config/targets.yml")


def list_products() -> None:
    config = load_targets_config()
    targets = config.get("targets", [])
    if not targets:
        print("No products configured. Edit config/targets.yml or use add/auto.")
        return

    print(f"{len(targets)} products configured:")
    for p in targets:
        print(f"  - {p.get('code')} | ASIN: {p.get('asin')} | market: {p.get('market')} | enabled: {p.get('enabled')}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage config/targets.yml (amazon_us only)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("add", help="Add a product (manual inputs).")
    sub.add_parser("auto", help="Add a product with auto-detected ASIN from URL.")
    sub.add_parser("list", help="List configured products.")
    return parser


def main(argv: Optional[List[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "add":
        add_product_interactive(auto_fetch=False)
    elif args.command == "auto":
        add_product_interactive(auto_fetch=True)
    elif args.command == "list":
        list_products()
    else:  # pragma: no cover
        parser.print_help()


if __name__ == "__main__":
    main()
