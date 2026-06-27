"""Tests for GET /api/poc/icon.png and POC endpoints regression."""
import io
import os
import pytest
import requests
from PIL import Image

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://stair-pro.preview.emergentagent.com").rstrip("/")


@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    return s


# --- /api/poc/icon.png (new endpoint) ---
class TestPocIcon:
    def test_status_200(self, api):
        r = api.get(f"{BASE_URL}/api/poc/icon.png", timeout=15)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"

    def test_content_type_png(self, api):
        r = api.get(f"{BASE_URL}/api/poc/icon.png", timeout=15)
        ct = r.headers.get("content-type", "")
        assert "image/png" in ct.lower(), f"Expected image/png, got {ct}"

    def test_dimensions_1024(self, api):
        r = api.get(f"{BASE_URL}/api/poc/icon.png", timeout=15)
        assert r.status_code == 200
        img = Image.open(io.BytesIO(r.content))
        assert img.size == (1024, 1024), f"Expected 1024x1024, got {img.size}"
        assert img.format == "PNG", f"Expected PNG format, got {img.format}"

    def test_file_under_1mb(self, api):
        r = api.get(f"{BASE_URL}/api/poc/icon.png", timeout=15)
        size = len(r.content)
        assert size < 1024 * 1024, f"Expected <1MB, got {size} bytes"
        assert size > 0, "Empty file returned"


# --- Non-regression on existing POC endpoints ---
class TestPocRegression:
    def test_markers_pdf(self, api):
        r = api.get(f"{BASE_URL}/api/poc/markers.pdf", timeout=15)
        assert r.status_code == 200, f"markers.pdf returned {r.status_code}"
        assert "application/pdf" in r.headers.get("content-type", "").lower()
        assert r.content[:4] == b"%PDF", "Not a valid PDF magic header"

    def test_results_md(self, api):
        r = api.get(f"{BASE_URL}/api/poc/results.md", timeout=15)
        assert r.status_code == 200, f"results.md returned {r.status_code}"
        # PlainTextResponse should yield text/plain
        assert "text/plain" in r.headers.get("content-type", "").lower()
        assert len(r.text) > 0, "Empty markdown content"
