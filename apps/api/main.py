import os
import asyncio
import logging
import json
from typing import Callable
from pathlib import Path
from uuid import UUID
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from urllib.parse import urlencode
from urllib.request import Request as UrlRequest, urlopen
from urllib.error import HTTPError
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from market_data import build_currency_rates_payload, build_live_snapshot_payload, CURATED_ASSETS
from supabase import create_client, Client
import yfinance as yf

try:
    from jwt import PyJWKClient, decode
    from jwt.exceptions import InvalidTokenError
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False

load_dotenv(dotenv_path=Path(__file__).with_name(".env"), override=True)
logger = logging.getLogger(__name__)

_supabase_admin_client: Client | None = None
_scheduler_task: asyncio.Task | None = None
BRT_TZ = ZoneInfo("America/Sao_Paulo")


class WatchlistItemPayload(BaseModel):
    symbol: str
    exchange: str
    notes: str | None = None


def _is_valid_uuid(value: str | None) -> bool:
    if not value:
        return False
    try:
        UUID(value)
        return True
    except Exception:
        return False


def _get_supabase_admin() -> Client | None:
    global _supabase_admin_client
    if _supabase_admin_client:
        return _supabase_admin_client

    url = os.getenv("SUPABASE_URL", "").strip()
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not service_key:
        return None

    try:
        _supabase_admin_client = create_client(url, service_key)
        return _supabase_admin_client
    except Exception as e:
        logger.warning(f"Failed to initialize Supabase admin client: {e}")
        return None


def _upsert_curated_assets(client: Client) -> None:
    rows = [
        {
            "name": a.name,
            "symbol": a.symbol,
            "exchange": a.exchange,
            "currency": a.currency,
            "asset_class": a.asset_class,
            "country_code": a.country_code,
            "is_active": True,
        }
        for a in CURATED_ASSETS
    ]
    client.table("assets").upsert(rows, on_conflict="symbol,exchange").execute()


def _ensure_default_watchlist(client: Client, owner_id: str) -> dict:
    query = (
        client.table("watchlists")
        .select("id,name,is_default")
        .eq("owner_id", owner_id)
        .eq("is_default", True)
        .limit(1)
        .execute()
    )
    if query.data:
        return query.data[0]

    created = (
        client.table("watchlists")
        .insert({"owner_id": owner_id, "name": "Default", "is_default": True})
        .execute()
    )
    if created.data:
        return created.data[0]
    raise RuntimeError("Failed to create default watchlist")


def _persist_snapshot(client: Client, owner_id: str, payload: dict) -> str | None:
    result = (
        client.table("snapshots")
        .insert(
            {
                "owner_id": owner_id,
                "snapshot_type": "manual_refresh",
                "data": payload,
            }
        )
        .execute()
    )
    if result.data:
        return result.data[0].get("id")
    return None


def _load_asset_ids_map(client: Client) -> dict[tuple[str, str], str]:
    query = client.table("assets").select("id,symbol,exchange").execute()
    mapping: dict[tuple[str, str], str] = {}
    for row in query.data or []:
        symbol = str(row.get("symbol", "")).upper()
        exchange = str(row.get("exchange", "")).upper()
        asset_id = row.get("id")
        if symbol and exchange and asset_id:
            mapping[(symbol, exchange)] = asset_id
    return mapping


def _persist_price_history(client: Client, owner_id: str, payload: dict, snapshot_id: str | None) -> None:
    assets = payload.get("assets") if isinstance(payload, dict) else None
    if not isinstance(assets, list) or not assets:
        return

    asset_ids_map = _load_asset_ids_map(client)
    rows = []

    for asset in assets:
        if not isinstance(asset, dict):
            continue
        symbol = str(asset.get("symbol", "")).upper()
        exchange = str(asset.get("exchange", "")).upper()
        asset_id = asset_ids_map.get((symbol, exchange))
        if not asset_id:
            continue

        currency = asset.get("currency") or "BRL"
        fx_to_brl = asset.get("fx_to_brl")
        if fx_to_brl is None:
            if currency == "BRL":
                fx_to_brl = 1.0
            elif currency == "USD":
                fx_to_brl = 5.0
            elif currency == "JPY":
                fx_to_brl = 0.033

        valuation_brl = asset.get("valuation_brl")
        price = asset.get("price")
        if valuation_brl is None and price is not None and fx_to_brl is not None:
            try:
                valuation_brl = float(price) * float(fx_to_brl)
            except Exception:
                valuation_brl = None

        rows.append(
            {
                "owner_id": owner_id,
                "asset_id": asset_id,
                "snapshot_id": snapshot_id,
                "price": price,
                "valuation_brl": valuation_brl,
                "currency": currency,
                "fx_to_brl": fx_to_brl,
                "data_quality": asset.get("data_quality") or "fallback_fx",
                "collected_at": payload.get("updated_at"),
            }
        )

    if rows:
        client.table("price_history").upsert(rows, on_conflict="owner_id,asset_id,collected_at").execute()


def _persist_exchange_rates(client: Client) -> None:
    rows = build_currency_rates_payload()
    if not rows:
        return
    client.table("exchange_rates").upsert(rows, on_conflict="base_currency,quote_currency,collected_at").execute()


def _list_owner_ids(client: Client) -> list[str]:
    owner_ids: set[str] = set()
    for table_name in ["snapshots", "watchlists", "portfolio_positions"]:
        try:
            rows = client.table(table_name).select("owner_id").limit(10000).execute().data or []
            for row in rows:
                owner = row.get("owner_id")
                if _is_valid_uuid(owner):
                    owner_ids.add(owner)
        except Exception:
            continue
    return sorted(owner_ids)


