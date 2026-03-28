from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf
from dotenv import load_dotenv
from supabase import create_client


def to_float(value) -> float | None:
    if value is None:
        return None
    try:
        num = float(value)
    except Exception:
        return None
    if math.isnan(num) or math.isinf(num):
        return None
    return num


def fetch_close_series(ticker: str, start: datetime, end: datetime):
    data = yf.Ticker(ticker).history(
        start=start.strftime("%Y-%m-%d"),
        end=(end + timedelta(days=1)).strftime("%Y-%m-%d"),
        auto_adjust=False,
    )
    if data is None or data.empty or "Close" not in data:
        return None
    series = data["Close"]
    if hasattr(series, "droplevel") and getattr(series.index, "nlevels", 1) > 1:
        series = series.droplevel(0)
    series = series.sort_index().ffill()
    series.index = pd.to_datetime(series.index).tz_localize(None)
    return series


def build_daily_fx_lookup(ticker: str, start: datetime, end: datetime) -> dict[str, float]:
    series = fetch_close_series(ticker, start, end)
    if series is None:
        return {}
    series = series.reindex(pd.date_range(start=start.date(), end=end.date(), freq="D")).ffill().bfill()
    return {
        pd.to_datetime(idx).strftime("%Y-%m-%d"): float(value)
        for idx, value in series.items()
        if to_float(value) is not None
    }


def chunked(items: list[dict], size: int):
    for start in range(0, len(items), size):
        yield items[start : start + size]


def main() -> int:
    load_dotenv(dotenv_path=Path(__file__).with_name(".env"), override=True)

    import os

    client = create_client(os.getenv("SUPABASE_URL", ""), os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""))
    crypto_assets = client.table("assets").select("id,symbol").eq("exchange", "CRYPTO").execute().data or []
    asset_ids = [row["id"] for row in crypto_assets]

    rows = []
    page_size = 1000
    start_index = 0
    while True:
        batch = (
            client.table("price_history")
            .select("id,collected_at,price,currency,fx_to_brl,valuation_brl,asset_id")
            .in_("asset_id", asset_ids)
            .range(start_index, start_index + page_size - 1)
            .execute()
            .data
            or []
        )
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < page_size:
            break
        start_index += page_size

    rows = [row for row in rows if row.get("fx_to_brl") is None or row.get("valuation_brl") is None]
    print({"rows_to_fix": len(rows)})
    if not rows:
        return 0

    timestamps = [datetime.fromisoformat(str(row["collected_at"]).replace("Z", "+00:00")).astimezone(timezone.utc) for row in rows]
    usd_brl = build_daily_fx_lookup("BRL=X", min(timestamps), max(timestamps))

    updates: list[dict[str, float | str]] = []
    for row in rows:
        price = to_float(row.get("price"))
        if price is None:
            continue
        date_key = datetime.fromisoformat(str(row["collected_at"]).replace("Z", "+00:00")).astimezone(timezone.utc).strftime("%Y-%m-%d")
        fx = usd_brl.get(date_key, 5.0)
        valuation_brl = price * fx
        updates.append({"id": row["id"], "fx_to_brl": fx, "valuation_brl": valuation_brl})

    updated = 0
    for batch in chunked(updates, 500):
        client.table("price_history").upsert(batch).execute()
        updated += len(batch)
        print({"updated_rows": updated})

    remaining = (
        client.table("price_history")
        .select("id")
        .in_("asset_id", asset_ids)
        .is_("fx_to_brl", None)
        .limit(1000)
        .execute()
        .data
        or []
    )
    print({"remaining_null_fx_rows": len(remaining)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
