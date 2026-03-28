import json
import os
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# Load env from apps/api/.env
load_dotenv(dotenv_path=Path(r'd:\invest-explorer\apps\api\.env'), override=True)

api_key = os.getenv("GNEWS_API_KEY", "").strip()
print(f"API Key: {api_key[:20]}..." if api_key else "NO KEY")

endpoint = "https://gnews.io/api/v4/search"
from_date = (datetime.now(timezone.utc) - timedelta(hours=72)).strftime("%Y-%m-%dT%H:%M:%SZ")
params = {
    "q": 'AAPL OR "Apple Inc."',
    "lang": "en",
    "sortby": "publishedAt",
    "max": "10",
    "from": from_date,
    "apikey": api_key,
}

url = f"{endpoint}?{urlencode(params)}"
print(f"\nURL: {url[:100]}...")

try:
    req = Request(url, headers={"User-Agent": "invest-explorer/1.0"})
    with urlopen(req, timeout=12) as response:
        data = json.loads(response.read().decode("utf-8"))
        print(f"\nResponse Status: OK")
        print(f"Articles count: {len(data.get('articles', []))}")
        print(f"Response keys: {list(data.keys())}")
        if "articles" in data and data["articles"]:
            print(f"\nFirst article:")
            art = data["articles"][0]
            print(f"  Title: {art.get('title', 'N/A')[:60]}...")
except Exception as e:
    import traceback
    print(f"\nError: {e}")
    traceback.print_exc()
