import urllib.request, json

req = urllib.request.Request(
    'http://localhost:8000/watchlist/news',
    headers={'Authorization': 'Bearer dev-token'}
)

try:
    resp = urllib.request.urlopen(req)
    data = json.loads(resp.read().decode())
    print("✓ Endpoint works!")
    items = data.get('items', [])
    print(f"  Items: {len(items)}")
    if data.get('message'):
        print(f"  Message: {data['message']}")
except urllib.error.HTTPError as e:
    print(f"✗ HTTP {e.code}: {e.reason}")
except Exception as e:
    print(f"✗ Error: {e}")
