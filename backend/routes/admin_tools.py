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

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse

from db import db

router = APIRouter()

_PROTECTED_RE = re.compile(r"@mesurechassis\.fr$", re.IGNORECASE)

# 🗺️ v1.1.3 — JWT court-vécu signé avec le PLATFORM_ADMIN_TOKEN comme secret.
#   Le mobile appelle `/admin/map/access-link` (auth JWT user habituel + platform
#   owner) → reçoit une URL `?token=<short_jwt>` valide 5 min. Il ouvre l'URL
#   dans Safari via Linking → le navigateur accède aux endpoints admin/map
#   sans jamais voir le PLATFORM_ADMIN_TOKEN long-vécu.
_MAP_JWT_SCOPE = "admin_map"
_MAP_JWT_TTL_MIN = 15  # 🆕 15 min (auparavant 5) — plus tolérant sur ouverture lente


def _check_token(token: str) -> None:
    """Autorise soit le PLATFORM_ADMIN_TOKEN long-vécu, soit un JWT court-vécu
    de scope 'admin_map' signé avec ce token comme secret (voir
    /admin/map/access-link)."""
    expected = os.getenv("PLATFORM_ADMIN_TOKEN", "").strip()
    if not expected:
        raise HTTPException(500, "PLATFORM_ADMIN_TOKEN non configuré côté serveur")
    if token == expected:
        return  # ✅ Token statique (usage terminal / lien direct)
    # Tentative JWT court-vécu
    try:
        import jwt as _jwt  # local import — pyjwt déjà installé (Apple Sign-In)
        # leeway=10s pour tolérer un léger décalage d'horloge entre serveurs
        claims = _jwt.decode(token, expected, algorithms=["HS256"], leeway=10)
    except Exception as e:
        # 🆕 Messages d'erreur explicites pour faciliter le debug côté client
        err_name = type(e).__name__
        if err_name == "ExpiredSignatureError":
            raise HTTPException(
                401,
                "Lien expiré (valide 5 min). Retourne dans l'app et clique à nouveau sur Carte.",
            ) from None
        if err_name == "InvalidSignatureError":
            raise HTTPException(
                401,
                "Signature invalide — clé serveur différente entre génération et validation.",
            ) from None
        if err_name in ("DecodeError", "InvalidTokenError"):
            raise HTTPException(
                401,
                f"Token malformé ({err_name}). Retourne dans l'app et régénère un lien.",
            ) from None
        # Fallback avec type d'erreur pour debug
        raise HTTPException(401, f"Token admin invalide ({err_name})") from None
    if claims.get("scope") != _MAP_JWT_SCOPE:
        raise HTTPException(401, "Token admin invalide (scope)")


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



# ══════════════════════════════════════════════════════════════════════
# 🗺️ CARTE DES MENUISIERS INSCRITS
# ══════════════════════════════════════════════════════════════════════

# Domaines et emails considérés comme "techniques" (à exclure du décompte
# des vrais menuisiers). Utilisé par le filtre `exclude_owner=true`.
# On aggrège plusieurs sources pour être robuste :
#   1. PLATFORM_OWNER_EMAILS (Michel + ses alias personnels)
#   2. Domaines internes MesureChâssis
#   3. Comptes de démo / test récurrents
_TECH_EMAIL_DOMAINS = {
    "mesurechassis.fr",
    "mesurechassis.com",
    "mesurechassis.be",
    "bruxmove.be",
    "bruxmove.com",
}
_TECH_EMAIL_HARDCODED = {
    "applereview@mesurechassis.com",
    "admin@mesurechassis.fr",
    "artisan@mesurechassis.fr",
    "michelpezzuto@gmail.com",
    "michelpezzuto@hotmail.com",
    "info@mesurechassis.com",
}


def _is_technical_account(email: str) -> bool:
    """Retourne True si l'email appartient à Michel, à un compte de test,
    ou à un domaine interne MesureChâssis / Bruxmove."""
    from deps import PLATFORM_OWNER_EMAILS

    email_lower = (email or "").lower().strip()
    if not email_lower or "@" not in email_lower:
        return False
    if email_lower in PLATFORM_OWNER_EMAILS:
        return True
    if email_lower in _TECH_EMAIL_HARDCODED:
        return True
    domain = email_lower.rsplit("@", 1)[-1]
    if domain in _TECH_EMAIL_DOMAINS:
        return True
    return False


# ══════════════════════════════════════════════════════════════════════
# 🗺️ v1.1.3 — Accès mobile à la carte via lien signé (JWT 5 min)
# ══════════════════════════════════════════════════════════════════════
from deps import require_platform_owner  # noqa: E402


def _generate_map_jwt() -> str:
    """Crée un JWT court-vécu signé avec le PLATFORM_ADMIN_TOKEN comme secret."""
    import jwt as _jwt
    from datetime import datetime, timezone, timedelta

    expected = os.getenv("PLATFORM_ADMIN_TOKEN", "").strip()
    if not expected:
        raise HTTPException(500, "PLATFORM_ADMIN_TOKEN non configuré côté serveur")
    payload = {
        "scope": _MAP_JWT_SCOPE,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=_MAP_JWT_TTL_MIN),
    }
    return _jwt.encode(payload, expected, algorithm="HS256")


