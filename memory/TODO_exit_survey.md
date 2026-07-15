# 📝 TODO — Exit Survey (suppression de compte)

**Status** : SPEC VALIDÉE — à implémenter après approbation build 131 par Apple.
**Priorité** : P1 (obligatoire Apple Guideline 5.1.1(v))
**Date spec** : 15 juillet 2026

---

## 🎯 Objectif

Comprendre pourquoi un utilisateur supprime son compte + sauver ~15% des utilisateurs
qui reviennent dans les 30 jours (grace period silencieuse).

---

## Frontend — Écran Réglages > "Supprimer mon compte"

### Modal 1 : Survey (Désolé de vous voir partir...)
- **Titre** : "Désolé de vous voir partir..."
- **Sous-titre** : "Avant de supprimer votre compte, pourriez-vous nous dire pourquoi ?
  Vos retours nous aident énormément à améliorer MesureChâssis pour les autres artisans."
- **Dropdown obligatoire** (6 options exactes) :
  1. C'est trop cher.
  2. L'application est trop compliquée à utiliser.
  3. Je ne trouve pas les fonctionnalités dont j'ai besoin.
  4. Problèmes techniques ou bugs récurrents.
  5. Je n'ai plus besoin de l'outil pour mes chantiers.
  6. Autre (avec champ texte libre qui apparaît UNIQUEMENT si sélectionné).
- **Bouton "Continuer"** désactivé (grisé) tant que dropdown non rempli.

### Modal 2 : Confirmation finale
- **Titre** : "Êtes-vous vraiment sûr ?"
- **Corps** : "Cette action est irréversible. Vos chantiers, mesures et documents
  seront définitivement supprimés dans 30 jours. Vous recevrez un email vous
  permettant de restaurer votre compte pendant cette période."
- **2 boutons** : "Annuler" (défaut) + "Supprimer définitivement" (rouge)

---

## Backend

### Collection MongoDB `account_deletion_surveys`
```json
{
  "_id": ObjectId,
  "user_id": "...",
  "email": "...",
  "reason": "too_expensive | too_complex | missing_features | technical_issues | no_longer_needed | other",
  "custom_text": "..." (uniquement si Autre),
  "plan_at_deletion": "freemium | standard | team | pro",
  "days_since_signup": 42,
  "chantier_count": 3,
  "deletion_requested_at": ISODate,
  "hard_delete_scheduled_at": ISODate (+30j),
  "restored_at": null | ISODate,
  "hard_deleted_at": null | ISODate
}
```

### Endpoint `POST /api/account/delete-with-survey`
1. Valide la raison (enum)
2. Insert dans `account_deletion_surveys`
3. Met à jour l'user : `status = "pending_deletion"`, `pending_deletion_until = now + 30j`
4. Envoie email Resend à `info@mesurechassis.com` :
   - Sujet : `[MesureChâssis] Suppression compte - Raison : {reason_label}`
   - Body : email user + plan + jours d'activité + chantiers + message libre
5. Envoie email Resend à l'utilisateur :
   - Sujet : "Compte MesureChâssis supprimé - vous avez 30 jours pour changer d'avis"
   - Bouton "Restaurer mon compte" avec token signé (30j)
6. Déconnecte l'utilisateur

### Endpoint `GET /api/account/restore?token=...`
- Vérifie token
- Remet `status = "active"`, `pending_deletion_until = null`
- Log dans `account_deletion_surveys.restored_at`
- Redirect vers login

### Job cron quotidien (à ajouter au scheduler existant)
- Query users avec `status = "pending_deletion"` et `pending_deletion_until < now`
- Pour chacun : **hard delete** de toutes ses données (users, chantiers, mesures,
  documents, jetons café, feedbacks, etc.) — RGPD compliant
- Log dans `account_deletion_surveys.hard_deleted_at`

### Vérification à l'auth (login)
- Si `status = "pending_deletion"` → refuser login avec message :
  "Ce compte a été supprimé. Consultez votre email pour le restaurer."

---

## 📊 Analytics pour Michel

Ajouter à `/admin/countdown` ou nouvelle route `/admin/exit-surveys` :
- Nombre de suppressions par période
- Répartition par raison (camembert)
- Top messages libres (mots-clés)
- Taux de restauration (combien changent d'avis dans les 30j)
- Corrélation raison ↔ plan / âge du compte

---

## ✅ Checklist implémentation (à cocher au moment du dev)

- [ ] Modal 1 (Survey) — dropdown + champ conditionnel
- [ ] Modal 2 (Confirmation)
- [ ] Endpoint POST /api/account/delete-with-survey
- [ ] Endpoint GET /api/account/restore
- [ ] Job cron hard delete +30j
- [ ] Guard login pour pending_deletion
- [ ] Email Resend à Michel
- [ ] Email Resend à l'utilisateur (avec token)
- [ ] Page HTML de restauration réussie
- [ ] Écran admin /admin/exit-surveys avec stats
- [ ] Tests : dropdown obligatoire, custom_text si Autre, restauration OK, hard delete OK
