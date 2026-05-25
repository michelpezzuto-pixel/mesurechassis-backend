#!/usr/bin/env python3
"""Remplacement ciblé des 6 images data:image/* dans la section 'Conçue pour le terrain'"""
import re
from pathlib import Path

INDEX = Path("/app/site_mesurechassis_final/index.html")
content = INDEX.read_text(encoding="utf-8")

# Trouver la position du début et fin de la section "Conçue pour le terrain"
start_marker = 'Conçue pour le <em'
# La section va jusqu'à </section> suivant
start_idx = content.find(start_marker)
assert start_idx > 0, "Section 'Conçue pour le terrain' introuvable"
# fin = balise </section> qui suit
end_idx = content.find('</section>', start_idx)
section = content[start_idx:end_idx]

# Trouver toutes les images base64 dans cette section (en ordre)
# Pattern: src="data:image/...base64,...."
img_pattern = re.compile(r'src="data:image/[^"]+"')
matches = list(img_pattern.finditer(section))
print(f"Nombre d'images base64 trouvées dans la section : {len(matches)}")

# Ordre attendu (selon Message 255 utilisateur):
# 1. Tableau de bord, 2. Statistiques, 3. 7 formes de baies,
# 4. Prise de cotes Rectangle, 5. Prise de cotes Trapèze, 6. Pipeline
new_images = [
    "images/tableau_de_bord.jpg",
    "images/Statistique.jpg",
    "images/7-formes-de-baies.jpg",
    "images/Prise-de-cotes-Rectangle.jpg",
    "images/Prise-de-cotes-Trapeze.jpg",
    "images/Pipeline-de-validation.jpg",
]

if len(matches) < 6:
    print(f"⚠️ Seulement {len(matches)} images trouvées — vérifier la section.")

# Remplacer dans l'ordre inverse pour préserver les positions
new_section = section
for i in range(min(len(matches), 6) - 1, -1, -1):
    m = matches[i]
    replacement = f'src="{new_images[i]}"'
    new_section = new_section[:m.start()] + replacement + new_section[m.end():]
    print(f"  [{i+1}] -> {new_images[i]}")

# Reconstruire le HTML complet
content = content[:start_idx] + new_section + content[end_idx:]

INDEX.write_text(content, encoding="utf-8")
print(f"✅ index.html mis à jour ({len(content)} caractères)")
