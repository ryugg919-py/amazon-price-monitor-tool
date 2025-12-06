"""
Cleanup helper to reset local dev artifacts (logs/reports/caches).
Does NOT delete the SQLite database by default.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]


def remove_dir_contents(path: Path) -> None:
    if not path.exists():
        return
    if path.is_file():
        path.unlink(missing_ok=True)
        return
    for item in path.iterdir():
        if item.is_dir():
            shutil.rmtree(item, ignore_errors=True)
        else:
            item.unlink(missing_ok=True)


def remove_named_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)


def remove_all_pycache(root: Path) -> None:
    for current, dirnames, _ in os.walk(root):
        for d in list(dirnames):
            if d in {"__pycache__", "pycache"}:
                shutil.rmtree(Path(current) / d, ignore_errors=True)


def main() -> None:
    remove_dir_contents(BASE_DIR / "logs")
    remove_dir_contents(BASE_DIR / "reports")
    remove_named_dir(BASE_DIR / ".pytest_cache")
    remove_named_dir(BASE_DIR / ".ruff_cache")
    remove_all_pycache(BASE_DIR)
    print("Cleaned logs/, reports/, __pycache__/, .pytest_cache/, .ruff_cache/ (DB untouched).")


if __name__ == "__main__":
    main()
