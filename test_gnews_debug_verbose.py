import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import logging

# Enable logging
logging.basicConfig(level=logging.DEBUG)

# Load env from apps/api/.env
load_dotenv(dotenv_path=Path(r'd:\invest-explorer\apps\api\.env'), override=True)

sys.path.insert(0, r'd:\invest-explorer\apps\api')

from main import _fetch_gnews_articles

# Test GNews with debug
print("Testing GNews with detailed output...\n")

# Set a logger to see what's happening
logger = logging.getLogger('main')

result = _fetch_gnews_articles(symbol="AAPL", asset_name="Apple Inc.", max_items=3, locale="en")
print(f"Result: {len(result)} articles")

if result:
    for r in result:
        print(f"  - {r.get('title')[:60]}...")
else:
    print("  No articles returned")
