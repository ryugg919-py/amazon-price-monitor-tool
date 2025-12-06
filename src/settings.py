"""
Settings loader with sane defaults and optional YAML overrides.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import yaml

from . import paths

logger = logging.getLogger(__name__)


@dataclass
class ScraperSettings:
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
    timeout: int = 10
    max_retries: int = 3
    sleep_sec: float = 2.0
    debug_html_dir: str | None = None
    force_usd: bool = True


DEFAULTS = {
    "scraper": ScraperSettings(),
}


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as exc:  # pragma: no cover - fallback log only
        logger.warning("Failed to load settings.yml, using defaults. Error: %s", exc)
        return {}


def load_settings(settings_path: Path | None = None) -> Dict[str, Any]:
    path = settings_path or (paths.CONFIG_DIR / "settings.yml")
    data = _load_yaml(path)
    scraper_data = data.get("scraper", {}) if isinstance(data, dict) else {}

    scraper = ScraperSettings(
        user_agent=scraper_data.get("user_agent", DEFAULTS["scraper"].user_agent),
        timeout=int(scraper_data.get("timeout", DEFAULTS["scraper"].timeout)),
        max_retries=int(scraper_data.get("max_retries", DEFAULTS["scraper"].max_retries)),
        sleep_sec=float(scraper_data.get("sleep_sec", DEFAULTS["scraper"].sleep_sec)),
        debug_html_dir=scraper_data.get("debug_html_dir", DEFAULTS["scraper"].debug_html_dir),
        force_usd=bool(scraper_data.get("force_usd", DEFAULTS["scraper"].force_usd)),
    )

    return {
        "scraper": scraper,
    }
