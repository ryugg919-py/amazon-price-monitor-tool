from datetime import datetime, timedelta

import pandas as pd

from src.price_logic import NotifySettings, build_diff_df


def make_history(prices):
    """Create a simple price history DataFrame for testing."""
    base = datetime(2025, 1, 1)
    rows = []
    for i, price in enumerate(prices):
        rows.append(
            {
                "site_name": "Amazon_JP",
                "product_code": "TEST-1",
                "product_name": "Test Product",
                "category": "Test",
                "price": float(price),
                "scraped_at": (base + timedelta(days=i)).isoformat(),
            }
        )
    return pd.DataFrame(rows)


def test_build_diff_df_detects_significant_change():
    """Should detect a significant price change."""
    df = make_history([1000, 1200])  # +200, +20%
    settings = NotifySettings(min_abs_diff=100, min_rate_percent=5.0)

    diff_df = build_diff_df(df, settings)

    assert diff_df is not None
    assert len(diff_df) == 1

    row = diff_df.iloc[0]
    assert row["old_price"] == 1000.0
    assert row["new_price"] == 1200.0
    assert row["abs_diff"] == 200.0
    assert round(row["rate_percent"], 2) == 20.00


def test_build_diff_df_flags_small_change_without_thresholds():
    """Any non-zero change should be detected regardless of thresholds."""
    df = make_history([1000, 1020])  # +20, +2%
    settings = NotifySettings(min_abs_diff=50, min_rate_percent=3.0)

    diff_df = build_diff_df(df, settings)

    assert diff_df is not None
    assert len(diff_df) == 1
    row = diff_df.iloc[0]
    assert row["old_price"] == 1000.0
    assert row["new_price"] == 1020.0
    assert row["abs_diff"] == 20.0
    assert round(row["rate_percent"], 2) == 2.0


def test_build_diff_df_empty_history_returns_none():
    """Empty history should return None."""
    empty_df = pd.DataFrame(
        columns=["site_name", "product_code", "product_name", "category", "price", "scraped_at"]
    )
    settings = NotifySettings(min_abs_diff=0.0, min_rate_percent=0.0)

    diff_df = build_diff_df(empty_df, settings)

    assert diff_df is None
