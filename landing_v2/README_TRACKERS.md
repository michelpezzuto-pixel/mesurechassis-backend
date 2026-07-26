# 🚀 Guide pas-à-pas — Configurer les IDs de tracking

Ce fichier explique **exactement** comment obtenir chaque ID à remplacer
dans `index.html`. Comptez environ **45 minutes** pour tout faire.

À chaque étape : je te donne l'URL, la marche à suivre, et l'ID à copier.

---

## 📊 1. Google Analytics 4 (GA4) — 10 min

**À quoi ça sert :** compter le nombre de visiteurs, savoir d'où ils viennent,
combien cliquent sur "Télécharger", combien restent longtemps, etc.
Gratuit à vie.

### Étapes

1. Va sur **https://analytics.google.com/**
2. Connecte-toi avec ton compte Google (le même que Google Ads si possible)
3. Clique sur **Admin** (roue crantée en bas à gauche)
4. **Créer un compte** :
   - Nom du compte : `MesureChâssis`
   - Coche "Suggestions techniques par email"
5. **Créer une propriété** :
   - Nom : `mesurechassis.com`
   - Fuseau : `(GMT+01:00) Bruxelles`
   - Devise : `Euro (€)`
   - Secteur : `Technologie` → `Logiciels`
6. **Créer un flux de données Web** :
   - URL : `https://mesurechassis.com`
   - Nom : `MesureChâssis Web`
7. Une fois créé, tu verras un encart **"ID de mesure"** en haut à droite :
   > **`G-XXXXXXXXXX`** ← copie cet ID (commence toujours par `G-`)

### Où le coller dans index.html

Cherche **2 occurrences** de `G-XXXXXXXXXX` et remplace-les par ton vrai ID :

```html
<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
                                                              ^^^^^^^^^^^^^ ici

gtag('config', 'G-XXXXXXXXXX', { anonymize_ip: true });
                ^^^^^^^^^^^^^ et ici
```

---

## 📘 2. Meta Pixel (Facebook + Instagram Ads) — 15 min

**À quoi ça sert :** quand tu lanceras Meta Ads (mois 3+), le Pixel permet
à Facebook/Instagram de mesurer combien de personnes ont visité ton site
suite à tes pubs, et d'affiner son ciblage automatiquement.
Gratuit à vie.

### Étapes

1. Va sur **https://business.facebook.com/**
2. Connecte-toi avec ton compte Facebook personnel (ne t'inquiète pas, tu ne
   seras pas obligé de publier quoi que ce soit)
3. Clique sur **Créer un compte** (Business Manager)
   - Nom : `MesureChâssis SRL` (ou ton nom de société)
   - Nom : `Michel Pezzuto`
   - Email pro : `info@mesurechassis.com`
4. Une fois dans Business Manager → **Configuration → Événements** → **Sources de données**
5. Clique sur **Ajouter → Pixel**
   - Nom : `MesureChâssis Web Pixel`
   - URL du site : `https://mesurechassis.com`
6. Choisis **"Configurer le Pixel manuellement"**
7. Tu verras un ID à **15 chiffres** :
   > **`123456789012345`** ← copie cet ID

### Où le coller dans index.html

Cherche **2 occurrences** de `000000000000000` et remplace-les :

```html
fbq('init', '000000000000000');
             ^^^^^^^^^^^^^^^ ici

src="https://www.facebook.com/tr?id=000000000000000&ev=PageView&noscript=1"
                                    ^^^^^^^^^^^^^^^ et ici
```

---

## 🎯 3. Google Ads Conversion Tag — 10 min

**À quoi ça sert :** quand tu lanceras Google Ads Search (septembre), il
faut que Google sache quels clics ont mené à un téléchargement ou un rdv
Calendly. Sinon Google ne peut pas optimiser ta campagne.
Gratuit à vie.

### Étapes

1. Va sur **https://ads.google.com/**
2. Connecte-toi (même compte Google que GA4 recommandé)
3. Ignore les popups d'onboarding ("Commencer avec Smart Campaign") →
   clique **"Passer en mode expert"** en bas
