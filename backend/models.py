"""Modèles Pydantic — schéma de validation des entrées/sorties API."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from db import VALID_WALL_TYPES


# --- Users ---------------------------------------------------------------
class UserPublic(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: str
    company_id: str
    status: str = "active"  # pending_verification | active | suspended
    email_verified_at: Optional[str] = None


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "technician"
    company_id: str = "default"


class RegisterMasterAdmin(BaseModel):
    """Inscription Master Admin uniquement (création d'une nouvelle société).

    Le rôle est forcé à `admin` côté serveur. Le statut initial est
    `pending_verification` et un email de double opt-in est envoyé.
    """
    name: str
    email: EmailStr
    password: str
    company_name: Optional[str] = None


class InvitationCreate(BaseModel):
    """Invitation envoyée par le Master Admin à un Commercial / Technicien."""
    name: str
    email: EmailStr
    role: str  # "commercial" | "technician"


class InvitationAccept(BaseModel):
    """Acceptation d'invitation : définit mot de passe + valide l'email."""
    password: str
    name: Optional[str] = None


class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class RegisterResponse(BaseModel):
    """Réponse register / invite : pas de token tant que l'email n'est pas vérifié."""
    user: UserPublic
    verification_link: Optional[str] = None  # MOCK MVP : lien renvoyé pour démo
    message: str


class PushTokenIn(BaseModel):
    push_token: Optional[str] = None


# --- Chantiers -----------------------------------------------------------
class ChantierCreate(BaseModel):
    client_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    address: str
    postal_code: Optional[str] = None
    city: Optional[str] = None
    status: str = "devis_a_faire"
    assigned_to: Optional[str] = None
    appointment_at: Optional[str] = None
    notes: Optional[str] = None
    site_photos: Optional[List[dict]] = None


class ChantierUpdate(BaseModel):
    client_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    address: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    appointment_at: Optional[str] = None
    notes: Optional[str] = None
    site_photos: Optional[List[dict]] = None


class Chantier(BaseModel):
    id: str
    client_name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    address: str
    postal_code: Optional[str] = None
    city: Optional[str] = None
    status: str
    created_by: str
    assigned_to: Optional[str] = None
    appointment_at: Optional[str] = None
    notes: Optional[str] = None
    company_id: str = "default"
    client_signature: Optional[str] = None
    signed_at: Optional[str] = None
    created_at: str
    site_photos: List[dict] = Field(default_factory=list)


class SignatureIn(BaseModel):
    signature: str  # base64 data URL ou raw base64


# --- Company -------------------------------------------------------------
class CompanyProfile(BaseModel):
    company_id: str
    name: Optional[str] = None
    artisan_mode: bool = False
    subscription_status: str = "trial"  # trial | active | suspended
    subscription_expires_at: Optional[str] = None
    # --- Plan & Freemium (anti-fraud) ---
    plan: str = "trial"  # free | trial | pro
    chantiers_lifetime_count: int = 0
    # --- Cancellation (graceful termination) ---
    cancel_at_period_end: bool = False
    cancelled_at: Optional[str] = None
    # --- Beta Mode (no payment required) ---
    # 🚧 Quand True, le frontend doit masquer paywall / trial / freemium
    # et afficher la bannière verte "Beta Gratuite".
    beta_mode: bool = False


class CompanyProfileUpdate(BaseModel):
    name: Optional[str] = None
    artisan_mode: Optional[bool] = None
    # Les champs subscription_*, plan, cancel_* sont updatés uniquement
    # via /platform/... ou /company/subscription/{cancel|reactivate}.


# --- Mesures -------------------------------------------------------------
class MesureCreate(BaseModel):
    chantier_id: str
    block_type: str
    label: str
    # Legacy (back-compat)
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
    # Baie brute (Step 2)
    bay_height: Optional[float] = None
    bay_width: Optional[float] = None
    bay_diagonal: Optional[float] = None
    bay_diagonal_1: Optional[float] = None
    bay_diagonal_2: Optional[float] = None
    diag_1_verified: Optional[bool] = None
    diag_2_verified: Optional[bool] = None
    floor_reserve: Optional[float] = None
    # Conception maçonnerie & isolation (Step 3)
    bloc_thickness: Optional[float] = None
    wall_type: Optional[str] = None
    insulation_thickness: Optional[float] = None
    finish_outer: Optional[float] = None
    finish_inner: Optional[float] = None
    options: dict = Field(default_factory=dict)
    photo_url: Optional[str] = None
    renovation_mode: Optional[bool] = None

    @field_validator("wall_type")
    @classmethod
    def _validate_wall_type(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if v not in VALID_WALL_TYPES:
            raise ValueError(
                f"wall_type must be one of {sorted(VALID_WALL_TYPES)}"
            )
        return v


class Mesure(MesureCreate):
    id: str
    created_at: str
    alerts: List[str] = Field(default_factory=list)
    slope_angle_deg: Optional[float] = None


# --- Feedback ------------------------------------------------------------
class FeedbackCreate(BaseModel):
    page_context: str
    user_comment: str
    screenshot_data: Optional[str] = None
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
