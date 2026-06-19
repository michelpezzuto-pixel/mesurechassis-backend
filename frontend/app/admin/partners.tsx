/**
 * Dashboard admin "Partenaires Affiliés".
 *
 * Permet à un administrateur de :
 *   • Créer un nouveau partenaire (modal)
 *   • Voir la liste complète + stats par partenaire (clics, signups, conversions, commission due)
 *   • Mettre à jour le statut (active/paused/terminated)
 *   • Marquer un contrat signé
 *   • Télécharger le contrat PDF prêt à signer
 *
 * 🔒 Accès limité au rôle admin/owner (check côté backend).
 */
import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import { api } from "@/src/services/api";
import { colors } from "@/src/theme";

type Partner = {
  id: string;
  name: string;
  email: string;
  platform: string;
  handle: string;
  audience_size: number;
  code: string;
  commission_rate: number;
  commission_duration_months: number;
  status: "pending" | "active" | "paused" | "terminated";
  contract_signed: boolean;
  contract_signed_at?: string | null;
  notes?: string;
  created_at: string;
};

type Summary = {
  total_partners: number;
  active: number;
  pending: number;
  total_clicks: number;
  total_signups: number;
  total_conversions: number;
  total_commission_due_eur: number;
  total_commission_paid_eur: number;
};

type Stats = {
  clicks: number;
  signups: number;
  conversions: number;
  click_to_signup_rate_pct: number;
  signup_to_paid_rate_pct: number;
  total_commission_due_eur: number;
};

const PLATFORMS = [
  { key: "tiktok", label: "TikTok" },
  { key: "youtube", label: "YouTube" },
  { key: "instagram", label: "Instagram" },
  { key: "facebook", label: "Facebook" },
  { key: "linkedin", label: "LinkedIn" },
  { key: "blog", label: "Blog" },
  { key: "podcast", label: "Podcast" },
  { key: "other", label: "Autre" },
] as const;

const STATUS_COLORS: Record<string, string> = {
  pending: "#F59E0B",
  active: "#10B981",
  paused: "#6B7280",
  terminated: "#EF4444",
};

