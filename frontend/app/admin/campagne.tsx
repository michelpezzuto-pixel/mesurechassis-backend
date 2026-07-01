import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import { api } from "@/src/services/api";
import { colors } from "@/src/theme";

type Stats = {
  pending: number;
  sent: number;
  failed: number;
  sending: number;
  sent_today: number;
  daily_limit: number;
  converted: number;
  relance_due: number;
  relances_sent: number;
  // 🆕 RGPD — Nombre de prospects désinscrits (cumul)
  unsubscribed?: number;
};

type Prospect = {
  id: string;
  email: string;
  company: string;
  region: string;
  status: "pending" | "sending" | "sent" | "failed";
  sent_at: string | null;
  relance_sent_at?: string | null;
  // 🆕 RGPD — true si le prospect a cliqué "Se désinscrire" ou si admin l'a blackliste
  unsubscribed?: boolean;
  unsubscribed_at?: string | null;
  unsubscribed_via?: "admin_manual" | "public_link" | string | null;
};

const STATUS_UI: Record<string, { label: string; color: string }> = {
  pending: { label: "À CONTACTER", color: "#9ca3af" },
  sending: { label: "ENVOI…", color: "#FBBF24" },
  sent: { label: "ENVOYÉ", color: "#22C55E" },
  relanced: { label: "RELANCÉ", color: "#60A5FA" },
  failed: { label: "ÉCHEC", color: "#F87171" },
};

/**
 * 🚫 Domaines emails génériques (fournisseurs) — À ne PAS afficher comme nom
 * d'entreprise. Utilisé pour filtrer les cas où le champ `company` a été
 * incorrectement rempli avec le fournisseur email (ex: "Gmail", "Free").
 */
const GENERIC_EMAIL_DOMAINS = new Set([
  "gmail", "googlemail",
  "yahoo", "yahoo.fr", "yahoo.com",
  "hotmail", "hotmail.fr", "hotmail.com",
  "outlook", "outlook.fr", "outlook.com",
  "live", "live.fr", "live.com",
  "orange", "orange.fr",
  "free", "free.fr",
  "wanadoo", "wanadoo.fr",
  "sfr", "sfr.fr",
  "laposte", "laposte.net",
  "bbox", "bouygtel",
  "aol", "aol.fr", "aol.com",
  "icloud", "me.com", "mac.com",
  "protonmail", "proton.me",
  "voila", "voila.fr",
  "numericable", "neuf.fr",
  "skynet", "skynet.be",
  "telenet", "telenet.be",
  "belgacom", "belgacom.be", "proximus.be",
  "gmx", "gmx.fr", "gmx.com",
  "mail", "mail.com", "mail.ru",
]);

/** Retourne le nom à afficher : ignore les "companies" qui sont en fait des domaines email génériques. */
function displayName(p: { company?: string; email: string }): string {
  const c = (p.company || "").trim();
  if (!c) return p.email;
  if (GENERIC_EMAIL_DOMAINS.has(c.toLowerCase())) return p.email;
  return c;
}

