"""
Optional Slack notification helpers (Webhook + Bot API), English-only.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING

import requests

try:
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError
except ImportError:  # pragma: no cover - optional dependency
    WebClient = None  # type: ignore
    SlackApiError = None  # type: ignore

if TYPE_CHECKING:  # pragma: no cover
    from slack_sdk import WebClient as SlackWebClient

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    def load_dotenv(*args, **kwargs):
        return None

logger = logging.getLogger(__name__)

load_dotenv()

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")

if SLACK_BOT_TOKEN and WebClient is not None:
    slack_client: Optional["SlackWebClient"] = WebClient(token=SLACK_BOT_TOKEN)
elif SLACK_BOT_TOKEN and WebClient is None:
    logger.info("slack_sdk is not installed; Slack Bot API is disabled.")
    slack_client = None
else:
    slack_client = None


def _format_suspicious_section(rows: Optional[List[dict]]) -> str:
    if not rows:
        return ""

    lines = ["[SUSPICIOUS PRICE CHANGE]"]
    for r in rows:
        lines.append(f"Product: {r.get('product_name') or r.get('product_code')}")
        lines.append(f"Old: {r.get('old_price')}")
        lines.append(f"New: {r.get('new_price')}")
        lines.append("Reason: Large deviation beyond threshold")
        lines.append("")
    return "\n".join(lines).rstrip()


def notify_slack(message: str, *, suspicious_rows: Optional[List[dict]] = None) -> None:
    """Send text via Incoming Webhook (if configured)."""
    if not SLACK_WEBHOOK_URL:
        logger.info("Slack settings not found. Skipping notifications.")
        return

    final_message = message
    suspicious_block = _format_suspicious_section(suspicious_rows)
    if suspicious_block:
        final_message = f"{message}\n\n{suspicious_block}"

    try:
        res = requests.post(
            SLACK_WEBHOOK_URL,
            json={"text": final_message},
            timeout=10,
        )
        res.raise_for_status()
        logger.info("Sent Slack webhook notification.")
    except Exception as exc:  # pragma: no cover
        logger.error("Slack notification failed: %s", exc)


def send_error_notification(message: str) -> None:
    """Send an error notification via webhook (if configured)."""
    notify_slack(":warning: *Price Monitor Error*\n" + message)


def upload_chart_to_slack(path: Path, message: str = "") -> None:
    """Upload chart image via Slack Bot API (optional)."""
    if SLACK_BOT_TOKEN and WebClient is None:
        logger.info("slack_sdk is not installed; skipping Slack image upload.")
        return

    if slack_client is None:
        logger.info("Slack Bot client is not configured; skipping Slack image upload.")
        return

    if not SLACK_CHANNEL_ID:
        logger.info("Slack channel ID is not set; skipping Slack image upload.")
        return

    if not path.exists():
        logger.warning("Slack upload target image is missing: %s", path)
        return

    try:
        with path.open("rb") as f:
            slack_client.files_upload_v2(
                channel=SLACK_CHANNEL_ID,
                initial_comment=message or "Latest price change report with chart.",
                file=f,
                filename=path.name,
            )
        logger.info("Uploaded chart image to Slack: %s", path)
    except Exception as exc:
        if SlackApiError is not None and isinstance(exc, SlackApiError):
            err = getattr(exc, "response", {}).get("error", str(exc))
            logger.error("Slack image upload failed: %s", err)
        else:
            logger.exception("Slack image upload raised an exception: %s", exc)
