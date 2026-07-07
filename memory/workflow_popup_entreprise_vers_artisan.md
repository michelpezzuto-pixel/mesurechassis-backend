# 💡 Workflow — Pop-up « Vous êtes seul ? Passez en Artisan » (À IMPLÉMENTER)

## Demande utilisateur (07/2026)
Cas fréquent des premiers utilisateurs : à l'inscription, ils choisissent « Entreprise »
sans faire exprès (ou par curiosité), remplissent leurs coordonnées, créent leur premier
chantier… et découvrent qu'ils sont OBLIGÉS d'attribuer le chantier à un commercial
alors qu'ils travaillent seuls.

## Comportement souhaité
1. **Déclencheur** : au moment où un admin en mode Entreprise crée son premier chantier
   et se retrouve face à l'attribution obligatoire à un commercial (et qu'il n'a AUCUN
   commercial dans son équipe → signal fort qu'il est seul).
2. **Pop-up pédagogique** :
   « En mode Entreprise, le concept repose sur 3 rôles : un administrateur, un commercial
   et un technicien. Si vous travaillez seul, nous vous conseillons plutôt le mode Artisan. »
3. **Actions du pop-up** :
   - « Fermer » (il reste en Entreprise)
   - « Passer en Artisan » → redirige vers les paramètres (company-profile → section
     TYPE DE COMPTE, bascule déjà existante) OU bascule directe.
4. **Garantie** : la bascule Entreprise → Artisan conserve les identifiants, les chantiers
   et toutes les données (la bascule existe déjà dans company-profile.tsx).

## Notes techniques
- Condition d'affichage : role=admin + account_type=entreprise + 0 commercial dans l'équipe
  + tentative de création/attribution du 1er chantier. Afficher UNE seule fois
  (flag AsyncStorage `mc.popup.soloEntreprise.shown` ou flag serveur).
- ⚠️ iOS : la bascule Artisan est MASQUÉE sur iOS (App Store 3.1.1 — Build 116).
  Ce pop-up ne doit donc PAS apparaître sur iOS tant que la politique B2B-only iOS est active
  (ou version iOS du pop-up sans mention Artisan).
- La bascule Artisan/Entreprise existe déjà : company-profile.tsx (section TYPE DE COMPTE).

## Statut
- NON DÉMARRÉ — à implémenter après l'approbation Apple.
