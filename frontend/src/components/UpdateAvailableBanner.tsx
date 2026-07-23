/**
 * 🟢 UpdateAvailableBanner — Bannière soft "Nouvelle version disponible"
 * v1.1.3 — style Revolut/Uber
 *
 * Affichée en haut du dashboard quand :
 *   - current < latest_version (mais pas encore < min_version)
 *
 * L'utilisateur peut la fermer (bouton X). Le dismiss est mémorisé par
 * version (AsyncStorage) → si une NOUVELLE latest_version sort, la bannière
 * réapparaît (comportement Revolut).
 */
import React, { useCallback, useEffect, useState } from "react";
import {
  Linking,
  Platform,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { colors } from "@/src/theme";
import { storage } from "@/src/utils/storage";

const DISMISS_KEY = "mc_update_banner_dismissed_v";

type Props = {
  currentVersion: string;
  latestVersion: string;
  highlights?: string[];
  appStoreUrl: string;
  playStoreUrl?: string | null;
};

export default function UpdateAvailableBanner({
  currentVersion,
  latestVersion,
  highlights = [],
  appStoreUrl,
  playStoreUrl,
}: Props) {
  const [dismissed, setDismissed] = useState<boolean | null>(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const dismissedFor = await storage.get<string>(DISMISS_KEY, "");
        if (mounted) {
          setDismissed(dismissedFor === latestVersion);
        }
      } catch {
        if (mounted) setDismissed(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, [latestVersion]);

  const handleUpdate = useCallback(async () => {
    const url = Platform.OS === "android" && playStoreUrl ? playStoreUrl : appStoreUrl;
    try {
      const supported = await Linking.canOpenURL(url);
      if (supported) {
        await Linking.openURL(url);
      }
    } catch {
      // ignore
    }
  }, [appStoreUrl, playStoreUrl]);

  const handleDismiss = useCallback(async () => {
    setDismissed(true);
    try {
      await storage.set(DISMISS_KEY, latestVersion);
    } catch {
      // ignore
    }
  }, [latestVersion]);

  // En cours de chargement OU l'utilisateur a déjà dismissed cette version
  if (dismissed !== false) return null;

  return (
    <View style={styles.container}>
      <View style={styles.iconWrap}>
        <Ionicons name="cloud-download" size={22} color="#fff" />
      </View>
      <View style={styles.textWrap}>
        <Text style={styles.title} numberOfLines={1}>
          🚀 Nouvelle version disponible ({latestVersion})
        </Text>
        <Text style={styles.subtitle} numberOfLines={2}>
          {highlights.length > 0
            ? highlights.slice(0, 2).join(" · ")
            : `Vous êtes en ${currentVersion} — mettez à jour pour les dernières améliorations.`}
        </Text>
      </View>
      <TouchableOpacity
        style={styles.cta}
        onPress={handleUpdate}
        activeOpacity={0.85}
      >
        <Text style={styles.ctaText}>Mettre à jour</Text>
      </TouchableOpacity>
      <TouchableOpacity
        style={styles.close}
        onPress={handleDismiss}
        hitSlop={8}
        activeOpacity={0.6}
      >
        <Ionicons name="close" size={16} color="rgba(255,255,255,0.85)" />
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    backgroundColor: colors.primary,
    paddingVertical: 10,
    paddingHorizontal: 12,
    marginHorizontal: 12,
    marginTop: 8,
    marginBottom: 4,
    borderRadius: 14,
    shadowColor: colors.primary,
    shadowOpacity: 0.35,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 },
    elevation: 4,
  },
  iconWrap: {
    width: 36,
    height: 36,
    borderRadius: 12,
    backgroundColor: "rgba(255,255,255,0.2)",
    alignItems: "center",
    justifyContent: "center",
  },
  textWrap: { flex: 1, minWidth: 0 },
  title: {
    color: "#fff",
    fontSize: 13,
    fontWeight: "800",
    marginBottom: 2,
    letterSpacing: 0.2,
  },
  subtitle: {
    color: "rgba(255,255,255,0.92)",
    fontSize: 11,
    lineHeight: 14,
  },
  cta: {
    backgroundColor: "#fff",
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 999,
  },
  ctaText: {
    color: colors.primary,
    fontSize: 12,
    fontWeight: "800",
    letterSpacing: 0.3,
  },
  close: {
    marginLeft: 4,
    width: 24,
    height: 24,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 12,
  },
});