@router.post("/admin/map/access-link")
async def admin_map_access_link(
    request: Request,
    user: dict = Depends(require_platform_owner),
):
    """Génère un lien temporaire (15 min) vers la carte HTML admin.

    Requiert : platform owner (email dans PLATFORM_OWNER_EMAILS).
    Le lien retourné peut être ouvert dans un navigateur ou un WebView —
    il embarque un JWT signé à durée courte.

    🔒 IMPORTANT : le `map_url` retourné pointe vers CE MÊME SERVEUR (celui
    qui a signé le JWT). C'est indispensable car le JWT est signé avec le
    PLATFORM_ADMIN_TOKEN local — un autre serveur avec un token différent
    rejetterait la signature.
    """
    short_jwt = _generate_map_jwt()
    # 🆕 Base URL dynamique : on utilise l'URL du serveur qui a reçu la requête
    # (via header X-Forwarded-Proto/Host si derrière un proxy, sinon request.url).
    # Priorité : env MAP_PUBLIC_BASE_URL > URL de la requête courante.
    env_base = os.getenv("MAP_PUBLIC_BASE_URL", "").strip().rstrip("/")
    if env_base:
        base = env_base
    else:
        # Reconstruit "scheme://host" depuis la requête courante
        scheme = request.headers.get("x-forwarded-proto") or request.url.scheme
        host = request.headers.get("x-forwarded-host") or request.url.netloc
        base = f"{scheme}://{host}"
    map_url = f"{base}/api/admin/map?token={short_jwt}&exclude_owner=true"
    data_url = f"{base}/api/admin/map/data?token={short_jwt}&exclude_owner=true"
    return {
        "map_url": map_url,
        "data_url": data_url,
        "expires_in_seconds": _MAP_JWT_TTL_MIN * 60,
    }


@router.get("/admin/map/data")
async def admin_map_data(
    token: str = Query(..., description="PLATFORM_ADMIN_TOKEN"),
    days: int = Query(0, description="Filtre : inscrits derniers N jours (0=tous)"),
    only_active: bool = Query(False, description="Filtre : uniquement comptes actifs"),
    exclude_owner: bool = Query(
        False,
        description=(
            "Exclut Michel (PLATFORM_OWNER_EMAILS + @bruxmove + comptes de test). "
            "Utiliser pour connaître le vrai volume d'usage extérieur."
        ),
    ),
):
    """JSON des utilisateurs inscrits avec leur géoloc (ville).

    Réponse enrichie :
    - `points[].account_type` : `real` (vrai menuisier) | `technical` (Michel/test)
    - `real_users_count` : nombre de vrais menuisiers (hors comptes techniques)
    - `technical_users_count` : comptes techniques identifiés
    """
    _check_token(token)

    from datetime import datetime, timedelta, timezone

    match: dict = {"status": {"$in": ["active", "pending_verification"]}}
    if only_active:
        match["status"] = "active"
    if days > 0:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        match["created_at"] = {"$gte": cutoff}

    projection = {
        "_id": 0,
        "id": 1,
        "email": 1,
        "name": 1,
        "role": 1,
        "status": 1,
        "created_at": 1,
        "google_linked": 1,
        "signup_geo": 1,
        "last_login_at": 1,
        "company_id": 1,
    }

    users = await db.users.find(match, projection).to_list(length=5000)

    # Aggrégations par région / pays (uniquement sur les vrais menuisiers
    # si exclude_owner=True, pour ne pas polluer les stats)
    by_region: dict = {}
    by_country: dict = {}
    total_with_geo = 0
    total_without_geo = 0
    real_users_count = 0
    technical_users_count = 0

    points: list = []
    for u in users:
        email_full = u.get("email") or ""
        is_tech = _is_technical_account(email_full)

        # Filtre : si exclude_owner, on saute les techniques
        if exclude_owner and is_tech:
            technical_users_count += 1
            continue

        if is_tech:
            technical_users_count += 1
        else:
            real_users_count += 1

        geo = u.get("signup_geo") or {}
        # Anonymisation légère : masquer l'email en public
        masked_email = email_full
        if "@" in email_full:
            local, domain = email_full.split("@", 1)
            if len(local) > 3:
                masked_email = f"{local[:2]}***@{domain}"

        item = {
            "id": u.get("id"),
            "email": masked_email,
            "email_full": email_full,
            "name": u.get("name") or "",
            "role": u.get("role") or "admin",
            "created_at": u.get("created_at"),
            "last_login_at": u.get("last_login_at"),
            "google_linked": bool(u.get("google_linked")),
            "status": u.get("status"),
            "company_id": u.get("company_id"),
            "city": geo.get("city") or "",
            "region": geo.get("region") or "",
            "country": geo.get("country") or "",
            "country_code": geo.get("country_code") or "",
            "lat": geo.get("lat"),
            "lng": geo.get("lng"),
            # 🆕 Distinction visuelle pour la carte HTML
            "account_type": "technical" if is_tech else "real",
        }
        if geo.get("lat") and geo.get("lng"):
            total_with_geo += 1
        else:
            total_without_geo += 1
        # Compteurs (uniquement pour ce qui est affiché, donc respecte filtre)
        r_key = geo.get("region") or "(inconnu)"
        c_key = geo.get("country") or "(inconnu)"
        by_region[r_key] = by_region.get(r_key, 0) + 1
        by_country[c_key] = by_country.get(c_key, 0) + 1
        points.append(item)

    return {
        "total": len(points),
        "with_geo": total_with_geo,
        "without_geo": total_without_geo,
        # 🆕 Distinction claire vrai vs technique
        "real_users_count": real_users_count,
        "technical_users_count": technical_users_count,
        "excluded_owner": exclude_owner,
        "by_region": by_region,
        "by_country": by_country,
        "points": points,
    }


