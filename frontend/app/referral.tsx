/**
 * Écran "Mon parrainage" — Build 9 (juin 2026).
 *
 * Permet à l'utilisateur de :
 *   • Voir son code de parrainage (auto-généré ou personnalisé)
 *   • Le personnaliser (ex. "JEAN-MENUISERIE")
 *   • Le partager via le composant Share natif
 *   • Voir ses statistiques (filleuls actifs, mois offerts gagnés)
 *
 * Règles métier rappelées dans l'UI :
 *   • Récompense PARRAIN : 2 mois offerts par filleul actif
 *   • Limite : 10 filleuls max
 *   • Déclenchement : à la 1ère facture payée du filleul
 */
import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Platform,
  ScrollView,
  Share,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import * as Clipboard from "expo-clipboard";
import { useRouter } from "expo-router";
import { api } from "@/src/services/api";
import { colors } from "@/src/theme";

type ReferralStatus = {
  code: string;
  code_is_custom: boolean;
  max_referrals: number;
  referrals_used: number;
  referrals_pending: number;
  credit_months_total: number;
  credit_months_remaining: number;
  referred_by_code: string | null;
};

export default function ReferralScreen() {
  const router = useRouter();
  const [status, setStatus] = useState<ReferralStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [draftCode, setDraftCode] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const load = useCallback(async () => {
    try {
      const { data } = await api.get<ReferralStatus>("/referral/me");
      setStatus(data);
      setDraftCode(data.code);
    } catch (e: any) {
      Alert.alert("Erreur", e?.response?.data?.detail || "Impossible de charger");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const handleSaveCode = async () => {
    if (!draftCode.trim() || draftCode === status?.code) {
      setEditing(false);
      return;
    }
    setSubmitting(true);
    try {
      const { data } = await api.post<ReferralStatus>("/referral/code", {
        code: draftCode.trim(),
      });
      setStatus(data);
      setEditing(false);
      Alert.alert("✅ Code mis à jour", "Votre code de parrainage personnalisé est désormais actif.");
    } catch (e: any) {
      Alert.alert(
        "Erreur",
        e?.response?.data?.detail ||
          "Impossible de mettre à jour ce code. Essayez-en un autre.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  const handleCopy = async () => {
    if (!status?.code) return;
    await Clipboard.setStringAsync(status.code);
    Alert.alert("📋 Copié", `Le code « ${status.code} » a été copié dans le presse-papiers.`);
  };

  const handleShare = async () => {
    if (!status?.code) return;
    const msg =
      `🎁 J'utilise MesureChâssis pour mes prises de mesures sur chantier.\n\n` +
      `Inscris-toi avec mon code de parrainage : ${status.code}\n\n` +
      `https://mesurechassis.com`;
    try {
      await Share.share({ message: msg, title: "Rejoignez-moi sur MesureChâssis" });
    } catch {
      // Annulé par l'utilisateur
    }
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.safe} edges={["top", "bottom"]}>
        <View style={styles.loadingBox}>
          <ActivityIndicator size="large" color={colors.primary} />
        </View>
      </SafeAreaView>
    );
  }
  if (!status) return null;

  const progress = (status.referrals_used / status.max_referrals) * 100;
  const reachedMax = status.referrals_used >= status.max_referrals;

  return (
    <SafeAreaView style={styles.safe} edges={["top", "bottom"]}>
      {/* ===== HEADER ===== */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
          <Ionicons name="chevron-back" size={22} color={colors.textPrimary} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Mon parrainage</Text>
        <View style={{ width: 40 }} />
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        {/* ===== CARTE CODE ===== */}
        <View style={styles.codeCard}>
          <Text style={styles.codeLabel}>VOTRE CODE PARRAINAGE</Text>
          {editing ? (
            <View style={styles.editBox}>
              <TextInput
                value={draftCode}
                onChangeText={(v) => setDraftCode(v.toUpperCase().replace(/\s/g, "-"))}
                placeholder="JEAN-MENUISERIE"
                placeholderTextColor={colors.placeholder}
                autoCapitalize="characters"
                autoCorrect={false}
                maxLength={24}
                style={styles.editInput}
              />
              <TouchableOpacity
                onPress={handleSaveCode}
                disabled={submitting}
                style={[styles.saveBtn, submitting && { opacity: 0.6 }]}
              >
                {submitting ? (
                  <ActivityIndicator color="#000" />
                ) : (
                  <Ionicons name="checkmark" size={20} color="#000" />
                )}
              </TouchableOpacity>
              <TouchableOpacity
                onPress={() => {
                  setEditing(false);
                  setDraftCode(status.code);
                }}
                style={styles.cancelBtn}
              >
                <Ionicons name="close" size={20} color={colors.textSecondary} />
              </TouchableOpacity>
            </View>
          ) : (
            <View style={styles.codeBox}>
              <Text style={styles.codeValue}>{status.code}</Text>
              <TouchableOpacity
                onPress={() => setEditing(true)}
                style={styles.editIconBtn}
                testID="edit-code-btn"
              >
                <Ionicons name="pencil" size={18} color={colors.primary} />
              </TouchableOpacity>
            </View>
          )}
          <Text style={styles.codeHint}>
            {status.code_is_custom
              ? "✨ Code personnalisé — facile à mémoriser et à partager"
              : "💡 Personnalisez votre code (ex. NOM-MENUISERIE) pour qu'il soit reconnaissable"}
          </Text>

          {/* Boutons Copier / Partager */}
          <View style={styles.actionRow}>
            <TouchableOpacity
              onPress={handleCopy}
              style={styles.actionBtn}
              testID="copy-code-btn"
            >
              <Ionicons name="copy-outline" size={16} color={colors.textPrimary} />
              <Text style={styles.actionBtnText}>Copier</Text>
            </TouchableOpacity>
            <TouchableOpacity
              onPress={handleShare}
              style={[styles.actionBtn, styles.actionBtnPrimary]}
              testID="share-code-btn"
            >
              <Ionicons name="share-social-outline" size={16} color="#000" />
              <Text style={[styles.actionBtnText, { color: "#000" }]}>Partager</Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* ===== STATS ===== */}
        <View style={styles.statsCard}>
          <View style={styles.statRow}>
            <View style={styles.statBox}>
              <Text style={styles.statValue}>{status.referrals_used}</Text>
              <Text style={styles.statLabel}>Filleuls actifs</Text>
            </View>
            <View style={styles.statBox}>
              <Text style={styles.statValue}>{status.referrals_pending}</Text>
              <Text style={styles.statLabel}>En attente</Text>
            </View>
            <View style={styles.statBox}>
              <Text style={[styles.statValue, { color: colors.primary }]}>
                {status.credit_months_total}
              </Text>
              <Text style={styles.statLabel}>Mois gagnés</Text>
            </View>
          </View>

          {/* Barre de progression */}
          <View style={styles.progressWrap}>
            <View
              style={[
                styles.progressFill,
                { width: `${Math.min(100, progress)}%` },
                reachedMax && { backgroundColor: colors.warning },
              ]}
            />
          </View>
          <Text style={styles.progressLabel}>
            {status.referrals_used} / {status.max_referrals} filleuls
            {reachedMax && " — limite atteinte"}
          </Text>

          {status.credit_months_remaining > 0 && (
            <View style={styles.creditBanner}>
              <Ionicons name="gift" size={18} color={colors.primary} />
              <Text style={styles.creditText}>
                <Text style={{ fontWeight: "900" }}>
                  {status.credit_months_remaining} mois offerts
                </Text>{" "}
                à appliquer à votre prochain renouvellement.
              </Text>
            </View>
          )}
        </View>

        {/* ===== INFO RÉCOMPENSE ===== */}
        <View style={styles.infoCard}>
          <View style={styles.infoHeader}>
            <Ionicons name="gift-outline" size={20} color={colors.primary} />
            <Text style={styles.infoTitle}>COMMENT ÇA MARCHE ?</Text>
          </View>
          <Text style={styles.infoText}>
            • Partagez votre code à un menuisier{"\n"}
            • Il s&apos;inscrit à MesureChâssis avec votre code{"\n"}
            • Dès qu&apos;il paie son 1er abonnement, vous gagnez{" "}
            <Text style={{ fontWeight: "900", color: colors.primary }}>
              2 mois offerts
            </Text>{" "}
            sur votre prochain renouvellement{"\n"}
            • Maximum {status.max_referrals} filleuls par parrain
          </Text>
        </View>

        {/* ===== PARRAIN ACTUEL (si on a été parrainé) ===== */}
        {status.referred_by_code && (
          <View style={styles.parrainCard}>
            <Ionicons name="person-circle-outline" size={20} color={colors.success} />
            <Text style={styles.parrainText}>
              Vous avez été parrainé par{" "}
              <Text style={{ fontWeight: "900" }}>{status.referred_by_code}</Text>
            </Text>
          </View>
        )}

        {/* Hint plateforme */}
        {Platform.OS === "ios" && (
          <Text style={styles.iosHint}>
            🍎 Les récompenses sont créditées automatiquement lors du paiement de
            l&apos;abonnement de votre filleul depuis mesurechassis.com.
          </Text>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  loadingBox: { flex: 1, alignItems: "center", justifyContent: "center" },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSubtle,
  },
  backBtn: {
    width: 40,
    height: 40,
    alignItems: "center",
    justifyContent: "center",
  },
  headerTitle: {
    color: colors.textPrimary,
    fontSize: 16,
    fontWeight: "800",
    letterSpacing: 0.4,
  },
  content: { padding: 16, paddingBottom: 80 },
  codeCard: {
    backgroundColor: colors.surface,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    padding: 18,
    marginBottom: 14,
  },
  codeLabel: {
    color: colors.textSecondary,
    fontSize: 11,
    fontWeight: "900",
    letterSpacing: 0.8,
    marginBottom: 12,
  },
  codeBox: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "rgba(255, 107, 26, 0.08)",
    borderWidth: 1.5,
    borderColor: colors.primary,
    borderRadius: 10,
    paddingHorizontal: 16,
    paddingVertical: 14,
  },
  codeValue: {
    flex: 1,
    color: colors.primary,
    fontSize: 22,
    fontWeight: "900",
    letterSpacing: 1.5,
    fontFamily: Platform.OS === "ios" ? "Menlo" : "monospace",
  },
  editIconBtn: { padding: 6 },
  editBox: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  editInput: {
    flex: 1,
    backgroundColor: colors.inputBg,
    color: colors.textPrimary,
    borderWidth: 1,
    borderColor: colors.primary,
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 12,
    fontSize: 16,
    fontWeight: "800",
    letterSpacing: 1.2,
  },
  saveBtn: {
    width: 44,
    height: 44,
    backgroundColor: colors.primary,
    borderRadius: 10,
    alignItems: "center",
    justifyContent: "center",
  },
  cancelBtn: {
    width: 44,
    height: 44,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    borderRadius: 10,
    alignItems: "center",
    justifyContent: "center",
  },
  codeHint: {
    color: colors.textSecondary,
    fontSize: 12,
    marginTop: 10,
    lineHeight: 16,
  },
  actionRow: {
    flexDirection: "row",
    gap: 10,
    marginTop: 14,
  },
  actionBtn: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    paddingVertical: 12,
    borderRadius: 10,
    backgroundColor: colors.bg,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
  },
  actionBtnPrimary: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  actionBtnText: {
    color: colors.textPrimary,
    fontWeight: "800",
    fontSize: 13,
  },
  statsCard: {
    backgroundColor: colors.surface,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    padding: 18,
    marginBottom: 14,
  },
  statRow: {
    flexDirection: "row",
    gap: 12,
    marginBottom: 14,
  },
  statBox: {
    flex: 1,
    alignItems: "center",
    paddingVertical: 10,
    borderRadius: 10,
    backgroundColor: colors.bg,
  },
  statValue: {
    color: colors.textPrimary,
    fontSize: 26,
    fontWeight: "900",
  },
  statLabel: {
    color: colors.textSecondary,
    fontSize: 10,
    fontWeight: "700",
    letterSpacing: 0.4,
    marginTop: 2,
    textAlign: "center",
  },
  progressWrap: {
    height: 8,
    backgroundColor: colors.bg,
    borderRadius: 4,
    overflow: "hidden",
  },
  progressFill: {
    height: "100%",
    backgroundColor: colors.success,
    borderRadius: 4,
  },
  progressLabel: {
    color: colors.textSecondary,
    fontSize: 11,
    fontWeight: "700",
    marginTop: 6,
    textAlign: "center",
  },
  creditBanner: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    marginTop: 14,
    padding: 12,
    backgroundColor: "rgba(255, 107, 26, 0.08)",
    borderWidth: 1,
    borderColor: colors.primary,
    borderRadius: 10,
  },
  creditText: {
    flex: 1,
    color: colors.textPrimary,
    fontSize: 13,
    lineHeight: 18,
  },
  infoCard: {
    backgroundColor: colors.surface,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    padding: 18,
    marginBottom: 14,
  },
  infoHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginBottom: 10,
  },
  infoTitle: {
    color: colors.textPrimary,
    fontSize: 13,
    fontWeight: "900",
    letterSpacing: 0.5,
  },
  infoText: {
    color: colors.textSecondary,
    fontSize: 13,
    lineHeight: 22,
  },
  parrainCard: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    padding: 14,
    borderRadius: 12,
    backgroundColor: "rgba(34, 197, 94, 0.08)",
    borderWidth: 1,
    borderColor: colors.success,
    marginBottom: 12,
  },
  parrainText: {
    flex: 1,
    color: colors.textPrimary,
    fontSize: 13,
  },
  iosHint: {
    color: colors.textSecondary,
    fontSize: 11,
    fontStyle: "italic",
    textAlign: "center",
    marginTop: 10,
    paddingHorizontal: 8,
  },
});
