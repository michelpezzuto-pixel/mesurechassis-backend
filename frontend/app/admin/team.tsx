import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Modal,
  Platform,
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
import { api } from "@/src/services/api";
import { useAuth } from "@/src/context/AuthContext";
import { colors } from "@/src/theme";

type Member = {
  id: string;
  name: string;
  email: string;
  role: "admin" | "commercial" | "technician";
  status?: string;
  email_verified_at?: string | null;
};

const ROLE_LABEL: Record<string, string> = {
  admin: "Admin",
  commercial: "Commercial",
  technician: "Technicien",
};

const ROLE_COLOR: Record<string, string> = {
  admin: "#A855F7",
  commercial: "#3B82F6",
  technician: "#22C55E",
};

export default function TeamAdmin() {
  const { user } = useAuth();
  const router = useRouter();
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<"commercial" | "technician">("commercial");
  const [submitting, setSubmitting] = useState(false);
  const [lastInviteLink, setLastInviteLink] = useState<string | null>(null);

  // Garde admin-only
  useEffect(() => {
    if (user && user.role !== "admin") {
      router.replace("/dashboard");
    }
  }, [user, router]);

  const fetchMembers = useCallback(async () => {
    try {
      const res = await api.get<Member[]>("/users");
      setMembers(res.data || []);
    } catch {
      Alert.alert("Erreur", "Impossible de charger l'équipe.");
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      fetchMembers();
    }, [fetchMembers])
  );

  const submitInvite = async () => {
    if (!email.trim() || !name.trim()) {
      Alert.alert("Champs requis", "Nom et email sont obligatoires.");
      return;
    }
    setSubmitting(true);
    setLastInviteLink(null);
    try {
      const res = await api.post("/admin/invitations", {
        name: name.trim(),
        email: email.trim(),
        role,
      });
      setLastInviteLink(res.data?.verification_link ?? null);
      Alert.alert(
        "✅ Invitation envoyée",
        `${email.trim()} recevra un email pour définir son mot de passe.`
      );
      setName("");
      setEmail("");
      await fetchMembers();
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      Alert.alert(
        "Erreur",
        typeof detail === "string"
          ? detail
          : "Invitation impossible."
      );
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <View style={[styles.flex, styles.center]}>
        <ActivityIndicator color={colors.primary} size="large" />
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.flex} edges={["top", "bottom"]}>
      <View style={styles.topBar}>
        <TouchableOpacity onPress={() => router.back()} hitSlop={10}>
          <Ionicons name="arrow-back" size={22} color={colors.textPrimary} />
        </TouchableOpacity>
        <Text style={styles.topTitle}>ÉQUIPE</Text>
        <View style={{ width: 22 }} />
      </View>

      <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 120 }}>
        <TouchableOpacity
          testID="open-invite-modal-button"
          activeOpacity={0.85}
          onPress={() => setModalOpen(true)}
          style={styles.btnPrimary}
        >
          <Ionicons name="person-add" size={20} color="#000" />
          <Text style={styles.btnPrimaryText}>INVITER UN MEMBRE</Text>
        </TouchableOpacity>

        <Text style={styles.sectionTitle}>MEMBRES ({members.length})</Text>

        {members.map((m) => {
          const isPending = (m.status || "active") === "pending_verification";
          return (
            <View key={m.id} style={styles.memberCard}>
              <View
                style={[
                  styles.roleDot,
                  { backgroundColor: ROLE_COLOR[m.role] || colors.primary },
                ]}
              />
              <View style={{ flex: 1 }}>
                <Text style={styles.memberName}>{m.name}</Text>
                <Text style={styles.memberEmail}>{m.email}</Text>
                <View style={styles.memberMeta}>
                  <View
                    style={[
                      styles.roleBadge,
                      { borderColor: ROLE_COLOR[m.role] || colors.primary },
                    ]}
                  >
                    <Text
                      style={[
                        styles.roleBadgeText,
                        { color: ROLE_COLOR[m.role] || colors.primary },
                      ]}
                    >
                      {ROLE_LABEL[m.role] || m.role}
                    </Text>
                  </View>
                  {isPending ? (
                    <View
                      style={[
                        styles.statusBadge,
                        {
                          backgroundColor: "#2a1c08",
                          borderColor: colors.warning,
                        },
                      ]}
                    >
                      <Ionicons
                        name="time-outline"
                        size={11}
                        color={colors.warning}
                      />
                      <Text
                        style={[
                          styles.statusBadgeText,
                          { color: colors.warning },
                        ]}
                      >
                        EN ATTENTE
                      </Text>
                    </View>
                  ) : (
                    <View
                      style={[
                        styles.statusBadge,
                        { backgroundColor: "#0b3b1c", borderColor: "#34d399" },
                      ]}
                    >
                      <Ionicons
                        name="checkmark-circle"
                        size={11}
                        color="#34d399"
                      />
                      <Text
                        style={[styles.statusBadgeText, { color: "#34d399" }]}
                      >
                        VÉRIFIÉ
                      </Text>
                    </View>
                  )}
                </View>
              </View>
            </View>
          );
        })}
      </ScrollView>

      {/* Modal Invitation */}
      <Modal
        visible={modalOpen}
        transparent
        animationType="slide"
        onRequestClose={() => setModalOpen(false)}
      >
        <KeyboardAvoidingView
          behavior={Platform.OS === "ios" ? "padding" : undefined}
          style={styles.modalBackdrop}
        >
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>INVITER UN MEMBRE</Text>
            <Text style={styles.modalSub}>
              Un email avec un lien d'activation sera envoyé.
            </Text>

            <Text style={styles.label}>Nom complet</Text>
            <TextInput
              testID="invite-form-name"
              value={name}
              onChangeText={setName}
              placeholder="ex. Sophie Martin"
              placeholderTextColor={colors.placeholder}
              style={styles.input}
            />

            <Text style={styles.label}>Email professionnel</Text>
            <TextInput
              testID="invite-form-email"
              value={email}
              onChangeText={setEmail}
              placeholder="prenom.nom@entreprise.fr"
              placeholderTextColor={colors.placeholder}
              keyboardType="email-address"
              autoCapitalize="none"
              style={styles.input}
            />

            <Text style={styles.label}>Rôle</Text>
            <View style={styles.roleRow}>
              {(["commercial", "technician"] as const).map((r) => (
                <TouchableOpacity
                  key={r}
                  testID={`invite-role-${r}`}
                  onPress={() => setRole(r)}
                  activeOpacity={0.85}
                  style={[
                    styles.roleCard,
                    role === r && {
                      backgroundColor: "rgba(255,90,0,0.1)",
                      borderColor: colors.primary,
                    },
                  ]}
                >
                  <Ionicons
                    name={r === "commercial" ? "briefcase" : "construct"}
                    size={20}
                    color={role === r ? colors.primary : colors.textSecondary}
                  />
                  <Text
                    style={[
                      styles.roleCardLabel,
                      role === r && { color: colors.primary },
                    ]}
                  >
                    {ROLE_LABEL[r]}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            {lastInviteLink && (
              <View style={styles.devLinkBox}>
                <Text style={styles.devLinkLabel}>
                  🔧 DÉMO — Lien d'invitation (mode dev) :
                </Text>
                <Text
                  testID="last-invitation-link"
                  selectable
                  style={styles.devLinkValue}
                >
                  {lastInviteLink}
                </Text>
              </View>
            )}

            <View style={styles.modalActions}>
              <TouchableOpacity
                onPress={() => {
                  setModalOpen(false);
                  setLastInviteLink(null);
                }}
                activeOpacity={0.85}
                style={[styles.btn, styles.btnGhost, { flex: 1 }]}
              >
                <Text style={styles.btnGhostText}>FERMER</Text>
              </TouchableOpacity>
              <TouchableOpacity
                testID="invite-form-submit"
                onPress={submitInvite}
                disabled={submitting}
                activeOpacity={0.85}
                style={[styles.btn, styles.btnPrimaryModal, { flex: 1.4 }]}
              >
                {submitting ? (
                  <ActivityIndicator color="#000" />
                ) : (
                  <>
                    <Ionicons name="mail" size={16} color="#000" />
                    <Text style={styles.btnPrimaryText}>ENVOYER</Text>
                  </>
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
  flex: { flex: 1, backgroundColor: colors.bg },
  center: { alignItems: "center", justifyContent: "center" },
  topBar: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSubtle,
  },
  topTitle: {
    color: colors.textPrimary,
    fontWeight: "900",
    letterSpacing: 1.2,
    fontSize: 13,
  },
  sectionTitle: {
    color: colors.textSecondary,
    fontSize: 11,
    letterSpacing: 1.5,
    fontWeight: "800",
    marginTop: 22,
    marginBottom: 10,
  },
  btnPrimary: {
    backgroundColor: colors.primary,
    minHeight: 52,
    borderRadius: 12,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
    paddingHorizontal: 14,
  },
  btnPrimaryModal: {
    backgroundColor: colors.primary,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
  },
  btnPrimaryText: {
    color: "#000",
    fontWeight: "900",
    letterSpacing: 1,
  },
  memberCard: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    backgroundColor: colors.surface,
    borderColor: colors.borderSubtle,
    borderWidth: 1,
    borderRadius: 10,
    padding: 12,
    marginBottom: 8,
  },
  roleDot: {
    width: 8,
    height: 36,
    borderRadius: 4,
    alignSelf: "flex-start",
    marginTop: 4,
  },
  memberName: { color: colors.textPrimary, fontWeight: "800", fontSize: 14 },
  memberEmail: { color: colors.textSecondary, fontSize: 12, marginTop: 2 },
  memberMeta: { flexDirection: "row", gap: 8, marginTop: 8 },
  roleBadge: {
    borderWidth: 1,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 5,
  },
  roleBadgeText: { fontSize: 10, fontWeight: "900", letterSpacing: 0.6 },
  statusBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 5,
    borderWidth: 1,
  },
  statusBadgeText: { fontSize: 10, fontWeight: "900", letterSpacing: 0.6 },
  modalBackdrop: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.7)",
    justifyContent: "flex-end",
  },
  modalCard: {
    backgroundColor: colors.bg,
    padding: 20,
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
    borderTopWidth: 1,
    borderColor: colors.borderStrong,
  },
  modalTitle: {
    color: colors.textPrimary,
    fontWeight: "900",
    fontSize: 15,
    letterSpacing: 1,
    marginBottom: 4,
  },
  modalSub: { color: colors.textSecondary, fontSize: 12, marginBottom: 14 },
  label: {
    color: colors.textSecondary,
    fontSize: 11,
    fontWeight: "700",
    letterSpacing: 0.6,
    marginBottom: 6,
    marginTop: 6,
  },
  input: {
    backgroundColor: colors.surface,
    color: colors.textPrimary,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.borderStrong,
    paddingHorizontal: 12,
    paddingVertical: Platform.OS === "ios" ? 13 : 9,
    fontSize: 15,
    minHeight: 46,
  },
  roleRow: { flexDirection: "row", gap: 10, marginBottom: 4 },
  roleCard: {
    flex: 1,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderStrong,
    borderRadius: 10,
    padding: 12,
    alignItems: "center",
    gap: 4,
  },
  roleCardLabel: {
    color: colors.textPrimary,
    fontWeight: "800",
    fontSize: 12,
  },
  devLinkBox: {
    backgroundColor: colors.surface,
    borderColor: colors.borderStrong,
    borderWidth: 1,
    borderRadius: 8,
    padding: 12,
    marginTop: 14,
  },
  devLinkLabel: {
    color: colors.warning,
    fontWeight: "800",
    fontSize: 10,
    letterSpacing: 0.6,
    marginBottom: 6,
  },
  devLinkValue: {
    color: colors.textPrimary,
    fontSize: 10,
    fontFamily: Platform.select({
      ios: "Menlo",
      android: "monospace",
      default: "monospace",
    }),
  },
  modalActions: { flexDirection: "row", gap: 10, marginTop: 18 },
  btn: {
    minHeight: 50,
    borderRadius: 12,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    paddingHorizontal: 14,
  },
  btnGhost: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderStrong,
  },
  btnGhostText: {
    color: colors.textPrimary,
    fontWeight: "800",
    fontSize: 13,
    letterSpacing: 0.8,
  },
});
