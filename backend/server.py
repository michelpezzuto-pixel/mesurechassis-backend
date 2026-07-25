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
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from starlette.middleware.cors import CORSMiddleware
import logging
import os

from db import client as mongo_client
from routes import auth as auth_routes
from routes import campaign as campaign_routes
from routes import chantiers as chantiers_routes
from routes import linkedin as linkedin_routes
from routes import company as company_routes
from routes import admin_tools as admin_tools_routes
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
from routes import jeton_cafe as jeton_cafe_routes
from routes import google_auth as google_auth_routes
from routes import apple_auth as apple_auth_routes
from routes import reactivation as reactivation_routes
from routes import validation as validation_routes
from routes import config as config_routes
from routes import account_deletion as account_deletion_routes
from routes import newsletter as newsletter_routes
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
    # 🆕 Auto-send quotidien 16h30 belge (Mar-Ven, lot de 40)
    _auto_send_task = _asyncio.create_task(campaign_routes.auto_send_daily_loop())
    # 🗑️ Exit Survey — hard-delete des comptes en pending_deletion +30j
    _hard_delete_task = _asyncio.create_task(
        account_deletion_routes.hard_delete_loop()
    )
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
# 📱 v1.1.3 — Config publique app-version (mise à jour requise/disponible)
api.include_router(config_routes.router)
# 🛡️ Endpoints admin one-shot (purge email, etc.) — protégés PLATFORM_ADMIN_TOKEN
api.include_router(admin_tools_routes.router)
# 🆕 RGPD — Routeur public unsubscribe (pas d'auth, accès via lien JWT signé)
api.include_router(campaign_routes.public_router)
# 🆕 Campagne LinkedIn 15 jours — post du jour + visuels
api.include_router(linkedin_routes.router)

# 🎬 Vidéos promo Sora 2 (publiques, pour mesurechassis.com + réseaux sociaux)
api.include_router(promo_routes.router)
# ☕ Priorité 4 — Système Jeton Café (stations partenaires)
api.include_router(jeton_cafe_routes.router)
# 🔑 Google Sign-In (Emergent-managed Google Auth)
api.include_router(google_auth_routes.router)
# 🍎 Sign in with Apple — Apple Guideline 4.8 (v1.1.3+)
api.include_router(apple_auth_routes.router)
api.include_router(reactivation_routes.router)
api.include_router(validation_routes.router)
# 🗑️ v1.1.4 — Exit Survey + Grace Period 30j (suppression compte)
api.include_router(account_deletion_routes.router)

# 📚 Juin 2026 — Capture email landing page (guide gratuit "5 pièges")
api.include_router(newsletter_routes.router)


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


# 🆕 Juillet 2026 — Page démo publique mesurechassis.com + sitemap
@api.get("/_downloads/demo-html")
async def download_demo_html():
    """Page HTML `demo.html` pour mesurechassis.com."""
    path = "/app/site_mesurechassis_final/demo.html"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="demo.html introuvable")
    return FileResponse(path, media_type="text/html", filename="demo.html")


@api.get("/_downloads/sitemap-xml")
async def download_sitemap_xml():
    """Sitemap XML mis à jour avec la nouvelle page démo."""
    path = "/app/site_mesurechassis_final/sitemap.xml"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="sitemap.xml introuvable")
    return FileResponse(path, media_type="application/xml", filename="sitemap.xml")


@api.get("/_downloads/kit-video-capcut")
async def download_kit_capcut():
    """Kit CapCut (storyboard 60s pour la vidéo de démo)."""
    path = "/app/memory/KIT_CAPCUT_video_demo.md"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Kit CapCut introuvable")
    return FileResponse(path, media_type="text/markdown", filename="Kit_CapCut_video_demo.md")


# 🆕 Juin 2026 — Landing page complète (double CTA + capture email)
@api.get("/_downloads/landing-www")
async def download_landing_www():
    """
    Archive ZIP de la landing page mesurechassis.com prête pour upload FTP.
    Contient : index.html (Double CTA + form guide) + toutes les autres pages,
    images, vidéos, .htaccess et robots.txt.
    """
    import glob
    matches = sorted(glob.glob("/app/backend/public_downloads/landing/mesurechassis-www-*.zip"))
    if not matches:
        raise HTTPException(status_code=404, detail="Archive introuvable")
    path = matches[-1]  # plus récent
    return FileResponse(
        path,
        media_type="application/zip",
        filename=os.path.basename(path),
    )


