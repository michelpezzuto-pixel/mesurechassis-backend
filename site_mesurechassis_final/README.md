# 🚀 MesureChâssis — Site vitrine (production)

Site vitrine complet prêt à déployer sur **Easyhost** (ou tout hébergement Apache/Nginx).

## 📦 Contenu du dossier

### Pages HTML (16)
| Fichier | Rôle | URL finale |
|---------|------|-------------|
| `index.html` | Landing page | `/` |
| `telecharger.html` | Téléchargement app (Android Bêta + iOS bientôt) | `/telecharger.html` |
| `beta.html` | Accès rapide bêta web | `/beta.html` |
| `guide.html` | Guide d'utilisation complet | `/guide.html` |
| `faq.html` | Questions fréquentes | `/faq.html` |
| `a-propos.html` | À propos / mission / roadmap | `/a-propos.html` |
| `contact.html` | Page contact | `/contact.html` |
| `mentions-legales.html` | Mentions légales (obligatoire) | `/mentions-legales.html` |
| `cgu.html` | CGU (obligatoire) | `/cgu.html` |
| `cgv.html` | CGV (obligatoire dès paiement) | `/cgv.html` |
| `confidentialite.html` | Politique RGPD (obligatoire) | `/confidentialite.html` |
| `cookies.html` | Politique cookies (obligatoire CNIL/APD) | `/cookies.html` |
| `404.html` | Page d'erreur personnalisée | `/404.html` |
| `googlea942b0ef641b8ae8.html` | Vérification Google Search Console | (à la racine) |

### Assets
- `logo.png` — Logo MesureChâssis 32×32
- `favicon.png` — Favicon du site
- `og-image.jpg` — Image partage réseaux sociaux (1200×630)

### Configuration
- `sitemap.xml` — Plan du site pour Google
- `robots.txt` — Directives crawlers
- `.htaccess` — Forçage HTTPS + 404 perso + cache + compression (Apache)

---

## ✅ AUCUNE MODIFICATION REQUISE AVANT DÉPLOIEMENT

Tous les fichiers sont prêts. Vous pouvez les uploader directement sur Easyhost.

> ℹ️ **Note** : L'application est en cours de validation par le Google Play Store et l'App Store. La page `telecharger.html` affiche actuellement un bouton "Bientôt disponible — Recevoir une notification" pour les deux plateformes. Dès que votre application sera validée, contactez-moi pour mettre à jour les vrais liens de téléchargement.

---

## 🌐 Déploiement sur Easyhost

1. **Connectez-vous** à votre cPanel Easyhost
2. Ouvrez le **Gestionnaire de fichiers**
3. Allez dans le dossier `public_html/` (ou `www/` selon votre config)
4. **Uploadez le contenu du dossier `site_mesurechassis_final/`** (pas le dossier lui-même, mais tout ce qu'il contient)
5. Vérifiez que `index.html` est bien à la racine
6. Activez **Let's Encrypt SSL** depuis cPanel pour HTTPS

### Vérification post-déploiement
- ✅ `https://mesurechassis.com/` → landing page
- ✅ `https://mesurechassis.com/cgu.html` → CGU
- ✅ `https://mesurechassis.com/sitemap.xml` → sitemap
- ✅ Le bouton "Télécharger l'app" est visible en haut + en bas à droite
- ✅ Le bandeau cookies apparaît à la première visite

---

## 📋 Conformité légale (Belgique / UE)

✅ **RGPD** : Politique de confidentialité complète + consentement cookies + droit d'accès/suppression
✅ **CNIL / APD** : Bandeau cookies opt-in (Refuser/Accepter) avant tout cookie non-essentiel
✅ **Code de droit économique belge** : Mentions légales + CGU + CGV
✅ **Directive ePrivacy** : Politique cookies détaillée
✅ **B2B** : Mention explicite "professionnels uniquement", pas de droit de rétractation conso

⚠️ **Recommandation** : Avant la mise en ligne définitive, faites relire les **Mentions légales, CGU, CGV et Confidentialité** par un juriste ou un service spécialisé (Legalstart, Captain Contrat, ~100-200€). Les modèles fournis sont un excellent point de départ mais ne se substituent pas à un avis juridique adapté à votre situation précise (statut juridique, sous-traitants, etc.).

---

## 🎨 Charte respectée

- **Couleurs** : Orange `#FF6B35` · Fond noir `#121214` / `#1a1a1e`
- **Typo** : Syne (titres) + DM Sans (corps), chargées via Google Fonts
- **Responsive** : Mobile-first, breakpoints 600/760/880px
- **Performance** : CSS inline (pas de fichier externe), images optimisées
- **Accessibilité** : Labels ARIA, contraste AAA, navigation clavier

---

## 🔧 Maintenance future

Pour modifier le **footer en masse** sur toutes les pages, utilisez les scripts de build dans `/app/build_site/` :
- `_shared.py` → header + footer + cookie banner (modifier ici pour appliquer partout)
- `_new_pages.py` → contenu des pages CGU/CGV/Cookies/FAQ/Télécharger/404/À propos
- `build.py` → orchestrateur (`python build.py` pour régénérer le site)

---

## 📞 Support

Pour toute question sur la structure du site ou les futures évolutions :
- ✉️ info@mesurechassis.com
- 💻 Réouvrir une conversation avec l'agent IA pour modifications

---

**Version** : 1.0  
**Date de build** : 2026-05-24  
**Charte** : MesureChâssis · Made in Belgium 🇧🇪
