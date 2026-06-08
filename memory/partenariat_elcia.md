# 🤝 Partenariat ELCIA / RAMASOFT — Intégration Devis ↔ Mesures Terrain

## Contexte
**Date du RDV** : 8 juin 2026, 13h30 — Gesves (Belgique)  
**Interlocuteur** : Hugues HUSSIN — Directeur Ramasoft (filiale Elcia Belgium)  
**Email** : hhussin@elcia.com  
**Téléphone** : +32 (0)81 30 90 88 / +32 495 25 90 88

## Proposition de partenariat
Elcia/Ramasoft édite un logiciel ERP/devis pour menuiseries. Ils n'ont PAS d'app mobile de prise de mesures terrain. Ils veulent intégrer MesureChâssis comme module complémentaire à leur écosystème.

## Workflow proposé (vision Elcia)

```
1. Admin Elcia crée un devis dans Ramasoft (dimensions théoriques)
2. Import du devis dans MesureChâssis
3. Mesureur va sur chantier avec MesureChâssis
4. Saisie des mesures brutes réelles
5. Comparaison automatique théorique vs réel
6. Alerte si écart > tolérance → correction avant fabrication
7. Validation OK → retour vers Elcia pour fabrication
```

## 🛠️ Fonctionnalités à développer (Build 10 ou ultérieur)

### Phase 1 — Import / Export basique
- [ ] Endpoint API `POST /api/elcia/import-quote` pour recevoir un devis
- [ ] Format d'échange à définir avec Elcia (JSON, XML, ou autre)
- [ ] Création automatique d'un chantier avec ouvertures pré-remplies
- [ ] Chaque ouverture contient ses dimensions THÉORIQUES (issues du devis)

### Phase 2 — Comparaison théorique vs réel
- [ ] Calcul automatique de l'écart entre théorique et terrain (en mm)
- [ ] Code couleur visuel : 🟢 OK / 🟡 Attention / 🔴 Erreur critique
- [ ] Tolérances paramétrables :
  - Par type d'ouverture (fenêtre, porte, baie, etc.)
  - Par dimension (largeur, hauteur, diagonale, équerrage)
  - Définies au niveau entreprise (configurables par l'Admin)

### Phase 3 — Retour vers Elcia
- [ ] Export du rapport de validation
- [ ] Endpoint API `POST /api/elcia/send-validation`
- [ ] Statuts : validated / requires_modification / blocked

### Phase 4 — Authentification croisée (optionnel)
- [ ] SSO entre Elcia et MesureChâssis
- [ ] Token d'API par client Elcia

## 💰 Modèle économique à négocier

**Options à présenter** :
- A. Module payant Elcia (30-50% des abonnements)
- B. Licence par utilisateur (forfait mensuel par client)
- C. Forfait global annuel (Elcia paie un montant fixe)

**Recommandation** : Combinaison A + B (revenus récurrents + variabilité)

## 🛡️ Points de vigilance à protéger

1. **Propriété intellectuelle** : code MesureChâssis reste 100% propriété de M. Pezzuto
2. **Pas d'exclusivité** : MesureChâssis pourra s'intégrer avec d'autres ERP plus tard
3. **Format d'échange clair** : Elcia fournit API + documentation
4. **Co-marketing** : mention mutuelle (site, presse, salons)
5. **Délais réalistes** : 2-3 mois minimum de développement + bêta
6. **Tarification protégée** : ne pas brader, marge claire pour les 2 parties

## ⏰ Roadmap proposée

- **Juin-Juillet 2026** : Définition technique + signature partenariat
- **Août-Septembre 2026** : Développement Phase 1 (Import)
- **Octobre 2026** : Bêta avec 2-3 clients Elcia
- **Novembre 2026** : Développement Phase 2 (Comparaison)
- **Q1 2027** : Lancement officiel public

## ❓ Questions à poser à Elcia (RDV de suivi)

1. Quel format de devis pouvez-vous exporter ? (API ? JSON ? PDF ?)
2. Avez-vous une API publique documentée ?
3. Combien de clients utilisent Ramasoft actuellement ?
4. Quels sont vos clients-cibles pour cette intégration ?
5. Quelles sont VOS attentes en termes de revenus/volume ?
6. Quel délai souhaitez-vous pour le MVP ?
7. Souhaitez-vous une exclusivité ? Si oui, sous quelles conditions ?
8. Qui sera mon interlocuteur technique côté Elcia ?
9. Pouvez-vous me fournir un accès test à votre logiciel ?
10. Vais-je avoir accès à votre force commerciale pour des présentations conjointes ?

## 📞 Prochaines actions

- [ ] Envoyer un email de remerciement à Hugues HUSSIN dans les 24h
- [ ] Demander une seconde réunion technique (visio si possible)
- [ ] Préparer un document de réponse à leur proposition (1-2 pages)
- [ ] Faire un brouillon de contrat de partenariat (avec aide d'un avocat si possible)
- [ ] Évaluer le ROI : combien de revenus potentiels vs coût de développement

## 🎯 Statut
🟡 **EN COURS DE NÉGOCIATION** — Décision finale à prendre après 2ème réunion + analyse business
