import React from "react";
import {
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
  status?: string;
  expires_at?: string;
  onContactSupport?: () => void;
  onLogout?: () => void;
};

export default function PaywallScreen({ status, expires_at, onContactSupport, onLogout }: Props) {
  const isSuspended = status === "suspended";
  const formattedExpiry = (() => {
    if (!expires_at) return null;
    try {
      const d = new Date(expires_at);
      return d.toLocaleDateString("fr-FR", {
        weekday: "long",
        day: "2-digit",
        month: "long",
        year: "numeric",
      });
    } catch {
      return expires_at;
    }
  })();

  return (
    <SafeAreaView style={styles.flex}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <View style={styles.iconWrap}>
          <Ionicons name="lock-closed" size={64} color={colors.warning} />
        </View>
        <Text style={styles.title}>ACCÈS BLOQUÉ</Text>

        <View style={styles.alertCard}>
          <View style={styles.row}>
            <Ionicons name="warning" size={22} color={colors.anomaly} />
            <Text style={styles.alertTitle}>Votre accès a expiré</Text>
          </View>
          <Text style={styles.alertBody}>
            Votre période de 3 mois est terminée ou votre abonnement n'est pas en ordre.
            Veuillez régulariser votre abonnement pour récupérer l'accès à vos chantiers
            et à vos outils de mesurage.
          </Text>
        </View>

        <View style={styles.infoCard}>
          <View style={styles.row}>
            <Ionicons name="information-circle-outline" size={18} color={colors.textSecondary} />
            <Text style={styles.infoTitle}>État de votre abonnement</Text>
          </View>
          <View style={styles.infoLine}>
            <Text style={styles.infoLabel}>Statut</Text>
            <View
              style={[
                styles.statusBadge,
                isSuspended
                  ? { backgroundColor: "#3a1010", borderColor: colors.anomaly }
                  : { backgroundColor: "#2a1c08", borderColor: colors.warning },
              ]}
            >
              <Text
                style={[
                  styles.statusBadgeText,
                  { color: isSuspended ? colors.anomaly : colors.warning },
                ]}
              >
                {isSuspended ? "SUSPENDU" : "EXPIRÉ"}
              </Text>
            </View>
          </View>
          {formattedExpiry && (
            <View style={styles.infoLine}>
              <Text style={styles.infoLabel}>Date d'expiration</Text>
              <Text style={styles.infoValue}>{formattedExpiry}</Text>
            </View>
          )}
        </View>

        <Text style={styles.bullet}>📋 Pendant ce verrouillage :</Text>
        <Text style={styles.help}>• Aucun chantier ni mesure ne peut être ouvert</Text>
        <Text style={styles.help}>• La saisie terrain est désactivée</Text>
        <Text style={styles.help}>• Vos données restent en sécurité dans notre base</Text>

        <View style={styles.actions}>
          {onContactSupport && (
            <TouchableOpacity
              testID="paywall-contact-button"
              onPress={onContactSupport}
              activeOpacity={0.85}
              style={[styles.btn, styles.btnPrimary]}
            >
              <Ionicons name="mail" size={20} color="#000" />
              <Text style={styles.btnPrimaryText}>CONTACTER LE SUPPORT</Text>
            </TouchableOpacity>
          )}
          {onLogout && (
            <TouchableOpacity
              testID="paywall-logout-button"
              onPress={onLogout}
              activeOpacity={0.85}
              style={[styles.btn, styles.btnSecondary]}
            >
              <Ionicons name="log-out-outline" size={20} color={colors.textPrimary} />
              <Text style={styles.btnSecondaryText}>SE DÉCONNECTER</Text>
            </TouchableOpacity>
          )}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: colors.bg },
  scroll: { padding: 22, paddingTop: 30, paddingBottom: 60, alignItems: "stretch" },
  iconWrap: { alignItems: "center", marginBottom: 18 },
  title: {
    color: colors.textPrimary,
    fontWeight: "900",
    fontSize: 22,
    letterSpacing: 2,
    textAlign: "center",
    marginBottom: 18,
  },
  row: { flexDirection: "row", alignItems: "center", gap: 8 },
  alertCard: {
    backgroundColor: "#1f0a0a",
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.anomaly,
    padding: 16,
    marginBottom: 14,
  },
  alertTitle: { color: colors.anomaly, fontWeight: "900", fontSize: 14, letterSpacing: 0.8 },
  alertBody: { color: colors.textPrimary, fontSize: 14, lineHeight: 20, marginTop: 10 },
  infoCard: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    padding: 16,
    marginBottom: 18,
  },
  infoTitle: { color: colors.textSecondary, fontWeight: "800", fontSize: 12, letterSpacing: 1 },
  infoLine: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginTop: 10,
  },
  infoLabel: { color: colors.textSecondary, fontSize: 12 },
  infoValue: { color: colors.textPrimary, fontWeight: "700", fontSize: 13 },
  statusBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 6,
    borderWidth: 1,
  },
  statusBadgeText: { fontSize: 11, fontWeight: "900", letterSpacing: 0.8 },
  bullet: { color: colors.textPrimary, fontWeight: "800", fontSize: 13, marginTop: 4 },
  help: { color: colors.textSecondary, fontSize: 13, marginTop: 4, lineHeight: 18 },
  actions: { marginTop: 24, gap: 10 },
  btn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    minHeight: 54,
    borderRadius: 12,
    paddingHorizontal: 16,
  },
  btnPrimary: { backgroundColor: colors.primary },
  btnPrimaryText: { color: "#000", fontWeight: "900", fontSize: 14, letterSpacing: 1 },
  btnSecondary: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
  },
  btnSecondaryText: { color: colors.textPrimary, fontWeight: "800", fontSize: 13 },
});
