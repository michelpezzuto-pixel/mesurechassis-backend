/**
 * FilleulInviteBanner — Bannière d'incitation au parrainage pour un filleul.
 *
 * Affichée sur le dashboard quand :
 *   • L'utilisateur a été parrainé (referred_by_code défini)
 *   • L'utilisateur n'a pas encore parrainé personne (referrals_used === 0)
 *
 * Disparait dès qu'il parraine 1 personne. Tap → écran /referral.
 *
 * 🍎 Conformité Apple : on ne mentionne PAS de prix, on parle juste de
 * "2 mois offerts" — c'est une mécanique de fidélisation, pas un IAP.
 */
import React, { useEffect, useState } from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import { api } from "@/src/services/api";
import { colors } from "@/src/theme";

type ReferralStatusLite = {
  referred_by_code: string | null;
  referrals_used: number;
};

export default function FilleulInviteBanner() {
  const router = useRouter();
  const [shouldShow, setShouldShow] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { data } = await api.get<ReferralStatusLite>("/referral/me");
        if (cancelled) return;
        // N'affiche QUE si l'utilisateur a un parrain ET n'a jamais parrainé.
        if (data.referred_by_code && (data.referrals_used ?? 0) === 0) {
          setShouldShow(true);
        }
      } catch {
        // 401 / 403 / réseau → ne rien afficher (silent fail).
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (!shouldShow) return null;

  return (
    <TouchableOpacity
      style={styles.card}
      onPress={() => router.push("/referral")}
      activeOpacity={0.85}
      testID="filleul-invite-banner"
    >
      <View style={styles.iconWrap}>
        <Ionicons name="gift" size={22} color={colors.primary} />
      </View>
      <View style={styles.body}>
        <Text style={styles.title}>À votre tour de parrainer 🎁</Text>
        <Text style={styles.subtitle}>
          Invitez un menuisier et gagnez <Text style={styles.bold}>2 mois offerts</Text> à chaque inscription validée.
        </Text>
      </View>
      <Ionicons name="chevron-forward" size={18} color={colors.textSecondary} />
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    marginHorizontal: 16,
    marginTop: 12,
    padding: 14,
    backgroundColor: "rgba(255, 107, 26, 0.08)",
    borderRadius: 14,
    borderWidth: 1,
    borderColor: colors.primary,
  },
  iconWrap: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: "rgba(255, 107, 26, 0.16)",
    alignItems: "center",
    justifyContent: "center",
  },
  body: { flex: 1 },
  title: {
    color: colors.textPrimary,
    fontSize: 14,
    fontWeight: "900",
    marginBottom: 2,
  },
  subtitle: {
    color: colors.textSecondary,
    fontSize: 12,
    lineHeight: 16,
  },
  bold: { color: colors.primary, fontWeight: "900" },
});