def _run_scheduled_refresh_once() -> None:
    admin = _get_supabase_admin()
    if not admin:
        return

    started_at = datetime.now(timezone.utc)
    status = "ok"
    message = "scheduled refresh completed"
    success_owners = 0

    owner_ids = _list_owner_ids(admin)
    if not owner_ids:
        _persist_scheduler_run(
            admin,
            status="skipped",
            message="No owners found for scheduled refresh",
            started_at=started_at,
            finished_at=datetime.now(timezone.utc),
            metadata={"owner_count": 0, "success_owners": 0},
        )
        return

    _upsert_curated_assets(admin)
    payload = build_live_snapshot_payload()
    try:
        _persist_exchange_rates(admin)
    except Exception as e:
        logger.warning(f"Scheduled exchange-rate persistence failed: {e}")
    for owner_id in owner_ids:
        try:
            snapshot_id = _persist_snapshot(admin, owner_id, payload)
            _persist_price_history(admin, owner_id, payload, snapshot_id)
            success_owners += 1
        except Exception as e:
            status = "partial"
            message = f"Some owner refresh operations failed: {e}"
            logger.warning(f"Scheduled refresh failed for owner {owner_id}: {e}")

    _persist_scheduler_run(
        admin,
        status=status,
        message=message,
        started_at=started_at,
        finished_at=datetime.now(timezone.utc),
        metadata={
            "owner_count": len(owner_ids),
            "success_owners": success_owners,
            "asset_count": payload.get("asset_count", 0),
            "live_asset_count": payload.get("live_asset_count", 0),
            "fallback_asset_count": payload.get("fallback_asset_count", 0),
            "updated_at": payload.get("updated_at"),
        },
    )


def _persist_scheduler_run(
    client: Client,
    *,
    status: str,
    message: str,
    started_at: datetime,
    finished_at: datetime,
    metadata: dict,
) -> None:
    try:
        client.table("scheduler_runs").insert(
            {
                "status": status,
                "message": message,
                "started_at": started_at.isoformat(),
                "finished_at": finished_at.isoformat(),
                "metadata": metadata,
            }
        ).execute()
    except Exception as e:
        text = str(e)
        if "PGRST205" in text or "scheduler_runs" in text:
            logger.info("Scheduler audit table not available yet; skipping persistence")
            return
        logger.warning(f"Failed to persist scheduler run audit: {e}")


def _get_scheduler_runs(client: Client, limit: int = 10) -> list[dict]:
    try:
        rows = (
            client.table("scheduler_runs")
            .select("id,status,message,started_at,finished_at,created_at,metadata")
            .order("started_at", desc=True)
            .limit(limit)
            .execute()
            .data
            or []
        )
        return rows
    except Exception as e:
        text = str(e)
        if "PGRST205" in text or "scheduler_runs" in text:
            return []
        logger.warning(f"Failed to load scheduler run audit: {e}")
        return []


def _latest_data_updated_at(client: Client | None) -> str | None:
    if not client:
        return None
    try:
        rows = (
            client.table("price_history")
            .select("collected_at")
            .order("collected_at", desc=True)
            .limit(1)
            .execute()
            .data
            or []
        )
        if rows:
            return rows[0].get("collected_at")
    except Exception as e:
        logger.warning(f"Failed to get latest data timestamp: {e}")
    return None


def _parse_scheduler_brt_times(raw: str | None) -> list[tuple[int, int]]:
    text = (raw or "").strip()
    parsed: list[tuple[int, int]] = []
    for token in text.split(","):
        clean = token.strip()
        if not clean:
            continue
        try:
            hour_str, minute_str = clean.split(":", 1)
            hour = int(hour_str)
            minute = int(minute_str)
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                parsed.append((hour, minute))
        except Exception:
            continue

    unique_sorted = sorted(set(parsed))
    return unique_sorted or [(8, 0), (14, 0), (20, 0)]


def _next_run_at_utc(now_utc: datetime, brt_times: list[tuple[int, int]]) -> datetime:
    now_brt = now_utc.astimezone(BRT_TZ)
    candidates: list[datetime] = []

    for day_offset in (0, 1):
        base_day = (now_brt + timedelta(days=day_offset)).date()
        for hour, minute in brt_times:
            candidate_brt = datetime(
                base_day.year,
                base_day.month,
                base_day.day,
                hour,
                minute,
                tzinfo=BRT_TZ,
            )
            if candidate_brt > now_brt:
                candidates.append(candidate_brt)

    next_brt = min(candidates)
    return next_brt.astimezone(timezone.utc)


async def _scheduler_loop() -> None:
    schedule_raw = os.getenv("SCHEDULER_BRT_TIMES", "08:00,14:00,20:00")

    brt_times = _parse_scheduler_brt_times(schedule_raw)
    logger.info(
        "Scheduler enabled for BRT slots: %s",
        ", ".join(f"{h:02d}:{m:02d}" for h, m in brt_times),
    )

    while True:
        now_utc = datetime.now(timezone.utc)
        next_run_utc = _next_run_at_utc(now_utc, brt_times)
        sleep_seconds = max(1.0, (next_run_utc - now_utc).total_seconds())
        logger.info(
            "Next scheduled refresh at %s BRT (%s UTC)",
            next_run_utc.astimezone(BRT_TZ).isoformat(timespec="seconds"),
            next_run_utc.isoformat(timespec="seconds"),
        )
        await asyncio.sleep(sleep_seconds)

        try:
            _run_scheduled_refresh_once()
        except Exception as e:
            logger.warning(f"Scheduled refresh cycle failed: {e}")


def _period_to_start(period: str) -> datetime:
    now = datetime.now(timezone.utc)
    p = period.lower().strip()
    if p in {"all", "max", "full"}:
        return datetime(1970, 1, 1, tzinfo=timezone.utc)
    if p == "30d":
        return now - timedelta(days=30)
    if p == "90d":
        return now - timedelta(days=90)
    if p == "1y":
        return now - timedelta(days=365)
    if p == "5y":
        return now - timedelta(days=365 * 5)
    return now - timedelta(days=365)


