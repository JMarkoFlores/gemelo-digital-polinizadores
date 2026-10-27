import requests
import json

base_url = "https://gemelo-agro.duckdns.org"

# Let's check health
try:
    r = requests.get(f"{base_url}/health", verify=False, timeout=10)
    print("Health:", r.status_code, r.text)
except Exception as e:
    print("Health error:", e)

# Let's check /api/model/status
try:
    r = requests.get(f"{base_url}/api/model/status", verify=False, timeout=10)
    print("Model status (unauth):", r.status_code, r.text)
except Exception as e:
    print("Model status error:", e)

# Let's login
login_data = {"email": "jeanmpachecof@gmail.com", "password": "jeanmarko"}
try:
    r = requests.post(f"{base_url}/api/auth/login", json=login_data, verify=False, timeout=10)
    print("Login:", r.status_code)
    if r.status_code == 200:
        token = r.json().get("access_token")
        print("Token received! Token preview:", token[:20], "...")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test /api/auth/me
        r_me = requests.get(f"{base_url}/api/auth/me", headers=headers, verify=False)
        print("Me:", r_me.status_code, r_me.json())

        # Test /api/model/status
        r_model = requests.get(f"{base_url}/api/model/status", headers=headers, verify=False)
        print("Model status:", r_model.status_code, r_model.json())

        # Test simulations
        r_sims = requests.get(f"{base_url}/api/simulations/me", headers=headers, verify=False)
        print("Simulations me:", r_sims.status_code, len(r_sims.json().get("items", [])))
        if r_sims.json().get("items"):
            for s in r_sims.json().get("items")[:3]:
                print("Sim item:", s.get("id"), s.get("name"), s.get("created_at"))
except Exception as e:
    print("Login error:", e)
