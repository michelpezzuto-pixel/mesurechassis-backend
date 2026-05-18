"""Retry cleanup for 7-in-1 batch tests."""
import requests, time, sys

BASE = "https://window-field-app.preview.emergentagent.com/api"

def login():
    for _ in range(3):
        try:
            r = requests.post(
                f"{BASE}/auth/login",
                json={"email": "admin@mesurechassis.fr", "password": "admin123"},
                timeout=30,
            )
            r.raise_for_status()
            return r.json()["access_token"]
        except Exception as exc:
            print(f"login retry: {exc}")
            time.sleep(2)
    raise RuntimeError("login failed")


tok = login()
H = {"Authorization": f"Bearer {tok}"}

# Identify all test chantiers that may remain
r = requests.get(f"{BASE}/chantiers", headers=H, timeout=30)
r.raise_for_status()
all_ch = r.json()
TARGET_NAMES = {"Assignment TEST", "SELF Assignment", "Fabrication Valide"}
to_delete = [c for c in all_ch if c.get("client_name") in TARGET_NAMES]
print(f"Found {len(to_delete)} test chantiers to delete: {[(c['client_name'], c['id']) for c in to_delete]}")
for c in to_delete:
    for _ in range(3):
        try:
            d = requests.delete(f"{BASE}/chantiers/{c['id']}", headers=H, timeout=30)
            print(f"DELETE {c['client_name']} ({c['id']}) -> {d.status_code}")
            break
        except Exception as exc:
            print(f"retry delete: {exc}")
            time.sleep(2)

# Also delete any feedbacks with TEST_feedback_visualization
r = requests.get(f"{BASE}/feedbacks", headers=H, timeout=30)
fbs = r.json()
test_fbs = [f for f in fbs if "TEST_feedback_visualization" in (f.get("user_comment") or "")]
print(f"Found {len(test_fbs)} test feedbacks to delete")
for f in test_fbs:
    d = requests.delete(f"{BASE}/feedbacks/{f['id']}", headers=H, timeout=30)
    print(f"DELETE feedback {f['id']} -> {d.status_code}")

# Restore artisan_mode=true
for _ in range(3):
    try:
        r = requests.patch(
            f"{BASE}/company/profile",
            headers=H,
            json={"artisan_mode": True},
            timeout=30,
        )
        r.raise_for_status()
        prof = r.json()
        print(f"PATCH artisan_mode=true -> {r.status_code}, profile: artisan_mode={prof['artisan_mode']}, plan={prof['plan']}, sub_status={prof['subscription_status']}, cape={prof.get('cancel_at_period_end')}")
        break
    except Exception as exc:
        print(f"retry patch: {exc}")
        time.sleep(2)

# Verify
r = requests.get(f"{BASE}/company/profile", headers=H, timeout=30)
prof = r.json()
print(f"FINAL profile: artisan_mode={prof['artisan_mode']}, plan={prof['plan']}, subscription_status={prof['subscription_status']}, cancel_at_period_end={prof.get('cancel_at_period_end')}")
assert prof["artisan_mode"] is True, "artisan_mode NOT restored"
print("\n✅ E) CLEANUP COMPLETE")