@router.get("/admin/map", response_class=HTMLResponse)
async def admin_map_html(
    token: str = Query(..., description="PLATFORM_ADMIN_TOKEN"),
):
    """Page HTML interactive avec Leaflet + OpenStreetMap. Aucune clé API
    requise. Charge les données via `/admin/map/data` en JSON."""
    _check_token(token)

    # HTML complet : Leaflet CDN + JS pour fetcher /admin/map/data
    html = """<!DOCTYPE html>
<html lang="fr"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Carte des menuisiers - Admin MesureChâssis</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css">
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { height: 100%; font-family: -apple-system, "Segoe UI", Roboto, sans-serif; background: #0a0a0a; color: #f5f5f5; }
  .app { display: flex; flex-direction: column; height: 100vh; }
  header {
    background: #0a0a0c; border-bottom: 1px solid #262626;
    padding: 14px 18px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px;
  }
  h1 { font-size: 17px; font-weight: 800; letter-spacing: -0.3px; }
  h1 span { color: #FF5A00; }
  .filters { display: flex; gap: 8px; flex-wrap: wrap; }
  .filters button {
    background: #1a1a1e; border: 1px solid #262626; color: #d4d4d4;
    padding: 8px 14px; border-radius: 999px; font-size: 12px; font-weight: 600; cursor: pointer;
    transition: all .15s ease;
  }
  .filters button:hover { background: #262626; }
  .filters button.active { background: #FF5A00; color: #0a0a0a; border-color: #FF5A00; }
  .stats-bar {
    display: flex; gap: 18px; padding: 10px 18px; background: #131315;
    border-bottom: 1px solid #262626; flex-wrap: wrap;
  }
  .stat { display: flex; flex-direction: column; }
  .stat-value { font-size: 20px; font-weight: 900; color: #FF5A00; letter-spacing: -0.5px; }
  .stat-label { font-size: 10.5px; color: #a3a3a3; text-transform: uppercase; letter-spacing: 0.7px; margin-top: 2px; }
  .main { flex: 1; display: flex; overflow: hidden; }
  #map { flex: 1; background: #1a1a1e; }
  aside {
    width: 320px; background: #131315; border-left: 1px solid #262626;
    overflow-y: auto; padding: 16px 14px;
  }
  aside h2 { font-size: 12px; text-transform: uppercase; letter-spacing: 1.2px; color: #a3a3a3; margin-bottom: 10px; }
  .region-row { display: flex; justify-content: space-between; padding: 8px 10px; border-radius: 8px; font-size: 13px; }
  .region-row:nth-child(odd) { background: #1a1a1e; }
  .region-count { color: #FF5A00; font-weight: 800; }
  .empty { color: #737373; font-size: 12px; padding: 12px; text-align: center; }
  .loading { position: absolute; top: 50%; left: 50%; transform: translate(-50%,-50%); color: #FF5A00; font-weight: 700; z-index: 999; }
  .leaflet-popup-content { color: #0a0a0c; font-family: inherit; }
  .leaflet-popup-content b { color: #FF5A00; }
  @media (max-width: 780px) {
    aside { display: none; }
  }
</style></head><body>
<div class="app">
  <header>
    <h1>🗺️ Carte des menuisiers <span>MesureChâssis</span></h1>
    <div class="filters" id="filters">
      <button data-days="0" class="active">Tous</button>
      <button data-days="7">7 jours</button>
      <button data-days="30">30 jours</button>
      <button data-days="90">90 jours</button>
      <button data-active="1">Actifs uniquement</button>
      <button data-exclude-owner="1" style="border-color:#22c55e;color:#22c55e">👤 Vrais menuisiers</button>
    </div>
  </header>
  <div class="stats-bar" id="stats"></div>
  <div class="main">
    <div id="map"></div>
    <aside>
      <h2>Par région</h2>
      <div id="regions"></div>
      <h2 style="margin-top:20px">Par pays</h2>
      <div id="countries"></div>
      <h2 style="margin-top:20px">Légende</h2>
      <div style="font-size:12px;color:#a3a3a3;line-height:1.8">
        <div><span style="display:inline-block;width:12px;height:12px;background:#22c55e;border-radius:50%;vertical-align:middle;margin-right:6px"></span>Vrai menuisier</div>
        <div><span style="display:inline-block;width:12px;height:12px;background:#3b82f6;border-radius:50%;vertical-align:middle;margin-right:6px"></span>Compte technique (toi, test, Apple)</div>
      </div>
    </aside>
  </div>
</div>
<script>
(function(){
  var TOKEN = new URLSearchParams(location.search).get("token");
  var API_BASE = "/api/admin/map/data";
  var state = { days: 0, only_active: false, exclude_owner: false };

  // Carte centrée sur la Belgique
  var map = L.map("map", { zoomControl: true }).setView([50.5, 4.5], 7);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '© OpenStreetMap',
    maxZoom: 18
  }).addTo(map);

  var cluster = L.markerClusterGroup({ maxClusterRadius: 45 });
  map.addLayer(cluster);

  function pinIcon(type) {
    // 🟢 vert = vrai menuisier | 🔵 bleu = compte technique (Michel/test)
    var color = type === "real" ? "#22c55e" : "#3b82f6";
    var shadow = type === "real" ? "rgba(34,197,94,0.5)" : "rgba(59,130,246,0.5)";
    return L.divIcon({
      className: "mc-pin",
      html: '<div style="width:22px;height:22px;background:' + color +
            ';border:3px solid #0a0a0c;border-radius:50%;box-shadow:0 4px 10px ' + shadow + '"></div>',
      iconSize: [22,22], iconAnchor: [11,11]
    });
  }

  function fmtDate(iso) {
    if (!iso) return "-";
    try { return new Date(iso).toLocaleDateString("fr-BE"); } catch(e) { return iso; }
  }

  function renderStats(d) {
    var realBadge = '<div class="stat"><div class="stat-value" style="color:#22c55e">' + (d.real_users_count||0) + '</div><div class="stat-label">Vrais menuisiers</div></div>';
    var techBadge = '<div class="stat"><div class="stat-value" style="color:#3b82f6">' + (d.technical_users_count||0) + '</div><div class="stat-label">Comptes techniques</div></div>';
    document.getElementById("stats").innerHTML =
      '<div class="stat"><div class="stat-value">' + d.total + '</div><div class="stat-label">Affichés</div></div>' +
      realBadge + techBadge +
      '<div class="stat"><div class="stat-value">' + d.with_geo + '</div><div class="stat-label">Géolocalisés</div></div>' +
      '<div class="stat"><div class="stat-value">' + d.without_geo + '</div><div class="stat-label">Sans géoloc</div></div>' +
      '<div class="stat"><div class="stat-value">' + Object.keys(d.by_country).length + '</div><div class="stat-label">Pays</div></div>';
  }

  function renderList(target, obj) {
    var entries = Object.entries(obj).sort(function(a,b){ return b[1]-a[1]; });
    if (!entries.length) { target.innerHTML = '<div class="empty">Aucune donnée</div>'; return; }
    target.innerHTML = entries.map(function(e){
      return '<div class="region-row"><span>' + e[0] + '</span><span class="region-count">' + e[1] + '</span></div>';
    }).join("");
  }

  function load() {
    cluster.clearLayers();
    var params = new URLSearchParams({
      token: TOKEN,
      days: state.days,
      only_active: state.only_active,
      exclude_owner: state.exclude_owner,
    });
    fetch(API_BASE + "?" + params.toString())
      .then(function(r){ return r.json(); })
      .then(function(d){
        renderStats(d);
        renderList(document.getElementById("regions"), d.by_region);
        renderList(document.getElementById("countries"), d.by_country);
        d.points.forEach(function(p){
          if (!p.lat || !p.lng) return;
          // Léger jitter pour éviter la superposition parfaite (multi-inscrits même ville)
          var jitter = 0.008;
          var lat = p.lat + (Math.random()-0.5) * jitter;
          var lng = p.lng + (Math.random()-0.5) * jitter;
          var typeLabel = p.account_type === "real"
            ? '<span style="color:#22c55e;font-weight:700">👷 Vrai menuisier</span>'
            : '<span style="color:#3b82f6;font-weight:700">🛠️ Compte technique</span>';
          var pop = '<b>' + (p.name || p.email) + '</b><br>' +
                    typeLabel + '<br>' +
                    (p.city || "?") + (p.region ? ", " + p.region : "") + '<br>' +
                    '📅 Inscrit : ' + fmtDate(p.created_at) + '<br>' +
                    (p.google_linked ? '🔑 Google' : '✉️ Email') + ' · <i>' + p.status + '</i><br>' +
                    '<small style="color:#666">' + p.email + '</small>';
          L.marker([lat, lng], { icon: pinIcon(p.account_type) })
            .bindPopup(pop)
            .addTo(cluster);
        });
      })
      .catch(function(err){ console.error(err); alert("Erreur chargement : " + err.message); });
  }

  document.getElementById("filters").addEventListener("click", function(e){
    if (e.target.tagName !== "BUTTON") return;
    var btn = e.target;
    if (btn.dataset.days !== undefined) {
      state.days = parseInt(btn.dataset.days, 10);
      state.only_active = false;
      Array.from(document.querySelectorAll("#filters button[data-days]")).forEach(function(b){ b.classList.remove("active"); });
      btn.classList.add("active");
    } else if (btn.dataset.active !== undefined) {
      state.only_active = !state.only_active;
      btn.classList.toggle("active", state.only_active);
    } else if (btn.dataset.excludeOwner !== undefined) {
      state.exclude_owner = !state.exclude_owner;
      btn.classList.toggle("active", state.exclude_owner);
    }
    load();
  });

  load();
})();
</script>
</body></html>"""

    return HTMLResponse(html)


