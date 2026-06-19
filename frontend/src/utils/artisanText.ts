/**
 * Adaptation du vocabulaire métier au "mode Artisan" (compte solo / artisan_mode).
 *
 * Règle métier (Build 9 — juin 2026) :
 *   En mode Artisan, l'utilisateur EST à la fois le commercial, le technicien
 *   et l'admin. Les mentions "commercial / technicien" deviennent confuses.
 *   On les remplace automatiquement par "vous" / "atelier" pour rendre les
 *   écrans cohérents.
 *
 *   Détection : `company.artisan_mode === true` (cf. AuthContext).
 *   Ce hook est désactivé pour les comptes Entreprise (où ces rôles existent).
 *
 *   ⚠️ Le helper opère sur la chaîne FINALE retournée par i18next : il ne
 *   modifie PAS les clés. Cela permet une adoption progressive : tout écran
 *   qui passe par `useT()` au lieu de `useTranslation().t` bénéficie
 *   automatiquement de la transformation.
 */

/**
 * Liste ordonnée de substitutions (priorité aux expressions longues).
 * Sensible à la casse pour préserver les majuscules de début de phrase.
 *
 * NOTE : les replacements sont conçus pour que le texte reste fluide même
 * si l'expression d'origine est précédée d'une apostrophe (l', d', …).
 */
const ARTISAN_REPLACEMENTS: [RegExp, string][] = [
  // ─── Phrases complètes (priorité maximale) ─────────────────────────
  [/transmettre au commercial pour mesurage/gi, "passer en prise de mesures"],
  [/À vérifier par le technicien/gi, "À vérifier avant fabrication"],
  [/Aucun commercial dans (votre |l['’])équipe/gi, "Mode Artisan Solo activé"],

  // ─── Verbes courants après "Le commercial / Le technicien" ─────────
  [/Le commercial assigné peut/g, "Vous pouvez"],
  [/le commercial assigné peut/g, "vous pouvez"],
  [/Le commercial sélectionné a/g, "Vous avez"],
  [/le commercial sélectionné a/g, "vous avez"],
  [/Le commercial peut/g, "Vous pouvez"],
  [/le commercial peut/g, "vous pouvez"],
  [/Le commercial pourra/g, "Vous pourrez"],
  [/le commercial pourra/g, "vous pourrez"],
  [/Le commercial sera/g, "Vous serez"],
  [/le commercial sera/g, "vous serez"],
  [/Le commercial est/g, "Vous êtes"],
  [/le commercial est/g, "vous êtes"],
  [/Le commercial doit/g, "Vous devez"],
  [/le commercial doit/g, "vous devez"],
  [/Le commercial a /g, "Vous avez "],
  [/le commercial a /g, "vous avez "],
  [/Le commercial souhaite/g, "Vous souhaitez"],
  [/le commercial souhaite/g, "vous souhaitez"],
  [/Le commercial assigné/g, "Vous"],
  [/le commercial assigné/g, "vous"],
  [/Le commercial sélectionné/g, "Vous"],
  [/le commercial sélectionné/g, "vous"],
  [/Le commercial/g, "Vous"],
  [/le commercial/g, "vous"],

  [/Seul le technicien peut/g, "Vous seul pouvez"],
  [/seul le technicien peut/g, "vous seul pouvez"],
  [/Seul le technicien/g, "Vous seul"],
  [/seul le technicien/g, "vous seul"],
  [/Le technicien peut/g, "Vous pouvez"],
  [/le technicien peut/g, "vous pouvez"],
  [/Le technicien pourra/g, "Vous pourrez"],
  [/le technicien pourra/g, "vous pourrez"],
  [/Le technicien sera/g, "Vous serez"],
  [/le technicien sera/g, "vous serez"],
  [/Le technicien doit/g, "Vous devez"],
  [/le technicien doit/g, "vous devez"],
  [/Le technicien a /g, "Vous avez "],
  [/le technicien a /g, "vous avez "],
  [/par le technicien/g, "par vous"],
  [/au technicien/g, "à vous-même"],
  [/du technicien/g, "de vous-même"],
  [/Le technicien/g, "Vous"],
  [/le technicien/g, "vous"],

  // ─── Mots isolés (en dernier pour ne pas casser les expressions) ───
  [/\bcommerciaux\b/g, "membres"],
  [/\btechniciens\b/g, "atelier"],
];

/**
 * Applique les substitutions Artisan à une chaîne.
 * @param text Texte d'origine (typiquement le retour de `t()`).
 * @param artisanMode Si false → retourne `text` inchangé.
 */
export function adaptArtisan(text: string, artisanMode: boolean): string {
  if (!artisanMode || !text) return text;
  let out = text;
  for (const [pattern, replacement] of ARTISAN_REPLACEMENTS) {
    out = out.replace(pattern, replacement);
  }
  return out;
}