# 🎬 Juillet 2026 — Composant Web animation marketing Vidéo 1 (format 9:16)
@api.get("/marketing/video1", response_class=HTMLResponse)
async def marketing_video1_view():
    """Animation marketing MesureChâssis — Vidéo 1 (à ouvrir dans le navigateur puis screen record)."""
    path = "/app/marketing/video1-animation.html"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Animation vidéo 1 introuvable")
    with open(path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read(), status_code=200)


@api.get("/_downloads/video1-animation")
async def download_video1_animation():
    """Télécharger le fichier HTML autonome de l'animation Vidéo 1."""
    path = "/app/marketing/video1-animation.html"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Animation vidéo 1 introuvable")
    return FileResponse(path, media_type="text/html", filename="mesurechassis-video1-animation.html")


# 🎬 Juillet 2026 — Pack vidéo pub 45s "Fait par un menuisier"
@api.get("/_downloads/video-pub-45s-pack")
async def download_video_pub_45s_pack():
    """ZIP complet de la pub vidéo 45s (24 assets PNG + README + script)."""
    path = "/app/backend/static/promo/video_pub_45s_pack.zip"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Pack vidéo pub introuvable")
    return FileResponse(
        path,
        media_type="application/zip",
        filename="mesurechassis-pub-video-45s-pack.zip",
    )


# 🎬 Juin 2026 — Kit Marketing MASTER (Pub 45s + 10 TikTok variantes + Photos + Guides CapCut)
@api.get("/_downloads/marketing-kit-master")
async def download_marketing_kit_master():
    """ZIP master de 88 MB : pub principale 45s + 10 scripts TikTok
    (assets + voix-off MP3 déjà générées) + photos réalistes + guide CapCut
    pas-à-pas + LISEZ-MOI stratégie de publication."""
    path = "/app/backend/static/promo/marketing_kit_master.zip"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Kit marketing master introuvable")
    return FileResponse(
        path,
        media_type="application/zip",
        filename="mesurechassis-marketing-kit-master.zip",
    )


# 🏷️ Juin 2026 — Watermark PNG pour montage vidéo CapCut
@api.get("/_downloads/watermark-logo")
async def download_watermark_logo():
    """Icône MesureChâssis PNG (1024×1024, fond orange plein) — style App Store."""
    path = "/app/backend/static/promo/mesurechassis_watermark_v1.png"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Watermark introuvable")
    return FileResponse(
        path,
        media_type="image/png",
        filename="mesurechassis-icon.png",
    )


@api.get("/_downloads/watermark-rounded")
async def download_watermark_rounded():
    """Icône MesureChâssis avec coins arrondis iOS (512×512, transparent autour)."""
    path = "/app/backend/static/promo/mesurechassis_watermark_rounded.png"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Watermark arrondi introuvable")
    return FileResponse(
        path,
        media_type="image/png",
        filename="mesurechassis-icon-rounded.png",
    )


@api.get("/_downloads/wordmark-dark")
async def download_wordmark_dark():
    """Logo horizontal (icône + texte orange) pour fond clair. 1077×220."""
    path = "/app/backend/static/promo/mesurechassis_wordmark.png"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Wordmark sombre introuvable")
    return FileResponse(
        path,
        media_type="image/png",
        filename="mesurechassis-wordmark-fond-clair.png",
    )


@api.get("/_downloads/wordmark-light")
async def download_wordmark_light():
    """Logo horizontal (icône + texte blanc) pour fond foncé. 1077×220."""
    path = "/app/backend/static/promo/mesurechassis_wordmark_light.png"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Wordmark clair introuvable")
    return FileResponse(
        path,
        media_type="image/png",
        filename="mesurechassis-wordmark-fond-fonce.png",
    )


@api.get("/_downloads/hero-measurer")
async def download_hero_measurer():
    """Photo marketing : mesureur en chantier + app MesureChâssis en surimpression.
    Format 16:9 landscape, prêt pour landing page, LinkedIn, YouTube, Meta Ads."""
    path = "/app/backend/static/promo/hero_shots/measurer_hero_v1.png"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Hero shot introuvable")
    return FileResponse(
        path,
        media_type="image/png",
        filename="mesurechassis-hero-mesureur-chantier.png",
    )


@api.get("/_downloads/hero-shapes-pack")
async def download_hero_shapes_pack():
    """ZIP des 12 hero shots (une par forme d'ouverture supportée)."""
    path = "/app/backend/static/promo/hero_shots/hero_shots_pack.zip"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Pack hero shots introuvable")
    return FileResponse(
        path,
        media_type="application/zip",
        filename="mesurechassis-hero-shots-12-formes.zip",
    )


