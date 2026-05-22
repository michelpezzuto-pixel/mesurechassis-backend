"""
MesureEscalier — Backend FastAPI server.
Roles: admin, commercial, technicien.
"""
from __future__ import annotations

import io
import math
import os
import logging
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional, Literal

import bcrypt
import jwt
from dotenv import load_dotenv
from fastapi import FastAPI, APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field
from starlette.middleware.cors import CORSMiddleware

# ReportLab for PDF
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image as RLImage,
)
from reportlab.graphics.shapes import Drawing, Line, Rect, String, Polygon
from reportlab.graphics import renderPDF

# OpenAI for Whisper
from openai import OpenAI

# ------------------------------------------------------------
# Setup
# ------------------------------------------------------------
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("mesure_escalier")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGO = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_EXPIRES_HOURS = int(os.environ.get("JWT_EXPIRES_HOURS", "168"))
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# OpenAI client for Whisper, routed via Emergent gateway
openai_client = OpenAI(
    api_key=EMERGENT_LLM_KEY,
    base_url="https://integrations.emergentagent.com/llm",
)

app = FastAPI(title="MesureEscalier API")
api = APIRouter(prefix="/api")
security = HTTPBearer(auto_error=False)

Role = Literal["admin", "commercial", "technicien"]
ProjectStatus = Literal["brouillon", "a_mesurer", "a_verifier", "valide", "en_fabrication", "termine"]


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


def make_token(user_id: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "role": role,
        "exp": now_utc() + timedelta(hours=JWT_EXPIRES_HOURS),
        "iat": now_utc(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


async def get_current_user(creds: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    if not creds:
        raise HTTPException(status_code=401, detail="Token manquant")
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALGO])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expiré")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token invalide")
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur introuvable")
    return user


def require_roles(*roles: str):
    async def checker(user=Depends(get_current_user)):
        if user["role"] not in roles:
            raise HTTPException(status_code=403, detail=f"Accès refusé (rôles autorisés: {', '.join(roles)})")
        return user
    return checker


