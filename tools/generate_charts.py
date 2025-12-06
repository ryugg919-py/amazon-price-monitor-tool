"""
tools/generate_charts.py

Helper script to generate price history charts under reports/ for all products,
using the last N days of price history regardless of whether the price changed.
"""

from __future__ import annotations

import logging
from pathlib import Path


from src.main import (
    load_price_history,
    generate_price_chart,
    DAYS_FOR_STATS,
    REPORT_DIR,
)

logger = logging.getLogger(__name__)
REPORTS_DIR = Path(REPORT_DIR)


def main() -> None:
    """
    Load the last DAYS_FOR_STATS days of history and generate a price chart per product.
    """
    # Load the most recent N days of history
    history_df = load_price_history(days=DAYS_FOR_STATS)

    if history_df is None or history_df.empty:
        print("No price history found. Run `python -m src.main` first to collect data.")
        logger.info("Price history is empty; skipping chart generation.")
        return

    # Collect target product_code list
    product_codes = sorted(history_df["product_code"].unique())
    print(f"Generating charts for {len(product_codes)} products.")

    # Ensure the reports directory exists
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    for code in product_codes:
        path = generate_price_chart(history_df, product_code=code, days=DAYS_FOR_STATS)
        if path is not None:
            msg = f"Saved chart: {path}"
            print(msg)
            logger.info(msg)
        else:
            msg = f"Skip (no history): {code}"
            print(msg)
            logger.info(msg)

    print("Finished generating all charts.")
    logger.info("Finished generating charts for all products.")


if __name__ == "__main__":
    main()
