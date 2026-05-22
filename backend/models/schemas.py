"""All Pydantic request / response schemas."""
from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field

from core.security import now_utc

Role = Literal["admin", "technicien"]
ProjectStatus = Literal[
    "brouillon", "a_mesurer", "a_verifier", "valide", "en_fabrication", "termine"
]


# ---------------------- Users ----------------------
class UserPublic(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: Role
    company_name: Optional[str] = None
    solo_mode: bool = False
    created_at: datetime


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    company_name: Optional[str] = None
    solo_mode: Optional[bool] = None


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
    role: Literal["technicien"] = "technicien"


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


# ---------------------- Measurements ----------------------
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
    # Optional ceiling height under trémie passage (mm) — used for échappée
    hauteur_sous_plafond_tremie: Optional[float] = None


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
    is_tournant: bool = False
    ligne_foulee_note: Optional[str] = None
    echappee: Optional[float] = None
    echappee_critique: bool = False
    blondel_value: float
    valid_blondel: bool
    notes: List[str] = []


class MeasurementFull(MeasurementInput):
    project_id: str
    result: MeasurementResult
    validated: bool = False
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)
