"""Test the a_verifier email notification flow on preview backend."""
import requests
import json
import time

BASE = "https://window-field-app.preview.emergentagent.com/api"

def login(email, pwd):
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": pwd}, timeout=20)
    assert r.status_code == 200, f"Login {email} failed: {r.status_code} {r.text}"
    data = r.json()
    return data["access_token"], data["user"]

def h(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}

print("=" * 70)
print("STEP 0 — Restore company default (account_type=entreprise, artisan_mode=false)")
print("=" * 70)
admin_tok, admin_u = login("admin@mesurechassis.fr", "admin123")
print(f"  admin id={admin_u['id']} role={admin_u['role']}")

# Restore company default to entreprise + artisan_mode false
r = requests.patch(f"{BASE}/company/profile",
                   headers=h(admin_tok),
                   json={"account_type": "entreprise", "artisan_mode": False},
                   timeout=20)
print(f"  PATCH /company/profile → {r.status_code} {r.json() if r.headers.get('content-type','').startswith('application/json') else r.text[:200]}")
assert r.status_code == 200

# Re-login admin to refresh the JWT artisan_mode claim if any
admin_tok, admin_u = login("admin@mesurechassis.fr", "admin123")

print()
print("=" * 70)
print("STEP 1 — Commercial login + Admin creates chantier assigned to commercial")
print("=" * 70)
com_tok, com_u = login("commercial@mesurechassis.fr", "commercial123")
print(f"  commercial id={com_u['id']}")

tech_tok, tech_u = login("tech@mesurechassis.fr", "tech123")
print(f"  tech id={tech_u['id']}")

payload = {
    "first_name": "Émile",
    "last_name": "Verif-Email-Test",
    "address": "12 rue du Test Email",
    "postal_code": "75011",
    "city": "Paris",
    "appointment_at": "2026-07-01T10:00:00Z",
    "notes": "Test notification a_verifier",
    "assigned_to": com_u["id"],
}
r = requests.post(f"{BASE}/chantiers", headers=h(admin_tok), json=payload, timeout=20)
print(f"  POST /chantiers → {r.status_code}")
assert r.status_code == 200, r.text
chantier = r.json()
chantier_id = chantier["id"]
print(f"  chantier_id={chantier_id}, status={chantier.get('status')}, assigned_to={chantier.get('assigned_to')}")

print()
print("=" * 70)
print("STEP 2 — Commercial creates a measurement (minimal body)")
print("=" * 70)
# A minimal valid body for mesures — let's check what backend accepts
mesure_payload = {
    "opening_type": "fenetre",
    "largeur": 1000,
    "hauteur": 1500,
}
r = requests.post(f"{BASE}/chantiers/{chantier_id}/mesures", headers=h(com_tok), json=mesure_payload, timeout=20)
print(f"  POST /chantiers/{{id}}/mesures (commercial, minimal) → {r.status_code}")
if r.status_code != 200:
    print(f"    Body: {r.text[:500]}")
    # Try with the documented fields the codebase uses
    mesure_payload = {
        "bay_width": 1000,
        "bay_height": 1500,
        "diag1": 1803,
        "diag2": 1803,
    }
    r = requests.post(f"{BASE}/chantiers/{chantier_id}/mesures", headers=h(com_tok), json=mesure_payload, timeout=20)
    print(f"  POST /chantiers/{{id}}/mesures (commercial, bay_*) → {r.status_code}")
    if r.status_code == 200:
        print(f"    mesure id={r.json().get('id')}")
    else:
        print(f"    Body: {r.text[:500]}")
else:
    print(f"    mesure id={r.json().get('id')}")

print()
print("=" * 70)
print("STEP 3 — Commercial: PATCH chantier → status=a_verifier (triggers email)")
print("=" * 70)
# Note: the chantier starts at status='devis_a_faire' in entreprise mode (admin-created).
# Need to first move it to a_mesurer (admin transition) then commercial → a_verifier.
# Let's first check current status:
r = requests.get(f"{BASE}/chantiers/{chantier_id}", headers=h(admin_tok), timeout=20)
print(f"  GET chantier current status → {r.json().get('status')}")
current_status = r.json().get('status')

if current_status == "devis_a_faire":
    # Admin transitions to a_mesurer
    r = requests.patch(f"{BASE}/chantiers/{chantier_id}", headers=h(admin_tok),
                       json={"status": "a_mesurer"}, timeout=20)
    print(f"  Admin PATCH devis_a_faire→a_mesurer → {r.status_code}")
    assert r.status_code == 200, r.text

# Now commercial → a_verifier
ts_before_patch = time.time()
r = requests.patch(f"{BASE}/chantiers/{chantier_id}", headers=h(com_tok),
                   json={"status": "a_verifier"}, timeout=30)
print(f"  Commercial PATCH a_mesurer→a_verifier → {r.status_code}")
if r.status_code != 200:
    print(f"    Body: {r.text[:500]}")
else:
    print(f"    OK status={r.json().get('status')}")

assert r.status_code == 200, "Transition to a_verifier failed"

# Give the email sender a moment to log
time.sleep(3)

print()
print("=" * 70)
print("STEP 4 — Cleanup: DELETE the test chantier")
print("=" * 70)
r = requests.delete(f"{BASE}/chantiers/{chantier_id}", headers=h(admin_tok), timeout=20)
print(f"  DELETE /chantiers/{chantier_id} → {r.status_code}")

print()
print(f"DONE — test chantier_id={chantier_id} cleaned up.")
print(f"PATCH a_verifier issued at unix ts={ts_before_patch:.2f}")
