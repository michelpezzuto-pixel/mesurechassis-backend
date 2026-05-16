"""Auth flow tests: login, register, /me, 401 handling."""
import requests

DEMO = [
    ("admin@mesurechassis.fr", "admin123", "admin"),
    ("commercial@mesurechassis.fr", "commercial123", "commercial"),
    ("tech@mesurechassis.fr", "tech123", "technician"),
]


class TestAuth:
    def test_login_admin(self, session, api_url):
        r = session.post(f"{api_url}/auth/login",
                         json={"email": DEMO[0][0], "password": DEMO[0][1]}, timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data and data["access_token"]
        assert data["user"]["email"] == DEMO[0][0]
        assert data["user"]["role"] == "admin"

    def test_login_commercial(self, session, api_url):
        r = session.post(f"{api_url}/auth/login",
                         json={"email": DEMO[1][0], "password": DEMO[1][1]}, timeout=30)
        assert r.status_code == 200
        assert r.json()["user"]["role"] == "commercial"

    def test_login_technician(self, session, api_url):
        r = session.post(f"{api_url}/auth/login",
                         json={"email": DEMO[2][0], "password": DEMO[2][1]}, timeout=30)
        assert r.status_code == 200
        assert r.json()["user"]["role"] == "technician"

    def test_login_bad_password(self, session, api_url):
        r = session.post(f"{api_url}/auth/login",
                         json={"email": DEMO[0][0], "password": "wrong"}, timeout=30)
        assert r.status_code == 401

    def test_me_with_valid_token(self, session, api_url, admin_headers):
        r = requests.get(f"{api_url}/auth/me", headers=admin_headers, timeout=30)
        assert r.status_code == 200
        body = r.json()
        assert body["email"] == DEMO[0][0]
        assert body["role"] == "admin"
        assert "id" in body and body["id"]

    def test_me_missing_token(self, session, api_url):
        r = requests.get(f"{api_url}/auth/me", timeout=30)
        assert r.status_code == 401

    def test_me_invalid_token(self, session, api_url):
        r = requests.get(f"{api_url}/auth/me",
                         headers={"Authorization": "Bearer not.a.real.jwt"}, timeout=30)
        assert r.status_code == 401

    def test_register_new_user_and_duplicate(self, session, api_url):
        import uuid
        email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        r = session.post(f"{api_url}/auth/register",
                         json={"name": "TEST User", "email": email,
                               "password": "pass1234", "role": "technician"}, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "access_token" in data
        assert data["user"]["email"] == email
        # duplicate
        r2 = session.post(f"{api_url}/auth/register",
                          json={"name": "TEST User", "email": email,
                                "password": "pass1234", "role": "technician"}, timeout=30)
        assert r2.status_code == 400
