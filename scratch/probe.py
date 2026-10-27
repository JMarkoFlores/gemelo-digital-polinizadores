import requests

for path in ['/api/health', '/health', '/api/auth/login', '/auth/login', '/api/model/status']:
    url = f'https://gemelo-agro.duckdns.org{path}'
    try:
        r = requests.get(url, verify=False, timeout=5)
        print(f'GET {path} -> {r.status_code} ({r.headers.get("content-type")})')
    except Exception as e:
        print(f'GET {path} -> {e}')

login_data = {"email": "jeanmpachecof@gmail.com", "password": "jeanmarko"}
for path in ['/api/auth/login', '/api/api/auth/login', '/auth/login']:
    url = f'https://gemelo-agro.duckdns.org{path}'
    try:
        r = requests.post(url, json=login_data, verify=False, timeout=5)
        print(f'POST {path} -> {r.status_code} {r.text[:100]}')
    except Exception as e:
        print(f'POST {path} -> {e}')
