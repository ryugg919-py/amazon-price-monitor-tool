# Contributing to amazon-price-monitor-tool

Thanks for your interest in improving the project!
This guide describes how to get a local environment running, the quality gates we expect, and the workflow for sending changes.

## Prerequisites
- Python 3.10+ (the CI runs 3.11)
- Git

## Setup
1. Clone the repository:
   git clone https://github.com/ryuhei-py/amazon-price-monitor-tool.git
   cd amazon-price-monitor-tool

2. (Optional but recommended) create a virtual environment:
   python -m venv .venv
   source .venv/Scripts/activate  # Windows PowerShell: .\.venv\Scripts\Activate.ps1

3. Install runtime dependencies:
   pip install -r requirements.txt

4. Install development dependencies:
   pip install -r requirements-dev.txt

5. Create your `.env` by copying the example:
   cp .env.example .env

Fill in Slack-related variables only if you want to test Slack integration.

## Running tests
- Lint: `ruff check .`
- Tests: `pytest -q`
- Type checks: not enforced, but please keep typing annotations consistent.

## Development workflow
1. Create a feature branch from `main`.
2. Make your changes with clear, focused commits.
3. Write or update tests alongside code changes.
4. Ensure `ruff check .` and `pytest -q` both pass.
5. Push your branch and open a Pull Request.

## Commit message style
- Use concise, imperative subject lines (e.g., “Add currency column migration”, “Fix selector fallback logging”).
- Group related changes into the same commit; avoid “misc fixes” when possible.

## Pull Request expectations
- Include a short summary of what changed and why.
- Mention any new tests or updates to existing tests.
- Note any follow-up work or known limitations.
- The CI workflow must be green (lint + tests).

## Code style and quality
- Follow the existing patterns in the codebase.
- Keep logging informative but not noisy.
- Avoid adding new dependencies unless necessary; if you do, update the appropriate requirements file.

Thanks for contributing!
