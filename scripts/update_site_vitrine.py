#!/usr/bin/env python3
"""Mise à jour du site vitrine mesurechassis.com (11 juin 2026).

- Supprime tout le wording "Bêta" → "Offre de lancement" / "avant-première"
- Redirige tous les CTA + QR codes vers la page d'inscription testeur
  (l'ancienne cible était la preview Emergent qui se met en veille)
"""

from pathlib import Path

SRC = Path("/tmp/site")
OUT = Path("/tmp/site_maj")
OUT.mkdir(exist_ok=True)

TESTEUR_URL = "https://mesurechassis.com/devenir-testeur.html"

# Ordre important : du plus spécifique au plus générique
REPLACEMENTS = [
    # --- Liens vers la preview (qui se met en veille) → page testeur ---
    ("https://window-field-app.preview.emergentagent.com", TESTEUR_URL),
    # --- CTA & libellés spécifiques ---
    ("🚀 Essayer l'application maintenant", "🚀 Devenir testeur gratuitement"),
    ("Essayer l'application →", "Devenir testeur →"),
    ("Ouvrir l'application →", "S'inscrire au programme de test →"),
    ("📱 Coller l'URL dans Expo Go pour expérience native",
     "📱 Installation via Google Play après inscription"),
    ("Scannez et accédez à la bêta", "Scannez et devenez testeur"),
    ("Bêta Android via Internal Testing Play Store",
     "Android via le programme de testeurs Google Play"),
    ("Android Bêta", "Android"),
    ("version bêta", "version d'avant-première"),
    # --- Wording générique ---
    ("pendant la phase bêta", "pendant l'offre de lancement"),
    ("pendant la bêta", "pendant l'offre de lancement"),
    ("la phase bêta", "l'offre de lancement"),
    ("Bêta Gratuite", "Offre de Lancement"),
    ("Bêta gratuite", "Offre de lancement"),
    ("bêta gratuite", "offre de lancement"),
]

total = {}
for f in sorted(SRC.glob("*.html")):
    html = f.read_text(encoding="utf-8")
    count = 0
    for old, new in REPLACEMENTS:
        n = html.count(old)
        if n:
            html = html.replace(old, new)
            count += n
    (OUT / f.name).write_text(html, encoding="utf-8")
    total[f.name] = count

for name, c in total.items():
    print(f"{name}: {c} remplacements")
print("TOTAL:", sum(total.values()))

# Contrôle : occurrences restantes de bêta/beta (hors 'beta.html' nom de fichier)
import re
print("\n--- Occurrences 'bêta' restantes (à vérifier) ---")
for f in sorted(OUT.glob("*.html")):
    rest = re.findall(r"[^>]{0,40}[Bb]êta[^<]{0,40}", f.read_text(encoding="utf-8"))
    for r in set(rest):
        print(f"{f.name}: …{r.strip()}…")
