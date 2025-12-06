"""
Entry point and job orchestration for the price monitor.
"""

from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from . import paths, db, price_logic
from .scraper_amazon import fetch_price, ScrapingError, DEFAULT_MARKET_CONFIG
from .settings import load_settings, ScraperSettings
from .slack_notifier import notify_slack, send_error_notification, upload_chart_to_slack

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    def load_dotenv(*args, **kwargs):
        return None


load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.FileHandler(paths.LOG_DIR / "app.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

DAYS_FOR_STATS = 30

DB_PATH = db.DB_PATH  # re-export for compatibility


@dataclass
class Target:
    code: str
    asin: str
    market: str
    enabled: bool
    url: str
    name: str = ""
    category: str = ""
    price_selector: str = ""
    selector: str | None = None


def load_config() -> Dict[str, Any]:
    """Load YAML config/targets.yml."""
    config_path = paths.CONFIG_DIR / "targets.yml"
    if not config_path.exists():
        raise FileNotFoundError(f"config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    return config


def _build_url_and_selector(market: str, asin: str) -> tuple[str, str]:
    market_cfg = DEFAULT_MARKET_CONFIG.get(market)
    if not market_cfg:
        raise ValueError(f"Unsupported market: {market}")
    base_url = market_cfg["base_url"].rstrip("/")
    selector = market_cfg["price_selector"]
    return f"{base_url}/{asin}", selector


def load_targets_and_settings() -> tuple[List[Target], price_logic.NotifySettings]:
    """Load targets.yml and build Target objects + notify settings."""
    config = load_config()
    return build_targets_and_settings(config)


def build_targets_and_settings(config: Dict[str, Any]) -> tuple[List[Target], price_logic.NotifySettings]:
    """Create Target list and NotifySettings from YAML content."""
    settings_raw = (config.get("settings") or {}).get("notify") or {}
    notify_settings = price_logic.NotifySettings(
        min_abs_diff=settings_raw.get("min_abs_diff"),
        min_rate_percent=settings_raw.get("min_rate_percent"),
    )

    targets: List[Target] = []
    for p in config.get("targets", []):
        if not p.get("enabled", False):
            continue
        code = p.get("code")
        asin = p.get("asin")
        market = p.get("market")
        if not code or not asin or not market:
            logger.warning("Target missing required fields (code/asin/market): %s", p)
            continue
        try:
            url, default_selector = _build_url_and_selector(market, asin)
        except Exception as exc:
            logger.error("Failed to build URL for %s: %s", code, exc)
            continue
        selector = p.get("selector") or default_selector

        target = Target(
            code=code,
            asin=asin,
            market=market,
            enabled=True,
            url=url,
            name=p.get("name", ""),
            category=p.get("category", ""),
            price_selector=selector,
            selector=p.get("selector"),
        )
        targets.append(target)

    return targets, notify_settings


def run_job(
    *,
    for_api: bool = False,
    send_notifications: bool = True,
    upload_images: bool = True,
    print_report: bool = False,
    products_filter: Optional[set[str]] = None,
    dry_run: bool = False,
    report_only: bool = False,
    scraper_settings: Optional[ScraperSettings] = None,
) -> Dict[str, Any]:
    """
    Execute one scrape + record + report cycle.
    Returns a dict with reports/rows/errors for reuse in API.
    """
    logger.info("Run started%s", " (via API)" if for_api else "")

    result: Dict[str, Any] = {
        "diff_report_text": "",
        "stats_report_text": "",
        "full_report_text": "",
        "diff_rows": [],
        "stats_rows": [],
        "chart_files": [],
        "errors": [],
    }

    settings = scraper_settings or load_settings().get("scraper")
    errors: List[str] = []

    if report_only:
        history_df = db.load_all_history()
        notify_settings = price_logic.NotifySettings()
    else:
        try:
            db.init_db()
            targets, notify_settings = load_targets_and_settings()
        except Exception as e:
            logger.exception("Initialization failed.")
            if send_notifications:
                send_error_notification(f"Initialization failed: {e}")
            result["errors"].append(f"initialization error: {e}")
            return result

        if products_filter:
            targets = [t for t in targets if t.code in products_filter]

        if not targets:
            logger.warning("No targets configured.")
            result["errors"].append("No targets configured. Please edit config/targets.yml.")
            return result

        with db.connect() as conn:
            for t in targets:
                try:
                    price, currency = fetch_price(
                        t.url,
                        t.price_selector,
                        market=t.market,
                        scraper_settings=settings,
                        debug_html_dir=settings.debug_html_dir,
                        site_name=t.market,
                        product_code=t.code,
                        asin=t.asin,
                    )
                    logger.info("Fetched price for %s: %s %s", t.code, price, currency)
                    if not dry_run:
                        db.store_price(
                            conn,
                            site_name=t.market,
                            product_code=t.code,
                            product_name=t.name or t.code,
                            category=t.category,
                            price=price,
                            status="ok",
                            error=None,
                            currency=currency,
                        )
                except ScrapingError as e:
                    msg = f"{t.market} / {t.name or t.code} ({t.code}) scrape failed: {e}"
                    logger.error(msg)
                    errors.append(msg)
                    if not dry_run:
                        db.store_price(
                            conn,
                            site_name=t.market,
                            product_code=t.code,
                            product_name=t.name or t.code,
                            category=t.category,
                            price=None,
                            status="failed",
                            error=str(e),
                            currency="UNKNOWN",
                        )
                except Exception as e:  # pragma: no cover - safety net
                    msg = f"{t.market} / {t.name or t.code} ({t.code}) unexpected error: {e}"
                    logger.exception(msg)
                    errors.append(msg)
                    if not dry_run:
                        db.store_price(
                            conn,
                            site_name=t.market,
                            product_code=t.code,
                            product_name=t.name or t.code,
                            category=t.category,
                            price=None,
                            status="failed",
                            error=str(e),
                            currency="UNKNOWN",
                        )

            if not dry_run:
                conn.commit()
            else:
                logger.info("Dry-run enabled; database writes skipped.")

    history_df = db.load_all_history()
    diff_df = price_logic.build_diff_df(history_df, notify_settings)
    diff_report = price_logic.format_diff_report(diff_df)
    has_diffs = diff_df is not None and not diff_df.empty
    changed_codes = set(diff_df["product_code"].unique()) if has_diffs else set()

    recent_history_df = db.load_price_history(days=DAYS_FOR_STATS)
    stats_df = price_logic.build_price_stats(recent_history_df)
    stats_report = price_logic.format_stats_report(stats_df, days=DAYS_FOR_STATS)

    chart_paths: List[Path] = []
    if upload_images and has_diffs and recent_history_df is not None and not recent_history_df.empty:
        for code in changed_codes:
            p = price_logic.generate_price_chart(
                recent_history_df,
                code,
                days=DAYS_FOR_STATS,
                report_dir=paths.REPORT_DIR,
            )
            if p:
                chart_paths.append(p)

    full_report = price_logic.compose_full_report(diff_report, stats_report, chart_paths, base_dir=paths.BASE_DIR)

    if print_report:
        print(full_report)

    has_diffs = diff_df is not None and not diff_df.empty
    if send_notifications:
        if has_diffs:
            suspicious_rows = diff_df[diff_df["suspicious"]].to_dict(orient="records") if has_diffs else None
            notify_slack(full_report, suspicious_rows=suspicious_rows)

            if upload_images:
                for p in chart_paths:
                    upload_chart_to_slack(
                        p,
                        message=f"Latest price change chart ({p.stem})",
                    )
        else:
            logger.info("No price changes detected; skipping Slack notifications.")

        if errors:
            error_text = "Some targets failed to scrape:\n" + "\n".join(f"- {msg}" for msg in errors)
            send_error_notification(error_text)
    else:
        if not has_diffs:
            logger.info("No price changes detected; skipping Slack notifications.")
        if errors:
            logger.warning("Some targets failed to scrape: %s", errors)

    logger.info("Run finished%s", " (via API)" if for_api else "")

    if diff_df is not None:
        result["diff_rows"] = diff_df.to_dict(orient="records")
    if stats_df is not None:
        result["stats_rows"] = stats_df.to_dict(orient="records")

    result["diff_report_text"] = diff_report
    result["stats_report_text"] = stats_report
    result["full_report_text"] = full_report
    result["chart_files"] = [str(p.relative_to(paths.BASE_DIR)) for p in chart_paths]
    result["errors"] = errors

    return result


def run_job_for_api() -> Dict[str, Any]:
    """Wrapper used by FastAPI endpoint."""
    return run_job(for_api=True, send_notifications=True, upload_images=True, print_report=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Amazon price monitor job runner.")
    parser.add_argument("--no-slack", action="store_true", help="Disable Slack notifications and image uploads.")
    parser.add_argument("--dry-run", action="store_true", help="Run without writing to the database.")
    parser.add_argument(
        "--products",
        nargs="+",
        type=str,
        help="One or more product codes to scrape (default: all configured).",
    )
    parser.add_argument(
        "--print-report-only",
        action="store_true",
        help="Skip scraping; generate reports/charts from existing history only.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    products_filter = set(p.strip() for p in args.products) if args.products else None
    slack_enabled = not args.no_slack and not args.print_report_only
    upload_images = slack_enabled and not args.print_report_only

    run_job(
        for_api=False,
        send_notifications=slack_enabled,
        upload_images=upload_images,
        print_report=True,
        products_filter=products_filter,
        dry_run=args.dry_run,
        report_only=args.print_report_only,
    )


if __name__ == "__main__":
    main()
