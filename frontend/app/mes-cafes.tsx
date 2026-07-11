/**
 * ☕ Mes cafés — Écran artisan (Priorité 4, juillet 2026)
 *
 * Accessible à tout moment depuis le tableau de bord (visible UNIQUEMENT
 * pour les comptes issus d'un QR code de station partenaire). L'artisan
 * peut faire valider son café à la pompe SANS interrompre son travail :
 * le jeton actif reste ici avec le gros bouton vert « VALIDATION POMPISTE ».
 */
import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import CafeJetonModal, { CafeJeton } from "@/src/components/CafeJetonModal";
import { api } from "@/src/services/api";
import { colors } from "@/src/theme";

const GREEN = "#10B981";

type Station = { id: string; name: string; city?: string; address?: string };
type Network = { id: string; name: string; logo_url?: string; country?: string };
type CafeMe = {
  station: Station | null;
  network: Network | null;
  network_stations: Station[];
  active_jeton: CafeJeton | null;
  jetons: CafeJeton[];
  consumed_total?: number;
};

function fmtDate(iso?: string | null): string {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleDateString("fr-BE", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    });
  } catch {
    return "";
  }
}

export default function MesCafesScreen() {
  const router = useRouter();
  const [data, setData] = useState<CafeMe | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);

  const load = useCallback(async () => {
    try {
      const r = await api.get<CafeMe>("/cafe/me");
      setData(r.data);
    } catch {
      setData(null);
    }
  }, []);

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

  const active = data?.active_jeton || null;
  const station = data?.station || null;
  const network = data?.network || null;
  const networkStations = data?.network_stations || [];
  const hasCampaign = !!station || !!network;
  const history = (data?.jetons || []).filter((j) => j.status !== "earned");

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} hitSlop={10} style={styles.backBtn}>
          <Ionicons name="arrow-back" size={24} color="#FFF" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Mes cafés ☕</Text>
        <View style={{ width: 32 }} />
      </View>

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color={colors.primary} />
        </View>
      ) : !hasCampaign ? (
        <View style={styles.center}>
          <Text style={{ fontSize: 40, marginBottom: 10 }}>☕</Text>
          <Text style={styles.emptyTitle}>Offre non activée</Text>
          <Text style={styles.emptyText}>
            Les cafés offerts sont réservés aux comptes créés pendant une
            campagne active.
          </Text>
        </View>
      ) : (
        <ScrollView
          contentContainerStyle={{ padding: 16, paddingBottom: 40 }}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={onRefresh}
              tintColor={colors.primary}
            />
          }
        >
          {/* Bandeau réseau (ex: Total) ou station simple */}
          {network ? (
            <View style={styles.networkCard}>
              <View style={styles.networkBadge}>
                <Text style={styles.networkBadgeText}>Réseau partenaire</Text>
              </View>
              <Text style={styles.networkName}>☕ {network.name}</Text>
              <Text style={styles.networkSub}>
                Valable dans {networkStations.length} station
                {networkStations.length > 1 ? "s" : ""} participante
                {networkStations.length > 1 ? "s" : ""}
              </Text>
              <View style={styles.counterBadgeRow}>
                <Text style={styles.counterText}>
                  {data?.consumed_total ?? 0} café
                  {(data?.consumed_total ?? 0) > 1 ? "s" : ""} dégusté
                  {(data?.consumed_total ?? 0) > 1 ? "s" : ""}
                </Text>
              </View>
            </View>
          ) : station ? (
            <View style={styles.stationCard}>
              <Ionicons name="location" size={18} color={colors.primary} />
              <View style={{ flex: 1 }}>
                <Text style={styles.stationName}>{station.name}</Text>
                {!!station.city && (
                  <Text style={styles.stationCity}>{station.city}</Text>
                )}
              </View>
              <View style={styles.counterBadge}>
                <Text style={styles.counterText}>
                  {data?.consumed_total ?? 0} ☕
                </Text>
              </View>
            </View>
          ) : null}

          {/* Jeton actif */}
          {active ? (
            <View style={styles.activeCard}>
              <Text style={styles.activeEmoji}>☕</Text>
              <Text style={styles.activeTitle}>1 café vous attend !</Text>

              {/* 🕒 Compte à rebours en JOURS restants (visible pompiste) */}
              {(() => {
                const daysLeft = Math.max(
                  0,
                  Math.ceil(
                    (new Date(active.expires_at).getTime() - Date.now()) /
                      (1000 * 60 * 60 * 24),
                  ),
                );
                return (
                  <View style={styles.countdownBadge}>
                    <Text style={styles.countdownLabel}>Validité</Text>
                    <Text style={styles.countdownValue}>
                      J-{daysLeft}
                    </Text>
                    <Text style={styles.countdownSub}>
                      {daysLeft > 1
                        ? `${daysLeft} jours restants`
                        : daysLeft === 1
                          ? "Dernier jour !"
                          : "Expire aujourd’hui"}
                    </Text>
                  </View>
                );
              })()}

              <Text style={styles.activeSub}>
                Valable jusqu’au {fmtDate(active.expires_at)}. Présentez cet
                écran au pompiste de la station.
              </Text>
              <TouchableOpacity
                style={styles.greenBtn}
                onPress={() => setModalOpen(true)}
                activeOpacity={0.85}
                testID="mescafes-validate-btn"
              >
                <Ionicons name="checkmark-circle" size={22} color="#FFF" />
                <Text style={styles.greenBtnText}>VALIDATION POMPISTE</Text>
              </TouchableOpacity>
              <Text style={styles.pompisteHint}>
                🔒 Réservé au pompiste — code PIN station requis
              </Text>
            </View>
          ) : (
            <View style={styles.noJetonCard}>
              <Ionicons name="cafe-outline" size={26} color="#8A8A92" />
              <Text style={styles.noJetonTitle}>Aucun café en attente</Text>
              <Text style={styles.noJetonText}>
                Créez une nouvelle ouverture dans un chantier pour gagner votre
                prochain café offert (1 max par jour).
              </Text>
            </View>
          )}

          {/* 🆕 Liste des stations participantes du réseau */}
          {network && networkStations.length > 0 && (
            <>
              <Text style={styles.sectionLabel}>
                Où utiliser mon café ({networkStations.length})
              </Text>
              {networkStations.map((s) => (
                <View key={s.id} style={styles.networkStationRow}>
                  <View style={styles.stationDot} />
                  <View style={{ flex: 1 }}>
                    <Text style={styles.historyLabel}>{s.name}</Text>
                    {(s.address || s.city) && (
                      <Text style={styles.historyDate}>
                        {s.address || s.city}
                      </Text>
                    )}
                  </View>
                  <Ionicons name="chevron-forward" size={18} color="#5A5A62" />
                </View>
              ))}
            </>
          )}

          {/* Historique */}
          {history.length > 0 && (
            <>
              <Text style={styles.sectionLabel}>Historique</Text>
              {history.map((j) => (
                <View key={j.id} style={styles.historyRow}>
                  <Ionicons
                    name={j.status === "consumed" ? "checkmark-circle" : "time-outline"}
                    size={20}
                    color={j.status === "consumed" ? GREEN : "#6E6E76"}
                  />
                  <View style={{ flex: 1 }}>
                    <Text style={styles.historyLabel}>
                      {j.status === "consumed" ? "Café dégusté" : "Jeton expiré"}
                    </Text>
                    <Text style={styles.historyDate}>
                      {j.status === "consumed"
                        ? fmtDate(j.consumed_at)
                        : `Gagné le ${fmtDate(j.earned_at)}`}
                    </Text>
                  </View>
                </View>
              ))}
            </>
          )}
        </ScrollView>
      )}

      <CafeJetonModal
        visible={modalOpen}
        jeton={active}
        stationName={station?.name}
        onClose={(consumed) => {
          setModalOpen(false);
          if (consumed) load();
        }}
      />
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
  headerTitle: { fontSize: 17, fontWeight: "800", color: "#FFF" },
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: 32,
  },
  emptyTitle: { fontSize: 18, fontWeight: "700", color: "#FFF", marginBottom: 6 },
  emptyText: {
    fontSize: 14,
    color: "#8A8A92",
    textAlign: "center",
    lineHeight: 20,
  },
  stationCard: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    backgroundColor: "#1A1A1E",
    borderRadius: 14,
    padding: 14,
    borderWidth: 1,
    borderColor: "#26262B",
    marginBottom: 14,
  },
  networkCard: {
    backgroundColor: "#1A1A1E",
    borderRadius: 14,
    padding: 16,
    borderWidth: 1,
    borderColor: colors.primary + "44",
    marginBottom: 14,
  },
  networkBadge: {
    alignSelf: "flex-start",
    backgroundColor: colors.primary + "22",
    borderColor: colors.primary + "55",
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 10,
    paddingVertical: 4,
    marginBottom: 8,
  },
  networkBadgeText: {
    color: colors.primary,
    fontSize: 10,
    fontWeight: "800",
    letterSpacing: 0.8,
    textTransform: "uppercase",
  },
  networkName: { fontSize: 22, fontWeight: "800", color: "#FFF" },
  networkSub: { fontSize: 13, color: "#A8A8B0", marginTop: 4 },
  counterBadgeRow: {
    marginTop: 10,
    alignSelf: "flex-start",
    backgroundColor: GREEN + "22",
    borderRadius: 10,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  networkStationRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    backgroundColor: "#1A1A1E",
    borderRadius: 12,
    padding: 12,
    borderWidth: 1,
    borderColor: "#26262B",
    marginBottom: 8,
  },
  stationDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: colors.primary,
  },
  stationName: { fontSize: 15, fontWeight: "700", color: "#FFF" },
  stationCity: { fontSize: 12, color: "#8A8A92", marginTop: 2 },
  counterBadge: {
    backgroundColor: GREEN + "20",
    borderRadius: 10,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  counterText: { fontSize: 13, fontWeight: "800", color: GREEN },
  activeCard: {
    backgroundColor: GREEN + "12",
    borderRadius: 18,
    padding: 22,
    alignItems: "center",
    borderWidth: 1,
    borderColor: GREEN + "44",
    marginBottom: 18,
  },
  activeEmoji: { fontSize: 44, marginBottom: 6 },
  activeTitle: { fontSize: 19, fontWeight: "800", color: "#FFF", marginBottom: 6 },
  countdownBadge: {
    backgroundColor: GREEN,
    borderRadius: 14,
    paddingHorizontal: 20,
    paddingVertical: 10,
    marginVertical: 12,
    alignItems: "center",
    minWidth: 180,
    shadowColor: GREEN,
    shadowOpacity: 0.35,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 4 },
    elevation: 6,
  },
  countdownLabel: {
    fontSize: 10,
    color: "#DCFCE7",
    fontWeight: "700",
    letterSpacing: 1,
    textTransform: "uppercase",
  },
  countdownValue: {
    fontSize: 36,
    fontWeight: "900",
    color: "#FFF",
    letterSpacing: 1,
    marginTop: -2,
  },
  countdownSub: {
    fontSize: 12,
    color: "#DCFCE7",
    fontWeight: "600",
    marginTop: 2,
  },
  activeSub: {
    fontSize: 13,
    color: "#A6A6AD",
    textAlign: "center",
    lineHeight: 19,
    marginBottom: 16,
  },
  greenBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    backgroundColor: GREEN,
    borderRadius: 14,
    paddingVertical: 15,
    alignSelf: "stretch",
    minHeight: 48,
  },
  greenBtnText: { fontSize: 15, fontWeight: "800", color: "#FFF" },
  pompisteHint: { fontSize: 11, color: "#6E6E76", marginTop: 8 },
  noJetonCard: {
    backgroundColor: "#1A1A1E",
    borderRadius: 14,
    padding: 20,
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#26262B",
    marginBottom: 18,
    gap: 6,
  },
  noJetonTitle: { fontSize: 15, fontWeight: "700", color: "#FFF" },
  noJetonText: {
    fontSize: 13,
    color: "#8A8A92",
    textAlign: "center",
    lineHeight: 19,
  },
  sectionLabel: {
    fontSize: 12,
    fontWeight: "700",
    color: "#6E6E76",
    textTransform: "uppercase",
    letterSpacing: 0.8,
    marginBottom: 8,
    marginTop: 4,
  },
  historyRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    backgroundColor: "#141417",
    borderRadius: 12,
    padding: 12,
    marginBottom: 8,
  },
  historyLabel: { fontSize: 14, fontWeight: "600", color: "#DDD" },
  historyDate: { fontSize: 12, color: "#6E6E76", marginTop: 2 },
});
