# 🔒 TODO — Écran TVA obligatoire post-Google Sign-In

**Status** : ✅ **IMPLÉMENTÉ (juin 2026, session courante) — Prêt à déployer**
**Priorité** : P1 (compliance Apple 3.1.3(c) + Stripe facturation UE)
**Estimation** : ~2h dev + 30 min tests
**Décidé le** : 12 juillet 2026 · **Implémenté le** : juin 2026

---

## 🚨 Problème constaté

Un utilisateur qui se connecte via **Google Sign-In pour la 1ère fois** :

1. Le backend crée une company avec `vat_number: None, vat_country: None`
   (voir `/app/backend/routes/google_auth.py` lignes 106-107)
2. L'utilisateur arrive sur le dashboard **sans jamais avoir renseigné sa TVA**
3. Aucun écran dans l'app ne lui permet de le faire :
   - `/app/frontend/app/company-profile.tsx` (1657 lignes) **ne contient aucun
     champ TVA** (vérifié via `grep -n "TVA\|vat" company-profile.tsx` → 0
     match significatif)
   - `/app/frontend/app/index.tsx` demande la TVA UNIQUEMENT pour l'inscription
     classique email/password (lignes 321-346)

**Conséquences business** :
- 🛡️ Non-compliance Apple Review 3.1.3(c) (modèle B2B européen où l'app
  se réserve aux professionnels avec TVA)
- 💳 Facturation Stripe cassée (TVA UE = obligatoire pour la reverse charge
  et les factures conformes)
- ⚖️ Mentions légales facture incomplètes (SIREN/TVA obligatoires)

---

## 🎯 Solution retenue — Option A « STRICT »