# ------------------------------------------------------------
# Pydantic Models
# ------------------------------------------------------------
class UserPublic(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: Role
    company_name: Optional[str] = None
    created_at: datetime


class RegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str = Field(min_length=6)
    company_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    token: str
    user: UserPublic


class InviteUserRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str = Field(min_length=6)
    role: Literal["commercial", "technicien"]


class ProjectCreate(BaseModel):
    client_nom: str
    client_prenom: Optional[str] = ""
    address: str
    postal_code: Optional[str] = ""
    city: Optional[str] = ""
    phone: Optional[str] = ""
    appointment_date: Optional[datetime] = None
    notes: Optional[str] = ""


class ProjectUpdate(BaseModel):
    client_nom: Optional[str] = None
    client_prenom: Optional[str] = None
    address: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    phone: Optional[str] = None
    appointment_date: Optional[datetime] = None
    notes: Optional[str] = None


class AssignRequest(BaseModel):
    technicien_id: str


class MeasurementInput(BaseModel):
    material: Literal["acier", "bois", "beton"]
    hauteur_brute: float
    sols_finis_zero: bool = True
    reserve_bas: float = 0
    reserve_haut: float = 0
    epaisseur_dalle: float
    tremie_longueur: float
    tremie_largeur: float
    reculement_max: float
    remarques: str


class MeasurementResult(BaseModel):
    true_height: float
    n_steps: int
    h: float
    g: float
    slope_angle: float
    hypotenuse: float
    reculement_needed: float
    shape: str
    blondel_value: float
    valid_blondel: bool
    notes: List[str] = []


class MeasurementFull(MeasurementInput):
    project_id: str
    result: MeasurementResult
    validated: bool = False
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


# ------------------------------------------------------------
# Calculation engine (Blondel's law)
# ------------------------------------------------------------
def compute_stair(inp: MeasurementInput) -> MeasurementResult:
    # True height
    if inp.sols_finis_zero:
        true_h = inp.hauteur_brute
    else:
        true_h = inp.hauteur_brute - inp.reserve_bas - inp.reserve_haut

    notes: List[str] = []
    if true_h <= 0:
        raise HTTPException(status_code=400, detail="Hauteur effective invalide (négative ou nulle)")

    # Ideal riser ~ 175mm, search best n
    best = None
    for n in range(8, 25):
        h = true_h / n
        if h < 150 or h > 220:
            continue
        g = 630 - 2 * h  # Blondel target 630mm
        if g < 200 or g > 350:
            continue
        # closer to target h=175 and Blondel=630 is better
        score = abs(h - 175) + abs((2 * h + g) - 630) * 0.5
        if best is None or score < best[0]:
            best = (score, n, h, g)

    if best is None:
        # Fallback: round to nearest 175mm
        n = max(1, round(true_h / 175))
        h = true_h / n
        g = max(200, min(350, 630 - 2 * h))
        notes.append("Hors plage idéale: ajustement manuel recommandé.")
    else:
        _, n, h, g = best

    reculement_needed = (n - 1) * g  # treads = n-1
    hypotenuse = math.sqrt(true_h ** 2 + reculement_needed ** 2)
    slope = math.degrees(math.atan2(true_h, reculement_needed))
    blondel = 2 * h + g
    valid_blondel = 600 <= blondel <= 640

    # Shape detection
    if inp.reculement_max >= reculement_needed:
        shape = "Escalier Droit Recommandé"
    elif inp.reculement_max >= reculement_needed * 0.65:
        shape = "Quart-tournant requis"
        notes.append("Reculement insuffisant pour escalier droit, quart-tournant nécessaire.")
    else:
        shape = "Double quart-tournant ou hélicoïdal"
        notes.append("Reculement très limité: envisager un escalier hélicoïdal ou en colimaçon.")

    if not valid_blondel:
        notes.append(f"Loi de Blondel hors plage: {round(blondel)}mm (idéal 600-640mm).")

    if slope > 42:
        notes.append("Pente élevée (>42°): inconfortable, à valider client.")
    elif slope < 25:
        notes.append("Pente faible (<25°): vérifier reculement.")

    return MeasurementResult(
        true_height=round(true_h, 1),
        n_steps=n,
        h=round(h, 1),
        g=round(g, 1),
        slope_angle=round(slope, 2),
        hypotenuse=round(hypotenuse, 1),
        reculement_needed=round(reculement_needed, 1),
        shape=shape,
        blondel_value=round(blondel, 1),
        valid_blondel=valid_blondel,
        notes=notes,
    )


# ------------------------------------------------------------
# Auth Endpoints
# ------------------------------------------------------------
@api.post("/auth/register", response_model=AuthResponse)
async def register(req: RegisterRequest):
    existing = await db.users.find_one({"email": req.email.lower()})
    if existing:
        raise HTTPException(status_code=409, detail="Email déjà utilisé")
    user_id = str(uuid.uuid4())
    user_doc = {
        "id": user_id,
        "email": req.email.lower(),
        "full_name": req.full_name,
        "company_name": req.company_name or req.full_name,
        "role": "admin",  # First registration creates a Master Admin
        "password_hash": hash_password(req.password),
        "created_at": now_utc(),
    }
    await db.users.insert_one(user_doc)
    token = make_token(user_id, "admin")
    user_doc.pop("password_hash")
    user_doc.pop("_id", None)
    return AuthResponse(token=token, user=UserPublic(**user_doc))


@api.post("/auth/login", response_model=AuthResponse)
async def login(req: LoginRequest):
    user = await db.users.find_one({"email": req.email.lower()})
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    token = make_token(user["id"], user["role"])
    user.pop("password_hash", None)
    user.pop("_id", None)
    return AuthResponse(token=token, user=UserPublic(**user))


@api.get("/auth/me", response_model=UserPublic)
async def me(user=Depends(get_current_user)):
    return UserPublic(**user)


# ------------------------------------------------------------
# Users (Admin invites Commercial / Technicien)
# ------------------------------------------------------------
@api.get("/users", response_model=List[UserPublic])
async def list_users(user=Depends(require_roles("admin"))):
    rows = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(1000)
    return [UserPublic(**r) for r in rows]


@api.post("/users", response_model=UserPublic)
async def invite_user(req: InviteUserRequest, user=Depends(require_roles("admin"))):
    if await db.users.find_one({"email": req.email.lower()}):
        raise HTTPException(status_code=409, detail="Email déjà utilisé")
    uid = str(uuid.uuid4())
    doc = {
        "id": uid,
        "email": req.email.lower(),
        "full_name": req.full_name,
        "company_name": user.get("company_name"),
        "role": req.role,
        "password_hash": hash_password(req.password),
        "created_at": now_utc(),
    }
    await db.users.insert_one(doc)
    doc.pop("password_hash")
    doc.pop("_id", None)
    return UserPublic(**doc)


@api.delete("/users/{uid}")
async def delete_user(uid: str, user=Depends(require_roles("admin"))):
    if uid == user["id"]:
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas vous supprimer vous-même")
    res = await db.users.delete_one({"id": uid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    return {"ok": True}


# ------------------------------------------------------------
# Projects
# ------------------------------------------------------------
def project_visible_to(user) -> dict:
    """MongoDB filter restricting projects to the user's scope."""
    if user["role"] == "admin":
        return {}
    if user["role"] == "commercial":
        return {"commercial_id": user["id"]}
    if user["role"] == "technicien":
        return {"technicien_id": user["id"]}
    return {"_never_match": True}


@api.get("/projects")
async def list_projects(user=Depends(get_current_user), status_filter: Optional[str] = None):
    q = project_visible_to(user)
    if status_filter and status_filter != "tous":
        q["status"] = status_filter
    rows = await db.projects.find(q, {"_id": 0}).sort("created_at", -1).to_list(2000)
    return rows


@api.post("/projects")
async def create_project(payload: ProjectCreate, user=Depends(require_roles("admin", "commercial"))):
    pid = str(uuid.uuid4())
    doc = {
        "id": pid,
        **payload.model_dump(),
        "status": "brouillon",
        "commercial_id": user["id"],
        "technicien_id": None,
        "company_name": user.get("company_name"),
        "locked": False,
        "transmitted_at": None,
        "created_at": now_utc(),
        "updated_at": now_utc(),
    }
    await db.projects.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api.get("/projects/{pid}")
async def get_project(pid: str, user=Depends(get_current_user)):
    q = {"id": pid, **project_visible_to(user)}
    p = await db.projects.find_one(q, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Chantier introuvable")
    m = await db.measurements.find_one({"project_id": pid}, {"_id": 0})
    p["measurement"] = m
    return p


@api.put("/projects/{pid}")
async def update_project(pid: str, payload: ProjectUpdate, user=Depends(get_current_user)):
    p = await db.projects.find_one({"id": pid})
    if not p:
        raise HTTPException(status_code=404, detail="Chantier introuvable")
    if user["role"] == "commercial":
        if p["commercial_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="Non autorisé")
        if p.get("locked"):
            raise HTTPException(status_code=403, detail="Chantier verrouillé (déjà transmis)")
    elif user["role"] == "technicien":
        raise HTTPException(status_code=403, detail="Le technicien ne peut pas modifier l'identification client")
    update = {k: v for k, v in payload.model_dump().items() if v is not None}
    update["updated_at"] = now_utc()
    await db.projects.update_one({"id": pid}, {"$set": update})
    p = await db.projects.find_one({"id": pid}, {"_id": 0})
    return p


@api.delete("/projects/{pid}")
async def delete_project(pid: str, user=Depends(get_current_user)):
    p = await db.projects.find_one({"id": pid})
    if not p:
        raise HTTPException(status_code=404, detail="Chantier introuvable")
    if user["role"] == "admin":
        pass
    elif user["role"] == "commercial":
        if p["commercial_id"] != user["id"] or p.get("locked"):
            raise HTTPException(status_code=403, detail="Suppression interdite (verrouillé ou non propriétaire)")
    else:
        raise HTTPException(status_code=403, detail="Suppression interdite")
    await db.projects.delete_one({"id": pid})
    await db.measurements.delete_many({"project_id": pid})
    return {"ok": True}


@api.post("/projects/{pid}/transmit")
async def transmit_project(pid: str, user=Depends(require_roles("admin", "commercial"))):
    p = await db.projects.find_one({"id": pid})
    if not p:
        raise HTTPException(status_code=404, detail="Chantier introuvable")
    if user["role"] == "commercial" and p["commercial_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Non autorisé")
    await db.projects.update_one(
        {"id": pid},
        {"$set": {"locked": True, "status": "a_mesurer", "transmitted_at": now_utc(), "updated_at": now_utc()}},
    )
    return {"ok": True}


@api.post("/projects/{pid}/assign")
async def assign_technicien(pid: str, payload: AssignRequest, user=Depends(require_roles("admin"))):
    tech = await db.users.find_one({"id": payload.technicien_id, "role": "technicien"})
    if not tech:
        raise HTTPException(status_code=404, detail="Technicien introuvable")
    await db.projects.update_one(
        {"id": pid},
        {"$set": {"technicien_id": payload.technicien_id, "updated_at": now_utc()}},
    )
    return {"ok": True}


# ------------------------------------------------------------
# Measurements
# ------------------------------------------------------------
@api.post("/projects/{pid}/measurement")
async def save_measurement(pid: str, payload: MeasurementInput, user=Depends(require_roles("admin", "technicien"))):
    p = await db.projects.find_one({"id": pid})
    if not p:
        raise HTTPException(status_code=404, detail="Chantier introuvable")
    if user["role"] == "technicien" and p.get("technicien_id") not in (user["id"], None):
        raise HTTPException(status_code=403, detail="Ce chantier ne vous est pas assigné")
    if user["role"] == "technicien" and p.get("technicien_id") is None:
        # Self-assign on first measurement
        await db.projects.update_one({"id": pid}, {"$set": {"technicien_id": user["id"]}})

    result = compute_stair(payload)
    doc = {
        "project_id": pid,
        **payload.model_dump(),
        "result": result.model_dump(),
        "validated": False,
        "updated_at": now_utc(),
    }
    existing = await db.measurements.find_one({"project_id": pid})
    if existing:
        await db.measurements.update_one({"project_id": pid}, {"$set": doc})
    else:
        doc["created_at"] = now_utc()
        await db.measurements.insert_one(doc)

    await db.projects.update_one({"id": pid}, {"$set": {"status": "a_verifier", "updated_at": now_utc()}})
    doc.pop("_id", None)
    return doc


@api.post("/projects/{pid}/measurement/preview")
async def preview_measurement(pid: str, payload: MeasurementInput, user=Depends(get_current_user)):
    return compute_stair(payload)


@api.post("/projects/{pid}/measurement/validate")
async def validate_measurement(pid: str, user=Depends(require_roles("admin", "technicien"))):
    m = await db.measurements.find_one({"project_id": pid})
    if not m:
        raise HTTPException(status_code=404, detail="Aucune mesure à valider")
    await db.measurements.update_one({"project_id": pid}, {"$set": {"validated": True, "updated_at": now_utc()}})
    await db.projects.update_one({"id": pid}, {"$set": {"status": "valide", "updated_at": now_utc()}})
    return {"ok": True}


# ------------------------------------------------------------
# Whisper transcription
# ------------------------------------------------------------
@api.post("/transcribe")
async def transcribe(audio: UploadFile = File(...), user=Depends(get_current_user)):
    if not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=503, detail="Clé LLM non configurée")
    try:
        content = await audio.read()
        # Whisper expects a file-like object with a name
        buf = io.BytesIO(content)
        buf.name = audio.filename or "audio.m4a"
        resp = openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=buf,
            language="fr",
            response_format="json",
        )
        return {"text": getattr(resp, "text", "") or ""}
    except Exception as e:
        logger.exception("Whisper error")
        raise HTTPException(status_code=500, detail=f"Erreur transcription: {e}")


# ------------------------------------------------------------
# Exports
# ------------------------------------------------------------
def build_pdf_bytes(project: dict, measurement: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
                            topMargin=18 * mm, bottomMargin=18 * mm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("title", parent=styles["Title"], fontSize=20, textColor=colors.HexColor("#1A1E2A"),
                                 spaceAfter=8)
    h_style = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=13,
                              textColor=colors.HexColor("#8CC63F"), spaceBefore=10, spaceAfter=4)
    body = styles["BodyText"]

    story = []
    story.append(Paragraph("MesureEscalier — Rapport de chantier", title_style))
    story.append(Paragraph(f"Société: {project.get('company_name', '-')}", body))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Client", h_style))
    client_rows = [
        ["Nom", f"{project.get('client_nom','')} {project.get('client_prenom','')}".strip()],
        ["Adresse", project.get("address", "")],
        ["Ville", f"{project.get('postal_code','')} {project.get('city','')}".strip()],
        ["Téléphone", project.get("phone", "") or "-"],
        ["Notes", project.get("notes", "") or "-"],
    ]
    table_style = TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F5F5F7")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#1A1E2A")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E0E0E6")),
    ])
    t = Table(client_rows, colWidths=[40 * mm, 130 * mm])
    t.setStyle(table_style)
    story.append(t)

    if measurement:
        story.append(Paragraph("Mesures terrain", h_style))
        m = measurement
        r = m["result"]
        meas_rows = [
            ["Matériau", m["material"].capitalize()],
            ["Hauteur brute (mm)", str(m["hauteur_brute"])],
            ["Sols finis à zéro", "Oui" if m["sols_finis_zero"] else "Non"],
            ["Réserve bas (mm)", str(m.get("reserve_bas", 0))],
            ["Réserve haut (mm)", str(m.get("reserve_haut", 0))],
            ["Épaisseur dalle (mm)", str(m["epaisseur_dalle"])],
            ["Trémie (mm)", f'{m["tremie_longueur"]} × {m["tremie_largeur"]}'],
            ["Reculement max (mm)", str(m["reculement_max"])],
            ["Remarques", m.get("remarques", "") or "-"],
        ]
        story.append(Table(meas_rows, colWidths=[60 * mm, 110 * mm],
                           style=table_style))

        story.append(Paragraph("Calculs (Loi de Blondel)", h_style))
        res_rows = [
            ["Forme déduite", r["shape"]],
            ["Hauteur effective H (mm)", str(r["true_height"])],
            ["Nombre de marches", str(r["n_steps"])],
            ["Hauteur marche h (mm)", str(r["h"])],
            ["Giron g (mm)", str(r["g"])],
            ["2h+g (mm)", f'{r["blondel_value"]} ({"OK" if r["valid_blondel"] else "Hors plage"})'],
            ["Angle de pente (°)", str(r["slope_angle"])],
            ["Hypoténuse (mm)", str(r["hypotenuse"])],
            ["Reculement requis (mm)", str(r["reculement_needed"])],
        ]
        story.append(Table(res_rows, colWidths=[60 * mm, 110 * mm], style=table_style))

        # SVG-ish sketch using ReportLab Drawing
        story.append(Spacer(1, 10))
        story.append(Paragraph("Schéma d'élévation", h_style))
        story.append(_stair_drawing(r))

        if r.get("notes"):
            story.append(Paragraph("Notes du moteur de calcul", h_style))
            for n in r["notes"]:
                story.append(Paragraph(f"• {n}", body))

    story.append(Spacer(1, 16))
    story.append(Paragraph(
        f"Généré le {now_utc().strftime('%d/%m/%Y %H:%M UTC')} — MesureEscalier",
        ParagraphStyle("foot", parent=body, fontSize=8, textColor=colors.HexColor("#9098A8"))
    ))
    doc.build(story)
    return buf.getvalue()


