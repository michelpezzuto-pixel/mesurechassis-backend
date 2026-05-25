#!/usr/bin/env python3
"""Correction de guide.html : nettoyer les images dupliquées et améliorer le layout."""
import re

with open('/app/site_mesurechassis_final/guide.html', 'r', encoding='utf-8') as f:
    content = f.read()

print(f"Taille initiale: {len(content)} caractères")

# === FIX 1: Pipeline de validation - supprimer le 2e image base64 (la page blanche PDF) ===
# Dans la section pipeline (lignes 593-615), il y a deux images base64 consécutives dans le même screen-wrap.
# On garde la première (écran clôture) et on supprime la 2e (la page blanche en doublon).

# Trouver le bloc de la section pipeline et y supprimer la 2e <img base64
# La section pipeline commence par <section class="section" id="pipeline">
pipeline_start = content.find('<section class="section" id="pipeline">')
pipeline_end = content.find('</section>', pipeline_start) + len('</section>')

pipeline_html = content[pipeline_start:pipeline_end]
print(f"Section pipeline trouvée: {len(pipeline_html)} caractères")

# Compter les <img dans cette section
img_count = pipeline_html.count('<img ')
print(f"Nombre d'images dans la section pipeline: {img_count}")

# Supprimer la 2e image base64 (la "page blanche" doublon)
# On utilise regex pour matcher : on cherche deux <img base64 d'affilée et on supprime le 2e
# Pattern: trouver toutes les <img src="data:image..."> dans pipeline et garder seulement la 1ère
# Approche: après avoir trouvé la 1ère image (qui se termine par .../>"), supprimer la 2ème image base64

# Trouver position de la 1ère <img dans pipeline
first_img = pipeline_html.find('<img ')
# Trouver la fin de la 1ère <img (le > qui ferme la balise)
first_img_end = pipeline_html.find('>', first_img) + 1
# Trouver la 2ème <img si elle existe
second_img = pipeline_html.find('<img ', first_img_end)

if second_img != -1:
    # Trouver la fin de la 2ème <img
    second_img_end = pipeline_html.find('>', second_img) + 1
    # Supprimer la 2ème image (et les espaces autour)
    # On capture aussi les espaces/newlines précédents
    new_pipeline_html = pipeline_html[:second_img] + pipeline_html[second_img_end:]
    print(f"2ème image supprimée. Pipeline section: {len(pipeline_html)} -> {len(new_pipeline_html)}")
    content = content[:pipeline_start] + new_pipeline_html + content[pipeline_end:]
else:
    print("Pas de 2ème image dans pipeline section.")

# === FIX 2: Configuration du mur - déplacer les images du step-text vers screen-visual ===
# Les images guide-04-a et guide-04-b sont actuellement dans step-text après h3.
# On veut les déplacer dans le screen-wrap.
mur_old = '''    <div class="step-layout reverse reveal from-right">
      <div class="step-visual">
        <div class="screen-wrap">
          
          
          
        </div>
      </div>
      <div class="step-text">
        <h3>🧱 Structure de la maison — Étape 1/3</h3>
<div style="display:flex;flex-wrap:wrap;justify-content:center;align-items:flex-start;gap:0;margin:1.5rem 0">
<img src="images/guide-04-a.jpg" alt="Étape 04 - Configuration du mur - 1" style="max-width:280px;height:auto;border-radius:18px;margin:10px;box-shadow:0 8px 30px rgba(0,0,0,0.3)">
<img src="images/guide-04-b.jpg" alt="Étape 04 - Configuration du mur - 2" style="max-width:280px;height:auto;border-radius:18px;margin:10px;box-shadow:0 8px 30px rgba(0,0,0,0.3)">
</div>
'''

mur_new = '''    <div class="step-layout reverse reveal from-right">
      <div class="step-visual">
        <div class="screen-wrap" style="display:flex;flex-direction:column;gap:16px;align-items:center;justify-content:center">
          <img src="images/guide-04-a.jpg" alt="Étape 04 - Configuration du mur - 1" style="max-width:280px;width:100%;height:auto;border-radius:18px;box-shadow:0 8px 30px rgba(0,0,0,0.3)">
          <img src="images/guide-04-b.jpg" alt="Étape 04 - Configuration du mur - 2" style="max-width:280px;width:100%;height:auto;border-radius:18px;box-shadow:0 8px 30px rgba(0,0,0,0.3)">
        </div>
      </div>
      <div class="step-text">
        <h3>🧱 Structure de la maison — Étape 1/3</h3>
'''

