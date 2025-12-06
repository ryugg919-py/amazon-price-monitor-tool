import pandas as pd
from datetime import datetime

from src import price_logic


def test_build_price_stats_uses_only_usd_ok():
    data = [
        {
            "site_name": "amazon_us",
            "product_code": "P1",
            "product_name": "Prod1",
            "category": "Cat",
            "price": 100,
            "status": "ok",
            "currency": "USD",
            "scraped_at": datetime(2025, 1, 1),
        },
        {
            "site_name": "amazon_us",
            "product_code": "P1",
            "product_name": "Prod1",
            "category": "Cat",
            "price": 200,
            "status": "ok",
            "currency": "JPY",
            "scraped_at": datetime(2025, 1, 2),
        },
    ]
    df = pd.DataFrame(data)
    stats = price_logic.build_price_stats(df)
    assert len(stats) == 1
    assert stats.iloc[0]["avg_price"] == 100


def test_build_price_stats_empty_when_only_jpy():
    data = [
        {
            "site_name": "amazon_us",
            "product_code": "P1",
            "product_name": "Prod1",
            "category": "Cat",
            "price": 200,
            "status": "ok",
            "currency": "JPY",
            "scraped_at": datetime(2025, 1, 2),
        },
    ]
    df = pd.DataFrame(data)
    stats = price_logic.build_price_stats(df)
    assert stats.empty
