/**
 * 🔴 ForceUpdateScreen — Écran bloquant "Mise à jour requise"
 * v1.1.3 — style Revolut/Uber
 *
 * Affiché quand :
 *   - APP_FORCE_UPDATE=true côté backend
 *   - ET version installée < APP_MIN_VERSION
 *
 * Aucun bouton "Plus tard" — l'utilisateur DOIT mettre à jour.
 * Bouton principal → Linking vers App Store.
 */
import React from "react";
import {
  Linking,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { colors } from "@/src/theme";

type Props = {
  currentVersion: string;
  latestVersion: string;
  minVersion: string;
  message: string;
  highlights?: string[];
  appStoreUrl: string;
  playStoreUrl?: string | null;
  onLogout?: () => void;
};

export default function ForceUpdateScreen({
  currentVersion,
  latestVersion,
  minVersion,
  message,
  highlights = [],
  appStoreUrl,
  playStoreUrl,
  onLogout,
}: Props) {
  const openStore = async () => {
    const url = Platform.OS === "android" && playStoreUrl ? playStoreUrl : appStoreUrl;
    try {
      const supported = await Linking.canOpenURL(url);
      if (supported) {
        await Linking.openURL(url);
      }
    } catch {
      // ignore silently — l'utilisateur peut réessayer
    }
  };

  return (
    <SafeAreaView style={styles.container} edges={["top", "bottom"]}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <View style={styles.iconWrap}>
          <Ionicons name="arrow-up-circle" size={96} color={colors.primary} />
        </View>

        <Text style={styles.title}>Mise à jour requise</Text>

        <Text style={styles.subtitle}>
          Votre version <Text style={styles.mono}>{currentVersion}</Text> n&apos;est
          plus supportée. Merci de mettre à jour vers la version{" "}
          <Text style={styles.mono}>{latestVersion}</Text> pour continuer.
        </Text>

        <View style={styles.card}>
          <Text style={styles.message}>{message}</Text>

          {highlights.length > 0 && (
            <>
              <Text style={styles.newsTitle}>Nouveautés de cette version</Text>
              <View style={styles.highlights}>
                {highlights.map((h, i) => (
                  <View key={i} style={styles.highlightRow}>
                    <Ionicons
                      name="checkmark-circle"
                      size={20}
                      color={colors.primary}
                      style={{ marginTop: 1 }}
                    />
                    <Text style={styles.highlightText}>{h}</Text>
                  </View>
                ))}
              </View>
            </>
          )}
        </View>

        <TouchableOpacity
          style={styles.primaryBtn}
          onPress={openStore}
          activeOpacity={0.85}
        >
          <Ionicons name="cloud-download" size={22} color="#fff" />
          <Text style={styles.primaryBtnText}>
            Ouvrir {Platform.OS === "android" && playStoreUrl ? "Play Store" : "App Store"}
          </Text>
        </TouchableOpacity>

        <View style={styles.metaRow}>
          <Text style={styles.metaText}>
            Version installée&nbsp;: {currentVersion}
          </Text>
          <Text style={styles.metaText}>
            Minimum requis&nbsp;: {minVersion}
          </Text>
        </View>

        {onLogout && (
          <TouchableOpacity onPress={onLogout} style={styles.logoutBtn}>
            <Text style={styles.logoutText}>Se déconnecter</Text>
          </TouchableOpacity>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  scroll: {
    padding: 24,
    paddingTop: 16,
    paddingBottom: 40,
    alignItems: "center",
  },
  iconWrap: {
    width: 128,
    height: 128,
    borderRadius: 64,
    backgroundColor: colors.primary + "18",
    alignItems: "center",
    justifyContent: "center",
    marginTop: 20,
    marginBottom: 20,
  },
  title: {
    fontSize: 26,
    fontWeight: "800",
    color: colors.textPrimary,
    textAlign: "center",
    marginBottom: 10,
    letterSpacing: -0.5,
  },
  subtitle: {
    fontSize: 15,
    color: colors.textSecondary,
    textAlign: "center",
    lineHeight: 22,
    marginBottom: 24,
    maxWidth: 340,
  },
  mono: {
    fontWeight: "700",
    color: colors.textPrimary,
  },
  card: {
    width: "100%",
    backgroundColor: colors.card,
    borderRadius: 16,
    padding: 18,
    marginBottom: 24,
    borderWidth: 1,
    borderColor: colors.line,
  },
  message: {
    fontSize: 15,
    lineHeight: 22,
    color: colors.textPrimary,
    marginBottom: 6,
  },
  newsTitle: {
    fontSize: 13,
    fontWeight: "800",
    color: colors.textSecondary,
    textTransform: "uppercase",
    letterSpacing: 0.5,
    marginTop: 14,
    marginBottom: 10,
  },
  highlights: { gap: 8 },
  highlightRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 10,
  },
  highlightText: {
    flex: 1,
    fontSize: 14,
    lineHeight: 20,
    color: colors.textPrimary,
  },
  primaryBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
    backgroundColor: colors.primary,
    paddingVertical: 16,
    paddingHorizontal: 22,
    borderRadius: 999,
    width: "100%",
    shadowColor: colors.primary,
    shadowOpacity: 0.35,
    shadowRadius: 14,
    shadowOffset: { width: 0, height: 6 },
    elevation: 6,
    marginBottom: 20,
  },
  primaryBtnText: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "800",
    letterSpacing: 0.3,
  },
  metaRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    width: "100%",
    marginBottom: 24,
    paddingHorizontal: 4,
  },
  metaText: {
    fontSize: 12,
    color: colors.textSecondary,
  },
  logoutBtn: {
    marginTop: 10,
    paddingVertical: 10,
  },
  logoutText: {
    fontSize: 14,
    color: colors.textSecondary,
    textDecorationLine: "underline",
  },
});
