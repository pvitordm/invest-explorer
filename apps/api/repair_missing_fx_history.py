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

    daily_index = pd.date_range(start=start.date(), end=end.date(), freq="D")
    series = series.reindex(daily_index).ffill().bfill()

    lookup: dict[str, float] = {}
    for idx, value in series.items():
        parsed = to_float(value)
        if parsed is not None:
            lookup[pd.to_datetime(idx).strftime("%Y-%m-%d")] = parsed
    return lookup


def fx_at_date(currency: str, date_key: str, usd_brl: dict[str, float], usd_jpy: dict[str, float]) -> float | None:
    if currency == "BRL":
        return 1.0

    usd_brl_val = usd_brl.get(date_key)
    if currency == "USD":
        return usd_brl_val if usd_brl_val is not None else 5.0

    if currency == "JPY":
        usd_jpy_val = usd_jpy.get(date_key)
        if usd_brl_val is None or usd_jpy_val is None or usd_jpy_val == 0:
            return 0.033
        return usd_brl_val / usd_jpy_val

    return None


def main() -> int:
    load_dotenv(dotenv_path=Path(__file__).with_name(".env"), override=True)

    import os

    url = os.getenv("SUPABASE_URL", "").strip()
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not service_key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in apps/api/.env")

    client = create_client(url, service_key)

    rows = []
    page_size = 1000
    start_index = 0
    while True:
        batch = (
            client.table("price_history")
            .select("id,collected_at,price,currency,fx_to_brl,valuation_brl")
            .in_("currency", ["USD", "JPY"])
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

    if not rows:
        print("No rows with missing FX found.")
        return 0

    dates = [datetime.fromisoformat(str(row["collected_at"]).replace("Z", "+00:00")) for row in rows if row.get("collected_at")]
    start = min(dates).astimezone(timezone.utc)
    end = max(dates).astimezone(timezone.utc)

    usd_brl = build_daily_fx_lookup("BRL=X", start, end)
    usd_jpy = build_daily_fx_lookup("JPY=X", start, end)

    updated = 0
    for row in rows:
        collected_at = str(row.get("collected_at") or "")
        price = to_float(row.get("price"))
        currency = str(row.get("currency") or "").upper()
        if not collected_at or price is None or currency not in {"USD", "JPY"}:
            continue

        date_key = datetime.fromisoformat(collected_at.replace("Z", "+00:00")).astimezone(timezone.utc).strftime("%Y-%m-%d")
        fx = fx_at_date(currency, date_key, usd_brl, usd_jpy)
        valuation_brl = price * fx if fx is not None else None
        if fx is None or valuation_brl is None:
            continue

        (
            client.table("price_history")
            .update({"fx_to_brl": fx, "valuation_brl": valuation_brl})
            .eq("id", row["id"])
            .execute()
        )
        updated += 1

    print(f"Updated {updated} rows with missing FX/BRL valuation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())