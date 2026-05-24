import React from "react";
import { Linking, Platform, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useAuth } from "@/src/context/AuthContext";
import { colors } from "@/src/theme";

/**
 * 🚧 BETA GRATUITE — bannière d'information.
 *
 * Pendant la phase beta (backend : `BETA_MODE=True` → flag `beta_mode`
 * dans le profil company), on remplace l'ancienne bannière "Essai 90j /
 * Passez Pro" par une bannière verte douce annonçant l'accès gratuit et
 * une invitation à donner du feedback.
 *
 * Quand Stripe sera intégré, il suffira de mettre `BETA_MODE=False` côté
 * backend : le composant détectera l'absence du flag et rebasculera sur
 * l'ancienne logique trial / pro / freemium (à restaurer le moment venu).
 */
export const TRIAL_DAYS = 90;

const SUPPORT_EMAIL = "info@mesurechassis.com";

export default function TrialCountdownBanner() {
  const { company } = useAuth();

  // Pas de bannière tant que le profil société n'est pas chargé
  if (!company) return null;

  // Hors mode beta → on n'affiche rien ici (Stripe / paywall prendra le
  // relais une fois la facturation activée).
  if (!company.beta_mode) return null;

  const openSupportMail = async () => {
    const subject = encodeURIComponent("MesureChâssis — Retour beta");
    const body = encodeURIComponent(
      "Bonjour l'équipe MesureChâssis,\n\nVoici mon retour / suggestion :\n\n"
    );
    const url = `mailto:${SUPPORT_EMAIL}?subject=${subject}&body=${body}`;
    try {
      if (Platform.OS === "web" && typeof window !== "undefined") {
        window.location.href = url;
        return;
      }
      const supported = await Linking.canOpenURL(url);
      if (supported) {
        await Linking.openURL(url);
      }
    } catch {
      /* noop */
    }
  };

  return (
    <TouchableOpacity
      testID="beta-banner"
      activeOpacity={0.7}
      onPress={openSupportMail}
      style={styles.wrap}
    >
      <View style={styles.dot} />
      <Text style={styles.label}>BETA · gratuit</Text>
      <Text style={styles.feedback} numberOfLines={1}>
        Vos retours sont précieux
      </Text>
      <Ionicons name="chevron-forward" size={12} color="#34d399" />
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  wrap: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: "rgba(52, 211, 153, 0.35)",
    backgroundColor: "rgba(52, 211, 153, 0.08)",
    alignSelf: "flex-start",
    marginBottom: 10,
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: "#34d399",
  },
  label: {
    fontSize: 10,
    fontWeight: "900",
    letterSpacing: 0.6,
    color: "#34d399",
  },
  feedback: {
    color: colors.textSecondary,
    fontSize: 10,
    fontStyle: "italic",
    maxWidth: 160,
  },
});