@api.get("/_downloads/hero-diverse-pack")
async def download_hero_diverse_pack():
    """ZIP FINAL des 12 hero shots divers (mix homme/femme + ethnies).
    Distribution : 5 hommes blancs + 2 femmes blanches + 2 hommes noirs
    + 2 hommes maghrébins + 1 homme asiatique. 16:9 HD, prêts Canva."""
    path = "/app/backend/static/promo/hero_shots/hero_shots_diverse_12.zip"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Pack diverse introuvable")
    return FileResponse(
        path,
        media_type="application/zip",
        filename="mesurechassis-hero-shots-diverse-12.zip",
    )


@api.get("/_downloads/hero-shape/{shape_id}")
async def download_hero_shape(shape_id: str):
    """Télécharge un hero shot individuel par nom de fichier
    (ex: 03_plein_cintre, 10_bow_window)."""
    safe = shape_id.replace("/", "").replace("..", "").strip()
    path = f"/app/backend/static/promo/hero_shots/{safe}.png"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail=f"Hero shape {safe} introuvable")
    return FileResponse(
        path,
        media_type="image/png",
        filename=f"mesurechassis-hero-{safe}.png",
    )


@api.get("/_downloads/hero-mascot")
async def download_hero_mascot():
    """Version mascotte cartoon du mesureur — style TikTok viral."""
    path = "/app/backend/static/promo/hero_shots/MASCOT_menuisier_v1.png"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Mascotte introuvable")
    return FileResponse(
        path,
        media_type="image/png",
        filename="mesurechassis-mascot-menuisier.png",
    )


# 🎠 Carrousel marketing — parcours utilisateur en 20 étapes
@api.get("/_downloads/carrousel-20-etapes")
async def download_carrousel_20():
    """ZIP de 20 screenshots authentiques triés chronologiquement — 
    du login jusqu'à l'export PDF. Photo Bosch intégrée à l'étape 16."""
    path = "/app/backend/static/promo/hero_shots/carrousel_20_etapes.zip"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Carrousel introuvable")
    return FileResponse(
        path,
        media_type="application/zip",
        filename="mesurechassis-carrousel-20-etapes.zip",
    )


@api.get("/_downloads/demo-hand-4slides")
async def download_demo_hand_4slides():
    """Démo vidéo de 4 slides (10 sec) avec main IA qui tap sur SUIVANT."""
    path = "/app/backend/static/promo/hero_shots/demo_hand_4slides.mp4"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Démo introuvable")
    return FileResponse(
        path,
        media_type="video/mp4",
        filename="mesurechassis-demo-hand-4slides.mp4",
    )


@api.get("/_downloads/demo-star-20slides")
async def download_demo_star_20slides():
    """Démo vidéo animée COMPLÈTE : 20 slides avec étoile orange qui clique
    sur les boutons selon le parcours utilisateur réel. 40 sec, 9:16."""
    path = "/app/backend/static/promo/hero_shots/demo_star_20slides.mp4"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Démo étoile introuvable")
    return FileResponse(
        path,
        media_type="video/mp4",
        filename="mesurechassis-demo-star-20slides.mp4",
    )


@api.get("/_downloads/demo-button-20slides")
async def download_demo_button_20slides():
    """Démo vidéo pro : 20 slides avec effet bouton-qui-s'enfonce (style Apple/Stripe).
    Ripple orange discret, transitions fluides. 30 sec, 9:16."""
    path = "/app/backend/static/promo/hero_shots/demo_button_20slides.mp4"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Démo bouton introuvable")
    return FileResponse(
        path,
        media_type="video/mp4",
        filename="mesurechassis-demo-button-20slides.mp4",
    )


# 🎬 Wizard Flow — 4 screenshots authentiques de l'app pour storytelling marketing
@api.get("/_downloads/wizard-flow/{step}")
async def download_wizard_flow(step: str):
    """Screenshots wizard : 1_choix_forme, 2_dimensions, 3_feuillures_allege,
    4_avec_bosch (photo pro Bosch en remplacement du mur)."""
    mapping = {
        "1_choix_forme": ("wizard_flow_1_choix_forme.webp", "image/webp"),
        "2_dimensions": ("wizard_flow_2_dimensions.webp", "image/webp"),
        "3_feuillures_allege": ("wizard_flow_3_feuillures_allege.webp", "image/webp"),
        "4_avec_bosch": ("wizard_flow_4_with_bosch.png", "image/png"),
    }
    if step not in mapping:
        raise HTTPException(status_code=404, detail=f"Étape {step} inconnue")
    filename, mime = mapping[step]
    path = f"/app/backend/static/promo/hero_shots/{filename}"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail=f"Fichier {filename} introuvable")
    return FileResponse(
        path,
        media_type=mime,
        filename=f"mesurechassis-wizard-{step}.{filename.split('.')[-1]}",
    )


