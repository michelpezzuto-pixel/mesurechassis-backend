"""Purge tous les documents contenant un email donné (ou un pattern) sur la DB.

⚠️ SCRIPT DE MAINTENANCE — À exécuter avec précaution.

Usage typique après un déploiement Railway pour nettoyer un email de test :

    # Sur Railway (via l'onglet "Shell" ou une commande SSH) :
    python -m tools.purge_email_pattern "bruxmove"

    # Ou en dry-run (n'efface rien, affiche uniquement) :
    python -m tools.purge_email_pattern "bruxmove" --dry-run

Le script parcourt TOUTES les collections MongoDB et supprime tout doc
dont un champ email/client_email/name/company/company_name/to
correspond au pattern (regex insensible à la casse).

Protection intégrée : les comptes `@mesurechassis.fr` sont TOUJOURS
préservés — impossible de les effacer même par erreur.

Retourne le nombre de docs supprimés par collection.
"""
from __future__ import annotations

import argparse
import asyncio
import re
import sys


async def main(pattern: str, dry_run: bool) -> int:
    """Purge tous les documents contenant `pattern` (regex, case-insensitive).

    Retourne le total de documents effacés (0 en dry-run).
    """
    if not pattern or len(pattern) < 3:
        print("❌ Pattern trop court (min 3 caractères pour éviter les catastrophes)")
        return 0

    # 🛡️ Protection ABSOLUE — refuse d'effacer les @mesurechassis.fr
    protected_regex = re.compile(r"@mesurechassis\.fr$", re.IGNORECASE)
    if protected_regex.search(pattern):
        print("❌ Pattern refusé : impossible d'effacer les @mesurechassis.fr")
        return 0

    # Import différé pour éviter que ce fichier plante si db.py absent
    sys.path.insert(0, "/app/backend")
    from db import db  # noqa: E402

    print(f"═══ PURGE pattern={pattern!r} (dry_run={dry_run}) ═══\n")

    query = {
        "$or": [
            {"email": {"$regex": pattern, "$options": "i"}},
            {"client_email": {"$regex": pattern, "$options": "i"}},
            {"to": {"$regex": pattern, "$options": "i"}},
            {"name": {"$regex": pattern, "$options": "i"}},
            {"company_name": {"$regex": pattern, "$options": "i"}},
            {"company": {"$regex": pattern, "$options": "i"}},
        ]
    }

    total = 0
    collections = await db.list_collection_names()
    for col_name in sorted(collections):
        col = db[col_name]
        # Compte d'abord
        n = await col.count_documents(query)
        if n == 0:
            continue
        # Détail des docs matchés
        docs = await col.find(
            query,
            {"_id": 0, "email": 1, "id": 1, "company_id": 1, "created_at": 1},
        ).limit(50).to_list(50)

        # 🛡️ Double check : rejet si un des docs contient un email protégé
        protected_hits = [d for d in docs if protected_regex.search(str(d.get("email") or ""))]
        if protected_hits:
            print(f"  ⚠️  SKIP {col_name}: {len(protected_hits)} doc(s) protégé(s)")
            for d in protected_hits:
                print(f"       · {d.get('email')}")
            continue

        print(f"  {'[DRY]' if dry_run else '[DEL]'} {col_name}: {n} doc(s)")
        for d in docs[:10]:
            print(f"     · {d.get('email') or d.get('id') or d}")
        if not dry_run:
            r = await col.delete_many(query)
            total += r.deleted_count

    print(f"\n{'✅ Total effacé' if not dry_run else '📋 Total (dry-run)'} : "
          f"{total if not dry_run else 'aucune suppression réelle'}")
    return total


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Purge par pattern d'email")
    ap.add_argument("pattern", help="Regex/substring à rechercher (min 3 caractères)")
    ap.add_argument("--dry-run", action="store_true", help="N'efface rien")
    args = ap.parse_args()
    n = asyncio.run(main(args.pattern, args.dry_run))
    sys.exit(0 if n >= 0 else 1)
