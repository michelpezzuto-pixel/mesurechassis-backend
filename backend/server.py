"""MesureChâssis backend — point d'entrée FastAPI.

Tous les modèles, dépendances, et routes vivent dans des modules
dédiés (db.py, models.py, deps.py, utils.py, routes/, seed.py).
Le cycle de vie applicatif utilise le moderne `lifespan` context
manager (les hooks `@app.on_event` sont deprecated depuis FastAPI 0.93).
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from starlette.middleware.cors import CORSMiddleware
import logging
import os

from db import client as mongo_client
from routes import auth as auth_routes
from routes import campaign as campaign_routes
from routes import chantiers as chantiers_routes
from routes import linkedin as linkedin_routes
from routes import company as company_routes
from routes import exports as exports_routes
from routes import feedbacks as feedbacks_routes
from routes import invitations as invitations_routes
from routes import mesures as mesures_routes
from routes import referral as referral_routes
from routes import yann as yann_routes
from routes import partners as partners_routes
from routes import stats as stats_routes
from routes import spec_import as spec_import_routes
from routes import stripe_routes
from routes import testers as testers_routes
from routes import promo as promo_routes
from seed import seed_data, ensure_apple_review_user


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # --- Startup ---------------------------------------------------------
    await seed_data()
    # 🍎 Apple App Review demo account — ALWAYS ensured at startup,
    # independent of MC_SEED_DEMO. Required by the iOS review team.
    try:
        await ensure_apple_review_user()
    except Exception as _e:
        logging.getLogger("mesurechassis").error(
            "Apple Review user seeding failed: %s", _e
        )
    # 🆕 Campagne — import auto des prospects depuis le CSV embarqué (idempotent,
    # dédoublonné par email). Fonctionne aussi sur Railway car le CSV est commité.
    try:
        await campaign_routes.seed_prospects_from_csv()
    except Exception as _e:
        logging.getLogger("mesurechassis").warning(
            "Import CSV prospects échoué : %s", _e
        )
    # 🆕 Récap hebdo campagne (lundi ≈ 9h belge) — tâche de fond annulée au shutdown
    import asyncio as _asyncio
    _recap_task = _asyncio.create_task(campaign_routes.weekly_recap_loop())
    # 🆕 Build 9 — Index unique sur referral_code (anti-collision concurrente).
    # `sparse=True` permet aux documents sans champ d'exister sans violer
    # l'unicité (migration progressive depuis les comptes pré-existants).
    try:
        from db import db as _db
        await _db.companies.create_index(
            "referral_code", unique=True, sparse=True, name="referral_code_unique"
        )
    except Exception as _e:
        # Pas critique : l'index existe peut-être déjà, ou collision sur
        # données legacy → on log et on continue.
        logging.getLogger("mesurechassis").warning(
            "Index referral_code non créé : %s", _e
        )
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

# 🆕 Build 9 — Assistant IA Yann (Claude Sonnet 4.5 via Emergent LLM Key)
api.include_router(yann_routes.router)

# 🆕 Build 9 — Partenaires affiliés (système d'influence marketing)
api.include_router(partners_routes.router)
# 🆕 Build 11 — Import cahier des charges (PDF/Excel/Photo) → IA Gemini 2.5 Flash
api.include_router(spec_import_routes.router)

api.include_router(testers_routes.router)
# 🆕 Campagne emailing — prospection testeurs à 1 bouton (max 15/jour via Resend)
api.include_router(campaign_routes.router)
# 🆕 RGPD — Routeur public unsubscribe (pas d'auth, accès via lien JWT signé)
api.include_router(campaign_routes.public_router)
# 🆕 Campagne LinkedIn 15 jours — post du jour + visuels
api.include_router(linkedin_routes.router)

# 🎬 Vidéos promo Sora 2 (publiques, pour mesurechassis.com + réseaux sociaux)
api.include_router(promo_routes.router)


# ─────────────────────────────────────────────────────────────────────
# 🪪 Handler global 422 — log détaillé des erreurs de validation pour
# débugger les uploads multipart (notamment l'import cahier des charges).
# ─────────────────────────────────────────────────────────────────────
@app.exception_handler(RequestValidationError)
async def _log_422(request: Request, exc: RequestValidationError):
    import logging as _logging
    _log = _logging.getLogger("mesurechassis.422")
    try:
        ctype = request.headers.get("content-type", "")
        _log.warning(
            "❌ 422 %s %s | content-type=%r | errors=%s",
            request.method,
            request.url.path,
            ctype,
            exc.errors(),
        )
    except Exception as e:  # noqa: BLE001
        _log.warning("422 handler failed to log: %s", e)
    return JSONResponse(status_code=422, content=jsonable_encoder({"detail": exc.errors()}))

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


@api.get("/_downloads/liste-prospects")
async def download_liste_prospects():
    """Liste des prospects testeurs nettoyée (CSV ; compatible Excel/Brevo)."""
    path = "/app/backend/static/liste_prospects_testeurs.csv"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Liste introuvable")
    return FileResponse(
        path,
        media_type="text/csv",
        filename="liste_prospects_testeurs.csv",
    )


# 🆕 Build 11.3 — Screenshots Apple App Store (iPhone 6.5" + iPad 12.9")
@api.get("/_downloads/apple-screenshots")
async def download_apple_screenshots():
    """ZIP de tous les screenshots Apple Store aux dimensions exactes.

    Contient :
        • iphone/01-05_*.png  → 1242×2688 px (iPhone 6.5")
        • ipad/01-03_*.png    → 2048×2732 px (iPad Pro 12.9")

    Si le ZIP n'existe pas, on le génère à la volée à partir du dossier
    /app/backend/static_artifacts/screenshots/ (peuplé par
    scripts/generate_apple_screenshots.py).
    """
    import zipfile
    src = "/app/backend/static_artifacts/screenshots"
    zip_path = "/app/backend/static_artifacts/apple_screenshots.zip"
    if not os.path.isdir(src):
        raise HTTPException(404, "Dossier de screenshots introuvable")
    # Recrée le zip à chaque appel pour s'assurer qu'il est à jour
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(src):
            for f in sorted(files):
                if f.endswith(".png"):
                    full = os.path.join(root, f)
                    arc = os.path.relpath(full, src)
                    zf.write(full, arc)
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename="mesurechassis_apple_screenshots.zip",
    )


@api.get("/_downloads/apple-screenshot/{device}/{name}")
async def download_single_apple_screenshot(device: str, name: str):
    """Téléchargement d'un screenshot individuel.

    Exemple : /api/_downloads/apple-screenshot/iphone/01_login.png
    """
    if device not in {"iphone", "ipad"}:
        raise HTTPException(404, "Device invalide")
    safe = os.path.basename(name)  # bloque les traversals
    path = f"/app/backend/static_artifacts/screenshots/{device}/{safe}"
    if not os.path.isfile(path):
        raise HTTPException(404, "Screenshot introuvable")
    return FileResponse(path, media_type="image/png", filename=safe)


@api.get("/_downloads/site-maj-offre-lancement")
async def download_site_maj():
    """Pages du site vitrine mises à jour (bêta → offre de lancement, QR testeur)."""
    path = "/app/backend/static/site_maj_offre_lancement.zip"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Archive introuvable")
    return FileResponse(
        path,
        media_type="application/zip",
        filename="site_maj_offre_lancement.zip",
    )


@api.get("/_downloads/site-freemium-apple")
async def download_site_freemium_apple():
    """Pages du site vitrine refondues pour conformité Apple Store + offre Freemium.
    Inclut : index, faq, tarifs (nouveau), telecharger, contact, guide, légal,
    + redirections beta.html / devenir-testeur.html.
    """
    path = "/app/backend/static/site_freemium_apple_compliant.zip"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Archive introuvable")
    return FileResponse(
        path,
        media_type="application/zip",
        filename="site_freemium_apple_compliant.zip",
    )


@api.get("/_downloads/site-v2-gratuit-parrainage")
async def download_site_v2():
    """Site vitrine v2 (Build 9 — juin 2026) — emphase GRATUIT + PARRAINAGE.

    Différences vs v1 :
      • Hero : 2 badges visibles (5 ouvertures GRATUITES à vie + 20 mois offerts)
      • Nouvelle section dédiée "🎁 PROGRAMME PARRAINAGE" avant les tarifs
      • Prix Artisan Solo passé de 24,99 € → 19,99 €
      • Plan Société : équipe ILLIMITÉE (suppression du +4,99 €/utilisateur)
      • Mention de l'add-on Assistant IA Yann disponible
    """
    path = "/app/backend/static/site_v2_gratuit_parrainage.zip"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Archive introuvable")
    return FileResponse(
        path,
        media_type="application/zip",
        filename="site_v2_gratuit_parrainage.zip",
    )


@api.get("/_downloads/roadmap-michel")
async def download_roadmap_pdf():
    """PDF imprimable A4 — Roadmap personnelle de Michel (juin → 1er oct 2026)."""
    pdf_path = "/app/backend/static/roadmap_michel_juin_octobre_2026.pdf"
    import subprocess
    if not os.path.isfile(pdf_path):
        subprocess.run(
            ["python", "/app/backend/scripts/generate_roadmap_pdf.py"],
            cwd="/app/backend",
            check=True,
        )
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename="MesureChassis_Roadmap_Michel_Juin-Octobre_2026.pdf",
    )


@api.get("/_downloads/partner-contract")
async def download_partner_contract():
    """Modèle de contrat partenariat affilié — PDF prêt à signer (BE/FR).

    Document juridique conforme RGPD, droit belge applicable. À imprimer en
    2 exemplaires, signer, scanner et renvoyer à contact@mesurechassis.com.
    """
    pdf_path = "/app/backend/static/contrat_partenariat_modele.pdf"
    import subprocess
    if not os.path.isfile(pdf_path):
        subprocess.run(
            ["python", "/app/backend/scripts/generate_partner_contract.py"],
            cwd="/app/backend",
            check=True,
        )
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename="MesureChassis_Contrat_Partenariat_Affilie.pdf",
    )


@api.get("/_downloads/devenir-testeur-html")
async def download_devenir_testeur_html():
    """Page statique d'inscription testeur à héberger sur mesurechassis.com."""
    path = "/app/backend/static/devenir-testeur.html"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Page introuvable")
    return FileResponse(
        path,
        media_type="text/html",
        filename="devenir-testeur.html",
    )


@api.get("/_downloads/play-feature-graphic")
async def download_play_feature_graphic():
    """Feature graphic Google Play (1024×500) générée pour la fiche store."""
    path = "/app/backend/static/play_feature_graphic_1024x500.png"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Bannière introuvable")
    return FileResponse(
        path,
        media_type="image/png",
        filename="mesurechassis_feature_graphic_1024x500.png",
    )


@api.get("/_downloads/dossier-continuite")
async def download_dossier_continuite():
    """Dossier de continuité d'entreprise (à imprimer et joindre aux accès)."""
    path = "/app/backend/static/dossier_continuite.html"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Dossier introuvable")
    return FileResponse(path, media_type="text/html")


@api.get("/_downloads/roadmap")
async def download_roadmap():
    """Roadmap 18 mois MesureChâssis (document HTML imprimable)."""
    path = "/app/backend/static/roadmap.html"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Roadmap introuvable")
    return FileResponse(path, media_type="text/html")


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
    """🔐 SEC-004 : archive du code source backend RETIRÉE (exposition publique)."""
    raise HTTPException(status_code=404, detail="Not found")


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
