import json, urllib.request, urllib.error
d = json.dumps({'username': 'admin@localhost', 'password': 'yNP!X2&g!rshw*)Bk^3V*V!q'}).encode()
req = urllib.request.Request('http://localhost:8000/api/auth/token', data=d, headers={'Content-Type': 'application/json'})
try:
    resp = urllib.request.urlopen(req)
    print(resp.status, resp.read()[:300])
except urllib.error.HTTPError as e:
    print(e.code, e.read())
