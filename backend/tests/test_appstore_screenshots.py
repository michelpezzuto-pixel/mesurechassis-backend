"""Tests for the App Store screenshots download endpoints (bug fix v114).

Verifies that each of the 4 endpoints (legacy + 3 size-specific) returns:
- HTTP 200
- Content-Type: application/zip
- Payload > 500 Ko
- ZIP contains exactly 5 PNGs with expected filenames and exact pixel dimensions.
"""

import io
import os
import zipfile

import pytest
import requests
from PIL import Image

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://window-field-app.preview.emergentagent.com").rstrip("/")

EXPECTED_FILENAMES = {
    "01_login.png",
    "02_dashboard.png",
    "03_modal_new_chantier.png",
    "04_fiche_chantier_wall_opt.png",
    "05_wizard_passer.png",
}

# (endpoint_path, expected_dims)
ENDPOINTS = [
    ("/api/_downloads/appstore-screenshots-v114", (1320, 2868)),          # legacy -> 6.9"
    ("/api/_downloads/appstore-screenshots-6_9-v114", (1320, 2868)),
    ("/api/_downloads/appstore-screenshots-6_7-v114", (1290, 2796)),
    ("/api/_downloads/appstore-screenshots-6_5-v114", (1242, 2688)),
]


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    yield s
    s.close()


@pytest.mark.parametrize("endpoint,expected_dims", ENDPOINTS)
def test_appstore_screenshots_endpoint(session, endpoint, expected_dims):
    url = f"{BASE_URL}{endpoint}"
    r = session.get(url, timeout=60)

    # 1. HTTP 200
    assert r.status_code == 200, f"{endpoint} -> HTTP {r.status_code}"

    # 2. Content-Type = application/zip
    ct = r.headers.get("content-type", "")
    assert "application/zip" in ct.lower(), f"{endpoint} -> Content-Type={ct}"

    # 3. Size > 500 Ko
    size_kb = len(r.content) // 1024
    assert size_kb > 500, f"{endpoint} -> only {size_kb} Ko"

    # 4. ZIP content check
    z = zipfile.ZipFile(io.BytesIO(r.content))
    names = [n for n in z.namelist() if not n.endswith("/")]
    # Take only basenames (in case zip has directory structure)
    basenames = {os.path.basename(n) for n in names}

    # Exactly 5 PNGs
    pngs = [n for n in names if n.lower().endswith(".png")]
    assert len(pngs) == 5, f"{endpoint} -> {len(pngs)} PNGs (names={names})"

    # Filenames match expected set
    assert EXPECTED_FILENAMES.issubset(basenames), (
        f"{endpoint} -> missing files. Got: {basenames}, expected: {EXPECTED_FILENAMES}"
    )

    # Dimensions
    for name in pngs:
        img = Image.open(io.BytesIO(z.read(name)))
        assert img.size == expected_dims, (
            f"{endpoint} -> {name} size={img.size} expected={expected_dims}"
        )

    print(f"OK {endpoint}: {size_kb} Ko, 5 PNGs @ {expected_dims}")
