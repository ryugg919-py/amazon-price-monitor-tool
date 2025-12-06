# Data Flow Overview

This document describes **how data moves through the Amazon Price Monitor Tool**, from scraping to storage, analytics, reporting, API consumption, and Slack notifications.

It complements `architecture.md` by focusing not on system structure, but on **runtime behavior and data transformations**.

---

# 1. High-Level Data Flow

```mermaid
flowchart TD

    A[Scheduler<br/>cron / Task Scheduler] --> B[Main Job<br/>src.main]

    B --> C[Scraper<br/>scraper_amazon.fetch_price]
    C -->|Success| D[(SQLite: prices)]
    C -->|Failure| E[(SQLite: scrape_failures)]
    C -->|Also| F[debug_html<br/>HTML snapshot]

    D --> G[price_logic<br/>diffs & stats]
    G --> H[Reports<br/>charts + text]

    G --> I[Slack Alerts<br/>(optional)]
    
    D --> J[FastAPI API<br/>src.api_app]
    J --> K[Dashboard<br/>HTML + Chart.js]
    J --> L[External Clients<br/>JSON API]
```

---

## 2. Step-by-Step Data Lifecycle

### 2.1 Triggering the Job

The execution begins from either:

- **cron** (Linux/macOS)
- **Windows Task Scheduler**
- **manual CLI**:

```bash
python -m src.main
```

The scheduler itself stores no data; it only invokes the job.

---

## 3. Scraping Stage

### 3.1 URL Resolution

For each target entry in `targets.yml`, the system builds a URL:

- preferring **USD-first Amazon URLs**
- falling back to region-specific pages if needed

**Example transformation:**

ASIN: B0ABC123
market: us
→ https://www.amazon.com/dp/B0ABC123?currency=USD&language=en_US

---

### 3.2 HTML Fetch

`scraper_amazon.fetch_html()` retrieves the product page using:

- rotating user agents  
- retry/backoff logic  
- timeout settings  

If fetching fails, the error is logged and stored in the `scrape_failures table`

---

### 3.3 Price Parsing

`parse_price_from_html()` extracts:

- price
- currency
- status (ok / failure / non-USD)

If parsing fails, the raw HTML is dumped to:`debug_html/amazon_us_<asin>_<timestamp>.html`

This is essential for diagnosing selector changes.

---

## 4. Persistence Stage (SQLite)

After a successful parse, the system writes to:

### 4.1 `prices` table

**Fields include:**

| Column     | Meaning                 |
|------------|-------------------------|
| asin       | Product identifier      |
| price      | Parsed price (float)    |
| currency   | Expected: USD           |
| status     | "ok"                    |
| scraped_at | Timestamp               |

Only `status = 'ok' AND currency = 'USD'` is considered valid for analytics.

### 4.2 `scrape_failures` table

Failures are also stored to track reliability.

| Column     | Meaning        |
|------------|----------------|
| asin       | Product ID     |
| reason     | Error message  |
| scraped_at | Timestamp      |

---

## 5. Analytics Stage (`price_logic`)

Once data is available, `price_logic` performs:

- diff calculation: today vs last successful scrape  
- rolling 30-day stats
- min/max detection
- volatility estimates
- filtering to USD-only rows

This prepares structured dictionaries for reports, dashboard, and notifications.

---

## 6. Reporting Stage

### 6.1 CLI Text Output

Summaries include:

- latest price
- change since last scrape  
- percent diff
- stats summary

**Example:**

AIRPODS-PRO3 → $199.99 (+5.3%)
30-day avg: $188.23

---

### 6.2 PNG Chart Generation

`tools/generate_charts.py` produces:

reports/<asin>_price_last30d.png

Used by Slack alerts and for portfolio documentation.

---

## 7. Slack Notification Stage (Optional)

If enabled, notifications include:

- text summary
- chart image upload

**Example:**

Price drop detected for B0ABC123:
Current: $199
Prev: $219 (-9.1%)
Chart uploaded.

Messages use either:

- webhook  
- bot token (`SLACK_BOT_TOKEN`)  

Both routes are supported.

---

## 8. API & Dashboard Stage

FastAPI reads directly from SQLite, serving:

### 8.1 Dashboard (`/`)

Renders:

- product list
- current prices
- sparkline trends
- diff indicators
- currency
- updated timestamps

Charts use **Chart.js** for dynamic visualization.

### 8.2 JSON Endpoints

| Endpoint              | Description             |
|---------------------- |-------------------------|
| `/api/current_prices` | Latest price snapshot   |
| `/api/price_history`  | Historical series       |
| `/api/products`       | Product metadata        |
| `/export/csv`         | Full CSV export         |

External systems/scripts can integrate using these endpoints.

---

## 9. Summary

The data flow is designed around:

- reliability (HTML snapshots, failure table)
- accuracy (USD-only filtering)
- observability (reports + dashboard + Slack)
- separation of concerns (scraper / DB / logic / API)

This combination results in a monitoring system that is:

- production-grade
- maintainable
- extensible
- easy to automate