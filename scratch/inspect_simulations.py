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
    print(f"ID: {item.get('id')} | Date: {item.get('fecha')}")
    print("  Baseline:", item.get("metricas_base"))
    print("  Optimal:", item.get("metricas_optimas"))
    pareto = item.get("pareto_front", [])
    print(f"  Pareto front points: {len(pareto)}")
    if pareto:
        print("  Pareto sample 0:", pareto[0])
        print("  Pareto sample last:", pareto[-1])
