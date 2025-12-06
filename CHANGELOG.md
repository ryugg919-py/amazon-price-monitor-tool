# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [1.0.0] - 2025-12-05
### Added
- Currency-aware scraping with USD-first URLs and fallback, plus `force_usd` option.
- Currency detection (USD/JPY/UNKNOWN) and storage on every scrape record.
- Lightweight DB migration adding the `currency` column to `prices`.
- USD-only stats, diffs, and dashboard charts to avoid cross-currency noise.
- Per-target price selectors with deterministic container selection.
- Debug HTML dump option for failed parses.
- FastAPI dashboard (Jinja + Chart.js) with currency display and failure messaging.
- JSON API endpoints for history/current prices and CSV export.
- Slack notifications via webhook and bot uploads with diff-only logic.
- Comprehensive tests for scraper, currency handling, DB, API, dashboard resilience, and diff logic.

### Changed
- Improved price parsing to avoid rating-count false positives while remaining resilient to DOM changes.
- Docs updated to reflect currency handling, DB schema, configuration, and operations.

### Fixed
- Eliminated prior bugs where rating counts could be misinterpreted as prices.
- Stabilized selector fallbacks and clarified error reporting on the dashboard.
