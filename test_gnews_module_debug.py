import os
from pathlib import Path
from urllib.parse import urlencode
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(r"d:\invest-explorer\apps\api\.env"), override=True)

import sys
sys.path.insert(0, r"d:\invest-explorer\apps\api")

import main

print("key-present:", bool(os.getenv("GNEWS_API_KEY", "").strip()))
print("main-key-present:", bool(main.os.getenv("GNEWS_API_KEY", "").strip()))

endpoint = "https://gnews.io/api/v4/search"
params = {
    "q": '"AAPL" OR "Apple Inc."',
    "lang": "en",
    "sortby": "publishedAt",
    "max": 3,
    "apikey": os.getenv("GNEWS_API_KEY", "").strip(),
}
url = f"{endpoint}?{urlencode(params)}"

try:
    payload = main._http_get_json(url)
    rows = payload.get("articles", []) if isinstance(payload, dict) else []
    print("rows-via-main-http:", len(rows))
except Exception as e:
    print("http-error:", repr(e))

items = main._fetch_gnews_articles("AAPL", "Apple Inc.", 3, "en")
print("items-via-function:", len(items))
if items:
    print("first-title:", items[0].get("title", "")[:70])
