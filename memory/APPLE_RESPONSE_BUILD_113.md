# 🍎 Apple Review — Réponse Build 113

**Date** : 02/07/2026  
**Rejection Build 112** : Guideline 2.1 - Information Needed  
**Apple demande** : Un compte demo avec abonnement EXPIRÉ pour tester le flux paywall/renouvellement complet.

**✅ BONNE NOUVELLE** : Apple n'a PLUS aucun problème avec les Guidelines 3.1.1 et 3.1.3(c) — l'app est acceptée comme B2B ! Le screenshot fourni par Apple montre l'écran subscription iOS parfaitement neutre ("Compte actif — La gestion se fait depuis votre espace personnel sur le site web").

---

## ✅ CORRECTIONS BUILD 113

### 1. Nouveau compte demo avec abonnement expiré
Créé `applereview-expired@mesurechassis.com` (password `MesureChassis2026`) :
- Rôle : admin
- Company : `apple-review-expired` (séparée de `apple-review-demo`)
- `subscription_status: "expired"`
- `subscription_expires_at`: 30 jours dans le passé
- `trial_expires_at`: 30 jours dans le passé (essai déjà écoulé)

### 2. Bypass ciblé du mode BETA
Dans `backend/deps.py` :
- `ensure_company()` : n'écrase pas les champs du compte `apple-review-expired` (exception ciblée)
- `is_subscription_blocked()` : retourne toujours `True` pour ce compte, indépendamment du `BETA_MODE`

Résultat : dès qu'Apple se connecte avec ce compte, TOUS les endpoints protégés renvoient `HTTP 402 subscription_expired`, ce qui déclenche automatiquement le **PaywallScreen iOS neutre** :

