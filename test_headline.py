#!/usr/bin/env python3
"""Test the _fetch_market_headline function directly."""

import sys
import os
from pathlib import Path

# Add the api directory to path
sys.path.insert(0, str(Path(__file__).parent / "apps" / "api"))

# Load .env
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / "apps" / "api" / ".env", override=True)

try:
    # Try importing and running the function
    from main import _fetch_market_headline, _collect_asset_news
    print("✓ Imported functions successfully")
    
    print("\n1. Testing _fetch_market_headline directly...")
    result = _fetch_market_headline(locale="pt-BR")
    print(f"   Result: {result is not None}")
    if result:
        print(f"   - Title: {result.get('title', 'N/A')[:100]}")
        print(f"   - Source: {result.get('source', 'N/A')}")
        print(f"   - URL: {result.get('url', 'N/A')[:100]}")
    else:
        print("   - No headline available (None returned)")
    
    print("\n2. Testing _collect_asset_news for PETR4...")
    items = _collect_asset_news("PETR4", "B3", "Petrobras PN", 2, locale="pt-BR")
    print(f"   Found {len(items)} items")
    for idx, item in enumerate(items[:2]):
        print(f"   Item {idx+1}:")
        print(f"     - Title: {item.get('title', 'N/A')[:80]}")
        print(f"     - Source: {item.get('source', 'N/A')}")
        
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
