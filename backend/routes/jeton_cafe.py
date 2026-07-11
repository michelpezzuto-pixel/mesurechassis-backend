"""☕ Système « Jeton Café » — Priorité 4 (juillet 2026).

Levier d'acquisition terrain via les stations-service partenaires :
    1. QR code affiché à la station → inscription avec `station_id` dans l'URL
       → le compte est tagué `campaign_station_id`.
    2. À chaque création d'ouverture, l'artisan tagué gagne un jeton café
       (pop-up « Vous avez gagné un café ! »).
    3. À la station, le POMPISTE valide le jeton sur le téléphone de
       l'artisan en tapant le code PIN à 4 chiffres de sa station.
    4. Le propriétaire (Michel) suit les cafés liquidés par station en temps
       réel (objectif : 50/mois/station) et peut déclencher une relance
       email ciblée 10 jours avant la fin du mois.

Règles métier :
    - Max 1 jeton gagné par jour et par artisan.
    - Un seul jeton actif (non consommé) à la fois.
    - Validité : 30 jours puis expiration automatique (lazy).
    - Anti-fraude PIN : 5 tentatives erronées → jeton verrouillé 10 min.
"""
from __future__ import annotations

import calendar
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from db import db
from deps import require_active_subscription, require_platform_owner

logger = logging.getLogger("mesurechassis.jeton_cafe")
router = APIRouter()

JETON_VALIDITY_DAYS = 15
MAX_PIN_ATTEMPTS = 5
PIN_LOCK_MINUTES = 10
DEFAULT_MONTHLY_OBJECTIVE = 50


# ════════════════════════════════════════════════════════════════════════
# Modèles
# ════════════════════════════════════════════════════════════════════════
class StationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    city: str = ""
    pin: str = Field(min_length=4, max_length=4)
    monthly_objective: int = DEFAULT_MONTHLY_OBJECTIVE
    # 🆕 Rattachement à un réseau (ex: "total-be", "shell-be"…). Facultatif.
    network_id: Optional[str] = None
    address: str = ""
    contact_name: str = ""
    contact_phone: str = ""
    contact_email: str = ""
    coffee_price: float = 0.0  # € TTC facturé au propriétaire


class StationUpdate(BaseModel):
    name: Optional[str] = None
    city: Optional[str] = None
    pin: Optional[str] = None
    monthly_objective: Optional[int] = None
    active: Optional[bool] = None
    network_id: Optional[str] = None
    address: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    coffee_price: Optional[float] = None


class NetworkCreate(BaseModel):
    id: str = Field(min_length=2, max_length=40)  # ex: "total-be"
    name: str = Field(min_length=2, max_length=80)  # ex: "Total"
    country: str = "BE"
    logo_url: str = ""
    active: bool = True


class ConsumePayload(BaseModel):
    pin: str


class EarnPayload(BaseModel):
    mesure_id: Optional[str] = None


# ════════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════════
def _now() -> datetime:
    return datetime.now(timezone.utc)


def _month_bounds(dt: datetime) -> tuple[str, str]:
    """Retourne (iso_start, iso_end) du mois de `dt` (UTC)."""
    start = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_day = calendar.monthrange(dt.year, dt.month)[1]
    end = dt.replace(day=last_day, hour=23, minute=59, second=59, microsecond=0)
    return start.isoformat(), end.isoformat()


def _relance_window_open(dt: datetime) -> bool:
    """True si on est à ≤ 10 jours de la fin du mois (fenêtre de relance)."""
    last_day = calendar.monthrange(dt.year, dt.month)[1]
    return (last_day - dt.day) <= 10


async def _expire_stale_jetons(user_id: Optional[str] = None) -> None:
    """Marque comme expirés les jetons 'earned' dont expires_at est passé."""
    q: dict = {"status": "earned", "expires_at": {"$lt": _now().isoformat()}}
    if user_id:
        q["user_id"] = user_id
    await db.cafe_jetons.update_many(
        q, {"$set": {"status": "expired", "expired_at": _now().isoformat()}}
    )


def _jeton_public(doc: dict) -> dict:
    return {
        "id": doc["id"],
        "station_id": doc.get("station_id"),
        "status": doc.get("status"),
        "earned_at": doc.get("earned_at"),
        "consumed_at": doc.get("consumed_at"),
        "expires_at": doc.get("expires_at"),
    }


