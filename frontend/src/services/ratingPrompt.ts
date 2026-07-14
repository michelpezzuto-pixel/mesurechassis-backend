/**
 * ⭐ Rating Prompt — Service centralisé (Priorité Campagne Jeton Café)
 *
 * Stratégie 2-étapes (industry standard, utilisée par Airbnb / Notion / Duolingo) :
 *   1. Notre modale custom en français avec le copywriting de Michel
 *      ("Un café, une note ?" + boutons Laisser 5 étoiles / Pas maintenant)
 *   2. SEULEMENT SI l'utilisateur clique "Laisser 5 étoiles" → on déclenche
 *      le pop-up natif Apple StoreKit (via expo-store-review).
 *
 * Cette approche :
 *   - Fait voir le copywriting spécifique "confrère" (+ conversion)
 *   - Ne consomme UN des 3 prompts natifs/365j Apple que si l'utilisateur
 *     est déjà positif → maximum d'étoiles 5
 *
 * ─── 🚦 FEATURE FLAG ────────────────────────────────────────────────
 * Actuellement DÉSACTIVÉ pour ne pas polluer les utilisateurs actuels.
 * Pour activer au lancement de la campagne Jeton Café :
 *
 *   1. Frontend : passer `RATING_PROMPT_ENABLED = true` ci-dessous
 *      OU définir EXPO_PUBLIC_RATING_PROMPT_ENABLED=true dans /app/frontend/.env
 *   2. Rebuild + soumettre à Apple
 *
 * Anti-spam :
 *   - Max 1 prompt tous les 90 jours par appareil (AsyncStorage)
 *   - Skippé si "Pas maintenant" cliqué au cours des 30 derniers jours
 */
import AsyncStorage from "@react-native-async-storage/async-storage";
import Constants from "expo-constants";
import * as StoreReview from "expo-store-review";
import { Platform } from "react-native";

/** 🚦 Master switch : activer au lancement de la campagne Jeton Café */
const RATING_PROMPT_ENABLED_DEFAULT = false;

/** Permet une override par variable d'env (utile pour QA/beta) */
function isFeatureEnabled(): boolean {
  const envFlag = (
    process.env.EXPO_PUBLIC_RATING_PROMPT_ENABLED ||
    (Constants.expoConfig?.extra as any)?.RATING_PROMPT_ENABLED ||
    ""
  ).toString().toLowerCase();
  if (envFlag === "true" || envFlag === "1") return true;
  if (envFlag === "false" || envFlag === "0") return false;
  return RATING_PROMPT_ENABLED_DEFAULT;
}

const KEY_LAST_SHOWN = "@mc/rating_prompt/last_shown_at";
const KEY_LAST_DISMISSED = "@mc/rating_prompt/last_dismissed_at";
const KEY_RATED = "@mc/rating_prompt/rated_at";

const DAYS = (n: number) => n * 24 * 60 * 60 * 1000;

/**
 * Décide si l'on peut proposer la modale custom maintenant.
 * Ne déclenche PAS l'UI — c'est à l'appelant d'afficher sa modale.
 */
export async function shouldShowRatingPrompt(): Promise<boolean> {
  if (!isFeatureEnabled()) return false;
  // iOS uniquement pour l'instant (Android arrive plus tard)
  if (Platform.OS !== "ios") return false;

  // Si l'utilisateur a déjà noté → on ne redemande jamais
  const rated = await AsyncStorage.getItem(KEY_RATED);
  if (rated) return false;

  const now = Date.now();

  // "Pas maintenant" < 30 jours → skip
  const dismissed = await AsyncStorage.getItem(KEY_LAST_DISMISSED);
  if (dismissed && now - parseInt(dismissed, 10) < DAYS(30)) return false;

  // Dernier affichage < 90 jours → skip
  const lastShown = await AsyncStorage.getItem(KEY_LAST_SHOWN);
  if (lastShown && now - parseInt(lastShown, 10) < DAYS(90)) return false;

  // Vérifier que StoreKit est disponible sur cet appareil
  try {
    const [available, hasAction] = await Promise.all([
      StoreReview.isAvailableAsync(),
      StoreReview.hasAction(),
    ]);
    if (!available || !hasAction) return false;
  } catch {
    return false;
  }

  return true;
}

/** Marque la modale custom comme "affichée" (limite à 1 tous les 90j). */
export async function markPromptShown(): Promise<void> {
  await AsyncStorage.setItem(KEY_LAST_SHOWN, Date.now().toString());
}

/** L'utilisateur a cliqué "Pas maintenant". */
export async function markPromptDismissed(): Promise<void> {
  await AsyncStorage.setItem(KEY_LAST_DISMISSED, Date.now().toString());
}

/**
 * L'utilisateur a cliqué "Laisser 5 étoiles" → on lance le pop-up natif
 * Apple StoreKit. Le retour de l'API n'indique pas si l'utilisateur a
 * réellement noté (Apple ne fournit pas cette info par design privé), on
 * marque donc "rated" de manière optimiste pour ne plus redemander.
 */
export async function triggerNativeReview(): Promise<void> {
  try {
    await StoreReview.requestReview();
    await AsyncStorage.setItem(KEY_RATED, Date.now().toString());
  } catch {
    // Silencieux : si StoreKit refuse (ex: quota Apple dépassé), on ne fait rien.
  }
}

/** Utilitaire debug (à retirer avant prod ou à laisser derrière un menu dev). */
export async function _resetRatingPromptState(): Promise<void> {
  await AsyncStorage.multiRemove([
    KEY_LAST_SHOWN,
    KEY_LAST_DISMISSED,
    KEY_RATED,
  ]);
}
