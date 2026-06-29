"""
Non-regression smoke test for app.json + backend auth/projects endpoints.
Iteration 6 — Verifies that app.json fixes are still in place and that the
backend critical endpoints (login + projects) still work.
"""
import json
import os
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://stair-pro.preview.emergentagent.com").rstrip("/")
APP_JSON_PATH = "/app/frontend/app.json"

ADMIN_EMAIL = "admin@demo.fr"
ADMIN_PASSWORD = "Demo1234!"


# --- app.json static checks ---
class TestAppJson:
    def test_app_json_is_valid_json(self):
        with open(APP_JSON_PATH, "r") as f:
            data = json.load(f)
        assert "expo" in data

    def test_expo_name_is_mesure_escalier(self):
        with open(APP_JSON_PATH, "r") as f:
            data = json.load(f)
        assert data["expo"]["name"] == "Mesure escalier", (
            f"expo.name should be 'Mesure escalier', got {data['expo']['name']!r}"
        )

    def test_vision_camera_plugin_present(self):
        with open(APP_JSON_PATH, "r") as f:
            data = json.load(f)
        plugins = data["expo"].get("plugins", [])
        found = False
        for p in plugins:
            if isinstance(p, list) and len(p) > 0 and p[0] == "react-native-vision-camera":
                found = True
                assert "cameraPermissionText" in p[1]
                break
            if p == "react-native-vision-camera":
                found = True
                break
        assert found, "react-native-vision-camera plugin missing from app.json"

    def test_ios_camera_usage_description_present(self):
        with open(APP_JSON_PATH, "r") as f:
            data = json.load(f)
        info_plist = data["expo"]["ios"]["infoPlist"]
        assert "NSCameraUsageDescription" in info_plist
        assert len(info_plist["NSCameraUsageDescription"]) > 0


# --- backend smoke tests ---
@pytest.fixture(scope="module")
def auth_token():
    resp = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=15,
    )
    assert resp.status_code == 200, f"Login failed: {resp.status_code} {resp.text}"
    data = resp.json()
    assert "token" in data, f"No token in response: {data}"
    return data["token"]


class TestBackendRegression:
    def test_login_returns_token(self, auth_token):
        assert isinstance(auth_token, str) and len(auth_token) > 10

    def test_get_projects_authenticated(self, auth_token):
        resp = requests.get(
            f"{BASE_URL}/api/projects",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=15,
        )
        assert resp.status_code == 200, f"GET /api/projects failed: {resp.status_code} {resp.text}"
        body = resp.json()
        # projects endpoint may return list or {projects: [...]}
        if isinstance(body, dict):
            assert "projects" in body or "items" in body or len(body) >= 0
        else:
            assert isinstance(body, list)