def _station_public(doc: dict, include_pin: bool = False) -> dict:
    out = {
        "id": doc["id"],
        "name": doc.get("name"),
        "city": doc.get("city", ""),
        "address": doc.get("address", ""),
        "active": doc.get("active", True),
        "monthly_objective": doc.get("monthly_objective", DEFAULT_MONTHLY_OBJECTIVE),
        "network_id": doc.get("network_id"),
    }
    if include_pin:
        out["pin"] = doc.get("pin", "")
        out["created_at"] = doc.get("created_at")
        out["contact_name"] = doc.get("contact_name", "")
        out["contact_phone"] = doc.get("contact_phone", "")
        out["contact_email"] = doc.get("contact_email", "")
        out["coffee_price"] = doc.get("coffee_price", 0.0)
    return out


def _network_public(doc: dict) -> dict:
    return {
        "id": doc["id"],
        "name": doc.get("name"),
        "country": doc.get("country", "BE"),
        "logo_url": doc.get("logo_url", ""),
        "active": doc.get("active", True),
    }


async def _station_month_stats(station_id: str, dt: datetime) -> dict:
    start, end = _month_bounds(dt)
    consumed = await db.cafe_jetons.count_documents(
        {
            "station_id": station_id,
            "status": "consumed",
            "consumed_at": {"$gte": start, "$lte": end},
        }
    )
    earned = await db.cafe_jetons.count_documents(
        {"station_id": station_id, "earned_at": {"$gte": start, "$lte": end}}
    )
    return {"consumed": consumed, "earned": earned}


# ════════════════════════════════════════════════════════════════════════
# Endpoints PUBLICS (badge inscription via QR)
# ════════════════════════════════════════════════════════════════════════
@router.get("/cafe/stations/{station_id}/public")
async def get_station_public(station_id: str):
    """Infos publiques d'une station (affichées à l'inscription via QR)."""
    doc = await db.cafe_stations.find_one({"id": station_id}, {"_id": 0})
    if not doc or not doc.get("active", True):
        raise HTTPException(404, "Station introuvable ou inactive")
    return _station_public(doc)


# ════════════════════════════════════════════════════════════════════════
# Endpoints UTILISATEUR (artisan tagué campagne)
# ════════════════════════════════════════════════════════════════════════
@router.get("/cafe/me")
async def my_cafe_status(user=Depends(require_active_subscription)):
    """Statut jeton café de l'utilisateur : station liée, jeton actif, historique."""
    user_id = user.get("user_id") or user.get("id") or ""
    user_doc = await db.users.find_one(
        {"id": user_id},
        {"_id": 0, "campaign_station_id": 1, "campaign_network_id": 1},
    )
    station_id = (user_doc or {}).get("campaign_station_id")
    network_id = (user_doc or {}).get("campaign_network_id")
    if not station_id and not network_id:
        return {
            "station": None,
            "network": None,
            "network_stations": [],
            "active_jeton": None,
            "jetons": [],
        }

    station = None
    if station_id:
        station = await db.cafe_stations.find_one({"id": station_id}, {"_id": 0})

    # 🆕 Réseau + stations participantes (pour les campagnes multi-stations)
    network_doc = None
    network_stations: List[dict] = []
    if network_id:
        network_doc = await db.cafe_networks.find_one({"id": network_id}, {"_id": 0})
        if network_doc and network_doc.get("active", True):
            docs = (
                await db.cafe_stations.find(
                    {"network_id": network_id, "active": True}, {"_id": 0}
                )
                .sort("name", 1)
                .to_list(200)
            )
            network_stations = [_station_public(d) for d in docs]

    await _expire_stale_jetons(user_id)

    jetons = (
        await db.cafe_jetons.find({"user_id": user_id}, {"_id": 0})
        .sort("earned_at", -1)
        .to_list(30)
    )
    active = next((j for j in jetons if j.get("status") == "earned"), None)
    consumed_total = sum(1 for j in jetons if j.get("status") == "consumed")
    return {
        "station": _station_public(station) if station else None,
        "network": _network_public(network_doc) if network_doc else None,
        "network_stations": network_stations,
        "active_jeton": _jeton_public(active) if active else None,
        "jetons": [_jeton_public(j) for j in jetons],
        "consumed_total": consumed_total,
    }


