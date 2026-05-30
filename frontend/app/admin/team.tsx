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
  const { user, company } = useAuth();
  const router = useRouter();
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<"commercial" | "technician">("commercial");
  // A3 — Mot de passe attribué directement par l'Admin
  const [memberPassword, setMemberPassword] = useState("");
  const [showMemberPassword, setShowMemberPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [lastInviteLink, setLastInviteLink] = useState<string | null>(null);

  // Garde admin-only + Artisan (compte solo, pas d'équipe possible)
  useEffect(() => {
    if (user && user.role !== "admin") {
      router.replace("/dashboard");
    } else if (company?.account_type === "artisan") {
      // Lot D — un Artisan n'a pas d'équipe à gérer.
      Alert.alert(
        "Compte Artisan",
        "Les comptes Artisan sont limités à un seul utilisateur. Pour inviter des collaborateurs, passez à un compte Entreprise.",
      );
      router.replace("/dashboard");
    }
  }, [user, company, router]);

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

  const [extraSeatInfo, setExtraSeatInfo] = useState<null | {
    next_seat_index: number;
    extra_seats_total: number;
    seat_price_eur: number;
    extra_amount_eur: number;
    free_seats: number;
    seats_used: number;
    message?: string;
  }>(null);

  /** A3 — Création directe d'un membre par l'Admin (nom + email +
   *  mot de passe). L'invitation par email est remplacée par cet appel
   *  direct car les emails Hotmail/Outlook étaient peu fiables.
   *  L'Admin transmet manuellement les identifiants au collaborateur.
   */
  const doInvite = useCallback(
    async (confirmExtraSeat: boolean) => {
      setSubmitting(true);
      setLastInviteLink(null);
      try {
        // Vérif locale du mot de passe
        if (!memberPassword || memberPassword.length < 6) {
          Alert.alert("Mot de passe trop court", "6 caractères minimum.");
          setSubmitting(false);
          return;
        }
        const res = await api.post("/team/members", {
          name: name.trim(),
          email: email.trim(),
          password: memberPassword,
          role,
          confirm_extra_seat: confirmExtraSeat,
        });
        setExtraSeatInfo(null);
        Alert.alert(
          "✅ Collaborateur créé",
          `Identifiants à transmettre à ${name.trim()} :\n\n` +
          `📧 Email : ${email.trim()}\n` +
          `🔐 Mot de passe : ${memberPassword}\n\n` +
          `(Communiquez ces identifiants par SMS / WhatsApp / papier — l'application n'envoie PAS d'email.)`,
        );
        setName("");
        setEmail("");
        setMemberPassword("");
        await fetchMembers();
      } catch (e: any) {
        const status = e?.response?.status;
        const detail = e?.response?.data?.detail;
        if (
          status === 402 &&
          typeof detail === "object" &&
          detail?.code === "EXTRA_SEAT_REQUIRED"
        ) {
          setExtraSeatInfo(detail);
          return;
        }
        Alert.alert(
          "Erreur",
          typeof detail === "string" ? detail : "Invitation impossible.",
        );
      } finally {
        setSubmitting(false);
      }
    },
    [name, email, role, fetchMembers],
  );

  const submitInvite = async () => {
    if (!email.trim() || !name.trim()) {
      Alert.alert("Champs requis", "Nom et email sont obligatoires.");
      return;
    }
    // 1er appel : confirm_extra_seat=false (le backend décide s'il faut afficher la popup)
    await doInvite(false);
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

      {/* Modal Invitation — scrollable + keyboard-safe */}
      <Modal
        visible={modalOpen}
        transparent
        animationType="slide"
        onRequestClose={() => setModalOpen(false)}
      >
        <KeyboardAvoidingView
          behavior={Platform.OS === "ios" ? "padding" : "height"}
          keyboardVerticalOffset={Platform.OS === "ios" ? 0 : 20}
          style={styles.modalBackdrop}
        >
          <View style={styles.modalCard}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>INVITER UN MEMBRE</Text>
              <TouchableOpacity
                onPress={() => {
                  setModalOpen(false);
                  setLastInviteLink(null);
                }}
                hitSlop={12}
                activeOpacity={0.7}
              >
                <Ionicons
                  name="close"
                  size={26}
                  color={colors.textSecondary}
                />
              </TouchableOpacity>
            </View>
            <Text style={styles.modalSub}>
              Le compte sera créé directement. Vous transmettrez les
              identifiants par SMS/WhatsApp.
            </Text>

            <ScrollView
              style={{ maxHeight: 460 }}
              contentContainerStyle={{ paddingBottom: 8 }}
              keyboardShouldPersistTaps="handled"
              showsVerticalScrollIndicator
            >
              <Text style={styles.label}>Nom complet</Text>
              <TextInput
                testID="invite-form-name"
                value={name}
                onChangeText={setName}
                placeholder="ex. Sophie Martin"
                placeholderTextColor={colors.placeholder}
                returnKeyType="next"
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
                autoCorrect={false}
                returnKeyType="next"
                style={styles.input}
              />

              <Text style={styles.label}>
                Mot de passe (vous le transmettrez)
              </Text>
              <View style={styles.passwordWrap}>
                <TextInput
                  testID="invite-form-password"
                  value={memberPassword}
                  onChangeText={setMemberPassword}
                  placeholder="Min. 6 caractères"
                  placeholderTextColor={colors.placeholder}
                  secureTextEntry={!showMemberPassword}
                  autoCapitalize="none"
                  autoCorrect={false}
                  returnKeyType="done"
                  style={styles.passwordInput}
                />
                <TouchableOpacity
                  onPress={() => setShowMemberPassword((v) => !v)}
                  style={styles.eyeBtn}
                  activeOpacity={0.6}
                >
                  <Ionicons
                    name={
                      showMemberPassword ? "eye-off-outline" : "eye-outline"
                    }
                    size={22}
                    color={colors.textSecondary}
                  />
                </TouchableOpacity>
              </View>
              <Text style={styles.hintText}>
                💡 Vous transmettrez ces identifiants à votre collaborateur
                par SMS ou WhatsApp.
              </Text>

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
                      color={
                        role === r ? colors.primary : colors.textSecondary
                      }
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
            </ScrollView>

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
                    <Ionicons
                      name="checkmark-circle"
                      size={16}
                      color="#000"
                    />
                    <Text style={styles.btnPrimaryText}>CRÉER LE COMPTE</Text>
                  </>
                )}
              </TouchableOpacity>
            </View>
          </View>
        </KeyboardAvoidingView>
      </Modal>

      {/* === Modal supplément de siège (HTTP 402 EXTRA_SEAT_REQUIRED) === */}
      <Modal
        visible={!!extraSeatInfo}
        transparent
        animationType="fade"
        onRequestClose={() => setExtraSeatInfo(null)}
      >
        <View style={styles.extraBackdrop}>
          <View style={styles.extraCard}>
            <View style={styles.extraIconWrap}>
              <Ionicons name="card" size={28} color="#000" />
            </View>
            <Text style={styles.extraTitle}>SUPPLÉMENT UTILISATEUR</Text>
            <Text style={styles.extraDesc}>
              Votre forfait{" "}
              <Text style={styles.extraBold}>Entreprise (54,99 €/mois)</Text>{" "}
              comprend{" "}
              <Text style={styles.extraBold}>
                {extraSeatInfo?.free_seats ?? 2} sièges gratuits
              </Text>{" "}
              (1 commercial + 1 technicien). Cet ajout sera votre{" "}
              <Text style={styles.extraBold}>
                {extraSeatInfo?.next_seat_index ?? "?"}
                {(extraSeatInfo?.next_seat_index ?? 0) === 1 ? "er" : "ème"}
              </Text>{" "}
              utilisateur.
            </Text>
            <View style={styles.extraPriceBox}>
              <Text style={styles.extraPriceLabel}>SUPPLÉMENT MENSUEL</Text>
              <Text style={styles.extraPriceValue}>
                +{(extraSeatInfo?.seat_price_eur ?? 4.99).toFixed(2)} € /mois
              </Text>
              {extraSeatInfo &&
                extraSeatInfo.extra_seats_total > 1 && (
                  <Text style={styles.extraPriceSub}>
                    Total sièges payants après ajout :{" "}
                    {extraSeatInfo.extra_seats_total} (
                    {extraSeatInfo.extra_amount_eur.toFixed(2)} €/mois)
                  </Text>
                )}
            </View>
            <Text style={styles.extraFine}>
              La facturation prendra effet lors de l'activation par
              l'utilisateur invité. Vous pouvez retirer un utilisateur à
              tout moment pour ajuster votre facture.
            </Text>
            <View style={styles.extraActions}>
              <TouchableOpacity
                testID="extra-seat-cancel"
                onPress={() => setExtraSeatInfo(null)}
                style={[styles.extraBtn, styles.extraBtnGhost]}
                activeOpacity={0.85}
              >
                <Text style={styles.extraBtnGhostText}>ANNULER</Text>
              </TouchableOpacity>
              <TouchableOpacity
                testID="extra-seat-confirm"
                onPress={() => doInvite(true)}
                disabled={submitting}
                style={[
                  styles.extraBtn,
                  styles.extraBtnPrimary,
                  submitting && { opacity: 0.6 },
                ]}
                activeOpacity={0.85}
              >
                {submitting ? (
                  <ActivityIndicator color="#000" />
                ) : (
                  <>
                    <Ionicons name="checkmark-circle" size={16} color="#000" />
                    <Text style={styles.extraBtnPrimaryText}>
                      CONFIRMER ET INVITER
                    </Text>
                  </>
                )}
              </TouchableOpacity>
            </View>
          </View>
        </View>
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
  modalHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
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
  passwordWrap: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.surface,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.borderStrong,
    paddingHorizontal: 12,
    minHeight: 46,
  },
  passwordInput: {
    flex: 1,
    color: colors.textPrimary,
    fontSize: 15,
    paddingVertical: Platform.OS === "ios" ? 13 : 9,
  },
  eyeBtn: {
    paddingHorizontal: 6,
    paddingVertical: 6,
    minHeight: 40,
    minWidth: 40,
    justifyContent: "center",
    alignItems: "center",
  },
  hintText: {
    color: colors.textSecondary,
    fontSize: 12,
    marginTop: 4,
    marginBottom: 6,
    fontStyle: "italic",
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
  // === Modal supplément (HTTP 402 EXTRA_SEAT_REQUIRED) ===
  extraBackdrop: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.7)",
    alignItems: "center",
    justifyContent: "center",
    padding: 20,
  },
  extraCard: {
    width: "100%",
    maxWidth: 420,
    backgroundColor: colors.surface,
    borderRadius: 16,
    padding: 22,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    alignItems: "center",
  },
  extraIconWrap: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 12,
  },
  extraTitle: {
    color: colors.textPrimary,
    fontSize: 14,
    fontWeight: "900",
    letterSpacing: 1.2,
    marginBottom: 10,
    textAlign: "center",
  },
  extraDesc: {
    color: colors.textSecondary,
    fontSize: 13,
    lineHeight: 19,
    textAlign: "center",
    marginBottom: 14,
  },
  extraBold: { color: colors.textPrimary, fontWeight: "800" },
  extraPriceBox: {
    width: "100%",
    backgroundColor: "rgba(255, 107, 26, 0.12)",
    borderColor: colors.primary,
    borderWidth: 1.5,
    borderRadius: 12,
    paddingVertical: 14,
    paddingHorizontal: 16,
    alignItems: "center",
    marginBottom: 12,
  },
  extraPriceLabel: {
    color: colors.primary,
    fontSize: 10,
    fontWeight: "900",
    letterSpacing: 1.5,
  },
  extraPriceValue: {
    color: colors.textPrimary,
    fontSize: 24,
    fontWeight: "900",
    marginTop: 4,
    letterSpacing: 0.4,
  },
  extraPriceSub: {
    color: colors.textSecondary,
    fontSize: 11,
    marginTop: 6,
    textAlign: "center",
  },
  extraFine: {
    color: colors.textSecondary,
    fontSize: 11,
    lineHeight: 16,
    textAlign: "center",
    marginBottom: 16,
    fontStyle: "italic",
  },
  extraActions: {
    flexDirection: "row",
    gap: 10,
    width: "100%",
  },
  extraBtn: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    paddingVertical: 13,
    borderRadius: 10,
  },
  extraBtnGhost: {
    borderWidth: 1,
    borderColor: colors.borderStrong,
    backgroundColor: "transparent",
  },
  extraBtnGhostText: {
    color: colors.textPrimary,
    fontWeight: "800",
    letterSpacing: 0.6,
    fontSize: 12,
  },
  extraBtnPrimary: {
    backgroundColor: colors.primary,
  },
  extraBtnPrimaryText: {
    color: "#000",
    fontWeight: "900",
    letterSpacing: 0.6,
    fontSize: 12,
  },
});
