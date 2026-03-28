import os
from pathlib import Path
from dotenv import load_dotenv

# Load env
load_dotenv(dotenv_path=Path(r'd:\invest-explorer\apps\api\.env'), override=True)

import sys
sys.path.insert(0, r'd:\invest-explorer\apps\api')

# Import the function
from main import _fetch_gnews_articles

# Test
print("Testing _fetch_gnews_articles...")
result = _fetch_gnews_articles(symbol="AAPL", asset_name="Apple Inc.", max_items=3, locale="en")
print(f"Result: {len(result)} items")

if result:
    for r in result[:2]:
        print(f"\n  Title: {r.get('title', 'N/A')[:60]}")
        print(f"  URL: {r.get('url', 'N/A')[:60]}")
else:
    print("Result is empty")
