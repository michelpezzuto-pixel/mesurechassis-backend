"""
Migration one-shot : Marquer tous les comptes existants comme "legacy".

À exécuter UNE SEULE FOIS en Phase 1 (avant activation du kill switch).
Idempotent : peut être relancé sans risque, ne modifie que les users qui
n'ont pas encore de validation_status.

Usage:
    cd /app/backend && python migrate_legacy_users.py
"""
import asyncio
import sys
from datetime import datetime, timezone

sys.path.insert(0, ".")
from db import db  # noqa: E402


async def migrate():
    now_iso = datetime.now(timezone.utc).isoformat()

    # Comptes existants (créés avant la mise en place du système Double-Phase)
    # → marqués "legacy" pour être grand-fatherés pendant la période de grâce
    # de 30 jours au moment du basculement en Phase 2.
    result = await db.users.update_many(
        {
            "validation_status": {"$exists": False},
            "status": {"$ne": "deleted"},
        },
        {
            "$set": {
                "validation_status": "legacy",
                "legacy_marked_at": now_iso,
            }
        },
    )
    print(f"[OK] {result.modified_count} comptes existants marqués 'legacy'")

    # Statistiques post-migration
    stats = {}
    async for u in db.users.find({}, {"_id": 0, "validation_status": 1, "role": 1}):
        st = u.get("validation_status", "unvalidated")
        stats[st] = stats.get(st, 0) + 1
    print("\n=== Répartition finale ===")
    for k, v in sorted(stats.items()):
        print(f"  {k:15s} : {v}")


if __name__ == "__main__":
    asyncio.run(migrate())
