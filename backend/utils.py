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


def block_label(b: str, options: dict | None = None) -> str:
    """Retourne le libellé d'affichage d'une mesure.

    Priorité 1 : la forme exacte stockée dans `options.shape` (porte_garage,
    triangle, oeil_de_boeuf…). C'est la valeur précise saisie dans le wizard.
    Priorité 2 : détection par champs `options` spécifiques d'une forme
    (mesures anciennes avant l'ajout d'`options.shape`).
    Priorité 3 : le `block_type` générique stocké en DB (porte, trapeze…).
    """
    SHAPE_LABELS = {
        "rect": "Rectangle / Carré",
        "porte_entree": "Porte d'entrée",
        "porte_garage": "Porte de garage",
        "trapeze": "Trapèze",
        "triangle": "Triangle",
        "oeil_de_boeuf": "Œil-de-bœuf",
        "coulissant_levant": "Coulissant levant",
    }
    # Priorité 1 : forme exacte (options.shape)
    if options and isinstance(options, dict):
        shape = options.get("shape")
        if shape and shape in SHAPE_LABELS:
            return SHAPE_LABELS[shape]
        # Priorité 2 : détection par autres champs options spécifiques
        # (mesures créées avant que `options.shape` ne soit envoyé).
        if (
            options.get("garage_lintel_mm")
            or options.get("garage_ecoincon_left_mm")
            or options.get("garage_ecoincon_right_mm")
        ):
            return SHAPE_LABELS["porte_garage"]
        if options.get("triangle_base_mm") or options.get("triangle_height_mm"):
            return SHAPE_LABELS["triangle"]
        if options.get("oeil_diameter_mm"):
            return SHAPE_LABELS["oeil_de_boeuf"]
    # Priorité 3 : block_type générique
    if b == "porte":
        return SHAPE_LABELS["porte_entree"]
    if b == "coulissant":
        return SHAPE_LABELS["coulissant_levant"]
    if b == "trapeze":
        return SHAPE_LABELS["trapeze"]
    if b == "standard" or b == "rect":
        return SHAPE_LABELS["rect"]
    return b or "Ouverture"


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
