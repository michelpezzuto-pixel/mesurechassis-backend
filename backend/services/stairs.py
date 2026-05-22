"""Stair calculation engine (Loi de Blondel + règles de l'art FR).

Hard safety rules:
    * Giron g >= 230 mm
    * Hauteur de marche h <= 210 mm
    * 560 <= 2h + g <= 670 mm
    * Idéal: h ~ 175 mm, 2h+g ~ 630 mm
"""
from __future__ import annotations

import math
from typing import List, Optional

from fastapi import HTTPException

from models.schemas import MeasurementInput, MeasurementResult

H_MIN = 150.0
H_MAX_HARD = 210.0
G_MIN_HARD = 230.0
G_MAX = 350.0
BLONDEL_MIN = 560.0
BLONDEL_MAX = 670.0
BLONDEL_TARGET = 630.0
H_TARGET = 175.0


def _search_step_combination(true_h: float):
    """Best (n, h, g) within hard limits. Returns (n, h, g, valid_hard)."""
    best_valid = None
    best_any = None
    for n in range(8, 30):
        h = true_h / n
        if h < H_MIN:
            continue
        g = BLONDEL_TARGET - 2 * h
        g = max(200.0, min(G_MAX, g))
        blondel = 2 * h + g
        score = abs(h - H_TARGET) + abs(blondel - BLONDEL_TARGET) * 0.5
        hard_ok = (
            h <= H_MAX_HARD
            and g >= G_MIN_HARD
            and BLONDEL_MIN <= blondel <= BLONDEL_MAX
        )
        if hard_ok and (best_valid is None or score < best_valid[0]):
            best_valid = (score, n, h, g)
        if best_any is None or score < best_any[0]:
            best_any = (score, n, h, g)
    if best_valid is not None:
        _, n, h, g = best_valid
        return n, h, g, True
    if best_any is not None:
        _, n, h, g = best_any
        return n, h, g, False
    n = max(1, round(true_h / H_TARGET))
    h = true_h / n
    g = max(G_MIN_HARD, BLONDEL_TARGET - 2 * h)
    return n, h, g, False


def compute_stair(inp: MeasurementInput) -> MeasurementResult:
    if inp.sols_finis_zero:
        true_h = inp.hauteur_brute
    else:
        true_h = inp.hauteur_brute - inp.reserve_bas - inp.reserve_haut

    notes: List[str] = []
    if true_h <= 0:
        raise HTTPException(status_code=400, detail="Hauteur effective invalide (négative ou nulle)")

    n, h, g, hard_ok = _search_step_combination(true_h)

    reculement_needed = (n - 1) * g
    limon = math.sqrt(true_h ** 2 + reculement_needed ** 2)
    slope = math.degrees(math.atan2(true_h, reculement_needed))
    blondel = 2 * h + g
    valid_blondel = BLONDEL_MIN <= blondel <= BLONDEL_MAX

    is_tournant = False
    ligne_foulee_note: Optional[str] = None
    shape_key: str = "droit"

    if not hard_ok:
        if inp.reculement_max >= reculement_needed * 0.65:
            shape = "Quart-tournant requis (règles de sécurité)"
            shape_key = "quart_bas"
        else:
            shape = "Hélicoïdal / colimaçon recommandé"
            shape_key = "helicoidal"
        is_tournant = True
        notes.append(
            "Règles de l'art non respectées sur un escalier droit "
            f"(h≤210 mm, g≥230 mm, 560≤2h+g≤670). "
            f"Valeurs calculées : h={round(h)} g={round(g)} 2h+g={round(blondel)}."
        )
    elif inp.reculement_max >= reculement_needed:
        shape = "Escalier Droit Recommandé"
        shape_key = "droit"
    elif inp.reculement_max >= reculement_needed * 0.65:
        shape = "Quart-tournant requis"
        shape_key = "quart_bas"
        is_tournant = True
        notes.append("Reculement insuffisant pour escalier droit, quart-tournant nécessaire.")
    else:
        shape = "Double quart-tournant ou hélicoïdal"
        shape_key = "double_quart"
        is_tournant = True
        notes.append("Reculement très limité : envisager un escalier hélicoïdal ou en colimaçon.")

    # Override automatique si l'utilisateur a forcé une forme
    if inp.forme_choisie:
        shape_key = inp.forme_choisie
        is_tournant = shape_key != "droit"
        forme_label = {
            "droit": "Escalier droit (choix utilisateur)",
            "quart_bas": "Quart-tournant bas (choix utilisateur)",
            "quart_haut": "Quart-tournant haut (choix utilisateur)",
            "double_quart": "Double quart-tournant (choix utilisateur)",
            "helicoidal": "Hélicoïdal (choix utilisateur)",
        }
        shape = forme_label.get(shape_key, shape)

    if is_tournant:
        ligne_foulee_note = (
            "Le giron g est mesuré sur la LIGNE DE FOULÉE (centre géométrique "
            "du passage, à ~50 cm de la rampe), et non aux extrémités des "
            "marches balancées — gage d'un bon balancement et d'un confort de marche."
        )
        notes.append("Calcul giron référencé à la ligne de foulée (escalier tournant).")

    if not valid_blondel:
        notes.append(
            f"⚠️ Loi de Blondel hors plage : 2h+g = {round(blondel)} mm "
            f"(autorisé {int(BLONDEL_MIN)}–{int(BLONDEL_MAX)} mm)."
        )
    if h > H_MAX_HARD:
        notes.append(f"⚠️ Hauteur de marche excessive : h = {round(h)} mm (max 210 mm).")
    if g < G_MIN_HARD:
        notes.append(f"⚠️ Giron insuffisant : g = {round(g)} mm (min 230 mm).")
    if slope > 42:
        notes.append("Pente élevée (>42°) : inconfortable, à valider client.")
    elif slope < 25:
        notes.append("Pente faible (<25°) : vérifier reculement.")

    # ---- Échappée ----
    echappee: Optional[float] = None
    echappee_critique = False
    if inp.hauteur_sous_plafond_tremie is not None and inp.hauteur_sous_plafond_tremie > 0:
        x_tremie_start = max(0.0, reculement_needed - inp.tremie_longueur)
        n_under_slab = max(0, math.floor(x_tremie_start / g)) if g > 0 else 0
        echappee = round(inp.hauteur_sous_plafond_tremie - n_under_slab * h, 1)
        if echappee < 2000:
            echappee_critique = True
            notes.append(
                f"⚠️ Échappée critique : {round(echappee)} mm (< 2000 mm). "
                "Risque de choc à la tête — revoir la longueur de la trémie."
            )

    return MeasurementResult(
        true_height=round(true_h, 1),
        n_steps=n,
        h=round(h, 1),
        g=round(g, 1),
        slope_angle=round(slope, 2),
        hypotenuse=round(limon, 1),
        limon_length=round(limon, 1),
        reculement_needed=round(reculement_needed, 1),
        shape=shape,
        shape_key=shape_key,
        is_tournant=is_tournant,
        ligne_foulee_note=ligne_foulee_note,
        echappee=echappee,
        echappee_critique=echappee_critique,
        blondel_value=round(blondel, 1),
        valid_blondel=valid_blondel,
        notes=notes,
        largeur_volee=float(inp.largeur_volee or 900),
        jour_escalier=float(inp.jour_escalier or 100),
    )
