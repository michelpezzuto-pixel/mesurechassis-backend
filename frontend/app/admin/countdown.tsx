import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Image,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import * as Clipboard from "expo-clipboard";
import { api } from "@/src/services/api";

const BASE_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

// ── Palette café/marron pour rester fidèle au visuel généré ─────────
const CAFE = {
  bg: "#1B0F08",
  surface: "#2E1A10",
  surfaceElevated: "#3E2417",
  cream: "#F5E6D3",
  creamSoft: "#DECDB4",
  gold: "#D7A86E",
  goldBright: "#F0C382",
  muted: "#A8947A",
  border: "#4E3426",
};

type Captions = { linkedin: string; facebook: string; instagram: string };
type Day = {
  n: number;
  title: string;
  publish_date: string; // YYYY-MM-DD
  visual_url: string;
  captions: Captions;
  status: "past" | "today" | "future";
  days_until_publish: number;
};

type ListResponse = {
  j_zero_date: string;
  today: string;
  today_day: number | null;
  campaign_active: boolean;
  days: Day[];
};

type Platform = "linkedin" | "facebook";

const PLATFORM_META: Record<
  Platform,
  { label: string; icon: any; color: string; short: string }
> = {
  linkedin: { label: "COPIER POUR LINKEDIN", icon: "logo-linkedin", color: "#0A66C2", short: "LinkedIn" },
  facebook: { label: "COPIER POUR FACEBOOK", icon: "logo-facebook", color: "#1877F2", short: "Facebook" },
};

/** Format court FR : « lun. 13 juil. » */
function fmtDate(iso: string): string {
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString("fr-FR", {
    weekday: "short",
    day: "2-digit",
    month: "short",
  });
}

/** ADMIN — Campagne countdown "Jeton Café" 30 jours (J-30 → Jour J).
 *  L'admin voit chaque jour le visuel + 3 captions (LinkedIn/FB/IG) à copier
 *  puis publier manuellement.
 */
