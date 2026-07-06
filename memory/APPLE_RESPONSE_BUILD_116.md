# Build 116 — Correctif rejet Apple 3.1.1 / 3.1.3(c) (Build 115)

## Rejet Apple (06/07/2026)
« Enterprise services also available to be sold to single users/consumers without IAP. »
Apple a vu sur iOS : prix des sièges (€4,99) dans la carte Getting Started, compte « Artisan »
(offre solo), section « Mon abonnement », FAQ avec tarifs des formules.

## Stratégie retenue (choix utilisateur : « supprimer tout ce qui touche au paiement »)
iOS = app 100 % B2B, ZÉRO mention de prix / essai / abonnement / offre individuelle.
Android + web conservent tout (prix, formules, parrainage).

## Correctifs appliqués (06/07/2026)
1. **i18n (fr/en/nl)** : carte « Getting started » — suppression des phrases
   « siège offert avec l'essai » et « chaque siège = 4,99 €/mois » (TOUTES plateformes).
2. **company-profile.tsx** : sections « TYPE DE COMPTE » (bascule Artisan) et
   « MON ABONNEMENT » entièrement masquées sur iOS.
3. **admin/team.tsx** : modal supplément de siège → version iOS neutre
   (« contactez info@mesurechassis.com »), sans prix ni confirmation d'achat.
4. **me.tsx** : carte Parrainage masquée sur iOS + description Aide sans « formules ».
5. **FilleulInviteBanner.tsx** : null sur iOS (récompense = crédit d'abonnement).
6. **referral.tsx** : redirection /dashboard sur iOS.
7. **ChatHelp.tsx (FAQ)** : filtrage sur iOS de toute entrée contenant
   €/formule/abonnement/tarif/prix.
8. Déjà propres avant : inscription (login-only iOS), PaywallScreen (contact support),
   yann.tsx, subscription.tsx (bloc prix non-iOS), bannières trial (null iOS), PremiumLockModal.

## 🔐 BONUS — Outils internes verrouillés (faille confidentialité + risque Apple)
Les boutons/APIs « Campagne » (prospection Resend), « LinkedIn » et « Testeurs » étaient
accessibles à TOUT admin client (y compris le reviewer Apple !).
- **backend/deps.py** : nouveau `require_platform_owner` (env `PLATFORM_OWNER_EMAILS`,
  défaut : info@mesurechassis.com, michelpezzuto@hotmail.com, michelpezzuto@gmail.com).
- **routes campaign.py / linkedin.py / testers.py** : `require_admin` → `require_platform_owner`.
- **dashboard.tsx** : boutons visibles uniquement pour `isPlatformOwner`.
- Vérifié : admin client → 403 sur /api/campaign/* et /api/linkedin/*, 200 sur /api/chantiers.
- ⚠️ Si l'utilisateur perd son bouton Campagne : ajouter son email à PLATFORM_OWNER_EMAILS.

## Validation
- Web smoke test : dashboard admin client sans Campagne/LinkedIn, Getting started sans prix. ✅
- Backend curl : 403/403/200. ✅
- Branches iOS = guards Platform.OS simples (non testables sur web preview).

## Statut
- Correctifs prêts. L'utilisateur doit : 1) Republier le backend (Publish),
  2) Générer le Build 116 et le soumettre à Apple.
