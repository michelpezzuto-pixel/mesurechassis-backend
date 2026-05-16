"""MesureChâssis backend - FastAPI + MongoDB."""
from __future__ import annotations

import io
import logging
import math
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Any, List, Optional

import jwt
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)
from starlette.middleware.cors import CORSMiddleware

# --- Setup ---------------------------------------------------------------
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("mesurechassis")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
JWT_SECRET = os.environ.get("JWT_SECRET", "change-me-mesurechassis-secret-key-dev-only")
JWT_ALGO = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="MesureChâssis API")
api = APIRouter(prefix="/api")

VALID_ROLES = {"admin", "commercial", "technician"}
VALID_STATUSES = {"devis_a_faire", "technique_a_valider", "cloture"}
VALID_BLOCK_TYPES = {"standard", "coulissant", "porte", "trapeze"}


# --- Models --------------------------------------------------------------
class UserPublic(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: str
    company_id: str


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "technician"
    company_id: str = "default"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class ChantierCreate(BaseModel):
    client_name: str
    address: str
    status: str = "devis_a_faire"
    assigned_to: Optional[str] = None


class ChantierUpdate(BaseModel):
    client_name: Optional[str] = None
    address: Optional[str] = None
    status: Optional[str] = None
    assigned_to: Optional[str] = None


class Chantier(BaseModel):
    id: str
    client_name: str
    address: str
    status: str
    created_by: str
    assigned_to: Optional[str] = None
    company_id: str = "default"
    created_at: str


class MesureCreate(BaseModel):
    chantier_id: str
    block_type: str
    label: str
    width_top: Optional[float] = None
    width_middle: Optional[float] = None
    width_bottom: Optional[float] = None
    height_left: Optional[float] = None
    height_middle: Optional[float] = None
    height_right: Optional[float] = None
    diag_1: Optional[float] = None
    diag_2: Optional[float] = None
    height_quarter_left: Optional[float] = None
    height_quarter_right: Optional[float] = None
    height_small: Optional[float] = None
    height_large: Optional[float] = None
    width_small: Optional[float] = None
    width_intermediate: Optional[float] = None
    options: dict = Field(default_factory=dict)
    photo_url: Optional[str] = None  # base64 data URL


class Mesure(MesureCreate):
    id: str
    created_at: str
    alerts: List[str] = Field(default_factory=list)
    slope_angle_deg: Optional[float] = None


class FeedbackCreate(BaseModel):
    page_context: str
    user_comment: str
    screenshot_data: Optional[str] = None  # base64
    encoded_data_snapshot: dict = Field(default_factory=dict)


class Feedback(BaseModel):
    id: str
    user_id: str
    user_email: str
    page_context: str
    user_comment: str
    screenshot_data: Optional[str] = None
    encoded_data_snapshot: dict
    company_id: str = "default"
    created_at: str


# --- Helpers -------------------------------------------------------------
def hash_password(p: str) -> str:
    return pwd_context.hash(p)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": user_id, "role": role, "exp": expire},
                      JWT_SECRET, algorithm=JWT_ALGO)


def user_to_public(doc: dict) -> UserPublic:
    return UserPublic(id=doc["id"], name=doc["name"], email=doc["email"],
                      role=doc["role"], company_id=doc.get("company_id", "default"))


async def get_current_user(authorization: Annotated[Optional[str], Depends(lambda: None)] = None,
                           **kwargs) -> dict:
    raise NotImplementedError  # replaced below by header dep


# Real dep using Header
from fastapi import Header