export default function PartnersAdminScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const [loading, setLoading] = useState(true);
  const [partners, setPartners] = useState<Partner[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [detailPartner, setDetailPartner] = useState<Partner | null>(null);
  const [detailStats, setDetailStats] = useState<Stats | null>(null);

  // Form state pour création
  const [fName, setFName] = useState("");
  const [fEmail, setFEmail] = useState("");
  const [fPlatform, setFPlatform] = useState<string>("tiktok");
  const [fHandle, setFHandle] = useState("");
  const [fAudience, setFAudience] = useState("");
  const [fCustomCode, setFCustomCode] = useState("");
  const [creating, setCreating] = useState(false);

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const [pRes, sRes] = await Promise.all([
        api.get<{ partners: Partner[]; total: number }>("/partners"),
        api.get<Summary>("/partners/stats/summary"),
      ]);
      setPartners(pRes.data.partners);
      setSummary(sRes.data);
    } catch (e: any) {
      Alert.alert("Erreur", e?.response?.data?.detail ?? "Chargement échoué");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const openDetail = useCallback(async (partner: Partner) => {
    setDetailPartner(partner);
    try {
      const { data } = await api.get<Stats>(`/partners/${partner.id}/stats`);
      setDetailStats(data);
    } catch {
      setDetailStats(null);
    }
  }, []);

  const createPartner = useCallback(async () => {
    if (!fName.trim() || !fEmail.trim()) {
      Alert.alert("Champs manquants", "Nom et email sont obligatoires.");
      return;
    }
    setCreating(true);
    try {
      await api.post("/partners", {
        name: fName.trim(),
        email: fEmail.trim(),
        platform: fPlatform,
        handle: fHandle.trim(),
        audience_size: parseInt(fAudience || "0", 10),
        custom_code: fCustomCode.trim() || undefined,
      });
      setCreateOpen(false);
      setFName("");
      setFEmail("");
      setFHandle("");
      setFAudience("");
      setFCustomCode("");
      await loadAll();
      Alert.alert("Succès", "Partenaire créé ! Vous pouvez maintenant lui envoyer son contrat.");
    } catch (e: any) {
      Alert.alert("Erreur", e?.response?.data?.detail ?? "Création impossible");
    } finally {
      setCreating(false);
    }
  }, [fName, fEmail, fPlatform, fHandle, fAudience, fCustomCode, loadAll]);

  const updateStatus = useCallback(
    async (partner: Partner, status: Partner["status"]) => {
      try {
        await api.patch(`/partners/${partner.id}`, { status });
        await loadAll();
        if (detailPartner?.id === partner.id) {
          setDetailPartner({ ...partner, status });
        }
      } catch (e: any) {
        Alert.alert("Erreur", e?.response?.data?.detail ?? "MAJ impossible");
      }
    },
    [loadAll, detailPartner],
  );

  const markContractSigned = useCallback(
    async (partner: Partner) => {
      try {
        await api.patch(`/partners/${partner.id}`, { contract_signed: true });
        await loadAll();
        Alert.alert("Contrat signé ✅", "Le partenaire est maintenant actif.");
      } catch (e: any) {
        Alert.alert("Erreur", e?.response?.data?.detail ?? "MAJ impossible");
      }
    },
    [loadAll],
  );

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={{ padding: 8 }}>
          <Ionicons name="chevron-back" size={24} color={colors.textPrimary} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Partenaires affiliés</Text>
        <TouchableOpacity
          onPress={() => setCreateOpen(true)}
          style={styles.addBtn}
          testID="add-partner-btn"
        >
          <Ionicons name="add" size={22} color="#000" />
        </TouchableOpacity>
      </View>

      <ScrollView
        contentContainerStyle={{ paddingBottom: insets.bottom + 30 }}
        refreshing={loading}
      >
        {/* Résumé global */}
        {summary && (
          <View style={styles.summaryCard}>
            <Text style={styles.summaryTitle}>📊 Vue d&apos;ensemble</Text>
            <View style={styles.summaryGrid}>
              <View style={styles.summaryItem}>
                <Text style={styles.summaryValue}>{summary.total_partners}</Text>
                <Text style={styles.summaryLabel}>Partenaires</Text>
              </View>
              <View style={styles.summaryItem}>
                <Text style={[styles.summaryValue, { color: "#10B981" }]}>
                  {summary.active}
                </Text>
                <Text style={styles.summaryLabel}>Actifs</Text>
              </View>
              <View style={styles.summaryItem}>
                <Text style={styles.summaryValue}>{summary.total_clicks}</Text>
                <Text style={styles.summaryLabel}>Clics</Text>
              </View>
              <View style={styles.summaryItem}>
                <Text style={styles.summaryValue}>{summary.total_signups}</Text>
                <Text style={styles.summaryLabel}>Inscrits</Text>
              </View>
              <View style={styles.summaryItem}>
                <Text style={[styles.summaryValue, { color: colors.primary }]}>
                  {summary.total_commission_due_eur.toFixed(0)} €
                </Text>
                <Text style={styles.summaryLabel}>Commission due</Text>
              </View>
              <View style={styles.summaryItem}>
                <Text style={[styles.summaryValue, { color: "#10B981" }]}>
                  {summary.total_commission_paid_eur.toFixed(0)} €
                </Text>
                <Text style={styles.summaryLabel}>Déjà payée</Text>
              </View>
            </View>
          </View>
        )}

        {/* Liste */}
        {loading && partners.length === 0 ? (
          <ActivityIndicator color={colors.primary} style={{ marginTop: 30 }} />
        ) : partners.length === 0 ? (
          <View style={styles.emptyState}>
            <Text style={styles.emptyIcon}>🤝</Text>
            <Text style={styles.emptyTitle}>Aucun partenaire pour l&apos;instant</Text>
            <Text style={styles.emptyText}>
              Crée ton premier partenaire affilié pour commencer à tracker tes
              campagnes d&apos;influence.
            </Text>
            <TouchableOpacity
              style={styles.emptyCta}
              onPress={() => setCreateOpen(true)}
            >
              <Text style={styles.emptyCtaText}>+ Créer un partenaire</Text>
            </TouchableOpacity>
          </View>
        ) : (
          partners.map((p) => (
            <TouchableOpacity
              key={p.id}
              style={styles.partnerCard}
              onPress={() => openDetail(p)}
              activeOpacity={0.85}
            >
              <View style={styles.partnerHeader}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.partnerName}>{p.name}</Text>
                  <Text style={styles.partnerMeta}>
                    {p.platform.toUpperCase()} · {p.handle || "—"} ·{" "}
                    {p.audience_size.toLocaleString()} abonnés
                  </Text>
                </View>
                <View
                  style={[
                    styles.statusBadge,
                    { backgroundColor: `${STATUS_COLORS[p.status]}22` },
                  ]}
                >
                  <Text style={[styles.statusText, { color: STATUS_COLORS[p.status] }]}>
                    {p.status.toUpperCase()}
                  </Text>
                </View>
              </View>
              <View style={styles.partnerCode}>
                <Ionicons name="key" size={14} color={colors.primary} />
                <Text style={styles.partnerCodeText}>{p.code}</Text>
                <Text style={styles.partnerCommission}>
                  · {p.commission_rate}% / {p.commission_duration_months} mois
                </Text>
              </View>
              {!p.contract_signed && (
                <View style={styles.contractWarn}>
                  <Ionicons name="alert-circle" size={14} color="#F59E0B" />
                  <Text style={styles.contractWarnText}>Contrat à signer</Text>
                </View>
              )}
            </TouchableOpacity>
          ))
        )}
      </ScrollView>

      {/* ═════ Modal Création ═════ */}
      <Modal visible={createOpen} animationType="slide" transparent>
        <View style={styles.modalBackdrop}>
          <ScrollView contentContainerStyle={styles.modalContent}>
            <Text style={styles.modalTitle}>Nouveau partenaire affilié</Text>

            <Text style={styles.label}>Nom complet *</Text>
            <TextInput
              style={styles.input}
              value={fName}
              onChangeText={setFName}
              placeholder="ex. Jean Durand"
              placeholderTextColor={colors.textSecondary}
            />

            <Text style={styles.label}>Email *</Text>
            <TextInput
              style={styles.input}
              value={fEmail}
              onChangeText={setFEmail}
              placeholder="jean@example.com"
              placeholderTextColor={colors.textSecondary}
              keyboardType="email-address"
              autoCapitalize="none"
            />

            <Text style={styles.label}>Plateforme</Text>
            <View style={styles.platformGrid}>
              {PLATFORMS.map((p) => (
                <TouchableOpacity
                  key={p.key}
                  style={[
                    styles.platformChip,
                    fPlatform === p.key && styles.platformChipActive,
                  ]}
                  onPress={() => setFPlatform(p.key)}
                >
                  <Text
                    style={[
                      styles.platformChipText,
                      fPlatform === p.key && { color: "#000" },
                    ]}
                  >
                    {p.label}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            <Text style={styles.label}>Pseudo / Handle</Text>
            <TextInput
              style={styles.input}
              value={fHandle}
              onChangeText={setFHandle}
              placeholder="@jean_menuiserie"
              placeholderTextColor={colors.textSecondary}
              autoCapitalize="none"
            />

            <Text style={styles.label}>Taille de l&apos;audience</Text>
            <TextInput
              style={styles.input}
              value={fAudience}
              onChangeText={setFAudience}
              placeholder="15000"
              placeholderTextColor={colors.textSecondary}
              keyboardType="numeric"
            />

            <Text style={styles.label}>Code promo personnalisé (optionnel)</Text>
            <TextInput
              style={styles.input}
              value={fCustomCode}
              onChangeText={setFCustomCode}
              placeholder="ex. JEAN-MENUISERIE (sinon auto-généré)"
              placeholderTextColor={colors.textSecondary}
              autoCapitalize="characters"
            />

            <Text style={styles.helpText}>
              Le partenaire touchera <Text style={{ color: colors.primary }}>20%</Text> du CA
              généré pendant <Text style={{ color: colors.primary }}>12 mois</Text> sur les
              abonnements convertis via son code.
            </Text>

            <View style={styles.modalActions}>
              <Pressable
                style={[styles.modalBtn, styles.modalBtnSec]}
                onPress={() => setCreateOpen(false)}
              >
                <Text style={styles.modalBtnSecText}>Annuler</Text>
              </Pressable>
              <Pressable
                style={[styles.modalBtn, styles.modalBtnPrimary]}
                onPress={createPartner}
                disabled={creating}
              >
                {creating ? (
                  <ActivityIndicator color="#000" />
                ) : (
                  <Text style={styles.modalBtnPrimaryText}>Créer</Text>
                )}
              </Pressable>
            </View>
          </ScrollView>
        </View>
      </Modal>

      {/* ═════ Modal Détail ═════ */}
      <Modal visible={!!detailPartner} animationType="slide" transparent>
        <View style={styles.modalBackdrop}>
          <ScrollView contentContainerStyle={styles.modalContent}>
            {detailPartner && (
              <>
                <Text style={styles.modalTitle}>{detailPartner.name}</Text>
                <Text style={styles.modalSub}>
                  {detailPartner.platform.toUpperCase()} ·{" "}
                  {detailPartner.handle || "—"}
                </Text>
                <View style={styles.codeBlock}>
                  <Text style={styles.codeBlockLabel}>CODE PROMO</Text>
                  <Text style={styles.codeBlockValue}>{detailPartner.code}</Text>
                </View>

                {detailStats && (
                  <View style={styles.statsGrid}>
                    <View style={styles.statsCell}>
                      <Text style={styles.statsValue}>{detailStats.clicks}</Text>
                      <Text style={styles.statsLabel}>Clics</Text>
                    </View>
                    <View style={styles.statsCell}>
                      <Text style={styles.statsValue}>{detailStats.signups}</Text>
                      <Text style={styles.statsLabel}>Inscriptions</Text>
                    </View>
                    <View style={styles.statsCell}>
                      <Text style={styles.statsValue}>{detailStats.conversions}</Text>
                      <Text style={styles.statsLabel}>Conversions</Text>
                    </View>
                    <View style={styles.statsCell}>
                      <Text style={[styles.statsValue, { color: colors.primary }]}>
                        {detailStats.total_commission_due_eur.toFixed(2)} €
                      </Text>
                      <Text style={styles.statsLabel}>Commission due</Text>
                    </View>
                  </View>
                )}

                <Text style={styles.label}>Statut</Text>
                <View style={styles.statusBtns}>
                  {(["pending", "active", "paused", "terminated"] as const).map((s) => (
                    <TouchableOpacity
                      key={s}
                      style={[
                        styles.statusBtn,
                        detailPartner.status === s && {
                          backgroundColor: STATUS_COLORS[s],
                        },
                      ]}
                      onPress={() => updateStatus(detailPartner, s)}
                    >
                      <Text
                        style={[
                          styles.statusBtnText,
                          detailPartner.status === s && { color: "#000" },
                        ]}
                      >
                        {s}
                      </Text>
                    </TouchableOpacity>
                  ))}
                </View>

                {!detailPartner.contract_signed && (
                  <TouchableOpacity
                    style={styles.contractBtn}
                    onPress={() => markContractSigned(detailPartner)}
                  >
                    <Ionicons name="checkmark-circle" size={20} color="#10B981" />
                    <Text style={styles.contractBtnText}>Marquer contrat signé</Text>
                  </TouchableOpacity>
                )}

                <Text style={styles.helpText}>
                  💡 Téléchargez le contrat partenariat prêt à signer depuis
                  l&apos;URL <Text style={{ color: colors.primary }}>
                    /api/_downloads/partner-contract
                  </Text>
                </Text>

                <Pressable
                  style={[styles.modalBtn, styles.modalBtnSec, { marginTop: 20 }]}
                  onPress={() => {
                    setDetailPartner(null);
                    setDetailStats(null);
                  }}
                >
                  <Text style={styles.modalBtnSecText}>Fermer</Text>
                </Pressable>
              </>
            )}
          </ScrollView>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  header: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 8,
    paddingBottom: 10,
    paddingTop: 8,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  headerTitle: {
    flex: 1,
    color: colors.textPrimary,
    fontSize: 18,
    fontWeight: "800",
  },
  addBtn: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
  },
  summaryCard: {
    margin: 12,
    padding: 14,
    backgroundColor: colors.surface,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: colors.border,
  },
  summaryTitle: {
    color: colors.textPrimary,
    fontSize: 14,
    fontWeight: "800",
    marginBottom: 10,
  },
  summaryGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 12,
  },
  summaryItem: { width: "30%" },
  summaryValue: {
    color: colors.textPrimary,
    fontSize: 20,
    fontWeight: "900",
  },
  summaryLabel: { color: colors.textSecondary, fontSize: 11 },
  emptyState: {
    alignItems: "center",
    paddingHorizontal: 30,
    paddingTop: 50,
  },
  emptyIcon: { fontSize: 50, marginBottom: 12 },
  emptyTitle: {
    color: colors.textPrimary,
    fontSize: 16,
    fontWeight: "800",
    marginBottom: 8,
  },
  emptyText: {
    color: colors.textSecondary,
    textAlign: "center",
    fontSize: 13,
    lineHeight: 18,
    marginBottom: 20,
  },
  emptyCta: {
    backgroundColor: colors.primary,
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 10,
  },
  emptyCtaText: { color: "#000", fontWeight: "800", fontSize: 14 },
  partnerCard: {
    marginHorizontal: 12,
    marginBottom: 8,
    padding: 14,
    backgroundColor: colors.surface,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.border,
  },
  partnerHeader: {
    flexDirection: "row",
    alignItems: "flex-start",
    marginBottom: 8,
  },
  partnerName: {
    color: colors.textPrimary,
    fontSize: 15,
    fontWeight: "800",
  },
  partnerMeta: {
    color: colors.textSecondary,
    fontSize: 11,
    marginTop: 2,
  },
  statusBadge: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
  },
  statusText: { fontSize: 9, fontWeight: "900", letterSpacing: 0.5 },
  partnerCode: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    marginTop: 4,
  },
  partnerCodeText: {
    color: colors.primary,
    fontSize: 12,
    fontWeight: "800",
    fontFamily: Platform.OS === "ios" ? "Menlo" : "monospace",
  },
  partnerCommission: { color: colors.textSecondary, fontSize: 11 },
  contractWarn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    marginTop: 8,
  },
  contractWarnText: { color: "#F59E0B", fontSize: 11, fontWeight: "700" },
  modalBackdrop: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.75)",
    justifyContent: "flex-end",
  },
  modalContent: {
    backgroundColor: colors.background,
    borderTopLeftRadius: 18,
    borderTopRightRadius: 18,
    padding: 20,
    paddingBottom: 50,
    minHeight: "65%",
  },
  modalTitle: {
    color: colors.textPrimary,
    fontSize: 19,
    fontWeight: "900",
    marginBottom: 4,
  },
  modalSub: {
    color: colors.textSecondary,
    fontSize: 12,
    marginBottom: 14,
  },
  label: {
    color: colors.textPrimary,
    fontSize: 12,
    fontWeight: "700",
    marginTop: 12,
    marginBottom: 6,
  },
  input: {
    color: colors.textPrimary,
    backgroundColor: colors.surface,
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 11,
    fontSize: 14,
    borderWidth: 1,
    borderColor: colors.border,
  },
  platformGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 6,
    marginTop: 4,
  },
  platformChip: {
    paddingHorizontal: 12,
    paddingVertical: 7,
    backgroundColor: colors.surface,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.border,
  },
  platformChipActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  platformChipText: { color: colors.textPrimary, fontSize: 12, fontWeight: "700" },
  helpText: {
    color: colors.textSecondary,
    fontSize: 11.5,
    lineHeight: 16,
    marginTop: 14,
    fontStyle: "italic",
  },
  modalActions: {
    flexDirection: "row",
    gap: 10,
    marginTop: 18,
  },
  modalBtn: {
    flex: 1,
    paddingVertical: 13,
    borderRadius: 10,
    alignItems: "center",
  },
  modalBtnSec: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
  },
  modalBtnSecText: { color: colors.textPrimary, fontWeight: "700" },
  modalBtnPrimary: { backgroundColor: colors.primary },
  modalBtnPrimaryText: { color: "#000", fontWeight: "900" },
  codeBlock: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.primary,
    borderRadius: 10,
    padding: 12,
    marginTop: 12,
    alignItems: "center",
  },
  codeBlockLabel: {
    color: colors.textSecondary,
    fontSize: 10,
    fontWeight: "700",
    letterSpacing: 1,
    marginBottom: 4,
  },
  codeBlockValue: {
    color: colors.primary,
    fontSize: 20,
    fontWeight: "900",
    fontFamily: Platform.OS === "ios" ? "Menlo" : "monospace",
  },
  statsGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 10,
    marginTop: 14,
  },
  statsCell: {
    width: "47%",
    backgroundColor: colors.surface,
    padding: 12,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.border,
  },
  statsValue: { color: colors.textPrimary, fontSize: 20, fontWeight: "900" },
  statsLabel: { color: colors.textSecondary, fontSize: 11, marginTop: 2 },
  statusBtns: { flexDirection: "row", flexWrap: "wrap", gap: 6, marginTop: 8 },
  statusBtn: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    backgroundColor: colors.surface,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.border,
  },
  statusBtnText: {
    color: colors.textPrimary,
    fontSize: 11,
    fontWeight: "700",
    textTransform: "uppercase",
  },
  contractBtn: {
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    gap: 8,
    marginTop: 16,
    padding: 13,
    backgroundColor: "rgba(16,185,129,0.12)",
    borderWidth: 1,
    borderColor: "rgba(16,185,129,0.5)",
    borderRadius: 10,
  },
  contractBtnText: { color: "#10B981", fontWeight: "800", fontSize: 14 },
});
