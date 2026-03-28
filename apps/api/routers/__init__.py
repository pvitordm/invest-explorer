"""
API Routers - Modular endpoint organization
"""

from .market import router as market_router
from .watchlist import router as watchlist_router
from .news import router as news_router

__all__ = ["market_router", "watchlist_router", "news_router"]
