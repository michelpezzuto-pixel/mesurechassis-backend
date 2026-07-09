/**
 * ☕ Admin Stations — Pilotage Jeton Café (Priorité 4, juillet 2026)
 *
 * 🔐 Réservé au PROPRIÉTAIRE de la plateforme (require_platform_owner).
 *
 * Fonctions :
 *   - Suivi temps réel : cafés liquidés / objectif (50/mois) par station.
 *   - QR code d'inscription par station (à imprimer pour les pancartes).
 *   - Relance email manuelle « Nouveau projet, nouvelle pause ! »
 *     (fenêtre recommandée : 10 derniers jours du mois).
 *   - Historique 6 mois par station.
 *   - Création / édition de stations (nom, ville, PIN 4 chiffres, objectif).
 */
import { Ionicons } from "@expo/vector-icons";
import Constants from "expo-constants";
import { useRouter } from "expo-router";
import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import QRCode from "react-native-qrcode-svg";
import { SafeAreaView } from "react-native-safe-area-context";

import { api } from "@/src/services/api";
import { colors } from "@/src/theme";

const GREEN = "#10B981";

const WEB_BASE_URL =
  process.env.EXPO_PUBLIC_BACKEND_URL ||
  Constants.expoConfig?.extra?.backendUrl ||
  "https://mesurechassis.com";

type Station = {
  id: string;
  name: string;
  city: string;
  pin: string;
  active: boolean;
  monthly_objective: number;
  month_consumed: number;
  month_earned: number;
  users_count: number;
  objective_reached: boolean;
};

type DashboardMonth = {
  month: string;
  stations: { station_id: string; station_name: string; consumed: number; objective: number }[];
};