@router.post("/cafe/earn")
async def earn_jeton(payload: EarnPayload, user=Depends(require_active_subscription)):
    """Tente de gagner un jeton (appelé après la création d'une ouverture).

    Renvoie {eligible: bool, jeton?, station?, reason?}. Jamais d'erreur 4xx
    métier : le frontend appelle en fire-and-forget après chaque création.
    """
    user_id = user.get("user_id") or user.get("id") or ""
    user_doc = await db.users.find_one(
        {"id": user_id},
        {
            "_id": 0,
            "campaign_station_id": 1,
            "campaign_network_id": 1,
            "name": 1,
            "email": 1,
        },
    )
    station_id = (user_doc or {}).get("campaign_station_id")
    network_id = (user_doc or {}).get("campaign_network_id")

    if not station_id and not network_id:
        return {"eligible": False, "reason": "no_campaign"}

    # 🆕 Mode réseau : on vérifie que le réseau est actif ET qu'au moins une
    # station participante existe (sinon le café ne pourrait pas être consommé).
    network_doc = None
    if network_id:
        network_doc = await db.cafe_networks.find_one(
            {"id": network_id, "active": True}, {"_id": 0}
        )
        if not network_doc:
            return {"eligible": False, "reason": "network_inactive"}
        network_stations_count = await db.cafe_stations.count_documents(
            {"network_id": network_id, "active": True}
        )
        if network_stations_count == 0:
            return {"eligible": False, "reason": "network_no_stations"}

    # Mode station directe (legacy) : on vérifie la station.
    station = None
    if station_id:
        station = await db.cafe_stations.find_one({"id": station_id}, {"_id": 0})
        if not station or not station.get("active", True):
            # Fallback réseau si dispo, sinon inactif
            if not network_doc:
                return {"eligible": False, "reason": "station_inactive"}
            station = None

    await _expire_stale_jetons(user_id)

    # Un seul jeton actif à la fois → on renvoie l'existant
    existing = await db.cafe_jetons.find_one(
        {"user_id": user_id, "status": "earned"}, {"_id": 0}
    )
    if existing:
        return {
            "eligible": False,
            "reason": "active_jeton_exists",
            "active_jeton": _jeton_public(existing),
            "station": _station_public(station) if station else None,
            "network": _network_public(network_doc) if network_doc else None,
        }

    # Max 1 jeton gagné par jour (UTC)
    day_start = _now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    today_count = await db.cafe_jetons.count_documents(
        {"user_id": user_id, "earned_at": {"$gte": day_start}}
    )
    if today_count >= 1:
        return {"eligible": False, "reason": "daily_limit"}

    now_iso = _now().isoformat()
    jeton = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "user_name": (user_doc or {}).get("name", ""),
        "user_email": (user_doc or {}).get("email", ""),
        "company_id": user.get("company_id", ""),
        "station_id": station_id,  # peut être None en mode réseau pur
        "network_id": network_id,  # 🆕
        "mesure_id": payload.mesure_id,
        "status": "earned",
        "earned_at": now_iso,
        "consumed_at": None,
        "consumed_station_id": None,  # 🆕 rempli à la consommation
        "expires_at": (_now() + timedelta(days=JETON_VALIDITY_DAYS)).isoformat(),
        "pin_attempts": 0,
        "locked_until": None,
    }
    await db.cafe_jetons.insert_one(jeton)
    logger.info(
        "☕ Jeton gagné user=%s station=%s network=%s",
        user_id,
        station_id,
        network_id,
    )
    return {
        "eligible": True,
        "jeton": _jeton_public(jeton),
        "station": _station_public(station) if station else None,
        "network": _network_public(network_doc) if network_doc else None,
    }


