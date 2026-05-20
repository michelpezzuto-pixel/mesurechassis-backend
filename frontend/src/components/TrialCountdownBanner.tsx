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
      activeOpacity={0.85}
      onPress={openSupportMail}
      style={styles.wrap}
    >
      <View style={styles.iconWrap}>
        <Ionicons name="rocket" size={20} color="#34d399" />
      </View>
      <View style={{ flex: 1 }}>
        <Text style={styles.title}>BETA GRATUITE · ACCÈS COMPLET</Text>
        <Text style={styles.sub}>
          Vous avez accès à toutes les fonctionnalités pendant la phase de test.
        </Text>
        <Text style={styles.feedback}>
          💬 Vos retours nous aident à grandir ! Signalez-nous la moindre idée
          via {SUPPORT_EMAIL}
        </Text>
      </View>
      <Ionicons name="chevron-forward" size={18} color="#34d399" />
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  wrap: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    paddingHorizontal: 14,
    paddingVertical: 12,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#34d399",
    backgroundColor: "#0b3b1c",
    marginBottom: 12,
  },
  iconWrap: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "rgba(255,255,255,0.06)",
  },
  title: {
    fontSize: 12,
    fontWeight: "900",
    letterSpacing: 0.8,
    color: "#34d399",
  },
  sub: {
    color: colors.textPrimary,
    fontSize: 12,
    marginTop: 2,
    fontWeight: "600",
  },
  feedback: {
    color: colors.textSecondary,
    fontSize: 11,
    marginTop: 4,
    fontStyle: "italic",
  },
});
