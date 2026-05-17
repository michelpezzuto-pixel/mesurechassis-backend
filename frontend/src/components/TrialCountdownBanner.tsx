import React, { useCallback, useEffect, useState } from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import { api } from "@/src/services/api";
import { useAuth } from "@/src/context/AuthContext";
import { colors } from "@/src/theme";

/** Durée de l'essai (3 mois = 90 jours), définie côté backend dans db.py. */
export const TRIAL_DAYS = 90;

type Profile = {
  plan?: "free" | "trial" | "pro";
  subscription_status?: string;
  subscription_expires_at?: string | null;
  cancel_at_period_end?: boolean;
};

function daysLeft(expiresAt?: string | null): number | null {
  if (!expiresAt) return null;
  try {
    const dt = new Date(expiresAt).getTime();
    if (isNaN(dt)) return null;
    return Math.ceil((dt - Date.now()) / (1000 * 60 * 60 * 24));
  } catch {
    return null;
  }
}

function severityFor(days: number): {
  bg: string;
  border: string;
  fg: string;
  icon: keyof typeof Ionicons.glyphMap;
} {
  if (days <= 7) {
    return {
      bg: "#3a1010",
      border: colors.anomaly,
      fg: colors.anomaly,
      icon: "alert-circle",
    };
  }
  if (days <= 30) {
    return {
      bg: "#2a1c08",
      border: colors.warning,
      fg: colors.warning,
      icon: "time-outline",
    };
  }
  return {
    bg: "#0b3b1c",
    border: "#34d399",
    fg: "#34d399",
    icon: "rocket-outline",
  };
}

function formatFR(iso?: string | null): string {
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

/**
 * Bannière de compte à rebours pour la période d'essai.
 *
 * Affiche les jours restants quand `plan === "trial"` (et non bloqué).
 * - Cachée pour Pro / Free / abonnement déjà annulé / suspendu / expiré.
 * - Couleur verte/orange/rouge selon l'urgence (>30j / 8-30j / ≤7j).
 * - Cliquable → ouvre `/company-profile` pour le détail facturation.
 */
export default function TrialCountdownBanner() {
  const router = useRouter();
  const { company } = useAuth();
  const [profile, setProfile] = useState<Profile | null>(null);

  const fetchProfile = useCallback(async () => {
    try {
      const res = await api.get<Profile>("/company/profile");
      setProfile(res.data);
    } catch {
      /* silent: la bannière n'est pas critique */
    }
  }, []);

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile, company?.company_id]);

  // Pas de bannière sans profil chargé
  if (!profile) return null;

  const plan = profile.plan ?? "trial";
  // Bannière visible uniquement en plan "trial"
  if (plan !== "trial") return null;
  // Si annulation programmée → l'écran profil gère déjà l'état
  if (profile.cancel_at_period_end) return null;
  if (profile.subscription_status === "suspended") return null;

  const days = daysLeft(profile.subscription_expires_at);
  // J91+ : on laisse le PaywallScreen plein-écran prendre le relais
  if (days === null || days <= 0) return null;

  const sev = severityFor(days);
  const dayLabel = days === 1 ? "jour" : "jours";

  return (
    <TouchableOpacity
      testID="trial-countdown-banner"
      activeOpacity={0.85}
      onPress={() => router.push("/company-profile")}
      style={[styles.wrap, { backgroundColor: sev.bg, borderColor: sev.border }]}
    >
      <View style={styles.iconWrap}>
        <Ionicons name={sev.icon} size={20} color={sev.fg} />
      </View>
      <View style={{ flex: 1 }}>
        <Text style={[styles.title, { color: sev.fg }]}>
          ESSAI {TRIAL_DAYS} JOURS · {days} {dayLabel} restant
          {days > 1 ? "s" : ""}
        </Text>
        <Text style={styles.sub}>
          Expire le {formatFR(profile.subscription_expires_at)} — Passez Pro pour
          un accès illimité.
        </Text>
      </View>
      <Ionicons name="chevron-forward" size={18} color={sev.fg} />
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
  title: { fontSize: 12, fontWeight: "900", letterSpacing: 0.8 },
  sub: { color: colors.textSecondary, fontSize: 11, marginTop: 2 },
});
