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
 * Règle métier :
 *   - Mode beta gratuit → Premium (admin-only override)
 *   - Mode "trial" actif → Premium (essai gratuit toutes fonctions)
 *   - Abonnement actif (solo/entreprise/pro) → Premium
 *   - Sinon → Free (formes premium verrouillées)
 */
export function isPremiumUser(company: CompanyProfile | null | undefined): boolean {
  if (!company) return false;
  // Override beta : pendant la beta, tout le monde a accès à tout
  if (company.beta_mode === true) return true;
  // Plan "free" explicite → pas Premium
  if (company.plan === "free") return false;
  // Abonnement actif ou en période d'essai → Premium
  const status = company.subscription_status;
  if (status === "active" || status === "trialing") return true;
  // Plan "trial" ou "pro" → Premium (cas legacy)
  if (company.plan === "trial" || company.plan === "pro") return true;
  // Par défaut → pas Premium
  return false;
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
