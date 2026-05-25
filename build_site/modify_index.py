"""
Modifie index.html, guide.html et telecharger.html selon les demandes utilisateur.
Toutes les modifications utilisent les fichiers /images/xxx.jpg copiés depuis le PDF.
"""
import re
from pathlib import Path

SITE = Path("/app/site_mesurechassis_final")

# ============================================================================
# INDEX.HTML
# ============================================================================
idx = (SITE / "index.html").read_text(encoding="utf-8")

# Pattern pour matcher un <img src="data:image/...,..."> (avec gestion du suffixe pour ne pas dépasser)
B64_IMG_RE = re.compile(r'<img\s+src="data:image/[^"]+?"[^>]*?/?>', re.DOTALL)

# Trouver tous les <img base64> avec leurs positions
matches = list(B64_IMG_RE.finditer(idx))
print(f"Index: {len(matches)} images base64 trouvées")
for i, m in enumerate(matches):
    print(f"  Image {i}: position {m.start()}-{m.end()}, taille {m.end()-m.start()} chars")

# Stratégie : 
# - Image 0 (~ligne 1445) = HERO VISUAL DROITE → SUPPRIMER complètement (avec sa div wrapper)
# - Images 1, 2, 3 (~lignes 1530, 1538, 1546) = 3 mockups hero → remplacer par hero1, hero2, hero3
# - Images 4, 5, 6 (~lignes 1559, 1567, 1575) = Section "Connexion & Inscription" → remplacer par connexion.jpg (1 seule)

# 1. SUPPRIMER HERO VISUAL (image 0) avec sa wrapper div
# Chercher le bloc <div class="hero-visual">...</div>
hero_visual_re = re.compile(
    r'<div class="hero-visual">\s*<div class="hero-visual-img-wrap">.*?</div>\s*</div>\s*</div>',
    re.DOTALL
)
m = hero_visual_re.search(idx)
if m:
    idx = idx[:m.start()] + '' + idx[m.end():]
    print(f"✅ Hero visual supprimé ({m.end()-m.start()} caractères)")
else:
    # essai pattern plus simple
    hero_visual_re2 = re.compile(r'<div class="hero-visual">.*?</div>\s*</div>', re.DOTALL)
    m = hero_visual_re2.search(idx)
    if m:
        idx = idx[:m.start()] + '' + idx[m.end():]
        print(f"✅ Hero visual supprimé (pattern 2)")

# 2. Re-chercher les images après suppression
matches = list(B64_IMG_RE.finditer(idx))
print(f"\nAprès suppression hero: {len(matches)} images base64 restantes")

# 3. Remplacer les 3 premiers <img> restants par hero1, hero2, hero3
# Reverse iteration pour ne pas décaler les positions
replacements_hero = ["hero1.jpg", "hero2.jpg", "hero3.jpg"]
hero_count = 0
new_idx = idx
matches = list(B64_IMG_RE.finditer(new_idx))
# Traiter les 3 premières
for i in range(min(3, len(matches))):
    m = matches[i]
    replacement = f'<img src="images/{replacements_hero[i]}" alt="MesureChâssis - mockup {i+1}" style="width:100%;height:auto;border-radius:24px;display:block">'
    # Le faire dans new_idx
    new_idx = new_idx.replace(m.group(0), replacement, 1)
    hero_count += 1
print(f"✅ {hero_count} mockups hero remplacés")

# 4. Remplacer les images restantes (4,5,6 → section Connexion) par UNE SEULE image connexion.jpg
# On garde la première et on supprime les 2 autres
matches_after = list(B64_IMG_RE.finditer(new_idx))
print(f"Après remplacement hero: {len(matches_after)} images base64 restantes")
if len(matches_after) > 0:
    # Remplacer la première par connexion.jpg
    m = matches_after[0]
    replacement = f'<img src="images/connexion.jpg" alt="Connexion & Inscription MesureChâssis" style="width:100%;max-width:340px;height:auto;border-radius:24px;display:block;margin:0 auto">'
    new_idx = new_idx.replace(m.group(0), replacement, 1)
    print("✅ Image connexion remplacée")

# Supprimer les images restantes (en garder une seule)
matches_after2 = list(B64_IMG_RE.finditer(new_idx))
for m in reversed(matches_after2):
    new_idx = new_idx[:m.start()] + '' + new_idx[m.end():]
print(f"✅ {len(matches_after2)} images base64 supprimées")

# 5. Modifier les liens "Participer à la bêta gratuitement" → beta.html
new_idx = re.sub(
    r'<a([^>]*?)href="[^"]*"([^>]*?)>(\s*Participer à la bêta gratuitement\s*)</a>',
    r'<a\1href="beta.html"\2>\3</a>',
    new_idx, flags=re.IGNORECASE
)

# 6. Modifier les liens "Voir comment ça marche" → guide.html
new_idx = re.sub(
    r'<a([^>]*?)href="[^"]*"([^>]*?)>(\s*Voir comment ça marche\s*)</a>',
    r'<a\1href="guide.html"\2>\3</a>',
    new_idx, flags=re.IGNORECASE
)

print("✅ Liens hero CTA mis à jour (Participer à la bêta → beta.html ; Voir comment ça marche → guide.html)")

(SITE / "index.html").write_text(new_idx, encoding="utf-8")
print(f"\n✅ index.html sauvegardé ({len(new_idx)} caractères)")
