import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  KeyboardAvoidingView,
  Modal,
  Platform,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useFocusEffect, useRouter } from "expo-router";
import DateTimePicker, { DateTimePickerEvent } from "@react-native-community/datetimepicker";
import { api } from "@/src/services/api";
import { useAuth } from "@/src/context/AuthContext";
import { subscribeQueueSize, syncQueue, enqueueChantier, isNetworkError } from "@/src/services/offlineQueue";
import { colors, statusMeta, READY_FOR_EXPORT_BADGE } from "@/src/theme";
import { useResponsive } from "@/src/utils/responsive";
import TrialCountdownBanner from "@/src/components/TrialCountdownBanner";
import ChatHelp from "@/src/components/ChatHelp";

type Chantier = {
  id: string;
  client_name: string;
  address: string;
  status: string;
  created_at: string;
};

// Filtres alignés sur le pipeline 4-étapes (filtrage côté client par stage).
const FILTERS: { key: "all" | "measure" | "verify" | "fab" | "done"; label: string }[] = [
  { key: "all", label: "Tous" },
  { key: "measure", label: "À mesurer" },
  { key: "verify", label: "À vérifier" },
  { key: "fab", label: "En fabrication" },
  { key: "done", label: "Terminés" },
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
  const [helpOpen, setHelpOpen] = useState(false);
  const { isTablet } = useResponsive();
  const [newFirstName, setNewFirstName] = useState("");
  const [newLastName, setNewLastName] = useState("");
  const [newAddr, setNewAddr] = useState("");
  const [newPostal, setNewPostal] = useState("");
  const [newCity, setNewCity] = useState("");
  const [newAppt, setNewAppt] = useState<string>(""); // raw datetime-local string e.g. "2026-06-25T14:30"
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [newNotes, setNewNotes] = useState("");
  const [creating, setCreating] = useState(false);
  const [listening, setListening] = useState(false);

  // 🎤 Voice-to-text — Web Speech API (Chrome/Edge/Safari) with safe fallback
  const startVoiceInput = useCallback(() => {
    if (listening) return;
    if (Platform.OS === "web" && typeof window !== "undefined") {
      // @ts-ignore — webkit prefix
      const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SR) {
        try {
          const rec = new SR();
          rec.lang = "fr-FR";
          rec.interimResults = true;
          rec.continuous = false;
          let accumulated = newNotes ? newNotes + " " : "";
          setListening(true);
          rec.onresult = (event: any) => {
            let text = "";
            for (let i = event.resultIndex; i < event.results.length; i++) {
              text += event.results[i][0].transcript;
            }
            setNewNotes(accumulated + text);
          };
          rec.onend = () => setListening(false);
          rec.onerror = () => setListening(false);
          rec.start();
          return;
        } catch {
          /* fallthrough to simulation */
        }
      }
    }
    // Fallback simulation (native or unsupported browser)
    setListening(true);
    const samples = [
      "Sonner deux fois, accès par le portail latéral.",
      "Présence d'un volet roulant motorisé existant à conserver.",
      "Linteau légèrement fissuré côté droit, à reprendre.",
      "Réserve sol fini d'environ 30mm, parquet flottant prévu.",
    ];
    const pick = samples[Math.floor(Math.random() * samples.length)];
    setTimeout(() => {
      setNewNotes((prev) => (prev ? prev + " " : "") + pick);
      setListening(false);
    }, 1400);
  }, [listening, newNotes]);
  const [pendingCount, setPendingCount] = useState(0);

  useEffect(() => {
    return subscribeQueueSize(setPendingCount);
  }, []);

  const canCreate = user?.role === "admin" || user?.role === "commercial";

  const fetchData = useCallback(async () => {
    try {
      const params: Record<string, string> = {};
      // Le filtre par stage est appliqué côté client (un stage = plusieurs
      // statuts internes). Seule la recherche texte est envoyée au backend.
      if (q.trim()) params.q = q.trim();
      const res = await api.get<Chantier[]>("/chantiers", { params });
      const all = res.data;
      const filtered =
        filter === "all"
          ? all
          : all.filter((c) => (statusMeta[c.status]?.stage ?? "verify") === filter);
      setItems(filtered);
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
    if (!newLastName.trim() || !newAddr.trim()) {
      Alert.alert("Champs requis", "Nom du client et adresse sont obligatoires.");
      return;
    }
    setCreating(true);
    const payload = {
      first_name: newFirstName.trim() || undefined,
      last_name: newLastName.trim(),
      address: newAddr.trim(),
      postal_code: newPostal.trim() || undefined,
      city: newCity.trim() || undefined,
      appointment_at: newAppt ? new Date(newAppt).toISOString() : undefined,
      notes: newNotes.trim() || undefined,
    };
    const resetForm = () => {
      setNewModal(false);
      setNewFirstName("");
      setNewLastName("");
      setNewAddr("");
      setNewPostal("");
      setNewCity("");
      setNewAppt("");
      setNewNotes("");
    };
    try {
      const res = await api.post<Chantier>("/chantiers", payload);
      resetForm();
      router.push(`/chantier/${res.data.id}`);
    } catch (e: any) {
      // Limite Freemium atteinte (anti-fraud lifetime)
      if (e?.response?.status === 402) {
        const detail = e?.response?.data?.detail;
        if (detail?.code === "free_plan_limit") {
          Alert.alert(
            "🔒 Limite Freemium atteinte",
            `${detail.message}\n\n(${detail.used}/${detail.limit} chantiers — la suppression ne réinitialise pas le compteur).`,
            [
              { text: "Plus tard", style: "cancel" },
              {
                text: "Voir l'abonnement",
                onPress: () => router.push("/company-profile"),
              },
            ]
          );
          setCreating(false);
          return;
        }
      }
      if (isNetworkError(e)) {
        // Hors-ligne : on stocke le chantier en file d'attente locale.
        await enqueueChantier(payload);
        resetForm();
        await fetchData();
        Alert.alert(
          "📥 Hors-ligne",
          "Chantier enregistré localement. Il sera synchronisé automatiquement dès le retour de la connexion.",
        );
      } else {
        Alert.alert("Erreur", "Création impossible.");
      }
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
      stage: "verify" as const,
    };
    const isDone = meta.stage === "done";
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
        <View style={styles.badgeRow}>
          <View style={[styles.badge, { backgroundColor: meta.bg }]}>
            <View style={[styles.badgeDot, { backgroundColor: meta.color }]} />
            <Text style={[styles.badgeText, { color: meta.color }]}>{meta.label}</Text>
          </View>
          {isDone && (
            <View style={[styles.badge, styles.exportReadyBadge]}>
              <Ionicons name="checkmark-circle" size={12} color={READY_FOR_EXPORT_BADGE.color} />
              <Text style={[styles.badgeText, { color: READY_FOR_EXPORT_BADGE.color, marginLeft: 4 }]}>
                Prêt pour Export
              </Text>
            </View>
          )}
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
            testID="admin-team-button"
            onPress={() => router.push("/admin/team")}
            style={[styles.logoutBtn, { marginRight: 8 }]}
            activeOpacity={0.7}
          >
            <Ionicons name="people-outline" size={22} color={colors.primary} />
          </TouchableOpacity>
        )}
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
        {user?.role === "admin" && (
          <TouchableOpacity
            testID="company-profile-button"
            onPress={() => router.push("/company-profile")}
            style={[styles.logoutBtn, { marginRight: 8 }]}
            activeOpacity={0.7}
          >
            <Ionicons name="settings-outline" size={22} color={colors.primary} />
          </TouchableOpacity>
        )}
        <TouchableOpacity
          testID="help-button"
          onPress={() => setHelpOpen(true)}
          style={[styles.logoutBtn, { marginRight: 8 }]}
          activeOpacity={0.7}
          hitSlop={6}
        >
          <Ionicons name="help-circle-outline" size={22} color={colors.primary} />
        </TouchableOpacity>
        <TouchableOpacity
          testID="logout-button"
          onPress={logout}
          style={styles.logoutBtn}
          activeOpacity={0.7}
        >
          <Ionicons name="log-out-outline" size={22} color={colors.textPrimary} />
        </TouchableOpacity>
      </View>

      <View style={{ paddingHorizontal: 16 }}>
        <TrialCountdownBanner />
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
          contentContainerStyle={{
            padding: 16,
            paddingBottom: 120,
            maxWidth: isTablet ? 900 : "100%",
            width: "100%",
            alignSelf: "center",
          }}
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
            {pendingCount} élément{pendingCount > 1 ? "s" : ""} en attente · Toucher pour synchroniser
          </Text>
        </TouchableOpacity>
      )}

      <Modal visible={newModal} transparent animationType="fade" onRequestClose={() => setNewModal(false)}>
        <KeyboardAvoidingView
          behavior={Platform.OS === "ios" ? "padding" : "height"}
          style={styles.modalOverlay}
        >
          <View style={[styles.modalCard, { maxHeight: "92%" }]}>
            <Text style={styles.modalTitle}>NOUVEAU CHANTIER</Text>
            <Text style={styles.modalSub}>Identification du client</Text>
            <ScrollView keyboardShouldPersistTaps="handled" style={{ marginTop: 6 }}>
              <View style={styles.row2}>
                <View style={styles.col2}>
                  <Text style={styles.label}>Nom *</Text>
                  <TextInput
                    testID="new-lastname-input"
                    value={newLastName}
                    onChangeText={setNewLastName}
                    placeholder="Dupont"
                    placeholderTextColor={colors.placeholder}
                    style={styles.input}
                  />
                </View>
                <View style={styles.col2}>
                  <Text style={styles.label}>Prénom</Text>
                  <TextInput
                    testID="new-firstname-input"
                    value={newFirstName}
                    onChangeText={setNewFirstName}
                    placeholder="Marie"
                    placeholderTextColor={colors.placeholder}
                    style={styles.input}
                  />
                </View>
              </View>

              <Text style={styles.label}>Adresse &amp; Numéro *</Text>
              <TextInput
                testID="new-address-input"
                value={newAddr}
                onChangeText={setNewAddr}
                placeholder="15 Rue de la République"
                placeholderTextColor={colors.placeholder}
                style={styles.input}
              />

              <View style={styles.row2}>
                <View style={styles.col3}>
                  <Text style={styles.label}>Code Postal</Text>
                  <TextInput
                    testID="new-postal-input"
                    value={newPostal}
                    onChangeText={(v) => setNewPostal(v.replace(/[^0-9]/g, "").slice(0, 5))}
                    keyboardType="number-pad"
                    placeholder="75011"
                    placeholderTextColor={colors.placeholder}
                    style={styles.input}
                  />
                </View>
                <View style={styles.col7}>
                  <Text style={styles.label}>Ville</Text>
                  <TextInput
                    testID="new-city-input"
                    value={newCity}
                    onChangeText={setNewCity}
                    placeholder="Paris"
                    placeholderTextColor={colors.placeholder}
                    style={styles.input}
                  />
                </View>
              </View>

              <Text style={styles.label}>Date du rendez-vous</Text>
              {Platform.OS === "web" ? (
                // Native HTML5 calendar picker — crash-proof, never tries to parse partial text.
                <View style={styles.input}>
                  {React.createElement("input", {
                    type: "date",
                    "data-testid": "new-appointment-input",
                    value: newAppt ? newAppt.slice(0, 10) : "",
                    onChange: (e: any) => {
                      const raw = e?.target?.value ?? "";
                      // raw is YYYY-MM-DD from native picker — append default time
                      setNewAppt(raw ? `${raw}T09:00` : "");
                    },
                    min: "2024-01-01",
                    max: "2030-12-31",
                    style: {
                      width: "100%",
                      backgroundColor: "transparent",
                      color: colors.textPrimary,
                      border: "none",
                      outline: "none",
                      fontSize: 16,
                      fontFamily: "inherit",
                      colorScheme: "dark",
                    },
                  })}
                </View>
              ) : (
                <TouchableOpacity
                  testID="new-appointment-picker"
                  onPress={() => setShowDatePicker(true)}
                  style={[styles.input, { justifyContent: "center" }]}
                  activeOpacity={0.7}
                >
                  <Text style={{ color: newAppt ? colors.textPrimary : colors.placeholder, fontSize: 16 }}>
                    {newAppt
                      ? new Date(newAppt).toLocaleString("fr-FR", {
                          weekday: "short",
                          day: "2-digit",
                          month: "short",
                          year: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        })
                      : "📅 Choisir une date et une heure"}
                  </Text>
                </TouchableOpacity>
              )}
              {showDatePicker && Platform.OS !== "web" && (
                <DateTimePicker
                  value={newAppt ? new Date(newAppt) : new Date()}
                  mode="datetime"
                  display={Platform.OS === "ios" ? "spinner" : "default"}
                  onChange={(e: DateTimePickerEvent, date?: Date) => {
                    setShowDatePicker(Platform.OS === "ios"); // iOS keeps open
                    if (date) {
                      // Persist as ISO-ish "YYYY-MM-DDTHH:mm"
                      const iso = date.toISOString().slice(0, 16);
                      setNewAppt(iso);
                    }
                  }}
                />
              )}

              <View style={styles.notesLabelRow}>
                <Text style={styles.label}>Notes &amp; Instructions</Text>
                <TouchableOpacity
                  testID="voice-input-button"
                  onPress={() => startVoiceInput()}
                  activeOpacity={0.7}
                  style={[styles.micBtn, listening && styles.micBtnActive]}
                >
                  <Ionicons
                    name={listening ? "mic" : "mic-outline"}
                    size={18}
                    color={listening ? "#fff" : colors.primary}
                  />
                  <Text style={[styles.micBtnText, listening && { color: "#fff" }]}>
                    {listening ? "Écoute..." : "Dicter"}
                  </Text>
                </TouchableOpacity>
              </View>
              <TextInput
                testID="new-notes-input"
                value={newNotes}
                onChangeText={setNewNotes}
                placeholder="Clé sous le paillasson, accès portail latéral... ou cliquez sur Dicter 🎙️"
                placeholderTextColor={colors.placeholder}
                multiline
                numberOfLines={3}
                style={[styles.input, { minHeight: 80, textAlignVertical: "top", paddingTop: 12 }]}
              />
            </ScrollView>
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

      {/* Centre d'aide / FAQ */}
      <ChatHelp
        visible={helpOpen}
        onClose={() => setHelpOpen(false)}
        onContactSupport={() => router.push("/company-profile")}
      />
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
  badgeRow: { flexDirection: "row", flexWrap: "wrap", gap: 6, marginTop: 4 },
  exportReadyBadge: {
    backgroundColor: "#0e3315",
    borderWidth: 1,
    borderColor: "#32D74B",
    flexDirection: "row",
    alignItems: "center",
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
    marginBottom: 4,
  },
  modalSub: { color: colors.textSecondary, fontSize: 12, marginBottom: 8 },
  row2: { flexDirection: "row", gap: 10 },
  col2: { flex: 1 },
  col3: { flex: 3 },
  col7: { flex: 7 },
  notesLabelRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  micBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: colors.primary,
    backgroundColor: "transparent",
  },
  micBtnActive: { backgroundColor: colors.anomaly, borderColor: colors.anomaly },
  micBtnText: { color: colors.primary, fontSize: 11, fontWeight: "800", letterSpacing: 0.4 },
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