# ══════════════════════════════════════════════════════════════════════
# 🌍 BACKFILL RÉTROACTIF de la géolocalisation
# ══════════════════════════════════════════════════════════════════════
@router.get("/admin/map/backfill", response_class=HTMLResponse)
async def admin_map_backfill(
    token: str = Query(..., description="PLATFORM_ADMIN_TOKEN"),
    confirm: str = Query("", description="Passer 'YES' pour exécuter"),
):
    """Applique une géolocalisation par défaut aux comptes déjà inscrits
    qui n'ont pas de `signup_geo` (comptes créés avant l'ajout de la
    géoloc automatique). Par défaut → Bruxelles, Belgique. Le vrai
    remplissage se fera au fil des connexions."""
    _check_token(token)

    dry = confirm != "YES"

    # Coordonnées par défaut = Bruxelles (fondateur belge)
    default_geo = {
        "city": "Bruxelles",
        "region": "Région de Bruxelles-Capitale",
        "country": "Belgique",
        "country_code": "BE",
        "lat": 50.8503,
        "lng": 4.3517,
        "source": "backfill_default",
    }

    query = {"signup_geo": {"$exists": False}}
    n = await db.users.count_documents(query)

    if dry:
        confirm_url = f"?token={token}&confirm=YES"
        body = (
            f"<p><b>Aperçu — {n} utilisateur(s) sans géoloc.</b></p>"
            f"<div class='stats'>{n}</div>"
            f"<p>Seront tagués comme <code>Bruxelles, Belgique</code> "
            f"(coordonnées par défaut) si vous confirmez. Les prochaines "
            f"connexions/inscriptions rempliront progressivement les vraies "
            f"villes.</p>"
            f'<a class="btn" href="{confirm_url}">🌍 CONFIRMER LE BACKFILL</a>'
        )
        return HTMLResponse(_html_page(title="APERÇU BACKFILL GÉOLOC", body_html=body))

    result = await db.users.update_many(query, {"$set": {"signup_geo": default_geo}})
    body = (
        f"<p><b>✅ Backfill effectué.</b></p>"
        f"<div class='stats'>{result.modified_count} comptes tagués</div>"
        f"<p>Tous les comptes existants sont désormais visibles sur la carte "
        f"(par défaut à Bruxelles). Les nouveaux inscrits auront leur vraie "
        f"ville détectée via IP.</p>"
    )
    return HTMLResponse(_html_page(title="BACKFILL OK", body_html=body))