def _resolve_asset_id(client: Client, symbol: str, exchange: str) -> str | None:
    query = (
        client.table("assets")
        .select("id")
        .eq("symbol", symbol)
        .eq("exchange", exchange)
        .limit(1)
        .execute()
    )
    if query.data:
        return query.data[0].get("id")
    return None


def _safe_parse_datetime(value: str | None) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc)


def _unique_points_from_desc(rows: list[dict], limit: int) -> list[dict]:
    seen: set[str] = set()
    picked: list[dict] = []
    for row in rows:
        key = str(row.get("collected_at") or "")
        if not key or key in seen:
            continue
        seen.add(key)
        picked.append(row)
        if len(picked) >= limit:
            break
    return sorted(
        picked,
        key=lambda r: _safe_parse_datetime(str(r.get("collected_at") or "")),
    )


def _http_get_json(url: str, headers: dict[str, str] | None = None, timeout: int = 12) -> dict | list | None:
    req = UrlRequest(url, headers={"User-Agent": "invest-explorer/1.0", **(headers or {})})
    with urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _normalize_news_item(
    provider: str,
    symbol: str,
    asset_name: str,
    title: str | None,
    description: str | None,
    url: str | None,
    published_at: str | None,
    source: str | None,
    image: str | None,
) -> dict | None:
    def _normalize_source(value) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            clean = value.strip()
            return clean or None
        if isinstance(value, dict):
            for key in ("displayName", "name", "sourceId", "site"):
                candidate = value.get(key)
                if isinstance(candidate, str) and candidate.strip():
                    return candidate.strip()
            return None
        if isinstance(value, list):
            for item in value:
                normalized = _normalize_source(item)
                if normalized:
                    return normalized
            return None
        as_text = str(value).strip()
        return as_text or None

    clean_url = str(url or "").strip()
    clean_title = str(title or "").strip()
    if not clean_url or not clean_title:
        return None

    return {
        "symbol": symbol,
        "asset_name": asset_name,
        "title": clean_title,
        "description": (description or "").strip() or None,
        "url": clean_url,
        "published_at": published_at,
        "source": _normalize_source(source),
        "image": image,
        "provider": provider,
    }


