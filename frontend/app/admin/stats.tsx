import React, { useCallback, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useFocusEffect, useRouter } from "expo-router";
import { api, getToken } from "@/src/services/api";
import { useAuth } from "@/src/context/AuthContext";
import { colors, statusMeta } from "@/src/theme";
import * as Sharing from "expo-sharing";

type Stats = {
  total_chantiers: number;
  by_status: Record<string, number>;
  closure_rate: number;
  total_mesures: number;
  total_alerts: number;
  by_technician: { user_id: string; name: string; role: string; mesures: number; alerts: number }[];
};

type Commercials = {
  commercials: { user_id: string; name: string; email: string; created: number; converted: number; conversion_rate: number }[];
  total_created: number;
  total_converted: number;
  global_conversion_rate: number;
};

export default function AdminStats() {
  const { user } = useAuth();
  const router = useRouter();
  const [data, setData] = useState<Stats | null>(null);
  const [perf, setPerf] = useState<Commercials | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [exporting, setExporting] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const [s, c] = await Promise.all([
        api.get<Stats>("/stats/company"),
        api.get<Commercials>("/stats/commercials"),
      ]);
      setData(s.data);
      setPerf(c.data);
    } catch (e: any) {
      if (e?.response?.status === 403) {
        Alert.alert("Accès refusé", "Réservé aux administrateurs.");
        router.replace("/dashboard");
      } else {
        Alert.alert("Erreur", "Chargement impossible.");
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [router]);

  const exportPerfPDF = async () => {
    setExporting(true);
    try {
      const token = await getToken();
      const r = await fetch(
        `${process.env.EXPO_PUBLIC_BACKEND_URL}/api/stats/commercials/export.pdf`,
        { headers: token ? { Authorization: `Bearer ${token}` } : {} }
      );
      const blob = await r.blob();
      const reader = new FileReader();
      reader.onload = async () => {
        const b64 = (reader.result as string).split(",")[1];
        const FS = await import("expo-file-system/legacy");
        const fileUri = `${FS.cacheDirectory}rapport-performance.pdf`;
        await FS.writeAsStringAsync(fileUri, b64, { encoding: FS.EncodingType.Base64 });
        if (await Sharing.isAvailableAsync()) {
          await Sharing.shareAsync(fileUri, { mimeType: "application/pdf" });
        }
      };
      reader.readAsDataURL(blob);
    } catch {
      Alert.alert("Erreur", "Export PDF impossible.");
    } finally {
      setExporting(false);
    }
  };

  useFocusEffect(
    useCallback(() => {
      if (user && user.role !== "admin") {
        router.replace("/dashboard");
        return;
      }
      fetchData();
    }, [user, fetchData, router])
  );

  if (loading || !data) {
    return (
      <View style={[styles.flex, styles.center]}>
        <ActivityIndicator color={colors.primary} size="large" />
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.flex} edges={["bottom"]}>
      <ScrollView
        contentContainerStyle={{ padding: 16, paddingBottom: 40 }}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => {
              setRefreshing(true);
              fetchData();
            }}
            tintColor={colors.primary}
          />
        }
      >
        <Text style={styles.section}>VUE D'ENSEMBLE</Text>
        <View style={styles.row}>
          <View style={[styles.card, styles.heroCard]}>
            <Text style={styles.heroValue} testID="stat-total-chantiers">
              {data.total_chantiers}
            </Text>
            <Text style={styles.heroLabel}>Chantiers totaux</Text>
          </View>
          <View style={[styles.card, styles.heroCard]}>
            <Text style={[styles.heroValue, { color: colors.success }]} testID="stat-closure-rate">
              {data.closure_rate}%
            </Text>
            <Text style={styles.heroLabel}>Taux de clôture</Text>
          </View>
        </View>

        <View style={styles.row}>
          <View style={[styles.card, styles.heroCard]}>
            <Text style={styles.heroValue}>{data.total_mesures}</Text>
            <Text style={styles.heroLabel}>Ouvertures mesurées</Text>
          </View>
          <View style={[styles.card, styles.heroCard]}>
            <Text style={[styles.heroValue, { color: colors.alert }]}>{data.total_alerts}</Text>
            <Text style={styles.heroLabel}>Alertes détectées</Text>
          </View>
        </View>

        <Text style={styles.section}>RÉPARTITION PAR STATUT</Text>
        {Object.entries(data.by_status).map(([key, count]) => {
          const meta = statusMeta[key] ?? { label: key, color: "#fff", bg: "#333" };
          const pct = data.total_chantiers > 0 ? (count / data.total_chantiers) * 100 : 0;
          return (
            <View key={key} style={styles.statusRow} testID={`status-row-${key}`}>
              <View style={styles.statusHeader}>
                <View style={[styles.dot, { backgroundColor: meta.color }]} />
                <Text style={styles.statusLabel}>{meta.label}</Text>
                <Text style={styles.statusValue}>{count}</Text>
              </View>
              <View style={styles.progressBg}>
                <View
                  style={[
                    styles.progressFill,
                    { width: `${pct}%`, backgroundColor: meta.color },
                  ]}
                />
              </View>
            </View>
          );
        })}

        <Text style={styles.section}>PERFORMANCE PAR TECHNICIEN</Text>
        {data.by_technician.length === 0 && (
          <Text style={styles.empty}>Aucune mesure encore enregistrée.</Text>
        )}
        {data.by_technician.map((t) => (
          <View key={t.user_id} style={styles.techCard} testID={`tech-row-${t.user_id}`}>
            <View style={styles.techHeader}>
              <Ionicons
                name={
                  t.role === "admin"
                    ? "shield-checkmark"
                    : t.role === "commercial"
                    ? "briefcase"
                    : "construct"
                }
                size={20}
                color={colors.primary}
              />
              <View style={{ flex: 1 }}>
                <Text style={styles.techName}>{t.name}</Text>
                <Text style={styles.techRole}>{t.role}</Text>
              </View>
            </View>
            <View style={styles.techStats}>
              <View style={styles.techPill}>
                <Text style={styles.techPillValue}>{t.mesures}</Text>
                <Text style={styles.techPillLabel}>mesures</Text>
              </View>
              <View style={[styles.techPill, t.alerts > 0 && { borderColor: colors.alert }]}>
                <Text style={[styles.techPillValue, t.alerts > 0 && { color: colors.alert }]}>
                  {t.alerts}
                </Text>
                <Text style={styles.techPillLabel}>alertes</Text>
              </View>
            </View>
          </View>
        ))}

        {perf && (
          <>
            <View style={{ flexDirection: "row", alignItems: "center", marginTop: 24 }}>
              <Text style={[styles.section, { flex: 1, marginTop: 0 }]}>PERFORMANCE COMMERCIAUX</Text>
              <TouchableOpacity
                testID="export-perf-pdf"
                onPress={exportPerfPDF}
                disabled={exporting}
                style={localStyles.exportBtn}
                activeOpacity={0.85}
              >
                {exporting ? (
                  <ActivityIndicator color="#000" size="small" />
                ) : (
                  <>
                    <Ionicons name="document-text" size={14} color="#000" />
                    <Text style={localStyles.exportBtnText}>PDF</Text>
                  </>
                )}
              </TouchableOpacity>
            </View>

            <View style={styles.card}>
              <Text style={localStyles.kpi}>
                Taux conversion global : <Text style={{ color: colors.success }}>{perf.global_conversion_rate}%</Text>
              </Text>
              <Text style={localStyles.kpiSub}>
                {perf.total_converted} convertis / {perf.total_created} créés
              </Text>
            </View>

            {perf.commercials.length === 0 ? (
              <Text style={styles.empty}>Aucun commercial enregistré.</Text>
            ) : (
              perf.commercials.map((c) => (
                <View key={c.user_id} style={styles.techCard} testID={`commercial-row-${c.user_id}`}>
                  <View style={styles.techHeader}>
                    <Ionicons name="briefcase" size={20} color={colors.primary} />
                    <View style={{ flex: 1 }}>
                      <Text style={styles.techName}>{c.name}</Text>
                      <Text style={styles.techRole}>{c.email}</Text>
                    </View>
                  </View>
                  <View style={styles.techStats}>
                    <View style={styles.techPill}>
                      <Text style={styles.techPillValue}>{c.created}</Text>
                      <Text style={styles.techPillLabel}>Créés</Text>
                    </View>
                    <View style={styles.techPill}>
                      <Text style={styles.techPillValue}>{c.converted}</Text>
                      <Text style={styles.techPillLabel}>Convertis</Text>
                    </View>
                    <View style={[styles.techPill, c.conversion_rate >= 50 && { borderColor: colors.success }]}>
                      <Text style={[styles.techPillValue, c.conversion_rate >= 50 && { color: colors.success }]}>
                        {c.conversion_rate}%
                      </Text>
                      <Text style={styles.techPillLabel}>Conversion</Text>
                    </View>
                  </View>
                </View>
              ))
            )}
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: colors.bg },
  center: { alignItems: "center", justifyContent: "center" },
  section: {
    color: colors.textSecondary,
    fontSize: 12,
    fontWeight: "800",
    letterSpacing: 1.5,
    marginTop: 18,
    marginBottom: 10,
  },
  row: { flexDirection: "row", gap: 12, marginBottom: 12 },
  card: {
    backgroundColor: colors.surface,
    borderColor: colors.borderSubtle,
    borderWidth: 1,
    borderRadius: 12,
    padding: 14,
  },
  heroCard: { flex: 1 },
  heroValue: { color: colors.primary, fontSize: 32, fontWeight: "900" },
  heroLabel: {
    color: colors.textSecondary,
    fontSize: 11,
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: 0.6,
    marginTop: 2,
  },
  statusRow: {
    backgroundColor: colors.surface,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    padding: 12,
    marginBottom: 8,
  },
  statusHeader: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 8 },
  dot: { width: 8, height: 8, borderRadius: 4 },
  statusLabel: { color: colors.textPrimary, fontWeight: "700", flex: 1, fontSize: 14 },
  statusValue: { color: colors.textPrimary, fontWeight: "900", fontSize: 18 },
  progressBg: {
    height: 6,
    backgroundColor: colors.bg,
    borderRadius: 3,
    overflow: "hidden",
  },
  progressFill: { height: "100%", borderRadius: 3 },
  techCard: {
    backgroundColor: colors.surface,
    borderColor: colors.borderSubtle,
    borderWidth: 1,
    borderRadius: 12,
    padding: 14,
    marginBottom: 8,
  },
  techHeader: { flexDirection: "row", alignItems: "center", gap: 10, marginBottom: 10 },
  techName: { color: colors.textPrimary, fontWeight: "800", fontSize: 15 },
  techRole: { color: colors.textSecondary, fontSize: 12, textTransform: "uppercase", letterSpacing: 0.6 },
  techStats: { flexDirection: "row", gap: 10 },
  techPill: {
    flex: 1,
    backgroundColor: colors.bg,
    borderColor: colors.borderSubtle,
    borderWidth: 1,
    borderRadius: 8,
    paddingVertical: 10,
    alignItems: "center",
  },
  techPillValue: { color: colors.textPrimary, fontWeight: "900", fontSize: 18 },
  techPillLabel: {
    color: colors.textSecondary,
    fontSize: 10,
    textTransform: "uppercase",
    letterSpacing: 0.6,
    marginTop: 2,
  },
  empty: { color: colors.textSecondary, fontStyle: "italic", textAlign: "center", padding: 16 },
});

const localStyles = StyleSheet.create({
  exportBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    backgroundColor: colors.primary,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 6,
  },
  exportBtnText: { color: "#000", fontWeight: "900", fontSize: 11, letterSpacing: 0.8 },
  kpi: { color: colors.textPrimary, fontWeight: "800", fontSize: 16 },
  kpiSub: { color: colors.textSecondary, fontSize: 12, marginTop: 4 },
});