# ══════════════════════════════════════════════════════════════════════
# 📊 Juin 2026 — Dashboard "Traction réelle" (owner-only)
#
# Distingue les vrais utilisateurs actifs des inscrits fantômes.
# KPIs affichés :
#   - Total inscrits & vrais menuisiers (non-techniques)
#   - Actifs 7j / 30j (basé sur last_login_at)
#   - Ont créé ≥ 1 chantier / ≥ 5 ouvertures mesurées
#   - Emails suspects (domaines jetables)
#   - Répartition par pays
#   - 20 derniers inscrits avec activité
# ══════════════════════════════════════════════════════════════════════

_DISPOSABLE_EMAIL_DOMAINS = {
    "yopmail.com", "yopmail.fr", "mailinator.com", "guerrillamail.com",
    "guerrillamail.net", "guerrillamail.info", "guerrillamail.biz",
    "10minutemail.com", "10minutemail.net", "tempmail.com", "temp-mail.org",
    "throwawaymail.com", "getnada.com", "sharklasers.com", "trashmail.com",
    "trashmail.io", "maildrop.cc", "mohmal.com", "dispostable.com",
    "mytemp.email", "moakt.com", "emailondeck.com", "fakeinbox.com",
    "spam4.me", "burnermail.io",
}


def _is_suspicious_email(email: str) -> bool:
    if not email or "@" not in email:
        return True
    domain = email.rsplit("@", 1)[-1].lower().strip()
    return domain in _DISPOSABLE_EMAIL_DOMAINS