def _format_alpha_datetime(value: str | None) -> str | None:
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    # Ex.: 20260327T120401
    try:
        parsed = datetime.strptime(raw, "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
        return parsed.isoformat()
    except Exception:
        return value


def _fetch_finnhub_articles(symbol: str, exchange: str, asset_name: str, max_items: int) -> list[dict]:
    api_key = os.getenv("FINNHUB_API_KEY", "").strip()
    if not api_key:
        return []

    now = datetime.now(timezone.utc).date()
    from_date = (now - timedelta(days=7)).isoformat()
    to_date = now.isoformat()

    symbol_candidates = [symbol]
    if exchange.upper() == "B3":
        symbol_candidates.append(f"{symbol}.SA")

    items: list[dict] = []
    for candidate in symbol_candidates:
        params = {
            "symbol": candidate,
            "from": from_date,
            "to": to_date,
            "token": api_key,
        }
        url = f"https://finnhub.io/api/v1/company-news?{urlencode(params)}"
        try:
            payload = _http_get_json(url)
        except HTTPError:
            continue
        except Exception:
            continue

        rows = payload if isinstance(payload, list) else []
        for row in rows[: max(1, min(max_items, 10))]:
            article = _normalize_news_item(
                provider="finnhub",
                symbol=symbol,
                asset_name=asset_name,
                title=row.get("headline"),
                description=row.get("summary"),
                url=row.get("url"),
                published_at=datetime.fromtimestamp(row.get("datetime", 0), tz=timezone.utc).isoformat() if row.get("datetime") else None,
                source=row.get("source"),
                image=row.get("image"),
            )
            if article:
                items.append(article)

        if items:
            break

    return items[:max_items]


def _fetch_alpha_vantage_articles(symbol: str, asset_name: str, max_items: int) -> list[dict]:
    api_key = os.getenv("ALPHAVANTAGE_API_KEY", "").strip()
    if not api_key:
        return []

    params = {
        "function": "NEWS_SENTIMENT",
        "tickers": symbol,
        "sort": "LATEST",
        "limit": max(1, min(max_items, 20)),
        "apikey": api_key,
    }
    url = f"https://www.alphavantage.co/query?{urlencode(params)}"

    try:
        payload = _http_get_json(url)
    except Exception:
        return []

    feed = payload.get("feed", []) if isinstance(payload, dict) else []
    items: list[dict] = []
    for row in feed[: max(1, min(max_items, 20))]:
        article = _normalize_news_item(
            provider="alphavantage",
            symbol=symbol,
            asset_name=asset_name,
            title=row.get("title"),
            description=row.get("summary"),
            url=row.get("url"),
            published_at=_format_alpha_datetime(row.get("time_published")),
            source=row.get("source"),
            image=row.get("banner_image"),
        )
        if article:
            items.append(article)

    return items[:max_items]


def _fetch_gnews_articles(symbol: str, asset_name: str, max_items: int, locale: str = "en") -> list[dict]:
    api_key = os.getenv("GNEWS_API_KEY", "").strip()
    if not api_key:
        return []

    language = "pt" if locale.lower().startswith("pt") else "en"
    endpoint = "https://gnews.io/api/v4/search"
    from_date = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _run_query(query: str, remaining: int) -> list[dict]:
        params = {
            "q": query,
            "lang": language,
            "sortby": "publishedAt",
            "max": max(1, min(remaining, 10)),
            "from": from_date,
            "apikey": api_key,
        }
        try:
            payload = _http_get_json(f"{endpoint}?{urlencode(params)}")
        except Exception:
            return []

        rows = payload.get("articles", []) if isinstance(payload, dict) else []
        batch: list[dict] = []
        for row in rows:
            article = _normalize_news_item(
                provider="gnews",
                symbol=symbol,
                asset_name=asset_name,
                title=row.get("title"),
                description=row.get("description"),
                url=row.get("url"),
                published_at=row.get("publishedAt"),
                source=(row.get("source") or {}).get("name"),
                image=row.get("image"),
            )
            if article:
                batch.append(article)
        return batch

    dedup: dict[str, dict] = {}
    queries = [
        f'"{symbol}" OR "{asset_name}"',
        f'"{asset_name}" stock OR market',
        symbol,
    ]

    for query in queries:
        remaining = max_items - len(dedup)
        if remaining <= 0:
            break
        for article in _run_query(query, remaining):
            url = str(article.get("url", "")).strip()
            if url and url not in dedup:
                dedup[url] = article

    return list(dedup.values())[:max_items]


def _fetch_yfinance_articles(symbol: str, exchange: str, asset_name: str, max_items: int) -> list[dict]:
    candidates = [symbol]
    if exchange.upper() == "B3":
        candidates.append(f"{symbol}.SA")

    dedup: dict[str, dict] = {}
    
    # Helper function to fetch news with timeout
    def fetch_news_with_timeout(ticker_symbol: str, timeout_secs: int = 5) -> list[dict]:
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(lambda: getattr(yf.Ticker(ticker_symbol), "news", None) or [])
                rows = future.result(timeout=timeout_secs)
                return rows if rows else []
        except (FuturesTimeoutError, Exception) as e:
            logger.debug(f"yfinance news fetch timeout/error for {ticker_symbol}: {e}")
            return []
    
    for candidate in candidates:
        try:
            rows = fetch_news_with_timeout(candidate, timeout_secs=5)
        except Exception:
            rows = []

        for row in rows:
            content = row.get("content") if isinstance(row, dict) else None
            url = None
            title = None
            summary = None
            source = None
            published_at = None

            if isinstance(content, dict):
                click = content.get("clickThroughUrl") or {}
                canonical = click.get("url") if isinstance(click, dict) else None
                title = content.get("title")
                summary = content.get("summary")
                source = content.get("provider")
                pub_ms = content.get("pubDate")
                if isinstance(pub_ms, (int, float)):
                    published_at = datetime.fromtimestamp(pub_ms / 1000, tz=timezone.utc).isoformat()
                url = canonical or content.get("canonicalUrl")

            if not url:
                url = row.get("link") if isinstance(row, dict) else None
            if not title:
                title = row.get("title") if isinstance(row, dict) else None
            if not summary:
                summary = row.get("summary") if isinstance(row, dict) else None
            if not source:
                source = row.get("publisher") if isinstance(row, dict) else None
            if not published_at and isinstance(row, dict):
                epoch = row.get("providerPublishTime")
                if isinstance(epoch, (int, float)):
                    published_at = datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()

            article = _normalize_news_item(
                provider="yfinance",
                symbol=symbol,
                asset_name=asset_name,
                title=title,
                description=summary,
                url=url,
                published_at=published_at,
                source=source,
                image=None,
            )
            if article:
                link = str(article.get("url", "")).strip()
                if link and link not in dedup:
                    dedup[link] = article
            if len(dedup) >= max_items:
                break

        if dedup:
            break

    return list(dedup.values())[:max_items]


def _fetch_market_fallback_news(max_items: int, locale: str = "en") -> list[dict]:
    api_key = os.getenv("GNEWS_API_KEY", "").strip()
    if not api_key:
        return []

    language = "pt" if locale.lower().startswith("pt") else "en"
    endpoint = "https://gnews.io/api/v4/search"
    from_date = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    query = "stock market OR investing OR finance"
    params = {
        "q": query,
        "lang": language,
        "sortby": "publishedAt",
        "max": max(1, min(max_items, 10)),
        "from": from_date,
        "apikey": api_key,
    }

    try:
        payload = _http_get_json(f"{endpoint}?{urlencode(params)}")
    except Exception:
        return []

    rows = payload.get("articles", []) if isinstance(payload, dict) else []
    items: list[dict] = []
    for row in rows:
        article = _normalize_news_item(
            provider="gnews",
            symbol="MKT",
            asset_name="Market",
            title=row.get("title"),
            description=row.get("description"),
            url=row.get("url"),
            published_at=row.get("publishedAt"),
            source=(row.get("source") or {}).get("name"),
            image=row.get("image"),
        )
        if article:
            items.append(article)
    return items[:max_items]


def _fetch_market_headline(locale: str = "en") -> dict | None:
    direct = _fetch_market_fallback_news(1, locale=locale)
    if direct:
        return direct[0]

    # If market-wide providers are empty, derive a headline from featured assets.
    # Stop at the first asset that returns any result to avoid slow cascades.
    featured_assets = [
        ("PETR4", "B3", "Petrobras PN"),
        ("AAPL", "NASDAQ", "Apple Inc."),
        ("NVDA", "NASDAQ", "NVIDIA Corp."),
        ("BTC", "CRYPTO", "Bitcoin"),
        ("ETH", "CRYPTO", "Ethereum"),
    ]

    for symbol, exchange, name in featured_assets:
        items = _collect_asset_news(symbol, exchange, name, 1, locale=locale)
        if items:
            return items[0]

    return None


def _collect_asset_news(symbol: str, exchange: str, asset_name: str, limit: int, locale: str = "en") -> list[dict]:
    has_finnhub = bool(os.getenv("FINNHUB_API_KEY", "").strip())
    has_alpha = bool(os.getenv("ALPHAVANTAGE_API_KEY", "").strip())
    has_gnews = bool(os.getenv("GNEWS_API_KEY", "").strip())

    provider_chain = [
        ("yfinance", lambda remaining: _fetch_yfinance_articles(symbol, exchange, asset_name, remaining)),
        ("finnhub", lambda remaining: _fetch_finnhub_articles(symbol, exchange, asset_name, remaining)),
        ("alphavantage", lambda remaining: _fetch_alpha_vantage_articles(symbol, asset_name, remaining)),
        ("gnews", lambda remaining: _fetch_gnews_articles(symbol, asset_name, remaining, locale=locale)),
    ]

    dedup: dict[str, dict] = {}
    for provider_name, provider_fetch in provider_chain:
        if provider_name == "finnhub" and not has_finnhub:
            continue
        if provider_name == "alphavantage" and not has_alpha:
            continue
        if provider_name == "gnews" and not has_gnews:
            continue

        remaining = limit - len(dedup)
        if remaining <= 0:
            break

        try:
            provider_items = provider_fetch(remaining)
        except Exception as e:
            logger.warning(f"News fetch failed for {symbol} on {provider_name}: {e}")
            continue

        for article in provider_items:
            url = str(article.get("url", "")).strip()
            if url and url not in dedup:
                dedup[url] = article

    if not dedup and has_gnews:
        for article in _fetch_market_fallback_news(limit, locale=locale):
            url = str(article.get("url", "")).strip()
            if url and url not in dedup:
                dedup[url] = article

    return sorted(
        dedup.values(),
        key=lambda row: _safe_parse_datetime(str(row.get("published_at") or "")),
        reverse=True,
    )[:limit]


class SupabaseJWTMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: FastAPI,
        supabase_url: str | None = None,
        excluded_paths: set[str] | None = None,
    ) -> None:
        super().__init__(app)
        self.excluded_paths = excluded_paths or {"/health", "/docs", "/redoc", "/openapi.json"}
        self.supabase_url = (supabase_url or os.getenv("SUPABASE_URL", "")).rstrip("/") if supabase_url else os.getenv("SUPABASE_URL", "").rstrip("/")
        self.jwt_audience = os.getenv("SUPABASE_JWT_AUDIENCE", "authenticated")
        self.issuer = f"{self.supabase_url}/auth/v1" if self.supabase_url else None
        self.jwks_client = None
        
        if JWT_AVAILABLE and self.supabase_url:
            try:
                self.jwks_client = PyJWKClient(f"{self.issuer}/.well-known/jwks.json")
                logger.info(f"JWT verification enabled for {self.supabase_url}")
            except Exception as e:
                logger.warning(f"Failed to initialize JWKS client: {e}. Using fallback mode.")

    async def dispatch(self, request: Request, call_next: Callable):
        # Always let CORS preflight (OPTIONS) pass through
        if request.method == "OPTIONS":
            return await call_next(request)

        if request.url.path in self.excluded_paths:
            return await call_next(request)

        authorization = request.headers.get("Authorization", "")
        if not authorization.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "Missing Bearer token"})

        token = authorization.replace("Bearer ", "", 1).strip()
        if not token:
            return JSONResponse(status_code=401, content={"detail": "Empty token"})

        # Try real JWT verification if available
        if JWT_AVAILABLE and self.jwks_client:
            try:
                signing_key = self.jwks_client.get_signing_key_from_jwt(token)
                claims = decode(
                    token,
                    signing_key.key,
                    algorithms=["RS256", "ES256"],
                    audience=self.jwt_audience,
                    issuer=self.issuer,
                )
                request.state.user = {
                    "sub": claims.get("sub"),
                    "role": claims.get("role", "authenticated"),
                    "email": claims.get("email"),
                    "verified_jwt": True,
                }
                logger.info(f"JWT verified for user {claims.get('sub')}")
                return await call_next(request)
            except (InvalidTokenError, Exception) as e:
                # In dev: if JWT validation fails, fall through to fallback mode
                logger.warning(f"JWT verification failed ({type(e).__name__}): {e}. Using fallback.")
        
        # Fallback: accept token without verification (dev mode)
        # Use a fixed UUID for dev mode to pass UUID validation in endpoints
        DEV_USER_UUID = "00000000-0000-0000-0000-000000000001"
        request.state.user = {
            "sub": DEV_USER_UUID,
            "role": "authenticated",
            "token_preview": f"{token[:8]}...",
            "verified_jwt": False,
            "dev_mode": True,
        }
        logger.info(f"Token accepted in fallback mode (dev)")
        return await call_next(request)


