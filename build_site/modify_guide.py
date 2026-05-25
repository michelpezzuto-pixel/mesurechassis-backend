"""
Modifie telecharger.html pour ajouter un QR code pointant vers beta.html
+ Modifie guide.html avec les nouvelles images.
"""
import re
from pathlib import Path

SITE = Path("/app/site_mesurechassis_final")

# ============================================================================
# TELECHARGER.HTML : ajouter QR code vers beta.html
# ============================================================================
tel = (SITE / "telecharger.html").read_text(encoding="utf-8")

QR_BLOCK = """
<h2 style="text-align:center;margin-top:3rem">📱 Accédez immédiatement à la version web</h2>
<p style="text-align:center">En attendant la validation des apps officielles, vous pouvez tester <strong>tout le potentiel de MesureChâssis</strong> sur la version web. Scannez le QR code ci-dessous avec votre téléphone pour vous connecter instantanément.</p>

<div style="background:#1a1a1e;border:2px solid #FF6B35;border-radius:16px;padding:2rem;margin:2rem auto;max-width:520px;text-align:center;box-shadow:0 12px 40px rgba(255,107,53,0.15)">
  <div style="background:#fff;display:inline-block;padding:1rem;border-radius:12px;margin-bottom:1.25rem">
    <img src="https://api.qrserver.com/v1/create-qr-code/?size=240x240&data=https%3A%2F%2Fmesurechassis.com%2Fbeta.html&color=121214&bgcolor=ffffff&qzone=1" alt="QR code MesureChâssis - accès version web" width="240" height="240" style="display:block">
  </div>
  <h3 style="margin:0 0 .5rem;color:#fff">Scannez et accédez à la bêta</h3>
  <p style="color:#a8a8b0;margin:0 0 1.25rem">Ouvre directement la version web sécurisée de l'application sur votre mobile.</p>
  <a href="beta.html" style="display:inline-block;background:#FF6B35;color:#fff;padding:.85rem 1.75rem;border-radius:8px;font-weight:600;text-decoration:none">🌐 Ou cliquez ici depuis ce navigateur</a>
</div>

<p style="text-align:center;font-size:.85rem;color:#5a5a65">💡 <strong>Astuce</strong> : ajoutez la page à votre écran d'accueil iOS/Android pour un accès rapide comme une vraie app.</p>
"""

# Insérer juste avant la section "Configuration requise"
tel_new = tel.replace(
    '<h2>Configuration requise</h2>',
    QR_BLOCK + '\n<h2>Configuration requise</h2>',
    1
)
if tel_new == tel:
    print("⚠️  Section 'Configuration requise' non trouvée, ajout en fin")
    tel_new = tel.replace('</main>', QR_BLOCK + '\n</main>', 1)

(SITE / "telecharger.html").write_text(tel_new, encoding="utf-8")
print(f"✅ telecharger.html mis à jour (QR code ajouté)")

# ============================================================================
# GUIDE.HTML : remplacement des images des étapes 02, 03, 04, 05, 08
# ============================================================================
guide = (SITE / "guide.html").read_text(encoding="utf-8")
print(f"\nGuide.html original : {len(guide)} caractères")

# Identifier toutes les images base64
B64_IMG_RE = re.compile(r'<img\s+src="data:image/[^"]+?"[^>]*?/?>', re.DOTALL)
matches = list(B64_IMG_RE.finditer(guide))
print(f"Guide: {len(matches)} images base64 trouvées")

# Trouver le contexte de chaque image en regardant le texte ~500 chars avant
for i, m in enumerate(matches):
    start = max(0, m.start() - 500)
    context = guide[start:m.start()]
    # Chercher un h2/h3 récent
    last_heading = list(re.finditer(r'<h[23][^>]*>([^<]+)</h[23]>', context))
    last_h = last_heading[-1].group(1)[:60] if last_heading else "???"
    print(f"  Image {i} (pos {m.start()}): après h2/h3 = '{last_h}'")