@router.post("/cafe/jetons/{jeton_id}/consume")
async def consume_jeton(
    jeton_id: str,
    payload: ConsumePayload,
    user=Depends(require_active_subscription),
):
    """Validation POMPISTE : consomme le jeton si le PIN station est correct.

    Anti-fraude : 5 PIN erronés → jeton verrouillé 10 minutes (empêche
    l'artisan de deviner le code et de s'auto-valider).
    """
    user_id = user.get("user_id") or user.get("id") or ""
    jeton = await db.cafe_jetons.find_one({"id": jeton_id, "user_id": user_id})
    if not jeton:
        raise HTTPException(404, "Jeton introuvable")
    if jeton.get("status") == "consumed":
        raise HTTPException(400, "Ce jeton a déjà été utilisé")
    if jeton.get("status") == "expired" or (
        jeton.get("expires_at") and jeton["expires_at"] < _now().isoformat()
    ):
        await db.cafe_jetons.update_one(
            {"id": jeton_id}, {"$set": {"status": "expired"}}
        )
        raise HTTPException(400, "Ce jeton a expiré (validité 30 jours)")

    # Verrouillage anti brute-force
    locked_until = jeton.get("locked_until")
    if locked_until and locked_until > _now().isoformat():
        raise HTTPException(
            429,
            "Trop de tentatives. Jeton verrouillé quelques minutes — "
            "demandez au pompiste de vérifier le code de sa station.",
        )

    # 🆕 Mode réseau : accepter le PIN de N'IMPORTE quelle station active
    # du réseau du jeton (ex: café gagné via Total Wavre, consommé chez
    # Total Louvain-la-Neuve). Fallback vers le mode station legacy.
    station = None
    pin_clean = (payload.pin or "").strip()
    jeton_network_id = jeton.get("network_id")

    if jeton_network_id:
        station = await db.cafe_stations.find_one(
            {
                "network_id": jeton_network_id,
                "pin": pin_clean,
                "active": True,
            }
        )
    if not station and jeton.get("station_id"):
        # Mode station directe (legacy)
        candidate = await db.cafe_stations.find_one({"id": jeton["station_id"]})
        if candidate and pin_clean == str(candidate.get("pin", "")):
            station = candidate

    if not station:
        attempts = int(jeton.get("pin_attempts") or 0) + 1
        update: dict = {"pin_attempts": attempts}
        if attempts >= MAX_PIN_ATTEMPTS:
            update["locked_until"] = (
                _now() + timedelta(minutes=PIN_LOCK_MINUTES)
            ).isoformat()
            update["pin_attempts"] = 0
        await db.cafe_jetons.update_one({"id": jeton_id}, {"$set": update})
        remaining = max(0, MAX_PIN_ATTEMPTS - attempts)
        raise HTTPException(
            400,
            f"Code PIN incorrect ({remaining} essai(s) restant(s))"
            if remaining
            else "Code PIN incorrect — jeton verrouillé 10 minutes.",
        )

    now_iso = _now().isoformat()
    await db.cafe_jetons.update_one(
        {"id": jeton_id},
        {
            "$set": {
                "status": "consumed",
                "consumed_at": now_iso,
                "consumed_station_id": station["id"],  # 🆕
                "pin_attempts": 0,
            }
        },
    )
    logger.info(
        "☕✅ Jeton consommé jeton=%s station=%s network=%s",
        jeton_id,
        station["id"],
        jeton_network_id,
    )
    return {
        "ok": True,
        "consumed_at": now_iso,
        "station_name": station.get("name", ""),
    }


# ════════════════════════════════════════════════════════════════════════
# Endpoints PROPRIÉTAIRE (Michel) — pilotage des stations
# ════════════════════════════════════════════════════════════════════════
@router.post("/cafe/stations")
async def create_station(
    payload: StationCreate, user=Depends(require_platform_owner)
):
    if not payload.pin.isdigit():
        raise HTTPException(400, "Le PIN doit être composé de 4 chiffres")
    # Vérifier que le network existe (si fourni)
    if payload.network_id:
        net = await db.cafe_networks.find_one({"id": payload.network_id})
        if not net:
            raise HTTPException(404, f"Réseau '{payload.network_id}' introuvable")
    doc = {
        "id": str(uuid.uuid4()),
        "name": payload.name.strip(),
        "city": payload.city.strip(),
        "address": payload.address.strip(),
        "pin": payload.pin,
        "monthly_objective": max(1, payload.monthly_objective),
        "network_id": payload.network_id,
        "contact_name": payload.contact_name.strip(),
        "contact_phone": payload.contact_phone.strip(),
        "contact_email": payload.contact_email.strip(),
        "coffee_price": max(0.0, float(payload.coffee_price or 0.0)),
        "active": True,
        "created_at": _now().isoformat(),
        "created_by": user.get("user_id") or user.get("id") or "",
    }
    await db.cafe_stations.insert_one(doc)
    doc.pop("_id", None)
    return _station_public(doc, include_pin=True)


