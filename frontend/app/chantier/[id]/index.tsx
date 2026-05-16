import React, { useCallback, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  Image,
  Modal,
  RefreshControl,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { api } from "@/src/services/api";
import { useAuth } from "@/src/context/AuthContext";
import { colors, statusMeta, blockMeta } from "@/src/theme";

type Chantier = {
  id: string;
  client_name: string;
  address: string;
  status: string;
  assigned_to?: string | null;
  created_at: string;
};

type Mesure = {
  id: string;
  block_type: string;
  label: string;
  photo_url?: string;
  alerts?: string[];
  slope_angle_deg?: number | null;
};

type UserOpt = { id: string; name: string; email: string; role: string };

export default function ChantierDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const { user } = useAuth();
  const canManage = user?.role === "admin" || user?.role === "commercial";
  const [chantier, setChantier] = useState<Chantier | null>(null);
  const [mesures, setMesures] = useState<Mesure[]>([]);
  const [users, setUsers] = useState<UserOpt[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [assignOpen, setAssignOpen] = useState(false);

  const fetchAll = useCallback(async () => {
    try {
      const [c, m, u] = await Promise.all([
        api.get<Chantier>(`/chantiers/${id}`),
        api.get<Mesure[]>(`/chantiers/${id}/mesures`),
        api.get<UserOpt[]>("/users"),
      ]);
      setChantier(c.data);
      setMesures(m.data);
      setUsers(u.data);
    } catch {
      Alert.alert("Erreur", "Impossible de charger le chantier.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [id]);

  useFocusEffect(
    useCallback(() => {
      fetchAll();
    }, [fetchAll])
  );

  const assignTo = async (userId: string | null) => {
    try {
      const res = await api.patch<Chantier>(`/chantiers/${id}`, { assigned_to: userId });
      setChantier(res.data);
      setAssignOpen(false);
    } catch {
      Alert.alert("Erreur", "Affectation impossible.");
    }
  };

  const assignedUser = chantier?.assigned_to
    ? users.find((u) => u.id === chantier.assigned_to)
    : null;

  const meta = chantier ? statusMeta[chantier.status] : null;

  if (loading || !chantier) {
    return (
      <View style={[styles.flex, styles.center]}>
        <ActivityIndicator color={colors.primary} size="large" />
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.flex} edges={["bottom"]}>
      <FlatList
        data={mesures}
        keyExtractor={(i) => i.id}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => {
              setRefreshing(true);
              fetchAll();
            }}
            tintColor={colors.primary}
          />
        }
        ListHeaderComponent={
          <View>
            <View style={styles.header}>
              <Text style={styles.clientName}>{chantier.client_name}</Text>
              <View style={styles.addressRow}>
                <Ionicons name="location" size={14} color={colors.textSecondary} />
                <Text style={styles.address}>{chantier.address}</Text>
              </View>
              {meta && (
                <View style={[styles.badge, { backgroundColor: meta.bg }]}>
                  <View style={[styles.badgeDot, { backgroundColor: meta.color }]} />
                  <Text style={[styles.badgeText, { color: meta.color }]}>{meta.label}</Text>
                </View>
              )}

              <TouchableOpacity
                testID="assign-button"
                onPress={() => canManage && setAssignOpen(true)}
                disabled={!canManage}
                style={[styles.assignRow, !canManage && { opacity: 0.6 }]}
                activeOpacity={0.7}
              >
                <Ionicons name="person-circle-outline" size={18} color={colors.primary} />
                <Text style={styles.assignLabel}>Affecté à :</Text>
                <Text style={styles.assignValue}>
                  {assignedUser ? assignedUser.name : "Personne — affecter"}
                </Text>
                <Ionicons name="chevron-down" size={16} color={colors.textSecondary} style={{ marginLeft: "auto" }} />
              </TouchableOpacity>
            </View>

            <View style={styles.statsRow}>
              <View style={styles.statCard}>
                <Text style={styles.statValue}>{mesures.length}</Text>
                <Text style={styles.statLabel}>Ouvertures</Text>
              </View>
              <View style={styles.statCard}>
                <Text style={styles.statValue}>
                  {mesures.reduce((acc, m) => acc + (m.alerts?.length ?? 0), 0)}
                </Text>
                <Text style={styles.statLabel}>Alertes</Text>
              </View>
            </View>

            <Text style={styles.sectionTitle}>OUVERTURES</Text>
          </View>
        }
        renderItem={({ item, index }) => {
          const block = blockMeta[item.block_type] ?? { label: item.block_type, icon: "square-outline" };
          return (
            <View testID={`mesure-card-${item.id}`} style={styles.mesureCard}>
              <View style={styles.mesureRow}>
                {item.photo_url ? (
                  <Image source={{ uri: item.photo_url }} style={styles.mesureThumb} />
                ) : (
                  <View style={styles.mesureThumbPlaceholder}>
                    <Ionicons name={block.icon as any} size={28} color={colors.textSecondary} />
                  </View>
                )}
                <View style={{ flex: 1 }}>
                  <Text style={styles.mesureLabel}>
                    #{index + 1} · {item.label}
                  </Text>
                  <Text style={styles.mesureType}>{block.label}</Text>
                  {item.slope_angle_deg != null && (
                    <Text style={styles.slope}>Pente : {item.slope_angle_deg}°</Text>
                  )}
                </View>
              </View>
              {item.alerts && item.alerts.length > 0 && (
                <View style={styles.alertWrap}>
                  {item.alerts.map((a, i) => (
                    <Text key={i} style={styles.alertText}>
                      {a}
                    </Text>
                  ))}
                </View>
              )}
            </View>
          );
        }}
        contentContainerStyle={{ padding: 16, paddingBottom: 200 }}
        ListEmptyComponent={
          <View style={styles.empty}>
            <Ionicons name="grid-outline" size={48} color={colors.borderStrong} />
            <Text style={styles.emptyText}>Aucune ouverture mesurée</Text>
          </View>
        }
      />

      <View style={styles.footer}>
        {chantier.status !== "cloture" && canManage && (
          <TouchableOpacity
            testID="close-project-button"
            onPress={() => router.push(`/chantier/${id}/closure`)}
            style={[styles.btn, styles.btnSecondary]}
            activeOpacity={0.7}
          >
            <Ionicons name="flag-outline" size={20} color={colors.textPrimary} />
            <Text style={styles.btnSecondaryText}>CLÔTURER</Text>
          </TouchableOpacity>
        )}
        <TouchableOpacity
          testID="add-mesure-button"
          onPress={() => router.push(`/chantier/${id}/new-mesure`)}
          style={[styles.btn, styles.btnPrimary]}
          activeOpacity={0.85}
        >
          <Ionicons name="add-circle" size={22} color="#000" />
          <Text style={styles.btnPrimaryText}>AJOUTER UNE OUVERTURE</Text>
        </TouchableOpacity>
      </View>

      <Modal visible={assignOpen} transparent animationType="fade" onRequestClose={() => setAssignOpen(false)}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>AFFECTER LE CHANTIER</Text>
            <Text style={styles.modalSub}>Sélectionnez un membre de l'équipe</Text>
            <FlatList
              data={users}
              keyExtractor={(u) => u.id}
              style={{ maxHeight: 320 }}
              ListHeaderComponent={
                <TouchableOpacity
                  testID="assign-none"
                  onPress={() => assignTo(null)}
                  style={[styles.assignItem, !chantier.assigned_to && styles.assignItemActive]}
                  activeOpacity={0.7}
                >
                  <Ionicons name="close-circle-outline" size={20} color={colors.textSecondary} />
                  <Text style={styles.assignItemText}>Aucune affectation</Text>
                </TouchableOpacity>
              }
              renderItem={({ item }) => {
                const active = chantier.assigned_to === item.id;
                return (
                  <TouchableOpacity
                    testID={`assign-user-${item.id}`}
                    onPress={() => assignTo(item.id)}
                    style={[styles.assignItem, active && styles.assignItemActive]}
                    activeOpacity={0.7}
                  >
                    <Ionicons
                      name={
                        item.role === "admin"
                          ? "shield-checkmark"
                          : item.role === "commercial"
                          ? "briefcase"
                          : "construct"
                      }
                      size={20}
                      color={active ? colors.primary : colors.textSecondary}
                    />
                    <View style={{ flex: 1 }}>
                      <Text style={styles.assignItemText}>{item.name}</Text>
                      <Text style={styles.assignItemRole}>{item.role}</Text>
                    </View>
                    {active && <Ionicons name="checkmark-circle" size={20} color={colors.primary} />}
                  </TouchableOpacity>
                );
              }}
            />
            <TouchableOpacity
              testID="assign-cancel"
              onPress={() => setAssignOpen(false)}
              style={[styles.btn, styles.btnSecondary, { marginTop: 12 }]}
              activeOpacity={0.7}
            >
              <Text style={styles.btnSecondaryText}>FERMER</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: colors.bg },
  center: { alignItems: "center", justifyContent: "center" },
  header: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: 18,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    marginBottom: 12,
  },
  clientName: { color: colors.textPrimary, fontSize: 22, fontWeight: "900" },
  addressRow: { flexDirection: "row", alignItems: "center", gap: 6, marginTop: 4 },
  address: { color: colors.textSecondary, fontSize: 13, flex: 1 },
  badge: {
    flexDirection: "row",
    alignItems: "center",
    alignSelf: "flex-start",
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 4,
    gap: 6,
    marginTop: 12,
  },
  badgeDot: { width: 6, height: 6, borderRadius: 3 },
  badgeText: { fontSize: 11, fontWeight: "800", textTransform: "uppercase", letterSpacing: 0.8 },
  statsRow: { flexDirection: "row", gap: 12, marginBottom: 18 },
  statCard: {
    flex: 1,
    backgroundColor: colors.surface,
    padding: 16,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
  },
  statValue: { color: colors.primary, fontSize: 28, fontWeight: "900" },
  statLabel: {
    color: colors.textSecondary,
    fontSize: 11,
    textTransform: "uppercase",
    letterSpacing: 0.8,
    fontWeight: "700",
  },
  sectionTitle: {
    color: colors.textSecondary,
    fontSize: 12,
    fontWeight: "800",
    letterSpacing: 1.5,
    marginBottom: 10,
  },
  mesureCard: {
    backgroundColor: colors.surface,
    borderColor: colors.borderSubtle,
    borderWidth: 1,
    borderRadius: 10,
    padding: 12,
    marginBottom: 10,
  },
  mesureRow: { flexDirection: "row", alignItems: "center", gap: 12 },
  mesureThumb: { width: 64, height: 64, borderRadius: 8, backgroundColor: colors.bg },
  mesureThumbPlaceholder: {
    width: 64,
    height: 64,
    borderRadius: 8,
    backgroundColor: colors.bg,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    alignItems: "center",
    justifyContent: "center",
  },
  mesureLabel: { color: colors.textPrimary, fontWeight: "800", fontSize: 15 },
  mesureType: { color: colors.textSecondary, marginTop: 2, fontSize: 13 },
  slope: { color: colors.primary, fontSize: 12, marginTop: 4, fontWeight: "700" },
  alertWrap: {
    marginTop: 10,
    paddingTop: 10,
    borderTopWidth: 1,
    borderTopColor: colors.borderSubtle,
    gap: 4,
  },
  alertText: { color: colors.alert, fontSize: 12, fontWeight: "700" },
  empty: { alignItems: "center", padding: 50, gap: 8 },
  emptyText: { color: colors.textSecondary, fontWeight: "700" },
  footer: {
    position: "absolute",
    bottom: 0,
    left: 0,
    right: 0,
    padding: 16,
    paddingBottom: 24,
    backgroundColor: colors.bg,
    borderTopWidth: 1,
    borderTopColor: colors.borderSubtle,
    gap: 10,
  },
  btn: {
    minHeight: 64,
    borderRadius: 8,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
  },
  btnPrimary: { backgroundColor: colors.primary },
  btnPrimaryText: { color: "#000", fontWeight: "900", fontSize: 15, letterSpacing: 1 },
  btnSecondary: { borderWidth: 2, borderColor: colors.borderStrong },
  btnSecondaryText: { color: colors.textPrimary, fontWeight: "800", letterSpacing: 1 },
});
