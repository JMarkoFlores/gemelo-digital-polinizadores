import requests
import json

base_url = "https://gemelo-agro.duckdns.org/api"
login_data = {"email": "jeanmpachecof@gmail.com", "password": "jeanmarko"}

r = requests.post(f"{base_url}/api/auth/login", json=login_data, verify=False)
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

for sim_id in [4, 3]:
    res = requests.get(f"{base_url}/api/simulations/me/{sim_id}", headers=headers, verify=False)
    data = res.json()
    print(f"=== SIMULATION {sim_id} ===")
    print("Baseline:", data.get("metricas_base"))
    print("Optimal:", data.get("metricas_optimas"))
    pareto = data.get("pareto_front", [])
    print(f"Pareto points: {len(pareto)}")
    if pareto:
        print("First 3 pareto points:")
        for p in pareto[:3]:
            print(" ", p)
        print("Last 3 pareto points:")
        for p in pareto[-3:]:
            print(" ", p)