/** Vue ADMIN : campagne email prospection testeurs (1 bouton / jour). */
export default function AdminCampagne() {
  const router = useRouter();
  const [stats, setStats] = useState<Stats | null>(null);
  const [prospects, setProspects] = useState<Prospect[]>([]);
  const [loading, setLoading] = useState(true);
  const [launching, setLaunching] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchAll = useCallback(async () => {
    try {
      const [s, p] = await Promise.all([
        api.get<Stats>("/campaign/stats"),
        api.get<{ prospects: Prospect[] }>("/campaign/prospects"),
      ]);
      setStats(s.data);
      setProspects(p.data.prospects);
      // Poll tant que des envois sont en cours
      if (s.data.sending > 0 && !pollRef.current) {
        pollRef.current = setInterval(() => void fetchAll(), 4000);
      } else if (s.data.sending === 0 && pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchAll();
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [fetchAll]);

  const launchBatch = async () => {
    setLaunching(true);
    setMessage(null);
    try {
      const res = await api.post<{ scheduled: number; message: string }>(
        "/campaign/send-batch",
      );
      setMessage(`🚀 ${res.data.message}`);
      void fetchAll();
    } catch (e: any) {
      setMessage(`⚠️ ${e?.response?.data?.detail || "Erreur lors du lancement."}`);
    } finally {
      setLaunching(false);
    }
  };

  // 🆕 RGPD — Désinscription manuelle d'un prospect par l'admin
  //   (utilisé quand un prospect a répondu STOP par email)
  const unsubscribeProspect = useCallback(
    (p: Prospect) => {
      Alert.alert(
        "Désinscrire ce prospect ?",
        `${p.email}\n\nIl ne recevra plus AUCUN email de campagne. Cette action est conforme RGPD.`,
        [
          { text: "Annuler", style: "cancel" },
          {
            text: "🚫 Désinscrire",
            style: "destructive",
            onPress: async () => {
              try {
                await api.post(`/campaign/prospects/${p.id}/unsubscribe`);
                setMessage(`🚫 ${p.email} désinscrit avec succès.`);
                // Update local state pour feedback immédiat (avant le refetch)
                setProspects((prev) =>
                  prev.map((q) =>
                    q.id === p.id
                      ? { ...q, unsubscribed: true, unsubscribed_via: "admin_manual" }
                      : q,
                  ),
                );
                void fetchAll();
              } catch (e: any) {
                setMessage(`⚠️ ${e?.response?.data?.detail || "Erreur"}`);
              }
            },
          },
        ],
      );
    },
    [fetchAll],
  );

  // 🆕 RGPD — Ré-inscription (cas exceptionnel, accord exprès du prospect)
  const resubscribeProspect = useCallback(
    (p: Prospect) => {
      Alert.alert(
        "Ré-inscrire ce prospect ?",
        `${p.email}\n\n⚠️ À utiliser SEULEMENT avec accord exprès du prospect.`,
        [
          { text: "Annuler", style: "cancel" },
          {
            text: "Ré-inscrire",
            onPress: async () => {
              try {
                await api.post(`/campaign/prospects/${p.id}/resubscribe`);
                setMessage(`✅ ${p.email} ré-inscrit.`);
                setProspects((prev) =>
                  prev.map((q) =>
                    q.id === p.id
                      ? { ...q, unsubscribed: false, unsubscribed_via: null }
                      : q,
                  ),
                );
                void fetchAll();
              } catch (e: any) {
                setMessage(`⚠️ ${e?.response?.data?.detail || "Erreur"}`);
              }
            },
          },
        ],
      );
    },
    [fetchAll],
  );

  const remaining = stats ? stats.daily_limit - stats.sent_today : 0;
  const todo = stats ? stats.pending + stats.relance_due : 0;
  const canSend = !!stats && todo > 0 && remaining > 0 && stats.sending === 0;

  return (
    <SafeAreaView style={styles.flex} edges={["top", "bottom"]}>
      <View style={styles.topBar}>
        <TouchableOpacity
          testID="campagne-back-button"
          onPress={() => router.back()}
          hitSlop={10}
        >
          <Ionicons name="arrow-back" size={22} color={colors.textPrimary} />
        </TouchableOpacity>
        <Text style={styles.topTitle}>📣 CAMPAGNE TESTEURS</Text>
        <TouchableOpacity
          testID="campagne-refresh-button"
          onPress={() => void fetchAll()}
          hitSlop={10}
        >
          <Ionicons name="refresh" size={20} color={colors.primary} />
        </TouchableOpacity>
      </View>

      {loading || !stats ? (
        <ActivityIndicator color={colors.primary} style={{ marginTop: 40 }} />
      ) : (
        <>
          <View style={styles.statsRow}>
            <View style={styles.statBox} testID="campagne-pending-box">
              <Text style={styles.statValue}>{stats.pending}</Text>
              <Text style={styles.statLabel}>à contacter</Text>
            </View>
            <View style={styles.statBox}>
              <Text style={[styles.statValue, { color: "#22C55E" }]}>
                {stats.sent}
              </Text>
              <Text style={styles.statLabel}>envoyés</Text>
            </View>
            <View style={styles.statBox}>
              <Text style={[styles.statValue, { color: "#FBBF24" }]}>
                {stats.sent_today}/{stats.daily_limit}
              </Text>
              <Text style={styles.statLabel}>aujourd&apos;hui</Text>
            </View>
            <View style={styles.statBox}>
              <Text style={[styles.statValue, { color: colors.primary }]}>
                {stats.converted}
              </Text>
              <Text style={styles.statLabel}>inscrits 🎉</Text>
            </View>
            {/* 🆕 RGPD — Stat désinscrits */}
            <View style={styles.statBox}>
              <Text style={[styles.statValue, { color: "#F87171" }]}>
                {stats.unsubscribed ?? 0}
              </Text>
              <Text style={styles.statLabel}>désinscrits</Text>
            </View>
          </View>

          <TouchableOpacity
            testID="campagne-send-batch-button"
            style={[styles.sendBtn, !canSend && styles.sendBtnDisabled]}
            onPress={() => void launchBatch()}
            disabled={!canSend || launching}
          >
            {launching || stats.sending > 0 ? (
              <>
                <ActivityIndicator color="#fff" size="small" />
                <Text style={styles.sendBtnText}>
                  {stats.sending > 0
                    ? `Envoi en cours… (${stats.sending} restants)`
                    : "Lancement…"}
                </Text>
              </>
            ) : (
              <>
                <Ionicons name="send" size={18} color="#fff" />
                <Text style={styles.sendBtnText}>
                  {remaining <= 0
                    ? "Limite du jour atteinte — revenez demain"
                    : todo === 0
                      ? "Liste épuisée 🎉"
                      : `ENVOYER LE LOT DU JOUR (${Math.min(remaining, todo)} emails)`}
                </Text>
              </>
            )}
          </TouchableOpacity>

          {!!stats.relance_due && (
            <Text style={styles.relanceInfo} testID="campagne-relance-info">
              🔁 {stats.relance_due} relance{stats.relance_due > 1 ? "s" : ""} J+5
              incluse{stats.relance_due > 1 ? "s" : ""} en priorité dans le
              prochain lot
            </Text>
          )}

          {message && (
            <Text style={styles.message} testID="campagne-message">
              {message}
            </Text>
          )}

          <FlatList
            data={prospects}
            keyExtractor={(p) => p.id}
            contentContainerStyle={{ padding: 16, paddingBottom: 50 }}
            renderItem={({ item }) => {
              const key =
                item.status === "sent" && item.relance_sent_at
                  ? "relanced"
                  : item.status;
              const ui = STATUS_UI[key] ?? STATUS_UI.pending;
              const isUnsub = !!item.unsubscribed;
              return (
                <View style={styles.card} testID={`prospect-${item.email}`}>
                  <View style={{ flex: 1 }}>
                    <Text
                      style={[
                        styles.cardName,
                        isUnsub && styles.unsubText,
                      ]}
                    >
                      {displayName(item)}
                    </Text>
                    <Text
                      style={[styles.cardEmail, isUnsub && styles.unsubText]}
                    >
                      {item.email}
                    </Text>
                    {!!item.region && (
                      <Text
                        style={[styles.cardMeta, isUnsub && styles.unsubText]}
                      >
                        {item.region}
                      </Text>
                    )}
                  </View>
                  <View style={styles.rightCol}>
                    {/* Badge statut (envoyé / pending / etc.) — masqué si désinscrit */}
                    {!isUnsub && (
                      <View
                        style={[
                          styles.badge,
                          { backgroundColor: `${ui.color}22` },
                        ]}
                      >
                        <Text style={[styles.badgeText, { color: ui.color }]}>
                          {ui.label}
                        </Text>
                      </View>
                    )}
                    {/* 🆕 Badge "DÉSINSCRIT" si opt-out actif */}
                    {isUnsub && (
                      <View style={styles.unsubBadge}>
                        <Ionicons name="ban" size={11} color="#F87171" />
                        <Text style={styles.unsubBadgeText}>
                          {item.unsubscribed_via === "public_link"
                            ? "DÉSINSCRIT (LIEN)"
                            : "DÉSINSCRIT"}
                        </Text>
                      </View>
                    )}
                    {/* 🆕 Bouton désinscrire / ré-inscrire */}
                    {isUnsub ? (
                      <TouchableOpacity
                        testID={`resubscribe-${item.email}`}
                        onPress={() => resubscribeProspect(item)}
                        style={styles.actionBtnGreen}
                      >
                        <Ionicons
                          name="refresh-circle"
                          size={14}
                          color="#22C55E"
                        />
                        <Text style={styles.actionBtnTextGreen}>
                          Ré-inscrire
                        </Text>
                      </TouchableOpacity>
                    ) : (
                      <TouchableOpacity
                        testID={`unsubscribe-${item.email}`}
                        onPress={() => unsubscribeProspect(item)}
                        style={styles.actionBtnRed}
                      >
                        <Ionicons
                          name="ban-outline"
                          size={14}
                          color="#F87171"
                        />
                        <Text style={styles.actionBtnTextRed}>
                          Désinscrire
                        </Text>
                      </TouchableOpacity>
                    )}
                  </View>
                </View>
              );
            }}
          />
        </>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: colors.bg },
  topBar: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 16,
    paddingVertical: 14,
  },
  topTitle: { color: colors.textPrimary, fontWeight: "800", fontSize: 15, letterSpacing: 1 },
  statsRow: { flexDirection: "row", gap: 8, paddingHorizontal: 16 },
  statBox: {
    flex: 1,
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: 12,
    alignItems: "center",
  },
  statValue: { color: colors.textPrimary, fontSize: 20, fontWeight: "800" },
  statLabel: { color: colors.textSecondary, fontSize: 10.5, marginTop: 2, textAlign: "center" },
  sendBtn: {
    flexDirection: "row",
    gap: 10,
    backgroundColor: colors.primary,
    margin: 16,
    marginBottom: 6,
    paddingVertical: 15,
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center",
  },
  sendBtnDisabled: { backgroundColor: colors.surfaceElevated },
  sendBtnText: { color: "#fff", fontWeight: "800", fontSize: 13.5 },
  message: {
    color: colors.textSecondary,
    fontSize: 12.5,
    textAlign: "center",
    paddingHorizontal: 20,
    marginBottom: 4,
  },
  relanceInfo: {
    color: "#60A5FA",
    fontSize: 12,
    textAlign: "center",
    paddingHorizontal: 20,
    marginBottom: 4,
  },
  card: {
    flexDirection: "row",
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: 13,
    marginBottom: 8,
    alignItems: "center",
  },
  cardName: { color: colors.textPrimary, fontWeight: "700", fontSize: 14 },
  cardEmail: { color: colors.primary, fontSize: 12.5, marginTop: 1 },
  cardMeta: { color: colors.textSecondary, fontSize: 11.5, marginTop: 1 },
  badge: { paddingHorizontal: 9, paddingVertical: 4, borderRadius: 7 },
  badgeText: { fontSize: 10, fontWeight: "800" },
  // 🆕 Colonne droite : badge + bouton désinscrire
  rightCol: {
    flexDirection: "column",
    alignItems: "flex-end",
    gap: 6,
    marginLeft: 10,
  },
  unsubText: {
    color: "#71717A",
    textDecorationLine: "line-through",
  },
  unsubBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    backgroundColor: "#F8717122",
    borderColor: "#F87171",
    borderWidth: 1,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
  },
  unsubBadgeText: {
    color: "#F87171",
    fontSize: 9.5,
    fontWeight: "900",
    letterSpacing: 0.3,
  },
  actionBtnRed: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    backgroundColor: "#F8717115",
    borderColor: "#F8717155",
    borderWidth: 1,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  actionBtnTextRed: {
    color: "#F87171",
    fontSize: 11,
    fontWeight: "700",
  },
  actionBtnGreen: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    backgroundColor: "#22C55E15",
    borderColor: "#22C55E55",
    borderWidth: 1,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  actionBtnTextGreen: {
    color: "#22C55E",
    fontSize: 11,
    fontWeight: "700",
  },
});