# 📸 v1.1.3 — Générateur captures App Store (iPhone + iPad)
@api.get("/marketing/appstore-screenshot", response_class=HTMLResponse)
async def marketing_appstore_screenshot(device: str = "iphone", slide: int = 1):
    """Rend une capture App Store à la dimension exacte (device + slide)."""
    path = "/app/marketing/appstore/screenshot.html"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Template screenshot introuvable")
    with open(path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read(), status_code=200)


@api.get("/_downloads/appstore-screenshots-pack")
async def download_appstore_screenshots_pack():
    """ZIP des 11 captures App Store PNG (iPhone × 6 + iPad × 5)."""
    path = "/app/backend/static/promo/appstore_screenshots_pack.zip"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Pack captures introuvable")
    return FileResponse(
        path,
        media_type="application/zip",
        filename="mesurechassis-appstore-screenshots-pack.zip",
    )


@api.get("/_downloads/kit-tournee")
async def download_kit_tournee():
    """Kit imprimable pour la tournée menuisiers de Michel.
    Contient : identité, questionnaire découverte, chrono démo, débrief,
    synthèse par visite, checklist de départ."""
    path = "/app/downloads_michel_terrain/Kit_Tournee_Menuisiers.pdf"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Kit tournée introuvable")
    return FileResponse(
        path, media_type="application/pdf",
        filename="Kit_Tournee_Menuisiers.pdf",
    )


@api.get("/_downloads/script-demo-90s")
async def download_script_demo():
    """Script de pitch 90 secondes + réponses aux objections classiques
    à mémoriser avant la tournée terrain."""
    path = "/app/downloads_michel_terrain/Script_Demo_90s.pdf"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Script démo introuvable")
    return FileResponse(
        path, media_type="application/pdf",
        filename="Script_Demo_90s.pdf",
    )


@api.get("/_downloads/site-propre")
async def download_site_propre():
    """ZIP complet du site mesurechassis.com — dernière version (15 juillet 2026).
    Contient index.html avec bouton orange 'Télécharger' iPhone, sitemap
    complet, toutes les pages HTML + images + vidéo hero + config."""
    # Cherche d'abord le ZIP daté du jour, fallback sur l'ancien nom
    candidates = [
        "/app/downloads_site/mesurechassis_site_v2026-07-15.zip",
        "/app/downloads_site/mesurechassis_site_propre.zip",
    ]
    path = next((p for p in candidates if os.path.isfile(p)), None)
    if not path:
        raise HTTPException(status_code=404, detail="ZIP introuvable")
    return FileResponse(
        path,
        media_type="application/zip",
        filename="mesurechassis_site_v2026-07-15.zip",
    )


@api.get("/_downloads/site_propre")
async def download_site_propre_alias():
    """Alias avec underscore (au cas où l'URL est mal copiée)."""
    return await download_site_propre()


@api.get("/_downloads/backend-railway-fix")
async def download_backend_railway_fix():
    """ZIP des fichiers backend à uploader sur Railway pour ajouter
    l'endpoint /api/auth/verify-link + la carte admin géo + la géoloc
    automatique dans les inscriptions."""
    path = "/app/downloads_site/backend_fixes_railway.zip"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="ZIP backend introuvable")
    return FileResponse(
        path,
        media_type="application/zip",
        filename="backend_fixes_railway.zip",
    )


@api.get("/_downloads/build-131-combo")
async def download_build_131_combo():
    """ZIP combo pour le build 131 iOS : Rating Prompt activé + HelpButton
    + backend/auth.py avec bouton d'aide sur page HTML verify-link."""
    path = "/app/downloads_site/build_131_combo.zip"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="ZIP combo introuvable")
    return FileResponse(
        path,
        media_type="application/zip",
        filename="build_131_combo.zip",
    )


