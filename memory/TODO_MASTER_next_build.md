# 🚀 TODO MAÎTRE — Prochain Build Unifié MesureChâssis

**Version cible** : v1.1.0 (rupture mineure car Sign in with Apple)
**Date de création** : 15 juillet 2026
**Estimation totale** : ~11-13h dev + 2h tests = **~15h** (2 sessions)
**Status** : Spec validée, en attente du feu vert Michel pour démarrer

---

## 🎯 Objectif de ce build

Regrouper toutes les améliorations en attente en UNE seule livraison Apple
pour :
- Éviter les multiples cycles de review (24-48h par soumission)
- Assurer la compliance Apple (Guideline 4.8 obligatoire)
- Offrir une expérience utilisateur cohérente

---

## 📋 Priorisation

| # | Feature | Priorité | Effort | Fichier détail |
|---|---|---|---|---|
| 1 | **Sign in with Apple + refonte écran Bienvenue** | 🔴 **P0** | 3h | Ci-dessous |
| 2 | Exit Survey + Grace Period 30j | 🔴 P0 | 3h | `TODO_exit_survey.md` |
| 3 | Fallback SIREN/SIRET auto-entrepreneurs | 🟠 P1 | 1h | `TODO_vat_google_signin.md` |
| 4 | Email proactif Resend users Google | 🟠 P1 | 30min | `TODO_vat_google_signin.md` |
| 5 | ~~Force update (style Revolut)~~ ✅ **FAIT en v1.1.3** | ~~🟠 P1~~ | ~~2h~~ | `TODO_force_update.md` + `GUIDE_notifications_maj_app.md` |
| 6 | Message adouci verrou TVA | 🟡 P2 | 15min | `TODO_vat_google_signin.md` |
| 7 | Carte admin dans l'app | 🟢 P2 | 30min | `TODO_carte_admin_mobile.md` |

**Total estimé** : ~11h dev + ~2h tests + review = **13h** (répartissable sur 2 sessions)

---

## 🍎 [1] Sign in with Apple + Refonte écran Bienvenue

### 🚨 Pourquoi c'est P0 CRITIQUE

Apple **Guideline 4.8** impose Sign in with Apple si Google Sign-In est
présent. MesureChâssis actuellement en **non-conformité** → risque de rejet
au prochain build submis. **SIWA est gratuit, aucun lien avec les commissions
Apple (IAP).**

### Backend

**Nouvel endpoint** `POST /api/auth/apple/session`
```python
class AppleSessionPayload(BaseModel):
    identity_token: str  # JWT Apple signé
    authorization_code: str
    email: Optional[str] = None  # Apple ne le renvoie qu'à la 1ère connexion
    full_name: Optional[dict] = None  # Idem
    station_id: Optional[str] = None  # Campagne Jeton Café
```

**Logique** :
1. Vérifier `identity_token` via clés publiques Apple (jwks Apple)
2. Extraire `sub` (Apple user ID stable) et `email` (peut être relais privé
   `xxxxx@privaterelay.appleid.com`)
3. Upsert user par email (comme Google), **mais** stocker aussi `apple_sub`
   pour retrouver les comptes anonymes ré-utilisant l'email relais
4. Émettre JWT applicatif
5. Réponse identique à `/auth/google/session` avec `vat_completion_required`

**Bibliothèques Python** : `python-jose[cryptography]` + `httpx` pour fetcher
les clés publiques Apple.

**Cas particulier email relais Apple** :
- L'utilisateur peut choisir "Cacher mon adresse email"
- Apple renvoie alors `xxxxx@privaterelay.appleid.com`
- Nos emails (Resend) sont **automatiquement forwarded** par Apple vers son
  vrai email — on n'a rien à faire de spécial

### Frontend

**Installation** :
```bash
cd /app/frontend && yarn expo install expo-apple-authentication
```

**Nouveau composant** `src/components/AppleSignInButton.tsx` :
```typescript
import * as AppleAuthentication from "expo-apple-authentication";

const handleAppleSignIn = async () => {
  const credential = await AppleAuthentication.signInAsync({
    requestedScopes: [
      AppleAuthentication.AppleAuthenticationScope.FULL_NAME,
      AppleAuthentication.AppleAuthenticationScope.EMAIL,
    ],
  });
  await signInWithApple({
    identity_token: credential.identityToken,
    authorization_code: credential.authorizationCode,
    email: credential.email,
    full_name: credential.fullName,
  });
};
```

