# 🔒 Démo Châssis Prime — Guide de protection

## 📁 Fichiers

| Fichier | Rôle |
|---|---|
| `index.html` | La démo protégée à présenter au client |
| `MESSAGE_CLIENT_APPEL_OFFRES.md` | Le message à envoyer au client pour l'appel d'offres public |
| `README_PROTECTION.md` | Ce fichier |

---

## 🛡️ Protections mises en place dans `index.html`

### ✅ Contre la copie de code
- **Meta tag `noindex,nofollow,noarchive`** → Google/Bing ne peuvent pas indexer le site
- **Meta `Cache-Control: no-store`** → Les CDN/proxys ne peuvent pas cacher le fichier
- **Meta `author` + `copyright`** → Signature dans le code
- **Clic droit désactivé** → Impossible d'ouvrir "Voir source" via le menu
- **Raccourcis clavier bloqués** :
  - `F12` (DevTools)
  - `Ctrl+Shift+I / J / C / K` (Inspecteur)
  - `Ctrl+U` (Voir source)
  - `Ctrl+S` (Enregistrer)
  - `Ctrl+P` (Imprimer)
  - `Ctrl+A` (Tout sélectionner — sauf champs de formulaire)

### ✅ Contre la copie de contenu
- **`user-select: none`** sur tout le site (sauf inputs/textareas)
- **Événement `copy` intercepté** → Si l'utilisateur réussit à copier, il colle le message : *"© Démo confidentielle Michel Guillaume — Contact : michel@mesurechassis.com"*
- **Drag & drop d'images désactivé** → Impossible de glisser une image vers le bureau

### ✅ Contre l'inspection technique
- **Détection DevTools par heuristique** (différence outerWidth/innerWidth) → Si l'inspecteur est ouvert, un overlay bleu marine + or plein écran masque tout le contenu et affiche : *"🔒 Démo confidentielle — Propriété exclusive de Michel Guillaume"*
- **Console warning** → Un message stylé apparaît dans la console si le client l'ouvre

### ✅ Contre l'impression
- **`@media print`** → Toute tentative d'impression affiche uniquement le message : *"⛔ Impression et enregistrement interdits — Démo confidentielle réalisée par Michel Guillaume"*

### ✅ Watermarks visibles
- **Watermark diagonal** en fond de page (opacité 3,5 %) répétant "DÉMO CONFIDENTIELLE · MICHEL GUILLAUME · MESURECHÂSSIS · NE PAS REPRODUIRE"
- **Bandeau fixe en bas d'écran** : *"🔒 Démo confidentielle · Maquette réalisée sur mesure par Michel Guillaume (MesureChâssis) pour Châssis Prime · Reproduction, copie et redistribution interdites"*

---

## ⚠️ Limites (à comprendre avant d'envoyer)

Un HTML servi par navigateur **reste techniquement téléchargeable** par un développeur déterminé (ouvrir un onglet privé sans JS activé, ou utiliser `curl`/`wget`). Les protections ci-dessus **découragent 99 % des tentatives**, mais elles ne sont pas absolues.

**Ce qui les rend efficaces dans TON contexte** :
1. Le client n'est pas un développeur → il ne connaît pas ces contournements
2. Même s'il transmet le lien à un dev, celui-ci verra immédiatement les watermarks + copyright → **preuve légale** que le code n'est pas libre d'utilisation
3. Le bandeau permanent en bas d'écran + le blur en cas d'inspection = **très inconfortable** pour tenter quoi que ce soit sans que ça se voie
4. Le message "Ne pas reproduire" est intégré dans les meta-tags → visible dans TOUTE tentative d'extraction

---

## 🚀 Comment servir cette démo au client ?

### Option A — Envoi direct par lien (recommandé pour l'instant)
Le fichier est actuellement dans `/app/backend/public_downloads/chassisprime-demo/index.html`.

Si ton backend expose ce dossier via une route statique, l'URL sera du type :
```
https://mesurechassis.com/public_downloads/chassisprime-demo/index.html
```

### Option B — Renforcement futur (si le client est méfiant)
Créer une route backend `GET /api/demo/chassisprime/{token}` qui :
- Vérifie un token à usage unique
- Sert le HTML avec headers `X-Frame-Options: DENY`, `Content-Security-Policy: frame-ancestors 'none'`
- Log l'IP et l'user-agent à chaque accès (traçabilité)
- Expire après X vues ou 7 jours

→ À implémenter si le client demande **explicitement** un lien "sécurisé", sinon inutile pour l'instant.

---

## 📞 Contact intégré dans la démo

- Téléphone : **0472 79 26 11** (celui de Châssis Prime, à confirmer)
- Email : **contact@chassisprime.store**
- WhatsApp float en bas à droite
- Bouton "Devis 24h" dans la nav

---

## 🎨 Design

- Palette : Bleu marine `#0A2540` + Or `#D4A574` + Crème `#F9F7F4`
- Typo : Playfair Display (titres) + Inter (corps)
- Ambiance : Premium, artisanal, wallon, patrimoine
- Sections : Hero → Partenaires → Services → Réalisations → Témoignages → Méthode → Primes → **Roadmap digitale** → Contact → Footer

---

*Fichier généré le 25 juin 2026 · Michel Guillaume · MesureChâssis*
