import requests
import json

base_url = "https://gemelo-agro.duckdns.org/api"
login_data = {"email": "jeanmpachecof@gmail.com", "password": "jeanmarko"}

r = requests.post(f"{base_url}/api/auth/login", json=login_data, verify=False)
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

res_sims = requests.get(f"{base_url}/api/simulations/me", headers=headers, verify=False)
items = res_sims.json().get("items", [])
for item in items:
    print(f"Item ID={item.get('id')} keys={list(item.keys())}")
    for k, v in item.items():
        if isinstance(v, list) and len(v) > 0:
            print(f"  List key '{k}' has {len(v)} items")
            if isinstance(v[0], dict):
                print(f"    sample item keys: {list(v[0].keys())}")
