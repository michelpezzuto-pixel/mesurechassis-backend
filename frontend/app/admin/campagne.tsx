import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import { api } from "@/src/services/api";
import { colors } from "@/src/theme";

type Stats = {
  pending: number;
  sent: number;
  failed: number;
  sending: number;
  sent_today: number;
  daily_limit: number;
  converted: number;
};

type Prospect = {
  id: string;
  email: string;
  company: string;
  region: string;
  status: "pending" | "sending" | "sent" | "failed";
  sent_at: string | null;
};

const STATUS_UI: Record<string, { label: string; color: string }> = {
  pending: { label: "À CONTACTER", color: "#9ca3af" },
  sending: { label: "ENVOI…", color: "#FBBF24" },
  sent: { label: "ENVOYÉ", color: "#22C55E" },
  failed: { label: "ÉCHEC", color: "#F87171" },
};

/** Vue ADMIN : campagne email prospection testeurs (1 bouton / jour). */
export default function AdminCampagne() {
  const router = useRouter();
  const [stats, setStats] = useState<Stats | null>(null);
  const [prospects, setProspects] = useState<Prospect[]>([]);
  const [loading, setLoading] = useState(true);
  const [launching, setLaunching] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchAll = useCallback(async () => {
    try {
      const [s, p] = await Promise.all([
        api.get<Stats>("/campaign/stats"),
        api.get<{ prospects: Prospect[] }>("/campaign/prospects"),
      ]);
      setStats(s.data);
      setProspects(p.data.prospects);
      // Poll tant que des envois sont en cours
      if (s.data.sending > 0 && !pollRef.current) {
        pollRef.current = setInterval(() => void fetchAll(), 4000);
      } else if (s.data.sending === 0 && pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchAll();
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [fetchAll]);

  const launchBatch = async () => {
    setLaunching(true);
    setMessage(null);
    try {
      const res = await api.post<{ scheduled: number; message: string }>(
        "/campaign/send-batch",
      );
      setMessage(`🚀 ${res.data.message}`);
      void fetchAll();
    } catch (e: any) {
      setMessage(`⚠️ ${e?.response?.data?.detail || "Erreur lors du lancement."}`);
    } finally {
      setLaunching(false);
    }
  };

  const remaining = stats ? stats.daily_limit - stats.sent_today : 0;
  const canSend =
    !!stats && stats.pending > 0 && remaining > 0 && stats.sending === 0;

  return (
    <SafeAreaView style={styles.flex} edges={["top", "bottom"]}>
      <View style={styles.topBar}>
        <TouchableOpacity
          testID="campagne-back-button"
          onPress={() => router.back()}
          hitSlop={10}
        >
          <Ionicons name="arrow-back" size={22} color={colors.textPrimary} />
        </TouchableOpacity>
        <Text style={styles.topTitle}>📣 CAMPAGNE TESTEURS</Text>
        <TouchableOpacity
          testID="campagne-refresh-button"
          onPress={() => void fetchAll()}
          hitSlop={10}
        >
          <Ionicons name="refresh" size={20} color={colors.primary} />
        </TouchableOpacity>
      </View>

      {loading || !stats ? (
        <ActivityIndicator color={colors.primary} style={{ marginTop: 40 }} />
      ) : (
        <>
          <View style={styles.statsRow}>
            <View style={styles.statBox} testID="campagne-pending-box">
              <Text style={styles.statValue}>{stats.pending}</Text>
              <Text style={styles.statLabel}>à contacter</Text>
            </View>
            <View style={styles.statBox}>
              <Text style={[styles.statValue, { color: "#22C55E" }]}>
                {stats.sent}
              </Text>
              <Text style={styles.statLabel}>envoyés</Text>
            </View>
            <View style={styles.statBox}>
              <Text style={[styles.statValue, { color: "#FBBF24" }]}>
                {stats.sent_today}/{stats.daily_limit}
              </Text>
              <Text style={styles.statLabel}>aujourd&apos;hui</Text>
            </View>
            <View style={styles.statBox}>
              <Text style={[styles.statValue, { color: colors.primary }]}>
                {stats.converted}
              </Text>
              <Text style={styles.statLabel}>inscrits 🎉</Text>
            </View>
          </View>

          <TouchableOpacity
            testID="campagne-send-batch-button"
            style={[styles.sendBtn, !canSend && styles.sendBtnDisabled]}
            onPress={() => void launchBatch()}
            disabled={!canSend || launching}
          >
            {launching || stats.sending > 0 ? (
              <>
                <ActivityIndicator color="#fff" size="small" />
                <Text style={styles.sendBtnText}>
                  {stats.sending > 0
                    ? `Envoi en cours… (${stats.sending} restants)`
                    : "Lancement…"}
                </Text>
              </>
            ) : (
              <>
                <Ionicons name="send" size={18} color="#fff" />
                <Text style={styles.sendBtnText}>
                  {remaining <= 0
                    ? "Limite du jour atteinte — revenez demain"
                    : stats.pending === 0
                      ? "Liste épuisée 🎉"
                      : `ENVOYER LE LOT DU JOUR (${Math.min(remaining, stats.pending)} emails)`}
                </Text>
              </>
            )}
          </TouchableOpacity>

          {message && (
            <Text style={styles.message} testID="campagne-message">
              {message}
            </Text>
          )}

          <FlatList
            data={prospects}
            keyExtractor={(p) => p.id}
            contentContainerStyle={{ padding: 16, paddingBottom: 50 }}
            renderItem={({ item }) => {
              const ui = STATUS_UI[item.status] ?? STATUS_UI.pending;
              return (
                <View style={styles.card} testID={`prospect-${item.email}`}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.cardName}>{item.company || item.email}</Text>
                    <Text style={styles.cardEmail}>{item.email}</Text>
                    {!!item.region && (
                      <Text style={styles.cardMeta}>{item.region}</Text>
                    )}
                  </View>
                  <View
                    style={[styles.badge, { backgroundColor: `${ui.color}22` }]}
                  >
                    <Text style={[styles.badgeText, { color: ui.color }]}>
                      {ui.label}
                    </Text>
                  </View>
                </View>
              );
            }}
          />
        </>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: colors.bg },
  topBar: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 16,
    paddingVertical: 14,
  },
  topTitle: { color: colors.textPrimary, fontWeight: "800", fontSize: 15, letterSpacing: 1 },
  statsRow: { flexDirection: "row", gap: 8, paddingHorizontal: 16 },
  statBox: {
    flex: 1,
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: 12,
    alignItems: "center",
  },
  statValue: { color: colors.textPrimary, fontSize: 20, fontWeight: "800" },
  statLabel: { color: colors.textSecondary, fontSize: 10.5, marginTop: 2, textAlign: "center" },
  sendBtn: {
    flexDirection: "row",
    gap: 10,
    backgroundColor: colors.primary,
    margin: 16,
    marginBottom: 6,
    paddingVertical: 15,
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center",
  },
  sendBtnDisabled: { backgroundColor: colors.surfaceElevated },
  sendBtnText: { color: "#fff", fontWeight: "800", fontSize: 13.5 },
  message: {
    color: colors.textSecondary,
    fontSize: 12.5,
    textAlign: "center",
    paddingHorizontal: 20,
    marginBottom: 4,
  },
  card: {
    flexDirection: "row",
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: 13,
    marginBottom: 8,
    alignItems: "center",
  },
  cardName: { color: colors.textPrimary, fontWeight: "700", fontSize: 14 },
  cardEmail: { color: colors.primary, fontSize: 12.5, marginTop: 1 },
  cardMeta: { color: colors.textSecondary, fontSize: 11.5, marginTop: 1 },
  badge: { paddingHorizontal: 9, paddingVertical: 4, borderRadius: 7, marginLeft: 10 },
  badgeText: { fontSize: 10, fontWeight: "800" },
});
