import React, { useCallback, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Modal,
  Platform,
  ScrollView,
  StyleSheet,
  Switch,
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

type Plan = "free" | "trial" | "pro";

type Profile = {
  company_id: string;
  name?: string;
  artisan_mode?: boolean;
  subscription_status?: string;
  subscription_expires_at?: string | null;
  plan?: Plan;
  chantiers_lifetime_count?: number;
  cancel_at_period_end?: boolean;
  cancelled_at?: string | null;
};

const FREE_LIMIT = 3;

function formatDate(iso?: string | null): string {
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

function planMeta(plan: Plan | undefined): { label: string; bg: string; fg: string } {
  switch (plan) {
    case "pro":
      return { label: "PRO", bg: "#0b3b1c", fg: "#34d399" };
    case "free":
      return { label: "FREE", bg: "#3a1010", fg: colors.anomaly };
    default:
      return { label: "ESSAI", bg: "#2a1c08", fg: colors.warning };
  }
}

export default function CompanyProfile() {
  const router = useRouter();
  const { user, company, refreshCompany } = useAuth();
  const [name, setName] = useState("");
  const [artisanMode, setArtisanMode] = useState(false);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [cancelling, setCancelling] = useState(false);

  const fetchProfile = useCallback(async () => {
    try {
      const res = await api.get<Profile>("/company/profile");
      setName(res.data?.name ?? "");
      setArtisanMode(!!res.data?.artisan_mode);
      setProfile(res.data);
    } catch {
      Alert.alert("Erreur", "Impossible de charger le profil société.");
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      fetchProfile();
    }, [fetchProfile])
  );

  const save = async () => {
    setSaving(true);
    try {
      await api.patch("/company/profile", {
        name: name.trim() || null,
        artisan_mode: artisanMode,
      });
      await refreshCompany();
      await fetchProfile();
      Alert.alert(
        "✅ Profil société mis à jour",
        artisanMode
          ? "Mode Artisan Unique activé — vous avez désormais accès à toutes les fonctionnalités."
          : "Mode Artisan Unique désactivé."
      );
    } catch (e: any) {
      const msg =
        e?.response?.status === 403
          ? "Réservé à l'administrateur de la société."
          : "Enregistrement impossible.";
      Alert.alert("Erreur", msg);
    } finally {
      setSaving(false);
    }
  };

  const doCancel = async () => {
    setCancelling(true);
    try {
      const res = await api.post<Profile>("/company/subscription/cancel");
      setProfile(res.data);
      await refreshCompany();
      setConfirmOpen(false);
      Alert.alert(
        "Annulation programmée",
        `Votre accès Pro reste actif jusqu'au ${formatDate(
          res.data.subscription_expires_at
        )}. Après cette date, l'écran de verrouillage s'activera automatiquement.`
      );
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      const msg =
        typeof detail === "string"
          ? detail
          : e?.response?.status === 403
            ? "Seul l'administrateur peut annuler l'abonnement."
            : "Annulation impossible.";
      Alert.alert("Erreur", msg);
    } finally {
      setCancelling(false);
    }
  };

  const doReactivate = async () => {
    setCancelling(true);
    try {
      const res = await api.post<Profile>("/company/subscription/reactivate");
      setProfile(res.data);
      await refreshCompany();
      Alert.alert("✅ Abonnement réactivé", "L'annulation a été annulée.");
    } catch {
      Alert.alert("Erreur", "Réactivation impossible.");
    } finally {
      setCancelling(false);
    }
  };

  if (loading) {
    return (
      <View style={[styles.flex, styles.center]}>
        <ActivityIndicator color={colors.primary} size="large" />
      </View>
    );
  }

  const isAdmin = user?.role === "admin";
  const plan = (profile?.plan ?? "trial") as Plan;
  const meta = planMeta(plan);
  const used = profile?.chantiers_lifetime_count ?? 0;
  const cancelScheduled = !!profile?.cancel_at_period_end;
  const expiresLabel = formatDate(profile?.subscription_expires_at);
  // Le bouton "Se désabonner" est dispo : admin + accès actif (trial ou pro) + pas déjà annulé
  const canUnsubscribe =
    isAdmin &&
    !cancelScheduled &&
    profile?.subscription_status !== "suspended" &&
    (plan === "pro" || plan === "trial" || profile?.subscription_status === "active");
  // Pour Free : afficher l'usage des chantiers
  const isFree = plan === "free";
  const remaining = Math.max(0, FREE_LIMIT - used);
  const overLimit = isFree && used >= FREE_LIMIT;

  return (
    <SafeAreaView style={styles.flex} edges={["top", "bottom"]}>
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        style={styles.flex}
      >
        <View style={styles.topBar}>
          <TouchableOpacity onPress={() => router.back()} hitSlop={10}>
            <Ionicons name="arrow-back" size={22} color={colors.textPrimary} />
          </TouchableOpacity>
          <Text style={styles.topTitle}>PROFIL SOCIÉTÉ</Text>
          <View style={{ width: 22 }} />
        </View>

        <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 120 }}>
          {/* === BLOC ABONNEMENT === */}
          <View style={styles.card}>
            <View style={styles.rowBetween}>
              <Text style={styles.section}>ABONNEMENT & FACTURATION</Text>
              <View
                style={[
                  styles.planBadge,
                  { backgroundColor: meta.bg, borderColor: meta.fg },
                ]}
              >
                <Text style={[styles.planBadgeText, { color: meta.fg }]}>
                  {meta.label}
                </Text>
              </View>
            </View>

            <View style={styles.kvRow}>
              <Text style={styles.kvLabel}>Statut</Text>
              <Text style={styles.kvValue}>
                {profile?.subscription_status?.toUpperCase() ?? "—"}
              </Text>
            </View>
            <View style={styles.kvRow}>
              <Text style={styles.kvLabel}>
                {cancelScheduled ? "Accès Pro jusqu'au" : "Expiration"}
              </Text>
              <Text style={styles.kvValue}>{expiresLabel}</Text>
            </View>

            {isFree && (
              <View style={styles.freeUsageBox}>
                <View style={styles.row}>
                  <Ionicons
                    name={overLimit ? "lock-closed" : "alert-circle"}
                    size={18}
                    color={overLimit ? colors.anomaly : colors.warning}
                  />
                  <Text style={styles.freeUsageTitle}>
                    Plan Freemium — {used}/{FREE_LIMIT} chantiers utilisés
                  </Text>
                </View>
                <Text style={styles.freeUsageBody}>
                  {overLimit
                    ? "Limite atteinte. Les exports (PDF/Excel/CSV/JSON) sont verrouillés. " +
                      "Supprimer un chantier ne réinitialise PAS le compteur (anti-fraude). " +
                      "Passez en Pro pour débloquer."
                    : `Il vous reste ${remaining} chantier(s) avant la limite Freemium. ` +
                      `Les exports techniques sont déjà verrouillés sur ce plan.`}
                </Text>
              </View>
            )}

            {cancelScheduled && (
              <View style={styles.cancelBox}>
                <View style={styles.row}>
                  <Ionicons name="time-outline" size={18} color={colors.warning} />
                  <Text style={styles.cancelBoxTitle}>
                    Annulation programmée
                  </Text>
                </View>
                <Text style={styles.cancelBoxBody}>
                  Votre accès Pro reste actif jusqu'au{" "}
                  <Text style={styles.bold}>{expiresLabel}</Text>. À cette date,
                  l'écran de verrouillage plein-écran sera activé automatiquement.
                </Text>
                {isAdmin && (
                  <TouchableOpacity
                    testID="reactivate-subscription-button"
                    onPress={doReactivate}
                    disabled={cancelling}
                    activeOpacity={0.85}
                    style={[styles.btn, styles.btnGhost, { marginTop: 12 }]}
                  >
                    {cancelling ? (
                      <ActivityIndicator color={colors.textPrimary} />
                    ) : (
                      <>
                        <Ionicons
                          name="refresh"
                          size={18}
                          color={colors.textPrimary}
                        />
                        <Text style={styles.btnGhostText}>
                          RÉACTIVER L'ABONNEMENT
                        </Text>
                      </>
                    )}
                  </TouchableOpacity>
                )}
              </View>
            )}

            {canUnsubscribe && (
              <TouchableOpacity
                testID="unsubscribe-button"
                onPress={() => setConfirmOpen(true)}
                disabled={cancelling}
                activeOpacity={0.85}
                style={[styles.btn, styles.btnDanger, { marginTop: 14 }]}
              >
                <Ionicons name="close-circle" size={20} color="#fff" />
                <Text style={styles.btnDangerText}>SE DÉSABONNER</Text>
              </TouchableOpacity>
            )}

            {!isAdmin && (
              <Text style={styles.warnNote}>
                ⚠ Seul l'administrateur principal peut gérer la facturation.
              </Text>
            )}
          </View>

          {/* === IDENTITÉ === */}
          <View style={styles.card}>
            <Text style={styles.section}>IDENTITÉ</Text>
            <Text style={styles.label}>ID Société</Text>
            <View style={styles.badge}>
              <Ionicons
                name="business-outline"
                size={14}
                color={colors.textSecondary}
              />
              <Text style={styles.badgeText}>
                {company?.company_id ?? "default"}
              </Text>
            </View>

            <Text style={[styles.label, { marginTop: 16 }]}>Nom commercial</Text>
            <TextInput
              testID="company-name-input"
              value={name}
              onChangeText={setName}
              placeholder="Ex. Menuiserie Dupont SARL"
              placeholderTextColor={colors.placeholder}
              editable={isAdmin}
              style={[styles.input, !isAdmin && { opacity: 0.6 }]}
            />
          </View>

          {/* === ARTISAN MODE === */}
          <View style={styles.card}>
            <Text style={styles.section}>MODE ARTISAN UNIQUE</Text>
            <Text style={styles.help}>
              Activez ce mode si vous êtes{" "}
              <Text style={styles.bold}>seul à utiliser l'application</Text>{" "}
              (artisan indépendant). Vous accéderez instantanément à{" "}
              <Text style={styles.bold}>toutes les fonctionnalités</Text> sans
              restriction de rôle.
            </Text>

            <View style={styles.toggleRow}>
              <View style={{ flex: 1 }}>
                <Text style={styles.toggleLabel}>Activer le mode artisan</Text>
                <Text style={styles.toggleSub}>
                  {artisanMode ? "✅ Accès total" : "⛔ Restrictions par rôle"}
                </Text>
              </View>
              <Switch
                testID="artisan-mode-switch"
                value={artisanMode}
                onValueChange={setArtisanMode}
                disabled={!isAdmin}
                trackColor={{ false: colors.borderStrong, true: colors.primary }}
                thumbColor={artisanMode ? "#fff" : "#f4f3f4"}
              />
            </View>

            {!isAdmin && (
              <Text style={styles.warnNote}>
                ⚠ Seul l'administrateur de la société peut modifier ce paramètre.
              </Text>
            )}
          </View>

          {isAdmin && (
            <TouchableOpacity
              testID="company-save-button"
              onPress={save}
              disabled={saving}
              activeOpacity={0.85}
              style={[styles.btn, styles.btnPrimary]}
            >
              {saving ? (
                <ActivityIndicator color="#000" />
              ) : (
                <>
                  <Ionicons name="checkmark-circle" size={22} color="#000" />
                  <Text style={styles.btnPrimaryText}>ENREGISTRER</Text>
                </>
              )}
            </TouchableOpacity>
          )}
        </ScrollView>

        {/* === Modal Confirmation Désabonnement === */}
        <Modal
          visible={confirmOpen}
          transparent
          animationType="fade"
          onRequestClose={() => setConfirmOpen(false)}
        >
          <View style={styles.modalBackdrop}>
            <View style={styles.modalCard}>
              <View style={styles.modalIconWrap}>
                <Ionicons
                  name="warning"
                  size={36}
                  color={colors.warning}
                />
              </View>
              <Text style={styles.modalTitle}>CONFIRMER LE DÉSABONNEMENT</Text>
              <Text style={styles.modalBody}>
                Votre accès Pro restera actif jusqu'au{" "}
                <Text style={styles.bold}>{expiresLabel}</Text>.
                {"\n\n"}
                Après cette date, l'écran de verrouillage plein-écran sera
                activé automatiquement. Vous pourrez réactiver l'abonnement à
                tout moment avant l'expiration.
              </Text>
              <View style={styles.modalActions}>
                <TouchableOpacity
                  testID="cancel-unsubscribe-button"
                  onPress={() => setConfirmOpen(false)}
                  disabled={cancelling}
                  activeOpacity={0.85}
                  style={[styles.btn, styles.btnGhost, { flex: 1 }]}
                >
                  <Text style={styles.btnGhostText}>ANNULER</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  testID="confirm-unsubscribe-button"
                  onPress={doCancel}
                  disabled={cancelling}
                  activeOpacity={0.85}
                  style={[styles.btn, styles.btnDanger, { flex: 1 }]}
                >
                  {cancelling ? (
                    <ActivityIndicator color="#fff" />
                  ) : (
                    <Text style={styles.btnDangerText}>CONFIRMER</Text>
                  )}
                </TouchableOpacity>
              </View>
            </View>
          </View>
        </Modal>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: colors.bg },
  center: { alignItems: "center", justifyContent: "center" },
  row: { flexDirection: "row", alignItems: "center", gap: 8 },
  rowBetween: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 8,
  },
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
  card: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    borderColor: colors.borderSubtle,
    borderWidth: 1,
    padding: 16,
    marginBottom: 14,
  },
  section: {
    color: colors.textSecondary,
    fontSize: 11,
    letterSpacing: 1.5,
    fontWeight: "800",
  },
  label: {
    color: colors.textSecondary,
    fontSize: 11,
    fontWeight: "700",
    letterSpacing: 0.6,
    marginBottom: 6,
  },
  input: {
    backgroundColor: colors.inputBg,
    color: colors.textPrimary,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.borderStrong,
    paddingHorizontal: 12,
    paddingVertical: Platform.OS === "ios" ? 14 : 10,
    fontSize: 16,
    minHeight: 48,
  },
  badge: {
    alignSelf: "flex-start",
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    backgroundColor: colors.bg,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
  },
  badgeText: { color: colors.textPrimary, fontWeight: "700", fontSize: 12 },
  help: { color: colors.textSecondary, fontSize: 13, lineHeight: 19 },
  bold: { color: colors.textPrimary, fontWeight: "800" },
  toggleRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    marginTop: 14,
    paddingTop: 14,
    borderTopWidth: 1,
    borderTopColor: colors.borderSubtle,
  },
  toggleLabel: { color: colors.textPrimary, fontWeight: "800", fontSize: 14 },
  toggleSub: { color: colors.textSecondary, fontSize: 12, marginTop: 2 },
  warnNote: {
    color: colors.warning,
    fontSize: 12,
    marginTop: 10,
    fontWeight: "700",
  },
  btn: {
    minHeight: 52,
    borderRadius: 12,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    paddingHorizontal: 14,
  },
  btnPrimary: { backgroundColor: colors.primary },
  btnPrimaryText: { color: "#000", fontWeight: "900", letterSpacing: 1 },
  btnDanger: { backgroundColor: colors.anomaly },
  btnDangerText: {
    color: "#fff",
    fontWeight: "900",
    letterSpacing: 1,
    fontSize: 13,
  },
  btnGhost: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderStrong,
  },
  btnGhostText: {
    color: colors.textPrimary,
    fontWeight: "800",
    letterSpacing: 0.8,
    fontSize: 13,
  },
  planBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 6,
    borderWidth: 1,
  },
  planBadgeText: { fontSize: 11, fontWeight: "900", letterSpacing: 1 },
  kvRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 8,
    borderTopWidth: 1,
    borderTopColor: colors.borderSubtle,
  },
  kvLabel: { color: colors.textSecondary, fontSize: 12 },
  kvValue: { color: colors.textPrimary, fontSize: 13, fontWeight: "700" },
  freeUsageBox: {
    backgroundColor: "#1f0a0a",
    borderColor: colors.anomaly,
    borderWidth: 1,
    borderRadius: 10,
    padding: 12,
    marginTop: 12,
  },
  freeUsageTitle: {
    color: colors.anomaly,
    fontWeight: "900",
    fontSize: 13,
    letterSpacing: 0.5,
  },
  freeUsageBody: {
    color: colors.textPrimary,
    fontSize: 12,
    lineHeight: 17,
    marginTop: 6,
  },
  cancelBox: {
    backgroundColor: "#2a1c08",
    borderColor: colors.warning,
    borderWidth: 1,
    borderRadius: 10,
    padding: 12,
    marginTop: 12,
  },
  cancelBoxTitle: {
    color: colors.warning,
    fontWeight: "900",
    fontSize: 13,
    letterSpacing: 0.5,
  },
  cancelBoxBody: {
    color: colors.textPrimary,
    fontSize: 12,
    lineHeight: 17,
    marginTop: 6,
  },
  modalBackdrop: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.75)",
    alignItems: "center",
    justifyContent: "center",
    padding: 20,
  },
  modalCard: {
    backgroundColor: colors.surface,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: colors.borderStrong,
    padding: 22,
    width: "100%",
    maxWidth: 460,
  },
  modalIconWrap: { alignItems: "center", marginBottom: 12 },
  modalTitle: {
    color: colors.textPrimary,
    fontWeight: "900",
    fontSize: 15,
    letterSpacing: 1,
    textAlign: "center",
    marginBottom: 10,
  },
  modalBody: {
    color: colors.textSecondary,
    fontSize: 13,
    lineHeight: 19,
    textAlign: "center",
  },
  modalActions: { flexDirection: "row", gap: 10, marginTop: 18 },
});