async def auth_user(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def require_admin(user: dict = Depends(auth_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return user


# --- Calculation logic ---------------------------------------------------
def compute_alerts(m: MesureCreate) -> tuple[list[str], Optional[float]]:
    alerts: list[str] = []
    slope: Optional[float] = None
    bt = m.block_type
    if bt == "standard":
        widths = [v for v in (m.width_top, m.width_middle, m.width_bottom) if v is not None]
        heights = [v for v in (m.height_left, m.height_middle, m.height_right) if v is not None]
        if widths and (max(widths) - min(widths)) > 5:
            alerts.append("⚠️ Faux-aplomb détecté (largeurs)")
        if heights and (max(heights) - min(heights)) > 5:
            alerts.append("⚠️ Faux-aplomb détecté (hauteurs)")
        if m.diag_1 is not None and m.diag_2 is not None and abs(m.diag_1 - m.diag_2) > 5:
            alerts.append("⚠️ Hors-équerre")
    elif bt == "coulissant":
        widths = [m.width_top, m.width_middle, m.width_bottom]
        heights = [m.height_left, m.height_quarter_left, m.height_middle,
                   m.height_quarter_right, m.height_right]
        if any(v is None for v in widths):
            alerts.append("ℹ️ 3 largeurs requises (haut/milieu/bas)")
        if any(v is None for v in heights):
            alerts.append("ℹ️ 5 hauteurs requises pour détecter la flèche du linteau")
        valid_h = [v for v in heights if v is not None]
        if len(valid_h) >= 3 and (max(valid_h) - min(valid_h)) > 5:
            alerts.append("⚠️ Flèche du linteau détectée")
    elif bt == "trapeze":
        if (m.width_small is not None and m.width_intermediate is not None
                and m.height_small is not None and m.height_large is not None):
            dw = abs(m.width_intermediate - m.width_small)
            dh = abs(m.height_large - m.height_small)
            if dw > 0:
                slope = round(math.degrees(math.atan(dh / dw)), 2)
    return alerts, slope


# --- Auth routes ---------------------------------------------------------
@api.post("/auth/register", response_model=TokenResponse)
async def register(payload: UserCreate):
    if payload.role not in VALID_ROLES:
        raise HTTPException(400, "Invalid role")
    existing = await db.users.find_one({"email": payload.email.lower()})
    if existing:
        raise HTTPException(400, "Email already registered")
    user_doc = {
        "id": str(uuid.uuid4()),
        "name": payload.name,
        "email": payload.email.lower(),
        "role": payload.role,
        "company_id": payload.company_id,
        "hashed_password": hash_password(payload.password),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(user_doc)
    token = create_access_token(user_doc["id"], user_doc["role"])
    return TokenResponse(access_token=token, user=user_to_public(user_doc))


@api.post("/auth/login", response_model=TokenResponse)
async def login(payload: LoginRequest):
    user = await db.users.find_one({"email": payload.email.lower()})
    if not user or not verify_password(payload.password, user["hashed_password"]):
        raise HTTPException(401, "Email ou mot de passe incorrect")
    token = create_access_token(user["id"], user["role"])
    return TokenResponse(access_token=token, user=user_to_public(user))


@api.get("/auth/me", response_model=UserPublic)
async def me(user=Depends(auth_user)):
    return user_to_public(user)


@api.get("/users", response_model=List[UserPublic])
async def list_users(user=Depends(auth_user)):
    docs = await db.users.find({"company_id": user.get("company_id", "default")},
                                {"_id": 0, "hashed_password": 0}).to_list(500)
    return [user_to_public(d) for d in docs]


# --- Chantiers routes ----------------------------------------------------
@api.post("/chantiers", response_model=Chantier)
async def create_chantier(payload: ChantierCreate, user=Depends(auth_user)):
    if payload.status not in VALID_STATUSES:
        raise HTTPException(400, "Invalid status")
    doc = {
        "id": str(uuid.uuid4()),
        "client_name": payload.client_name,
        "address": payload.address,
        "status": payload.status,
        "created_by": user["id"],
        "assigned_to": payload.assigned_to,
        "company_id": user.get("company_id", "default"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.chantiers.insert_one(doc)
    doc.pop("_id", None)
    return Chantier(**doc)


@api.get("/chantiers", response_model=List[Chantier])
async def list_chantiers(status_filter: Optional[str] = None, q: Optional[str] = None,
                          user=Depends(auth_user)):
    query: dict = {"company_id": user.get("company_id", "default")}
    if status_filter and status_filter in VALID_STATUSES:
        query["status"] = status_filter
    if q:
        import re as _re
        safe = _re.escape(q.strip())
        query["$or"] = [
            {"client_name": {"$regex": safe, "$options": "i"}},
            {"address": {"$regex": safe, "$options": "i"}},
        ]
    docs = await db.chantiers.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return [Chantier(**d) for d in docs]


@api.get("/chantiers/{chantier_id}", response_model=Chantier)
async def get_chantier(chantier_id: str, user=Depends(auth_user)):
    doc = await db.chantiers.find_one(
        {"id": chantier_id, "company_id": user.get("company_id", "default")},
        {"_id": 0})
    if not doc:
        raise HTTPException(404, "Chantier introuvable")
    return Chantier(**doc)


@api.patch("/chantiers/{chantier_id}", response_model=Chantier)
async def update_chantier(chantier_id: str, payload: ChantierUpdate, user=Depends(auth_user)):
    company = user.get("company_id", "default")
    existing = await db.chantiers.find_one({"id": chantier_id, "company_id": company})
    if not existing:
        raise HTTPException(404, "Chantier introuvable")
    update = {k: v for k, v in payload.model_dump().items() if v is not None}
    if "status" in update and update["status"] not in VALID_STATUSES:
        raise HTTPException(400, "Invalid status")
    if update:
        await db.chantiers.update_one({"id": chantier_id, "company_id": company}, {"$set": update})
    doc = await db.chantiers.find_one({"id": chantier_id, "company_id": company}, {"_id": 0})
    return Chantier(**doc)


@api.delete("/chantiers/{chantier_id}")
async def delete_chantier(chantier_id: str, user=Depends(auth_user)):
    company = user.get("company_id", "default")
    res = await db.chantiers.delete_one({"id": chantier_id, "company_id": company})
    if res.deleted_count:
        await db.mesures.delete_many({"chantier_id": chantier_id})
    return {"ok": True}


# --- Mesures routes ------------------------------------------------------
async def _check_chantier_access(chantier_id: str, user: dict) -> dict:
    chantier = await db.chantiers.find_one(
        {"id": chantier_id, "company_id": user.get("company_id", "default")})
    if not chantier:
        raise HTTPException(404, "Chantier introuvable")
    return chantier


@api.post("/mesures", response_model=Mesure)
async def create_mesure(payload: MesureCreate, user=Depends(auth_user)):
    if payload.block_type not in VALID_BLOCK_TYPES:
        raise HTTPException(400, "Invalid block_type")
    await _check_chantier_access(payload.chantier_id, user)
    alerts, slope = compute_alerts(payload)
    doc = payload.model_dump()
    doc.update({
        "id": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "alerts": alerts,
        "slope_angle_deg": slope,
    })
    await db.mesures.insert_one(doc)
    doc.pop("_id", None)
    return Mesure(**doc)


@api.get("/chantiers/{chantier_id}/mesures", response_model=List[Mesure])
async def list_mesures(chantier_id: str, user=Depends(auth_user)):
    await _check_chantier_access(chantier_id, user)
    docs = await db.mesures.find({"chantier_id": chantier_id}, {"_id": 0}) \
        .sort("created_at", 1).to_list(500)
    return [Mesure(**d) for d in docs]


@api.delete("/mesures/{mesure_id}")
async def delete_mesure(mesure_id: str, user=Depends(auth_user)):
    mesure = await db.mesures.find_one({"id": mesure_id})
    if mesure:
        await _check_chantier_access(mesure["chantier_id"], user)
        await db.mesures.delete_one({"id": mesure_id})
    return {"ok": True}


# --- Feedback routes -----------------------------------------------------
@api.post("/feedbacks", response_model=Feedback)
async def create_feedback(payload: FeedbackCreate, user=Depends(auth_user)):
    doc = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "user_email": user["email"],
        "page_context": payload.page_context,
        "user_comment": payload.user_comment,
        "screenshot_data": payload.screenshot_data,
        "encoded_data_snapshot": payload.encoded_data_snapshot,
        "company_id": user.get("company_id", "default"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.feedbacks.insert_one(doc)
    doc.pop("_id", None)
    return Feedback(**doc)


@api.get("/feedbacks", response_model=List[Feedback])
async def list_feedbacks(user=Depends(require_admin)):
    docs = await db.feedbacks.find(
        {"company_id": user.get("company_id", "default")},
        {"_id": 0}).sort("created_at", -1).to_list(500)
    return [Feedback(**d) for d in docs]


@api.delete("/feedbacks/{feedback_id}")
async def delete_feedback(feedback_id: str, user=Depends(require_admin)):
    await db.feedbacks.delete_one(
        {"id": feedback_id, "company_id": user.get("company_id", "default")})
    return {"ok": True}


# --- Export routes -------------------------------------------------------
def _status_label(s: str) -> str:
    return {"devis_a_faire": "Devis à faire",
            "technique_a_valider": "Technique à valider",
            "cloture": "Clôturé"}.get(s, s)


def _block_label(b: str) -> str:
    return {"standard": "Standard", "coulissant": "Coulissant",
            "porte": "Porte", "trapeze": "Trapèze"}.get(b, b)


@api.get("/chantiers/{chantier_id}/export.pdf")
async def export_pdf(chantier_id: str, user=Depends(auth_user)):
    chantier = await db.chantiers.find_one({"id": chantier_id}, {"_id": 0})
    if not chantier:
        raise HTTPException(404, "Chantier introuvable")
    mesures = await db.mesures.find({"chantier_id": chantier_id}, {"_id": 0}) \
        .sort("created_at", 1).to_list(500)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title=f"MesureChâssis - {chantier['client_name']}")
    styles = getSampleStyleSheet()
    story: list[Any] = []

    story.append(Paragraph("<b>MesureChâssis</b> — Fiche Chantier", styles["Title"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"<b>Client :</b> {chantier['client_name']}", styles["Normal"]))
    story.append(Paragraph(f"<b>Adresse :</b> {chantier['address']}", styles["Normal"]))
    story.append(Paragraph(f"<b>Statut :</b> {_status_label(chantier['status'])}", styles["Normal"]))
    story.append(Paragraph(f"<b>Date :</b> {chantier['created_at'][:10]}", styles["Normal"]))
    story.append(Spacer(1, 18))
    story.append(Paragraph(f"<b>Ouvertures ({len(mesures)})</b>", styles["Heading2"]))

    for i, m in enumerate(mesures, 1):
        story.append(Spacer(1, 8))
        story.append(Paragraph(
            f"<b>#{i} — {m.get('label', '')} ({_block_label(m['block_type'])})</b>",
            styles["Heading3"]))
        rows = [["Mesure", "Valeur (mm)"]]
        fields = [
            ("Largeur haut", m.get("width_top")),
            ("Largeur milieu", m.get("width_middle")),
            ("Largeur bas", m.get("width_bottom")),
            ("Hauteur gauche", m.get("height_left")),
            ("Hauteur milieu", m.get("height_middle")),
            ("Hauteur droite", m.get("height_right")),
            ("Diagonale 1", m.get("diag_1")),
            ("Diagonale 2", m.get("diag_2")),
            ("Hauteur 1/4 gauche", m.get("height_quarter_left")),
            ("Hauteur 1/4 droite", m.get("height_quarter_right")),
            ("Hauteur petite", m.get("height_small")),
            ("Hauteur grande", m.get("height_large")),
            ("Largeur petite", m.get("width_small")),
            ("Largeur intermédiaire", m.get("width_intermediate")),
        ]
        for label, val in fields:
            if val is not None:
                rows.append([label, str(val)])
        if m.get("slope_angle_deg") is not None:
            rows.append(["Angle de pente", f"{m['slope_angle_deg']}°"])
        tbl = Table(rows, colWidths=[260, 200])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FF5A00")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]))
        story.append(tbl)
        if m.get("alerts"):
            story.append(Spacer(1, 4))
            for a in m["alerts"]:
                story.append(Paragraph(
                    f'<font color="#CC0000">{a}</font>', styles["Normal"]))

    doc.build(story)
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/pdf",
                             headers={"Content-Disposition":
                                      f'attachment; filename="chantier-{chantier_id}.pdf"'})


@api.get("/chantiers/{chantier_id}/export.json")
async def export_json(chantier_id: str, user=Depends(auth_user)):
    chantier = await db.chantiers.find_one(
        {"id": chantier_id, "company_id": user.get("company_id", "default")},
        {"_id": 0})
    if not chantier:
        raise HTTPException(404, "Chantier introuvable")
    mesures = await db.mesures.find({"chantier_id": chantier_id}, {"_id": 0}) \
        .sort("created_at", 1).to_list(500)
    return {"chantier": chantier, "mesures": mesures}


# --- Demo data seeding ---------------------------------------------------
DEMO_USERS = [
    {"name": "Marc Dubois", "email": "admin@mesurechassis.fr",
     "password": "admin123", "role": "admin"},
    {"name": "Sophie Martin", "email": "commercial@mesurechassis.fr",
     "password": "commercial123", "role": "commercial"},
    {"name": "Lucas Petit", "email": "tech@mesurechassis.fr",
     "password": "tech123", "role": "technician"},
]


@app.on_event("startup")
async def seed_data():
    # Seed users (idempotent)
    user_ids: dict[str, str] = {}
    for u in DEMO_USERS:
        existing = await db.users.find_one({"email": u["email"]})
        if existing:
            user_ids[u["role"]] = existing["id"]
            continue
        uid = str(uuid.uuid4())
        await db.users.insert_one({
            "id": uid, "name": u["name"], "email": u["email"], "role": u["role"],
            "company_id": "default",
            "hashed_password": hash_password(u["password"]),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        user_ids[u["role"]] = uid
        logger.info("Seeded user %s", u["email"])

    # Seed chantiers if none exist
    if await db.chantiers.count_documents({}) == 0:
        demos = [
            ("Famille Lefèvre", "12 rue de la Paix, 75002 Paris", "devis_a_faire"),
            ("Boulangerie Moreau", "45 av. Victor Hugo, 69006 Lyon", "devis_a_faire"),
            ("M. et Mme Bernard", "8 chemin des Vignes, 33000 Bordeaux", "technique_a_valider"),
            ("SCI Le Clos", "23 rue Nationale, 59000 Lille", "technique_a_valider"),
            ("Cabinet Dr. Rousseau", "5 place Bellecour, 69002 Lyon", "cloture"),
        ]
        for name, addr, status_v in demos:
            await db.chantiers.insert_one({
                "id": str(uuid.uuid4()),
                "client_name": name,
                "address": addr,
                "status": status_v,
                "created_by": user_ids.get("commercial", "system"),
                "assigned_to": user_ids.get("technician"),
                "company_id": "default",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
        logger.info("Seeded %d demo chantiers", len(demos))

    # Backfill missing company_id on existing rows (from previous schema)
    await db.chantiers.update_many(
        {"company_id": {"$exists": False}}, {"$set": {"company_id": "default"}})
    await db.feedbacks.update_many(
        {"company_id": {"$exists": False}}, {"$set": {"company_id": "default"}})


# --- App wiring ----------------------------------------------------------
app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
