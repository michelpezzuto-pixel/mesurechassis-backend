"""MesureChâssis backend — point d'entrée FastAPI.

Tous les modèles, dépendances, et routes vivent dans des modules
dédiés (db.py, models.py, deps.py, utils.py, routes/, seed.py).
Le cycle de vie applicatif utilise le moderne `lifespan` context
manager (les hooks `@app.on_event` sont deprecated depuis FastAPI 0.93).
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import FileResponse
from starlette.middleware.cors import CORSMiddleware
import os

from db import client as mongo_client
from routes import auth as auth_routes
from routes import chantiers as chantiers_routes
from routes import company as company_routes
from routes import exports as exports_routes
from routes import feedbacks as feedbacks_routes
from routes import invitations as invitations_routes
from routes import mesures as mesures_routes
from routes import referral as referral_routes
from routes import stats as stats_routes
from routes import stripe_routes
from seed import seed_data


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # --- Startup ---------------------------------------------------------
    await seed_data()
    yield
    # --- Shutdown --------------------------------------------------------
    mongo_client.close()


app = FastAPI(title="MesureChâssis API", lifespan=lifespan)
api = APIRouter(prefix="/api")

api.include_router(auth_routes.router)
api.include_router(invitations_routes.router)
api.include_router(stripe_routes.router)
api.include_router(chantiers_routes.router)
api.include_router(mesures_routes.router)
api.include_router(feedbacks_routes.router)
api.include_router(company_routes.router)
api.include_router(stats_routes.router)
api.include_router(exports_routes.router)
# 🆕 Build 9 — Système de parrainage (2 mois offerts par filleul actif)
api.include_router(referral_routes.router)

# ─────────────────────────────────────────────────────────────────────
# Route publique TEMPORAIRE pour télécharger les screenshots tablette
# destinés à Google Play Console. À retirer après la mise en ligne.
# ─────────────────────────────────────────────────────────────────────
_TABLET_SHOTS_DIR = "/app/playstore_tablet_screenshots"
_TABLET_ALLOWED = {
    "01_dashboard.jpeg",
    "02_statistiques.jpeg",
    "03_selection_menuiserie.jpeg",
    "04_prise_cotes_rectangle.jpeg",
    "05_prise_cotes_trapeze.jpeg",
    "06_dashboard_nouveau_layout.jpeg",
}


@api.get("/_assets/playstore-tablet/{filename}")
async def get_playstore_tablet_asset(filename: str):
    if filename not in _TABLET_ALLOWED:
        raise HTTPException(status_code=404, detail="Not found")
    path = os.path.join(_TABLET_SHOTS_DIR, filename)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File missing on disk")
    return FileResponse(path, media_type="image/jpeg", filename=filename)


@api.get("/_downloads/site-mesurechassis")
async def download_site_zip():
    """Endpoint temporaire pour télécharger l'archive du site vitrine."""
    path = "/app/site_mesurechassis_final.zip"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Archive introuvable")
    return FileResponse(
        path,
        media_type="application/zip",
        filename="site_mesurechassis_final.zip",
    )


@api.get("/_downloads/play-store-assets")
async def download_play_store_zip():
    """Pack d'assets et textes prêts à coller dans Google Play Console."""
    path = "/app/play-store-mesurechassis.zip"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Archive introuvable")
    return FileResponse(
        path,
        media_type="application/zip",
        filename="play-store-mesurechassis.zip",
    )


@api.get("/_downloads/feature-graphic")
async def download_feature_graphic():
    """Image de présentation 1024x500 pour Google Play Console (générée v2)."""
    path = "/app/play-store-assets/feature-graphic-1024x500-v2.png"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Image introuvable")
    return FileResponse(
        path,
        media_type="image/png",
        filename="feature-graphic-1024x500.png",
    )


