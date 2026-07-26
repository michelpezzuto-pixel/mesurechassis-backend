/**
 * FreeLimitPaywallModal.tsx — Modal Paywall pour limites Freemium (juillet 2026)
 * =============================================================================
 * S'affiche automatiquement quand le backend renvoie HTTP 402 avec
 * `code: "free_limit_reached"`. Écoute le bus d'événements exposé par
 * services/api.ts (onFreeLimitReached).
 *
 * Design : cohérent avec PaywallScreen existant, mais moins agressif
 * (modal in-app, pas full-screen), avec bouton "Passer à Artisan Pro"
 * qui ouvre Stripe Checkout dans le navigateur (retour app via
 * deep-link mesurechassis://stripe-success).
 */
import React, { useEffect, useState, useCallback } from "react";
import {
  Modal,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
  Linking,
  ActivityIndicator,
  Alert,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { colors } from "@/src/theme";
import { api, onFreeLimitReached, type FreeLimitState } from "@/src/services/api";

// Mapping limite → icône + titre + CTA principal
const LIMIT_CONFIG: Record<
  FreeLimitState["limitType"],
  { icon: keyof typeof Ionicons.glyphMap; title: string; subtitle: string }
> = {
  chantiers: {
    icon: "briefcase-outline",
    title: "Tu as atteint la limite de 3 chantiers",
    subtitle: "Passe à Artisan Pro pour créer des chantiers illimités.",
  },
  ouvertures: {
    icon: "resize-outline",
    title: "5 ouvertures maximum en plan gratuit",
    subtitle: "Passe à Artisan Pro pour mesurer sans limite.",
  },
  yann_question: {
    icon: "chatbubbles-outline",
    title: "10 questions Yann par mois épuisées",
    subtitle: "Passe à Artisan Pro pour poser autant de questions que tu veux.",
  },
  ia_cdc_import: {
    icon: "document-text-outline",
    title: "3 imports IA / mois atteints",
    subtitle: "Passe à Artisan Pro pour des imports illimités du cahier des charges.",
  },
  export_format: {
    icon: "download-outline",
    title: "Export Excel/CSV réservé aux plans Pro",
    subtitle: "L'export PDF reste gratuit. Passe à Pro pour tous les formats.",
  },
};

export default function FreeLimitPaywallModal() {
  const [limit, setLimit] = useState<FreeLimitState | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const unsubscribe = onFreeLimitReached((state) => {
      setLimit(state);
    });
    return unsubscribe;
  }, []);

  const config = limit ? LIMIT_CONFIG[limit.limitType] : null;

  const handleUpgrade = useCallback(async () => {
    setLoading(true);
    try {
      // Appel backend pour créer une session Stripe Checkout
      const { data } = await api.post("/stripe/create-checkout-session", {
        plan: "artisan_pro", // alias explicite (19€/mois)
      });
      const url = data?.checkout_url;
      if (url) {
        setLimit(null); // Ferme le modal avant redirection
        await Linking.openURL(url);
      } else {
        throw new Error("Pas d'URL Stripe reçue");
      }
    } catch (e: any) {
      console.warn("[Paywall] Stripe checkout failed:", e?.message || e);
      Alert.alert(
        "Impossible de démarrer le paiement",
        "Une erreur est survenue. Veuillez réessayer dans quelques instants.",
        [{ text: "OK" }]
      );
    } finally {
      setLoading(false);
    }
  }, []);

  const handleClose = () => setLimit(null);

  if (!limit || !config) return null;

  return (
    <Modal
      visible={true}
      transparent
      animationType="fade"
      onRequestClose={handleClose}
    >
      <View style={styles.backdrop}>
        <View style={styles.card}>
          <TouchableOpacity onPress={handleClose} style={styles.closeBtn}>
            <Ionicons name="close" size={24} color="#aaa" />
          </TouchableOpacity>

          <View style={styles.iconWrap}>
            <Ionicons name={config.icon} size={40} color={colors.primary} />
          </View>

          <Text style={styles.title}>{config.title}</Text>
          <Text style={styles.subtitle}>{config.subtitle}</Text>

          <View style={styles.usageBar}>
            <View style={styles.usageText}>
              <Text style={styles.usageLabel}>Ton usage :</Text>
              <Text style={styles.usageValue}>
                {limit.current} / {limit.maximum}
              </Text>
            </View>
            <View style={styles.progressBar}>
              <View
                style={[
                  styles.progressFill,
                  { width: `${Math.min(100, (limit.current / limit.maximum) * 100)}%` },
                ]}
              />
            </View>
          </View>

          {/* CTA principal - Passe à Pro */}
          <TouchableOpacity
            style={[styles.primaryBtn, loading && { opacity: 0.6 }]}
            onPress={handleUpgrade}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <>
                <Text style={styles.primaryBtnText}>Passe à Artisan Pro</Text>
                <Text style={styles.primaryBtnPrice}>19 €/mois</Text>
              </>
            )}
          </TouchableOpacity>

          {/* Features Pro */}
          <View style={styles.featuresList}>
            <FeatureRow text="Chantiers & ouvertures illimités" />
            <FeatureRow text="Yann IA illimité" />
            <FeatureRow text="Import IA CDC illimité" />
            <FeatureRow text="Laser Bluetooth + tous les exports" />
            <FeatureRow text="Résiliation en 1 clic" />
          </View>

          <TouchableOpacity onPress={handleClose} style={styles.laterBtn}>
            <Text style={styles.laterBtnText}>Plus tard</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );
}

