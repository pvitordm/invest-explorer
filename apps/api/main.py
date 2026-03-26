import os
from typing import Callable

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from market_data import build_live_snapshot_payload, CURATED_ASSETS

load_dotenv()


class SupabaseJWTMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: FastAPI,
        excluded_paths: set[str] | None = None,
    ) -> None:
        super().__init__(app)
        self.excluded_paths = excluded_paths or {"/health", "/docs", "/redoc", "/openapi.json"}

    async def dispatch(self, request: Request, call_next: Callable):
        if request.url.path in self.excluded_paths:
            return await call_next(request)

        authorization = request.headers.get("Authorization", "")
        if not authorization.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "Missing Bearer token"})

        token = authorization.replace("Bearer ", "", 1).strip()
        if not token:
            return JSONResponse(status_code=401, content={"detail": "Empty token"})

        request.state.user = {
            "sub": "stub-user",
            "role": "authenticated",
            "token_preview": f"{token[:8]}...",
        }
        return await call_next(request)


app = FastAPI(title="Invest Explorer API", version="0.1.0")

allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in allowed_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SupabaseJWTMiddleware)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "invest-explorer-api"}


@app.post("/refresh")
def refresh_snapshot(request: Request) -> dict:
    try:
        payload = build_live_snapshot_payload()
        return {
            "status": "accepted",
            "message": "Snapshot refreshed with live/fallback prices and BRL conversion.",
            "requested_by": getattr(request.state, "user", None),
            "snapshot_id": f"snapshot_{payload.get('updated_at', 'unknown')}",
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
    return {
        "read_only": True,
        "owner": getattr(request.state, "user", None),
        "watchlist": {"id": "default", "name": "Default", "is_default": True},
        "items": [],
    }