app = FastAPI(title="Invest Explorer API", version="0.1.0")

allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
supabase_url = os.getenv("SUPABASE_URL", "")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in allowed_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SupabaseJWTMiddleware, supabase_url=supabase_url)


@app.on_event("startup")
async def on_startup() -> None:
    global _scheduler_task
    if os.getenv("ENABLE_DAILY_REFRESH_SCHEDULER", "true").lower() in {"1", "true", "yes", "on"}:
        if _scheduler_task is None:
            _scheduler_task = asyncio.create_task(_scheduler_loop())


@app.on_event("shutdown")
async def on_shutdown() -> None:
    global _scheduler_task
    if _scheduler_task is not None:
        _scheduler_task.cancel()
        _scheduler_task = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "invest-explorer-api"}


@app.get("/scheduler/status")
def scheduler_status() -> dict:
    enabled = os.getenv("ENABLE_DAILY_REFRESH_SCHEDULER", "true").lower() in {"1", "true", "yes", "on"}
    brt_times = _parse_scheduler_brt_times(os.getenv("SCHEDULER_BRT_TIMES", "08:00,14:00,20:00"))
    now_utc = datetime.now(timezone.utc)
    next_run_utc = _next_run_at_utc(now_utc, brt_times)
    admin = _get_supabase_admin()
    history = _get_scheduler_runs(admin, limit=1) if admin else []
    last_run = history[0] if history else None
    return {
        "enabled": enabled,
        "timezone": "America/Sao_Paulo",
        "slots_brt": [f"{hour:02d}:{minute:02d}" for hour, minute in brt_times],
        "now_brt": now_utc.astimezone(BRT_TZ).isoformat(timespec="seconds"),
        "next_run_brt": next_run_utc.astimezone(BRT_TZ).isoformat(timespec="seconds"),
        "next_run_utc": next_run_utc.isoformat(timespec="seconds"),
        "task_running": _scheduler_task is not None and not _scheduler_task.done(),
        "last_run": last_run,
    }


