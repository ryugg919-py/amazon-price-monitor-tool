"""
Quick DB checker.
- If prices table exists: show first 20 rows.
- If missing: print guidance instead of crashing.
"""

import sqlite3
from pathlib import Path


def check_db(db_path: Path) -> None:
    if not db_path.exists():
        print(f"Database not found at {db_path}. Run `python -m src.main` first.")
        return

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        has_table = cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='prices';"
        ).fetchone()
        if not has_table:
            print("Table 'prices' does not exist. Run `python -m src.main` to initialize.")
            return

        print("\n=== prices (first 20 rows) ===\n")
        for row in cur.execute("SELECT * FROM prices ORDER BY scraped_at DESC LIMIT 20"):
            print(row)
    finally:
        conn.close()


def main() -> None:
    db_path = Path("data/database.sqlite")
    check_db(db_path)


if __name__ == "__main__":
    main()
