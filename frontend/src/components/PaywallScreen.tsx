import React, { useState } from "react";
import {
  Alert,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import { colors } from "@/src/theme";

type Props = {
  status?: string;
  expires_at?: string;
  onContactSupport?: () => void;
  onLogout?: () => void;
};

export default function PaywallScreen({
  status,
  expires_at,
  onContactSupport,
  onLogout,
}: Props) {
  const router = useRouter();
  const isSuspended = status === "suspended";
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const [subscribing, setSubscribing] = useState(false);

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

  const onSubscribe = async () => {
    if (!acceptedTerms) {
      Alert.alert(
        "Acceptation requise",
        "Vous devez accepter les CGV et la Politique de Confidentialité pour souscrire."
      );
      return;
    }
    setSubscribing(true);
    // MOCKED : Pas d'intégration Stripe à ce stade.
    setTimeout(() => {
      setSubscribing(false);
      Alert.alert(
        "✅ Demande enregistrée",
        "Votre demande d'abonnement Pro a été enregistrée. " +
          "Notre équipe vous recontactera dans les 24h pour finaliser le paiement et activer votre accès Pro.\n\n" +
          "Pour toute question : support@mesurechassis.fr",
        [{ text: "Compris", style: "default" }]
      );
    }, 600);
  };

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
            {Platform.OS === "ios"
              ? "Votre accès est actuellement suspendu. Pour rétablir votre compte, contactez notre support."
              : "Votre période d'essai de 3 mois est terminée ou votre abonnement n'est pas en ordre. Régularisez votre abonnement pour récupérer l'accès complet à vos chantiers, mesures et exports."}
          </Text>
        </View>

        <View style={styles.infoCard}>
          <View style={styles.row}>
            <Ionicons
              name="information-circle-outline"
              size={18}
              color={colors.textSecondary}
            />
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

        {/* ============ OFFRE PRO ============
         * 🍎 iOS — Apple App Store Guidelines 3.1.1 :
         * sur iOS on n'affiche AUCUN CTA d'achat. À la place,
         * un bandeau neutre invite à contacter le support.
         */}
        {Platform.OS === "ios" ? (
          <View style={styles.iosNoticeCard}>
            <Ionicons
              name="information-circle-outline"
              size={22}
              color={colors.primary}
            />
            <Text style={styles.iosNoticeText}>
              Pour réactiver votre compte, contactez notre support à{" "}
              <Text style={styles.bold}>support@mesurechassis.fr</Text>.
              {"\n\n"}
              Vos données restent stockées en sécurité et seront restaurées
              dès que votre accès sera rétabli.
            </Text>
          </View>
        ) : (
          <View style={styles.proCard}>
          <View style={styles.proHeader}>
            <Ionicons name="rocket" size={20} color={colors.primary} />
            <Text style={styles.proTitle}>PASSER EN PRO</Text>
          </View>
          <Text style={styles.proBody}>
            Accès illimité — Chantiers, mesures, exports PDF / Excel / CSV /
            JSON, gestion d'équipe et statistiques avancées.
          </Text>

          {/* ====== Compliance checkbox ====== */}
          <TouchableOpacity
            testID="legal-terms-checkbox"
            onPress={() => setAcceptedTerms((v) => !v)}
            activeOpacity={0.85}
            style={styles.termsRow}
          >
            <View
              style={[
                styles.checkbox,
                acceptedTerms && styles.checkboxChecked,
              ]}
            >
              {acceptedTerms && (
                <Ionicons name="checkmark" size={14} color="#000" />
              )}
            </View>
            <Text style={styles.termsLabel}>
              J'accepte les{" "}
              <Text
                testID="legal-link-cgv"
                onPress={(e) => {
                  // Empêche le toggle de la checkbox au clic du lien
                  // @ts-ignore — RN Text onPress propagation
                  e?.stopPropagation?.();
                  router.push("/cgv");
                }}
                style={styles.link}
              >
                Conditions Générales de Vente (CGV)
              </Text>
              {" "}et la{" "}
              <Text
                testID="legal-link-privacy"
                onPress={(e) => {
                  // @ts-ignore
                  e?.stopPropagation?.();
                  router.push("/privacy");
                }}
                style={styles.link}
              >
                Politique de Confidentialité
              </Text>
              {" "}de MesureChâssis.
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            testID="paywall-subscribe-button"
            onPress={onSubscribe}
            disabled={!acceptedTerms || subscribing}
            activeOpacity={0.85}
            style={[
              styles.btn,
              styles.btnPrimary,
              (!acceptedTerms || subscribing) && styles.btnDisabled,
            ]}
          >
            <Ionicons
              name={subscribing ? "hourglass" : "card"}
              size={20}
              color="#000"
            />
            <Text style={styles.btnPrimaryText}>
              {subscribing ? "ENVOI EN COURS…" : "S'ABONNER À PRO"}
            </Text>
          </TouchableOpacity>

          {!acceptedTerms && (
            <Text style={styles.hint}>
              ⚠ Cochez la case ci-dessus pour activer le bouton.
            </Text>
          )}
        </View>
        )}

        <Text style={styles.bullet}>📋 Pendant ce verrouillage :</Text>
        <Text style={styles.help}>
          • Aucun chantier ni mesure ne peut être ouvert
        </Text>
        <Text style={styles.help}>• La saisie terrain est désactivée</Text>
        <Text style={styles.help}>
          • Vos données restent en sécurité dans notre base
        </Text>

        <View style={styles.actions}>
          {onContactSupport && (
            <TouchableOpacity
              testID="paywall-contact-button"
              onPress={onContactSupport}
              activeOpacity={0.85}
              style={[styles.btn, styles.btnSecondary]}
            >
              <Ionicons
                name="mail"
                size={18}
                color={colors.textPrimary}
              />
              <Text style={styles.btnSecondaryText}>CONTACTER LE SUPPORT</Text>
            </TouchableOpacity>
          )}
          {onLogout && (
            <TouchableOpacity
              testID="paywall-logout-button"
              onPress={onLogout}
              activeOpacity={0.85}
              style={[styles.btn, styles.btnSecondary]}
            >
              <Ionicons
                name="log-out-outline"
                size={18}
                color={colors.textPrimary}
              />
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
  scroll: {
    padding: 22,
    paddingTop: 30,
    paddingBottom: 60,
    alignItems: "stretch",
  },
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
  alertTitle: {
    color: colors.anomaly,
    fontWeight: "900",
    fontSize: 14,
    letterSpacing: 0.8,
  },
  alertBody: {
    color: colors.textPrimary,
    fontSize: 14,
    lineHeight: 20,
    marginTop: 10,
  },
  infoCard: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    padding: 16,
    marginBottom: 18,
  },
  infoTitle: {
    color: colors.textSecondary,
    fontWeight: "800",
    fontSize: 12,
    letterSpacing: 1,
  },
  infoLine: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginTop: 10,
  },
  infoLabel: { color: colors.textSecondary, fontSize: 13 },
  infoValue: { color: colors.textPrimary, fontWeight: "700", fontSize: 13 },
  statusBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 6,
    borderWidth: 1,
  },
  statusBadgeText: { fontSize: 11, fontWeight: "900", letterSpacing: 1 },
  // ----- Pro card -----
  proCard: {
    backgroundColor: "#0b3b1c",
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "#34d399",
    padding: 18,
    marginBottom: 18,
  },
  // ----- iOS notice card (App Store 3.1.1 compliant) -----
  iosNoticeCard: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 10,
    backgroundColor: "#1a0e05",
    borderWidth: 1,
    borderColor: colors.primary,
    borderRadius: 12,
    padding: 16,
    marginBottom: 18,
  },
  iosNoticeText: {
    color: colors.textPrimary,
    fontSize: 13,
    lineHeight: 19,
    flex: 1,
  },
  bold: {
    fontWeight: "800",
    color: colors.primary,
  },
  proHeader: { flexDirection: "row", alignItems: "center", gap: 8 },
  proTitle: {
    color: "#34d399",
    fontWeight: "900",
    letterSpacing: 1.4,
    fontSize: 14,
  },
  proBody: {
    color: colors.textPrimary,
    fontSize: 13,
    lineHeight: 19,
    marginTop: 10,
    marginBottom: 14,
  },
  termsRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 10,
    marginBottom: 14,
  },
  checkbox: {
    width: 22,
    height: 22,
    borderRadius: 5,
    borderWidth: 2,
    borderColor: colors.borderStrong,
    backgroundColor: "rgba(0,0,0,0.3)",
    alignItems: "center",
    justifyContent: "center",
    marginTop: 1,
  },
  checkboxChecked: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  termsLabel: {
    color: colors.textPrimary,
    fontSize: 12,
    lineHeight: 18,
    flex: 1,
  },
  link: {
    color: "#3B82F6",
    textDecorationLine: "underline",
    fontWeight: "700",
  },
  hint: {
    color: colors.warning,
    fontSize: 11,
    textAlign: "center",
    marginTop: 8,
    fontWeight: "700",
  },
  // ----- General bullets/help -----
  bullet: {
    color: colors.textPrimary,
    fontWeight: "800",
    marginTop: 8,
    marginBottom: 6,
    letterSpacing: 0.4,
  },
  help: {
    color: colors.textSecondary,
    fontSize: 13,
    lineHeight: 19,
    marginBottom: 4,
  },
  // ----- Buttons -----
  actions: { marginTop: 16, gap: 10 },
  btn: {
    minHeight: 52,
    borderRadius: 12,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
    paddingHorizontal: 14,
  },
  btnPrimary: { backgroundColor: colors.primary },
  btnPrimaryText: {
    color: "#000",
    fontWeight: "900",
    letterSpacing: 1,
    fontSize: 13,
  },
  btnDisabled: { backgroundColor: "#3a3a3a", opacity: 0.55 },
  btnSecondary: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderStrong,
  },
  btnSecondaryText: {
    color: colors.textPrimary,
    fontWeight: "800",
    letterSpacing: 0.8,
    fontSize: 12,
  },
});