@app.get("/scheduler/history")
def scheduler_history(limit: int = Query(10, ge=1, le=100)) -> dict:
    admin = _get_supabase_admin()
    if not admin:
        return {
            "items": [],
            "message": "Supabase admin not configured",
        }

    items = _get_scheduler_runs(admin, limit=limit)
    return {
        "items": items,
        "count": len(items),
    }


@app.post("/refresh")
def refresh_snapshot(request: Request) -> dict:
    try:
        payload = build_live_snapshot_payload()
        user = getattr(request.state, "user", None) or {}
        owner_id = user.get("sub")
        snapshot_id = f"snapshot_{payload.get('updated_at', 'unknown')}"

        admin = _get_supabase_admin()
        if admin:
            try:
                _persist_exchange_rates(admin)
            except Exception as e:
                logger.warning(f"Failed to persist exchange rates in Supabase: {e}")

        if admin and _is_valid_uuid(owner_id):
            try:
                _upsert_curated_assets(admin)
                persisted_id = _persist_snapshot(admin, owner_id, payload)
                if persisted_id:
                    snapshot_id = persisted_id
                _persist_price_history(admin, owner_id, payload, persisted_id)
            except Exception as e:
                logger.warning(f"Failed to persist snapshot in Supabase: {e}")

        return {
            "status": "accepted",
            "message": "Snapshot refreshed with live/fallback prices and BRL conversion.",
            "requested_by": user,
            "snapshot_id": snapshot_id,
            "snapshot_asset_count": len(CURATED_ASSETS),
            "live_asset_count": payload.get("live_asset_count", 0),
            "fallback_asset_count": payload.get("fallback_asset_count", 0),
            "data": payload,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to refresh snapshot: {str(e)}",
            "requested_by": getattr(request.state, "user", None),
        }


@app.get("/watchlist")
def get_watchlist(request: Request) -> dict:
    user = getattr(request.state, "user", None) or {}
    owner_id = user.get("sub")

    admin = _get_supabase_admin()
    if not admin or not _is_valid_uuid(owner_id):
        return {
            "read_only": True,
            "owner": user,
            "watchlist": {"id": "default", "name": "Default", "is_default": True},
            "items": [],
        }

    try:
        _upsert_curated_assets(admin)
        watchlist = _ensure_default_watchlist(admin, owner_id)

        items_query = (
            admin.table("watchlist_items")
            .select("id,asset_id,notes,created_at")
            .eq("watchlist_id", watchlist["id"])
            .order("created_at", desc=False)
            .execute()
        )
        watchlist_items = items_query.data or []

        asset_ids = [item.get("asset_id") for item in watchlist_items if item.get("asset_id")]
        assets_by_id: dict[str, dict] = {}
        if asset_ids:
            assets_query = (
                admin.table("assets")
                .select("id,name,symbol,exchange,currency,asset_class,country_code")
                .in_("id", asset_ids)
                .execute()
            )
            for asset in assets_query.data or []:
                assets_by_id[asset["id"]] = asset

        response_items = []
        for item in watchlist_items:
            asset = assets_by_id.get(item.get("asset_id"))
            if not asset:
                continue
            response_items.append(
                {
                    "id": item.get("id"),
                    "notes": item.get("notes"),
                    "created_at": item.get("created_at"),
                    "asset": asset,
                    "display": f"{asset['name']} ({asset['symbol']}) • {asset['exchange']}",
                }
            )

        return {
            "read_only": False,
            "owner": user,
            "watchlist": {
                "id": watchlist.get("id"),
                "name": watchlist.get("name", "Default"),
                "is_default": watchlist.get("is_default", True),
            },
            "items": response_items,
        }
    except Exception as e:
        logger.warning(f"Failed to fetch watchlist from Supabase: {e}")
        return {
            "read_only": True,
            "owner": user,
            "watchlist": {"id": "default", "name": "Default", "is_default": True},
            "items": [],
        }


@app.post("/watchlist/items")
def add_watchlist_item(payload: WatchlistItemPayload, request: Request):
    user = getattr(request.state, "user", None) or {}
    owner_id = user.get("sub")
    admin = _get_supabase_admin()
    if not admin or not _is_valid_uuid(owner_id):
        return JSONResponse(status_code=400, content={"detail": "Watchlist write requires a verified user session"})

    try:
        symbol = payload.symbol.strip().upper()
        exchange = payload.exchange.strip().upper()
        _upsert_curated_assets(admin)
        watchlist = _ensure_default_watchlist(admin, owner_id)

        asset_id = _resolve_asset_id(admin, symbol, exchange)
        if not asset_id:
            return JSONResponse(status_code=404, content={"detail": f"Asset {symbol}/{exchange} not found"})

        admin.table("watchlist_items").upsert(
            {
                "watchlist_id": watchlist["id"],
                "asset_id": asset_id,
                "notes": payload.notes,
            },
            on_conflict="watchlist_id,asset_id",
        ).execute()
    except Exception as e:
        logger.warning(f"Failed to add watchlist item: {e}")
        return JSONResponse(status_code=500, content={"detail": "Failed to add item to watchlist"})

    return get_watchlist(request)


@app.delete("/watchlist/items")
def remove_watchlist_item(payload: WatchlistItemPayload, request: Request):
    user = getattr(request.state, "user", None) or {}
    owner_id = user.get("sub")
    admin = _get_supabase_admin()
    if not admin or not _is_valid_uuid(owner_id):
        return JSONResponse(status_code=400, content={"detail": "Watchlist write requires a verified user session"})

    try:
        symbol = payload.symbol.strip().upper()
        exchange = payload.exchange.strip().upper()
        watchlist = _ensure_default_watchlist(admin, owner_id)
        asset_id = _resolve_asset_id(admin, symbol, exchange)
        if asset_id:
            (
                admin.table("watchlist_items")
                .delete()
                .eq("watchlist_id", watchlist["id"])
                .eq("asset_id", asset_id)
                .execute()
            )
    except Exception as e:
        logger.warning(f"Failed to remove watchlist item: {e}")
        return JSONResponse(status_code=500, content={"detail": "Failed to remove item from watchlist"})

    return get_watchlist(request)


