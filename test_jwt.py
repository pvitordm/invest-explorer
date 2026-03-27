import urllib.request
import json

try:
    req = urllib.request.Request(
        'http://localhost:8000/refresh',
        data=b'{}',
        headers={
            'Authorization': 'Bearer test-jwt-token',
            'Content-Type': 'application/json'
        },
        method='POST'
    )
    resp = urllib.request.urlopen(req)
    data = json.loads(resp.read())
    print(f"✓ Refresh com JWT middleware funcionando!")
    print(f"  Status: {data.get('status')}")
    print(f"  User verified: {data.get('requested_by', {}).get('verified_jwt', 'N/A')}")
    print(f"  Assets ao vivo: {data.get('live_asset_count')}")
except Exception as e:
    print(f"✗ Erro: {e}")
