import requests
import json

base_url = "https://gemelo-agro.duckdns.org/api"
login_data = {"email": "jeanmpachecof@gmail.com", "password": "jeanmarko"}

r = requests.post(f"{base_url}/api/auth/login", json=login_data, verify=False)
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

res_model = requests.get(f"{base_url}/api/model/status", headers=headers, verify=False)
print("=== MODEL STATUS ===")
print(json.dumps(res_model.json(), indent=2))

res_sims = requests.get(f"{base_url}/api/simulations/me", headers=headers, verify=False)
print("=== SIMULATIONS ME ===")
print(json.dumps(res_sims.json(), indent=2))
