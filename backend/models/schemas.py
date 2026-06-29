"""All Pydantic request / response schemas."""
from __future__ import annotations

import re
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from core.security import now_utc

Role = Literal["admin", "technicien"]
ProjectStatus = Literal[
    "brouillon", "a_mesurer", "a_verifier", "valide", "en_fabrication", "termine"
]


# ── Password policy (P3 hardening) ──────────────────────────────────────
# Require 8+ chars with at least 1 letter AND 1 digit.
# Existing demo password `Demo1234!` (9 chars) satisfies this.
_PWD_MIN_LEN = 8
_PWD_LETTER_RE = re.compile(r"[A-Za-z]")
_PWD_DIGIT_RE = re.compile(r"\d")


def _validate_password_strength(v: str) -> str:
    if not isinstance(v, str) or len(v) < _PWD_MIN_LEN:
        raise ValueError(
            f"Le mot de passe doit contenir au moins {_PWD_MIN_LEN} caractères."
        )
    if not _PWD_LETTER_RE.search(v) or not _PWD_DIGIT_RE.search(v):
        raise ValueError(
            "Le mot de passe doit contenir au moins une lettre et un chiffre."
        )
    return v


# ---------------------- Users ----------------------
class UserPublic(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: Role
    company_id: Optional[str] = None
    company_name: Optional[str] = None
    solo_mode: bool = False
    company_logo_base64: Optional[str] = None  # data URI or raw base64
    created_at: datetime
    # Subscription / trial state
    trial_start_date: Optional[datetime] = None
    trial_days_remaining: int = 0
    is_trial_active: bool = False
    subscription_active: bool = False
    is_locked: bool = False


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    company_name: Optional[str] = None
    solo_mode: Optional[bool] = None
    company_logo_base64: Optional[str] = None  # "" or None to clear, base64 string to set


class RegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str = Field(min_length=_PWD_MIN_LEN)
    company_name: Optional[str] = None

    @field_validator("password")
    @classmethod
    def _check_password(cls, v: str) -> str:
        return _validate_password_strength(v)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    token: str
    user: UserPublic


class InviteUserRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str = Field(min_length=_PWD_MIN_LEN)
    role: Literal["technicien"] = "technicien"

    @field_validator("password")
    @classmethod
    def _check_password(cls, v: str) -> str:
        return _validate_password_strength(v)


# ---------------------- Projects ----------------------
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


# ---------------------- Project Photos ----------------------
class PhotoCreate(BaseModel):
    base64: str  # raw base64 (no data URI prefix)
    caption: Optional[str] = ""


class PhotoUpdate(BaseModel):
    caption: Optional[str] = None


class ProjectPhoto(BaseModel):
    id: str
    base64: str
    caption: str = ""
    created_at: datetime


# ---------------------- Multi-stair v2 (Niveaux > Tronçons) ----------------------
TronconType = Literal["droit", "palier", "quart_bas", "quart_haut"]


class Troncon(BaseModel):
    id: str
    type: TronconType
    # Longueur horizontale du tronçon en mm.
    # - droit/quart_bas/quart_haut : reculement utile (marches enchaînées)
    # - palier : longueur du palier (aucune marche, mais consomme du reculement)
    longueur_mm: float
    largeur_mm: float = 900
    order: int = 0


class TronconCreate(BaseModel):
    type: TronconType
    longueur_mm: float
    largeur_mm: float = 900


class TronconUpdate(BaseModel):
    type: Optional[TronconType] = None
    longueur_mm: Optional[float] = None
    largeur_mm: Optional[float] = None
    order: Optional[int] = None


class Niveau(BaseModel):
    id: str
    label: str = "Niveau"       # display label (auto-derived from floor_index server-side)
    floor_index: int = 0        # ⬅️ -3..+7 (0=RDC, 1=R+1, -1=Sous-sol)
    is_ghost: bool = False      # ⬅️ "Pas d'escalier ici" — préserve la continuité
    hauteur_mm: float            # hauteur brute du niveau (mm) = Hauteur Totale (HT)
    sol_fini: bool = True         # niveau bas fini ; si False, on déduit reserve_mm
    reserve_mm: float = 0
    # Logique HT / ED / HSP (mai 2025) — saisie liée, l'un des 3 est auto-calculé
    epaisseur_dalle_mm: float = 0        # ED : épaisseur de la dalle haute (mm)
    hauteur_sous_plafond_mm: float = 0   # HSP : HT - ED (mm) — calculé ou saisi
    entry_mode: Literal["hauteur", "hsp"] = "hauteur"   # ⬅️ champ saisi par l'utilisateur ; l'autre est verrouillé
    troncons: List[Troncon] = []
    order: int = 0


class NiveauCreate(BaseModel):
    label: str = ""               # vide → auto-dérivé du floor_index ("RDC", "R+1", …)
    floor_index: int = 0          # niveau strict -3..+7
    is_ghost: bool = False        # "Pas d'escalier ici"
    hauteur_mm: float
    sol_fini: bool = True
    reserve_mm: float = 0
    epaisseur_dalle_mm: float = 0
    hauteur_sous_plafond_mm: float = 0
    entry_mode: Literal["hauteur", "hsp"] = "hauteur"


class NiveauUpdate(BaseModel):
    label: Optional[str] = None
    floor_index: Optional[int] = None
    is_ghost: Optional[bool] = None
    hauteur_mm: Optional[float] = None
    sol_fini: Optional[bool] = None
    reserve_mm: Optional[float] = None
    epaisseur_dalle_mm: Optional[float] = None
    hauteur_sous_plafond_mm: Optional[float] = None
    entry_mode: Optional[Literal["hauteur", "hsp"]] = None
    order: Optional[int] = None


# 4 formes officielles + 'tournant' conservé en alias pour rétrocompat V1
StairShape = Literal["droit", "quart_tournant", "demi_tournant", "helicoidal", "tournant"]


class Stair(BaseModel):
    id: str
    name: str = "Escalier Principal"
    shape: StairShape = "tournant"          # ⬅️ NEW : DROIT (simplifié) ou TOURNANT (multi-niveaux)
    niveaux: List[Niveau] = []
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class StairCreate(BaseModel):
    name: str = "Escalier Principal"
    shape: StairShape = "tournant"          # ⬅️ NEW


class StairUpdate(BaseModel):
    name: Optional[str] = None
    shape: Optional[StairShape] = None      # ⬅️ NEW


# ---------------------- Measurements ----------------------
class MeasurementInput(BaseModel):
    # Phase 1 addition: titre libre de l'élément mesuré (ex. "Escalier Principal", "Escalier Cave")
    element_title: Optional[str] = "Escalier"
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
    # Optional ceiling height under trémie passage (mm) — used for échappée
    hauteur_sous_plafond_tremie: Optional[float] = None
    # Phase 2 — Trajectoire (interactive design center)
    # Si vide → détection automatique selon reculement disponible.
    forme_choisie: Optional[Literal["droit", "quart_bas", "quart_haut", "double_quart", "helicoidal"]] = None
    # Largeur utile de la volée (mm), défaut 900mm (norme française).
    largeur_volee: Optional[float] = 900
    # Jour d'escalier — espace vide entre 2 volées en tournant (mm), défaut 100mm.
    jour_escalier: Optional[float] = 100


class MeasurementResult(BaseModel):
    true_height: float
    n_steps: int
    h: float
    g: float
    slope_angle: float
    hypotenuse: float            # = limon_length (kept for backward-compat)
    limon_length: float          # Longueur du limon (mm) = hypoténuse exacte
    reculement_needed: float
    shape: str
    # Phase 2: Trajectoire — clé machine-readable de la forme
    shape_key: Literal["droit", "quart_bas", "quart_haut", "double_quart", "helicoidal"] = "droit"
    is_tournant: bool = False
    ligne_foulee_note: Optional[str] = None
    echappee: Optional[float] = None
    echappee_critique: bool = False
    blondel_value: float
    valid_blondel: bool
    notes: List[str] = []
    # Phase 2 — Géométrie de la trajectoire (echo pour SVG plan)
    largeur_volee: float = 900
    jour_escalier: float = 100


class MeasurementFull(MeasurementInput):
    project_id: str
    result: MeasurementResult
    validated: bool = False
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)