# ════════════════════════════════════════════════════════════════════════
# Endpoints RÉSEAU (« Total », « Shell », etc.) — Priorité 5 (juillet 2026)
# ════════════════════════════════════════════════════════════════════════
@router.post("/cafe/networks")
async def create_network(payload: NetworkCreate, user=Depends(require_platform_owner)):
    """Crée un réseau (ex: Total-BE) — un menuisier tagué sur ce réseau peut
    consommer son café dans N'IMPORTE quelle station participante."""
    existing = await db.cafe_networks.find_one({"id": payload.id})
    if existing:
        raise HTTPException(400, f"Réseau '{payload.id}' existe déjà")
    doc = {
        "id": payload.id,
        "name": payload.name,
        "country": payload.country,
        "logo_url": payload.logo_url,
        "active": payload.active,
        "created_at": _now().isoformat(),
        "created_by": user.get("user_id") or user.get("id") or "",
    }
    await db.cafe_networks.insert_one(doc)
    doc.pop("_id", None)
    return _network_public(doc)


@router.get("/cafe/networks")
async def list_networks(user=Depends(require_platform_owner)):
    """Liste tous les réseaux + stats (nb stations, nb utilisateurs, mois)."""
    docs = await db.cafe_networks.find({}, {"_id": 0}).to_list(50)
    out = []
    now = _now()
    start, end = _month_bounds(now)
    for n in docs:
        stations_count = await db.cafe_stations.count_documents(
            {"network_id": n["id"], "active": True}
        )
        users_count = await db.users.count_documents(
            {"campaign_network_id": n["id"]}
        )
        consumed_month = await db.cafe_jetons.count_documents(
            {
                "network_id": n["id"],
                "status": "consumed",
                "consumed_at": {"$gte": start, "$lte": end},
            }
        )
        out.append(
            {
                **_network_public(n),
                "stations_count": stations_count,
                "users_count": users_count,
                "consumed_this_month": consumed_month,
            }
        )
    return {"networks": out}


@router.get("/cafe/networks/{network_id}/public")
async def get_network_public(network_id: str):
    """Infos publiques d'un réseau + liste des stations participantes."""
    n = await db.cafe_networks.find_one({"id": network_id}, {"_id": 0})
    if not n or not n.get("active", True):
        raise HTTPException(404, "Réseau introuvable ou inactif")
    stations = (
        await db.cafe_stations.find(
            {"network_id": network_id, "active": True}, {"_id": 0}
        )
        .sort("name", 1)
        .to_list(200)
    )
    return {
        **_network_public(n),
        "stations": [_station_public(s) for s in stations],
    }


@router.post("/cafe/networks/{network_id}/backfill-users")
async def backfill_network_users(
    network_id: str, user=Depends(require_platform_owner)
):
    """Tag rétroactif : associe tous les utilisateurs existants (sans
    campagne) à ce réseau. Utile pour ouvrir la campagne aux comptes créés
    avant l'activation."""
    n = await db.cafe_networks.find_one({"id": network_id})
    if not n:
        raise HTTPException(404, "Réseau introuvable")
    r = await db.users.update_many(
        {
            "campaign_network_id": {"$in": [None, ""]},
            "campaign_station_id": {"$in": [None, ""]},
            "status": {"$ne": "deleted"},
        },
        {"$set": {"campaign_network_id": network_id}},
    )
    logger.info(
        "🔄 Backfill réseau=%s users=%s (auteur=%s)",
        network_id,
        r.modified_count,
        user.get("email"),
    )
    return {"ok": True, "network_id": network_id, "tagged_users": r.modified_count}


@router.get("/cafe/stations")
async def list_stations(user=Depends(require_platform_owner)):
    """Liste des stations avec stats du mois courant + fenêtre de relance."""
    now = _now()
    docs = await db.cafe_stations.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    out = []
    for s in docs:
        stats = await _station_month_stats(s["id"], now)
        users_count = await db.users.count_documents(
            {"campaign_station_id": s["id"]}
        )
        out.append(
            {
                **_station_public(s, include_pin=True),
                "month_consumed": stats["consumed"],
                "month_earned": stats["earned"],
                "users_count": users_count,
                "objective_reached": stats["consumed"]
                >= s.get("monthly_objective", DEFAULT_MONTHLY_OBJECTIVE),
            }
        )
    return {"stations": out, "relance_window_open": _relance_window_open(now)}


