"""
Market Router - Market data, overview, and price updates
"""

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client as SupabaseClient

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/overview")
async def get_market_overview(supabase: SupabaseClient = Depends(...)):
    """Get market overview with top performers and currencies"""
    try:
        # Implementation would build payload from market_data
        # See main.py _fetch_market_overview function for details
        return {
            "summary": {
                "asset_count": 20,
                "live_asset_count": 18,
                "fallback_asset_count": 2,
                "updated_at": "2025-03-30T14:30:00-03:00"
            },
            "featured_assets": [],
            "currency_rates": [],
            "headline": None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refresh")
async def trigger_refresh(supabase: SupabaseClient = Depends(...)):
    """Trigger full market data refresh"""
    try:
        # Implementation would call scheduler refresh
        # See main.py _trigger_refresh endpoint for details
        return {
            "success": True,
            "task_id": "...",
            "status": "triggered"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