export default function AdminCountdown() {
  const router = useRouter();
  const [data, setData] = useState<ListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedN, setSelectedN] = useState<number | null>(null);
  const [copied, setCopied] = useState<Platform | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const fetchAll = useCallback(async () => {
    try {
      const res = await api.get<ListResponse>("/campaign/countdown/list");
      setData(res.data);
    } catch (e: any) {
      setMessage(
        `⚠️ ${
          e?.response?.data?.detail ||
          "Impossible de charger la campagne. Assurez-vous d'avoir lancé build_countdown_campaign.py."
        }`,
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchAll();
  }, [fetchAll]);

  // Sélection par défaut : le jour "today", ou le prochain à venir si pas
  // encore commencé, ou le dernier passé si campagne terminée.
  const effectiveN = useMemo(() => {
    if (selectedN !== null) return selectedN;
    if (!data) return null;
    if (data.today_day !== null) return data.today_day;
    // hors fenêtre : montrer J-30 avant début, ou J-0 après fin
    const j0 = new Date(data.j_zero_date + "T00:00:00");
    const today = new Date(data.today + "T00:00:00");
    return today < j0 ? 30 : 0;
  }, [data, selectedN]);

  const shown = useMemo<Day | null>(() => {
    if (!data || effectiveN === null) return null;
    return data.days.find((d) => d.n === effectiveN) ?? null;
  }, [data, effectiveN]);

  const isTodayView = shown && data && shown.n === data.today_day;

  const copyCaption = async (platform: Platform) => {
    if (!shown) return;
    await Clipboard.setStringAsync(shown.captions[platform]);
    setCopied(platform);
    setTimeout(() => setCopied(null), 2500);
  };

  const openZip = async () => {
    // Le ZIP est protégé (require_platform_owner). On l'ouvre via api en
    // laissant le navigateur/Safari le télécharger. Sur mobile, il est plus
    // simple d'informer l'utilisateur de la commande curl (dev), sinon
    // Linking vers l'URL avec token en query. Ici : Linking basique.
    const { Linking } = await import("react-native");
    Linking.openURL(`${BASE_URL}/api/campaign/countdown/zip`);
  };

  // ── Compteur global de progression : X/31 posts publiés (past + today)
  const progress = useMemo(() => {
    if (!data) return { done: 0, total: 31 };
    const done = data.days.filter((d) => d.status === "past").length;
    return { done, total: data.days.length };
  }, [data]);

  return (
    <SafeAreaView style={styles.flex} edges={["top", "bottom"]}>
      <View style={styles.topBar}>
        <TouchableOpacity
          testID="countdown-back-button"
          onPress={() => router.back()}
          hitSlop={10}
        >
          <Ionicons name="arrow-back" size={22} color={CAFE.cream} />
        </TouchableOpacity>
        <Text style={styles.topTitle}>☕ CAMPAGNE JETON CAFÉ</Text>
        <TouchableOpacity
          testID="countdown-refresh-button"
          onPress={() => void fetchAll()}
          hitSlop={10}
        >
          <Ionicons name="refresh" size={20} color={CAFE.gold} />
        </TouchableOpacity>
      </View>

      {loading || !data ? (
        <ActivityIndicator color={CAFE.gold} style={{ marginTop: 60 }} />
      ) : (
        <ScrollView contentContainerStyle={styles.scroll}>
          {/* Bandeau info Jour J */}
          <View style={styles.jourJBox}>
            <Text style={styles.jourJLabel}>JOUR J</Text>
            <Text style={styles.jourJDate}>{fmtDate(data.j_zero_date)}</Text>
            {data.today_day !== null ? (
              <Text style={styles.jourJHint}>
                Aujourd&apos;hui : publier J-{data.today_day}
              </Text>
            ) : (
              <Text style={styles.jourJHint}>
                {new Date(data.today) < new Date(data.j_zero_date)
                  ? `Campagne démarre dans ${Math.max(
                      1,
                      Math.ceil(
                        (new Date(data.j_zero_date).getTime() -
                          new Date(data.today).getTime()) /
                          86_400_000,
                      ) - 30,
                    )} jour(s)`
                  : "Campagne terminée 🎉"}
              </Text>
            )}
          </View>

          {/* Progression */}
          <View style={styles.progressRow}>
            <Text style={styles.progressText}>
              {progress.done}/{progress.total} jours écoulés
            </Text>
            <View style={styles.progressTrack}>
              <View
                style={[
                  styles.progressFill,
                  { width: `${(progress.done / progress.total) * 100}%` },
                ]}
              />
            </View>
          </View>

          {/* Zone actions globales */}
          <TouchableOpacity
            testID="countdown-download-zip"
            style={styles.zipBtn}
            onPress={() => void openZip()}
            activeOpacity={0.85}
          >
            <Ionicons name="download-outline" size={18} color={CAFE.bg} />
            <Text style={styles.zipBtnText}>
              TÉLÉCHARGER LE ZIP COMPLET (31 VISUELS)
            </Text>
          </TouchableOpacity>

          {/* Bloc du jour sélectionné */}
          {shown && (
            <>
              {!isTodayView && (
                <TouchableOpacity
                  testID="countdown-back-to-today"
                  style={styles.consultBanner}
                  onPress={() => setSelectedN(null)}
                  activeOpacity={0.8}
                >
                  <Ionicons name="eye-outline" size={16} color={CAFE.goldBright} />
                  <Text style={styles.consultText}>
                    Consultation de J-{shown.n} — toucher pour revenir au jour
                    actif
                  </Text>
                </TouchableOpacity>
              )}

              <View style={styles.dayBadge}>
                <Text style={styles.dayBadgeText}>
                  {shown.n === 0 ? "JOUR J" : `J-${shown.n}`} ·{" "}
                  {fmtDate(shown.publish_date)}
                </Text>
              </View>

              <Text style={styles.title} testID="countdown-title">
                {shown.title}
              </Text>

              {/* Visuel */}
              <Image
                testID="countdown-visual"
                source={{ uri: `${BASE_URL}/api/campaign/countdown/visual/${shown.n}` }}
                style={styles.visual}
                resizeMode="contain"
              />
              <Text style={styles.hint}>
                📲 Appui long sur l&apos;image → « Enregistrer l&apos;image »,
                puis attachez-la au post sur chaque réseau.
              </Text>

              {/* Boutons plateformes */}
              {(["linkedin", "facebook"] as Platform[]).map((p) => {
                const meta = PLATFORM_META[p];
                const isCopied = copied === p;
                return (
                  <View key={p} style={styles.platformBlock}>
                    <View style={styles.platformHeader}>
                      <Ionicons name={meta.icon} size={16} color={meta.color} />
                      <Text style={styles.platformLabel}>{meta.short}</Text>
                    </View>
                    <View style={styles.textBox}>
                      <Text
                        style={styles.postText}
                        testID={`countdown-caption-${p}`}
                      >
                        {shown.captions[p]}
                      </Text>
                    </View>
                    <TouchableOpacity
                      testID={`countdown-copy-${p}`}
                      style={[
                        styles.copyBtn,
                        { backgroundColor: meta.color },
                        isCopied && styles.copyBtnOk,
                      ]}
                      onPress={() => void copyCaption(p)}
                      activeOpacity={0.85}
                    >
                      <Ionicons
                        name={isCopied ? "checkmark-circle" : meta.icon}
                        size={18}
                        color="#fff"
                      />
                      <Text style={styles.copyBtnText}>
                        {isCopied ? "COPIÉ ! COLLEZ DANS L'APP" : meta.label}
                      </Text>
                    </TouchableOpacity>
                  </View>
                );
              })}
            </>
          )}

          {!!message && (
            <Text style={styles.message} testID="countdown-message">
              {message}
            </Text>
          )}

          {/* Aperçu des 31 jours */}
          <Text style={styles.listHeader}>
            LES 31 JOURS — touchez pour consulter
          </Text>
          {data.days.map((d) => {
            const isSel = effectiveN === d.n;
            const dot =
              d.status === "past"
                ? "checkmark-circle"
                : d.status === "today"
                  ? "radio-button-on"
                  : "ellipse-outline";
            const dotColor =
              d.status === "past"
                ? "#22C55E"
                : d.status === "today"
                  ? CAFE.goldBright
                  : CAFE.border;
            return (
              <TouchableOpacity
                key={d.n}
                testID={`countdown-row-${d.n}`}
                style={[
                  styles.row,
                  isSel && {
                    borderWidth: 1.5,
                    borderColor: CAFE.goldBright,
                  },
                  d.status === "today" && !isSel && {
                    backgroundColor: CAFE.surfaceElevated,
                  },
                ]}
                onPress={() => {
                  setSelectedN(d.n === data.today_day ? null : d.n);
                  setCopied(null);
                }}
                activeOpacity={0.7}
              >
                <Text
                  style={[
                    styles.rowDay,
                    d.status === "today" && { color: CAFE.goldBright },
                  ]}
                >
                  {d.n === 0 ? "J0" : `J${d.n}`}
                </Text>
                <View style={styles.rowMain}>
                  <Text style={styles.rowTitle} numberOfLines={1}>
                    {d.title}
                  </Text>
                  <Text style={styles.rowDate}>{fmtDate(d.publish_date)}</Text>
                </View>
                <Ionicons name={dot as any} size={18} color={dotColor} />
              </TouchableOpacity>
            );
          })}
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: CAFE.bg },
  topBar: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: CAFE.border,
    backgroundColor: CAFE.surface,
  },
  topTitle: { color: CAFE.cream, fontSize: 14, fontWeight: "800", letterSpacing: 0.5 },
  scroll: { padding: 16, paddingBottom: 48 },

  jourJBox: {
    backgroundColor: CAFE.surface,
    borderRadius: 14,
    padding: 14,
    borderWidth: 1,
    borderColor: CAFE.border,
    marginBottom: 12,
  },
  jourJLabel: { color: CAFE.goldBright, fontSize: 11, fontWeight: "800", letterSpacing: 1 },
  jourJDate: { color: CAFE.cream, fontSize: 20, fontWeight: "800", marginTop: 2 },
  jourJHint: { color: CAFE.muted, fontSize: 12.5, marginTop: 4 },

  progressRow: { marginBottom: 14 },
  progressText: {
    color: CAFE.creamSoft,
    fontSize: 12.5,
    marginBottom: 6,
    fontWeight: "600",
  },
  progressTrack: {
    height: 8,
    borderRadius: 4,
    backgroundColor: CAFE.surfaceElevated,
    overflow: "hidden",
  },
  progressFill: { height: 8, backgroundColor: CAFE.gold },

  zipBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    backgroundColor: CAFE.goldBright,
    borderRadius: 24,
    paddingVertical: 13,
    marginBottom: 20,
  },
  zipBtnText: { color: CAFE.bg, fontWeight: "800", fontSize: 12.5, letterSpacing: 0.3 },

  consultBanner: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    backgroundColor: "rgba(240,195,130,0.12)",
    borderRadius: 10,
    padding: 10,
    marginBottom: 12,
  },
  consultText: { color: CAFE.goldBright, fontSize: 12, flex: 1 },

  dayBadge: {
    alignSelf: "flex-start",
    backgroundColor: CAFE.gold,
    borderRadius: 14,
    paddingHorizontal: 12,
    paddingVertical: 5,
    marginBottom: 10,
  },
  dayBadgeText: { color: CAFE.bg, fontWeight: "800", fontSize: 12 },

  title: { color: CAFE.cream, fontSize: 22, fontWeight: "800" },
  visual: {
    width: "100%",
    aspectRatio: 1,
    borderRadius: 14,
    marginTop: 14,
    backgroundColor: CAFE.surface,
  },
  hint: {
    color: CAFE.muted,
    fontSize: 11.5,
    marginTop: 8,
    textAlign: "center",
  },

  platformBlock: { marginTop: 20 },
  platformHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    marginBottom: 6,
  },
  platformLabel: { color: CAFE.creamSoft, fontSize: 12, fontWeight: "700", letterSpacing: 0.5 },
  textBox: {
    backgroundColor: CAFE.surface,
    borderRadius: 12,
    padding: 12,
    borderWidth: 1,
    borderColor: CAFE.border,
  },
  postText: { color: CAFE.cream, fontSize: 13.5, lineHeight: 20 },

  copyBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    borderRadius: 24,
    paddingVertical: 13,
    marginTop: 10,
  },
  copyBtnOk: { backgroundColor: "#16A34A" },
  copyBtnText: { color: "#fff", fontWeight: "800", fontSize: 12.5 },

  message: {
    color: CAFE.muted,
    fontSize: 12.5,
    textAlign: "center",
    marginTop: 14,
  },

  listHeader: {
    color: CAFE.creamSoft,
    fontSize: 12,
    fontWeight: "800",
    letterSpacing: 1,
    marginTop: 26,
    marginBottom: 8,
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    backgroundColor: CAFE.surface,
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    marginBottom: 6,
    borderWidth: 1,
    borderColor: CAFE.border,
  },
  rowDay: {
    color: CAFE.gold,
    fontWeight: "800",
    width: 40,
    fontSize: 12.5,
  },
  rowMain: { flex: 1 },
  rowTitle: { color: CAFE.cream, fontSize: 13.5, fontWeight: "600" },
  rowDate: { color: CAFE.muted, fontSize: 11, marginTop: 2 },
});
