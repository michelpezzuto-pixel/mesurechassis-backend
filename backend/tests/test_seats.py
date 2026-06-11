"""Tests unitaires de la logique de sièges par plan (seats.py)."""

import sys

sys.path.insert(0, "/app/backend")

from seats import SEAT_PLANS, seat_config_for_plan


def test_entreprise_config():
    cfg = seat_config_for_plan("entreprise")
    assert cfg["free_team_seats"] == 2  # + admin = 3 comptes inclus
    assert cfg["seat_price_eur"] == 4.99
    assert cfg["label"] == "Entreprise"


def test_pro_config():
    cfg = seat_config_for_plan("pro")
    assert cfg["free_team_seats"] == 5  # + admin = 6 comptes inclus
    assert cfg["seat_price_eur"] == 9.99
    assert cfg["label"] == "Entreprise Pro"


def test_fallback_to_entreprise():
    """Plan inconnu, None ou solo → config Entreprise par défaut."""
    for plan in (None, "", "solo", "inconnu", "ENTREPRISE"):
        cfg = seat_config_for_plan(plan)
        assert cfg["seat_price_eur"] in (4.99, 9.99)
    assert seat_config_for_plan(None) == SEAT_PLANS["entreprise"]
    assert seat_config_for_plan("PRO") == SEAT_PLANS["pro"]


def test_extra_seat_computation():
    """Vérifie le calcul du surcoût pour chaque plan."""
    for plan, team_size, expected_extra in [
        ("entreprise", 2, 0),   # 3 comptes au total → inclus
        ("entreprise", 3, 1),   # 4ème compte → 1 siège facturé
        ("entreprise", 5, 3),
        ("pro", 5, 0),          # 6 comptes au total → inclus
        ("pro", 6, 1),          # 7ème compte → 1 siège facturé
        ("pro", 9, 4),
    ]:
        cfg = seat_config_for_plan(plan)
        extra = max(0, team_size - cfg["free_team_seats"])
        assert extra == expected_extra, f"{plan} team={team_size}"


def test_extra_amounts():
    cfg_e = seat_config_for_plan("entreprise")
    cfg_p = seat_config_for_plan("pro")
    assert round(2 * cfg_e["seat_price_eur"], 2) == 9.98
    assert round(2 * cfg_p["seat_price_eur"], 2) == 19.98
