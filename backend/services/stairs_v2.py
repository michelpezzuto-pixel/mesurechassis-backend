"""
Compute v2 — Multi-stair / Niveaux / Tronçons.
Le moteur Blondel (services/stairs.py) reste intact. Ce module l'utilise
comme une lib pure de base.

Stratégie :
- Un escalier = N niveaux empilés (RDC → R+1 → ...).
- Chaque niveau a une hauteur (mm) et N tronçons :
   * droit / quart_bas / quart_haut : portent des marches (longueur = reculement utile)
   * palier : longueur fixe, 0 marche, consomme du reculement.
- On répartit les marches du niveau proportionnellement aux LONGUEURS des tronçons "marche".
- On calcule h = hauteur_effective / n_marches_niveau, g optimisé par Blondel (~630).
- Pour chaque tronçon "marche", on déduit le nombre de marches dédiées.
- Cohérence : si h sort de [150-210] ou Blondel hors [560-670] → warning.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List

MIN_H = 150
MAX_H = 210
MIN_G = 230
BLONDEL_LOW = 560
BLONDEL_HIGH = 670
BLONDEL_TARGET = 630


def _effective_height(niveau: Dict[str, Any]) -> float:
    """Soustrait la réserve de sol si le niveau n'est pas en finition zéro."""
    h = float(niveau.get("hauteur_mm") or 0)
    if not niveau.get("sol_fini", True):
        h -= float(niveau.get("reserve_mm") or 0)
    return max(h, 0)


def _solve_n_steps(true_height: float) -> int:
    """Trouve n tel que h = true_height/n est dans [MIN_H..MAX_H], préférence vers ~180."""
    if true_height <= 0:
        return 0
    n_opt = max(1, round(true_height / 180))
    # Cherche le n qui donne h le plus proche de 180 ET valide [150-210]
    for delta in range(0, 6):
        for n in (n_opt + delta, n_opt - delta):
            if n <= 0:
                continue
            h = true_height / n
            if MIN_H <= h <= MAX_H:
                return n
    return n_opt  # fallback