# Pour le guide, on a 6 sections (Étapes 1, 2, 3, 4, 5, 6, 7, 8, ...)
# On va identifier par les <h2> précédents les zones à remplacer.

# Stratégie : utiliser des marqueurs textuels pour identifier les sections
# Et remplacer les images entre 2 sections

def replace_images_in_section(html, section_start_text, section_end_text, new_images, alt_prefix):
    """Replace ALL base64 images in a section by new images."""
    start_idx = html.find(section_start_text)
    if start_idx == -1:
        print(f"  ⚠️  Section début '{section_start_text[:40]}' non trouvée")
        return html, 0
    end_idx = html.find(section_end_text, start_idx + 1)
    if end_idx == -1:
        end_idx = len(html)
    section = html[start_idx:end_idx]
    img_matches = list(B64_IMG_RE.finditer(section))
    if not img_matches:
        print(f"  ⚠️  Aucune image base64 dans la section '{section_start_text[:40]}'")
        return html, 0
    # Construire nouveau bloc d'images
    new_block_parts = []
    for j, img_file in enumerate(new_images):
        new_block_parts.append(
            f'<img src="images/{img_file}" alt="{alt_prefix} - {j+1}" style="max-width:280px;height:auto;border-radius:18px;margin:10px;box-shadow:0 8px 30px rgba(0,0,0,0.3)">'
        )
    new_block = '<div style="display:flex;flex-wrap:wrap;justify-content:center;align-items:flex-start;gap:0;margin:1.5rem 0">' + ''.join(new_block_parts) + '</div>'
    # Remplacer la 1ère image par new_block, supprimer les autres
    new_section = section[:img_matches[0].start()] + new_block + section[img_matches[0].end():]
    # Re-extraire et supprimer les images restantes dans new_section
    remaining = list(B64_IMG_RE.finditer(new_section))
    for rm in reversed(remaining):
        new_section = new_section[:rm.start()] + '' + new_section[rm.end():]
    new_html = html[:start_idx] + new_section + html[end_idx:]
    print(f"  ✅ Section '{section_start_text[:50]}': {len(img_matches)} images remplacées par {len(new_images)} nouvelles")
    return new_html, len(img_matches)

# Étape 02 (Créer chantier) : 2 images
guide, _ = replace_images_in_section(
    guide,
    "Remplir la fiche client", "Structure de la maison",
    ["guide-02-a.jpg", "guide-02-b.jpg"],
    "Étape 02 - Créer un nouveau chantier"
)

# Étape 04 (Config mur) : 2 images
guide, _ = replace_images_in_section(
    guide,
    "Structure de la maison", "Étape 2/3",
    ["guide-04-a.jpg", "guide-04-b.jpg"],
    "Étape 04 - Configuration du mur"
)

# Étape 05 (Sélection menuiserie) : 2 images
guide, _ = replace_images_in_section(
    guide,
    "Étape 2/3 — La forme de la baie", "Étape 3/3",
    ["guide-05-a.jpg", "guide-05-b.jpg"],
    "Étape 05 - Sélection menuiserie"
)

# Étape 03 (Prise de cotes) : 6 images
guide, _ = replace_images_in_section(
    guide,
    "Étape 3/3 — Cotes & Vérification", "Depuis la fiche chantier",
    ["guide-03-1.jpg", "guide-03-2.jpg", "guide-03-3.jpg",
     "guide-03-4.jpg", "guide-03-5.jpg", "guide-03-6.jpg"],
    "Étape 03 - Prise de cotes"
)

# Étape 08 (Pipeline validation) : 3 images
guide, _ = replace_images_in_section(
    guide,
    "Clôturer & Valider", "Le flux de travail en entreprise",
    ["guide-08-a.jpg", "guide-08-b.jpg", "guide-08-c.jpg"],
    "Étape 08 - Pipeline de validation"
)

(SITE / "guide.html").write_text(guide, encoding="utf-8")
print(f"\n✅ guide.html sauvegardé ({len(guide)} caractères)")
