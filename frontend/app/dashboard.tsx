import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  KeyboardAvoidingView,
  Modal,
  Platform,
  RefreshControl,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useFocusEffect, useRouter } from "expo-router";
import { api } from "@/src/services/api";
import { useAuth } from "@/src/context/AuthContext";
import { subscribeQueueSize, syncQueue } from "@/src/services/offlineQueue";
import { colors, statusMeta } from "@/src/theme";

type Chantier = {
  id: string;
  client_name: string;
  address: string;
  status: string;
  created_at: string;
};

const FILTERS: { key: string; label: string }[] = [
  { key: "all", label: "Tous" },
  { key: "devis_a_faire", label: "Devis à faire" },
  { key: "technique_a_valider", label: "Technique à valider" },
  { key: "cloture", label: "Clôturés" },
];

export default function Dashboard() {
  const { user, signOut } = useAuth();
  const router = useRouter();
  const [items, setItems] = useState<Chantier[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [filter, setFilter] = useState("all");
  const [q, setQ] = useState("");
  const [newModal, setNewModal] = useState(false);
  const [newClient, setNewClient] = useState("");
  const [newAddr, setNewAddr] = useState("");
  const [creating, setCreating] = useState(false);
  const [pendingCount, setPendingCount] = useState(0);

  useEffect(() => {
    return subscribeQueueSize(setPendingCount);
  }, []);

  const canCreate = user?.role === "admin" || user?.role === "commercial";

  const fetchData = useCallback(async () => {
    try {
      const params: Record<string, string> = {};
      if (filter !== "all") params.status_filter = filter;
      if (q.trim()) params.q = q.trim();
      const res = await api.get<Chantier[]>("/chantiers", { params });
      setItems(res.data);
    } catch (e) {
      Alert.alert("Erreur", "Chargement impossible.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [filter, q]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useFocusEffect(
    useCallback(() => {
      fetchData();
    }, [fetchData])
  );

  const onRefresh = () => {
    setRefreshing(true);
    fetchData();
  };

  const createChantier = async () => {
    if (!newClient.trim() || !newAddr.trim()) {
      Alert.alert("Champs requis", "Client et adresse sont obligatoires.");
      return;
    }
    setCreating(true);
    try {
      const res = await api.post<Chantier>("/chantiers", {
        client_name: newClient.trim(),
        address: newAddr.trim(),
      });
      setNewModal(false);
      setNewClient("");
      setNewAddr("");
      router.push(`/chantier/${res.data.id}`);
    } catch (e) {
      Alert.alert("Erreur", "Création impossible.");
    } finally {
      setCreating(false);
    }
  };

  const logout = async () => {
    await signOut();
    router.replace("/");
  };

  const renderItem = ({ item }: { item: Chantier }) => {
    const meta = statusMeta[item.status] ?? {
      label: item.status,
      color: "#fff",
      bg: "#333",
    };
    return (
      <TouchableOpacity
        testID={`project-card-${item.id}`}
        onPress={() => router.push(`/chantier/${item.id}`)}
        activeOpacity={0.7}
        style={styles.card}
      >
        <View style={styles.cardHeader}>
          <View style={{ flex: 1 }}>
            <Text style={styles.cardTitle} numberOfLines={1}>
              {item.client_name}
            </Text>
            <Text style={styles.cardAddr} numberOfLines={1}>
              <Ionicons name="location-outline" size={12} color={colors.textSecondary} />{" "}
              {item.address}
            </Text>
          </View>
          <Ionicons name="chevron-forward" size={20} color={colors.textSecondary} />
        </View>
        <View
          style={[styles.badge, { backgroundColor: meta.bg }]}
        >
          <View style={[styles.badgeDot, { backgroundColor: meta.color }]} />
          <Text style={[styles.badgeText, { color: meta.color }]}>{meta.label}</Text>
        </View>
      </TouchableOpacity>
    );
  };

  return (
    <SafeAreaView style={styles.container} edges={["top", "bottom"]}>
      <View style={styles.topBar}>
        <View style={{ flex: 1 }}>
          <Text style={styles.welcome}>Bonjour</Text>
          <Text style={styles.userName} numberOfLines={1}>
            {user?.name}
          </Text>
          {user?.company_id && user.company_id !== "default" && (
            <Text style={styles.companyTag} numberOfLines={1}>
              {user.company_id}
            </Text>
          )}
        </View>
        {user?.role === "admin" && (
          <TouchableOpacity
            testID="admin-stats-button"
            onPress={() => router.push("/admin/stats")}
            style={[styles.logoutBtn, { marginRight: 8 }]}
            activeOpacity={0.7}
          >
            <Ionicons name="stats-chart" size={22} color={colors.primary} />
          </TouchableOpacity>
        )}
        {user?.role === "admin" && (
          <TouchableOpacity
            testID="admin-feedbacks-button"
            onPress={() => router.push("/admin/feedbacks")}
            style={[styles.logoutBtn, { marginRight: 8 }]}
            activeOpacity={0.7}
          >
            <Ionicons name="megaphone-outline" size={22} color={colors.primary} />
          </TouchableOpacity>
        )}
        <TouchableOpacity
          testID="logout-button"
          onPress={logout}
          style={styles.logoutBtn}
          activeOpacity={0.7}
        >
          <Ionicons name="log-out-outline" size={22} color={colors.textPrimary} />
        </TouchableOpacity>
      </View>

      <View style={styles.searchWrap}>
        <Ionicons name="search" size={18} color={colors.textSecondary} />
        <TextInput
          testID="search-input"
          value={q}
          onChangeText={setQ}
          placeholder="Rechercher un client ou une adresse..."
          placeholderTextColor={colors.placeholder}
          style={styles.searchInput}
          returnKeyType="search"
          onSubmitEditing={fetchData}
        />
        {q.length > 0 && (
          <TouchableOpacity onPress={() => setQ("")}>
            <Ionicons name="close-circle" size={18} color={colors.textSecondary} />
          </TouchableOpacity>
        )}
      </View>

      <View style={styles.filterRow}>
        <FlatList
          horizontal
          data={FILTERS}
          showsHorizontalScrollIndicator={false}
          keyExtractor={(i) => i.key}
          contentContainerStyle={{ paddingHorizontal: 16, gap: 8 }}
          renderItem={({ item }) => (
            <TouchableOpacity
              testID={`filter-${item.key}`}
              onPress={() => setFilter(item.key)}
              style={[styles.chip, filter === item.key && styles.chipActive]}
              activeOpacity={0.7}
            >
              <Text style={[styles.chipText, filter === item.key && styles.chipTextActive]}>
                {item.label}
              </Text>
            </TouchableOpacity>
          )}
        />
      </View>

      {loading ? (
        <View style={[styles.flex, styles.center]}>
          <ActivityIndicator color={colors.primary} size="large" />
        </View>
      ) : (
        <FlatList
          data={items}
          keyExtractor={(i) => i.id}
          renderItem={renderItem}
          contentContainerStyle={{ padding: 16, paddingBottom: 120 }}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={onRefresh}
              tintColor={colors.primary}
            />
          }
          ListEmptyComponent={
            <View style={styles.empty}>
              <Ionicons name="folder-open-outline" size={48} color={colors.borderStrong} />
              <Text style={styles.emptyText}>Aucun chantier</Text>
              <Text style={styles.emptySub}>Créez votre premier chantier ↓</Text>
            </View>
          }
        />
      )}

      <TouchableOpacity
        testID="new-chantier-button"
        onPress={() => setNewModal(true)}
        style={[styles.fab, !canCreate && { display: "none" }]}
        activeOpacity={0.85}
      >
        <Ionicons name="add" size={26} color="#000" />
        <Text style={styles.fabText}>NOUVEAU CHANTIER</Text>
      </TouchableOpacity>

      {pendingCount > 0 && (
        <TouchableOpacity
          testID="offline-queue-banner"
          onPress={() => syncQueue().then(() => fetchData())}
          activeOpacity={0.8}
          style={[styles.offlineBanner, !canCreate && { bottom: 24 }]}
        >
          <Ionicons name="cloud-upload" size={18} color="#000" />
          <Text style={styles.offlineText}>
            {pendingCount} mesure{pendingCount > 1 ? "s" : ""} en attente · Toucher pour synchroniser
          </Text>
        </TouchableOpacity>
      )}

      <Modal visible={newModal} transparent animationType="fade" onRequestClose={() => setNewModal(false)}>
        <KeyboardAvoidingView
          behavior={Platform.OS === "ios" ? "padding" : "height"}
          style={styles.modalOverlay}
        >
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>NOUVEAU CHANTIER</Text>
            <Text style={styles.label}>Nom du client</Text>
            <TextInput
              testID="new-client-input"
              value={newClient}
              onChangeText={setNewClient}
              placeholder="ex. M. Dupont"
              placeholderTextColor={colors.placeholder}
              style={styles.input}
            />
            <Text style={styles.label}>Adresse</Text>
            <TextInput
              testID="new-address-input"
              value={newAddr}
              onChangeText={setNewAddr}
              placeholder="ex. 12 rue de la Paix, Paris"
              placeholderTextColor={colors.placeholder}
              style={styles.input}
            />
            <View style={styles.modalActions}>
              <TouchableOpacity
                onPress={() => setNewModal(false)}
                style={[styles.modalBtn, styles.modalBtnSecondary]}
                activeOpacity={0.7}
              >
                <Text style={styles.modalBtnSecondaryText}>Annuler</Text>
              </TouchableOpacity>
              <TouchableOpacity
                testID="new-chantier-submit"
                onPress={createChantier}
                disabled={creating}
                style={[styles.modalBtn, styles.modalBtnPrimary]}
                activeOpacity={0.85}
              >
                {creating ? (
                  <ActivityIndicator color="#000" />
                ) : (
                  <Text style={styles.modalBtnPrimaryText}>Créer</Text>
                )}
              </TouchableOpacity>
            </View>
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  flex: { flex: 1 },
  center: { alignItems: "center", justifyContent: "center" },
  topBar: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 20,
    paddingTop: 8,
    paddingBottom: 14,
  },
  welcome: { color: colors.textSecondary, fontSize: 13, letterSpacing: 0.5 },
  userName: { color: colors.textPrimary, fontSize: 22, fontWeight: "900", marginTop: 2 },
  companyTag: {
    color: colors.primary,
    fontSize: 11,
    fontWeight: "700",
    letterSpacing: 1,
    textTransform: "uppercase",
    marginTop: 2,
  },
  logoutBtn: {
    marginLeft: "auto",
    width: 48,
    height: 48,
    borderRadius: 8,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    alignItems: "center",
    justifyContent: "center",
  },
  searchWrap: {
    marginHorizontal: 16,
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    backgroundColor: colors.surface,
    borderColor: colors.borderSubtle,
    borderWidth: 1,
    borderRadius: 10,
    paddingHorizontal: 14,
    minHeight: 56,
  },
  searchInput: { flex: 1, color: colors.textPrimary, fontSize: 16, paddingVertical: 8 },
  filterRow: { marginTop: 14, marginBottom: 4 },
  chip: {
    paddingHorizontal: 16,
    minHeight: 40,
    borderRadius: 100,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    alignItems: "center",
    justifyContent: "center",
  },
  chipActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  chipText: {
    color: colors.textSecondary,
    fontWeight: "700",
    fontSize: 12,
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  chipTextActive: { color: "#000" },
  card: {
    backgroundColor: colors.surface,
    borderColor: colors.borderSubtle,
    borderWidth: 1,
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
  },
  cardHeader: { flexDirection: "row", alignItems: "center", marginBottom: 10 },
  cardTitle: { color: colors.textPrimary, fontSize: 17, fontWeight: "800", marginBottom: 4 },
  cardAddr: { color: colors.textSecondary, fontSize: 13 },
  badge: {
    flexDirection: "row",
    alignItems: "center",
    alignSelf: "flex-start",
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 4,
    gap: 6,
  },
  badgeDot: { width: 6, height: 6, borderRadius: 3 },
  badgeText: {
    fontSize: 10,
    fontWeight: "800",
    textTransform: "uppercase",
    letterSpacing: 0.8,
  },
  empty: { alignItems: "center", padding: 60, gap: 8 },
  emptyText: { color: colors.textPrimary, fontWeight: "800", fontSize: 16 },
  emptySub: { color: colors.textSecondary, fontSize: 13 },
  fab: {
    position: "absolute",
    bottom: 24,
    left: 16,
    right: 16,
    minHeight: 64,
    backgroundColor: colors.primary,
    borderRadius: 8,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    shadowColor: colors.primary,
    shadowOpacity: 0.4,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 },
    elevation: 8,
  },
  fabText: { color: "#000", fontWeight: "900", fontSize: 16, letterSpacing: 1.2 },
  offlineBanner: {
    position: "absolute",
    bottom: 100,
    left: 16,
    right: 16,
    backgroundColor: colors.warning,
    borderRadius: 8,
    paddingHorizontal: 14,
    minHeight: 48,
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  offlineText: { color: "#000", fontWeight: "800", fontSize: 13, flex: 1 },
  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.8)",
    justifyContent: "center",
    padding: 20,
  },
  modalCard: {
    backgroundColor: colors.surface,
    borderColor: colors.borderSubtle,
    borderWidth: 1,
    borderRadius: 12,
    padding: 22,
  },
  modalTitle: {
    color: colors.textPrimary,
    fontWeight: "900",
    fontSize: 18,
    letterSpacing: 1,
    marginBottom: 16,
  },
  label: {
    color: colors.textSecondary,
    fontSize: 11,
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: 1.2,
    marginTop: 10,
    marginBottom: 6,
  },
  input: {
    backgroundColor: colors.inputBg,
    borderColor: colors.borderSubtle,
    borderWidth: 2,
    borderRadius: 8,
    color: colors.textPrimary,
    minHeight: 56,
    paddingHorizontal: 14,
    fontSize: 16,
  },
  modalActions: { flexDirection: "row", marginTop: 20, gap: 10 },
  modalBtn: { flex: 1, minHeight: 56, alignItems: "center", justifyContent: "center", borderRadius: 8 },
  modalBtnSecondary: { borderWidth: 2, borderColor: colors.borderStrong },
  modalBtnSecondaryText: { color: colors.textPrimary, fontWeight: "700", textTransform: "uppercase" },
  modalBtnPrimary: { backgroundColor: colors.primary },
  modalBtnPrimaryText: { color: "#000", fontWeight: "900", textTransform: "uppercase", letterSpacing: 0.8 },
});
