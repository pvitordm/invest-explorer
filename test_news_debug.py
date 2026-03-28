import urllib.request, json

req = urllib.request.Request(
    'http://localhost:8000/watchlist/news?limit=20&per_asset=4&locale=en',
    headers={'Authorization': 'Bearer dev-token'}
)

try:
    resp = urllib.request.urlopen(req)
    data = json.loads(resp.read().decode())
    
    print("=== Response ===")
    print(f"Read-only: {data.get('read_only')}")
    print(f"Source: {data.get('source')}")
    print(f"Message: {data.get('message')}")
    print(f"Items count: {len(data.get('items', []))}")
    
    if data.get('items'):
        print("\n=== First 3 Items ===")
        for item in data.get('items', [])[:3]:
            print(f"  - {item.get('symbol')}: {item.get('title')[:50]}...")
    else:
        print("\n⚠ No items returned")
        
except urllib.error.HTTPError as e:
    print(f"✗ HTTP {e.code}: {e.reason}")
    print(e.read().decode())
except Exception as e:
    print(f"✗ Error: {e}")