async def _compute_traction_stats() -> dict:
    """Calcule les KPIs de traction réelle depuis la base."""
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    d7 = now - timedelta(days=7)
    d30 = now - timedelta(days=30)

    total = 0
    real = 0
    technical = 0
    active_7d = 0
    active_30d = 0
    suspicious = 0
    with_chantier = 0
    with_5_ouvertures = 0
    by_country: dict[str, int] = {}
    signup_dates_7d = 0
    signup_dates_30d = 0
    latest_signups: list[dict] = []

    cursor = db.users.find(
        {},
        {
            "id": 1,
            "email": 1,
            "name": 1,
            "role": 1,
            "created_at": 1,
            "last_login_at": 1,
            "signup_geo": 1,
            "company_id": 1,
            "google_linked": 1,
            "status": 1,
        },
    )

    async for u in cursor:
        total += 1
        email = (u.get("email") or "").lower().strip()
        is_tech = _is_technical_account(email)
        if is_tech:
            technical += 1
            continue
        real += 1

        # Activité
        ll = u.get("last_login_at")
        if isinstance(ll, datetime):
            if ll.tzinfo is None:
                ll = ll.replace(tzinfo=timezone.utc)
            if ll >= d7:
                active_7d += 1
            if ll >= d30:
                active_30d += 1

        # Ancienneté du signup
        ca = u.get("created_at")
        if isinstance(ca, datetime):
            if ca.tzinfo is None:
                ca = ca.replace(tzinfo=timezone.utc)
            if ca >= d7:
                signup_dates_7d += 1
            if ca >= d30:
                signup_dates_30d += 1
            latest_signups.append({
                "email": email,
                "name": u.get("name") or "",
                "created_at": ca,
                "last_login_at": ll if isinstance(ll, datetime) else None,
                "company_id": u.get("company_id"),
                "google_linked": bool(u.get("google_linked")),
                "status": u.get("status") or "active",
                "signup_geo": u.get("signup_geo") or {},
            })

        # Emails suspects
        if _is_suspicious_email(email):
            suspicious += 1

        # Répartition par pays
        geo = u.get("signup_geo") or {}
        country = (geo.get("country") or "(inconnu)").strip() or "(inconnu)"
        by_country[country] = by_country.get(country, 0) + 1

        # Compter chantiers/ouvertures pour ce user
        company_id = u.get("company_id")
        if company_id:
            n_chantiers = await db.chantiers.count_documents(
                {"company_id": company_id}, limit=1
            )
            if n_chantiers > 0:
                with_chantier += 1

    # Pour compter ceux qui ont ≥5 ouvertures, on remonte via chantiers → ouvertures
    # Aggregation par company_id
    pipeline = [
        {"$unwind": "$ouvertures"},
        {"$group": {"_id": "$company_id", "n": {"$sum": 1}}},
        {"$match": {"n": {"$gte": 5}}},
    ]
    companies_with_5plus = 0
    async for _doc in db.chantiers.aggregate(pipeline):
        companies_with_5plus += 1

    # Tri des 20 derniers signups
    latest_signups.sort(key=lambda x: x["created_at"], reverse=True)
    latest_signups = latest_signups[:20]

    return {
        "total": total,
        "real": real,
        "technical": technical,
        "signups_7d": signup_dates_7d,
        "signups_30d": signup_dates_30d,
        "active_7d": active_7d,
        "active_30d": active_30d,
        "with_chantier": with_chantier,
        "companies_with_5plus_openings": companies_with_5plus,
        "suspicious_emails": suspicious,
        "by_country": by_country,
        "latest_signups": latest_signups,
    }


