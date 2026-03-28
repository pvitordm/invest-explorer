import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from datetime import datetime, timezone, timedelta

# Load env
load_dotenv(dotenv_path=Path(r'd:\invest-explorer\apps\api\.env'), override=True)

sys.path.insert(0, r'd:\invest-explorer\apps\api')
from main import _normalize_news_item

api_key = os.getenv("GNEWS_API_KEY", "").strip()
print(f"API Key loaded: {bool(api_key)}")

endpoint = "https://gnews.io/api/v4/search"
from_date = (datetime.now(timezone.utc) - timedelta(hours=72)).strftime("%Y-%m-%dT%H:%M:%SZ")
params = {
    "q": '"AAPL" OR "Apple Inc."',
    "lang": "en",
    "sortby": "publishedAt",
    "max": max(1, min(3, 10)),
    "from": from_date,
    "apikey": api_key,
}

url = f"{endpoint}?{urlencode(params)}"
print(f"URL: {url[:80]}...")

try:
    req = Request(url, headers={"User-Agent": "invest-explorer/1.0"})
    with urlopen(req, timeout=12) as response:
        payload = json.loads(response.read().decode("utf-8"))
        print(f"\nResponse OK")
        print(f"  Type: {type(payload)}")
        print(f"  Keys: {list(payload.keys()) if isinstance(payload, dict) else 'N/A'}")
        
        rows = payload.get("articles", []) if isinstance(payload, dict) else []
        print(f"  Articles returned: {len(rows)}")
        
        # Now test normalization
        items = []
        for row in rows:
            article = _normalize_news_item(
                provider="gnews",
                symbol="AAPL",
                asset_name="Apple Inc.",
                title=row.get("title"),
                description=row.get("description"),
                url=row.get("url"),
                published_at=row.get("publishedAt"),
                source=(row.get("source") or {}).get("name"),
                image=row.get("image"),
            )
            print(f"\n  Article: {row.get('title')[:50]}...")
            print(f"    Has URL: {bool(row.get('url'))}")
            print(f"    Normalized: {bool(article)}")
            if article:
                items.append(article)
        
        print(f"\n  Final items: {len(items)}")
        
except Exception as e:
    import traceback
    print(f"Error: {e}")
    traceback.print_exc()
