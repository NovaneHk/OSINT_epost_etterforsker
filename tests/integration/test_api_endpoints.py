"""Quick API endpoint smoke test"""
import requests
import json

base = "http://127.0.0.1:8000"

tests = [
    ("Health",           "GET",  "/health",              None),
    ("API Root",         "GET",  "/api/",                None),
    ("Leads GET",        "GET",  "/api/leads/",          None),
    ("KPIs GET",         "GET",  "/api/kpis/",           None),
    ("Sources GET",      "GET",  "/api/sources",         None),
    ("Exports GET",      "GET",  "/api/exports",         None),
    ("Campaigns GET",    "GET",  "/api/campaigns",       None),
    ("Runs GET",         "GET",  "/api/runs",            None),
    ("Users GET",        "GET",  "/api/users",           None),
    ("Settings GET",     "GET",  "/api/settings/",       None),
    ("Activity GET",     "GET",  "/api/activity/",       None),
    ("Playbooks GET",    "GET",  "/api/playbooks/",      None),
    ("Investigations GET","GET", "/api/investigations/",  None),
    ("Health DB",        "GET",  "/api/health/database",  None),
    ("Health App",       "GET",  "/api/health/application", None),
    ("Register",         "POST", "/api/auth/register", {
        "email": "test@example.com",
        "username": "testuser",
        "password": "TestPass123!",
        "full_name": "Test User"
    }),
    ("Login admin",      "POST", "/api/auth/token", {
        "username": "admin@example.com",
        "password": "Admin1234"
    }),
    ("Login form",       "FORM", "/api/auth/login", {
        "username": "admin@example.com",
        "password": "Admin1234"
    }),
]

passed = 0
failed = 0
errors = []

for name, method, path, body in tests:
    try:
        url = base + path
        if method == "GET":
            r = requests.get(url, timeout=5)
        elif method == "FORM":
            r = requests.post(url, data=body, timeout=5)
        else:
            r = requests.post(url, json=body, timeout=5)
        
        status = r.status_code
        ok = status < 500
        symbol = "PASS" if ok else "FAIL"
        
        if ok:
            passed += 1
        else:
            failed += 1
            errors.append((name, status, r.text[:300]))
        
        print(f"[{symbol}] {name}: {status} - {r.text[:150]}")
    except Exception as e:
        failed += 1
        errors.append((name, 0, str(e)))
        print(f"[FAIL] {name}: EXCEPTION - {e}")

print(f"\n{'='*60}")
print(f"Results: {passed} passed, {failed} failed out of {passed+failed}")

if errors:
    print(f"\nFailed endpoints:")
    for name, status, msg in errors:
        print(f"  - {name} ({status}): {msg[:200]}")
