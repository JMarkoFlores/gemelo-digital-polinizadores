import requests

url = "https://laboratorio-agro.duckdns.org/"
try:
    r = requests.get(url, verify=False, timeout=10)
    print("Status:", r.status_code)
    print("Headers:", r.headers)
    print("Text preview:", r.text[:500])
except Exception as e:
    print("Error:", e)
