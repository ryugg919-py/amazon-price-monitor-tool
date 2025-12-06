"""
Common filesystem paths for the project.
Ensures data/logs/reports directories exist.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
REPORT_DIR = BASE_DIR / "reports"

for _dir in (DATA_DIR, LOG_DIR, REPORT_DIR):
    _dir.mkdir(exist_ok=True)
