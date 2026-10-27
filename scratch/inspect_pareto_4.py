import requests
import json
import pandas as pd

base_url = "https://gemelo-agro.duckdns.org/api"
login_data = {"email": "jeanmpachecof@gmail.com", "password": "jeanmarko"}

r = requests.post(f"{base_url}/api/auth/login", json=login_data, verify=False)
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

res = requests.get(f"{base_url}/api/simulations/me/4", headers=headers, verify=False)
data = res.json()
pareto = data.get("frente_pareto", [])
df_pareto = pd.DataFrame(pareto)
print("Pareto shape:", df_pareto.shape)
print("Pareto columns:", df_pareto.columns.tolist())
print(df_pareto[["crop_yield_index", "pollinator_abundance_index", "crop_area_pct", "natural_area_pct", "floral_strips_pct"]].describe().round(3))
print("\nFirst 5 solutions:")
print(df_pareto[["crop_yield_index", "pollinator_abundance_index", "crop_area_pct", "natural_area_pct", "floral_strips_pct"]].head())
print("\nOptimal solution:")
print(data.get("metricas_optimas"))
print("\nBaseline:")
print(data.get("metricas_base"))