**Modif `AuthContext.tsx`** :
- Ajouter `signInWithApple(payload)` sur le même modèle que
  `signInWithGoogle`.

**Refonte `/app/frontend/app/index.tsx`** (écran Bienvenue) :

Design inspiré de Base :
```
┌────────────────────────────────────┐
│                                    │
│     Bienvenue sur MesureChâssis    │
│                                    │
│     L'app B2B des menuisiers pros  │
│                                    │
│                                    │
│          🍎           G            │  ← 2 boutons ronds (60x60px)
│                                    │
│                                    │
│    ┌─────────────────────────┐     │
│    │ Continuer avec un e-mail│     │  ← pill orange
│    └─────────────────────────┘     │
│                                    │
│    Déjà un compte ? Se connecter   │
│                                    │
└────────────────────────────────────┘
```

**Ordre imposé par Apple** : Apple à gauche, Google à droite.
**iOS uniquement** : le bouton Apple ne s'affiche pas sur Android via
`Platform.OS === "ios"`.

### `app.json`

Ajouter le plugin :
```json
{
  "expo": {
    "plugins": [
      "expo-apple-authentication"
    ]
  }
}
```

### Tests

- [ ] Sign in with Apple sur simulateur iOS (Xcode)
- [ ] Sign in avec email relais Apple → vérifier réception emails Resend
- [ ] Reconnexion après logout → pas de doublon en DB
- [ ] Bouton Apple absent sur Android
- [ ] Guideline 4.8 respecté (audit visuel)

---

## 🚪 [2] Exit Survey + Grace Period 30 jours

**Détail complet** : `TODO_exit_survey.md`

### Résumé
- Modal survey obligatoire avec dropdown 6 raisons + champ libre si "Autre"
- Modal confirmation "Êtes-vous vraiment sûr ?"
- Endpoint `POST /account/delete-with-survey`
- Endpoint `GET /account/restore?token=...`
- Job cron J+30 → hard delete RGPD
- Guard login pour `status = pending_deletion`
- Email Resend vers `suppressions@mesurechassis.com` ✅ (alias créé)
- Email vers l'utilisateur avec token de restauration
- Écran admin HTML `/admin/exit-surveys` (stats + camembert raisons)

### Checklist rapide
- [ ] Collection MongoDB `account_deletion_surveys`
- [ ] Modal 1 (Survey) — dropdown + champ conditionnel
- [ ] Modal 2 (Confirmation)
- [ ] POST /api/account/delete-with-survey
- [ ] GET /api/account/restore?token=
- [ ] Job cron hard delete J+30
- [ ] Guard login pending_deletion
- [ ] Emails Resend (admin + user)
- [ ] Page HTML restauration réussie
- [ ] Dashboard admin /admin/exit-surveys

---

## 🆔 [3] Fallback SIREN / SIRET / BCE pour auto-entrepreneurs

**Détail complet** : `TODO_vat_google_signin.md`

### Résumé
Certains artisans sont légalement sans TVA :
- 🇫🇷 France : auto-entrepreneurs (franchise <36 800 €)
- 🇧🇪 Belgique : franchise TVA (<25 000 €)
- 🇱🇺 Luxembourg : franchise (<35 000 €)

### Ce qu'il faut faire
- Toggle "Je n'ai pas de TVA (auto-entrepreneur)" dans `CompleteVatScreen`
- Input alternatif SIREN (9 chiffres FR) / SIRET (14 chiffres FR) / BCE
  (10 chiffres BE)
- Endpoint `POST /company/complete-signup` accepte `national_id` OU
  `vat_number` (au moins un des deux)
- Nouveaux champs `company` : `national_id`, `national_id_type`
  (`siren` | `siret` | `bce` | `other`), `has_vat: bool`
- Ajustement Stripe : `automatic_tax=false` sur ces comptes

### Validation format
- SIREN : `^\d{9}$` — algorithme Luhn en bonus
- SIRET : `^\d{14}$`
- BCE : `^\d{10}$`

