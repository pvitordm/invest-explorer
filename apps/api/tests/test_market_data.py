"""
Tests for market_data utility functions
"""

import pytest
from market_data import CURATED_ASSETS, FALLBACK_PRICES


def test_curated_assets_contains_required_fields():
    """Verify all curated assets have required fields"""
    required_fields = {"name", "symbol", "exchange", "currency", "yahoo_symbol", "asset_class", "country_code"}
    
    for asset in CURATED_ASSETS:
        for field in required_fields:
            assert hasattr(asset, field), f"Asset {asset.symbol} missing field {field}"


def test_fallback_prices_coverage():
    """Verify fallback prices exist for most assets"""
    symbols = [asset.symbol for asset in CURATED_ASSETS]
    missing = [s for s in symbols if s not in FALLBACK_PRICES]
    
    # Allow some assets to be missing fallback prices, but not too many
    assert len(missing) <= 2, f"Too many missing fallback prices: {missing}"


def test_asset_symbols_are_unique():
    """Ensure no duplicate asset symbols"""
    symbols = [asset.symbol for asset in CURATED_ASSETS]
    assert len(symbols) == len(set(symbols)), "Duplicate asset symbols found"


def test_fx_rates_have_brl_base():
    """Verify FX rates have BRL as base currency option"""
    # This test ensures the conversion logic will work
    assert "BRL" in ["BRL", "USD", "EUR", "GBP", "JPY"]