Écran plein écran **obligatoire** au 1er login Google (bloque le dashboard tant
que la TVA n'est pas fournie).

### Backend

1. **Nouvel endpoint** `POST /api/company/complete-signup` — dans
   `/app/backend/routes/company.py` (ou nouveau fichier si absent)

   ```python
   class CompleteSignupPayload(BaseModel):
       vat_number: str
       company_name: str
       # Optionnels (préfill si connu via VIES) :
       vat_country: Optional[str] = None
       address: Optional[str] = None

   @router.post("/company/complete-signup")
   async def complete_signup(payload: CompleteSignupPayload, user=Depends(require_auth)):
       # Vérifier que la TVA n'est pas déjà remplie (idempotence anti-rejeu)
       company = await db.companies.find_one({"company_id": user["company_id"]})
       if company.get("vat_number"):
           raise HTTPException(400, "TVA déjà renseignée. Utilisez le profil société.")

       # Valider via VIES (réutilise vat_validator.py qui existe déjà)
       from services.vat_validator import validate_vat
       result = await validate_vat(payload.vat_number.strip())
       if not result.valid:
           raise HTTPException(400, {"code": "VAT_INVALID", "message": result.message})

       await db.companies.update_one(
           {"company_id": user["company_id"]},
           {"$set": {
               "vat_number": result.normalized,
               "vat_country": result.country_code,
               "vat_verified_at": datetime.utcnow().isoformat(),
               "name": payload.company_name.strip(),
               "address": payload.address,
           }}
       )
       return {"ok": True, "vat_number": result.normalized}
   ```

2. **Nouveau champ user** — `vat_completion_required: bool` (calculé, pas stocké
   en DB) exposé dans le retour `/auth/me` et `/auth/google/session` :

   ```python
   # Dans auth.py, route /auth/me (et google_auth.py, retour du POST session) :
   company = await db.companies.find_one({"company_id": user["company_id"]})
   user_out["vat_completion_required"] = not bool(company.get("vat_number"))
   ```

### Frontend

1. **Nouvel écran** `/app/frontend/app/complete-signup.tsx` (~250 lignes)
   - Composant plein écran avec 2 inputs (TVA + Nom société)
   - Validation live via `POST /auth/validate-vat` (déjà existant, 500ms debounce)
   - Badge vert "✓ Validé (BE0123456789 — Pezzuto SPRL)" une fois vérifié
   - Bouton "VALIDER ET COMMENCER →" désactivé tant que TVA invalide
   - POST vers `/company/complete-signup` puis `router.replace('/dashboard')`
   - **Pas de bouton retour** (verrou total)

2. **Modif `AuthContext.tsx`** — Watcher `vat_completion_required` (~10 lignes)
   ```typescript
   // Nouveau state
   const [vatCompletionRequired, setVatCompletionRequired] = useState(false);

   // Dans signInWithGoogle et fetchCompany, après avoir eu user :
   setVatCompletionRequired(!!user.vat_completion_required);

   // Nouveau writer :
   {user && vatCompletionRequired ? (
     <CompleteSignupScreen onComplete={() => setVatCompletionRequired(false)} />
   ) : (
     children
   )}
   ```
   Positionnement : **AVANT** ValidationRequiredScreen dans le rendu (verrou
   priorité 1).

3. **Modif `company-profile.tsx`** — Ajouter section TVA en lecture seule +
   possibilité de modifier (~50 lignes ajoutées) — mais LOWER PRIORITY que
   les 2 points ci-dessus.

### Tests

- Backend testing_agent : verify `/company/complete-signup` avec TVA valide/invalide/déjà remplie
- Frontend : screenshot du nouvel écran + flow Google → complete-signup → dashboard
- Regression : login classique (email/password) ne doit PAS être impacté

---

## 📁 Fichiers à modifier

| Fichier | Nature | Estim. LOC |
|---|---|---|
| `/app/backend/routes/company.py` (ou similaire) | ADD endpoint | ~40 |
| `/app/backend/routes/auth.py` | ADD field in /me | ~5 |
| `/app/backend/routes/google_auth.py` | ADD field in return | ~3 |
| `/app/frontend/app/complete-signup.tsx` | NEW | ~250 |
| `/app/frontend/src/context/AuthContext.tsx` | Wire verrou | ~15 |
| `/app/frontend/app/_layout.tsx` | Register screen | ~2 |
| `/app/frontend/app/company-profile.tsx` | ADD section TVA (LOW) | ~50 |

---

## 🚦 Comment reprendre

Quand Michel dit « go TVA Google » :

```bash
1. Relire ce fichier
2. Faire les 3 endpoints backend (~30 min)
3. Créer complete-signup.tsx (~1h)
4. Wire AuthContext + _layout (~15 min)
5. Screenshot test + testing_agent backend (~30 min)
6. Commit + finish
```

Total : ~2h30 max. Aucune dépendance externe, tout le code VIES existe déjà
côté backend.

---

## ✅ Récap implémentation (juin 2026)

**Backend** :
- `models.py` : `UserPublic.vat_completion_required: Optional[bool] = None`
- `deps.py` : helper `user_needs_vat_completion(user, company)` + set
  `VAT_CHECK_EXEMPT_EMAILS = PLATFORM_OWNER_EMAILS ∪ {applereview,
  admin@mesurechassis.fr}` pour bypass des comptes techniques.
- `auth.py` : `/auth/me` calcule dynamiquement le flag.
- `google_auth.py` : `/auth/google/session` calcule dynamiquement le flag.
- `company.py` : nouveau endpoint `POST /api/company/complete-signup`
  (validation VIES + idempotence anti-rejeu + skip_vies pour Apple Review).

**Frontend** :
- Nouveau composant `src/components/CompleteVatScreen.tsx` (verrou plein
  écran, validation VIES en direct avec debounce 500ms).
- `AuthContext.tsx` : `User.vat_completion_required?: boolean` + rendu
  conditionnel `CompleteVatScreen` juste après `PaywallScreen` (priorité
  MAX, avant `ValidationRequiredScreen`).

**Tests** : 24/24 passent (14 fonctionnels + 10 bypass), fichiers
`test_vat_completion_lock.py` et `test_vat_bypass_iter35.py`.

**Comptes bypassés** (voir résultat sur `/auth/me`) :
- artisan@mesurechassis.fr (owner plateforme)
- admin@mesurechassis.fr (super admin)
- applereview@mesurechassis.com (Apple Review)
- Tous les autres emails dans `PLATFORM_OWNER_EMAILS`

---

## 🚧 Améliorations reportées à la PROCHAINE mise à jour (décidées juin 2026)

Michel a validé la mise en prod du verrou TVA MVP (v1.0.27) tel quel. Les
3 améliorations suivantes seront regroupées dans un futur build unique,
APRÈS avoir observé si des users Google existants tombent sur le verrou :

### 1. 📧 Email proactif Resend aux users Google existants
Avant le déclenchement du verrou, envoyer un email :
- Sujet : « Mise à jour MesureChâssis — numéro de TVA (ou SIREN/SIRET) requis »
- Corps : explique la nouvelle exigence légale Apple/UE, prépare le user
  à saisir sa TVA ou son SIREN/SIRET au prochain lancement.
- Query cible :
  ```python
  await db.users.find({
      "google_linked": True,
      "email": {"$nin": list(VAT_CHECK_EXEMPT_EMAILS)},
  })
  ```
  puis filtrer sur `company.vat_number` absent.

### 2. 🆔 Fallback SIREN/SIRET/BCE pour auto-entrepreneurs
Certains artisans sont **légalement sans TVA** :
- 🇫🇷 France : auto-entrepreneurs (franchise en base <36 800 € en 2026)
- 🇧🇪 Belgique : régime de la franchise TVA (<25 000 €)
- 🇱🇺 Luxembourg : franchise <35 000 €

Bloquer strictement sur la TVA = les exclure. Solution :
- Dans `CompleteVatScreen`, ajouter un toggle « Je n'ai pas de TVA
  (auto-entrepreneur / franchise) » qui bascule sur un input SIREN
  (FR) / SIRET / BCE (BE) / autre identifiant national.
- Backend : `POST /company/complete-signup` accepte soit `vat_number`
  soit `national_id` (SIREN, SIRET, BCE) avec validation format
  minimale par pays.
- Nouveaux champs company : `national_id`, `national_id_type`
  (`siren` | `siret` | `bce` | `other`), `has_vat: bool`.
- Facturation Stripe : marquer `automatic_tax=false` pour ces users
  (pas de TVA à collecter).

### 3. ✨ Message adouci pour les comptes existants
Différencier UI selon l'ancienneté du compte dans `CompleteVatScreen` :
- **Comptes < 24h** (nouveaux Google signup) : garder « Une dernière
  étape · Bienvenue » actuel.
- **Comptes existants** : bandeau « ✨ Mise à jour légale » + titre
  « Complétez votre profil pour continuer » + phrase rassurante
  « Vos chantiers, mesures et factures restent intacts. »

Détection : `user.created_at < now - 24h` (exposer `created_at` dans
`/auth/me` si pas déjà fait).

### 📋 Séquence recommandée pour la prochaine version
1. Coder l'email Resend + endpoint admin déclenchable manuellement
2. Coder le fallback SIREN/SIRET (backend + frontend)
3. Adoucir le message dans `CompleteVatScreen`
4. Michel déclenche l'email de com **J-3** avant push Railway
5. Push Railway + rebuild mobile (bundle 1 seule fois)
