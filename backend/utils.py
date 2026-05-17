"""Utilitaires métier : calculs d'alertes et libellés humains."""
from __future__ import annotations

import math
from typing import Optional

from models import MesureCreate


# --- Labels --------------------------------------------------------------
def status_label(s: str) -> str:
    return {
        "devis_a_faire": "Devis à faire",
        "technique_a_valider": "Technique à valider",
        "en_commande": "En commande",
        "en_fabrication": "En fabrication",
        "cloture": "Clôturé",
    }.get(s, s)


def block_label(b: str) -> str:
    return {
        "standard": "Standard",
        "coulissant": "Coulissant",
        "porte": "Porte",
        "trapeze": "Trapèze",
    }.get(b, b)


WALL_TYPE_LABELS = {
    "ite": "ITE",
    "iti": "ITI",
    "brique_parement": "Brique de parement",
    "crepi_simple": "Crépi simple",
}


# --- Calcul des alertes (faux-aplomb, équerre, pente trapèze) ------------
def compute_alerts(
    m: MesureCreate,
) -> tuple[list[str], Optional[float]]:
    alerts: list[str] = []
    slope: Optional[float] = None
    bt = m.block_type
    if bt == "standard":
        widths = [
            v for v in (m.width_top, m.width_middle, m.width_bottom)
            if v is not None
        ]
        heights = [
            v for v in (m.height_left, m.height_middle, m.height_right)
            if v is not None
        ]
        if widths and (max(widths) - min(widths)) > 5:
            alerts.append("⚠️ Faux-aplomb détecté (largeurs)")
        if heights and (max(heights) - min(heights)) > 5:
            alerts.append("⚠️ Faux-aplomb détecté (hauteurs)")
        if (
            m.diag_1 is not None
            and m.diag_2 is not None
            and abs(m.diag_1 - m.diag_2) > 5
        ):
            alerts.append("⚠️ Hors-équerre")
    elif bt == "coulissant":
        widths = [m.width_top, m.width_middle, m.width_bottom]
        heights = [
            m.height_left,
            m.height_quarter_left,
            m.height_middle,
            m.height_quarter_right,
            m.height_right,
        ]
        if any(v is None for v in widths):
            alerts.append("ℹ️ 3 largeurs requises (haut/milieu/bas)")
        if any(v is None for v in heights):
            alerts.append(
                "ℹ️ 5 hauteurs requises pour détecter la flèche du linteau"
            )
        valid_h = [v for v in heights if v is not None]
        if len(valid_h) >= 3 and (max(valid_h) - min(valid_h)) > 5:
            alerts.append("⚠️ Flèche du linteau détectée")
    elif bt == "trapeze":
        if (
            m.width_small is not None
            and m.width_intermediate is not None
            and m.height_small is not None
            and m.height_large is not None
        ):
            dw = abs(m.width_intermediate - m.width_small)
            dh = abs(m.height_large - m.height_small)
            if dw > 0:
                slope = round(math.degrees(math.atan(dh / dw)), 2)
    return alerts, slope


# --- Helper d'accès au chantier (utilisé par /mesures) -------------------
async def check_chantier_access(db, chantier_id: str, user: dict) -> dict:
    from fastapi import HTTPException
    chantier = await db.chantiers.find_one(
        {
            "id": chantier_id,
            "company_id": user.get("company_id", "default"),
        }
    )
    if not chantier:
        raise HTTPException(404, "Chantier introuvable")
    return chantier