@router.patch("/cafe/stations/{station_id}")
async def update_station(
    station_id: str, payload: StationUpdate, user=Depends(require_platform_owner)
):
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if "pin" in updates and (
        len(updates["pin"]) != 4 or not updates["pin"].isdigit()
    ):
        raise HTTPException(400, "Le PIN doit être composé de 4 chiffres")
    if not updates:
        raise HTTPException(400, "Aucune modification fournie")
    r = await db.cafe_stations.update_one({"id": station_id}, {"$set": updates})
    if r.matched_count == 0:
        raise HTTPException(404, "Station introuvable")
    doc = await db.cafe_stations.find_one({"id": station_id}, {"_id": 0})
    return _station_public(doc, include_pin=True)


@router.get("/cafe/dashboard")
async def cafe_dashboard(user=Depends(require_platform_owner)):
    """Tableau de bord : historique 6 mois par station (cafés liquidés)."""
    now = _now()
    stations = await db.cafe_stations.find({}, {"_id": 0}).to_list(100)
    months: List[dict] = []
    dt = now
    for _ in range(6):
        start, end = _month_bounds(dt)
        label = dt.strftime("%m/%Y")
        per_station = []
        for s in stations:
            consumed = await db.cafe_jetons.count_documents(
                {
                    "station_id": s["id"],
                    "status": "consumed",
                    "consumed_at": {"$gte": start, "$lte": end},
                }
            )
            per_station.append(
                {
                    "station_id": s["id"],
                    "station_name": s.get("name"),
                    "consumed": consumed,
                    "objective": s.get("monthly_objective", DEFAULT_MONTHLY_OBJECTIVE),
                }
            )
        months.append({"month": label, "stations": per_station})
        # Mois précédent
        dt = (dt.replace(day=1) - timedelta(days=1)).replace(day=1)
    total_consumed = await db.cafe_jetons.count_documents({"status": "consumed"})
    total_earned = await db.cafe_jetons.count_documents({})
    return {
        "months": months,
        "total_consumed": total_consumed,
        "total_earned": total_earned,
        "relance_window_open": _relance_window_open(now),
    }


@router.post("/cafe/stations/{station_id}/relance")
async def relance_station(station_id: str, user=Depends(require_platform_owner)):
    """Relance email manuelle : cible les artisans de la station qui n'ont
    PAS consommé de café ce mois-ci (« Nouveau projet, nouvelle pause ! »).

    Déclenchée MANUELLEMENT par le propriétaire (recommandé : 10 jours avant
    la fin du mois si l'objectif de la station n'est pas atteint).
    """
    station = await db.cafe_stations.find_one({"id": station_id}, {"_id": 0})
    if not station:
        raise HTTPException(404, "Station introuvable")

    start, end = _month_bounds(_now())
    # Users tagués sur cette station
    users = await db.users.find(
        {"campaign_station_id": station_id, "status": {"$ne": "deleted"}},
        {"_id": 0, "id": 1, "name": 1, "email": 1},
    ).to_list(500)

    # Exclut ceux qui ont déjà consommé un café ce mois-ci
    consumed_this_month = await db.cafe_jetons.distinct(
        "user_id",
        {
            "station_id": station_id,
            "status": "consumed",
            "consumed_at": {"$gte": start, "$lte": end},
        },
    )
    targets = [u for u in users if u["id"] not in set(consumed_this_month)]

    from email_service import send_email

    sent = 0
    for u in targets:
        first_name = (u.get("name") or "").split(" ")[0] or "artisan"
        try:
            send_email(
                to=u["email"],
                subject="☕ Nouveau projet, nouvelle pause ?",
                body=(
                    f"Bonjour {first_name},\n\n"
                    f"Votre café offert vous attend à la station {station.get('name')}"
                    f"{' (' + station.get('city') + ')' if station.get('city') else ''} !\n\n"
                    "Créez une nouvelle ouverture dans MesureChâssis et passez "
                    "faire valider votre jeton café à la pompe. "
                    "Nouveau projet, nouvelle pause !\n\n"
                    "À très vite,\nL'équipe MesureChâssis"
                ),
            )
            sent += 1
        except Exception:  # noqa: BLE001
            logger.warning("Relance email KO pour %s", u["email"])

    await db.cafe_relances.insert_one(
        {
            "id": str(uuid.uuid4()),
            "station_id": station_id,
            "sent_count": sent,
            "targets_count": len(targets),
            "triggered_by": user.get("email", ""),
            "triggered_at": _now().isoformat(),
        }
    )
    logger.info(
        "📧 Relance café station=%s → %d/%d emails", station_id, sent, len(targets)
    )
    return {"ok": True, "sent": sent, "targets": len(targets)}
