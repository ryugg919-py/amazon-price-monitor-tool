from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import db, paths, price_logic
from .main import run_job_for_api, load_targets_and_settings

BASE_DIR = paths.BASE_DIR

app = FastAPI(
    title="amazon-price-monitor-tool API",
    description="Amazon price monitor API + dashboard",
)


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _price_level(diff_pct: Optional[float]) -> str:
    if diff_pct is None:
        return "level-normal"
    if diff_pct <= -5.0:
        return "level-cheap"
    if diff_pct >= 5.0:
        return "level-expensive"
    return "level-normal"


def _safe_int(value: Any) -> Optional[int]:
    """Safely convert a value to int, returning None if invalid."""
    try:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return int(value)
        s = str(value).strip()
        if not s:
            return None
        return int(float(s))
    except (TypeError, ValueError):
        return None


def build_amazon_url(asin: str, market: str) -> str:
    base = "https://www.amazon.com/dp"
    if market.lower() in {"amazon_jp", "amazon jp"}:
        base = "https://www.amazon.co.jp/dp"
    return f"{base}/{asin}"


def _build_dashboard_items(days: int = 30) -> List[dict]:
    targets: List = []
    try:
        targets, _ = load_targets_and_settings()
    except Exception:
        targets = []

    latest_df = db.load_latest_prices()
    history_df = db.load_price_history(days=days)

    stats_df = price_logic.build_price_stats(history_df) if not history_df.empty else pd.DataFrame()

    stats_map = {}
    if not stats_df.empty:
        for _, row in stats_df.iterrows():
            key = row["product_code"]
            stats_map[key] = {
                "avg_price": float(row["avg_price"]),
                "diff_from_avg_percent": float(row["diff_from_avg_percent"]),
            }

    latest_map: Dict[str, Any] = {}
    if not latest_df.empty:
        for _, row in latest_df.iterrows():
            latest_map[row["product_code"]] = row

    # Latest OK USD rows for current price
    latest_ok_usd: Dict[str, Any] = {}
    if not history_df.empty:
        ok_usd = history_df.copy()
        if "status" in ok_usd.columns:
            ok_usd = ok_usd[ok_usd["status"] == "ok"]
        if "currency" in ok_usd.columns:
            ok_usd = ok_usd[ok_usd["currency"] == "USD"]
        if not ok_usd.empty:
            ok_usd = ok_usd.sort_values("scraped_at").drop_duplicates(subset=["product_code"], keep="last")
            for _, row in ok_usd.iterrows():
                latest_ok_usd[row["product_code"]] = row

    items: List[dict] = []
    for target in targets:
        code = target.code
        latest_row = latest_map.get(code)
        ok_row = latest_ok_usd.get(code)
        stats = stats_map.get(code)
        diff_pct = stats["diff_from_avg_percent"] if stats else None

        scraped_at_val = latest_row["scraped_at"] if latest_row is not None else None
        if scraped_at_val is not None and not isinstance(scraped_at_val, str):
            scraped_at_val = str(scraped_at_val)

        price_val = None
        currency_val = None
        if ok_row is not None:
            price_val = _safe_int(ok_row["price"])
            currency_val = ok_row.get("currency")
        elif latest_row is not None:
            price_val = _safe_int(latest_row["price"])
            currency_val = latest_row.get("currency")

        items.append(
            {
                "site_name": target.market,
                "product_code": code,
                "product_name": target.name or "",
                "category": target.category or "",
                "price": price_val,
                "avg_price": stats["avg_price"] if stats else None,
                "diff_from_avg_percent": diff_pct,
                "scraped_at": scraped_at_val,
                "price_level": _price_level(diff_pct),
                "asin": target.asin,
                "url": build_amazon_url(target.asin, target.market),
                "status": latest_row["status"] if latest_row is not None else "failed",
                "error": latest_row.get("error") if latest_row is not None else None,
                "currency": currency_val,
            }
        )
    return items


@app.post("/run", response_class=JSONResponse)
def run_job() -> JSONResponse:
    """Trigger one scrape+store+report job."""
    result = run_job_for_api()
    return JSONResponse({"status": "ok", **result})


@app.get("/prices/latest", response_class=JSONResponse)
def get_latest_prices() -> JSONResponse:
    """Return the latest price per product."""
    df = db.load_latest_prices()
    if df.empty:
        return JSONResponse([])

    records = df.to_dict(orient="records")
    for r in records:
        if not isinstance(r.get("scraped_at"), str):
            r["scraped_at"] = str(r["scraped_at"])
    return JSONResponse(records)


@app.get("/prices/{product_code}/history", response_class=JSONResponse)
def get_price_history(product_code: str, days: int = 30, limit: int = 100, offset: int = 0) -> JSONResponse:
    """Return history for a product, limited to the last N days, with pagination."""
    df = db.load_price_history(days=days, limit=limit, offset=offset)
    if df.empty:
        return JSONResponse([])

    sub = df[df["product_code"] == product_code].copy()
    if sub.empty:
        return JSONResponse([])

    sub = sub.sort_values("scraped_at")
    sub["scraped_at"] = sub["scraped_at"].astype(str)
    records = sub[
        ["site_name", "product_code", "product_name", "category", "price", "currency", "scraped_at"]
    ].to_dict(orient="records")
    return JSONResponse(records)


@app.get("/api/products", response_class=JSONResponse)
def list_products(days: int = 30) -> JSONResponse:
    """Return products with latest price (or nulls if missing)."""
    items = _build_dashboard_items(days=days)
    return JSONResponse(items)


@app.get("/prices/{product_code}/history.csv")
def export_price_history_csv(product_code: str, days: int = 30, limit: int = 100, offset: int = 0):
    """Return history for a product as CSV."""
    df = db.load_price_history(days=days, limit=limit, offset=offset)
    sub = df[df["product_code"] == product_code].copy()
    if sub.empty:
        return HTMLResponse(content="", status_code=200, media_type="text/csv")

    sub = sub.sort_values("scraped_at")
    csv_text = sub[["site_name", "product_code", "product_name", "category", "price", "scraped_at"]].to_csv(index=False)
    return HTMLResponse(
        content=csv_text,
        status_code=200,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={product_code}_history.csv"},
    )


def _render_dashboard(request: Request, days: int = 30) -> HTMLResponse:
    items = _build_dashboard_items(days=days)
    has_data = any(item.get("price") is not None for item in items)
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "request": request,
            "items": items,
            "days": days,
            "has_data": has_data,
        },
    )


@app.get("/", response_class=HTMLResponse)
def root_dashboard(request: Request, days: int = 30) -> HTMLResponse:
    """Render dashboard at root path."""
    return _render_dashboard(request, days)


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, days: int = 30) -> HTMLResponse:
    """Render dashboard (legacy path)."""
    return _render_dashboard(request, days)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.api_app:app", host="127.0.0.1", port=8000, reload=True)
