/**
 * 💎 FREEMIUM — Helper central pour le verrouillage des formes premium.
 *
 * Stratégie (validée client juin 2026) :
 *   - GRATUIT : 5 formes basiques (couvrent ~60-70% des chantiers menuisier débutant)
 *   - PREMIUM : 7 formes complexes débloquées par abonnement à 19€/mois minimum
 *
 * Source de vérité :
 *   - L'utilisateur a-t-il un abonnement actif ? → `isPremiumUser(company)`
 *   - Une forme est-elle gratuite ?              → `isFreeShape(shape)`
 *   - Forme accessible pour cet utilisateur ?     → `canUseShape(shape, company)`
 *
 * ⚠️ iOS : ne JAMAIS afficher de bouton de paiement dans l'app iOS pour
 * respecter la guideline Apple 3.1.1 (in-app purchase). À la place, rediriger
 * vers mesurechassis.com pour upgrader. Le helper `getUpgradeUrl()` gère ça.
 */
import type { Shape } from "@/src/components/wizard/types";
import type { CompanyProfile } from "@/src/context/AuthContext";
import { Platform } from "react-native";

// ════════════════════════════════════════════════════════════════════════
// Liste des formes GRATUITES (Free tier)
// ════════════════════════════════════════════════════════════════════════
//
// ⚠️ NE PAS modifier sans validation client. Ces 5 formes ont été choisies
// pour couvrir le "chantier classique" d'un menuisier sans avoir besoin de
// payer. Les formes plus rares ou prestigieuses sont en Premium.
export const FREE_SHAPES: Shape[] = [
  "rect",              // A — Carré / Rectangle (la base absolue)
  "porte_entree",      // B — Porte d'entrée (quotidien)
  "porte_garage",      // C — Porte de garage (courant)
  "trapeze",           // D — Trapèze (demandé en base)
  "coulissant_levant", // K — Coulissant levant (très demandé)
];

// Toutes les autres formes définies dans `SHAPES` sont automatiquement
// considérées comme premium (pas besoin de les lister explicitement).

// ════════════════════════════════════════════════════════════════════════
// API PUBLIQUE
// ════════════════════════════════════════════════════════════════════════

/**
 * Une forme est-elle gratuite (accessible sans abonnement) ?
 */
export function isFreeShape(shape: Shape | null | undefined): boolean {
  if (!shape) return true;
  return FREE_SHAPES.includes(shape);
}

/**
 * L'utilisateur a-t-il un statut "premium" (= peut accéder à TOUTES les formes) ?
 *
 * Règle métier (ordre de priorité) :
 *   1. Mode beta gratuit          → Premium (admin/testeurs)
 *   2. Essai gratuit 14 jours actif → Premium (nouveaux utilisateurs)
 *   3. Abonnement actif/trialing   → Premium
 *   4. Plan "trial" ou "pro"       → Premium (cas legacy)
 *   5. Sinon                       → Free (formes premium verrouillées)
 */
export function isPremiumUser(company: CompanyProfile | null | undefined): boolean {
  if (!company) return false;
  // 1. Override beta (admin/testeurs)
  if (company.beta_mode === true) return true;
  // 2. Essai gratuit 14 jours (auto-attribué à l'inscription)
  if (isInFreemiumTrial(company)) return true;
  // 3. Plan "free" explicite → pas Premium
  if (company.plan === "free") return false;
  // 4. Abonnement actif ou en période d'essai Stripe → Premium
  const status = company.subscription_status;
  if (status === "active" || status === "trialing") return true;
  // 5. Plan "trial" ou "pro" → Premium (cas legacy)
  if (company.plan === "trial" || company.plan === "pro") return true;
  // Par défaut → pas Premium
  return false;
}

// ════════════════════════════════════════════════════════════════════════
// 🎁 ESSAI GRATUIT 14 JOURS
// ════════════════════════════════════════════════════════════════════════

/**
 * L'utilisateur est-il actuellement dans sa période d'essai gratuit 14 jours ?
 * Vérifie `freemium_trial_ends_at` (date ISO) contre l'horloge actuelle.
 */
export function isInFreemiumTrial(company: CompanyProfile | null | undefined): boolean {
  if (!company?.freemium_trial_ends_at) return false;
  const end = Date.parse(company.freemium_trial_ends_at);
  if (Number.isNaN(end)) return false;
  return end > Date.now();
}

/**
 * Combien de jours restants avant la fin de l'essai gratuit ?
 * Retourne `null` si pas d'essai en cours.
 */
export function getFreemiumTrialDaysRemaining(
  company: CompanyProfile | null | undefined,
): number | null {
  if (!company?.freemium_trial_ends_at) return null;
  const end = Date.parse(company.freemium_trial_ends_at);
  if (Number.isNaN(end)) return null;
  const now = Date.now();
  if (end <= now) return 0;
  const ms = end - now;
  return Math.ceil(ms / (24 * 60 * 60 * 1000));
}

/**
 * Cet utilisateur peut-il utiliser cette forme ?
 * Combine `isFreeShape` et `isPremiumUser`.
 */
export function canUseShape(
  shape: Shape | null | undefined,
  company: CompanyProfile | null | undefined,
): boolean {
  if (isFreeShape(shape)) return true;
  return isPremiumUser(company);
}

// ════════════════════════════════════════════════════════════════════════
// UPGRADE URL (iOS vs Android/Web)
// ════════════════════════════════════════════════════════════════════════

/**
 * URL vers laquelle rediriger l'utilisateur pour upgrader vers Premium.
 *
 * Sur iOS : on retourne `null` (à gérer par l'appelant — affiche un message
 * "Allez sur mesurechassis.com" car Apple interdit les achats hors in-app
 * via la Guideline 3.1.1).
 *
 * Sur Android/Web : route interne `/subscription` qui mène au Stripe Checkout.
 */
export function getUpgradeRoute(): string | null {
  if (Platform.OS === "ios") return null;
  return "/subscription";
}

/**
 * Lorsque sur iOS, on dirige vers le site web pour upgrader.
 */
export const UPGRADE_WEB_URL = "https://mesurechassis.com/abonnement";

// ════════════════════════════════════════════════════════════════════════
// PRICING (affichage)
// ════════════════════════════════════════════════════════════════════════

export const PREMIUM_PRICE_MONTHLY = "19 €";
export const PREMIUM_PRICE_YEARLY = "190 €";
export const PREMIUM_YEARLY_SAVINGS = "2 mois offerts";