function FeatureRow({ text }: { text: string }) {
  return (
    <View style={styles.featureRow}>
      <Ionicons name="checkmark-circle" size={18} color={colors.success ?? "#22c55e"} />
      <Text style={styles.featureText}>{text}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.72)",
    justifyContent: "center",
    alignItems: "center",
    padding: 20,
  },
  card: {
    backgroundColor: colors.surface ?? "#1a1a1e",
    borderRadius: 20,
    padding: 24,
    width: "100%",
    maxWidth: 400,
    borderWidth: 1,
    borderColor: colors.border ?? "#2a2a30",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 20 },
    shadowOpacity: 0.5,
    shadowRadius: 40,
    elevation: 20,
  },
  closeBtn: {
    position: "absolute",
    top: 12,
    right: 12,
    padding: 8,
    zIndex: 10,
  },
  iconWrap: {
    alignSelf: "center",
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: "rgba(255,107,53,0.15)",
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 16,
  },
  title: {
    color: colors.textPrimary ?? "#f0f0f2",
    fontSize: 20,
    fontWeight: "800",
    textAlign: "center",
    marginBottom: 8,
  },
  subtitle: {
    color: colors.textSecondary ?? "#a8a8b0",
    fontSize: 14,
    textAlign: "center",
    lineHeight: 20,
    marginBottom: 20,
  },
  usageBar: {
    marginBottom: 20,
    backgroundColor: colors.bgTertiary ?? "#0f0f11",
    borderRadius: 10,
    padding: 12,
  },
  usageText: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 8,
  },
  usageLabel: {
    color: colors.textSecondary ?? "#a8a8b0",
    fontSize: 12,
  },
  usageValue: {
    color: colors.primary,
    fontSize: 14,
    fontWeight: "700",
  },
  progressBar: {
    height: 6,
    backgroundColor: colors.border ?? "#2a2a30",
    borderRadius: 3,
    overflow: "hidden",
  },
  progressFill: {
    height: "100%",
    backgroundColor: colors.primary,
  },
  primaryBtn: {
    backgroundColor: colors.primary,
    borderRadius: 12,
    paddingVertical: 14,
    paddingHorizontal: 16,
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 16,
  },
  primaryBtnText: {
    color: "#000",
    fontSize: 15,
    fontWeight: "800",
  },
  primaryBtnPrice: {
    color: "#000",
    fontSize: 15,
    fontWeight: "700",
    opacity: 0.85,
  },
  featuresList: {
    marginBottom: 16,
  },
  featureRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    paddingVertical: 4,
  },
  featureText: {
    color: colors.textSecondary ?? "#a8a8b0",
    fontSize: 13,
    flex: 1,
  },
  laterBtn: {
    alignItems: "center",
    padding: 10,
  },
  laterBtnText: {
    color: colors.textSecondary ?? "#a8a8b0",
    fontSize: 14,
  },
});
