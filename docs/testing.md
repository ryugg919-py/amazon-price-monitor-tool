# Testing guide

This document describes the testing strategy, scope, and execution flow for the **Amazon Price Monitor Tool**. The goal is to ensure reliability, prevent regressions, and maintain production-level quality through automated tests.

The project uses:

- **pytest** - test runner
- **ruff** - linting and static checks
- **SQLite-in-memory DB mocks** - fast, isolated testing
- **monkeypatch** - behavior overrides for scraper and DB functions

---

# 1. Testing philosophy

The test suite is designed around three core goals:

### 1.1 Reliability

Scraping pipelines break frequently due to selector changes.
Tests ensure that critical logic (stats, diffs, DB I/O) stays correct.

### 1.2 Safety

Before each release, running the test suite validates:
- scraper fallback behavior
- DB integrity
- dashboard resilience
- API behavior

### 1.3 Maintainability

Each module has targeted tests so that future changes do not produce regressions.

---

# 2. Test execution

To run the full suite:

```bash
pytest
```

Expected output:

```text
33 passed
```

This confirms all components of the system are functioning correctly.

Run linting:

```bash
ruff check .
```

---

# 3. Test structure

```text
tests/
|- test_api_app.py
|- test_dashboard_resilience.py
|- test_db_io.py
|- test_diff_logic.py
|- test_failed_scrape_persistence.py
|- test_manage_targets.py
|- test_parser.py
|- test_run_job_integration.py
|- test_scraper_amazon.py
|- test_slack_notifier.py
```

Each file tests a dedicated responsibility.

---

# 4. Module-by-module coverage

## 4.1 API tests (test_api_app.py)

- Validates that FastAPI endpoints respond correctly.
- Ensures the dashboard loads even when the database is empty.
- Confirms JSON responses are well-formed.
- Ensures missing-product cases do not crash the server.

**Risk prevented:** broken dashboard or API after scrape or database changes.

## 4.2 Dashboard resilience (test_dashboard_resilience.py)

- Ensures templates render without data.
- Confirms missing stats do not raise errors.
- Verifies that Chart.js receives valid payloads.

**Risk prevented:** dashboard crashes in empty or partial-data scenarios.

## 4.3 Database I/O (test_db_io.py)

- Covers schema creation.
- Stores valid prices and failures correctly.
- Loads historical data.
- Filters to USD-only rows.
- Checks migration compatibility.

**Risk prevented:** corrupted database or incorrect data feeding into analytics.

## 4.4 Diff and stats logic (test_diff_logic.py)

- Verifies diff calculation (up, down, no-change).
- Validates 30-day statistics.
- Handles missing values.
- Tests numeric coercion logic.
- Ensures fallback logic works when only failures exist.

**Risk prevented:** incorrect Slack alerts and incorrect dashboard metrics.

## 4.5 Scrape failure handling (test_failed_scrape_persistence.py)

- Ensures failures correctly write into `scrape_failures`.
- Prevents a single failure from breaking the full run.
- Confirms failures are surfaced appropriately.

**Risk prevented:** silent scraping failures.

## 4.6 Manage targets (test_manage_targets.py)

- Covers listing targets.
- Tests adding new entries.
- Validates data rules.
- Ensures correct YAML serialization.

**Risk prevented:** broken configuration caused by malformed YAML.

## 4.7 HTML parsing rules (test_parser.py)

- Validates price selector grammar.
- Tests multi-selector fallback logic.
- Detects non-USD prices.
- Verifies error reporting.  
Ensures scraper stability under Amazon DOM changes.

**Risk prevented:** incorrect prices stored in the database.

## 4.8 Integration flow (test_run_job_integration.py)

- Runs a full execution path across main job, scraper, database, `price_logic`, and reporting.
- Ensures all layers work together coherently.

**Risk prevented:** cross-module regressions.

## 4.9 Scraper tests (test_scraper_amazon.py)

- Covers URL building.
- Validates USD-first logic.
- Tests fallback behavior.
- Verifies currency validation.

**Risk prevented:** incorrect scraping URLs and multi-currency errors.

## 4.10 Slack notifier (test_slack_notifier.py)

- Validates Slack message formatting.
- Confirms optional Slack behavior works properly.
- Ensures silent failure handling.
- Tests chart upload behavior.

**Risk prevented:** production failures during Slack alerts.

---

# 5. Mocks and monkeypatching

- **Scraper mocks:** simulate stable HTML, missing selectors, non-USD values, and network errors.
- **Database mocks:** run tests without writing to disk.
- **Slack mocks:** ensure alerts do not hit the real API during tests.

---

# 6. Integration strategy

The suite balances:

| Type               | Tests                     | Purpose                             |
|--------------------|---------------------------|-------------------------------------|
| Unit tests         | parser, diff_logic, db_io | Correctness of core functions       |
| Component tests    | API, dashboard, scraper   | Module-level integrity              |
| Integration tests  | run_job                   | Validate end-to-end behavior        |
| Reliability tests  | failure persistence       | Ensure robustness                   |

This is the same test layering used in production engineering teams.

---

# 7. What "all tests passed" guarantees

When:

```bash
pytest
```

```text
33 passed
```

It confirms:
- scraper can parse expected formats
- failures are handled gracefully
- main workflow is reliable
- dashboard will not break under empty or partial data
- database schema is correct
- Slack alerts work under mocks
- the system behaves consistently across modules

This gives high confidence that the tool is safe for scheduled automation, long-running monitoring, external integrations, and portfolio demonstrations.

---

# 8. How to extend the tests

Suggested future additions:
- load test for the API
- visual regression test for charts
- selector-change detection tests
- YAML schema validator for targets.yml

These are optional but enhance production-readiness.

---

# 9. Summary

The testing suite ensures:
- correctness
- robustness
- regression prevention
- maintainability
- real-world reliability

The system meets the standards expected of a portfolio-grade, production-style automation tool.