if mur_old in content:
    content = content.replace(mur_old, mur_new)
    print("FIX 2: Configuration du mur - images déplacées dans screen-wrap ✓")
else:
    print("FIX 2: Pattern Configuration du mur non trouvé ✗")

# === FIX 3: Prise de cotes - améliorer le layout des 6 images avec une grille responsive ===
# Actuellement, les 6 images sont dans un flex-wrap avec gap:0 ce qui peut paraitre désordonné.
# On va utiliser une grille CSS 3x2 (responsive 2x3 sur mobile) pour un affichage propre.
cotes_old = '<div class="screen-wrap"><div style="display:flex;flex-wrap:wrap;justify-content:center;align-items:flex-start;gap:0;margin:1.5rem 0"><img src="images/guide-03-1.jpg" alt="Étape 03 - Prise de cotes - 1" style="max-width:280px;height:auto;border-radius:18px;margin:10px;box-shadow:0 8px 30px rgba(0,0,0,0.3)"><img src="images/guide-03-2.jpg" alt="Étape 03 - Prise de cotes - 2" style="max-width:280px;height:auto;border-radius:18px;margin:10px;box-shadow:0 8px 30px rgba(0,0,0,0.3)"><img src="images/guide-03-3.jpg" alt="Étape 03 - Prise de cotes - 3" style="max-width:280px;height:auto;border-radius:18px;margin:10px;box-shadow:0 8px 30px rgba(0,0,0,0.3)"><img src="images/guide-03-4.jpg" alt="Étape 03 - Prise de cotes - 4" style="max-width:280px;height:auto;border-radius:18px;margin:10px;box-shadow:0 8px 30px rgba(0,0,0,0.3)"><img src="images/guide-03-5.jpg" alt="Étape 03 - Prise de cotes - 5" style="max-width:280px;height:auto;border-radius:18px;margin:10px;box-shadow:0 8px 30px rgba(0,0,0,0.3)"><img src="images/guide-03-6.jpg" alt="Étape 03 - Prise de cotes - 6" style="max-width:280px;height:auto;border-radius:18px;margin:10px;box-shadow:0 8px 30px rgba(0,0,0,0.3)"></div></div>'

cotes_new = '''<div class="screen-wrap"><div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:20px;justify-items:center;align-items:start;margin:1.5rem 0;max-width:920px;margin-left:auto;margin-right:auto"><img src="images/guide-03-1.jpg" alt="Étape 03 - Prise de cotes - 1" style="width:100%;max-width:280px;height:auto;border-radius:18px;box-shadow:0 8px 30px rgba(0,0,0,0.3)"><img src="images/guide-03-2.jpg" alt="Étape 03 - Prise de cotes - 2" style="width:100%;max-width:280px;height:auto;border-radius:18px;box-shadow:0 8px 30px rgba(0,0,0,0.3)"><img src="images/guide-03-3.jpg" alt="Étape 03 - Prise de cotes - 3" style="width:100%;max-width:280px;height:auto;border-radius:18px;box-shadow:0 8px 30px rgba(0,0,0,0.3)"><img src="images/guide-03-4.jpg" alt="Étape 03 - Prise de cotes - 4" style="width:100%;max-width:280px;height:auto;border-radius:18px;box-shadow:0 8px 30px rgba(0,0,0,0.3)"><img src="images/guide-03-5.jpg" alt="Étape 03 - Prise de cotes - 5" style="width:100%;max-width:280px;height:auto;border-radius:18px;box-shadow:0 8px 30px rgba(0,0,0,0.3)"><img src="images/guide-03-6.jpg" alt="Étape 03 - Prise de cotes - 6" style="width:100%;max-width:280px;height:auto;border-radius:18px;box-shadow:0 8px 30px rgba(0,0,0,0.3)"></div></div>'''

if cotes_old in content:
    content = content.replace(cotes_old, cotes_new)
    print("FIX 3: Prise de cotes - grille responsive appliquée ✓")
else:
    print("FIX 3: Pattern Prise de cotes non trouvé ✗")

# Sauvegarder
with open('/app/site_mesurechassis_final/guide.html', 'w', encoding='utf-8') as f:
    f.write(content)

print(f"\nTaille finale: {len(content)} caractères")
print("✓ guide.html mis à jour")
