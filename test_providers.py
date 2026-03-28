import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load env from apps/api/.env
load_dotenv(dotenv_path=Path(r'd:\invest-explorer\apps\api\.env'), override=True)

sys.path.insert(0, r'd:\invest-explorer\apps\api')

from main import _fetch_finnhub_articles, _fetch_alpha_vantage_articles, _fetch_gnews_articles

# Test each provider
print("=== Testing News Providers ===\n")

# Test Finnhub
print("1. Finnhub (AAPL):")
try:
    result = _fetch_finnhub_articles("AAPL", "NASDAQ", "Apple Inc.", 3)
    print(f"   ✓ Got {len(result)} articles")
    if result:
        print(f"   First: {result[0].get('title', 'No title')[:60]}...")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test Alpha Vantage
print("\n2. Alpha Vantage (AAPL):")
try:
    result = _fetch_alpha_vantage_articles("AAPL", "Apple Inc.", 3)
    print(f"   ✓ Got {len(result)} articles")
    if result:
        print(f"   First: {result[0].get('title', 'No title')[:60]}...")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test GNews
print("\n3. GNews (Apple):")
try:
    result = _fetch_gnews_articles("AAPL", "Apple Inc.", 3, locale="en")
    print(f"   ✓ Got {len(result)} articles")
    if result:
        print(f"   First: {result[0].get('title', 'No title')[:60]}...")
except Exception as e:
    print(f"   ✗ Error: {e}")

print("\n=== API Keys Status ===")
print(f"FINNHUB_API_KEY: {'✓ Set' if os.getenv('FINNHUB_API_KEY') else '✗ Not set'}")
print(f"ALPHAVANTAGE_API_KEY: {'✓ Set' if os.getenv('ALPHAVANTAGE_API_KEY') else '✗ Not set'}")
print(f"GNEWS_API_KEY: {'✓ Set' if os.getenv('GNEWS_API_KEY') else '✗ Not set'}")
