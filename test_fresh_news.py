#!/usr/bin/env python3
"""
Direct test that starts fresh without any cached modules
"""
import subprocess
import sys

result = subprocess.run([
    sys.executable, "-c", 
    """
import os
from pathlib import Path
from dotenv import load_dotenv

# Explicit override
load_dotenv(dotenv_path=Path(r'd:\\invest-explorer\\apps\\api\\.env'), override=True)

import urllib.request
import json

req = urllib.request.Request(
    'http://localhost:8000/watchlist/news?limit=5&per_asset=2',
    headers={'Authorization': 'Bearer test-token'}
)

try:
    resp = urllib.request.urlopen(req)
    data = json.loads(resp.read().decode())
    print('✓ Endpoint OK')
    print(f'  Items: {len(data.get(\"items\", []))}')
    if data.get('items'):
        print(f'  First: {data[\"items\"][0].get(\"title\", \"N/A\")[:50]}...')
    else:
        print(f'  Message: {data.get(\"message\", \"No message\")}')
except Exception as e:
    print(f'✗ Error: {e}')
"""
], capture_output=False, text=True)

sys.exit(result.returncode)