### Checklist
- [ ] Backend : accepter `national_id` en payload complete-signup
- [ ] Validation format par type (helper `validate_national_id`)
- [ ] Migration `has_vat` sur toutes les companies existantes
- [ ] Frontend : toggle + input adaptatif dans CompleteVatScreen
- [ ] Frontend : validation live selon le type
- [ ] Adapter Stripe checkout selon `has_vat`

---

## 📧 [4] Email proactif Resend aux users Google existants

**Détail complet** : `TODO_vat_google_signin.md`

### Résumé
Prévenir les users Google existants **avant** le push de la nouvelle version
(3 jours avant idéalement) qu'ils devront saisir leur TVA/SIREN au prochain
lancement.

### Contenu email
- **Sujet** : "Mise à jour importante — Votre TVA sera bientôt requise"
- **Corps** :
  - Explique la nouvelle règle Apple 3.1.3(c)
  - Rassure : "Vos chantiers restent intacts"
  - Précise que SIREN/SIRET fonctionne aussi pour les auto-entrepreneurs
  - CTA : "Ouvrir l'app pour saisir ma TVA dès maintenant"
- **Signature** : "L'équipe MesureChâssis"

### Cible
```python
users_to_notify = db.users.find({
    "google_linked": True,
    "email": {"$nin": list(VAT_CHECK_EXEMPT_EMAILS)},
})
# Filtrer côté Python sur company.vat_number absent
```

### Déclenchement
- **Endpoint admin** `POST /admin/campaigns/notify-vat-required`
  (require_platform_owner)
- Michel le déclenche manuellement 3 jours avant le push Railway
- Anti-spam : flag `notified_vat_required_at` sur user

### Checklist
- [ ] Endpoint admin déclencheur
- [ ] Template HTML Resend
- [ ] Query cible (Google users sans TVA, hors exempt)
- [ ] Flag anti-spam
- [ ] Compteur envoyés/échoués retourné en réponse

---

## 🔄 [5] Force Update (style Revolut)

**Détail complet** : `TODO_force_update.md`

### Résumé
Système pour forcer les users à mettre à jour l'app quand une version est
obsolète. 2 niveaux :
1. **Version < min_version** → écran plein écran bloquant "Mise à jour requise"
2. **Version < latest_version** → bannière dismissable "Nouvelle version dispo"

### Backend
- `GET /config/app-version` (public) — retourne min/latest/force_update
- Variables Railway : `APP_MIN_VERSION`, `APP_LATEST_VERSION`,
  `APP_FORCE_UPDATE`, `APP_UPDATE_MESSAGE`
- Tracking `last_app_version` sur user via header `X-App-Version`
- Job cron quotidien email Resend aux users obsolètes (anti-spam 7j)

### Frontend
- Service `src/services/appVersion.ts` avec comparaison sémantique
- Composant `ForceUpdateScreen.tsx` (verrou plein écran)
- Composant `UpdateAvailableBanner.tsx` (bannière dismissable)
- Wire dans `AuthContext.tsx` (priorité MAX, avant tous les autres verrous)
- Interceptor Axios pour header `X-App-Version`

### Checklist
- [ ] Endpoint /config/app-version
- [ ] Variables Railway
- [ ] Tracking last_app_version
- [ ] Cron notify obsolete users
- [ ] Service appVersion.ts
- [ ] ForceUpdateScreen.tsx
- [ ] UpdateAvailableBanner.tsx
- [ ] Wire AuthContext
- [ ] Interceptor Axios
- [ ] Écran admin /admin/versions (HTML tableau users par version)

---

## ✨ [6] Message adouci verrou TVA pour comptes existants

**Détail complet** : `TODO_vat_google_signin.md`

### Résumé
Différencier l'UX de `CompleteVatScreen` selon l'ancienneté du compte.

### Comptes < 24 h (nouveaux Google signup)
Titre actuel conservé :
> "Une dernière étape · Bienvenue"
> "Pour activer votre compte, indiquez votre TVA..."

### Comptes existants (> 24h)
Bandeau bleu "✨ Mise à jour légale" + titre :
> "Complétez votre profil pour continuer"
> "Vos chantiers, mesures et factures restent intacts. Nous vous demandons
> juste de renseigner votre numéro de TVA (ou SIREN/SIRET si vous êtes
> auto-entrepreneur) pour être en conformité avec les règles Apple et de
> facturation UE."

