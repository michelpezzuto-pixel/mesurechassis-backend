"""🛡️ Endpoints admin one-shot pour maintenance rapide depuis un navigateur.

Ces endpoints sont **protégés par PLATFORM_ADMIN_TOKEN** (variable d'env
définie sur Railway prod). Un simple query param `?token=XXX` permet à
Michel d'exécuter des actions de nettoyage depuis Safari iPhone sans avoir
besoin d'un shell.

⚠️ SÉCURITÉ :
- Token doit être long et secret (utiliser `openssl rand -base64 48`).
- Ne PAS commit le token dans le code.
- Protection anti-effacement : impossible de toucher aux
  `@mesurechassis.fr` (protection en dur).
"""
from __future__ import annotations

import os
import re

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse

from db import db

router = APIRouter()

_PROTECTED_RE = re.compile(r"@mesurechassis\.fr$", re.IGNORECASE)


def _check_token(token: str) -> None:
    expected = os.getenv("PLATFORM_ADMIN_TOKEN", "").strip()
    if not expected:
        raise HTTPException(500, "PLATFORM_ADMIN_TOKEN non configuré côté serveur")
    if token != expected:
        raise HTTPException(401, "Token admin invalide")


def _html_page(*, title: str, body_html: str, is_error: bool = False) -> str:
    accent = "#ef4444" if is_error else "#22c55e"
    return f"""<!DOCTYPE html>
<html lang="fr"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — Admin MesureChâssis</title>
<style>
  body {{
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: #0a0a0a;
    color: #f5f5f5;
    min-height: 100vh;
    display: flex;
    justify-content: center;
    padding: 24px 16px;
  }}
  .wrap {{ max-width: 600px; width: 100%; }}
  .card {{
    background: #171717;
    border: 1px solid {accent};
    border-radius: 20px;
    padding: 28px 22px;
    margin-top: 20px;
  }}
  h1 {{
    font-size: 20px;
    margin: 0 0 16px;
    color: {accent};
    letter-spacing: 0.3px;
  }}
  h2 {{ font-size: 15px; color: #d4d4d4; margin: 20px 0 10px; }}
  p {{ font-size: 14px; line-height: 1.6; color: #a3a3a3; margin: 6px 0; }}
  code {{
    background: #262626;
    color: #f0c382;
    padding: 3px 8px;
    border-radius: 6px;
    font-size: 12.5px;
  }}
  .list {{
    background: #262626;
    border-radius: 10px;
    padding: 12px 14px;
    margin-top: 8px;
    max-height: 300px;
    overflow-y: auto;
  }}
  .list ul {{ margin: 0; padding-left: 18px; }}
  .list li {{ font-size: 12.5px; color: #d4d4d4; margin: 4px 0; }}
  .col {{ color: {accent}; font-weight: 700; }}
  .btn {{
    display: inline-block;
    margin-top: 20px;
    padding: 14px 22px;
    background: #ef4444;
    color: #fff;
    text-decoration: none;
    border-radius: 26px;
    font-weight: 800;
    font-size: 13px;
    letter-spacing: 0.5px;
  }}
  .btn.safe {{ background: #22c55e; }}
  .stats {{ font-size: 32px; font-weight: 900; color: {accent}; margin: 10px 0; }}
</style></head>
<body><div class="wrap">
  <h1>🛡️ ADMIN — {title}</h1>
  <div class="card">{body_html}</div>
</div></body></html>"""


@router.get("/admin/purge-email", response_class=HTMLResponse)
async def admin_purge_email(
    token: str = Query(..., description="PLATFORM_ADMIN_TOKEN"),
    pattern: str = Query(..., min_length=3, description="Pattern d'email (regex, insensible casse)"),
    confirm: str = Query("", description="Passer 'YES' pour exécuter, sinon dry-run"),
):
    """Purge par pattern d'email — accessible en un simple clic depuis
    Safari iPhone. Sans `confirm=YES` → mode dry-run (aperçu uniquement)."""
    _check_token(token)

    # 🛡️ Protection ABSOLUE — refus d'effacer @mesurechassis.fr
    if _PROTECTED_RE.search(pattern):
        return HTMLResponse(
            _html_page(
                title="OPÉRATION REFUSÉE",
                body_html=(
                    "<p>Pattern <code>{}</code> refusé : impossible d'effacer "
                    "les comptes <code>@mesurechassis.fr</code>.</p>".format(pattern)
                ),
                is_error=True,
            ),
            status_code=403,
        )

    dry = confirm != "YES"

    # Query MongoDB
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

    total_found = 0
    total_deleted = 0
    details_per_col = []

    for col_name in sorted(await db.list_collection_names()):
        col = db[col_name]
        n = await col.count_documents(query)
        if n == 0:
            continue

        # Sample des emails trouvés
        docs = await col.find(
            query, {"_id": 0, "email": 1, "client_email": 1, "id": 1}
        ).limit(20).to_list(20)
        samples = [
            d.get("email") or d.get("client_email") or d.get("id") or "?"
            for d in docs
        ]
        # Skip si protégé
        protected = [s for s in samples if _PROTECTED_RE.search(str(s or ""))]
        if protected:
            details_per_col.append(
                {"col": col_name, "count": n, "skipped": True, "samples": protected[:5]}
            )
            continue

        total_found += n
        if not dry:
            r = await col.delete_many(query)
            total_deleted += r.deleted_count

        details_per_col.append(
            {"col": col_name, "count": n, "skipped": False, "samples": samples[:8]}
        )

    # HTML output
    if not details_per_col:
        return HTMLResponse(
            _html_page(
                title="AUCUN RÉSULTAT",
                body_html=f"<p>Aucun document ne contient <code>{pattern}</code> "
                          f"dans la base actuelle.</p>",
                is_error=False,
            )
        )

    rows_html = ""
    for d in details_per_col:
        skip_mark = ' (⛔ ignoré protection)' if d["skipped"] else ''
        rows_html += (
            f"<h2>{d['col']} — <span class='col'>{d['count']} doc(s){skip_mark}</span></h2>"
            f"<div class='list'><ul>"
            + "".join(f"<li>{s}</li>" for s in d["samples"])
            + "</ul></div>"
        )

    if dry:
        # Lien de confirmation
        confirm_url = f"?token={token}&pattern={pattern}&confirm=YES"
        body = (
            f"<p><b>Aperçu (aucune suppression réelle)</b></p>"
            f"<div class='stats'>{total_found} docs</div>"
            f"<p>seraient supprimés si vous confirmez.</p>"
            + rows_html
            + f"<p style='margin-top:24px'><b>Pour confirmer, tape :</b></p>"
              f'<a class="btn" href="{confirm_url}">🗑️ CONFIRMER LA SUPPRESSION</a>'
        )
        return HTMLResponse(_html_page(title=f"APERÇU · pattern={pattern}", body_html=body))

    # Réalisée
    body = (
        f"<p><b>✅ Suppression effectuée avec succès.</b></p>"
        f"<div class='stats'>{total_deleted} docs supprimés</div>"
        f"<p>Vous pouvez maintenant vous réinscrire avec cet email.</p>"
        + rows_html
    )
    return HTMLResponse(_html_page(title=f"PURGE OK · pattern={pattern}", body_html=body))
