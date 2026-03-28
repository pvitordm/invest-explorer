import urllib.request, json

req = urllib.request.Request(
    'http://localhost:8000/watchlist',
    headers={'Authorization': 'Bearer test-token'}
)

try:
    resp = urllib.request.urlopen(req)
    data = json.loads(resp.read().decode())
    print("Owner info:")
    print(json.dumps(data.get('owner', {}), indent=2))
except Exception as e:
    print(f"Error: {e}")
