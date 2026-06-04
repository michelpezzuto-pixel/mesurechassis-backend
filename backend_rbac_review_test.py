"""
Tests RBAC review request — MesureChâssis preview backend.

Cible: https://window-field-app.preview.emergentagent.com/api

Suit le plan exact de la review request :
  TEST 1 — Création chantier avec assigned_to obligatoire (mode entreprise)
  TEST 2 — Transitions de statut multi-rôles
  TEST 3 — Workflow demande de modification (mod-request)
  TEST 4 — Permissions négatives
"""
from __future__ import annotations

import json
import sys
import time
import uuid
from typing import Any, Dict, Optional

import requests

BASE = "https://window-field-app.preview.emergentagent.com/api"

ADMIN = ("admin@mesurechassis.fr", "admin123")
COMMERCIAL = ("commercial@mesurechassis.fr", "commercial123")
TECH = ("tech@mesurechassis.fr", "tech123")

PLATFORM_TOKEN = "mc-platform-2026"


def hdr(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def jsonify(resp: requests.Response) -> Any:
    try:
        return resp.json()
    except Exception:
        return resp.text


passed: list[str] = []
failed: list[str] = []


def ok(label: str, condition: bool, info: str = "") -> None:
    if condition:
        print(f"  ✅ PASS — {label}{(' — ' + info) if info else ''}")
        passed.append(label)
    else:
        print(f"  ❌ FAIL — {label} — {info}")
        failed.append(f"{label} — {info}")


# ─────────────────────────────────────────────────────────────────────
# Setup : login 3 rôles + s'assurer artisan_mode=False sur la company
# ─────────────────────────────────────────────────────────────────────
def login(email: str, password: str) -> Dict[str, Any]:
    r = requests.post(
        f"{BASE}/auth/login",
        json={"email": email, "password": password},
        timeout=20,
    )
    if r.status_code != 200:
        print(f"❌ Login {email} → {r.status_code} : {jsonify(r)}")
        sys.exit(1)
    return r.json()


print("=" * 70)
print("PRÉ-REQUIS : Login 3 rôles + désactiver artisan_mode (mode entreprise)")
print("=" * 70)

admin_login = login(*ADMIN)
commercial_login = login(*COMMERCIAL)
tech_login = login(*TECH)

ADMIN_TOKEN = admin_login["access_token"]
COMMERCIAL_TOKEN = commercial_login["access_token"]
TECH_TOKEN = tech_login["access_token"]
ADMIN_ID = admin_login["user"]["id"]
COMMERCIAL_ID = commercial_login["user"]["id"]
TECH_ID = tech_login["user"]["id"]

print(f"  admin       id={ADMIN_ID}  role={admin_login['user'].get('role')}")
print(f"  commercial  id={COMMERCIAL_ID}  role={commercial_login['user'].get('role')}")
print(f"  technician  id={TECH_ID}  role={tech_login['user'].get('role')}")

# Force artisan_mode=False ET account_type=entreprise pour activer le RBAC strict
r = requests.patch(
    f"{BASE}/company/profile",
    headers=hdr(ADMIN_TOKEN),
    json={"artisan_mode": False, "account_type": "entreprise"},
    timeout=15,
)
print(f"  PATCH /company/profile artisan_mode=False, account_type=entreprise → {r.status_code}")
assert r.status_code == 200, f"Préparation artisan_mode KO : {jsonify(r)}"
profile_after = r.json()
print(
    "  Company profile: "
    f"artisan_mode={profile_after.get('artisan_mode')}, "
    f"account_type={profile_after.get('account_type')}"
)

# Re-login après bascule pour rafraîchir l'attribut artisan_mode dans le token contexte
admin_login = login(*ADMIN)
commercial_login = login(*COMMERCIAL)
tech_login = login(*TECH)
ADMIN_TOKEN = admin_login["access_token"]
COMMERCIAL_TOKEN = commercial_login["access_token"]
TECH_TOKEN = tech_login["access_token"]


def patch_status(
    chantier_id: str,
    new_status: str,
    token: str,
) -> requests.Response:
    return requests.patch(
        f"{BASE}/chantiers/{chantier_id}",
        headers=hdr(token),
        json={"status": new_status},
        timeout=15,
    )


def get_chantier(chantier_id: str, token: str) -> requests.Response:
    return requests.get(
        f"{BASE}/chantiers/{chantier_id}",
        headers=hdr(token),
        timeout=15,
    )


def delete_chantier(chantier_id: str, token: str) -> requests.Response:
    return requests.delete(
        f"{BASE}/chantiers/{chantier_id}", headers=hdr(token), timeout=15
    )


# Helper : ajoute une mesure standard
def add_mesure(chantier_id: str, token: str) -> requests.Response:
    payload = {
        "chantier_id": chantier_id,
        "label": "Salon — fenêtre 1",
        "block_type": "standard",
        "bay_width": 1500.0,
        "bay_height": 2400.0,
        "diag1": 2829.0,
        "diag2": 2829.0,
    }
    return requests.post(
        f"{BASE}/mesures", headers=hdr(token), json=payload, timeout=15
    )


CREATED_IDS: list[str] = []


# ═════════════════════════════════════════════════════════════════════
# TEST 1 — Création chantier avec assigned_to obligatoire
# ═════════════════════════════════════════════════════════════════════
print()
print("=" * 70)
print("TEST 1 — Création chantier (assigned_to obligatoire en mode Entreprise)")
print("=" * 70)

# 1.1 — POST sans assigned_to → 400
payload_no_assign = {
    "first_name": "Marie",
    "last_name": "Dupont",
    "address": "12 rue de la Paix",
    "postal_code": "75002",
    "city": "Paris",
    "appointment_at": "2026-08-15T10:00:00Z",
    "notes": "Rendez-vous pour mesures fenêtres salon",
}
r = requests.post(
    f"{BASE}/chantiers", headers=hdr(ADMIN_TOKEN), json=payload_no_assign, timeout=15
)
detail = jsonify(r)
ok(
    "1.1 POST /chantiers SANS assigned_to → 400 assigned_to obligatoire",
    r.status_code == 400
    and "assigned_to" in str(detail).lower()
    and ("obligatoire" in str(detail).lower() or "obligatoir" in str(detail).lower()),
    f"status={r.status_code} body={detail}",
)

# 1.2 — POST avec assigned_to inexistant → 400
payload_bad_assign = dict(payload_no_assign)
payload_bad_assign["assigned_to"] = "non-existent-user-id-" + uuid.uuid4().hex[:6]
r = requests.post(
    f"{BASE}/chantiers", headers=hdr(ADMIN_TOKEN), json=payload_bad_assign, timeout=15
)
detail = jsonify(r)
ok(
    "1.2 POST /chantiers avec assigned_to inexistant → 400 Collaborateur introuvable",
    r.status_code == 400 and "collaborateur" in str(detail).lower(),
    f"status={r.status_code} body={detail}",
)

# 1.3 — POST avec assigned_to=commercial → 200 OK
payload_ok = dict(payload_no_assign)
payload_ok["assigned_to"] = COMMERCIAL_ID
r = requests.post(
    f"{BASE}/chantiers", headers=hdr(ADMIN_TOKEN), json=payload_ok, timeout=15
)
detail = jsonify(r)
chantier_t2: Optional[Dict[str, Any]] = detail if r.status_code == 200 else None
ok(
    "1.3 POST /chantiers avec assigned_to=commercial valide → 200",
    r.status_code == 200
    and isinstance(detail, dict)
    and detail.get("assigned_to") == COMMERCIAL_ID
    and detail.get("client_name") == "Dupont Marie",
    f"status={r.status_code} client_name={detail.get('client_name') if isinstance(detail, dict) else detail}",
)
if chantier_t2:
    CREATED_IDS.append(chantier_t2["id"])
    print(f"     → chantier créé id={chantier_t2['id']} status={chantier_t2.get('status')}")


# ═════════════════════════════════════════════════════════════════════
# TEST 2 — Transitions de statut
# ═════════════════════════════════════════════════════════════════════
print()
print("=" * 70)
print("TEST 2 — Transitions de statut multi-rôles")
print("=" * 70)

if not chantier_t2:
    print("  ❌ Skipped — pas de chantier de TEST 1")
else:
    cid = chantier_t2["id"]
    initial = chantier_t2.get("status")
    print(f"  Chantier {cid} initial status={initial}")

    # 2.2 — Commercial : add 1 mesure puis PATCH à a_verifier
    r = add_mesure(cid, COMMERCIAL_TOKEN)
    ok(
        "2.2a Commercial POST /mesures → 200",
        r.status_code == 200,
        f"status={r.status_code} body={jsonify(r)}",
    )

    # Le chantier doit être en a_mesurer pour transition vers a_verifier.
    # Si l'initial status est devis_a_faire, on doit d'abord passer à a_mesurer (admin).
    cur = get_chantier(cid, ADMIN_TOKEN).json().get("status")
    if cur == "devis_a_faire":
        r0 = patch_status(cid, "a_mesurer", ADMIN_TOKEN)
        print(f"     → transition admin devis_a_faire → a_mesurer : {r0.status_code}")
        cur = get_chantier(cid, ADMIN_TOKEN).json().get("status")
    print(f"     → status avant transition commerciale = {cur}")

    r = patch_status(cid, "a_verifier", COMMERCIAL_TOKEN)
    ok(
        "2.2b Commercial PATCH a_mesurer → a_verifier → 200",
        r.status_code == 200 and r.json().get("status") == "a_verifier",
        f"status={r.status_code} body={jsonify(r)}",
    )

    # 2.3 — Technicien a_verifier → a_mesurer (renvoi)
    r = patch_status(cid, "a_mesurer", TECH_TOKEN)
    ok(
        "2.3 Tech PATCH a_verifier → a_mesurer → 200",
        r.status_code == 200 and r.json().get("status") == "a_mesurer",
        f"status={r.status_code} body={jsonify(r)}",
    )

    # 2.4 — Technicien a_mesurer → a_verifier → 403
    r = patch_status(cid, "a_verifier", TECH_TOKEN)
    ok(
        "2.4 Tech PATCH a_mesurer → a_verifier → 403",
        r.status_code == 403,
        f"status={r.status_code} body={jsonify(r)}",
    )

    # 2.5 — Commercial a_mesurer → a_verifier
    r = patch_status(cid, "a_verifier", COMMERCIAL_TOKEN)
    ok(
        "2.5 Commercial PATCH a_mesurer → a_verifier → 200",
        r.status_code == 200 and r.json().get("status") == "a_verifier",
        f"status={r.status_code} body={jsonify(r)}",
    )

    # 2.6 — Technicien a_verifier → en_fabrication
    r = patch_status(cid, "en_fabrication", TECH_TOKEN)
    ok(
        "2.6 Tech PATCH a_verifier → en_fabrication → 200",
        r.status_code == 200 and r.json().get("status") == "en_fabrication",
        f"status={r.status_code} body={jsonify(r)}",
    )

    # 2.7 — Admin en_fabrication → cloture
    r = patch_status(cid, "cloture", ADMIN_TOKEN)
    ok(
        "2.7 Admin PATCH en_fabrication → cloture → 200",
        r.status_code == 200 and r.json().get("status") == "cloture",
        f"status={r.status_code} body={jsonify(r)}",
    )


# ═════════════════════════════════════════════════════════════════════
# TEST 3 — Workflow demande de modification
# ═════════════════════════════════════════════════════════════════════
print()
print("=" * 70)
print("TEST 3 — Workflow demande de modification (mod-request)")
print("=" * 70)

# Créer un chantier dédié pour TEST 3 et le mettre en a_verifier
payload_t3 = {
    "first_name": "Lucas",
    "last_name": "Martin",
    "address": "5 avenue des Champs",
    "postal_code": "75008",
    "city": "Paris",
    "appointment_at": "2026-09-10T14:30:00Z",
    "notes": "Chantier de test mod-request",
    "assigned_to": COMMERCIAL_ID,
}
r = requests.post(
    f"{BASE}/chantiers", headers=hdr(ADMIN_TOKEN), json=payload_t3, timeout=15
)
chantier_t3: Optional[Dict[str, Any]] = r.json() if r.status_code == 200 else None
if chantier_t3:
    CREATED_IDS.append(chantier_t3["id"])
    cid3 = chantier_t3["id"]
    print(f"  Chantier TEST 3 créé id={cid3} status={chantier_t3.get('status')}")

    # Avancer à a_verifier : commercial doit avoir au moins une mesure
    r_m = add_mesure(cid3, COMMERCIAL_TOKEN)
    print(f"  Mesure ajoutée → {r_m.status_code}")

    # Ramener à a_mesurer si besoin (initial status pourrait être devis_a_faire)
    cur = get_chantier(cid3, ADMIN_TOKEN).json().get("status")
    if cur == "devis_a_faire":
        patch_status(cid3, "a_mesurer", ADMIN_TOKEN)
    # passer à a_verifier
    rstat = patch_status(cid3, "a_verifier", COMMERCIAL_TOKEN)
    print(f"  → status après PATCH commercial→a_verifier = {rstat.status_code} / {rstat.json().get('status') if rstat.status_code == 200 else jsonify(rstat)}")

    # 3.1 — Commercial POST /mod-request → 200 (chantier en a_verifier)
    r = requests.post(
        f"{BASE}/chantiers/{cid3}/mod-request",
        headers=hdr(COMMERCIAL_TOKEN),
        json={"reason": "Test demande de modification"},
        timeout=15,
    )
    detail = jsonify(r)
    ok(
        "3.1 Commercial POST /mod-request (chantier a_verifier) → 200",
        r.status_code == 200
        and isinstance(detail, dict)
        and (detail.get("ok") is True or "mod_request" in detail),
        f"status={r.status_code} body={detail}",
    )

    # 3.2 — GET /chantiers/{id} → mod_request.status = pending
    r = get_chantier(cid3, COMMERCIAL_TOKEN)
    body = jsonify(r)
    mod = (body or {}).get("mod_request") if isinstance(body, dict) else None
    ok(
        "3.2 GET chantier → mod_request.status == 'pending'",
        r.status_code == 200 and isinstance(mod, dict) and mod.get("status") == "pending",
        f"status={r.status_code} mod_request={mod}",
    )

    # 3.3 — Tech POST /mod-request/respond {approve:true} → 200
    r = requests.post(
        f"{BASE}/chantiers/{cid3}/mod-request/respond",
        headers=hdr(TECH_TOKEN),
        json={"approve": True},
        timeout=15,
    )
    ok(
        "3.3 Tech POST /mod-request/respond {approve:true} → 200",
        r.status_code == 200 and r.json().get("ok") is True and r.json().get("approved") is True,
        f"status={r.status_code} body={jsonify(r)}",
    )

    # 3.4 — Vérifier status=a_mesurer + mod_request.status=approved
    r = get_chantier(cid3, COMMERCIAL_TOKEN)
    body = r.json() if r.status_code == 200 else {}
    mod = body.get("mod_request") if isinstance(body, dict) else None
    ok(
        "3.4 GET chantier → status='a_mesurer' ET mod_request.status='approved'",
        body.get("status") == "a_mesurer"
        and isinstance(mod, dict)
        and mod.get("status") == "approved",
        f"status={body.get('status')} mod_request={mod}",
    )

    # 3.5 — Recréer une demande (repasser à a_verifier d'abord)
    # On est en a_mesurer, donc commercial fait PATCH → a_verifier
    rstat = patch_status(cid3, "a_verifier", COMMERCIAL_TOKEN)
    print(f"  3.5 PATCH a_mesurer → a_verifier (commercial) = {rstat.status_code}")
    # POST mod-request
    r = requests.post(
        f"{BASE}/chantiers/{cid3}/mod-request",
        headers=hdr(COMMERCIAL_TOKEN),
        json={"reason": "Deuxième demande pour test refus"},
        timeout=15,
    )
    ok(
        "3.5 Commercial POST /mod-request (2e demande) → 200",
        r.status_code == 200,
        f"status={r.status_code} body={jsonify(r)}",
    )

    # 3.6 — Tech POST /respond {approve:false} → 200
    r = requests.post(
        f"{BASE}/chantiers/{cid3}/mod-request/respond",
        headers=hdr(TECH_TOKEN),
        json={"approve": False},
        timeout=15,
    )
    ok(
        "3.6 Tech POST /mod-request/respond {approve:false} → 200",
        r.status_code == 200 and r.json().get("ok") is True and r.json().get("approved") is False,
        f"status={r.status_code} body={jsonify(r)}",
    )

    # 3.7 — mod_request.status=refused ET status reste a_verifier
    r = get_chantier(cid3, COMMERCIAL_TOKEN)
    body = r.json() if r.status_code == 200 else {}
    mod = body.get("mod_request") if isinstance(body, dict) else None
    ok(
        "3.7 GET chantier → status='a_verifier' (inchangé) ET mod_request.status='refused'",
        body.get("status") == "a_verifier"
        and isinstance(mod, dict)
        and mod.get("status") == "refused",
        f"status={body.get('status')} mod_request={mod}",
    )
else:
    print(f"  ❌ Impossible de créer chantier TEST 3 : {jsonify(r)}")
    failed.append("TEST 3 setup — création chantier impossible")


# ═════════════════════════════════════════════════════════════════════
# TEST 4 — Permissions négatives
# ═════════════════════════════════════════════════════════════════════
print()
print("=" * 70)
print("TEST 4 — Permissions négatives")
print("=" * 70)

if chantier_t3:
    cid4 = chantier_t3["id"]

    # 4.1 — Admin POST /mod-request → 403
    r = requests.post(
        f"{BASE}/chantiers/{cid4}/mod-request",
        headers=hdr(ADMIN_TOKEN),
        json={"reason": "Tentative admin"},
        timeout=15,
    )
    ok(
        "4.1 Admin POST /mod-request → 403",
        r.status_code == 403,
        f"status={r.status_code} body={jsonify(r)}",
    )

    # 4.2 — Commercial POST /mod-request/respond → 403
    r = requests.post(
        f"{BASE}/chantiers/{cid4}/mod-request/respond",
        headers=hdr(COMMERCIAL_TOKEN),
        json={"approve": True},
        timeout=15,
    )
    ok(
        "4.2 Commercial POST /mod-request/respond → 403",
        r.status_code == 403,
        f"status={r.status_code} body={jsonify(r)}",
    )

    # 4.3 — Commercial POST /mod-request sur chantier en a_mesurer → 400
    # Créer un chantier neuf en a_mesurer
    payload_t4 = {
        "first_name": "Sophie",
        "last_name": "Bernard",
        "address": "10 boulevard Saint-Germain",
        "postal_code": "75005",
        "city": "Paris",
        "appointment_at": "2026-10-01T09:00:00Z",
        "notes": "Test 4.3",
        "assigned_to": COMMERCIAL_ID,
    }
    r = requests.post(
        f"{BASE}/chantiers", headers=hdr(ADMIN_TOKEN), json=payload_t4, timeout=15
    )
    if r.status_code == 200:
        new_cid = r.json()["id"]
        CREATED_IDS.append(new_cid)
        # ramener à a_mesurer si nécessaire
        cur = get_chantier(new_cid, ADMIN_TOKEN).json().get("status")
        if cur == "devis_a_faire":
            patch_status(new_cid, "a_mesurer", ADMIN_TOKEN)
        # commercial essaie POST /mod-request
        r2 = requests.post(
            f"{BASE}/chantiers/{new_cid}/mod-request",
            headers=hdr(COMMERCIAL_TOKEN),
            json={"reason": "Pas en vérification"},
            timeout=15,
        )
        detail = jsonify(r2)
        ok(
            "4.3 Commercial POST /mod-request sur chantier en a_mesurer → 400 (uniquement en vérification)",
            r2.status_code == 400
            and (
                "vérification" in str(detail).lower()
                or "verification" in str(detail).lower()
                or "attente" in str(detail).lower()
            ),
            f"status={r2.status_code} body={detail}",
        )
    else:
        ok("4.3 setup chantier", False, f"create failed status={r.status_code} body={jsonify(r)}")


# ═════════════════════════════════════════════════════════════════════
# CLEANUP — Supprimer les chantiers créés
# ═════════════════════════════════════════════════════════════════════
print()
print("=" * 70)
print("CLEANUP")
print("=" * 70)
for cid in CREATED_IDS:
    r = delete_chantier(cid, ADMIN_TOKEN)
    print(f"  DELETE /chantiers/{cid} → {r.status_code}")


# ═════════════════════════════════════════════════════════════════════
# SUMMARY
# ═════════════════════════════════════════════════════════════════════
print()
print("=" * 70)
print(f"RÉSULTAT — {len(passed)} PASS / {len(failed)} FAIL")
print("=" * 70)
if failed:
    print("ÉCHECS :")
    for f in failed:
        print(f"  ❌ {f}")
    sys.exit(1)
else:
    print("🎉 Tous les tests RBAC passent.")
    sys.exit(0)