@app.get("/price-history")
def get_price_history(
    request: Request,
    symbol: str = Query(...),
    exchange: str = Query(...),
    period: str = Query("1y"),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    limit: int = Query(5000, ge=1, le=20000),
) -> dict:
    user = getattr(request.state, "user", None) or {}
    owner_id = user.get("sub")
    admin = _get_supabase_admin()
    if not admin or not _is_valid_uuid(owner_id):
        return {
            "read_only": True,
            "owner": user,
            "asset": {"symbol": symbol.upper(), "exchange": exchange.upper()},
            "period": period,
            "points": [],
        }

    symbol_norm = symbol.strip().upper()
    exchange_norm = exchange.strip().upper()

    def _parse_query_datetime(value: str | None) -> datetime | None:
        if not value:
            return None
        raw = value.strip()
        if not raw:
            return None

        normalized = raw.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            try:
                parsed = datetime.strptime(raw, "%Y-%m-%d")
            except ValueError:
                return None

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        else:
            parsed = parsed.astimezone(timezone.utc)
        return parsed

    try:
        asset_row = (
            admin.table("assets")
            .select("id,name,symbol,exchange,currency")
            .eq("symbol", symbol_norm)
            .eq("exchange", exchange_norm)
            .limit(1)
            .execute()
            .data
        )
        if not asset_row:
            return JSONResponse(status_code=404, content={"detail": f"Asset {symbol_norm}/{exchange_norm} not found"})

        asset = asset_row[0]
        parsed_start = _parse_query_datetime(start_date)
        parsed_end = _parse_query_datetime(end_date)
        if start_date and not parsed_start:
            return JSONResponse(status_code=400, content={"detail": "Invalid start_date. Use YYYY-MM-DD or ISO datetime."})
        if end_date and not parsed_end:
            return JSONResponse(status_code=400, content={"detail": "Invalid end_date. Use YYYY-MM-DD or ISO datetime."})
        if parsed_start and parsed_end and parsed_start > parsed_end:
            return JSONResponse(status_code=400, content={"detail": "start_date must be <= end_date."})

        effective_period = period
        if parsed_start or parsed_end:
            effective_period = "custom"

        lower_bound_iso = parsed_start.isoformat() if parsed_start else _period_to_start(period).isoformat()
        upper_bound_iso = parsed_end.isoformat() if parsed_end else None

        def _build_history_query(include_owner: bool):
            query = (
                admin.table("price_history")
                .select("collected_at,price,valuation_brl,currency,fx_to_brl,data_quality")
                .eq("asset_id", asset["id"])
                .gte("collected_at", lower_bound_iso)
            )
            if upper_bound_iso:
                query = query.lte("collected_at", upper_bound_iso)
            if include_owner:
                query = query.eq("owner_id", owner_id)
            return query

        def _fetch_history_rows(include_owner: bool, desc: bool, max_rows: int) -> list[dict]:
            rows: list[dict] = []
            page_size = 1000
            offset = 0
            while len(rows) < max_rows:
                batch = (
                    _build_history_query(include_owner=include_owner)
                    .order("collected_at", desc=desc)
                    .range(offset, offset + page_size - 1)
                    .execute()
                    .data
                    or []
                )
                if not batch:
                    break
                rows.extend(batch)
                if len(batch) < page_size:
                    break
                offset += page_size

            return rows[:max_rows]

        owner_rows = _fetch_history_rows(include_owner=True, desc=False, max_rows=limit)

        rows = owner_rows
        history_source = "owner"

        if parsed_end is None:
            latest_owner = _safe_parse_datetime(str(owner_rows[-1].get("collected_at") or "")) if owner_rows else datetime.min.replace(tzinfo=timezone.utc)
            first_owner = _safe_parse_datetime(str(owner_rows[0].get("collected_at") or "")) if owner_rows else datetime.max.replace(tzinfo=timezone.utc)
            shared_desc = _fetch_history_rows(
                include_owner=False,
                desc=True,
                max_rows=min(50000, max(limit * 8, 5000)),
            )
            shared_rows = _unique_points_from_desc(shared_desc, limit)
            latest_shared = _safe_parse_datetime(str(shared_rows[-1].get("collected_at") or "")) if shared_rows else datetime.min.replace(tzinfo=timezone.utc)
            first_shared = _safe_parse_datetime(str(shared_rows[0].get("collected_at") or "")) if shared_rows else datetime.max.replace(tzinfo=timezone.utc)

            owner_is_stale = latest_shared > latest_owner + timedelta(hours=24)
            owner_has_shorter_coverage = first_shared + timedelta(days=30) < first_owner

            if shared_rows and (not owner_rows or owner_is_stale or owner_has_shorter_coverage):
                rows = shared_rows
                history_source = "shared_fallback"

        return {
            "read_only": False,
            "owner": user,
            "asset": asset,
            "period": effective_period,
            "history_source": history_source,
            "points": rows,
        }
    except Exception as e:
        logger.warning(f"Failed to fetch price history: {e}")
        return JSONResponse(status_code=500, content={"detail": "Failed to fetch price history"})


