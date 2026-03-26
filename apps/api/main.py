import os
from functools import lru_cache
from typing import Any, Callable

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from jwt import PyJWKClient, decode
from jwt.exceptions import InvalidTokenError
from market_data import CURATED_ASSETS, build_live_snapshot_payload
from supabase import Client, create_client
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

load_dotenv()


class SupabaseJWTMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: FastAPI,
        supabase_url: str,
        audience: str | None,
        excluded_paths: set[str] | None = None,
    ) -> None:
        super().__init__(app)
        self.excluded_paths = excluded_paths or {"/health", "/docs", "/redoc", "/openapi.json"}
        self.supabase_url = supabase_url.rstrip("/")
        self.issuer = f"{self.supabase_url}/auth/v1"
        self.audience = audience
        self.jwks_client = (
            PyJWKClient(f"{self.issuer}/.well-known/jwks.json") if self.supabase_url else None
        )

    async def dispatch(self, request: Request, call_next: Callable):
        if request.url.path in self.excluded_paths:
            return await call_next(request)

        if not self.supabase_url:
            return JSONResponse(
                status_code=500,
                content={"detail": "SUPABASE_URL is not configured"},
            )

        authorization = request.headers.get("Authorization", "")
        if not authorization.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing Bearer token"},
            )

        token = authorization.replace("Bearer ", "", 1).strip()
        if not token:
            return JSONResponse(
                status_code=401,
                content={"detail": "Empty token"},
            )

        try:
            if self.jwks_client is None:
                return JSONResponse(status_code=500, content={"detail": "JWKS client not initialized"})
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            verify_options = {"verify_aud": bool(self.audience)}
            claims = decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=self.issuer,
                options=verify_options,
            )
        except InvalidTokenError:
            return JSONResponse(status_code=401, content={"detail": "Invalid token"})
        except Exception:
            return JSONResponse(status_code=401, content={"detail": "Token verification failed"})

        request.state.user = {
            "sub": claims.get("sub"),
            "role": claims.get("role"),
            "email": claims.get("email"),
        }

        return await call_next(request)


app = FastAPI(title="Invest Explorer API", version="0.1.0")

supabase_url = os.getenv("SUPABASE_URL", "")
supabase_service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
supabase_jwt_audience = os.getenv("SUPABASE_JWT_AUDIENCE", "authenticated")


@lru_cache
def get_supabase_admin_client() -> Client:
    if not supabase_url or not supabase_service_role_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required")
    return create_client(supabase_url, supabase_service_role_key)


def get_authenticated_user_id(request: Request) -> str:
    user = getattr(request.state, "user", None) or {}
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return str(user_id)


def get_or_create_default_watchlist(client: Client, user_id: str) -> dict[str, Any]:
    result = (
        client.table("watchlists")
        .select("id, name, is_default")
        .eq("owner_id", user_id)
        .eq("is_default", True)
        .limit(1)
        .execute()
    )
    if result.data:
        return result.data[0]

    created = (
        client.table("watchlists")
        .insert({"owner_id": user_id, "name": "Default", "is_default": True})
        .execute()
    )
    if not created.data:
        raise HTTPException(status_code=500, detail="Failed to create default watchlist")
    return created.data[0]


app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in allowed_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    SupabaseJWTMiddleware,
    supabase_url=supabase_url,
    audience=supabase_jwt_audience,
    excluded_paths={"/health", "/docs", "/redoc", "/openapi.json"},
)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "invest-explorer-api",
        "supabase_url_configured": bool(os.getenv("SUPABASE_URL")),
        "jwt_audience": supabase_jwt_audience,
    }


@app.post("/refresh")
def refresh_snapshot(request: Request) -> dict:
    user_id = get_authenticated_user_id(request)

    try:
        client = get_supabase_admin_client()
        payload = build_live_snapshot_payload()
        insert_result = (
            client.table("snapshots")
            .insert(
                {
                    "owner_id": user_id,
                    "snapshot_type": "manual_refresh",
                    "data": payload,
                }
            )
            .execute()
        )
        snapshot_row = insert_result.data[0] if insert_result.data else {}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Refresh failed: {exc}") from exc

    return {
        "status": "accepted",
        "message": "Snapshot refreshed with live/fallback prices and BRL conversion.",
        "requested_by": request.state.user,
        "snapshot_id": snapshot_row.get("id"),
        "snapshot_asset_count": len(CURATED_ASSETS),
        "live_asset_count": payload.get("live_asset_count"),
        "fallback_asset_count": payload.get("fallback_asset_count"),
    }


@app.get("/watchlist")
def get_watchlist(request: Request) -> dict:
    user_id = get_authenticated_user_id(request)

    try:
        client = get_supabase_admin_client()
        watchlist = get_or_create_default_watchlist(client, user_id)
        rows = (
            client.table("watchlist_items")
            .select(
                "id, notes, created_at, asset:assets(id, name, symbol, exchange, currency, asset_class, country_code)"
            )
            .eq("watchlist_id", watchlist["id"])
            .order("created_at")
            .execute()
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load watchlist: {exc}") from exc

    items = []
    for row in rows.data or []:
        asset = row.get("asset") or {}
        display = f"{asset.get('name', '-') } {asset.get('symbol', '-') } • {asset.get('exchange', '-') } • {asset.get('currency', '-') }"
        items.append(
            {
                "id": row.get("id"),
                "notes": row.get("notes"),
                "created_at": row.get("created_at"),
                "asset": asset,
                "display": display,
            }
        )

    return {
        "read_only": True,
        "owner": request.state.user,
        "watchlist": watchlist,
        "items": items,
    }
