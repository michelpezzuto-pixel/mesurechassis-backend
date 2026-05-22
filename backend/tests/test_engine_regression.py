"""
Tests de NON-RÉGRESSION pour le moteur de calcul d'escalier.
Figent le comportement actuel AVANT toute refonte. Toute modif qui casse
l'un de ces tests doit être considérée comme une régression et rejetée.

Lancer : pytest backend/tests/test_engine_regression.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.schemas import MeasurementInput  # noqa: E402
from services.stairs import compute_stair  # noqa: E402


def _payload(**overrides) -> MeasurementInput:
    base = dict(
        hauteur_brute=2700,
        sols_finis_zero=True,
        reserve_bas=0,
        reserve_haut=0,
        epaisseur_dalle=200,
        tremie_longueur=2400,
        tremie_largeur=900,
        reculement_max=3500,
        material="bois",
        remarques="",
    )
    base.update(overrides)
    return MeasurementInput(**base)


def _compute(**overrides) -> dict:
    """compute_stair() renvoie un Pydantic model — on le wrappe en dict."""
    result = compute_stair(_payload(**overrides))
    return result.model_dump() if hasattr(result, "model_dump") else dict(result)


# ─── Cas standard h=2700 / recul=3500 (référence baseline) ────────────────────

def test_standard_n_steps_15():
    r = _compute()
    assert r["n_steps"] == 15


def test_standard_h_180():
    r = _compute()
    assert r["h"] == 180.0


def test_standard_giron_dans_blondel():
    r = _compute()
    assert 240 <= r["g"] <= 280


def test_standard_blondel_valide():
    r = _compute()
    assert r["valid_blondel"] is True
    assert 560 <= r["blondel_value"] <= 670


def test_standard_limon_coherent():
    r = _compute()
    assert 4200 <= r["limon_length"] <= 4900


def test_standard_echappee_presente():
    r = _compute()
    assert "echappee" in r


def test_standard_shape_renvoyee():
    r = _compute()
    assert isinstance(r.get("shape"), str) and len(r["shape"]) > 0


def test_standard_notes_liste():
    r = _compute()
    assert isinstance(r.get("notes", []), list)


# ─── Réserves : déduire de la hauteur brute ──────────────────────────────────

def test_hauteur_effective_sans_sols_finis():
    r = _compute(sols_finis_zero=False, reserve_bas=30, reserve_haut=20)
    assert r["true_height"] in (2650, 2700 - 30 - 20)


# ─── Cas extrêmes : petite et grande hauteur ─────────────────────────────────

def test_petit_h_1800():
    r = _compute(hauteur_brute=1800, reculement_max=2500)
    assert 8 <= r["n_steps"] <= 12
    assert r["h"] > 0


def test_grande_h_3200():
    r = _compute(hauteur_brute=3200, reculement_max=4200)
    assert 16 <= r["n_steps"] <= 20
    assert 160 <= r["h"] <= 200


# ─── Trémie courte : échappée critique ───────────────────────────────────────

def test_echappee_critique_si_tremie_courte():
    r = _compute(tremie_longueur=1500)
    if r.get("echappee") is not None and r["echappee"] < 2000:
        assert r.get("echappee_critique") is True


# ─── Contrat API (champs obligatoires pour le frontend) ──────────────────────

@pytest.mark.parametrize("field", [
    "n_steps", "h", "g", "blondel_value", "valid_blondel", "true_height",
    "reculement_needed", "slope_angle", "shape", "limon_length",
])
def test_contrat_champ(field):
    r = _compute()
    assert field in r, f"Champ obligatoire absent: {field}"


def test_n_steps_entier_positif():
    r = _compute()
    assert isinstance(r["n_steps"], int)
    assert r["n_steps"] > 0


def test_angle_pente_realiste():
    r = _compute()
    assert 20 <= r["slope_angle"] <= 50
