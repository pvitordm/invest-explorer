import os
import logging
from typing import Callable

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from market_data import build_live_snapshot_payload, CURATED_ASSETS

try:
    from jwt import PyJWKClient, decode
    from jwt.exceptions import InvalidTokenError
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False

load_dotenv()
logger = logging.getLogger(__name__)


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
                    algorithms=["RS256"],
                    audience="authenticated",
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
                logger.debug(f"JWT verification failed ({type(e).__name__}): {e}. Using fallback.")
        
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