@router.get("/admin/traction", response_class=HTMLResponse)
async def admin_traction_dashboard(
    token: str = Query(..., description="PLATFORM_ADMIN_TOKEN ou JWT scope admin_map"),
):
    """Dashboard HTML de traction réelle — accès via lien JWT court-vécu."""
    _check_token(token)
    stats = await _compute_traction_stats()

    # % actifs sur vrais menuisiers
    real = stats["real"] or 1
    pct_active_7d = round(stats["active_7d"] / real * 100, 1)
    pct_active_30d = round(stats["active_30d"] / real * 100, 1)
    pct_with_chantier = round(stats["with_chantier"] / real * 100, 1)

    # Verdict global honnête
    if pct_active_30d < 5:
        verdict = "🔴 Traction faible — la majorité des inscrits n'a jamais réutilisé l'app"
        verdict_color = "#dc2626"
    elif pct_active_30d < 20:
        verdict = "🟡 Traction moyenne — beaucoup d'inscrits fantômes, mais un noyau existe"
        verdict_color = "#d97706"
    elif pct_active_30d < 50:
        verdict = "🟢 Bonne traction — engagement solide chez tes vrais utilisateurs"
        verdict_color = "#16a34a"
    else:
        verdict = "🚀 Excellente traction — tu as une vraie base fidèle"
        verdict_color = "#059669"

    # Pays
    country_rows = "".join(
        f"<tr><td>{c}</td><td style='text-align:right'>{n}</td></tr>"
        for c, n in sorted(stats["by_country"].items(), key=lambda x: -x[1])[:10]
    )

    # 20 derniers inscrits
    from datetime import datetime, timezone

    def _fmt_dt(dt):
        if not dt:
            return "<i style='color:#666'>jamais</i>"
        if isinstance(dt, str):
            return dt[:10]
        return dt.strftime("%d/%m/%Y %H:%M")

    def _row_bg(u):
        # rouge = suspect ; gris = jamais reconnecté ; blanc = OK
        if _is_suspicious_email(u["email"]):
            return "background:#fee2e2"
        if not u.get("last_login_at"):
            return "background:#f3f4f6;color:#666"
        return ""

    latest_rows = "".join(
        f"<tr style='{_row_bg(u)}'>"
        f"<td>{_fmt_dt(u['created_at'])}</td>"
        f"<td>{u['email']}</td>"
        f"<td>{u.get('name') or '<i style=color:#999>—</i>'}</td>"
        f"<td>{_fmt_dt(u.get('last_login_at'))}</td>"
        f"<td>{'🔵 Google' if u.get('google_linked') else '📧 Email'}</td>"
        f"<td>{(u.get('signup_geo') or {}).get('country') or '<i>?</i>'}</td>"
        f"</tr>"
        for u in stats["latest_signups"]
    )

    body = f"""
    <style>
      .verdict {{ text-align: center; }}
      .kpi-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 12px;
        margin: 12px 0 24px;
      }}
      .kpi {{
        background: #262626;
        border-radius: 12px;
        padding: 14px 12px;
        text-align: center;
      }}
      .kpi .v {{ font-size: 30px; font-weight: 900; color: #22c55e; line-height: 1.1; }}
      .kpi .l {{ font-size: 11px; color: #a3a3a3; margin-top: 6px; letter-spacing: 0.4px; text-transform: uppercase; }}
      .kpi .l small {{ display: block; color: #737373; text-transform: none; font-size: 11px; margin-top: 3px; }}
      table {{
        width: 100%;
        border-collapse: collapse;
        margin-top: 10px;
        background: #1a1a1a;
        border-radius: 10px;
        overflow: hidden;
        font-size: 12.5px;
      }}
      thead th {{
        background: #262626;
        color: #d4d4d4;
        text-align: left;
        padding: 10px 10px;
        font-size: 11.5px;
        font-weight: 700;
        letter-spacing: 0.4px;
        text-transform: uppercase;
      }}
      tbody td {{
        padding: 8px 10px;
        border-top: 1px solid #262626;
        color: #e5e5e5;
      }}
      tbody tr:hover td {{ background: #262626; }}
    </style>

    <div class='verdict' style='background:{verdict_color};color:white;padding:16px;border-radius:12px;font-size:15px;font-weight:600;margin-bottom:24px'>
        {verdict}
    </div>

    <h2>📊 KPIs Traction Réelle</h2>
    <div class='kpi-grid'>
      <div class='kpi'><div class='v'>{stats['real']}</div><div class='l'>VRAIS MENUISIERS<br><small>(hors techniques)</small></div></div>
      <div class='kpi'><div class='v' style='color:#22c55e'>{stats['active_7d']}</div><div class='l'>ACTIFS 7j<br><small>{pct_active_7d}%</small></div></div>
      <div class='kpi'><div class='v' style='color:#0891b2'>{stats['active_30d']}</div><div class='l'>ACTIFS 30j<br><small>{pct_active_30d}%</small></div></div>
      <div class='kpi'><div class='v' style='color:#f97316'>{stats['with_chantier']}</div><div class='l'>ONT CRÉÉ ≥ 1 CHANTIER<br><small>{pct_with_chantier}%</small></div></div>
      <div class='kpi'><div class='v' style='color:#a855f7'>{stats['companies_with_5plus_openings']}</div><div class='l'>ENTREPRISES ≥ 5 OUVERTURES<br><small>vrais utilisateurs</small></div></div>
      <div class='kpi'><div class='v' style='color:#ef4444'>{stats['suspicious_emails']}</div><div class='l'>EMAILS SUSPECTS<br><small>(domaines jetables)</small></div></div>
    </div>

    <h2>📈 Croissance récente</h2>
    <div class='kpi-grid'>
      <div class='kpi'><div class='v'>{stats['signups_7d']}</div><div class='l'>INSCRIPTIONS 7 derniers jours</div></div>
      <div class='kpi'><div class='v'>{stats['signups_30d']}</div><div class='l'>INSCRIPTIONS 30 derniers jours</div></div>
      <div class='kpi'><div class='v' style='color:#94a3b8'>{stats['technical']}</div><div class='l'>COMPTES TECHNIQUES<br><small>(Michel, tests, internes)</small></div></div>
    </div>

    <h2>🌍 Répartition par pays (top 10)</h2>
    <table>
      <thead><tr><th>Pays</th><th style='text-align:right'>Nb inscrits</th></tr></thead>
      <tbody>{country_rows}</tbody>
    </table>

    <h2>🕐 20 derniers inscrits</h2>
    <p style='color:#666;font-size:13px'>
      🔴 fond rouge = email suspect (domaine jetable) &nbsp;·&nbsp;
      ⚪ fond gris = jamais reconnecté depuis inscription
    </p>
    <table>
      <thead><tr>
        <th>Inscription</th><th>Email</th><th>Nom</th>
        <th>Dernière connexion</th><th>Type</th><th>Pays</th>
      </tr></thead>
      <tbody>{latest_rows}</tbody>
    </table>

    <p style='margin-top:32px;color:#666;font-size:13px;line-height:1.6'>
      💡 <b>Comment interpréter</b> : le vrai KPI de traction est le taux <b>ACTIFS 30j</b>
      sur vrais menuisiers. Un ratio &lt; 15% signifie que la majorité de tes inscrits
      testent l'app une fois et disparaissent. Un ratio &gt; 30% indique un vrai
      product-market fit qui se construit.
    </p>

    <h2>📥 Exports CSV (pour campagne emailing Resend/Mailchimp)</h2>
    <p style='color:#a3a3a3;font-size:13px;margin-bottom:12px'>
      Les fichiers sont ouvrables dans Excel / Google Sheets. Séparateur : point-virgule.
      Encodage UTF-8 avec BOM (accents préservés).
    </p>
    <div style='display:flex;flex-wrap:wrap;gap:10px;margin-top:8px'>
      <a class='btn safe' href='/api/admin/traction/export.csv?token={token}&segment=all'
         style='background:#22c55e;text-decoration:none'>📋 TOUS les vrais menuisiers</a>
      <a class='btn' href='/api/admin/traction/export.csv?token={token}&segment=inactive'
         style='background:#f97316;text-decoration:none'>💤 Inscrits jamais reconnectés</a>
      <a class='btn' href='/api/admin/traction/export.csv?token={token}&segment=no_chantier'
         style='background:#8b5cf6;text-decoration:none'>📭 Sans aucun chantier créé</a>
      <a class='btn' href='/api/admin/traction/export.csv?token={token}&segment=suspicious'
         style='background:#ef4444;text-decoration:none'>⚠️ Emails suspects (à purger)</a>
    </div>
    <p style='color:#737373;font-size:12px;margin-top:14px'>
      Colonnes fournies : email, nom, entreprise, pays, ville, région, date d'inscription,
      dernière connexion, connecté via Google, a créé un chantier, statut, email suspect.
    </p>
    """

    return HTMLResponse(_html_page(title="📊 TRACTION RÉELLE", body_html=body))