def _stair_drawing(r: dict) -> Drawing:
    W, H = 170 * mm, 90 * mm
    d = Drawing(W, H)
    d.add(Rect(0, 0, W, H, fillColor=colors.HexColor("#F7F8FC"), strokeColor=colors.HexColor("#E0E0E6")))
    n = max(1, int(r["n_steps"]))
    true_h = r["true_height"]
    reculement = r["reculement_needed"]
    margin = 15 * mm
    avail_w = W - 2 * margin
    avail_h = H - 2 * margin
    scale = min(avail_w / max(reculement, 1), avail_h / max(true_h, 1))
    sw = reculement * scale
    sh = true_h * scale
    x0 = margin
    y0 = margin
    # Hypotenuse
    d.add(Line(x0, y0, x0 + sw, y0 + sh, strokeColor=colors.HexColor("#8CC63F"), strokeWidth=1.4))
    # Steps polyline
    h_px = sh / n
    g_px = sw / max(n - 1, 1)
    pts = [x0, y0]
    cx, cy = x0, y0
    for i in range(n):
        cy += h_px
        pts += [cx, cy]
        cx += g_px
        pts += [cx, cy]
    d.add(Polygon(pts, fillColor=None, strokeColor=colors.HexColor("#1A1E2A"), strokeWidth=1.0))
    # Floor / ceiling lines
    d.add(Line(x0 - 8, y0, x0 + sw + 8, y0, strokeColor=colors.HexColor("#9098A8"), strokeWidth=0.8))
    d.add(Line(x0 - 8, y0 + sh, x0 + sw + 8, y0 + sh, strokeColor=colors.HexColor("#9098A8"),
               strokeWidth=0.8, strokeDashArray=[3, 2]))
    # Labels
    d.add(String(x0 + sw / 2, y0 - 10, f"Reculement {round(reculement)} mm",
                 fontSize=9, fillColor=colors.HexColor("#1A1E2A"), textAnchor="middle"))
    d.add(String(x0 - 10, y0 + sh / 2, f"H {round(true_h)} mm",
                 fontSize=9, fillColor=colors.HexColor("#1A1E2A"), textAnchor="end"))
    d.add(String(x0 + sw / 2, y0 + sh + 6, f"{n} marches · h {r['h']} · g {r['g']}",
                 fontSize=9, fillColor=colors.HexColor("#8CC63F"), textAnchor="middle"))
    return d