### Détection
- Exposer `created_at` dans `/auth/me` (déjà en DB, il suffit de l'ajouter au
  serializer `user_to_public`)
- Frontend : `isExistingUser = Date.now() - Date.parse(user.created_at) > 86400000`

### Checklist
- [ ] Ajouter `created_at` au modèle Pydantic `UserPublic`
- [ ] Frontend : prop `isExistingUser` calculée dans AuthContext
- [ ] Deux variantes de textes dans `CompleteVatScreen`
- [ ] Bandeau "Mise à jour légale" si comptes existants

---

## 🗺️ [7] Carte admin des inscrits dans l'app

**Détail complet** : `TODO_carte_admin_mobile.md`

### Résumé
Ajouter un bouton "🗺️ Carte des inscrits" dans l'écran admin qui ouvre la
carte HTML Leaflet dans le navigateur du téléphone via `Linking.openURL()`.

### Backend
- `POST /admin/map/access-link` (require_platform_owner) → génère un JWT
  temporaire (5 min TTL) avec scope=admin_map
- Modifier `_check_token()` pour accepter aussi `?jwt=<token>` en plus de
  `?token=PLATFORM_ADMIN_TOKEN`

### Frontend
- Bouton dans écran admin (visible uniquement pour PLATFORM_OWNER_EMAILS)
- Au clic → API call → `Linking.openURL(url)` → navigateur affiche la carte

### Checklist
- [ ] Endpoint /admin/map/access-link
- [ ] Modif _check_token pour JWT scope=admin_map
- [ ] Bouton dans écran admin
- [ ] Guard visibilité platform_owner
- [ ] Test lien expiré → 403

---

## 📅 Planning d'exécution recommandé

### Session 1 (~7h) — Compliance et sécurité
1. Sign in with Apple + refonte écran Bienvenue (3h)
2. Force Update (2h)
3. Fallback SIREN/SIRET (1h)
4. Message adouci verrou TVA (15min)
5. Tests session 1 (45min)

**Publication interne v1.1.0-beta pour test Michel**

### Session 2 (~6h) — Suppression compte et outils admin
1. Exit Survey backend + frontend (3h)
2. Email proactif Resend + endpoint admin (30min)
3. Carte admin dans l'app (30min)
4. Tests testing_agent (1h)
5. Ajustements + review (1h)

**Publication v1.1.0 App Store**

---

## 🚦 Séquence de déploiement finale

1. ✅ Code merged sur `conflict_070626_1317`
2. ✅ Force push GitHub → Railway auto-deploy
3. ✅ Config Railway : variables `APP_MIN_VERSION`, `APP_LATEST_VERSION`, etc.
4. 📧 Michel déclenche l'email proactif Resend (J-3)
5. 📱 Build mobile v1.1.0 via Emergent Publish
6. 🍎 Submit for Review App Store (24-48h)
7. 👀 Une fois approuvé : release + monitoring 1 semaine

---

## ⚠️ Points de vigilance

### Compliance Apple 4.8
🚨 Sign in with Apple est **OBLIGATOIRE** dès qu'un login social tiers est
proposé. À faire **AVANT** toute autre soumission Apple.

### Apple Review — Comptes de test
Le compte `applereview@mesurechassis.com` doit être testé avec :
- Login classique email/password ✅
- Login Google ✅
- Login Apple (nouveau) — à valider

### Backward compatibility
Les users existants ne doivent pas être cassés. Toutes les nouvelles features
sont **additives**, pas destructives. Le verrou TVA existe déjà mais accepte
maintenant SIREN/SIRET en fallback.

### Timing envoi email proactif
Envoyer l'email J-3 **avant** que Michel push Railway → users préparés à la
nouvelle exigence lors du prochain lancement de l'app.

---

## 📝 Fichiers TODO liés (à lire pour les détails)

- `/app/memory/TODO_exit_survey.md`
- `/app/memory/TODO_vat_google_signin.md`
- `/app/memory/TODO_force_update.md`
- `/app/memory/TODO_carte_admin_mobile.md`

## 📝 Fichiers info liés

- `/app/memory/MEMO_metriques_dashboard.md` — comment Michel voit ses inscrits
- `/app/memory/KIT_CAPCUT_video_demo.md` — kit vidéo marketing (non lié au build)
