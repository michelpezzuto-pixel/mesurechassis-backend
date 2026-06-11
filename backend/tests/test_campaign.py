"""Tests unitaires du module Campagne (routes/campaign.py) — parties pures."""

import csv
import sys

sys.path.insert(0, "/app/backend")

from routes.campaign import (
    BODY_TEMPLATE,
    DAILY_LIMIT,
    EMAIL_RE,
    ORIGIN_PHRASES,
    PROSPECTS_CSV,
    RELANCE_DELAY_DAYS,
    RELANCE_TEMPLATE,
    SUBJECTS,
)


def test_csv_embarque_present_et_valide():
    """Le CSV des 56 prospects doit être commité et parsable (utf-8-sig, `;`)."""
    assert PROSPECTS_CSV.exists()
    with PROSPECTS_CSV.open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f, delimiter=";"))
    assert len(rows) >= 50
    valides = [r for r in rows if EMAIL_RE.match((r.get("EMAIL") or "").strip().lower())]
    assert len(valides) == len(rows), "Tous les emails du CSV doivent être valides"


def test_limite_quotidienne_anti_spam():
    """Resend petit volume : on ne dépasse jamais 15 emails/jour."""
    assert DAILY_LIMIT == 15


def test_template_email():
    """Le corps personnalise l'entreprise et contient lien testeur + mention STOP."""
    body = BODY_TEMPLATE.format(company="FT Châssis", origin=ORIGIN_PHRASES["be"])
    assert "FT Châssis" in body
    assert "https://mesurechassis.com/devenir-testeur.html" in body
    assert "STOP" in body  # RGPD / désinscription
    for subject in SUBJECTS.values():
        assert "beta" not in subject.lower()  # conformité stores


def test_adaptation_pays():
    """Option B client : 'belge' pour BE uniquement, texte neutre pour FR/LU."""
    assert "belge" in ORIGIN_PHRASES["be"]
    assert "belge" not in ORIGIN_PHRASES["fr"]
    assert "belge" not in ORIGIN_PHRASES["lu"]
    assert "belge" in SUBJECTS["be"]
    assert "belge" not in SUBJECTS["fr"]
    assert "belge" not in SUBJECTS["lu"]


def test_regex_email():
    assert EMAIL_RE.match("info@ftchassis.be")
    assert not EMAIL_RE.match("pas-un-email")
    assert not EMAIL_RE.match("a@b")


def test_relance_j5():
    """Relance auto J+5 : délai correct, template avec lien + STOP."""
    assert RELANCE_DELAY_DAYS == 5
    body = RELANCE_TEMPLATE.format(company="FT Châssis")
    assert "FT Châssis" in body
    assert "https://mesurechassis.com/devenir-testeur.html" in body
    assert "STOP" in body
    assert "beta" not in body.lower()


def test_recap_hebdo_config():
    """Récap hebdo : destinataire admin, programmé le lundi matin."""
    from routes.campaign import RECAP_HOUR_UTC, RECAP_RECIPIENT, RECAP_WEEKDAY

    assert RECAP_RECIPIENT == "info@mesurechassis.com"
    assert RECAP_WEEKDAY == 0  # lundi
    assert 6 <= RECAP_HOUR_UTC <= 9  # matinée belge
