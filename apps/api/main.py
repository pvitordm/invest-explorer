import os
import logging
from typing import Callable
from pathlib import Path
from uuid import UUID

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from market_data import build_live_snapshot_payload, CURATED_ASSETS
from supabase import create_client, Client

try:
    from jwt import PyJWKClient, decode
    from jwt.exceptions import InvalidTokenError
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False

load_dotenv(dotenv_path=Path(__file__).with_name(".env"), override=False)
logger = logging.getLogger(__name__)

_supabase_admin_client: Client | None = None


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

        rows.append(
            {
                "owner_id": owner_id,
                "asset_id": asset_id,
                "snapshot_id": snapshot_id,
                "price": asset.get("price"),
                "valuation_brl": asset.get("valuation_brl"),
                "currency": asset.get("currency") or "BRL",
                "fx_to_brl": asset.get("fx_to_brl"),
                "data_quality": asset.get("data_quality"),
                "collected_at": payload.get("updated_at"),
            }
        )

    if rows:
        client.table("price_history").insert(rows).execute()


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
        request.state.user = {
            "sub": "anonymous-dev",
            "role": "authenticated",
            "token_preview": f"{token[:8]}...",
            "verified_jwt": False,
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


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "invest-explorer-api"}


@app.post("/refresh")
def refresh_snapshot(request: Request) -> dict:
    try:
        payload = build_live_snapshot_payload()
        user = getattr(request.state, "user", None) or {}
        owner_id = user.get("sub")
        snapshot_id = f"snapshot_{payload.get('updated_at', 'unknown')}"

        admin = _get_supabase_admin()
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

