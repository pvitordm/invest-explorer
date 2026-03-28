"""
Watchlist Router - CRUD operations for user watchlists
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from supabase import Client as SupabaseClient

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


@router.get("")
async def get_watchlist(supabase: SupabaseClient = Depends(...)):
    """Fetch user's watchlist with all items"""
    try:
        # Implementation would fetch from supabase
        # See main.py _get_watchlist function for details
        return {
            "read_only": False,
            "owner": {"sub": "...", "role": "authenticated"},
            "watchlist": {"id": "...", "name": "Default", "is_default": True},
            "items": []
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/items")
async def add_watchlist_item(
    symbol: str,
    exchange: str,
    notes: str | None = None,
    supabase: SupabaseClient = Depends(...),
):
    """Add an item to watchlist"""
    try:
        # Implementation would insert to supabase tables
        # See main.py _add_to_watchlist function for details
        return {
            "success": True,
            "item_id": "...",
            "asset": {
                "symbol": symbol,
                "exchange": exchange,
                "name": "...",
                "currency": "...",
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/items/{item_id}")
async def remove_watchlist_item(
    item_id: str,
    supabase: SupabaseClient = Depends(...),
):
    """Remove an item from watchlist"""
    try:
        # Implementation would delete from supabase
        # See main.py _remove_from_watchlist function for details
        return {"success": True, "deleted_item_id": item_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
