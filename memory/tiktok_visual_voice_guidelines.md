# 🎬 Charte visuelle & sonore — Contenu TikTok MesureChâssis

> ⚠️ **À LIRE AVANT toute génération d'images/voix pour TikTok**
> Décidé avec Michel le 30/06/2026 après validation du Script #5

## 🖼️ STYLE VISUEL DES IMAGES (Gemini Nano Banana)

### Univers menuiserie : ALUMINIUM uniquement
- ✅ Châssis en aluminium gris anthracite, noir, blanc, bronze
- ✅ Fenêtres modernes minimalistes (profilés Schüco, Reynaers, Aluk style)
- ✅ Maisons / immeubles en béton, façades contemporaines
- ✅ Bâtiments modernes (verre, béton, métal)
- ❌ JAMAIS de bois (châssis bois, chalets, ancien)
- ❌ JAMAIS de petits bouts de bois isolés sur table

### Action / mise en scène
- ✅ Un menuisier en action sur chantier (vue de dos / mains uniquement)
- ✅ Mètre ruban tendu DANS l'ouverture (diagonale, hauteur, largeur)
- ✅ Outils pro visibles (laser de mesure, ruban 5m, niveau bulle)
- ✅ Tenue : t-shirt de chantier, gilet jaune fluo, casque optionnel
- ✅ Lumière : soleil rasant ou lumière de chantier (style cinéma)
- ❌ JAMAIS d'objet décontextualisé hors chantier
- ❌ JAMAIS de scènes "intérieur cosy"

### Format technique
- 9:16 vertical (1080×1920)
- Photoréaliste, qualité pro
- Couleurs : palette MesureChâssis (orange #FF6F00, noir, blanc)
- Textes overlay : orange + blanc, bold uppercase

## 🎙️ VOIX-OFF (OpenAI TTS)

### Préférée
- **Modèle** : `tts-1-hd` (qualité supérieure, plus naturel)
- **Voix** : `nova` (féminine, énergique, naturelle)
- Alternative : `shimmer` (féminine, plus douce)
- **Speed** : 1.0 (standard) ou 1.05 (légèrement énergique)

### À ÉVITER
- ❌ `onyx` (voix masculine trop robotique selon Michel)
- ❌ `tts-1` (qualité basique)

### Si toujours trop robotique
- Tester gpt-4o-mini-tts (modèle plus récent)
- Ou proposer ElevenLabs (nécessite API key séparée)

## 📚 Prompts type pour images alu

```
Vertical 9:16 portrait, photorealistic, professional French carpenter
on construction site, taking a DIAGONAL measurement on a large
ALUMINUM window frame (anthracite grey, modern profile, Schüco/Reynaers
style), measuring tape extended across the diagonal of the opening,
modern CONCRETE house façade in the background (contemporary
architecture), warm cinematic lighting (golden hour), worker hands
visible holding the tape, focus on precision and craftsmanship,
high-end B2B SaaS marketing visual
```

## 🎯 Pour ajuster un prompt à un script

Toujours inclure :
1. "ALUMINUM window frame" (jamais wood)
2. "modern CONCRETE building" (jamais wooden chalet)
3. "professional carpenter ON SITE" (jamais isolated objects)
4. "measuring tape extended in the actual opening" (jamais bois isolé)
5. "anthracite grey / black / white aluminum profile"

## 🎬 État des scripts

- Script #5 (5 erreurs à 1000€) : ✅ généré + voix `onyx` (à régénérer en `nova`)
- Scripts #1, #2, #3, #4, #6, #7, #8, #9, #10 : à générer avec NOUVEAU style