@api.get("/_downloads/railway-update")
async def download_railway_update():
    """Package de mise à jour des fichiers backend pour Railway (auth.py + stripe_routes.py + server.py + requirements.txt)."""
    path = "/app/backend/public_downloads/railway-update-2026-06-01.zip"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Archive introuvable")
    return FileResponse(
        path,
        media_type="application/zip",
        filename="railway-update-2026-06-01.zip",
    )


@api.get("/_downloads/railway-fix-stripe")
async def download_railway_fix_stripe():
    """Hotfix Railway : corrige bug 'Entreprise introuvable' Stripe + ajoute endpoint /platform/db/cleanup."""
    path = "/app/backend/public_downloads/railway-fix-stripe-cleanup.zip"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Archive introuvable")
    return FileResponse(
        path,
        media_type="application/zip",
        filename="railway-fix-stripe-cleanup.zip",
    )


@api.get("/_downloads/frontend-source")
async def download_frontend_source():
    """Archive du code source de l'app Expo (sans node_modules) pour build EAS local."""
    path = "/app/backend/public_downloads/mesurechassis-frontend.zip"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Archive introuvable")
    return FileResponse(
        path,
        media_type="application/zip",
        filename="mesurechassis-frontend.zip",
    )


@api.get("/_downloads/screenshots")
async def download_screenshots():
    """Captures d'ecran iPhone redimensionnees au format App Store (6.7 et 6.9 pouces)."""
    path = "/app/backend/public_downloads/mesurechassis-screenshots.zip"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Archive introuvable")
    return FileResponse(
        path,
        media_type="application/zip",
        filename="mesurechassis-screenshots.zip",
    )


@api.get("/_downloads/screenshots-ipad")
async def download_screenshots_ipad():
    """Captures d'ecran iPad 13 pouces (2048x2732)."""
    path = "/app/backend/public_downloads/mesurechassis-screenshots-ipad.zip"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Archive introuvable")
    return FileResponse(
        path,
        media_type="application/zip",
        filename="mesurechassis-screenshots-ipad.zip",
    )


@api.get("/_downloads/file/{which}")
async def download_raw_file(which: str):
    """Sert le contenu BRUT (texte) des fichiers backend pour copier-coller manuel."""
    allowed = {
        "company": "/app/backend/routes/company.py",
        "stripe": "/app/backend/routes/stripe_routes.py",
        "server": "/app/backend/server.py",
    }
    if which not in allowed:
        raise HTTPException(status_code=404, detail="Fichier inconnu")
    path = allowed[which]
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Fichier manquant")
    return FileResponse(
        path,
        media_type="text/plain; charset=utf-8",
        filename=f"{which}.py",
    )


# ─────────────────────────────────────────────────────────────────────
# Mini-UI cleanup DB (un seul écran, pas besoin d'outil externe)
# Sert une page HTML qui poste vers /api/platform/db/cleanup
# ─────────────────────────────────────────────────────────────────────
from fastapi.responses import HTMLResponse


