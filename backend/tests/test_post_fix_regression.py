"""
Post-fix regression tests (Iteration 7):
- Validate stats.py modifications (.limit(1000) on 2 cursors).
- Confirm auth + projects endpoints still respond.
- Validate frontend assets/files unchanged (app.json valid JSON, opencv2.framework absent).
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess

import pytest
import requests

BASE_URL = (
    os.environ.get("EXPO_BACKEND_URL")
    or os.environ.get("EXPO_PUBLIC_BACKEND_URL")
    or "https://stair-pro.preview.emergentagent.com"
).rstrip("/")

ADMIN_EMAIL = "admin@demo.fr"
ADMIN_PASSWORD = "Demo1234!"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def token(api):
    r = api.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=30,
    )
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text[:200]}"
    data = r.json()
    assert "token" in data, f"no token in response: {data}"
    return data["token"]


# ---------------------------------------------------------------------------
# Backend: auth
# ---------------------------------------------------------------------------
class TestAuth:
    def test_login_admin_ok(self, api):
        r = api.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=30,
        )
        assert r.status_code == 200
        body = r.json()
        assert "token" in body and isinstance(body["token"], str) and len(body["token"]) > 10


# ---------------------------------------------------------------------------
# Backend: projects
# ---------------------------------------------------------------------------
class TestProjects:
    def test_list_projects_with_bearer(self, api, token):
        r = api.get(
            f"{BASE_URL}/api/projects",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        assert r.status_code == 200, f"GET /api/projects -> {r.status_code} {r.text[:200]}"
        data = r.json()
        assert isinstance(data, list), f"expected list, got {type(data).__name__}"


# ---------------------------------------------------------------------------
# Backend: stats (post-fix with .limit(1000))
# ---------------------------------------------------------------------------
class TestStats:
    def test_stats_endpoint_ok(self, api, token):
        # The router exposes GET /api/stats (review request mentions
        # /api/stats/overview which is a typo; verified in server.py).
        r = api.get(
            f"{BASE_URL}/api/stats",
            headers={"Authorization": f"Bearer {token}"},
            timeout=60,
        )
        assert r.status_code == 200, f"GET /api/stats -> {r.status_code} {r.text[:400]}"
        body = r.json()
        # validate expected fields
        for key in ("total_projects", "by_status", "total_measurements",
                    "validated_measurements", "average_steps", "team_size"):
            assert key in body, f"missing key {key} in stats response: {body}"
        # types
        assert isinstance(body["total_projects"], int)
        assert isinstance(body["by_status"], dict)
        assert isinstance(body["total_measurements"], int)
        assert isinstance(body["validated_measurements"], int)
        # avg_steps may be None or float/int
        assert body["average_steps"] is None or isinstance(body["average_steps"], (int, float))


# ---------------------------------------------------------------------------
# Frontend assets / repo hygiene
# ---------------------------------------------------------------------------
class TestRepoHygiene:
    def test_app_json_is_valid(self):
        p = pathlib.Path("/app/frontend/app.json")
        assert p.exists(), "app.json missing"
        with p.open() as f:
            data = json.load(f)  # raises on invalid JSON
        assert "expo" in data
        assert data["expo"]["slug"] == "mesure-escalier"

    def test_opencv_framework_absent_from_repo(self):
        framework = pathlib.Path(
            "/app/frontend/modules/aruco-detector/ios/Frameworks/opencv2.framework"
        )
        assert not framework.exists(), (
            f"opencv2.framework still present at {framework}; should be removed."
        )

    def test_frontend_size_under_50mb(self):
        # du -sm /app/frontend excluding node_modules and dist
        # Use rsync-like approach via du with --exclude
        result = subprocess.run(
            [
                "du", "-sm",
                "--exclude=node_modules",
                "--exclude=dist",
                "--exclude=.metro-cache",
                "--exclude=.expo",
                "/app/frontend",
            ],
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"du failed: {result.stderr}"
        size_mb = int(result.stdout.split()[0])
        print(f"/app/frontend (excl node_modules/dist/.metro-cache/.expo) = {size_mb} MB")
        assert size_mb < 50, f"/app/frontend = {size_mb} MB (>= 50MB threshold)"


# ---------------------------------------------------------------------------
# Frontend bundle (Metro web) -- optional sanity check
# ---------------------------------------------------------------------------
class TestMetroBundle:
    def test_metro_web_serves_200(self):
        try:
            r = requests.get("http://localhost:3000", timeout=30)
        except Exception as e:
            pytest.skip(f"Metro not reachable on localhost:3000: {e}")
        assert r.status_code == 200, f"Metro returned {r.status_code}"
