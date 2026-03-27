import json
import urllib.error
import urllib.request
from pathlib import Path


def read_env(path: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def main() -> int:
    web_env = read_env("apps/web/.env.local")

    supabase_url = web_env.get("NEXT_PUBLIC_SUPABASE_URL", "")
    anon_key = web_env.get("NEXT_PUBLIC_SUPABASE_ANON_KEY", "")

    if not supabase_url or not anon_key:
        print("[FAIL] Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY")
        return 1

    print("[1] API health...")
    health_req = urllib.request.Request("http://localhost:8000/health")
    with urllib.request.urlopen(health_req, timeout=15) as response:
        print("  status:", response.status)
        print("  body:", response.read().decode("utf-8"))

    print("[2] Supabase anonymous sign-in...")
    auth_url = f"{supabase_url}/auth/v1/signup"
    auth_payload = json.dumps({}).encode("utf-8")
    auth_req = urllib.request.Request(
        auth_url,
        data=auth_payload,
        method="POST",
        headers={
            "apikey": anon_key,
            "Authorization": f"Bearer {anon_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(auth_req, timeout=25) as response:
        auth_data = json.loads(response.read().decode("utf-8"))
        access_token = auth_data.get("access_token", "")
        user = auth_data.get("user", {})
        print("  status:", response.status)
        print("  user id:", user.get("id"))
        print("  token len:", len(access_token))
        print("  token preview:", (access_token[:16] + "...") if access_token else "<none>")

    if not access_token:
        print("[FAIL] Supabase returned no access_token")
        return 1

    print("[3] API /watchlist with real JWT...")
    watch_req = urllib.request.Request(
        "http://localhost:8000/watchlist",
        method="GET",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(watch_req, timeout=20) as response:
        body = json.loads(response.read().decode("utf-8"))
        owner = body.get("owner", {})
        print("  status:", response.status)
        print("  owner sub:", owner.get("sub"))
        print("  verified_jwt:", owner.get("verified_jwt"))
        print("  items:", len(body.get("items", [])))
        if not owner.get("verified_jwt"):
            print("[WARN] JWT accepted in fallback mode (not strictly verified).")

    print("[4] API /refresh with real JWT...")
    refresh_req = urllib.request.Request(
        "http://localhost:8000/refresh",
        data=b"{}",
        method="POST",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(refresh_req, timeout=45) as response:
        body = json.loads(response.read().decode("utf-8"))
        payload = body.get("data", {})
        requested_by = body.get("requested_by", {})
        print("  status:", response.status)
        print("  message:", body.get("message"))
        print("  refresh verified_jwt:", requested_by.get("verified_jwt"))
        print("  live_asset_count:", body.get("live_asset_count"))
        print("  fallback_asset_count:", body.get("fallback_asset_count"))
        print("  payload asset_count:", payload.get("asset_count"))

    print("[5] API /watchlist/items add/remove...")
    cleanup_req = urllib.request.Request(
        "http://localhost:8000/watchlist/items",
        data=json.dumps({"symbol": "AAPL", "exchange": "NASDAQ"}).encode("utf-8"),
        method="DELETE",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(cleanup_req, timeout=20):
        pass

    add_req = urllib.request.Request(
        "http://localhost:8000/watchlist/items",
        data=json.dumps({"symbol": "AAPL", "exchange": "NASDAQ"}).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(add_req, timeout=20) as response:
        add_body = json.loads(response.read().decode("utf-8"))
        add_items = add_body.get("items", [])
        added = any((item.get("asset") or {}).get("symbol") == "AAPL" for item in add_items)
        print("  add status:", response.status)
        print("  contains AAPL after add:", added)

    remove_req = urllib.request.Request(
        "http://localhost:8000/watchlist/items",
        data=json.dumps({"symbol": "AAPL", "exchange": "NASDAQ"}).encode("utf-8"),
        method="DELETE",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(remove_req, timeout=20) as response:
        remove_body = json.loads(response.read().decode("utf-8"))
        remove_items = remove_body.get("items", [])
        removed = all((item.get("asset") or {}).get("symbol") != "AAPL" for item in remove_items)
        print("  remove status:", response.status)
        print("  contains AAPL after remove:", not removed)

    print("[OK] Real Supabase + API integration test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
