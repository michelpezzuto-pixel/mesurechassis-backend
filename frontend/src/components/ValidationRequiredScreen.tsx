import React from "react";
import {
  Alert,
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
  message?: string;
  reason?: string;
  onLogout?: () => void;
  onRefresh?: () => Promise<void> | void;
};

/**
 * 🔒 Écran affiché quand le backend renvoie 403 PAYWALL_VALIDATION_REQUIRED.
 *
 * Diffère du PaywallScreen (402 subscription_expired) : ici l'abonnement
 * de la société est OK, mais le compte individuel de l'utilisateur
 * doit être approuvé par son gérant avant de pouvoir utiliser l'app
 * (Phase 2 — double validation Freemium/Team).
 */
export default function ValidationRequiredScreen({
  message,
  reason,
  onLogout,
  onRefresh,
}: Props) {
  const [refreshing, setRefreshing] = React.useState(false);

  const contactManager = () => {
    const subject = encodeURIComponent(
      "MesureChâssis — Validation de mon compte requise",
    );
    const body = encodeURIComponent(
      "Bonjour,\n\n" +
        "Je viens de tenter d'utiliser l'app MesureChâssis mais mon compte " +
        "est en attente de votre validation. Merci d'approuver mon " +
        "rattachement à notre société.\n\n" +
        "Cordialement,",
    );
    const url = `mailto:?subject=${subject}&body=${body}`;
    Linking.openURL(url).catch(() => {
      Alert.alert(
        "Aucun client mail",
        "Aucune app mail détectée. Contactez votre gérant par téléphone.",
      );
    });
  };

  const handleRefresh = async () => {
    if (!onRefresh || refreshing) return;
    setRefreshing(true);
    try {
      await onRefresh();
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <SafeAreaView style={styles.flex} edges={["top", "bottom"]}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <View style={styles.iconWrap}>
          <Ionicons name="hourglass-outline" size={72} color={colors.warning} />
        </View>

        <Text style={styles.title}>Validation en attente</Text>
        <Text style={styles.subtitle}>
          Votre compte est bloqué jusqu&apos;à l&apos;approbation de votre gérant
        </Text>

        <View style={styles.messageBox}>
          <Text style={styles.messageText}>
            {message ||
              "Votre compte nécessite une approbation de votre gérant " +
                "pour continuer à utiliser MesureChâssis. Veuillez " +
                "contacter votre direction pour valider votre rattachement " +
                "à la structure de facturation."}
          </Text>
          {!!reason && (
            <Text style={styles.reasonText}>
              Motif technique : <Text style={styles.reasonStrong}>{reason}</Text>
            </Text>
          )}
        </View>

        <View style={styles.stepsBox}>
          <Text style={styles.stepsTitle}>Étapes à suivre</Text>
          <View style={styles.stepRow}>
            <View style={styles.stepDot}>
              <Text style={styles.stepNum}>1</Text>
            </View>
            <Text style={styles.stepText}>
              Contactez votre gérant / administrateur de société
            </Text>
          </View>
          <View style={styles.stepRow}>
            <View style={styles.stepDot}>
              <Text style={styles.stepNum}>2</Text>
            </View>
            <Text style={styles.stepText}>
              Il valide votre compte depuis son écran{" "}
              <Text style={styles.stepBold}>« Équipe »</Text>
            </Text>
          </View>
          <View style={styles.stepRow}>
            <View style={styles.stepDot}>
              <Text style={styles.stepNum}>3</Text>
            </View>
            <Text style={styles.stepText}>
              Touchez{" "}
              <Text style={styles.stepBold}>« J&apos;ai été validé »</Text>{" "}
              ci-dessous pour rafraîchir
            </Text>
          </View>
        </View>

        <TouchableOpacity
          testID="validation-contact-manager"
          style={styles.primaryBtn}
          onPress={contactManager}
          activeOpacity={0.85}
        >
          <Ionicons name="mail-outline" size={18} color="#fff" />
          <Text style={styles.primaryBtnText}>CONTACTER MON GÉRANT</Text>
        </TouchableOpacity>

        <TouchableOpacity
          testID="validation-refresh"
          style={[styles.secondaryBtn, refreshing && { opacity: 0.5 }]}
          onPress={handleRefresh}
          disabled={refreshing}
          activeOpacity={0.85}
        >
          <Ionicons
            name={refreshing ? "sync" : "refresh-outline"}
            size={18}
            color={colors.primary}
          />
          <Text style={styles.secondaryBtnText}>
            {refreshing ? "Vérification…" : "J'AI ÉTÉ VALIDÉ — RAFRAÎCHIR"}
          </Text>
        </TouchableOpacity>

        {!!onLogout && (
          <TouchableOpacity
            testID="validation-logout"
            style={styles.logoutBtn}
            onPress={onLogout}
            activeOpacity={0.85}
          >
            <Ionicons
              name="log-out-outline"
              size={16}
              color={colors.textSecondary}
            />
            <Text style={styles.logoutText}>Se déconnecter</Text>
          </TouchableOpacity>
        )}

        <Text style={styles.helper}>
          Besoin d&apos;aide ?{"  "}
          <Text
            style={styles.helperLink}
            onPress={() =>
              Linking.openURL(
                "mailto:support@mesurechassis.com?subject=Validation%20compte%20en%20attente",
              )
            }
          >
            support@mesurechassis.com
          </Text>
        </Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: colors.bg },
  scroll: {
    flexGrow: 1,
    padding: 24,
    alignItems: "center",
    justifyContent: "flex-start",
  },
  iconWrap: {
    width: 120,
    height: 120,
    borderRadius: 60,
    backgroundColor: "rgba(255,204,0,0.10)",
    alignItems: "center",
    justifyContent: "center",
    marginTop: Platform.OS === "web" ? 32 : 12,
    marginBottom: 20,
  },
  title: {
    color: colors.textPrimary,
    fontSize: 24,
    fontWeight: "800",
    textAlign: "center",
  },
  subtitle: {
    color: colors.textSecondary,
    fontSize: 14,
    textAlign: "center",
    marginTop: 6,
    marginBottom: 22,
  },
  messageBox: {
    backgroundColor: colors.surface,
    borderRadius: 14,
    padding: 16,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    width: "100%",
  },
  messageText: {
    color: colors.textPrimary,
    fontSize: 14,
    lineHeight: 21,
  },
  reasonText: {
    color: colors.textSecondary,
    fontSize: 11.5,
    marginTop: 10,
    fontStyle: "italic",
  },
  reasonStrong: {
    color: colors.textPrimary,
    fontWeight: "700",
    fontStyle: "normal",
  },
  stepsBox: {
    backgroundColor: colors.surface,
    borderRadius: 14,
    padding: 16,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    width: "100%",
    marginTop: 14,
  },
  stepsTitle: {
    color: colors.textSecondary,
    fontSize: 11,
    fontWeight: "800",
    letterSpacing: 1,
    marginBottom: 10,
  },
  stepRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 12,
    marginBottom: 10,
  },
  stepDot: {
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
  },
  stepNum: { color: "#fff", fontSize: 12, fontWeight: "800" },
  stepText: { color: colors.textPrimary, fontSize: 13.5, flex: 1, lineHeight: 20 },
  stepBold: { fontWeight: "800", color: colors.textPrimary },

  primaryBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    backgroundColor: colors.primary,
    borderRadius: 26,
    paddingVertical: 15,
    marginTop: 22,
    width: "100%",
  },
  primaryBtnText: {
    color: "#fff",
    fontWeight: "800",
    fontSize: 13,
    letterSpacing: 0.5,
  },
  secondaryBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    borderWidth: 1.5,
    borderColor: colors.primary,
    borderRadius: 26,
    paddingVertical: 14,
    marginTop: 10,
    width: "100%",
  },
  secondaryBtnText: {
    color: colors.primary,
    fontWeight: "800",
    fontSize: 12.5,
    letterSpacing: 0.5,
  },
  logoutBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    marginTop: 18,
    padding: 8,
  },
  logoutText: { color: colors.textSecondary, fontSize: 13 },
  helper: {
    color: colors.textSecondary,
    fontSize: 11.5,
    marginTop: 24,
    textAlign: "center",
  },
  helperLink: { color: colors.primary, fontWeight: "600" },
});
