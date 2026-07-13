# 🔒 TODO — Écran TVA obligatoire post-Google Sign-In

**Status** : En attente (Michel a validé l'idée mais préfère finir la campagne
août 2026 avant de le prendre)
**Priorité** : P1 (compliance Apple 3.1.3(c) + Stripe facturation UE)
**Estimation** : ~2h dev + 30 min tests
**Décidé le** : 12 juillet 2026 · **À déclencher** : sur demande explicite Michel

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
