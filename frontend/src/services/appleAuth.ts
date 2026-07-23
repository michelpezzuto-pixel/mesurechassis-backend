/**
 * 🍎 Sign in with Apple — Client wrapper (iOS only)
 * v1.1.3 — Apple Guideline 4.8 compliance
 *
 * Flux :
 *   1. Vérifier `isAvailableAsync()` — iOS 13+ uniquement, jamais Android/web
 *   2. `signInAsync` avec scopes FULL_NAME + EMAIL
 *   3. Apple retourne { identityToken, fullName?, email? } — nom/email
 *      renvoyés UNIQUEMENT à la 1re connexion. On les persiste immédiatement.
 *   4. POST /api/auth/apple/session → notre JWT applicatif
 *   5. AuthContext.signInWithApple({ identityToken, fullName, email })
 */
import { Platform } from "react-native";
import * as AppleAuthentication from "expo-apple-authentication";

export type AppleSignInResult = {
  identityToken: string;
  userName: string | null;
  userEmail: string | null;
};

export async function isAppleSignInAvailable(): Promise<boolean> {
  if (Platform.OS !== "ios") return false;
  try {
    return await AppleAuthentication.isAvailableAsync();
  } catch {
    return false;
  }
}

/**
 * Lance le flow natif Apple Sign-In.
 *
 * Retourne null si l'utilisateur annule (pas une erreur).
 * Throw une Error avec message lisible pour les autres cas.
 */
export async function signInWithApple(): Promise<AppleSignInResult | null> {
  if (Platform.OS !== "ios") {
    throw new Error(
      "Sign in with Apple n'est disponible que sur iPhone/iPad."
    );
  }

  let credential: AppleAuthentication.AppleAuthenticationCredential;
  try {
    credential = await AppleAuthentication.signInAsync({
      requestedScopes: [
        AppleAuthentication.AppleAuthenticationScope.FULL_NAME,
        AppleAuthentication.AppleAuthenticationScope.EMAIL,
      ],
    });
  } catch (err: any) {
    // ERR_REQUEST_CANCELED = utilisateur a annulé la fenêtre Apple → pas une erreur
    if (err?.code === "ERR_REQUEST_CANCELED" || err?.code === "ERR_CANCELED") {
      return null;
    }
    // eslint-disable-next-line no-console
    console.warn("[appleAuth] signInAsync failed", err);
    throw new Error(err?.message || "Connexion Apple échouée. Réessayez.");
  }

  if (!credential.identityToken) {
    throw new Error("Apple n'a pas renvoyé de jeton d'identité. Réessayez.");
  }

  // Nom : Apple retourne fullName SEULEMENT à la 1re connexion.
  const fullName = credential.fullName;
  let userName: string | null = null;
  if (fullName) {
    const parts = [fullName.givenName, fullName.familyName]
      .filter((s): s is string => Boolean(s && s.trim()))
      .map((s) => s.trim());
    userName = parts.length ? parts.join(" ") : null;
  }

  return {
    identityToken: credential.identityToken,
    userName,
    userEmail: credential.email || null,
  };
}
