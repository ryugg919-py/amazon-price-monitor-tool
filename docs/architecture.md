# Architecture Overview

This document describes the system architecture of the **Amazon Price Monitor Tool**, including its major components, data storage, runtime workflow, and integration points.
The goal is to provide a clear understanding of how the system is structured and why each part exists.

---

## 1. System Goals

The system is designed to:

- Scrape **accurate Amazon USD prices**
- Persist historical price data
- Compute **diffs** and **statistics**
- Expose data via a **FastAPI dashboard + JSON API**
- Optionally send **Slack alerts** enriched with charts
- Operate as a **scheduled automation tool** (cron / Task Scheduler)
- Maintain production-quality reliability and observability

---

## 2. High-Level Architecture

```mermaid
flowchart LR
    Scheduler[Task Scheduler / cron] --> MainJob[Python entrypoint<br/>python -m src.main]
    MainJob --> Scraper[scraper_amazon.fetch_price]
    Scraper --> MainJob
    MainJob --> DB[(SQLite<br/>prices & scrape_failures)]
    MainJob --> Logic[price_logic<br/>diffs & stats]
    DB --> Logic
    Logic --> Reports[reports/<br/>PNG charts + text summaries]
    Logic --> Slack[Slack notifier<br/>(optional)]
    DB --> API[FastAPI app<br/>src.api_app]
    API --> Dashboard[HTML Dashboard<br/>Chart.js]
    API --> Clients[Integrations / scripts<br/>JSON API]
```

---

## 3. Component Breakdown

### 3.1 Scraper (`src/scraper_amazon.py`)

- Extracts the price from Amazon product pages.
- Uses USD-first URL strategy, with fallback HTML selectors.
- Saves `debug_html/` snapshots on failure.
- Returns `(price, currency)` with validation.

**Responsibility:** data acquisition

---

### 3.2 Main Job (`src/main.py`)

- Main orchestration layer.  
- Reads target products from `targets.yml`.
- Runs the scraper for each ASIN.  
- Stores results via `db.store_price`.  
- Calls diff/stat computation.  
- Emits reports and optionally Slack alerts.  

**Responsibility:** job orchestration + workflow control  

---

### 3.3 Database Layer (`src/db_io.py`)

SQLite storage with two main tables:

- `prices`  
- `scrape_failures`  

Provides:

- `store_price`
- `load_price_history`
- `load_latest_success`

Supports currency-aware queries.

**Responsibility:** durable data persistence  

---

### 3.4 Price Logic (`src/price_logic.py`)

Computes:

- price differences
- 30-day moving stats
- volatility and min/max

Prepares data for dashboard, reports, and alerts.
Ensures only `status="ok"` **AND** `currency="USD"` rows are used.

**Responsibility:** analytics and business logic  

---

### 3.5 Reporting (`tools/generate_charts.py`)

- Generates PNG charts from price history.
- Used both manually and by Slack alerts.
- Outputs images to `reports/`.

**Responsibility:** data visualization

---

### 3.6 Slack Notifier (`src/slack_notifier.py`)

Sends:

- text alerts
- chart image uploads

Optional (disabled via flags).

**Responsibility:** external notifications

---

### 3.7 FastAPI Application (`src/api_app.py`)

Serves:

- `/` dashboard (HTML)
- `/api/price_history` (JSON)
- `/api/current_prices`
- `/export/csv`

Reads directly from SQLite.  
Includes defensive error handling for missing data.

**Responsibility:** web/UI/API interface

---

### 3.8 Dashboard UI

- HTML template served by FastAPI.
- Interactive charts rendered by Chart.js.
- Allows:
  - filtering by ASIN
  - viewing latest price
  - trend visualization

**Responsibility:** visual analytics for humans

---

### 3.9 Scheduler (External)

Not included in repo—used by the user:

- cron (Linux/macOS)
- Task Scheduler (Windows)

**Purpose:** Automation of the scraping job

---

## 4. Technology Stack

| Layer         | Technology                            |
|---------------|---------------------------------------|
| Runtime       | Python 3.10+                          |
| Web Framework | FastAPI                               |
| Database      | SQLite                                |
| Charts        | Chart.js (Frontend), Matplotlib (PNG) |
| Notifications | Slack API / Webhooks                  |
| Testing       | pytest, ruff                          |
| Config        | YAML (`targets.yml`), env files       |
| Scheduler     | cron / Task Scheduler                 |

---

## 5. Design Principles

### Reliability
- SQLite-based durable storage
- Robust selector fallback
- `debug_html` on failure
- Defensive dashboard handling

### Modularity
- Scraping, logic, API, DB, Slack fully separated
- Each file has a single responsibility

### Observability
- Logging throughout
- Slack notifications include images
- Reports available offline

### Extensibility
- Can add new markets or scrapers
- Dashboard supports new metrics
- API is stable for automation workflows

---

## 6. Summary

This architecture enables:

- repeatable automation
- resilient scraping
- long-term historical tracking
- integrated alerts
- API-driven analytics
- clean separation between layers

It is intentionally structured like a real-job production monitoring tool, demonstrating engineering-level design and maintainability.
