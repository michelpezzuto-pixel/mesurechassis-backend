# 📋 BRIEF TECHNIQUE & STRATÉGIQUE — MesureChâssis (juillet 2026)
(Rédigé pour synchroniser un assistant IA externe — copie du brief remis à Michel)

## 1. Architecture et Fonctionnalités
- SaaS mobile B2B de prise de mesures de châssis pour menuisiers/poseurs.
- Stack : React Native Expo (iOS/Android/Web, expo-router, i18n FR/EN/NL) + FastAPI + MongoDB Atlas.
- Infra prod : Railway (backend), mesurechassis.com (site), Resend (emails), Stripe (web only, en pause), OpenAI/Gemini (IA).
- RBAC : Admin / Commercial / Technicien + mode Artisan solo. JWT 7 jours.
- Formes gérées (14 historiques → 12 types consolidés) : Rectangle, Porte d'entrée, Porte de garage,
  Trapèze, Œil-de-bœuf, Coulissant levant, Plein cintre, Arc surbaissé, Pan coupé, Bow-window,
  Polygone 3-8 arêtes (unifie triangle/pentagone/hexagone/octogone), Ovale.
- Wizard 3 étapes (mur → forme → cotes en mm, schémas SVG), exports PDF/Excel/XML ERP, scan CDC IA,
  parrainage, FAQ, assistant IA Yann, outils internes propriétaire (campagne Resend, LinkedIn, testeurs)
  verrouillés via require_platform_owner.

## 2. Statut Actuel
- iOS : build 1.0.14 (116) en review (~16 soumissions). Modèle B2B sans IAP accepté (3.1.3c).
  iOS = ZÉRO mention prix/essai/abonnement/Artisan (guards Platform.OS ios partout). Compte démo expiré
  pour test paywall. NE JAMAIS réintroduire de mention commerciale sur iOS.
- Android : tests fermés à venir (12 testeurs/14 jours), gratuité à vie promise aux testeurs (flag lifetime_free à créer).
- Monétisation : BETA_MODE global (gratuit). Cibles : Artisan 24,99€/m, Entreprise 59,99€/m, siège +4,99€/m — vente web only.
- Dettes (post-Apple) : JWT_SECRET + PLATFORM_ADMIN_TOKEN hardcodés, routes ZIP publiques, pas d'offline, compression photos.

## 3. Vision et RoadMap
- Priorités : approbation Apple → sécurité P0 → Play Store.
- Dev : Odoo + auto-devis, partenariat Elcia/Ramasoft, extraction CDC stricte + alertes dates,
  config mur optionnelle, pop-up « seul ? passez Artisan » (pas sur iOS), offline sync queue,
  module Escalier, signature client, unités impériales (US).
- Marketing : TikTok faceless (6 scripts faits, #7-#10 à venir), cold email Resend (~200 envoyés, scaling post-Apple),
  campagne scratch cards à Charleroi (guérilla locale, QR code à cadrer), LinkedIn auto, refonte site + SEO.

## 4. Contexte Business
- Menuiserie/pose de châssis, Belgique francophone d'abord puis NL/FR/Europe.
- Fondateur du métier (Michel) → app encode les vraies pratiques chantier (réserve sol, écoinçons, ITE/ITI, seuils).
- Cible : artisans solo + PME de pose (1-20 poseurs). SaaS abonnement web, app = outil terrain.
- Traction : bêta-testeurs, feedback Elcia positif, reco organique ChatGPT constatée.
