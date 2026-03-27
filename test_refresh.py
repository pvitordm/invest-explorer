import urllib.request
import json

try:
    req = urllib.request.Request(
        'http://localhost:8000/refresh',
        data=b'{}',
        headers={
            'Authorization': 'Bearer test-token',
            'Content-Type': 'application/json'
        },
        method='POST'
    )
    resp = urllib.request.urlopen(req)
    data = json.loads(resp.read())
    print(f"✓ Refresh funcionando!")
    print(f"  Status: {data.get('status')}")
    print(f"  Assets ao vivo: {data.get('live_asset_count')}")
    print(f"  Fallback: {data.get('fallback_asset_count')}")
    print(f"  Total assets: {data.get('snapshot_asset_count')}")
except Exception as e:
    print(f"✗ Erro: {e}")
