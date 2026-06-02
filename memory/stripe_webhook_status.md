# 🔵 État Stripe Webhook — À reprendre plus tard

## 📅 Date de pause
2 juin 2026 (session après-midi) — Utilisateur a fait une pause après plusieurs heures de debug.

## ✅ Ce qui MARCHE déjà
1. **Stripe Checkout** : l'écran de paiement s'ouvre correctement (UI 100% OK)
2. **Bug "Entreprise introuvable" résolu** : `stripe_routes.py` cherche maintenant par `company_id` (et non plus `id`)
3. **Bug KeyError 'get' résolu** : webhook handler utilise `json.loads()` au lieu de `stripe.Webhook.construct_event()` pour avoir des vrais dicts Python (évite les quirks de StripeObject)
4. **Logs diagnostic ajoutés** : `🩺 Webhook diag` affiche secret prefix/suffix + longueur + sig header + payload bytes
5. **`.strip()`** appliqué sur `STRIPE_WEBHOOK_SECRET` et `STRIPE_SECRET_KEY` (protection contre espaces invisibles)

## ❌ Ce qui ne MARCHE PAS encore
**Webhook Stripe → backend : 400 "Signature invalide"**

Diagnostic confirmé sur Railway logs :
```
🩺 Webhook diag — secret=whsec_MU0W...g8Yb (38 chars) | sig-header=t=1780408397,v1=573a49...
🩺 Webhook diag — payload bytes=6021
WARNING - Webhook : signature Stripe invalide
```

- Secret bien chargé (38 chars, format `whsec_...`)
- Signature reçue par le serveur
- Payload bien reçu (6021 bytes)
- Mais `stripe.WebhookSignature.verify_header()` rejette la signature

## 🔧 Tentatives faites (qui n'ont PAS résolu)
1. Mise à jour de la variable `STRIPE_WEBHOOK_SECRET` sur Railway (plusieurs fois)
2. Rotation de la clé secrète Stripe via "Invalider la clé secrète" → toujours 400
3. Vérification visuelle des 2 clés (Stripe et Railway) → semblent identiques
4. Ajout de `.strip()` sur la lecture du secret

## 🤔 Hypothèses restantes à explorer (prochaine session)
1. **Railway proxy modifie le body** : load balancer Railway pourrait re-encoder/décompresser le body avant qu'il arrive à notre code. La signature signée par Stripe portait sur les bytes ORIGINAUX, donc ne matche plus.
   - Test : utiliser `request.stream()` au lieu de `request.body()` pour récupérer les bytes vraiment bruts
   - Test : ajouter un middleware FastAPI qui capture le body brut AVANT toute transformation
2. **CharSet / encoding** : peut-être que `payload.decode("utf-8")` ne fait pas le bon encoding
   - Test : passer `payload` brut (bytes) à `verify_header` au lieu de decoder
3. **Vérification d'ordre des CORS** : le middleware CORS pourrait toucher au body
   - Test : déplacer le CORS APRÈS le webhook
4. **Tester en local avec Stripe CLI** : `stripe listen --forward-to http://localhost:8001/api/stripe/webhook` puis `stripe trigger checkout.session.completed`
5. **Tester avec un fake webhook** : créer un endpoint qui simule Stripe et signe manuellement avec le même secret → si ça marche, c'est bien Railway le coupable
6. **Vérifier `railway.json`** : voir si une option active gzip ou autre transformation
7. **Demander support Railway** : indiquer qu'on a un webhook Stripe avec signature invalide

## 💡 Workaround pragmatique en attendant
**Tant que `BETA_MODE=True` sur Railway** :
- Tous les comptes ont accès complet GRATUIT
- Le webhook n'est pas nécessaire pour le bon fonctionnement de l'app
- Quand on basculera en mode payant (`BETA_MODE=False`), il faudra IMPÉRATIVEMENT résoudre le webhook

## 📍 État du code (déployé sur Railway)
- Commit GitHub `routes/stripe_routes.py` : 42 min ago au moment de la pause (avec logs 🩺 et `.strip()`)
- ⚠️ TODO à la reprise : vérifier que le user a bien mis à jour `stripe_routes.py` avec la dernière version contenant les logs diagnostic

## 🎯 Prochaines actions concrètes (à la reprise)
1. Vérifier le diagnostic Railway log pour voir le secret prefix/suffix CURRENT
2. Tester l'hypothèse Railway proxy avec `request.stream()` ou capture middleware
3. Tester avec Stripe CLI en local pour isoler si c'est Railway ou notre code
4. Si rien ne marche : contacter le support Railway

## 🚫 Choses à NE PAS faire
- ❌ Ne pas redonner la clé secrète au user dans le chat (sécurité)
- ❌ Ne pas refaire 10 rotations de clé Stripe (inutile, le problème est dans la vérification)
- ❌ Ne pas désactiver la vérification de signature (faille de sécurité)
