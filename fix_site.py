#!/usr/bin/env python3
"""Script de correction du site MesureChâssis - Hero + Conçue pour le terrain + Guide"""
import re
from pathlib import Path

SITE_DIR = Path("/app/site_mesurechassis_final")
INDEX = SITE_DIR / "index.html"
GUIDE = SITE_DIR / "guide.html"

# ============================================================
# 1) INDEX.HTML - Hero refonte + section "Conçue pour le terrain"
# ============================================================
content = INDEX.read_text(encoding="utf-8")

# --- 1.A : Supprimer le bloc hero-visual (image base64 droite) ---
# On localise <div class="hero-visual"> jusqu'au </div> qui ferme hero-visual
# Pattern : ouvre hero-visual, contient hero-visual-img-wrap, img, fermetures
hero_visual_pattern = re.compile(
    r'\s*<div class="hero-visual">.*?</div>\s*</div>',
    re.DOTALL
)
content_new, count = hero_visual_pattern.subn('', content, count=1)
print(f"[Hero-visual] Bloc supprimé : {count} occurrence(s)")
assert count == 1, "Échec suppression hero-visual"
content = content_new

# --- 1.B : Mettre à jour CTA principal ---
content = content.replace(
    'Participer à la bêta gratuitement',
    "Télécharger l'app en version bêta gratuit"
)
# Et le lien CTA principal vers telecharger.html (au lieu de window-field-app preview)
content = content.replace(
    '<a href="https://window-field-app.preview.emergentagent.com" target="_blank" rel="noopener" class="btn-hero">',
    '<a href="telecharger.html" class="btn-hero">'
)
print("[Hero CTA] Texte + lien CTA mis à jour")

# --- 1.C : Bouton secondaire "Voir comment ça marche" -> guide.html ---
content = content.replace(
    '<a href="#storytelling" class="btn-secondary">Voir comment ça marche</a>',
    '<a href="guide.html" class="btn-secondary">Voir comment ça marche</a>'
)
print("[Hero CTA secondaire] Lien mis à jour vers guide.html")

# --- 1.D : Adapter le CSS pour pleine largeur (titre élargi) ---
# On modifie .hero-inner pour passer en 1 colonne et augmenter la taille du h1
# 1) Remplacer grid template
content = content.replace(
    ".hero-inner { grid-template-columns: 1fr; gap: 3rem; }",
    ".hero-inner { grid-template-columns: 1fr; gap: 2rem; max-width: 1100px; }"
)

# Modifier la règle hero-inner principale (chercher la déclaration originale)
content = re.sub(
    r'(\.hero-inner\s*\{[^}]*?)\}',
    lambda m: m.group(1).replace('grid-template-columns: 1.05fr 1fr', 'grid-template-columns: 1fr') + '}'
    if 'grid-template-columns' in m.group(1) else m.group(0) + '}'.replace('}}', '}'),
    content,
    count=1
)
print("[Hero CSS] Layout passé en 1 colonne (pleine largeur)")

# --- 1.E : Remplacer les 6 images de la section "Conçue pour le terrain" ---
# Pour trouver ces images, on cherche les 6 cards dans la section #apercu (ligne ~1518)
# On va injecter les nouvelles images. Examinons d'abord le contenu actuel.
# Stratégie: injecter <img> dans chaque card en remplaçant les placeholders existants.

# Carte 1 : Tableau de bord
img_tags = {
    "tableau_de_bord": "tableau_de_bord.jpg",
    "statistique": "Statistique.jpg",
    "7_formes": "7-formes-de-baies.jpg",
    "rectangle": "Prise-de-cotes-Rectangle.jpg",
    "trapeze": "Prise-de-cotes-Trapeze.jpg",
    "pipeline": "Pipeline-de-validation.jpg",
}

# Sauver les modifications en cours
INDEX.write_text(content, encoding="utf-8")
print(f"[OK] index.html sauvegardé ({len(content)} caractères)")

# ============================================================
# 2) GUIDE.HTML - Nettoyage et réorganisation
# ============================================================
guide_content = GUIDE.read_text(encoding="utf-8")
original_size = len(guide_content)

# Identifier les images PDF (page blanche) en doublon dans pipeline
# Les images guide-08-* étaient pour pipeline. Vérifions qu'il n'y a pas de doublon
import re as re2
pipeline_images = re2.findall(r'<img[^>]*guide-08[^>]*>', guide_content)
print(f"[Guide] Images pipeline détectées : {len(pipeline_images)}")

GUIDE.write_text(guide_content, encoding="utf-8")
print(f"[OK] guide.html sauvegardé ({len(guide_content)} caractères, original={original_size})")

print("\n✅ Script terminé.")
