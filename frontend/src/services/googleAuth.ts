/**
 * 🔑 Emergent-managed Google Sign-In flow for Expo mobile + web.
 *
 * Flow :
 *   1. Compute redirect URL (Linking.createURL on mobile, window.location on web).
 *   2. Open https://auth.emergentagent.com/?redirect=<redirect_url>.
 *   3. After Google auth, user comes back with `#session_id=<id>` in URL.
 *   4. We extract the session_id and hand it to AuthContext.signInWithGoogle,
 *      which exchanges it for our app JWT via POST /api/auth/google/session.
 *
 * Usage example :
 *
 *   const { startGoogleAuth, consumeUrlIfSessionId } = useGoogleAuth();
 *
 *   // Sur bouton "Continuer avec Google"
 *   await startGoogleAuth(); // sur mobile → openAuthSessionAsync, sur web → location.href
 *
 *   // Au démarrage de l'app (une fois pour tenter de récupérer un session_id
 *   // laissé par le redirect web) :
 *   await consumeUrlIfSessionId();
 */
import { Platform, Linking } from "react-native";
import * as WebBrowser from "expo-web-browser";
import * as ExpoLinking from "expo-linking";

const EMERGENT_AUTH_URL = "https://auth.emergentagent.com/";

/**
 * Extract session_id from a URL fragment or query — supports both formats:
 *  - `#session_id=xyz`
 *  - `?session_id=xyz`
 */
export function extractSessionId(url: string | null): string | null {
  if (!url) return null;
  try {
    // Support both #session_id= and ?session_id=
    const hashMatch = url.match(/[#&]session_id=([^&#]+)/i);
    if (hashMatch) return decodeURIComponent(hashMatch[1]);
    const queryMatch = url.match(/[?&]session_id=([^&#]+)/i);
    if (queryMatch) return decodeURIComponent(queryMatch[1]);
  } catch {
    /* noop */
  }
  return null;
}

/** Retourne l'URL de redirection à donner à Emergent selon la plateforme. */
export function getRedirectUrl(): string {
  if (Platform.OS === "web") {
    // Sur web, on doit revenir à une route qui existe dans l'app.
    // La racine `/` de expo-router affiche l'écran de login → parfait.
    if (typeof window !== "undefined") {
      return window.location.origin + "/";
    }
    return "/";
  }
  // Sur mobile (Expo Go = exp://..., build natif = mesurechassis://...).
  // ExpoLinking.createURL("") retourne le bon schéma.
  return ExpoLinking.createURL("");
}

/**
 * Ouvre l'écran d'authentification Emergent + Google.
 *
 * Sur mobile : utilise `WebBrowser.openAuthSessionAsync` (ASWebAuthSession
 *   sur iOS, Custom Tabs sur Android). Retourne l'URL de callback.
 *
 * Sur web : navigue directement via window.location.href. La fonction
 *   ne retourne rien (la page va être remplacée).
 *
 * Retourne le `session_id` extrait si le flux est complet, sinon null.
 */
export async function openGoogleAuth(): Promise<string | null> {
  const redirect = getRedirectUrl();
  const authUrl = `${EMERGENT_AUTH_URL}?redirect=${encodeURIComponent(redirect)}`;

  if (Platform.OS === "web") {
    // Navigation directe — la page va se recharger, on revient plus tard
    // avec un #session_id=xxx sur la même origine.
    if (typeof window !== "undefined") {
      window.location.href = authUrl;
    }
    return null;
  }

  // Mobile — ouvrir un WebBrowser natif
  const result = await WebBrowser.openAuthSessionAsync(authUrl, redirect);
  if (result.type !== "success" || !result.url) {
    return null;
  }
  return extractSessionId(result.url);
}

/**
 * À appeler au mount de l'écran de login. Sur web, extrait le session_id
 * s'il est présent dans l'URL courante (après un redirect Google → app).
 * Sur mobile, lit `Linking.getInitialURL()` (cold-start deep link).
 *
 * Nettoie l'URL après extraction (web only).
 */
export async function consumeInitialSessionId(): Promise<string | null> {
  if (Platform.OS === "web") {
    if (typeof window === "undefined") return null;
    const full = window.location.href;
    const id = extractSessionId(full);
    if (id) {
      // Nettoyer l'URL (retire le #session_id=... du navigateur)
      try {
        window.history.replaceState(null, "", window.location.pathname);
      } catch {
        /* noop */
      }
    }
    return id;
  }
  // Mobile — cold start deep link
  try {
    const url = await Linking.getInitialURL();
    return extractSessionId(url);
  } catch {
    return null;
  }
}