@api.get("/_admin/cleanup-ui", response_class=HTMLResponse)
async def cleanup_ui():
    html = """<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>MesureChâssis · Nettoyage base</title>
<style>
  *{box-sizing:border-box;font-family:-apple-system,BlinkMacSystemFont,sans-serif}
  body{background:#0f172a;color:#f1f5f9;padding:24px;max-width:560px;margin:0 auto}
  h1{font-size:22px;margin-bottom:8px}
  p{color:#94a3b8;line-height:1.5;font-size:14px}
  label{display:block;margin:18px 0 6px;font-weight:600;font-size:14px}
  input{width:100%;padding:14px;background:#1e293b;border:1px solid #334155;border-radius:10px;color:#f1f5f9;font-size:15px}
  button{margin-top:24px;width:100%;padding:16px;background:#dc2626;color:#fff;border:none;border-radius:10px;font-size:16px;font-weight:700;cursor:pointer}
  button:disabled{opacity:.5}
  .warn{background:#7f1d1d;padding:14px;border-radius:10px;margin-top:16px;font-size:13px}
  pre{background:#020617;padding:14px;border-radius:10px;font-size:12px;overflow-x:auto;white-space:pre-wrap;word-break:break-all}
  .ok{color:#22c55e}.ko{color:#ef4444}
</style></head><body>
<h1>🗑️ Nettoyage base MesureChâssis</h1>
<p>Cette action supprime <b>tous les comptes utilisateurs, entreprises, chantiers, mesures, feedbacks et invitations</b> de la base, <b>sauf</b> ceux liés à l'email indiqué ci-dessous.</p>
<div class="warn">⚠️ Action IRRÉVERSIBLE. Vérifiez bien l'email à conserver avant de cliquer.</div>
<label>Email à conserver</label>
<input id="keep" type="email" placeholder="info@mesurechassis.com" autocomplete="off"/>
<label>Token plateforme (X-Platform-Token)</label>
<input id="token" type="password" placeholder="mc-platform-2026"/>
<button id="btn">SUPPRIMER TOUT LE RESTE</button>
<pre id="out"></pre>
<script>
document.getElementById('btn').onclick=async()=>{
  const keep=document.getElementById('keep').value.trim();
  const token=document.getElementById('token').value.trim();
  const out=document.getElementById('out');
  if(!keep||!token){out.innerHTML='<span class="ko">Email et token requis.</span>';return}
  if(!confirm('Confirmer la suppression de TOUS les comptes sauf '+keep+' ?'))return;
  document.getElementById('btn').disabled=true;
  out.textContent='⏳ Nettoyage en cours...';
  try{
    const r=await fetch('/api/platform/db/cleanup',{
      method:'POST',
      headers:{'Content-Type':'application/json','X-Platform-Token':token},
      body:JSON.stringify({keep_email:keep,confirm:'DELETE_ALL'})
    });
    const j=await r.json();
    if(r.ok){
      out.innerHTML='<span class="ok">✅ Nettoyage terminé !</span>\\n\\n'+JSON.stringify(j,null,2);
    }else{
      out.innerHTML='<span class="ko">❌ Erreur '+r.status+'</span>\\n\\n'+JSON.stringify(j,null,2);
    }
  }catch(e){
    out.innerHTML='<span class="ko">❌ '+e.message+'</span>';
  }
  document.getElementById('btn').disabled=false;
};
</script></body></html>"""
    return HTMLResponse(content=html)


@api.get("/_downloads/feature-graphic/{variant}")
async def download_feature_graphic_variant(variant: str):
    """Variantes redimensionnées de l'image utilisateur (stretch / fit / cover)."""
    allowed = {"stretch", "fit", "cover"}
    if variant not in allowed:
        raise HTTPException(status_code=404, detail="Variant inconnu")
    path = f"/app/play-store-assets/feature-graphic-user-{variant}.png"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Image introuvable")
    return FileResponse(
        path,
        media_type="image/png",
        filename=f"feature-graphic-{variant}-1024x500.png",
    )


@api.get("/_downloads/backend-railway")
async def download_backend_zip():
    """Pack du backend prêt à pousser sur GitHub puis déployer sur Railway."""
    path = "/app/backend/mesurechassis-backend.zip"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Archive introuvable")
    return FileResponse(
        path,
        media_type="application/zip",
        filename="mesurechassis-backend.zip",
    )


@api.get("/_gallery/{filename}")
async def gallery_file(filename: str):
    """Galerie temporaire pour visualiser les images extraites du PDF utilisateur."""
    # Sécurité : pas de path traversal
    if "/" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    path = os.path.join("/app/frontend/assets/marketing_screenshots/pdf_images", filename)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Not found")
    if filename.endswith(".html"):
        return FileResponse(path, media_type="text/html")
    if filename.endswith(".jpg") or filename.endswith(".jpeg"):
        return FileResponse(path, media_type="image/jpeg")
    if filename.endswith(".png"):
        return FileResponse(path, media_type="image/png")
    return FileResponse(path)



app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
