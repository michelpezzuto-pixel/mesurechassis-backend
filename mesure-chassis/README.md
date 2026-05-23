# MesureChassis

> Application mobile de relevé métrologique pour **châssis** (fenêtres, baies, portes-fenêtres).
> Application sœur de **MesureEscalier**, partageant la même base technique (Expo / FastAPI / MongoDB)
> et la même librairie de composants partagés `@shared-ui`.

---

## 🎯 Objectif

Fournir à un artisan menuisier sur le terrain un outil mobile-first pour :

1. **Créer un chantier** (client + adresse + photos).
2. **Saisir les châssis** un par un, avec leurs dimensions et options (type d'ouverture,
   matériau, vitrage, accessoires).
3. **Calculer automatiquement** : surface, prix unitaire (selon barème),
   ajustements (renforts, pose dépose, finitions).
4. **Visualiser** : élévation (côté pièce) + vue en plan (vue de dessus avec sens d'ouverture).
5. **Exporter** un rapport PDF complet à transmettre à l'atelier ou au client.

**Vocabulaire métier ciblé** :
`Châssis fixe`, `Ouvrant 1 vantail / 2 vantaux`, `Oscillo-battant`, `Coulissant`,
`Imposte`, `Trumeau`, `Allège`, `Tablette`, `Sens d'ouverture (G/D)`, etc.

---

## 📦 État actuel du repo

- ✅ `app.json` configuré avec les Application IDs officiels (Android + iOS).
- ⏳ **Scaffold complet à générer** (cf. `MAINTENANCE.md → Bootstrap du projet`).
- ⏳ Backend dédié à brancher (peut réutiliser le même domaine `*.mesurechassis.*`
  avec un router FastAPI `routers/chassis.py`).

| App | Application ID Android | Bundle ID iOS |
|---|---|---|
| MesureEscalier | `com.mesurechassis.escalier` | `com.mesurechassis.escalier` |
| **MesureChassis** | `com.mesurechassis.chassis` | `com.mesurechassis.chassis` |

---

## 🚀 Démarrage rapide (une fois le scaffold complet)

```bash
# 1. Installer les dépendances
cd /app/mesure-chassis
yarn install

# 2. Lancer le serveur de dev (web + QR Code Expo Go)
yarn expo start

# 3. Backend (réutilise l'instance MesureEscalier ou un router dédié)
sudo supervisorctl restart backend
```

---

## 📚 Documents associés

- [`MAINTENANCE.md`](./MAINTENANCE.md) — guide complet de maintenance, ajout
  de features, conventions de code, patterns réutilisables.
- [`ARCHITECTURE.md`](./ARCHITECTURE.md) — schéma technique, dépendances entre
  modules, flow de données, contrats API.

---

## 📋 Workflow de release

1. Bumper `expo.version` + `android.versionCode` + `ios.buildNumber` dans `app.json`.
2. `eas build --platform all --profile production`.
3. Soumettre via `eas submit` ou manuellement sur la Play Console / App Store Connect.