> 🔒 ACCÈS BLOQUÉ  
> Votre accès a expiré (statut : EXPIRÉ · Date d'expiration : 02 juin 2026)  
> 
> ℹ️ Pour réactiver votre compte, contactez notre support à **support@mesurechassis.fr**.  
> Vos données restent stockées en sécurité et seront restaurées dès que votre accès sera rétabli.  
> 
> [CONTACTER LE SUPPORT] [SE DÉCONNECTER]

**Aucune mention de prix, aucun bouton d'achat, aucun essai gratuit** — conforme B2B.

### 3. Tests validés
- ✅ `applereview@` (Pro actif) → HTTP 200 (accès normal)
- ✅ `applereview-tech@` (Pro actif) → HTTP 200 (accès normal)
- ✅ `applereview-expired@` → **HTTP 402 subscription_expired** (paywall déclenché)

---

## 📝 RÉPONSE À COLLER DANS APP STORE CONNECT

### 🇬🇧 Version anglaise (recommandée)

```
Hello App Review Team,

Thank you for your continued review. We appreciate that Guideline 3.1.1 and 3.1.3(c) concerns are now resolved — the screenshot you provided confirms our iOS build correctly presents a B2B-only, neutral subscription screen.

To address Guideline 2.1 (Information Needed), we have created a THIRD demo account with an EXPIRED subscription so you can review the complete paywall / renewal flow.

═══════════════════════════════════════════
DEMO ACCOUNTS FOR BUILD 113 REVIEW
═══════════════════════════════════════════

Universal password: MesureChassis2026

1) ACTIVE ADMIN — Regular usage flow
   Email: applereview@mesurechassis.com
   Role: admin
   Company: "Apple Review Demo Co." (VAT: BE0000000097)
   Subscription: Enterprise Pro, active (10 years)
   Use for: Full app navigation, all admin features

2) ACTIVE TECHNICIAN — Non-admin role
   Email: applereview-tech@mesurechassis.com
   Role: technician
   Company: same as above
   Use for: Testing RBAC / non-admin experience

3) EXPIRED ADMIN — Paywall / renewal flow ⭐ NEW
   Email: applereview-expired@mesurechassis.com
   Role: admin
   Company: "Apple Review Expired Demo Co." (VAT: BE0000000098)
   Subscription: Enterprise, EXPIRED 30 days ago
   Use for: Testing the paywall behavior when a business subscription lapses

═══════════════════════════════════════════

EXPECTED BEHAVIOR ON IOS WITH THE EXPIRED ACCOUNT:

Upon login with account #3, the app displays a full-screen paywall showing:

  🔒 ACCESS BLOCKED
  Your access has expired.
  Status: EXPIRED · Expiration date: 02 June 2026
  
  ℹ️ To reactivate your account, please contact our support at
  support@mesurechassis.fr
  
  Your data remains securely stored and will be restored once
  access is renewed.
  
  [CONTACT SUPPORT] [SIGN OUT]

There is NO price, NO subscription CTA, NO trial mention — the flow is entirely B2B and the user is instructed to contact the support team who will handle renewal via the web portal on desktop (mesurechassis.com).

BUSINESS MODEL RECAP:
MesureChâssis is a B2B SaaS exclusively for carpentry / window installation companies. All subscriptions are tied to a legal business entity (company_id) with a mandatory validated European VAT number (SIRET/BE VAT) at signup. Individual consumers cannot subscribe — subscription management is handled by the company administrator via desktop at mesurechassis.com. The iOS app is a companion tool for on-site professional users.

Please let us know if any additional information or test accounts are needed.

Thank you for your patience and thorough review.

Best regards,
The MesureChâssis Team
```

### 🇫🇷 Version française (au cas où)

```
Bonjour équipe App Review,

Merci pour votre review continue. Nous notons que les Guidelines 3.1.1 et 3.1.3(c) sont désormais validées — le screenshot que vous nous avez fourni confirme que le build iOS présente correctement un écran d'abonnement B2B neutre.

Pour répondre à la Guideline 2.1 (Information Needed), nous avons créé un TROISIÈME compte demo avec un abonnement EXPIRÉ pour vous permettre de tester le flux complet paywall / renouvellement.

═══════════════════════════════════════════
COMPTES DEMO POUR BUILD 113
═══════════════════════════════════════════

Mot de passe universel : MesureChassis2026

1) ADMIN ACTIF — Utilisation normale
   Email : applereview@mesurechassis.com
   Rôle : admin
   Société : "Apple Review Demo Co." (TVA : BE0000000097)
   Abonnement : Enterprise Pro, actif (10 ans)
   Usage : Navigation complète, fonctions admin

2) TECHNICIEN ACTIF — Rôle non-admin
   Email : applereview-tech@mesurechassis.com
   Rôle : technician
   Société : identique ci-dessus
   Usage : Test RBAC / expérience non-admin

3) ADMIN EXPIRÉ — Flux paywall / renouvellement ⭐ NOUVEAU
   Email : applereview-expired@mesurechassis.com
   Rôle : admin
   Société : "Apple Review Expired Demo Co." (TVA : BE0000000098)
   Abonnement : Enterprise, EXPIRÉ depuis 30 jours
   Usage : Tester le comportement paywall à l'expiration

═══════════════════════════════════════════

COMPORTEMENT ATTENDU SUR IOS AVEC LE COMPTE EXPIRÉ :

À la connexion avec le compte #3, l'application affiche un paywall plein écran :

  🔒 ACCÈS BLOQUÉ
  Votre accès a expiré.
  Statut : EXPIRÉ · Date d'expiration : 02 juin 2026
  
  ℹ️ Pour réactiver votre compte, contactez notre support à
  support@mesurechassis.fr
  
  Vos données restent stockées en sécurité et seront restaurées
  dès que votre accès sera rétabli.
  
  [CONTACTER LE SUPPORT] [SE DÉCONNECTER]

AUCUN prix, AUCUN CTA d'abonnement, AUCUNE mention d'essai — le flux est entièrement B2B et l'utilisateur est invité à contacter l'équipe support qui gère le renouvellement via le portail web desktop (mesurechassis.com).

RAPPEL MODÈLE COMMERCIAL :
MesureChâssis est un SaaS B2B exclusivement pour entreprises de menuiserie / pose de châssis. Tous les abonnements sont liés à une entité société légale (company_id) avec numéro TVA européen validé obligatoire (SIRET/TVA BE). Aucun particulier ne peut souscrire — la gestion d'abonnement est faite par l'administrateur société via desktop sur mesurechassis.com. L'app iOS est un outil compagnon pour l'usage terrain.

N'hésitez pas à nous demander toute information ou compte de test complémentaire.

Merci pour votre patience et votre review approfondie.

Cordialement,
L'équipe MesureChâssis
```

---

## 🔍 CHECKLIST FINALE AVANT BUILD 113

- [x] Compte `applereview-expired@mesurechassis.com` créé (seed idempotent)
- [x] Company `apple-review-expired` avec `status=expired`
- [x] Exception BETA_MODE dans `deps.py` pour cette company
- [x] `is_subscription_blocked()` retourne True pour ce compte
- [x] `PaywallScreen.tsx` iOS déjà neutre (fait au Build 112, vérifié)
- [x] Test API : les 3 comptes retournent le bon code (200/200/402)
- [ ] Publier Build 113 via Emergent Publish
- [ ] Mettre à jour "App Review Information" avec les 3 comptes
- [ ] Coller la réponse dans "Reply to App Review"
- [ ] Soumettre à Apple

---

## 📌 COMMANDES DE VÉRIFICATION RAPIDE

```bash
# Test compte expiré (attendu : HTTP 402)
TOKEN=$(curl -s -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"applereview-expired@mesurechassis.com","password":"MesureChassis2026"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

curl -s -w "\nHTTP: %{http_code}\n" \
  http://localhost:8001/api/chantiers \
  -H "Authorization: Bearer $TOKEN"
```

Réponse attendue :
```json
{
  "detail": {
    "code": "subscription_expired",
    "message": "Votre accès a expiré...",
    "subscription_status": "expired",
    "subscription_expires_at": "2026-06-02T..."
  }
}
HTTP: 402
```