4. Menu **Outils → Conversions** (icône clé à molette en haut à droite)
5. Clique sur **+ Nouvelle action de conversion → Site web**
6. URL de ton site : `https://mesurechassis.com`
7. Choisis les événements à tracker : coche **"Ajouter manuellement"** puis :
   - **Nom** : `App Download Click`
   - **Catégorie** : `Download`
   - **Valeur** : `Valeurs différentes` → laisse vide
   - **Comptage** : `1 par clic`
   - **Fenêtre de conversion** : 30 jours
8. Une fois créé, tu obtiens 2 valeurs :
   - **ID de conversion** : `AW-1234567890` ← c'est celle-ci qui compte ici
   - **Libellé de conversion** : `abcdef123` ← à retenir pour plus tard

### Où le coller dans index.html

Cherche **2 occurrences** de `AW-XXXXXXXXX` et remplace-les :

```html
<script async src="https://www.googletagmanager.com/gtag/js?id=AW-XXXXXXXXX"></script>
                                                               ^^^^^^^^^^^^ ici

gtag('config', 'AW-XXXXXXXXX');
                ^^^^^^^^^^^^ et ici
```

---

## 📞 4. Calendly (rdv 15 min avec Michel) — 10 min

**À quoi ça sert :** un menuisier hésite à installer l'app ? Il clique sur
"Réserver 15 min avec Michel" et choisit son créneau. Tu reçois un email
avec le sujet et son numéro. Bloque 3 créneaux/semaine.
Gratuit (plan basic suffit).

### Étapes

1. Va sur **https://calendly.com/signup**
2. Inscris-toi avec ton email pro
3. Après inscription, choisis :
   - **Fuseau horaire** : Bruxelles
   - **Ton URL personnalisée** : `calendly.com/michel-pezzuto` (ou similaire)
4. Clique **"Créer un événement" → "Rendez-vous individuel"**
   - Nom : `Démo MesureChâssis (15 min)`
   - Durée : `15 min`
   - Description : "Je te montre l'app en direct et tu me poses toutes tes questions techniques."
   - Disponibilités : Bloque **3 créneaux fixes** dans la semaine
     (ex: Mardi 17h30, Jeudi 18h, Vendredi 12h)
5. **Copie le lien** de l'événement, il ressemble à :
   > `https://calendly.com/michel-pezzuto/15min`

### Où le coller dans index.html

Cherche **1 occurrence** de `YOUR-CALENDLY-USERNAME` et remplace :

```html
<a href="https://calendly.com/YOUR-CALENDLY-USERNAME/15min"
                              ^^^^^^^^^^^^^^^^^^^^^^ ici
```

---

## ✅ Checklist finale

Avant de republier ton site sur ton hébergement (OVH, Netlify, Cloudflare,
Vercel, ou ton FTP habituel) :

- [ ] `G-XXXXXXXXXX` remplacé (2× dans le fichier)
- [ ] `000000000000000` remplacé (2× dans le fichier)
- [ ] `AW-XXXXXXXXX` remplacé (2× dans le fichier)
- [ ] `YOUR-CALENDLY-USERNAME` remplacé (1× dans le fichier)

Puis teste :

- [ ] Ouvre ton site sur mesurechassis.com
- [ ] Ouvre les outils dev du navigateur (F12) → Console
- [ ] Tu devrais voir apparaître (ou pas d'erreurs)
- [ ] Va sur **https://analytics.google.com/** → Real-Time → tu dois te voir
  toi-même comme visiteur actif
- [ ] Clique sur "📞 Réserver 15 min avec Michel" → doit ouvrir ton Calendly

---

## 🎯 Ordre recommandé pour Michel

1. **Cette semaine** : GA4 + Calendly (les 2 les plus rapides, valeur immédiate)
2. **Semaine du 4 août** : Google Ads Conversion Tag (quand tu créeras la campagne)
3. **Mois 3 (octobre)** : Meta Pixel (quand tu commenceras Facebook Ads)

**Tu peux mettre les 4 en place tout de suite** — les balises restent silencieuses
tant que tu ne lances pas les campagnes, aucun risque.