export default function AdminStationsScreen() {
  const router = useRouter();
  const [stations, setStations] = useState<Station[]>([]);
  const [relanceWindow, setRelanceWindow] = useState(false);
  const [months, setMonths] = useState<DashboardMonth[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [formOpen, setFormOpen] = useState(false);
  const [qrStation, setQrStation] = useState<Station | null>(null);
  const [relancing, setRelancing] = useState<string | null>(null);

  // Formulaire nouvelle station
  const [fName, setFName] = useState("");
  const [fCity, setFCity] = useState("");
  const [fPin, setFPin] = useState("");
  const [fObjective, setFObjective] = useState("50");
  const [creating, setCreating] = useState(false);

  const load = useCallback(async () => {
    try {
      const [rs, rd] = await Promise.all([
        api.get<{ stations: Station[]; relance_window_open: boolean }>("/cafe/stations"),
        api.get<{ months: DashboardMonth[] }>("/cafe/dashboard"),
      ]);
      setStations(rs.data.stations || []);
      setRelanceWindow(rs.data.relance_window_open);
      setMonths(rd.data.months || []);
    } catch (e: any) {
      const status = e?.response?.status;
      if (status === 403) {
        Alert.alert("Accès refusé", "Réservé au propriétaire de la plateforme.", [
          { text: "OK", onPress: () => router.back() },
        ]);
      }
    }
  }, [router]);

  useEffect(() => {
    (async () => {
      await load();
      setLoading(false);
    })();
  }, [load]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  }, [load]);

  const createStation = async () => {
    if (fName.trim().length < 2) {
      Alert.alert("Erreur", "Nom de station requis (2 caractères min).");
      return;
    }
    if (!/^\d{4}$/.test(fPin)) {
      Alert.alert("Erreur", "Le PIN doit être composé de 4 chiffres.");
      return;
    }
    setCreating(true);
    try {
      await api.post("/cafe/stations", {
        name: fName.trim(),
        city: fCity.trim(),
        pin: fPin,
        monthly_objective: parseInt(fObjective || "50", 10) || 50,
      });
      setFName("");
      setFCity("");
      setFPin("");
      setFObjective("50");
      setFormOpen(false);
      await load();
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      Alert.alert("Erreur", typeof detail === "string" ? detail : "Création impossible.");
    } finally {
      setCreating(false);
    }
  };

  const triggerRelance = (s: Station) => {
    Alert.alert(
      "📧 Relance email",
      `Envoyer « Nouveau projet, nouvelle pause ! » aux artisans de ${s.name} qui n'ont pas consommé de café ce mois-ci ?`,
      [
        { text: "Annuler", style: "cancel" },
        {
          text: "Envoyer",
          onPress: async () => {
            setRelancing(s.id);
            try {
              const r = await api.post(`/cafe/stations/${s.id}/relance`);
              Alert.alert(
                "✅ Relance envoyée",
                `${r.data?.sent ?? 0} email(s) envoyé(s) sur ${r.data?.targets ?? 0} artisan(s) ciblé(s).`,
              );
            } catch {
              Alert.alert("Erreur", "Envoi de la relance impossible.");
            } finally {
              setRelancing(null);
            }
          },
        },
      ],
    );
  };

  const qrValue = (s: Station) => `${WEB_BASE_URL}/?station=${s.id}`;

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} hitSlop={10} style={styles.backBtn}>
          <Ionicons name="arrow-back" size={24} color="#FFF" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Stations ☕ Jeton Café</Text>
        <TouchableOpacity
          onPress={() => setFormOpen((v) => !v)}
          hitSlop={10}
          testID="station-add-toggle"
        >
          <Ionicons name={formOpen ? "close" : "add-circle"} size={26} color={colors.primary} />
        </TouchableOpacity>
      </View>

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color={colors.primary} />
        </View>
      ) : (
        <ScrollView
          contentContainerStyle={{ padding: 16, paddingBottom: 40 }}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.primary} />
          }
        >
          {/* Fenêtre de relance */}
          {relanceWindow && (
            <View style={styles.windowBanner}>
              <Ionicons name="alarm" size={18} color="#F59E0B" />
              <Text style={styles.windowBannerText}>
                Fenêtre de relance OUVERTE (10 derniers jours du mois) — relancez
                les stations sous objectif.
              </Text>
            </View>
          )}

          {/* Formulaire nouvelle station */}
          {formOpen && (
            <View style={styles.formCard}>
              <Text style={styles.formTitle}>Nouvelle station partenaire</Text>
              <TextInput
                value={fName}
                onChangeText={setFName}
                placeholder="Nom (ex: Total Wavre)"
                placeholderTextColor="#555"
                style={styles.input}
                testID="station-name-input"
              />
              <TextInput
                value={fCity}
                onChangeText={setFCity}
                placeholder="Ville (optionnel)"
                placeholderTextColor="#555"
                style={styles.input}
              />
              <View style={{ flexDirection: "row", gap: 10 }}>
                <TextInput
                  value={fPin}
                  onChangeText={(v) => setFPin(v.replace(/[^0-9]/g, "").slice(0, 4))}
                  placeholder="PIN pompiste (4 chiffres)"
                  placeholderTextColor="#555"
                  keyboardType="number-pad"
                  maxLength={4}
                  style={[styles.input, { flex: 1 }]}
                  testID="station-pin-input"
                />
                <TextInput
                  value={fObjective}
                  onChangeText={(v) => setFObjective(v.replace(/[^0-9]/g, ""))}
                  placeholder="Objectif/mois"
                  placeholderTextColor="#555"
                  keyboardType="number-pad"
                  style={[styles.input, { width: 110 }]}
                />
              </View>
              <TouchableOpacity
                style={[styles.createBtn, creating && { opacity: 0.5 }]}
                onPress={createStation}
                disabled={creating}
                activeOpacity={0.85}
                testID="station-create-btn"
              >
                {creating ? (
                  <ActivityIndicator color="#000" />
                ) : (
                  <Text style={styles.createBtnText}>Créer la station</Text>
                )}
              </TouchableOpacity>
            </View>
          )}

          {stations.length === 0 && !formOpen && (
            <View style={styles.emptyCard}>
              <Text style={{ fontSize: 36 }}>⛽</Text>
              <Text style={styles.emptyTitle}>Aucune station partenaire</Text>
              <Text style={styles.emptyText}>
                Créez votre première station avec le bouton + en haut à droite,
                puis imprimez son QR code pour la pancarte.
              </Text>
            </View>
          )}

          {/* Liste des stations */}
          {stations.map((s) => {
            const pct = Math.min(1, s.month_consumed / Math.max(1, s.monthly_objective));
            return (
              <View key={s.id} style={styles.stationCard}>
                <View style={styles.stationHeader}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.stationName}>{s.name}</Text>
                    <Text style={styles.stationMeta}>
                      {s.city ? `${s.city} · ` : ""}PIN {s.pin} · {s.users_count} inscrit(s)
                    </Text>
                  </View>
                  {s.objective_reached ? (
                    <View style={styles.badgeOk}>
                      <Text style={styles.badgeOkText}>Objectif ✓</Text>
                    </View>
                  ) : (
                    relanceWindow && (
                      <View style={styles.badgeWarn}>
                        <Text style={styles.badgeWarnText}>Sous objectif</Text>
                      </View>
                    )
                  )}
                </View>

                {/* Progress cafés du mois */}
                <View style={styles.progressRow}>
                  <Text style={styles.progressLabel}>
                    ☕ {s.month_consumed} / {s.monthly_objective} ce mois
                  </Text>
                  <Text style={styles.progressSub}>{s.month_earned} gagné(s)</Text>
                </View>
                <View style={styles.progressTrack}>
                  <View
                    style={[
                      styles.progressFill,
                      {
                        width: `${pct * 100}%`,
                        backgroundColor: s.objective_reached ? GREEN : colors.primary,
                      },
                    ]}
                  />
                </View>

                {/* Actions */}
                <View style={styles.actionsRow}>
                  <TouchableOpacity
                    style={styles.actionBtn}
                    onPress={() => setQrStation(qrStation?.id === s.id ? null : s)}
                    activeOpacity={0.8}
                    testID={`station-qr-${s.id}`}
                  >
                    <Ionicons name="qr-code" size={16} color={colors.primary} />
                    <Text style={styles.actionBtnText}>QR code</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={[styles.actionBtn, styles.actionBtnRelance]}
                    onPress={() => triggerRelance(s)}
                    disabled={relancing === s.id}
                    activeOpacity={0.8}
                    testID={`station-relance-${s.id}`}
                  >
                    {relancing === s.id ? (
                      <ActivityIndicator size="small" color="#F59E0B" />
                    ) : (
                      <Ionicons name="megaphone" size={16} color="#F59E0B" />
                    )}
                    <Text style={[styles.actionBtnText, { color: "#F59E0B" }]}>
                      Relance email
                    </Text>
                  </TouchableOpacity>
                </View>

                {/* QR code dépliable */}
                {qrStation?.id === s.id && (
                  <View style={styles.qrBox}>
                    <View style={styles.qrWrap}>
                      <QRCode value={qrValue(s)} size={170} backgroundColor="#FFF" />
                    </View>
                    <Text style={styles.qrHint} selectable>
                      {qrValue(s)}
                    </Text>
                    <Text style={styles.qrSub}>
                      À imprimer sur la pancarte : l’artisan scanne → s’inscrit →
                      gagne des cafés à valider chez vous.
                    </Text>
                  </View>
                )}
              </View>
            );
          })}

          {/* Historique 6 mois */}
          {stations.length > 0 && (
            <>
              <Text style={styles.sectionLabel}>Historique 6 mois (cafés liquidés)</Text>
              {months.map((m) => (
                <View key={m.month} style={styles.monthRow}>
                  <Text style={styles.monthLabel}>{m.month}</Text>
                  <View style={{ flex: 1 }}>
                    {m.stations.map((st) => (
                      <Text key={st.station_id} style={styles.monthStationText}>
                        {st.station_name} : {st.consumed}/{st.objective}
                      </Text>
                    ))}
                  </View>
                </View>
              ))}
            </>
          )}
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: "#0C0C0E" },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: "#1F1F24",
  },
  backBtn: { width: 32, height: 32, justifyContent: "center" },
  headerTitle: { fontSize: 16, fontWeight: "800", color: "#FFF" },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  windowBanner: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 8,
    backgroundColor: "#F59E0B15",
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#F59E0B44",
    padding: 12,
    marginBottom: 14,
  },
  windowBannerText: { flex: 1, fontSize: 12, color: "#F5D08A", lineHeight: 17 },
  formCard: {
    backgroundColor: "#1A1A1E",
    borderRadius: 14,
    padding: 14,
    borderWidth: 1,
    borderColor: colors.primary + "44",
    marginBottom: 14,
    gap: 10,
  },
  formTitle: { fontSize: 15, fontWeight: "700", color: "#FFF" },
  input: {
    backgroundColor: "#0C0C0E",
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#2A2A2E",
    color: "#FFF",
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 14,
  },
  createBtn: {
    backgroundColor: colors.primary,
    borderRadius: 12,
    paddingVertical: 13,
    alignItems: "center",
  },
  createBtnText: { fontSize: 14, fontWeight: "800", color: "#000" },
  emptyCard: {
    alignItems: "center",
    padding: 30,
    gap: 8,
  },
  emptyTitle: { fontSize: 17, fontWeight: "700", color: "#FFF" },
  emptyText: { fontSize: 13, color: "#8A8A92", textAlign: "center", lineHeight: 19 },
  stationCard: {
    backgroundColor: "#1A1A1E",
    borderRadius: 14,
    padding: 14,
    borderWidth: 1,
    borderColor: "#26262B",
    marginBottom: 12,
  },
  stationHeader: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 10 },
  stationName: { fontSize: 16, fontWeight: "700", color: "#FFF" },
  stationMeta: { fontSize: 12, color: "#8A8A92", marginTop: 2 },
  badgeOk: {
    backgroundColor: GREEN + "20",
    borderRadius: 8,
    paddingHorizontal: 8,
    paddingVertical: 4,
  },
  badgeOkText: { fontSize: 11, fontWeight: "700", color: GREEN },
  badgeWarn: {
    backgroundColor: "#F59E0B20",
    borderRadius: 8,
    paddingHorizontal: 8,
    paddingVertical: 4,
  },
  badgeWarnText: { fontSize: 11, fontWeight: "700", color: "#F59E0B" },
  progressRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 6,
  },
  progressLabel: { fontSize: 14, fontWeight: "700", color: "#FFF" },
  progressSub: { fontSize: 12, color: "#8A8A92" },
  progressTrack: {
    height: 8,
    borderRadius: 4,
    backgroundColor: "#0C0C0E",
    overflow: "hidden",
    marginBottom: 12,
  },
  progressFill: { height: "100%", borderRadius: 4 },
  actionsRow: { flexDirection: "row", gap: 10 },
  actionBtn: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    backgroundColor: "#0C0C0E",
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#2A2A2E",
    paddingVertical: 11,
    minHeight: 44,
  },
  actionBtnRelance: { borderColor: "#F59E0B44" },
  actionBtnText: { fontSize: 13, fontWeight: "700", color: colors.primary },
  qrBox: {
    alignItems: "center",
    marginTop: 14,
    gap: 8,
  },
  qrWrap: { backgroundColor: "#FFF", borderRadius: 12, padding: 12 },
  qrHint: { fontSize: 11, color: "#8A8A92", textAlign: "center" },
  qrSub: { fontSize: 12, color: "#A6A6AD", textAlign: "center", lineHeight: 17 },
  sectionLabel: {
    fontSize: 12,
    fontWeight: "700",
    color: "#6E6E76",
    textTransform: "uppercase",
    letterSpacing: 0.8,
    marginTop: 10,
    marginBottom: 8,
  },
  monthRow: {
    flexDirection: "row",
    gap: 12,
    backgroundColor: "#141417",
    borderRadius: 12,
    padding: 12,
    marginBottom: 8,
  },
  monthLabel: { fontSize: 13, fontWeight: "800", color: colors.primary, width: 64 },
  monthStationText: { fontSize: 12, color: "#A6A6AD", lineHeight: 18 },
});
