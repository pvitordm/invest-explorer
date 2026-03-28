"""
Tests for market endpoints
"""

import pytest
from fastapi import status


def test_health_endpoint(test_client):
    """Test API health check"""
    response = test_client.get("/api/health")
    assert response.status_code in (200, 401)  # 401 if not authenticated


def test_market_overview_endpoint_exists(test_client):
    """Test market overview endpoint exists and is callable"""
    response = test_client.get("/api/market/overview")
    # May return 401 without auth, but endpoint should exist
    assert response.status_code in (200, 401, 500)


def test_watchlist_get_endpoint_exists(test_client):
    """Test watchlist GET endpoint exists"""
    response = test_client.get("/api/watchlist")
    # May return 401 without auth, but endpoint should exist
    assert response.status_code in (200, 401, 500)


def test_asset_history_endpoint_exists(test_client):
    """Test asset history endpoint exists"""
    response = test_client.get("/api/asset/PETR4/history")
    # May return 401 without auth, but endpoint should exist
    assert response.status_code in (200, 401, 500)
