# Operations guide

This document explains how to install, configure, run, automate, and maintain the Amazon Price Monitor Tool.
It serves as a practical reference for local development, scheduled execution, troubleshooting, and production-style usage.

---

## 1. Requirements

### 1.1 Software
- Python **3.10+**
- pip and venv
- Git
- (Optional) Slack webhook or bot token
- (Optional) cron (Linux/macOS) or Windows Task Scheduler

### 1.2 Python environment setup

```bash
git clone https://github.com/<your-username>/amazon-price-monitor-tool.git
cd amazon-price-monitor-tool

python -m venv .venv
source .venv/bin/activate   # Windows: .venv/Scripts/activate

pip install -r requirements.txt
```

---

## 2. Configuration

### 2.1 targets.yml
Define the targets to monitor. `market: us` ensures USD-first scraping URLs.

```yaml
- asin: B0ABC123
  market: us
  name: AIRPODS-PRO3

- asin: B0ZZ9999
  market: us
  name: MECHANICAL-KEYBOARD
```

### 2.2 Environment variables (.env)
Create `./.env` (do not commit it). Slack integration works with either webhook or bot upload.

```ini
SLACK_WEBHOOK_URL=<optional>
SLACK_BOT_TOKEN=<optional>
SLACK_CHANNEL_ID=<optional>
```

---

## 3. Running the tool

### 3.1 One-time execution (CLI)

```bash
python -m src.main
```

This run will read targets, scrape prices, store in SQLite, compute diffs and stats, print a text summary, generate charts (optional), and send Slack notifications (optional).

### 3.2 CLI options (src/main.py)

```bash
python -m src.main --help
```

| Option                    | Purpose                                       |
|---------------------------|-----------------------------------------------|
| `--no-slack`              | Disable Slack notifications                   |
| `--dry-run`               | Print actions without writing to the database |
| `--products AIRPODS-PRO3` | Run for selected products                     |
| `--print-report-only`     | Show summary without scraping                 |

---

## 4. Dashboard and API

### 4.1 Start FastAPI server

```bash
python -m src.api_app
```

The server starts at http://127.0.0.1:8000.

### 4.2 Dashboard features

- Current price
- Trend sparkline
- 30-day stats
- Currency
- Updated timestamp
- Product filter dropdown

### 4.3 Export and integrations

| Endpoint                      | Purpose           |
|-------------------------------|-------------------|
| `/api/current_prices`         | Latest snapshot   |
| `/api/price_history?asin=...` | Historical data   |
| `/api/products`               | Product list      |
| `/export/csv`                 | Download full CSV |

## 5. Automation (scheduling)

The tool is designed for daily or hourly automated runs.

### 5.1 Linux / macOS (cron)

Edit cron jobs:

```bash
crontab -e
```

Run every day at 08:00:

```bash
0 8 * * * cd /path/to/project && .venv/bin/python -m src.main >> run.log 2>&1
```

### 5.2 Windows (Task Scheduler)

 - Open Task Scheduler and create a Basic Task with your schedule.
 - Action: Start a program.
 - Program: `C:/path/to/python.exe`
 - Arguments: `-m src.main`
 - Start in: project directory.

---

## 6. File and directory structure

```text
debug_html/       # Raw HTML snapshots on scrape failure
reports/          # PNG price charts and text summaries
src/              # Application code
tests/            # pytest test suite
database.sqlite   # SQLite data store
```

---

## 7. Maintenance

### 7.1 Clearing debug HTML

```bash
rm debug_html/*.html
```

These files accumulate when selectors fail and are safe to delete anytime.

### 7.2 Resetting the database

```bash
rm database.sqlite
python -m src.main
```

The database will be recreated automatically.

### 7.3 Updating dependencies

```bash
pip install --upgrade -r requirements.txt
```

---

## 8. Troubleshooting

### 8.1 No data in dashboard
- Ensure `database.sqlite` exists.
- Ensure you ran `python -m src.main` at least once.

### 8.2 Price parsing fails
- Check `debug_html/amazon_us_<asin>_<timestamp>.html` to identify selector issues.

### 8.3 Slack not sending
- Verify the webhook URL.
- Verify the bot token.
- Verify the channel ID.
- Confirm internet access.

### 8.4 FastAPI not starting

```bash
uvicorn src.api_app:app --reload
```

This is useful for debugging template errors.

---

## 9. Summary
- Installation and configuration
- CLI usage
- Dashboard usage
- Automation
- Maintenance
- Troubleshooting

Combined with the architecture and data_flow docs, this enables complete setup, operation, and long-term monitoring.
