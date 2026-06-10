import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
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
import { useRouter, useFocusEffect } from "expo-router";
import * as WebBrowser from "expo-web-browser";
import { api } from "@/src/services/api";
import { colors } from "@/src/theme";

/**
 * Écran « Mon abonnement »
 *
 * Affiche les 3 plans MesureChâssis, le statut d'abonnement actuel
 * (essai gratuit, actif, en retard, annulé) et permet de souscrire
 * ou ouvrir le portail Stripe pour gérer son abonnement.
 *
 * Architecture :
 *   - L'app appelle le backend pour créer une session Stripe Checkout
 *   - Le backend renvoie l'URL hébergée Stripe
 *   - On l'ouvre dans un in-app browser (expo-web-browser)
 *   - Stripe redirige vers mesurechassis://stripe-success — l'app se rouvre
 *   - On rafraîchit alors le statut depuis le backend (source de vérité)
 */
type SubscriptionStatus = {
  has_subscription: boolean;
  plan: string | null;
  status: string | null;
  trial_end: string | null;
  current_period_end: string | null;
  is_locked: boolean;
  days_left_in_trial: number | null;
};

type PlanKey = "solo" | "entreprise" | "pro";

const PLANS: {
  key: PlanKey;
  name: string;
  price: string;
  unit: string;
  features: string[];
  badge?: string;
  highlight?: boolean;
}[] = [
  {
    key: "solo",
    name: "Artisan Solo",
    price: "24,99 €",
    unit: "/mois",
    features: [
      "1 utilisateur (vous-même)",
      "Chantiers illimités",
      "Exports PDF & Excel",
      "Support par email",
    ],
  },
  {
    key: "entreprise",
    name: "Entreprise",
    price: "59,99 €",
    unit: "/mois",
    badge: "POPULAIRE",
    highlight: true,
    features: [
      "3 utilisateurs inclus",
      "Combinaison libre commercial + technicien",
      "Utilisateur supplémentaire : +4,99 €/mois",
      "Tableaux de bord équipe",
      "Support prioritaire",
    ],
  },
  {
    key: "pro",
    name: "Entreprise Pro",
    price: "89,99 €",
    unit: "/mois",
    features: [
      "6 utilisateurs inclus",
      "Utilisateur supplémentaire : +9,99 €/mois",
      "📡 Bluetooth (mesure laser) — à venir",
      "🚀 Fonctionnalités avancées pour faciliter encore plus vos prises de mesures",
      "Support dédié",
    ],
  },
];