@router.post("/admin/traction/access-link")
async def admin_traction_access_link(
    request: Request,
    user: dict = Depends(require_platform_owner),
):
    """Génère un lien signé pour ouvrir le dashboard traction dans un navigateur."""
    short_jwt = _generate_map_jwt()  # même scope admin_map suffit
    env_base = os.getenv("MAP_PUBLIC_BASE_URL", "").strip().rstrip("/")
    if env_base:
        base = env_base
    else:
        scheme = request.headers.get("x-forwarded-proto") or request.url.scheme
        host = request.headers.get("x-forwarded-host") or request.url.netloc
        base = f"{scheme}://{host}"
    return {
        "url": f"{base}/api/admin/traction?token={short_jwt}",
        "expires_in_seconds": _MAP_JWT_TTL_MIN * 60,
    }



# ══════════════════════════════════════════════════════════════════════
# 📥 Export CSV des utilisateurs (owner-only, JWT admin_map)
# ══════════════════════════════════════════════════════════════════════
from fastapi.responses import PlainTextResponse  # noqa: E402


@router.get("/admin/traction/export.csv", response_class=PlainTextResponse)
async def admin_traction_export_csv(
    token: str = Query(..., description="JWT scope admin_map"),
    segment: str = Query(
        "all",
        description=(
            "Segment à exporter : 'all' (tous vrais menuisiers), "
            "'inactive' (jamais reconnectés), "
            "'no_chantier' (aucun chantier créé), "
            "'suspicious' (emails jetables)"
        ),
    ),
):
    """Export CSV des emails utilisateurs. Ouvrable dans Excel/Sheets.

    Colonnes : email, nom, entreprise, pays, ville, inscrit_le,
               dernière_connexion, google_link, a_chantier, statut, segment.
    """
    _check_token(token)

    from datetime import datetime, timezone
    import csv
    from io import StringIO

    now = datetime.now(timezone.utc)

    def _to_iso(dt):
        if not dt:
            return ""
        if isinstance(dt, datetime):
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.strftime("%Y-%m-%d %H:%M")
        return str(dt)

    # Récupération users
    cursor = db.users.find({}, {
        "id": 1, "email": 1, "name": 1, "role": 1, "created_at": 1,
        "last_login_at": 1, "signup_geo": 1, "company_id": 1,
        "google_linked": 1, "status": 1,
    })

    # Company names (pour lisibilité)
    company_names: dict[str, str] = {}

    rows: list[dict] = []
    async for u in cursor:
        email = (u.get("email") or "").lower().strip()
        if _is_technical_account(email):
            continue  # on exclut TOUJOURS les comptes techniques du CSV
        geo = u.get("signup_geo") or {}
        cid = u.get("company_id")
        if cid and cid not in company_names:
            comp = await db.companies.find_one({"id": cid}, {"name": 1})
            company_names[cid] = (comp or {}).get("name", "") if comp else ""
        company_name = company_names.get(cid, "") if cid else ""
        has_chantier = False
        if cid:
            n = await db.chantiers.count_documents({"company_id": cid}, limit=1)
            has_chantier = n > 0

        last_login = u.get("last_login_at")
        has_ever_logged_in = last_login is not None

        row = {
            "email": email,
            "nom": u.get("name") or "",
            "entreprise": company_name,
            "pays": geo.get("country") or "",
            "ville": geo.get("city") or "",
            "region": geo.get("region") or "",
            "inscrit_le": _to_iso(u.get("created_at")),
            "derniere_connexion": _to_iso(last_login),
            "google_linked": "oui" if u.get("google_linked") else "non",
            "a_cree_chantier": "oui" if has_chantier else "non",
            "statut": u.get("status") or "active",
            "email_suspect": "oui" if _is_suspicious_email(email) else "non",
        }
        rows.append(row)

    # Filtrer selon segment
    if segment == "inactive":
        rows = [r for r in rows if r["derniere_connexion"] == ""]
    elif segment == "no_chantier":
        rows = [r for r in rows if r["a_cree_chantier"] == "non"]
    elif segment == "suspicious":
        rows = [r for r in rows if r["email_suspect"] == "oui"]
    # else 'all' → tout garder

    # Tri : plus récent en haut
    rows.sort(key=lambda r: r["inscrit_le"], reverse=True)

    # Écrire CSV
    buf = StringIO()
    if not rows:
        buf.write("Aucun utilisateur ne correspond à ce segment.\n")
    else:
        # BOM UTF-8 pour Excel qui lit bien les accents
        buf.write("\ufeff")
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()), delimiter=";")
        writer.writeheader()
        writer.writerows(rows)

    csv_text = buf.getvalue()
    from fastapi.responses import Response
    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="mesurechassis-users-{segment}-'
                f'{now.strftime("%Y%m%d")}.csv"'
            ),
        },
    )
