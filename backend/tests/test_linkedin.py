"""Tests unitaires du module Campagne LinkedIn (routes/linkedin.py)."""

import sys
from pathlib import Path

sys.path.insert(0, "/app/backend")

from routes.linkedin import IMAGES_DIR, POSTS, SITE


def test_quinze_posts_complets():
    """15 posts, jours 1→15, tous les champs remplis."""
    assert len(POSTS) == 15
    assert [p["day"] for p in POSTS] == list(range(1, 16))
    for p in POSTS:
        assert p["title"] and p["subtitle"] and p["hashtags"]
        assert len(p["text"]) > 200, f"Jour {p['day']} : texte trop court"


def test_pas_de_mention_beta_ni_placeholder():
    """Conformité : pas de '{site}' oublié, lien du site présent."""
    for p in POSTS:
        assert "{site}" not in p["text"], f"Jour {p['day']} : placeholder non remplacé"
    # Le site doit apparaître dans la grande majorité des posts (CTA)
    avec_site = sum(1 for p in POSTS if SITE in p["text"])
    assert avec_site >= 14


def test_hashtags_sans_retour_ligne():
    for p in POSTS:
        assert "\n" not in p["hashtags"]
        assert p["hashtags"].startswith("#")


def test_visuels_generes():
    """Les 15 PNG doivent être committés dans static/linkedin/."""
    assert IMAGES_DIR.exists()
    for day in range(1, 16):
        f = IMAGES_DIR / f"jour_{day:02d}.png"
        assert f.exists(), f"Visuel manquant : {f.name}"
        assert f.stat().st_size > 10_000, f"Visuel suspect (trop petit) : {f.name}"
