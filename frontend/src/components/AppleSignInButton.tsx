/**
 * 🍎 AppleSignInButton — Bouton natif Sign in with Apple
 * v1.1.3 — Design natif imposé par App Store (Guideline 4.8)
 *
 * S'affiche UNIQUEMENT sur iOS (le composant natif n'est pas dispo ailleurs).
 * Utilise AppleAuthenticationButton d'expo-apple-authentication → rendu
 * natif conforme aux Human Interface Guidelines d'Apple.
 */
import React, { useEffect, useState } from "react";
import { StyleSheet, View } from "react-native";
import * as AppleAuthentication from "expo-apple-authentication";
import {
  isAppleSignInAvailable,
  signInWithApple,
  type AppleSignInResult,
} from "@/src/services/appleAuth";
import { useAuth } from "@/src/context/AuthContext";

type Props = {
  /** Callback appelé après la connexion Apple réussie (avant navigation) */
  onSuccess?: () => void;
  /** Callback erreur — reçoit un message lisible */
  onError?: (message: string) => void;
  /** ID de station (☕ campagne Jeton Café), optionnel */
  stationId?: string;
  /** Style du bouton : "signin" (défaut), "signup", "continue" */
  buttonType?: "signin" | "signup" | "continue";
  /** Largeur totale (défaut : 100%) */
  fullWidth?: boolean;
};

export default function AppleSignInButton({
  onSuccess,
  onError,
  stationId,
  buttonType = "signin",
  fullWidth = true,
}: Props) {
  const [available, setAvailable] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);
  const { signInWithApple: authSignInWithApple } = useAuth();

  useEffect(() => {
    let mounted = true;
    (async () => {
      const ok = await isAppleSignInAvailable();
      if (mounted) setAvailable(ok);
    })();
    return () => {
      mounted = false;
    };
  }, []);

  // iOS 13+ uniquement — pas d'affichage ailleurs
  if (available !== true) return null;

  const handlePress = async () => {
    if (busy) return;
    setBusy(true);
    try {
      const res: AppleSignInResult | null = await signInWithApple();
      if (!res) {
        // Utilisateur a annulé la fenêtre Apple → silence
        return;
      }
      await authSignInWithApple(
        res.identityToken,
        res.userName || undefined,
        res.userEmail || undefined,
        stationId,
      );
      onSuccess?.();
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail || err?.message || "Connexion Apple échouée.";
      onError?.(String(msg));
    } finally {
      setBusy(false);
    }
  };

  const nativeType = (() => {
    switch (buttonType) {
      case "signup":
        return AppleAuthentication.AppleAuthenticationButtonType.SIGN_UP;
      case "continue":
        return AppleAuthentication.AppleAuthenticationButtonType.CONTINUE;
      case "signin":
      default:
        return AppleAuthentication.AppleAuthenticationButtonType.SIGN_IN;
    }
  })();

  return (
    <View style={[styles.wrapper, fullWidth && { width: "100%" }]}>
      <AppleAuthentication.AppleAuthenticationButton
        buttonType={nativeType}
        buttonStyle={
          AppleAuthentication.AppleAuthenticationButtonStyle.BLACK
        }
        cornerRadius={12}
        style={styles.button}
        onPress={handlePress}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    alignItems: "stretch",
    justifyContent: "center",
  },
  button: {
    width: "100%",
    height: 50,
  },
});
