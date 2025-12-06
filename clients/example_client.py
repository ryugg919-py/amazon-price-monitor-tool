import requests
from pprint import pprint

BASE_URL = "http://127.0.0.1:8000"


def get_latest_prices():
    """Fetch and print the latest prices for all products."""
    url = f"{BASE_URL}/prices/latest"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    print("=== Latest prices ===")
    pprint(data["items"])


def get_history(product_code: str, days: int = 30):
    """Fetch and print the last N days of history for the given product_code."""
    url = f"{BASE_URL}/prices/{product_code}/history"
    params = {"days": days}
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    print(f"=== History for {product_code} (last {days} days) ===")
    pprint(data["items"])


def main():
    # 1. Show latest prices for all products
    get_latest_prices()

    # 2. Show the history for a specific product (using AIRPODS-PRO3 as an example)
    get_history("AIRPODS-PRO3", days=30)


if __name__ == "__main__":
    main()