export default function SubscriptionScreen() {
  const router = useRouter();
  const [status, setStatus] = useState<SubscriptionStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [subscribing, setSubscribing] = useState<PlanKey | null>(null);
  const [openingPortal, setOpeningPortal] = useState(false);

  const fetchStatus = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get<SubscriptionStatus>(
        "/stripe/subscription-status",
      );
      setStatus(res.data);
    } catch {
      setStatus({
        has_subscription: false,
        plan: null,
        status: null,
        trial_end: null,
        current_period_end: null,
        is_locked: true,
        days_left_in_trial: null,
      });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchStatus();
  }, [fetchStatus]);

  // Recharger à chaque retour sur l'écran (après un retour de Stripe Checkout)
  useFocusEffect(
    useCallback(() => {
      void fetchStatus();
    }, [fetchStatus]),
  );

  // Listener deep link pour fermer le browser quand Stripe redirige
  useEffect(() => {
    const sub = Linking.addEventListener("url", (event) => {
      if (
        event.url.includes("stripe-success") ||
        event.url.includes("stripe-cancel") ||
        event.url.includes("stripe-portal-return")
      ) {
        if (Platform.OS !== "web") {
          WebBrowser.dismissBrowser();
        }
        // Rafraîchit le statut après un petit délai pour laisser
        // au webhook le temps d'arriver côté backend.
        setTimeout(() => void fetchStatus(), 1500);
      }
    });
    return () => sub.remove();
  }, [fetchStatus]);

  const handleSubscribe = async (plan: PlanKey) => {
    setSubscribing(plan);
    try {
      const res = await api.post<{ checkout_url: string }>(
        "/stripe/create-checkout-session",
        { plan },
      );
      const url = res.data?.checkout_url;
      if (!url) throw new Error("URL Checkout manquante");

      if (Platform.OS === "web") {
        window.location.href = url;
        return;
      }

      await WebBrowser.openBrowserAsync(url, {
        dismissButtonStyle: "close",
        presentationStyle: WebBrowser.WebBrowserPresentationStyle.PAGE_SHEET,
      });
      // Après fermeture du browser : refresh
      await fetchStatus();
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      Alert.alert(
        "Souscription impossible",
        typeof detail === "string"
          ? detail
          : "Une erreur est survenue lors de l'ouverture du paiement. Réessayez dans quelques instants.",
      );
    } finally {
      setSubscribing(null);
    }
  };

  const handleManageSubscription = async () => {
    setOpeningPortal(true);
    try {
      const res = await api.post<{ portal_url: string }>(
        "/stripe/customer-portal",
        {},
      );
      const url = res.data?.portal_url;
      if (!url) throw new Error("URL portail manquante");

      if (Platform.OS === "web") {
        window.location.href = url;
        return;
      }

      await WebBrowser.openBrowserAsync(url, {
        dismissButtonStyle: "close",
        presentationStyle: WebBrowser.WebBrowserPresentationStyle.PAGE_SHEET,
      });
      await fetchStatus();
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      Alert.alert(
        "Portail indisponible",
        typeof detail === "string"
          ? detail
          : "Impossible d'ouvrir le portail de gestion. Réessayez plus tard.",
      );
    } finally {
      setOpeningPortal(false);
    }
  };

  const currentPlanKey = (status?.plan || "").toLowerCase() as PlanKey | "";
  const statusLabel = computeStatusLabel(status);

  return (
    <SafeAreaView style={styles.safe} edges={["top", "bottom"]}>
      <View style={styles.header}>
        <TouchableOpacity
          onPress={() => router.back()}
          style={styles.backBtn}
          hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
        >
          <Ionicons name="chevron-back" size={26} color={colors.textPrimary} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Mon abonnement</Text>
        <View style={{ width: 26 }} />
      </View>

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.scrollContent}
      >
        {/* ===== BANNIÈRE DE STATUT ===== */}
        {loading ? (
          <View style={styles.statusCard}>
            <ActivityIndicator color={colors.primary} />
          </View>
        ) : (
          <View
            style={[
              styles.statusCard,
              statusLabel.color === "green" && styles.statusCardOk,
              statusLabel.color === "orange" && styles.statusCardWarn,
              statusLabel.color === "red" && styles.statusCardDanger,
            ]}
          >
            <Ionicons
              name={statusLabel.icon}
              size={28}
              color={
                statusLabel.color === "green"
                  ? "#22c55e"
                  : statusLabel.color === "orange"
                    ? colors.warning
                    : statusLabel.color === "red"
                      ? colors.anomaly
                      : colors.textSecondary
              }
            />
            <View style={{ flex: 1, marginLeft: 12 }}>
              <Text style={styles.statusTitle}>{statusLabel.title}</Text>
              <Text style={styles.statusBody}>{statusLabel.body}</Text>
            </View>
          </View>
        )}

        {/* ===== BOUTON MANAGE SI ABONNEMENT EXISTANT =====
         * 🍎 Masqué sur iOS — Apple App Store Guideline 3.1.1 :
         * une app B2B SaaS ne peut PAS proposer la gestion d'un abonnement
         * payé hors IAP depuis l'app iOS. Sur iOS, l'utilisateur est invité
         * à se rendre sur mesurechassis.com. */}
        {status?.has_subscription && Platform.OS !== "ios" && (
          <TouchableOpacity
            style={[styles.manageBtn, openingPortal && { opacity: 0.6 }]}
            onPress={handleManageSubscription}
            disabled={openingPortal}
          >
            {openingPortal ? (
              <ActivityIndicator color={colors.textPrimary} />
            ) : (
              <>
                <Ionicons
                  name="settings-outline"
                  size={18}
                  color={colors.textPrimary}
                />
                <Text style={styles.manageBtnText}>
                  GÉRER MON ABONNEMENT
                </Text>
              </>
            )}
          </TouchableOpacity>
        )}

        {/* 🍎 iOS — Bandeau d'information remplaçant les CTA Stripe.
         * Conforme à la règle App Store : aucune mention de paiement
         * externe, juste un rappel que la gestion se fait sur le site web. */}
        {Platform.OS === "ios" && (
          <View style={styles.iosNoticeBox}>
            <Ionicons
              name="information-circle-outline"
              size={20}
              color={colors.primary}
            />
            <View style={{ flex: 1, marginLeft: 10 }}>
              <Text style={styles.iosNoticeTitle}>Gestion sur le web</Text>
              <Text style={styles.iosNoticeBody}>
                Pour souscrire, changer ou annuler votre formule, rendez-vous
                sur <Text style={{ fontWeight: "800" }}>mesurechassis.com</Text>{" "}
                depuis un navigateur. Votre compte est synchronisé
                automatiquement.
              </Text>
            </View>
          </View>
        )}

        {/* ===== LISTE DES PLANS =====
         * 🍎 Masquée sur iOS (App Store 3.1.1) — voir bandeau d'info ci-dessus.
         */}
        {Platform.OS !== "ios" && (
          <>
            <Text style={styles.sectionTitle}>
              {status?.has_subscription ? "Changer de plan" : "Choisir un plan"}
            </Text>
            <Text style={styles.sectionHint}>
              ✨ 3 mois gratuits pour démarrer, sans engagement. Annulez à tout
              moment depuis le portail.
            </Text>

            {PLANS.map((plan) => {
              const isCurrent = currentPlanKey === plan.key;
              const isLoading = subscribing === plan.key;
              return (
                <View
                  key={plan.key}
                  style={[
                    styles.planCard,
                    plan.highlight && styles.planCardHighlight,
                    isCurrent && styles.planCardCurrent,
                  ]}
                >
                  {plan.badge && !isCurrent && (
                    <View style={styles.badge}>
                      <Text style={styles.badgeText}>{plan.badge}</Text>
                    </View>
                  )}
                  {isCurrent && (
                    <View style={[styles.badge, styles.badgeCurrent]}>
                      <Text style={styles.badgeText}>VOTRE PLAN</Text>
                    </View>
                  )}
                  <Text style={styles.planName}>{plan.name}</Text>
                  <View style={styles.priceRow}>
                    <Text style={styles.priceValue}>{plan.price}</Text>
                    <Text style={styles.priceUnit}>{plan.unit}</Text>
                  </View>
                  {plan.features.map((f, i) => (
                    <View key={i} style={styles.featureRow}>
                      <Ionicons name="checkmark" size={16} color={colors.primary} />
                      <Text style={styles.featureText}>{f}</Text>
                    </View>
                  ))}
                  {!isCurrent && (
                    <TouchableOpacity
                      style={[
                        styles.subscribeBtn,
                        plan.highlight && styles.subscribeBtnHighlight,
                        isLoading && { opacity: 0.6 },
                      ]}
                      onPress={() => handleSubscribe(plan.key)}
                      disabled={isLoading || subscribing !== null}
                    >
                      {isLoading ? (
                        <ActivityIndicator color="#000" />
                      ) : (
                        <Text style={styles.subscribeBtnText}>
                          {status?.has_subscription
                            ? "Passer à ce plan"
                            : "Démarrer l'essai gratuit"}
                        </Text>
                      )}
                    </TouchableOpacity>
                  )}
                </View>
              );
            })}

            <Text style={styles.smallNote}>
              🔒 Paiement sécurisé via Stripe. Cartes bancaires et SEPA acceptés.
              {"\n"}TVA collectée selon votre pays de résidence.
            </Text>
          </>
        )}

        <View style={{ height: 32 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

function computeStatusLabel(s: SubscriptionStatus | null) {
  if (!s || !s.has_subscription) {
    return {
      title: "Aucun abonnement actif",
      body: "Démarrez votre essai gratuit de 3 mois en choisissant un plan ci-dessous.",
      color: "neutral" as const,
      icon: "lock-closed-outline" as const,
    };
  }
  if (s.status === "trialing") {
    return {
      title: `Essai gratuit en cours`,
      body: `Il vous reste ${s.days_left_in_trial ?? "?"} jour(s). Aucun prélèvement avant la fin de l'essai.`,
      color: "green" as const,
      icon: "gift-outline" as const,
    };
  }
  if (s.status === "active") {
    return {
      title: "Abonnement actif ✨",
      body: `Renouvellement automatique le ${formatDate(s.current_period_end)}.`,
      color: "green" as const,
      icon: "checkmark-circle" as const,
    };
  }
  if (s.status === "past_due") {
    return {
      title: "Paiement en retard ⚠️",
      body: "Une facture est en attente de règlement. Mettez à jour votre moyen de paiement pour éviter le verrouillage.",
      color: "orange" as const,
      icon: "warning-outline" as const,
    };
  }
  if (s.status === "canceled" || s.status === "unpaid") {
    return {
      title: "Abonnement annulé",
      body: "Souscrivez à nouveau pour réactiver l'accès à toutes les fonctionnalités.",
      color: "red" as const,
      icon: "close-circle-outline" as const,
    };
  }
  return {
    title: `Statut : ${s.status ?? "inconnu"}`,
    body: "Consultez votre portail pour plus de détails.",
    color: "neutral" as const,
    icon: "information-circle-outline" as const,
  };
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("fr-FR", {
      day: "2-digit",
      month: "long",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.borderSubtle,
  },
  backBtn: { padding: 4 },
  headerTitle: {
    color: colors.textPrimary,
    fontSize: 17,
    fontWeight: "600",
  },
  scroll: { flex: 1 },
  scrollContent: { padding: 16 },
  statusCard: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
  },
  statusCardOk: { borderColor: "#22c55e44" },
  statusCardWarn: { borderColor: colors.warning + "66" },
  statusCardDanger: { borderColor: colors.anomaly + "66" },
  statusTitle: {
    color: colors.textPrimary,
    fontSize: 15,
    fontWeight: "700",
    marginBottom: 4,
  },
  statusBody: {
    color: colors.textSecondary,
    fontSize: 13,
    lineHeight: 18,
  },
  manageBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    paddingVertical: 14,
    borderRadius: 10,
    marginBottom: 24,
  },
  manageBtnText: {
    color: colors.textPrimary,
    fontWeight: "700",
    fontSize: 13,
  },
  // 🍎 Bandeau iOS (App Store 3.1.1) — remplace les CTA Stripe
  iosNoticeBox: {
    flexDirection: "row",
    alignItems: "flex-start",
    backgroundColor: "#1a0e05",
    borderWidth: 1,
    borderColor: colors.primary,
    borderRadius: 12,
    padding: 14,
    marginBottom: 24,
  },
  iosNoticeTitle: {
    color: colors.primary,
    fontSize: 14,
    fontWeight: "800",
    marginBottom: 4,
  },
  iosNoticeBody: {
    color: colors.textSecondary,
    fontSize: 13,
    lineHeight: 18,
  },
  sectionTitle: {
    color: colors.textPrimary,
    fontSize: 18,
    fontWeight: "800",
    marginTop: 8,
    marginBottom: 4,
  },
  sectionHint: {
    color: colors.textSecondary,
    fontSize: 13,
    marginBottom: 16,
    lineHeight: 18,
  },
  planCard: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    borderRadius: 14,
    padding: 18,
    marginBottom: 16,
    position: "relative",
  },
  planCardHighlight: {
    borderColor: colors.primary,
    borderWidth: 2,
  },
  planCardCurrent: {
    borderColor: "#22c55e",
    borderWidth: 2,
  },
  badge: {
    position: "absolute",
    top: -10,
    right: 16,
    backgroundColor: colors.primary,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 6,
  },
  badgeCurrent: { backgroundColor: "#22c55e" },
  badgeText: { color: "#000", fontSize: 11, fontWeight: "800" },
  planName: {
    color: colors.textPrimary,
    fontSize: 17,
    fontWeight: "800",
    marginBottom: 6,
  },
  priceRow: {
    flexDirection: "row",
    alignItems: "baseline",
    marginBottom: 14,
  },
  priceValue: {
    color: colors.primary,
    fontSize: 28,
    fontWeight: "900",
  },
  priceUnit: {
    color: colors.textSecondary,
    fontSize: 14,
    marginLeft: 4,
  },
  featureRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 8,
    marginBottom: 6,
  },
  featureText: {
    color: colors.textSecondary,
    fontSize: 13,
    flex: 1,
    lineHeight: 18,
  },
  subscribeBtn: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.primary,
    paddingVertical: 14,
    borderRadius: 10,
    marginTop: 12,
    alignItems: "center",
  },
  subscribeBtnHighlight: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  subscribeBtnText: {
    color: "#000",
    fontWeight: "800",
    fontSize: 14,
  },
  smallNote: {
    color: colors.textSecondary,
    fontSize: 11,
    textAlign: "center",
    marginTop: 8,
    lineHeight: 16,
  },
});
