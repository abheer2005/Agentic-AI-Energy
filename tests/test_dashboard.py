from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(
    __file__
).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from fastapi.testclient import TestClient

from api.main import app


client = TestClient(
    app
)


print("\n1) Dashboard route")
response = client.get(
    "/dashboard/"
)
assert response.status_code == 200
assert "Agentic Energy AI" in response.text
print("   PASS")


print("\n2) Dashboard stylesheet")
response = client.get(
    "/dashboard/styles.css"
)
assert response.status_code == 200
assert "--accent" in response.text
print("   PASS")


print("\n3) Dashboard JavaScript")
response = client.get(
    "/dashboard/app.js"
)
assert response.status_code == 200
assert "/ws/live" in response.text
assert "/api/v1/live" in response.text
print("   PASS")


print("\n4) Root redirects to dashboard")
response = client.get(
    "/",
    follow_redirects=False,
)
assert response.status_code in {
    302,
    307,
    308,
}
assert (
    response.headers["location"]
    == "/dashboard/"
)
print("   PASS")


print("\n5) API info remains available")
response = client.get(
    "/api-info"
)
assert response.status_code == 200
assert (
    response.json()["dashboard"]
    == "/dashboard/"
)
print("   PASS")


print(
    "\n✅ STEP 6 DASHBOARD TESTS PASSED"
)