@api.get("/_downloads", response_class=HTMLResponse)
@api.get("/_downloads/", response_class=HTMLResponse)
async def downloads_index():
    """Page d'accueil listant tous les fichiers téléchargeables — 1 clic
    au lieu de copier des URL à la main sur iPhone."""
    files = [
        ("Build 131 iOS - COMBO (Rating + Aide + Backend)",
         "build-131-combo",
         "TOUT pour build 131 : Rating Prompt activé, bouton Aide, backend page HTML avec support. À uploader dans GitHub Desktop.",
         "36 Ko · ZIP"),
        ("Backend Railway seul (fix email verify)",
         "backend-railway-fix",
         "Si tu veux uniquement le backend (deja poussé, plus nécessaire).",
         "25 Ko · ZIP"),
        ("Site propre (ZIP complet)",
         "site-propre",
         "mesurechassis.com nettoyé, index.html mis à jour, sitemap complet.",
         "2.9 Mo · ZIP"),
        ("Page démo seule (HTML)",
         "demo-html",
         "Uniquement le fichier demo.html si vous voulez juste le mettre à jour.",
         "31 Ko · HTML"),
        ("Sitemap XML",
         "sitemap-xml",
         "Nouveau sitemap avec toutes les pages incluant Démo et Tarifs.",
         "2.3 Ko · XML"),
        ("Kit CapCut vidéo démo",
         "kit-video-capcut",
         "Storyboard 60s + script voix off + recommandations musique.",
         "11 Ko · Markdown"),
    ]
    rows = "".join(
        f'''<a class="dl" href="/api/_downloads/{slug}">
             <div>
               <div class="title">{title}</div>
               <div class="desc">{desc}</div>
             </div>
             <div class="meta">{meta}<span class="arrow">↓</span></div>
           </a>'''
        for title, slug, desc, meta in files
    )
    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="fr"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Téléchargements — MesureChâssis</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, "Segoe UI", Roboto, sans-serif;
    background: #0a0a0c; color: #f5f5f5;
    min-height: 100vh; padding: 24px 18px;
  }}
  .wrap {{ max-width: 640px; margin: 0 auto; }}
  h1 {{
    font-size: 22px; font-weight: 900; margin-bottom: 6px;
    letter-spacing: -0.4px;
  }}
  h1 span {{ color: #FF5A00; }}
  p.sub {{ color: #9E9EA5; font-size: 13.5px; margin-bottom: 28px; line-height: 1.5; }}
  .dl {{
    display: flex; align-items: center; justify-content: space-between;
    gap: 14px; background: #16161a; border: 1px solid #2a2a30;
    border-radius: 14px; padding: 18px 18px;
    margin-bottom: 12px; text-decoration: none; color: inherit;
    transition: border-color .15s, transform .1s;
  }}
  .dl:hover, .dl:active {{ border-color: #FF5A00; transform: translateY(-1px); }}
  .title {{ font-weight: 700; font-size: 15px; color: #ffffff; margin-bottom: 4px; }}
  .desc {{ font-size: 12.5px; color: #9E9EA5; line-height: 1.45; }}
  .meta {{
    display: flex; flex-direction: column; align-items: flex-end;
    gap: 6px; flex-shrink: 0; font-size: 11px; color: #737383;
  }}
  .arrow {{
    display: inline-flex; width: 36px; height: 36px; border-radius: 50%;
    background: #FF5A00; color: #0a0a0c; font-weight: 900; font-size: 18px;
    justify-content: center; align-items: center;
  }}
</style></head><body><div class="wrap">
  <h1>📥 Téléchargements <span>MesureChâssis</span></h1>
  <p class="sub">Touchez un fichier pour le télécharger directement — plus besoin de copier une URL à la main.</p>
  {rows}
</div></body></html>""")



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


@api.get("/_downloads/site-appstore")
async def download_site_appstore():
    """
    ZIP contenant les fichiers du site vitrine mis à jour :
    - QR Code App Store (4 versions PNG/SVG)
    - 7 pages HTML refondues (5 plans, section Entreprise MAX, Expertise MAX,
      Priorité 5 Générateur de devis, QR download page, etc.)
    À uploader tel quel via FTP à la racine du site.
    """
    path = "/app/backend/public_downloads/mesurechassis-site-appstore-v2.zip"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Archive introuvable")
    return FileResponse(
        path,
        media_type="application/zip",
        filename="mesurechassis-site-appstore-v2.zip",
    )


@api.get("/_downloads/site-v2-4tiers")
async def download_site_v2_4tiers():
    """🆕 Site vitrine mesurechassis.com — refonte 4 tiers + Enterprise MAX (juil. 2026).

    Contient l'intégralité du répertoire /site_mesurechassis_final avec la
    nouvelle section tarifs alignée sur le backend :
      • Freemium (0 €)  • Standard (19,99 €)  • Team (49,99 €)
      • Pro (99,99 €)   • Enterprise MAX (Sur devis · Bientôt)

    À uploader tel quel via FTP à la racine du site (remplace les anciens
    fichiers, garde les mêmes URLs).
    """
    path = "/app/backend/public_downloads/site_v2_4tiers.zip"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Archive introuvable")
    return FileResponse(
        path,
        media_type="application/zip",
        filename="mesurechassis-site-v2-4tiers.zip",
    )


# 🚀 v1.1.4 — Audit landing page + trackers + Calendly + preuve sociale (24 juil 2026)
@api.get("/_downloads/site-v2-audit-ads-ready")
async def download_site_v2_audit_ads_ready():
    """🚀 Site vitrine mesurechassis.com — version "prête pour Ads" (24 juil 2026).

    Version bonifiée avec :
      • Bandeau promo "Gratuit jusqu'à 31 oct 2026"
      • Trackers Meta Pixel + GA4 + Google Ads Conversion + Schema.org
      • Bouton "📞 Réserver 15 min avec Michel" (Calendly, avec placeholder)
      • Section preuve sociale (4 chiffres clés)
      • Twitter Card + Open Graph enrichis

    ⚠️ Contient un README_TRACKERS.md à lire — 4 IDs à remplacer avant upload FTP.

    À uploader tel quel via FTP à la racine du site.
    """
    path = "/app/backend/static/promo/mesurechassis-site-v2.zip"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Archive introuvable")
    return FileResponse(
        path,
        media_type="application/zip",
        filename="mesurechassis-site-v2-audit-ads-ready.zip",
    )


@api.get("/_downloads/site-index-html")
async def download_site_index_html():
    """🆕 Fichier index.html modifié cette session (juil. 2026).

    Seul fichier ayant changé : la section tarifs est passée de 2 plans
    (Artisan Solo 24,99 € / Société 54,99 €) à 5 cartes (Freemium 0 € ·
    Standard 19,99 € · Team 49,99 € populaire · Pro 99,99 € · Enterprise
    MAX Bientôt), alignée sur `backend/seats.py`.

    À uploader tel quel via FTP à la racine de mesurechassis.com pour
    écraser l'ancien index.html — les autres pages n'ont pas changé.
    """
    path = "/app/site_mesurechassis_final/index.html"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="index.html introuvable")
    return FileResponse(
        path,
        media_type="text/html; charset=utf-8",
        filename="index.html",
    )


@api.get("/_downloads/panneau-cafe-a3")
async def download_panneau_cafe_a3():
    """Panneau A3 (chevalet de comptoir) — Campagne Café en station-service.
    HTML → à ouvrir puis Fichier → Imprimer → PDF (format A3)."""
    path = "/app/backend/public_downloads/print/panneau-A3-cafe.html"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    return FileResponse(path, media_type="text/html", filename="panneau-A3-cafe.html")


@api.get("/_downloads/panneau-cafe-a3/preview", response_class=HTMLResponse)
async def preview_panneau_cafe_a3():
    """Aperçu direct du panneau (sans download)."""
    path = "/app/backend/public_downloads/print/panneau-A3-cafe.html"
    if not os.path.isfile(path):
        raise HTTPException(404, "Fichier introuvable")
    with open(path, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@api.get("/_downloads/fiche-pompiste-a5")
async def download_fiche_pompiste_a5():
    """Fiche pompiste A5 — Guide simple pour valider le café offert."""
    path = "/app/backend/public_downloads/print/fiche-pompiste-A5.html"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    return FileResponse(path, media_type="text/html", filename="fiche-pompiste-A5.html")


@api.get("/_downloads/fiche-pompiste-a5/preview", response_class=HTMLResponse)
async def preview_fiche_pompiste_a5():
    """Aperçu direct de la fiche pompiste."""
    path = "/app/backend/public_downloads/print/fiche-pompiste-A5.html"
    if not os.path.isfile(path):
        raise HTTPException(404, "Fichier introuvable")
    with open(path, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@api.get("/_downloads/dossier-cafe")
async def download_dossier_cafe():
    """Dossier complet 12 pages — À imprimer via le navigateur (Cmd/Ctrl+P → PDF)."""
    path = "/app/backend/public_downloads/print/dossier-cafe-complet.html"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    return FileResponse(path, media_type="text/html", filename="dossier-cafe-mesurechassis.html")


@api.get("/_downloads/dossier-cafe/preview", response_class=HTMLResponse)
async def preview_dossier_cafe():
    """Aperçu direct du dossier 12 pages (impression → PDF)."""
    path = "/app/backend/public_downloads/print/dossier-cafe-complet.html"
    if not os.path.isfile(path):
        raise HTTPException(404, "Fichier introuvable")
    with open(path, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


# ------------------------------------------------------------------
# Guides mode d'emploi : Débutant & Professionnel
# ------------------------------------------------------------------
@api.get("/_downloads/guide-debutant")
async def download_guide_debutant():
    """Mode d'emploi pour novices : découverte de la fenêtre et prise de mesure pas-à-pas."""
    path = "/app/backend/public_downloads/print/guide-debutant.html"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    return FileResponse(
        path,
        media_type="text/html",
        filename="mesurechassis-guide-debutant.html",
    )


@api.get("/_downloads/guide-debutant/preview", response_class=HTMLResponse)
async def preview_guide_debutant():
    """Aperçu direct du guide débutant (impression → PDF via Cmd/Ctrl+P)."""
    path = "/app/backend/public_downloads/print/guide-debutant.html"
    if not os.path.isfile(path):
        raise HTTPException(404, "Fichier introuvable")
    with open(path, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@api.get("/_downloads/guide-pro")
async def download_guide_pro():
    """Mode d'emploi pour professionnels de la menuiserie bois / alu / PVC."""
    path = "/app/backend/public_downloads/print/guide-pro.html"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    return FileResponse(
        path,
        media_type="text/html",
        filename="mesurechassis-guide-pro.html",
    )


@api.get("/_downloads/guide-pro/preview", response_class=HTMLResponse)
async def preview_guide_pro():
    """Aperçu direct du guide professionnel (impression → PDF via Cmd/Ctrl+P)."""
    path = "/app/backend/public_downloads/print/guide-pro.html"
    if not os.path.isfile(path):
        raise HTTPException(404, "Fichier introuvable")
    with open(path, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@api.get("/_downloads/guide-artisan-pro")
async def download_guide_artisan_pro():
    """Mode d'emploi Artisan solo & Entreprise Pro — RBAC, workflow équipe, exports."""
    path = "/app/backend/public_downloads/print/guide-artisan-pro.html"
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    return FileResponse(
        path,
        media_type="text/html",
        filename="mesurechassis-guide-artisan-pro.html",
    )


@api.get("/_downloads/guide-artisan-pro/preview", response_class=HTMLResponse)
async def preview_guide_artisan_pro():
    """Aperçu direct du guide Artisan & Entreprise Pro."""
    path = "/app/backend/public_downloads/print/guide-artisan-pro.html"
    if not os.path.isfile(path):
        raise HTTPException(404, "Fichier introuvable")
    with open(path, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@api.get("/_downloads/appstore-screenshots-v114")
async def download_appstore_screenshots_v114():
    """ZIP des 5 screenshots App Store format iPhone 6.9" (1320x2868)."""
    path = "/app/backend/public_downloads/appstore_screenshots_v114.zip"
    if not os.path.isfile(path):
        raise HTTPException(404, "ZIP introuvable")
    return FileResponse(
        path,
        media_type="application/zip",
        filename="mesurechassis-appstore-6_9-v114.zip",
    )


@api.get("/_downloads/appstore-screenshots-6_9-v114")
async def download_appstore_screenshots_6_9():
    """ZIP iPhone 6.9\" — 1320x2868 (iPhone 16 Pro Max)."""
    path = "/app/backend/public_downloads/appstore_screenshots_6_9_v114.zip"
    if not os.path.isfile(path):
        raise HTTPException(404, "ZIP introuvable")
    return FileResponse(path, media_type="application/zip",
                        filename="mesurechassis-appstore-6_9-v114.zip")


@api.get("/_downloads/appstore-screenshots-6_7-v114")
async def download_appstore_screenshots_6_7():
    """ZIP iPhone 6.7\" — 1290x2796 (iPhone 15/14 Pro Max)."""
    path = "/app/backend/public_downloads/appstore_screenshots_6_7_v114.zip"
    if not os.path.isfile(path):
        raise HTTPException(404, "ZIP introuvable")
    return FileResponse(path, media_type="application/zip",
                        filename="mesurechassis-appstore-6_7-v114.zip")


@api.get("/_downloads/appstore-screenshots-6_5-v114")
async def download_appstore_screenshots_6_5():
    """ZIP iPhone 6.5\" — 1242x2688 (iPhone 11 Pro Max / XS Max)."""
    path = "/app/backend/public_downloads/appstore_screenshots_6_5_v114.zip"
    if not os.path.isfile(path):
        raise HTTPException(404, "ZIP introuvable")
    return FileResponse(path, media_type="application/zip",
                        filename="mesurechassis-appstore-6_5-v114.zip")


@api.get("/_downloads/appstore-screenshots-ipad-12_9-v114")
async def download_appstore_screenshots_ipad_12_9():
    """ZIP iPad Pro 12.9\" — 2048x2732."""
    path = "/app/backend/public_downloads/appstore_screenshots_ipad_12_9_v114.zip"
    if not os.path.isfile(path):
        raise HTTPException(404, "ZIP introuvable")
    return FileResponse(path, media_type="application/zip",
                        filename="mesurechassis-appstore-ipad-12_9-v114.zip")


@api.get("/_downloads/appstore-screenshots-ipad-13-v114")
async def download_appstore_screenshots_ipad_13():
    """ZIP iPad Pro 13\" (M4) — 2064x2752."""
    path = "/app/backend/public_downloads/appstore_screenshots_ipad_13_v114.zip"
    if not os.path.isfile(path):
        raise HTTPException(404, "ZIP introuvable")
    return FileResponse(path, media_type="application/zip",
                        filename="mesurechassis-appstore-ipad-13-v114.zip")


@api.get("/_downloads/appstore-screenshots/preview", response_class=HTMLResponse)
async def preview_appstore_screenshots():
    """Page d'aperçu des 5 screenshots App Store."""
    import base64
    slides = [
        (1, "01_login.png", "1. Login FR/NL/EN"),
        (2, "02_dashboard.png", "2. Dashboard"),
        (3, "03_modal_new_chantier.png", "3. Nouveau chantier (tel/email)"),
        (4, "04_fiche_chantier_wall_opt.png", "4. Fiche chantier + Wall OPT"),
        (5, "05_wizard_passer.png", "5. Wizard + bouton PASSER"),
    ]
    imgs_html = ""
    for num, fname, caption in slides:
        p = f"/app/backend/public_downloads/appstore_screenshots/{fname}"
        if os.path.isfile(p):
            with open(p, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            size_kb = os.path.getsize(p) // 1024
            imgs_html += (
                f'<figure style="margin:0;text-align:center">'
                f'<img src="data:image/png;base64,{b64}" '
                f'style="width:280px;height:auto;border-radius:20px;box-shadow:0 8px 20px rgba(0,0,0,.3)">'
                f'<figcaption style="color:#fff;font-family:-apple-system,sans-serif;'
                f'padding:12px 0;font-size:14px;font-weight:600">{caption}<br>'
                f'<small style="color:#a1a1aa;font-size:11px">1320x2868 px · {size_kb} Ko</small>'
                f'</figcaption></figure>'
            )
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Screenshots App Store — v114</title>
<style>body{{margin:0;padding:40px 20px;background:#0C0C0E;font-family:-apple-system,sans-serif}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:32px;max-width:1600px;margin:0 auto}}
h1{{color:#fff;text-align:center;margin:0 0 24px;font-size:26px}}
.dl{{display:block;background:#FF5A00;color:#fff;text-align:center;padding:14px 24px;border-radius:12px;text-decoration:none;font-weight:700;max-width:400px;margin:0 auto 40px}}
</style></head><body>
<h1>📱 Screenshots App Store — MesureChâssis v114</h1>
<a href="/api/_downloads/appstore-screenshots-v114" class="dl">📦 Télécharger le ZIP (5 PNG · 1320×2868)</a>
<div class="grid">{imgs_html}</div>
</body></html>"""
    return HTMLResponse(html)


@api.get("/_downloads/appstore-screenshot/{num}")
async def download_appstore_screenshot(num: int):
    """PNG individuel App Store (1 a 5)."""
    mapping = {
        1: "01_login.png",
        2: "02_dashboard.png",
        3: "03_modal_new_chantier.png",
        4: "04_fiche_chantier_wall_opt.png",
        5: "05_wizard_passer.png",
    }
    if num not in mapping:
        raise HTTPException(404, "Numero invalide (1-5)")
    path = f"/app/backend/public_downloads/appstore_screenshots/{mapping[num]}"
    if not os.path.isfile(path):
        raise HTTPException(404, "Fichier introuvable")
    return FileResponse(path, media_type="image/png", filename=mapping[num])


@api.get("/_downloads/email-launch/preview", response_class=HTMLResponse)
async def preview_email_launch():
    """Aperçu du template email 'Lancement App Store'.

    Génère un email de démo avec Marc Dubois / Menuiserie Dubois comme
    destinataire fictif, pour valider visuellement le rendu avant envoi
    réel. Le prospect fictif est créé puis supprimé pour ne pas polluer
    la DB.
    """
    import sys
    sys.path.insert(0, "/app/backend")
    from db import db as pdb
    from services.prospection_utils import upsert_prospect
    from send_launch_appstore import render_email
    p = await upsert_prospect(
        "preview.demo@mesurechassis.fr",
        first_name="Marc",
        company="Menuiserie Dubois",
        source="preview_only",
    )
    _, body = render_email(
        first_name="Marc",
        company="Menuiserie Dubois",
        prospect_id=p["id"],
        email=p["email"],
    )
    # Cleanup — on ne garde pas le prospect fictif en DB
    await pdb.prospects.delete_many({"email": "preview.demo@mesurechassis.fr"})
    return HTMLResponse(body)


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
