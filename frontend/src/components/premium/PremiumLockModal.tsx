/**
 * 🔒 PremiumLockModal — Modal qui apparaît quand un utilisateur tape sur
 * une forme verrouillée (Freemium).
 *
 * ⚠️ Comportement iOS / Android pour respecter la Guideline Apple 3.1.3(b)
 * (Multiplatform Services) :
 *
 * - Sur iOS  : message générique, AUCUNE mention de prix, AUCUN bouton
 *   redirigeant vers un paiement externe. L'utilisateur doit aller sur
 *   mesurechassis.com depuis son navigateur pour gérer son abonnement,
 *   sans que l'app iOS le lui suggère activement.
 *
 * - Sur Android / Web : pitch commercial assumé avec prix et CTA vers
 *   l'écran d'abonnement interne.
 */
import React from "react";
import { Modal, Platform, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import { useTranslation } from "react-i18next";
import { colors } from "@/src/theme";
import { PREMIUM_PRICE_MONTHLY } from "@/src/lib/freemium";

export function PremiumLockModal({
  visible,
  onClose,
  shapeLabel,
}: {
  visible: boolean;
  onClose: () => void;
  shapeLabel?: string;
}) {
  const router = useRouter();
  const { t } = useTranslation();
  const isIOS = Platform.OS === "ios";

  const handleUpgrade = () => {
    onClose();
    router.push("/subscription");
  };

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={onClose}
    >
      <View style={styles.backdrop}>
        <View style={styles.card}>
          <View style={styles.iconCircle}>
            <Ionicons name="lock-closed" size={32} color={colors.primary} />
          </View>

          {isIOS ? (
            // ───── iOS : message neutre, aucun prix, aucun lien externe ─────
            <>
              <Text style={styles.title}>
                {t("premium.iosTitle", {
                  defaultValue: "Forme avancée",
                })}
              </Text>
              {shapeLabel ? (
                <Text style={styles.shapeBadge}>{shapeLabel}</Text>
              ) : null}
              <Text style={styles.body}>
                {t("premium.iosBody", {
                  defaultValue:
                    "Cette forme n'est pas disponible avec votre compte actuel. Les paramètres de votre compte sont gérés depuis votre profil utilisateur.",
                })}
              </Text>
              <TouchableOpacity style={styles.primaryBtn} onPress={onClose}>
                <Text style={styles.primaryBtnText}>
                  {t("common.close", { defaultValue: "Fermer" })}
                </Text>
              </TouchableOpacity>
            </>
          ) : (
            // ───── Android / Web : pitch complet avec prix + CTA ─────
            <>
              <Text style={styles.title}>
                {t("premium.title", {
                  defaultValue: "Forme Premium 🔒",
                })}
              </Text>
              {shapeLabel ? (
                <Text style={styles.shapeBadge}>{shapeLabel}</Text>
              ) : null}
              <Text style={styles.body}>
                {t("premium.body", {
                  defaultValue:
                    "Débloquez cette forme et les 6 autres formes avancées avec Premium. Cintrée, anse-de-panier, œil-de-bœuf, bow-window…",
                })}
              </Text>
              <View style={styles.priceRow}>
                <Text style={styles.price}>{PREMIUM_PRICE_MONTHLY}</Text>
                <Text style={styles.priceUnit}>
                  {t("premium.perMonth", { defaultValue: "/mois" })}
                </Text>
              </View>
              <TouchableOpacity
                style={styles.primaryBtn}
                onPress={handleUpgrade}
                testID="premium-upgrade-btn"
              >
                <Ionicons name="rocket" size={18} color="#fff" />
                <Text style={styles.primaryBtnText}>
                  {t("premium.cta", { defaultValue: "Voir les formules" })}
                </Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.secondaryBtn} onPress={onClose}>
                <Text style={styles.secondaryBtnText}>
                  {t("common.cancel", { defaultValue: "Plus tard" })}
                </Text>
              </TouchableOpacity>
            </>
          )}
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.55)",
    justifyContent: "center",
    alignItems: "center",
    padding: 24,
  },
  card: {
    backgroundColor: "#fff",
    borderRadius: 20,
    padding: 28,
    width: "100%",
    maxWidth: 420,
    alignItems: "center",
    shadowColor: "#000",
    shadowOpacity: 0.2,
    shadowRadius: 20,
    shadowOffset: { width: 0, height: 10 },
    elevation: 12,
  },
  iconCircle: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: `${colors.primary}15`,
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 12,
  },
  title: {
    fontSize: 20,
    fontWeight: "800",
    color: colors.textPrimary,
    textAlign: "center",
    marginBottom: 6,
  },
  shapeBadge: {
    fontSize: 13,
    fontWeight: "600",
    color: colors.primary,
    backgroundColor: `${colors.primary}12`,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 999,
    overflow: "hidden",
    marginBottom: 12,
  },
  body: {
    fontSize: 14,
    color: colors.textSecondary,
    textAlign: "center",
    lineHeight: 20,
    marginBottom: 18,
  },
  priceRow: {
    flexDirection: "row",
    alignItems: "baseline",
    marginBottom: 16,
  },
  price: {
    fontSize: 32,
    fontWeight: "800",
    color: colors.primary,
  },
  priceUnit: {
    fontSize: 14,
    color: colors.textSecondary,
    marginLeft: 4,
  },
  primaryBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    backgroundColor: colors.primary,
    paddingHorizontal: 22,
    paddingVertical: 13,
    borderRadius: 12,
    width: "100%",
  },
  primaryBtnText: {
    color: "#fff",
    fontWeight: "700",
    fontSize: 15,
  },
  secondaryBtn: {
    marginTop: 10,
    paddingVertical: 10,
    paddingHorizontal: 18,
  },
  secondaryBtnText: {
    color: colors.textSecondary,
    fontSize: 14,
    fontWeight: "600",
  },
});
