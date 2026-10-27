import requests
import json

base_url = "https://gemelo-agro.duckdns.org/api"
login_data = {"email": "jeanmpachecof@gmail.com", "password": "jeanmarko"}

r = requests.post(f"{base_url}/api/auth/login", json=login_data, verify=False)
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

endpoints = [
    "/api/auth/me",
    "/api/model/status",
    "/api/simulations/me",
    "/api/admin/dashboard",
    "/api/admin/simulations",
    "/api/admin/users",
    "/api/admin/reports/operational",
    "/api/admin/reports/management",
]

for ep in endpoints:
    try:
        res = requests.get(f"{base_url}{ep}", headers=headers, verify=False, timeout=10)
        print(f"GET {ep} -> {res.status_code}")
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, dict):
                print("  Keys:", list(data.keys())[:10])
                if "status" in data or "model_loaded" in data or "version" in data or "active_model" in data:
                    print("  Model info:", data)
            elif isinstance(data, list):
                print(f"  List of {len(data)} items")
    except Exception as e:
        print(f"GET {ep} -> Error: {e}")
