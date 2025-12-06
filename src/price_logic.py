"""
Price diff/statistics logic and formatting.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.dates import DateFormatter

from . import paths


@dataclass
class NotifySettings:
    min_abs_diff: Optional[float] = None  # absolute difference threshold
    min_rate_percent: Optional[float] = None  # percent difference threshold


def _is_suspicious_change(old_price: float, new_price: float, rate_percent: float) -> bool:
    """Flag extreme jumps/drops as suspicious."""
    if old_price <= 0:
        return False

    factor = new_price / old_price
    if factor >= 5 or factor <= 0.2:
        return True
    if abs(rate_percent) >= 500:
        return True
    return False


def build_diff_df(history_df: pd.DataFrame, notify_settings: NotifySettings) -> Optional[pd.DataFrame]:
    """
    Compute price difference between the latest two points per product.

    Returns:
        DataFrame with columns:
        site_name, product_code, product_name, category,
        old_price, new_price, abs_diff, rate_percent, suspicious
        or None if no differences pass thresholds.
    """
    _ = notify_settings  # thresholds no longer gate changes

    if history_df.empty:
        return None

    rows: List[Dict[str, Any]] = []

    df = history_df.copy()
    if "status" in df.columns:
        df = df[df["status"] == "ok"]
    if "currency" in df.columns:
        df = df[df["currency"] == "USD"]
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df = df.dropna(subset=["price"])

    grouped = df.sort_values("scraped_at").groupby(["site_name", "product_code"])

    for (site_name, product_code), g in grouped:
        g_sorted = g.sort_values("scraped_at")
        if len(g_sorted) < 2:
            continue
        prev = g_sorted.iloc[-2]
        curr = g_sorted.iloc[-1]

        old_price = float(prev["price"])
        new_price = float(curr["price"])
        if old_price == new_price:
            continue

        abs_diff = new_price - old_price
        rate_percent = (abs_diff / old_price) * 100.0 if old_price else 0.0

        suspicious = _is_suspicious_change(old_price, new_price, rate_percent)

        rows.append(
            {
                "site_name": site_name,
                "product_code": product_code,
                "product_name": curr["product_name"],
                "category": curr.get("category", ""),
                "old_price": old_price,
                "new_price": new_price,
                "abs_diff": abs_diff,
                "rate_percent": rate_percent,
                "suspicious": suspicious,
            }
        )

    if not rows:
        return None

    diff_df = pd.DataFrame(rows)
    diff_df = diff_df.sort_values(["category", "site_name", "product_name"]).reset_index(drop=True)
    return diff_df


def format_diff_report(diff_df: Optional[pd.DataFrame]) -> str:
    """Render diff DataFrame as multi-line text."""
    if diff_df is None or diff_df.empty:
        return "No price changes detected."

    lines: List[str] = []
    lines.append("=== Price Changes ===")

    for category, g in diff_df.groupby("category"):
        lines.append("")
        lines.append(f"[Category] {category or '(unspecified)'}")
        for _, row in g.iterrows():
            site = row["site_name"]
            name = row["product_name"]
            code = row["product_code"]
            old_p = row["old_price"]
            new_p = row["new_price"]
            diff = row["abs_diff"]
            rate = row["rate_percent"]

            header = f"- {site} - {name} (code: {code})"
            if row.get("suspicious"):
                header += " [SUSPICIOUS]"
            lines.append(header)
            lines.append(
                f"  {old_p:,.0f} -> {new_p:,.0f} ({diff:+,.0f} / {rate:+.2f}%)"
            )
            if row.get("suspicious"):
                lines.append("  Reason: Large deviation beyond threshold.")

    return "\n".join(lines)


def build_price_stats(history_df: pd.DataFrame) -> pd.DataFrame:
    """Compute min/max/avg/current price stats."""
    if history_df.empty:
        return pd.DataFrame()

    df = history_df.copy()
    if "status" in df.columns:
        df = df[df["status"] == "ok"]
    if "currency" in df.columns:
        df = df[df["currency"] == "USD"]
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df = df.dropna(subset=["price"])
    if df.empty:
        return pd.DataFrame()

    group_cols = ["site_name", "product_code", "product_name", "category"]

    agg = (
        df.groupby(group_cols)["price"]
        .agg(["min", "max", "mean"])
        .rename(columns={"min": "min_price", "max": "max_price", "mean": "avg_price"})
        .reset_index()
    )

    latest = (
        df.sort_values("scraped_at")
        .groupby(group_cols)
        .tail(1)[group_cols + ["price"]]
        .rename(columns={"price": "current_price"})
    )

    stats = agg.merge(latest, on=group_cols, how="left")
    stats["diff_from_avg"] = stats["current_price"] - stats["avg_price"]
    stats["diff_from_avg_percent"] = stats["diff_from_avg"] / stats["avg_price"] * 100.0

    return stats


def format_stats_report(stats_df: pd.DataFrame, days: int = 30) -> str:
    """Render statistics as text."""
    if stats_df.empty:
        return f"(No stats for the last {days} days)"

    lines: List[str] = []
    lines.append(f"=== Price Stats (last {days} days) ===")

    for _, row in stats_df.iterrows():
        site = row["site_name"]
        code = row["product_code"]
        name = row["product_name"]
        cat = row.get("category", "")
        min_price = row["min_price"]
        max_price = row["max_price"]
        avg_price = row["avg_price"]
        cur = row["current_price"]
        diff = row["diff_from_avg"]
        diff_pct = row["diff_from_avg_percent"]

        lines.append(
            f"[{cat}] {site} - {name} ({code})\n"
            f"  Min: {min_price:,.0f} / Max: {max_price:,.0f} / Avg: {avg_price:,.0f}\n"
            f"  Current: {cur:,.0f} (vs avg: {diff:+,.0f} / {diff_pct:+.2f}%)"
        )

    return "\n".join(lines)


def generate_price_chart(
    history_df: pd.DataFrame,
    product_code: str,
    *,
    days: int = 30,
    report_dir: Path = paths.REPORT_DIR,
) -> Optional[Path]:
    """Generate a PNG chart for a product and return its path."""
    sub = history_df[history_df["product_code"] == product_code].copy()
    if "status" in sub.columns:
        sub = sub[sub["status"] == "ok"]
    if "currency" in sub.columns:
        sub = sub[sub["currency"] == "USD"]
    if sub.empty:
        return None

    sub = sub.sort_values("scraped_at")

    fig, ax = plt.subplots(figsize=(6, 3))
    ax.plot(sub["scraped_at"], sub["price"], marker="o")
    ax.set_title(f"Price history ({product_code}) - last {days} days")
    ax.set_xlabel("Date")
    ax.set_ylabel("Price")

    ax.xaxis.set_major_formatter(DateFormatter("%m-%d"))
    fig.autofmt_xdate()

    out_path = report_dir / f"{product_code}_price_last{days}d.png"
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)

    return out_path


def compose_full_report(diff_report: str, stats_report: str, chart_paths: List[Path], base_dir: Path = paths.BASE_DIR) -> str:
    """Combine reports and chart file list into one text blob."""
    full_report_lines = [diff_report or "No price changes detected.", "", stats_report]

    if chart_paths:
        full_report_lines.append("")
        full_report_lines.append("[Chart files]")
        for p in chart_paths:
            try:
                rel = p.relative_to(base_dir)
            except ValueError:
                rel = p
            full_report_lines.append(f"- {rel}")

    return "\n".join(full_report_lines)