def build_dxf_text(project: dict, measurement: dict) -> str:
    """Generate a minimal AutoCAD-readable DXF (ASCII)."""
    r = measurement["result"]
    n = int(r["n_steps"])
    H = float(r["true_height"])
    L = float(r["reculement_needed"])
    h = H / n
    g = L / max(n - 1, 1)

    # Build polyline points: floor → steps zigzag → ceiling
    pts = [(0.0, 0.0)]
    cx, cy = 0.0, 0.0
    for _ in range(n):
        cy += h
        pts.append((cx, cy))
        cx += g
        pts.append((cx, cy))

    out = ["0", "SECTION", "2", "HEADER", "0", "ENDSEC",
           "0", "SECTION", "2", "ENTITIES"]

    # Add LINE entities for each segment
    def add_line(x1, y1, x2, y2, layer="STAIR"):
        out.extend([
            "0", "LINE", "8", layer,
            "10", f"{x1:.3f}", "20", f"{y1:.3f}", "30", "0.0",
            "11", f"{x2:.3f}", "21", f"{y2:.3f}", "31", "0.0",
        ])

    for i in range(len(pts) - 1):
        x1, y1 = pts[i]
        x2, y2 = pts[i + 1]
        add_line(x1, y1, x2, y2, "STAIR_PROFILE")

    # Hypotenuse
    add_line(0, 0, L, H, "HYPOTENUSE")
    # Floor
    add_line(-50, 0, L + 50, 0, "FLOOR")
    # Ceiling (top)
    add_line(-50, H, L + 50, H, "CEILING")
    # Trémie box
    tl = float(measurement.get("tremie_longueur", 0))
    tw = float(measurement.get("tremie_largeur", 0))
    if tl > 0 and tw > 0:
        add_line(L - tl, H, L, H, "TREMIE")
        add_line(L - tl, H + tw, L, H + tw, "TREMIE")
        add_line(L - tl, H, L - tl, H + tw, "TREMIE")
        add_line(L, H, L, H + tw, "TREMIE")

    # TEXT annotations
    def add_text(x, y, text, height=20, layer="LABELS"):
        out.extend([
            "0", "TEXT", "8", layer,
            "10", f"{x:.3f}", "20", f"{y:.3f}", "30", "0.0",
            "40", f"{height:.3f}",
            "1", text,
        ])
    add_text(L / 2, -60, f"Reculement: {round(L)} mm")
    add_text(-80, H / 2, f"H: {round(H)} mm")
    add_text(L / 2, H + 30, f"{n} marches  h={r['h']}  g={r['g']}")
    add_text(0, -120, f"MesureEscalier - {project.get('client_nom','')} {project.get('client_prenom','')}")

    out.extend(["0", "ENDSEC", "0", "EOF"])
    return "\n".join(out)


