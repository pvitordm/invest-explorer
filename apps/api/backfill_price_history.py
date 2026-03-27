from __future__ import annotations

import argparse
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf
from dotenv import load_dotenv
from supabase import Client, create_client

from market_data import CURATED_ASSETS


def chunked(items: list[dict], size: int) -> list[list[dict]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


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


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Backfill price_history in Supabase with up to 5 years of daily prices."
    )
    parser.add_argument(
        "--owner-id",
        action="append",
        default=[],
        help="Owner UUID to receive historical rows. You can pass multiple times.",
    )
    parser.add_argument(
        "--all-owners",
        action="store_true",
        help="Backfill for all owners found in snapshots/watchlists/portfolio_positions.",
    )
    parser.add_argument(
        "--years",
        type=int,
        default=5,
        help="How many years to backfill (default: 5).",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default="",
        help="Start date in YYYY-MM-DD. If provided, overrides --years.",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default="",
        help="End date in YYYY-MM-DD. Default is today UTC.",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Delete existing rows in range before inserting (recommended).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Insert batch size (default: 500).",
    )
    return parser


def read_env_and_client() -> Client:
    load_dotenv(dotenv_path=Path(__file__).with_name(".env"), override=False)
    # Values are loaded from environment by load_dotenv above.
    import os

    url = os.getenv("SUPABASE_URL", "").strip()
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not service_key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in apps/api/.env")
    return create_client(url, service_key)


def infer_owner_ids(client: Client) -> list[str]:
    owner_ids: set[str] = set()

    for table in ["snapshots", "watchlists", "portfolio_positions"]:
        try:
            data = client.table(table).select("owner_id").limit(10000).execute().data or []
            for row in data:
                owner_id = row.get("owner_id")
                if owner_id:
                    owner_ids.add(owner_id)
        except Exception:
            # Keep going; some tables might be empty.
            continue

    return sorted(owner_ids)


def get_assets_map(client: Client) -> dict[tuple[str, str], str]:
    rows = client.table("assets").select("id,symbol,exchange").limit(10000).execute().data or []
    mapping: dict[tuple[str, str], str] = {}
    for row in rows:
        symbol = str(row.get("symbol", "")).upper()
        exchange = str(row.get("exchange", "")).upper()
        asset_id = row.get("id")
        if symbol and exchange and asset_id:
            mapping[(symbol, exchange)] = asset_id
    return mapping


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
    try:
        series.index = pd.to_datetime(series.index)
    except Exception:
        pass
    return series


def fx_at_date(currency: str, date_key: str, usd_brl, usd_jpy) -> float | None:
    if currency == "BRL":
        return 1.0

    usd_brl_val = to_float(usd_brl.get(date_key)) if usd_brl is not None else None
    if currency == "USD":
        return usd_brl_val

    if currency == "JPY":
        usd_jpy_val = to_float(usd_jpy.get(date_key)) if usd_jpy is not None else None
        if usd_brl_val is None or usd_jpy_val is None or usd_jpy_val == 0:
            return None
        return usd_brl_val / usd_jpy_val

    return None


def backfill_owner(
    client: Client,
    owner_id: str,
    start: datetime,
    end: datetime,
    replace: bool,
    batch_size: int,
) -> None:
    assets_map = get_assets_map(client)

    if replace:
        start_iso = start.replace(tzinfo=timezone.utc).isoformat()
        client.table("price_history").delete().eq("owner_id", owner_id).gte("collected_at", start_iso).execute()

    usd_brl = fetch_close_series("BRL=X", start, end)
    usd_jpy = fetch_close_series("JPY=X", start, end)

    total_rows = 0
    for asset in CURATED_ASSETS:
        asset_id = assets_map.get((asset.symbol.upper(), asset.exchange.upper()))
        if not asset_id:
            continue

        closes = fetch_close_series(asset.yahoo_symbol, start, end)
        if closes is None:
            continue

        rows: list[dict] = []
        for idx, close in closes.items():
            ts = pd.to_datetime(idx)
            date_key = ts.strftime("%Y-%m-%d")
            price = to_float(close)
            if price is None:
                continue

            fx = fx_at_date(asset.currency, date_key, usd_brl, usd_jpy)
            valuation_brl = price * fx if fx is not None else None

            collected_at = datetime(ts.year, ts.month, ts.day, tzinfo=timezone.utc).isoformat()
            rows.append(
                {
                    "owner_id": owner_id,
                    "asset_id": asset_id,
                    "snapshot_id": None,
                    "price": price,
                    "valuation_brl": valuation_brl,
                    "currency": asset.currency,
                    "fx_to_brl": fx,
                    "data_quality": "historical_backfill",
                    "collected_at": collected_at,
                }
            )

        if not rows:
            continue

        for batch in chunked(rows, batch_size):
            client.table("price_history").insert(batch).execute()
            total_rows += len(batch)

    print(f"owner {owner_id}: inserted {total_rows} rows")


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    if not args.owner_id and not args.all_owners:
        parser.error("Provide --owner-id <uuid> or --all-owners")

    client = read_env_and_client()

    owner_ids = list(args.owner_id)
    if args.all_owners:
        inferred = infer_owner_ids(client)
        owner_ids = sorted(set(owner_ids + inferred))

    if not owner_ids:
        raise RuntimeError("No owner ids found to backfill")

    if args.end_date:
        end = datetime.strptime(args.end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    else:
        end = datetime.now(timezone.utc)

    if args.start_date:
        start = datetime.strptime(args.start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    else:
        start = end - timedelta(days=365 * args.years)

    if start >= end:
        raise RuntimeError("start date must be before end date")

    print(f"Backfilling from {start.date()} to {end.date()} for {len(owner_ids)} owner(s)")
    for owner_id in owner_ids:
        backfill_owner(
            client=client,
            owner_id=owner_id,
            start=start,
            end=end,
            replace=args.replace,
            batch_size=args.batch_size,
        )

    print("Backfill completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