@app.get("/market/overview")
def get_market_overview(
    request: Request,
    locale: str = Query("en"),
) -> dict:
    user = getattr(request.state, "user", None) or {}
    try:
        admin = _get_supabase_admin()
        payload = build_live_snapshot_payload()
        assets = payload.get("assets", []) if isinstance(payload, dict) else []
        featured_symbols = ["PETR4", "AAPL", "NVDA", "BTC", "ETH"]
        featured_assets = [asset for asset in assets if str(asset.get("symbol", "")).upper() in featured_symbols]
        featured_assets = sorted(featured_assets, key=lambda asset: featured_symbols.index(str(asset.get("symbol", "")).upper()))
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_fetch_market_headline, locale)
                headline = future.result(timeout=8)
        except (FuturesTimeoutError, Exception):
            headline = None
        latest_data_at = _latest_data_updated_at(admin) or payload.get("updated_at")
        return {
            "read_only": False,
            "owner": user,
            "summary": {
                "asset_count": payload.get("asset_count", 0),
                "live_asset_count": payload.get("live_asset_count", 0),
                "fallback_asset_count": payload.get("fallback_asset_count", 0),
                "updated_at": payload.get("updated_at"),
                "data_updated_at": latest_data_at,
            },
            "featured_assets": featured_assets,
            "currency_rates": build_currency_rates_payload(),
            "headline": headline,
        }
    except Exception as e:
        logger.warning(f"Failed to build market overview: {e}")
        return JSONResponse(status_code=500, content={"detail": "Failed to build market overview"})


@app.get("/asset/news")
def get_asset_news(
    request: Request,
    symbol: str = Query(...),
    exchange: str = Query(...),
    locale: str = Query("en"),
    limit: int = Query(8, ge=1, le=20),
) -> dict:
    user = getattr(request.state, "user", None) or {}
    owner_id = user.get("sub")
    admin = _get_supabase_admin()

    if not admin or not _is_valid_uuid(owner_id):
        return {
            "read_only": True,
            "owner": user,
            "source": "none",
            "items": [],
            "message": "News requires a verified user session and configured Supabase.",
        }

    symbol_norm = symbol.strip().upper()
    exchange_norm = exchange.strip().upper()
    try:
        asset_row = (
            admin.table("assets")
            .select("name,symbol,exchange")
            .eq("symbol", symbol_norm)
            .eq("exchange", exchange_norm)
            .limit(1)
            .execute()
            .data
        )
        asset_name = asset_row[0].get("name") if asset_row else symbol_norm
        items = _collect_asset_news(symbol_norm, exchange_norm, str(asset_name), limit, locale=locale)

        if not items:
            items = _fetch_market_fallback_news(limit, locale=locale)
            if items:
                return {
                    "read_only": False,
                    "owner": user,
                    "source": "market_fallback",
                    "items": items,
                    "message": "No asset-specific news found. Showing general market news.",
                }

        return {
            "read_only": False,
            "owner": user,
            "source": "yfinance|finnhub|alphavantage|gnews",
            "items": items,
            "message": "ok" if items else "No news available right now.",
        }
    except Exception as e:
        logger.warning(f"Failed to fetch asset news: {e}")
        return JSONResponse(status_code=500, content={"detail": "Failed to fetch asset news"})


@app.get("/watchlist/news")
def get_watchlist_news(
    request: Request,
    limit: int = Query(30, ge=1, le=100),
    per_asset: int = Query(5, ge=1, le=10),
    locale: str = Query("en"),
) -> dict:
    user = getattr(request.state, "user", None) or {}
    owner_id = user.get("sub")
    admin = _get_supabase_admin()

    if not admin or not _is_valid_uuid(owner_id):
        return {
            "read_only": True,
            "owner": user,
            "source": "gnews",
            "items": [],
            "message": "News requires a verified user session and configured Supabase.",
        }

    has_finnhub = bool(os.getenv("FINNHUB_API_KEY", "").strip())
    has_alpha = bool(os.getenv("ALPHAVANTAGE_API_KEY", "").strip())
    has_gnews = bool(os.getenv("GNEWS_API_KEY", "").strip())

    if not any([has_finnhub, has_alpha, has_gnews]):
        return {
            "read_only": False,
            "owner": user,
            "source": "none",
            "items": [],
            "message": "Set at least one key: FINNHUB_API_KEY, ALPHAVANTAGE_API_KEY, or GNEWS_API_KEY.",
        }

    try:
        watchlist_payload = get_watchlist(request)
        raw_items = watchlist_payload.get("items", []) if isinstance(watchlist_payload, dict) else []
        
        # In dev mode (when JWT is not verified), use curated assets if watchlist is empty
        is_dev_mode = not user.get("verified_jwt", False)
        if not raw_items and is_dev_mode:
            logger.info("Dev mode: using curated assets for news since watchlist is empty")
            raw_items = [
                {
                    "asset": {
                        "name": asset.name,
                        "symbol": asset.symbol,
                        "exchange": asset.exchange,
                        "currency": asset.currency,
                    }
                }
                for asset in CURATED_ASSETS[:10]  # Use first 10 curated assets
            ]
        
        candidates = raw_items[:15]

        dedup: dict[str, dict] = {}
        for item in candidates:
            asset = item.get("asset", {}) if isinstance(item, dict) else {}
            symbol = str(asset.get("symbol", "")).strip().upper()
            exchange = str(asset.get("exchange", "")).strip().upper()
            name = str(asset.get("name", "")).strip()
            if not symbol:
                continue

            for article in _collect_asset_news(symbol, exchange, name, per_asset, locale=locale):
                url = str(article.get("url", "")).strip()
                if url and url not in dedup:
                    dedup[url] = article

        items = sorted(
            dedup.values(),
            key=lambda row: _safe_parse_datetime(str(row.get("published_at") or "")),
            reverse=True,
        )[:limit]

        return {
            "read_only": False,
            "owner": user,
            "source": "finnhub|alphavantage|gnews",
            "items": items,
            "message": "ok",
        }
    except Exception as e:
        logger.warning(f"Failed to fetch watchlist news: {e}")
        return JSONResponse(status_code=500, content={"detail": "Failed to fetch watchlist news"})