@api.get("/projects/{pid}/export/pdf")
async def export_pdf(pid: str, user=Depends(get_current_user)):
    q = {"id": pid, **project_visible_to(user)}
    p = await db.projects.find_one(q, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Chantier introuvable")
    m = await db.measurements.find_one({"project_id": pid}, {"_id": 0})
    pdf = build_pdf_bytes(p, m)
    filename = f"chantier_{p.get('client_nom','export').lower()}.pdf"
    return StreamingResponse(io.BytesIO(pdf), media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@api.get("/projects/{pid}/export/dxf")
async def export_dxf(pid: str, user=Depends(get_current_user)):
    q = {"id": pid, **project_visible_to(user)}
    p = await db.projects.find_one(q, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Chantier introuvable")
    m = await db.measurements.find_one({"project_id": pid}, {"_id": 0})
    if not m:
        raise HTTPException(status_code=400, detail="Aucune mesure disponible pour DXF")
    dxf = build_dxf_text(p, m)
    filename = f"chantier_{p.get('client_nom','export').lower()}.dxf"
    return StreamingResponse(io.BytesIO(dxf.encode()), media_type="application/dxf",
                             headers={"Content-Disposition": f'attachment; filename="{filename}"'})


# ------------------------------------------------------------
# Future-proof integration endpoint for sister app "MesureGardeCorps"
# ------------------------------------------------------------
@api.get("/integration/sites/{pid}")
async def integration_site(pid: str, user=Depends(get_current_user)):
    p = await db.projects.find_one({"id": pid}, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Chantier introuvable")
    m = await db.measurements.find_one({"project_id": pid}, {"_id": 0})
    payload = {
        "site_id": pid,
        "client": {
            "nom": p.get("client_nom"),
            "prenom": p.get("client_prenom"),
            "address": p.get("address"),
            "city": p.get("city"),
            "postal_code": p.get("postal_code"),
        },
        "structure": None,
    }
    if m:
        r = m["result"]
        payload["structure"] = {
            "material": m["material"],
            "true_height_mm": r["true_height"],
            "reculement_mm": r["reculement_needed"],
            "slope_angle_deg": r["slope_angle"],
            "hypotenuse_mm": r["hypotenuse"],
            "n_steps": r["n_steps"],
            "step_h_mm": r["h"],
            "step_g_mm": r["g"],
            "shape": r["shape"],
            "tremie": {
                "longueur_mm": m["tremie_longueur"],
                "largeur_mm": m["tremie_largeur"],
            },
        }
    return payload


@api.get("/")
async def root():
    return {"app": "MesureEscalier", "version": "1.0", "status": "ok"}


# ------------------------------------------------------------
# App wire-up + seed
# ------------------------------------------------------------
app.include_router(api)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


async def seed_demo_users():
    demo = [
        {
            "email": "admin@demo.fr", "full_name": "Marie Dubois",
            "company_name": "Menuiserie Demo SARL", "role": "admin", "password": "Demo1234!",
        },
        {
            "email": "marc@mesureescalier.com", "full_name": "Marc Commercial",
            "company_name": "Menuiserie Demo SARL", "role": "commercial", "password": "Demo1234!",
        },
        {
            "email": "sophie@mesureescaliee.com", "full_name": "Sophie Technicienne",
            "company_name": "Menuiserie Demo SARL", "role": "technicien", "password": "Demo1234!",
        },
    ]
    for u in demo:
        existing = await db.users.find_one({"email": u["email"]})
        if existing:
            continue
        await db.users.insert_one({
            "id": str(uuid.uuid4()),
            "email": u["email"],
            "full_name": u["full_name"],
            "company_name": u["company_name"],
            "role": u["role"],
            "password_hash": hash_password(u["password"]),
            "created_at": now_utc(),
        })
        logger.info("Seeded demo user %s (%s)", u["email"], u["role"])


@app.on_event("startup")
async def on_startup():
    await db.users.create_index("email", unique=True)
    await db.projects.create_index("created_at")
    await db.measurements.create_index("project_id", unique=True)
    await seed_demo_users()


@app.on_event("shutdown")
async def on_shutdown():
    client.close()