def compute_niveau(niveau: Dict[str, Any]) -> Dict[str, Any]:
    """Compute geometry for a single niveau."""
    h_eff = _effective_height(niveau)
    troncons = niveau.get("troncons") or []
    # Trier par order
    troncons_sorted = sorted(troncons, key=lambda t: t.get("order", 0))
    # Séparer marches vs paliers
    marche_troncons = [t for t in troncons_sorted if t.get("type") in ("droit", "quart_bas", "quart_haut")]
    palier_troncons = [t for t in troncons_sorted if t.get("type") == "palier"]
    total_reculement_marches = sum(float(t.get("longueur_mm") or 0) for t in marche_troncons)
    total_reculement_paliers = sum(float(t.get("longueur_mm") or 0) for t in palier_troncons)
    total_reculement = total_reculement_marches + total_reculement_paliers

    notes: List[str] = []
    warnings: List[str] = []

    # Cas dégénéré
    if h_eff <= 0 or not marche_troncons:
        return {
            "hauteur_effective": round(h_eff, 1),
            "n_steps_niveau": 0,
            "h": 0,
            "g": 0,
            "blondel_value": 0,
            "valid_blondel": True,
            "slope_angle": 0,
            "total_reculement_marches": round(total_reculement_marches, 1),
            "total_reculement_paliers": round(total_reculement_paliers, 1),
            "total_reculement": round(total_reculement, 1),
            "troncons_calc": [],
            "warnings": warnings,
            "notes": notes,
        }

    n = _solve_n_steps(h_eff)
    h = h_eff / n if n > 0 else 0
    # Giron optimisé pour Blondel ~630
    # On choisit g pour que g * (n-1) ≈ total_reculement_marches si raisonnable.
    if n > 1 and total_reculement_marches > 0:
        g_geo = total_reculement_marches / (n - 1)
    else:
        g_geo = BLONDEL_TARGET - 2 * h
    g = max(MIN_G, g_geo)
    blondel = 2 * h + g
    valid_blondel = BLONDEL_LOW <= blondel <= BLONDEL_HIGH
    slope = math.degrees(math.atan2(h_eff, max(total_reculement_marches, 1)))

    if not (MIN_H <= h <= MAX_H):
        warnings.append(
            f"Hauteur de marche hors plage confortable : h={round(h)} mm (cible 150-210). "
            f"Ajuste la longueur des tronçons ou la hauteur du niveau."
        )
    if not valid_blondel:
        warnings.append(
            f"Loi de Blondel hors plage : 2h+g={round(blondel)} mm (cible 560-670). "
            f"Ergonomie compromise."
        )

    # Répartition marches par tronçon proportionnellement à la longueur
    troncons_calc: List[Dict[str, Any]] = []
    if total_reculement_marches > 0:
        raw_alloc = [
            (t, (float(t.get("longueur_mm") or 0) / total_reculement_marches) * n)
            for t in marche_troncons
        ]
        # Arrondi avec préservation du total
        alloc_int = [(t, int(round(v))) for t, v in raw_alloc]
        diff = n - sum(v for _, v in alloc_int)
        # Ajuste le plus gros tronçon si arrondi en dessous/dessus
        if diff != 0 and alloc_int:
            idx_max = max(range(len(alloc_int)), key=lambda i: alloc_int[i][1])
            t0, v0 = alloc_int[idx_max]
            alloc_int[idx_max] = (t0, max(0, v0 + diff))
        for t, marches in alloc_int:
            troncons_calc.append({
                "troncon_id": t["id"],
                "type": t["type"],
                "longueur_mm": float(t.get("longueur_mm") or 0),
                "n_marches": marches,
            })

    # Echo paliers
    for t in palier_troncons:
        troncons_calc.append({
            "troncon_id": t["id"],
            "type": "palier",
            "longueur_mm": float(t.get("longueur_mm") or 0),
            "n_marches": 0,
        })
    troncons_calc.sort(key=lambda c: next((idx for idx, x in enumerate(troncons_sorted) if x["id"] == c["troncon_id"]), 0))

    return {
        "hauteur_effective": round(h_eff, 1),
        "n_steps_niveau": n,
        "h": round(h, 1),
        "g": round(g, 1),
        "blondel_value": round(blondel, 1),
        "valid_blondel": valid_blondel,
        "slope_angle": round(slope, 2),
        "total_reculement_marches": round(total_reculement_marches, 1),
        "total_reculement_paliers": round(total_reculement_paliers, 1),
        "total_reculement": round(total_reculement, 1),
        "troncons_calc": troncons_calc,
        "warnings": warnings,
        "notes": notes,
    }


def compute_stair(stair: Dict[str, Any]) -> Dict[str, Any]:
    """Aggrège les calculs de tous les niveaux d'un escalier."""
    niveaux = sorted(stair.get("niveaux") or [], key=lambda n: n.get("order", 0))
    niveaux_calc = [compute_niveau(n) for n in niveaux]

    total_height = sum(n["hauteur_effective"] for n in niveaux_calc)
    total_steps = sum(n["n_steps_niveau"] for n in niveaux_calc)
    total_reculement = sum(n["total_reculement"] for n in niveaux_calc)
    # Limon = hypoténuse globale
    limon = math.sqrt(total_height ** 2 + total_reculement ** 2) if total_reculement > 0 else total_height
    all_warnings = [w for c in niveaux_calc for w in c.get("warnings", [])]

    return {
        "stair_id": stair["id"],
        "name": stair.get("name"),
        "n_niveaux": len(niveaux),
        "total_height": round(total_height, 1),
        "total_steps": total_steps,
        "total_reculement": round(total_reculement, 1),
        "limon_length": round(limon, 1),
        "niveaux_calc": [
            {**c, "niveau_id": n["id"], "label": n.get("label"), "hauteur_mm": n.get("hauteur_mm")}
            for c, n in zip(niveaux_calc, niveaux)
        ],
        "warnings": all_warnings,
    }
