# Backlog : Mise à jour du site web mesurechassis.com

## Objectif
Aligner le contenu du site web sur les nouvelles fonctionnalités du Build 8/26 de l'application mobile.

## Date d'ajout
2026-06-08 (suite à la présentation de M. Pezzuto)

## Statut
🟡 À PLANIFIER — après stabilisation des stores (Google Play validation + Apple resoumission)

---

## Mises à jour à effectuer

### 🎨 Section "Fonctionnalités"
- [ ] Mettre en avant les **14 formes de fenêtres** (vs 7 actuellement)
  - Détailler les 7 nouvelles : Plein cintre, Arc surbaissé, Angle 90°, Bow-Window, Pentagone, Hexagone, Ovale
- [ ] Présenter le **système RBAC** complet :
  - Admin Entreprise
  - Commercial (mesure et clôture)
  - Technicien (vérifie, approuve ou renvoie)
  - Artisan Solo (tout-en-un)
- [ ] Workflow de validation Commercial → Technicien avec mod-requests
- [ ] Emails automatiques (inscription, prise de cotes à vérifier)
- [ ] Mode lecture seule pour l'Admin
- [ ] Mise à jour mobile (iOS + Android)

### 📚 Section "FAQ"
- [ ] Mettre à jour avec les **25 questions** (vs 10) actuelles dans l'app
- [ ] Source : `/app/frontend/src/data/faq_data.json`

### 📥 Section "Téléchargement / Get the app"
- [ ] Bouton **Google Play** (dès validation publique)
- [ ] Bouton **App Store** (dès validation post-correction Stripe)
- [ ] Liens vers les pages stores une fois publié

### 🏠 Page d'accueil
- [ ] Hero section avec visuel des nouvelles formes
- [ ] Screenshots du Build 8 (RBAC, nouvelles formes, etc.)
- [ ] Section témoignages menuisiers (à recueillir auprès des 12 testeurs)
- [ ] Mise en avant du programme de parrainage (Build 9 — mois gratuits)

### 💰 Section "Tarifs / Pricing"
- [ ] Vérifier cohérence avec l'abonnement Stripe
- [ ] Mentionner le programme de parrainage à venir (Build 9)

### 📞 Section "Contact"
- [ ] Vérifier email contact : `info@mesurechassis.com`
- [ ] Formulaire de contact fonctionnel

---

## Stack technique du site
- À identifier lors de la reprise (probablement HTML/CSS/JS statique ou WordPress)
- Localisation : `/app/site_mesurechassis_final/` ? À vérifier

## Priorité
**P2 — Après stabilisation des stores**

Pas urgent tant que :
1. Google Play n'a pas validé le test fermé
2. Apple n'a pas re-validé le Build 8 corrigé

Une fois les 2 stores OK → mise à jour site web devient P1 (pour le lancement marketing).
