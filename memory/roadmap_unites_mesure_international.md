# 🌍 Roadmap — Unités de mesure internationales (À FAIRE AVANT EXPANSION HORS EUROPE)

## Demande utilisateur (07/2026)
Si l'app est lancée aux États-Unis (ou tout pays non métrique), il faudra un réglage
dans les paramètres pour choisir le système d'unités :
- **Métrique** (mm/cm/m) — actuel, par défaut
- **Impérial** (pieds / pouces, fractions de pouce : 1/2", 1/4", 1/8", 1/16")

## Portée technique à prévoir
1. **Paramètre société ou utilisateur** `unit_system: "metric" | "imperial"` (profil société +
   éventuellement override par utilisateur). Détection auto possible via la locale du device.
2. **Wizard de mesures** : saisie et affichage dans l'unité choisie ; stockage TOUJOURS en mm
   en base (conversion à l'affichage uniquement — évite les incohérences).
3. **Exports PDF / Excel / ERP (XML)** : afficher l'unité choisie + mention explicite de l'unité.
4. **Scan CDC (IA)** : détecter l'unité du cahier des charges et convertir vers l'unité de la société.
5. **i18n** : l'app a déjà fr/en/nl → ajouter les formats numériques locaux (virgule vs point décimal).
6. Attention aux champs dérivés : périmètres, surfaces (m² vs sq ft), tolérances.

## Statut
- NON DÉMARRÉ — à planifier uniquement si lancement hors zone métrique.
