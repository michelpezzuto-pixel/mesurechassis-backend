import React, { useCallback, useEffect, useState } from "react";
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
import { colors } from "@/src/theme";

const BASE_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

type Post = {
  day: number;
  title: string;
  subtitle: string;
  text: string;
  hashtags: string;
  fb_hashtags: string;
  posted?: boolean;
  image_url?: string;
};

type Today = {
  total: number;
  posted_count: number;
  done: boolean;
  post: Post | null;
  image_url: string | null;
};

/** Vue ADMIN : campagne LinkedIn 15 jours — post du jour à copier en 1 clic. */
export default function AdminLinkedin() {
  const router = useRouter();
  const [today, setToday] = useState<Today | null>(null);
  const [allPosts, setAllPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState<"li" | "fb" | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [marking, setMarking] = useState(false);
  // Consultation d'un jour précis (ex: rattrapage Facebook d'un post déjà publié)
  const [selectedDay, setSelectedDay] = useState<number | null>(null);

  const fetchAll = useCallback(async () => {
    try {
      const [t, p] = await Promise.all([
        api.get<Today>("/linkedin/today"),
        api.get<{ posts: Post[] }>("/linkedin/posts"),
      ]);
      setToday(t.data);
      setAllPosts(p.data.posts);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchAll();
  }, [fetchAll]);

  // Post affiché : celui sélectionné dans la liste, sinon le post du jour
  const shown: Post | null = selectedDay
    ? (allPosts.find((p) => p.day === selectedDay) ?? null)
    : (today?.post ?? null);
  const isConsultation = !!selectedDay && selectedDay !== today?.post?.day;

  const copyText = async (target: "li" | "fb") => {
    if (!shown) return;
    const tags = target === "fb" ? shown.fb_hashtags : shown.hashtags;
    await Clipboard.setStringAsync(`${shown.text}\n\n${tags}`);
    setCopied(target);
    setTimeout(() => setCopied(null), 2500);
  };

  const markPosted = async () => {
    if (!today?.post || marking) return;
    // 1er appui = demande de confirmation ; 2e appui = validation.
    if (!confirming) {
      setConfirming(true);
      setTimeout(() => setConfirming(false), 4000);
      return;
    }
    setConfirming(false);
    setMarking(true);
    try {
      await api.post("/linkedin/mark-posted", { day: today.post.day });
      setMessage(`✅ Jour ${today.post.day} publié — à demain !`);
      await fetchAll();
    } catch (e: any) {
      setMessage(`⚠️ ${e?.response?.data?.detail || "Erreur"}`);
    } finally {
      setMarking(false);
    }
  };

  return (
    <SafeAreaView style={styles.flex} edges={["top", "bottom"]}>
      <View style={styles.topBar}>
        <TouchableOpacity
          testID="linkedin-back-button"
          onPress={() => router.back()}
          hitSlop={10}
        >
          <Ionicons name="arrow-back" size={22} color={colors.textPrimary} />
        </TouchableOpacity>
        <Text style={styles.topTitle}>💼 CAMPAGNE LINKEDIN</Text>
        <TouchableOpacity
          testID="linkedin-refresh-button"
          onPress={() => void fetchAll()}
          hitSlop={10}
        >
          <Ionicons name="refresh" size={20} color={colors.primary} />
        </TouchableOpacity>
      </View>

      {loading || !today ? (
        <ActivityIndicator color={colors.primary} style={{ marginTop: 60 }} />
      ) : (
        <ScrollView contentContainerStyle={styles.scroll}>
          {/* Progression */}
          <View style={styles.progressRow} testID="linkedin-progress">
            <Text style={styles.progressText}>
              {today.posted_count}/{today.total} posts publiés
            </Text>
            <View style={styles.progressTrack}>
              <View
                style={[
                  styles.progressFill,
                  { width: `${(today.posted_count / today.total) * 100}%` },
                ]}
              />
            </View>
          </View>

          {today.done && !isConsultation ? (
            <View style={styles.doneBox} testID="linkedin-done">
              <Text style={styles.doneEmoji}>🏆</Text>
              <Text style={styles.doneText}>
                Campagne terminée ! Les 15 posts sont publiés. Bravo Michel !
              </Text>
            </View>
          ) : (
            shown && (
              <>
                {isConsultation && (
                  <TouchableOpacity
                    testID="linkedin-back-to-today"
                    style={styles.consultBanner}
                    onPress={() => setSelectedDay(null)}
                    activeOpacity={0.8}
                  >
                    <Ionicons name="eye-outline" size={16} color="#60A5FA" />
                    <Text style={styles.consultText}>
                      Consultation du Jour {shown.day} — toucher ici pour
                      revenir au post du jour
                    </Text>
                  </TouchableOpacity>
                )}
                <View style={styles.dayBadge}>
                  <Text style={styles.dayBadgeText}>
                    JOUR {shown.day}/{today.total}
                  </Text>
                </View>
                <Text style={styles.title} testID="linkedin-post-title">
                  {shown.title}
                </Text>
                <Text style={styles.subtitle}>{shown.subtitle}</Text>

                {/* Visuel — appui long pour enregistrer sur iPhone */}
                <Image
                  testID="linkedin-post-image"
                  source={{ uri: `${BASE_URL}/api/linkedin/image/${shown.day}` }}
                  style={styles.visual}
                  resizeMode="contain"
                />
                <Text style={styles.hint}>
                  📲 Appui long sur l&apos;image → « Enregistrer l&apos;image »,
                  puis attachez-la à votre post LinkedIn
                </Text>

                {/* Texte du post */}
                <View style={styles.textBox}>
                  <Text style={styles.postText} testID="linkedin-post-text">
                    {shown.text}
                  </Text>
                  <Text style={styles.hashtags}>{shown.hashtags}</Text>
                </View>

                <TouchableOpacity
                  testID="linkedin-copy-button"
                  style={[styles.copyBtn, copied === "li" && styles.copyBtnOk]}
                  onPress={() => void copyText("li")}
                  activeOpacity={0.8}
                >
                  <Ionicons
                    name={copied === "li" ? "checkmark-circle" : "logo-linkedin"}
                    size={20}
                    color="#fff"
                  />
                  <Text style={styles.copyBtnText}>
                    {copied === "li"
                      ? "COPIÉ ! COLLEZ DANS LINKEDIN"
                      : "COPIER POUR LINKEDIN"}
                  </Text>
                </TouchableOpacity>

                <TouchableOpacity
                  testID="facebook-copy-button"
                  style={[
                    styles.copyBtn,
                    styles.fbBtn,
                    copied === "fb" && styles.copyBtnOk,
                  ]}
                  onPress={() => void copyText("fb")}
                  activeOpacity={0.8}
                >
                  <Ionicons
                    name={copied === "fb" ? "checkmark-circle" : "logo-facebook"}
                    size={20}
                    color="#fff"
                  />
                  <Text style={styles.copyBtnText}>
                    {copied === "fb"
                      ? "COPIÉ ! COLLEZ DANS FACEBOOK"
                      : "COPIER POUR FACEBOOK"}
                  </Text>
                </TouchableOpacity>

                {/* Marquage publié uniquement pour le post du jour (pas en consultation) */}
                {!isConsultation && (
                  <TouchableOpacity
                    testID="linkedin-mark-posted-button"
                    style={[
                      styles.postedBtn,
                      confirming && { backgroundColor: colors.primary },
                      marking && { opacity: 0.5 },
                    ]}
                    onPress={() => void markPosted()}
                    disabled={marking}
                    activeOpacity={0.8}
                  >
                    <Ionicons
                      name={confirming ? "alert-circle" : "checkmark-done"}
                      size={18}
                      color={confirming ? "#fff" : colors.primary}
                    />
                    <Text
                      style={[styles.postedBtnText, confirming && { color: "#fff" }]}
                    >
                      {marking
                        ? "..."
                        : confirming
                          ? `CONFIRMER : JOUR ${shown.day} PUBLIÉ ?`
                          : "MARQUER COMME PUBLIÉ → POST SUIVANT"}
                    </Text>
                  </TouchableOpacity>
                )}
              </>
            )
          )}

          {!!message && (
            <Text style={styles.message} testID="linkedin-message">
              {message}
            </Text>
          )}

          {/* Aperçu des 15 jours — toucher un jour pour le consulter/copier */}
          <Text style={styles.listHeader}>
            LES 15 POSTS — touchez un jour pour le revoir
          </Text>
          {allPosts.map((p) => (
            <TouchableOpacity
              key={p.day}
              style={[
                styles.row,
                selectedDay === p.day && { borderWidth: 1, borderColor: "#60A5FA" },
              ]}
              testID={`linkedin-row-${p.day}`}
              onPress={() => {
                setSelectedDay(p.day === today.post?.day ? null : p.day);
                setCopied(null);
              }}
              activeOpacity={0.7}
            >
              <Text style={[styles.rowDay, p.posted && { color: "#22C55E" }]}>
                J{p.day}
              </Text>
              <Text style={styles.rowTitle} numberOfLines={1}>
                {p.title}
              </Text>
              <Ionicons
                name={p.posted ? "checkmark-circle" : "ellipse-outline"}
                size={18}
                color={p.posted ? "#22C55E" : "#3f3f46"}
              />
            </TouchableOpacity>
          ))}
        </ScrollView>
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
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: colors.surfaceElevated,
  },
  topTitle: { color: colors.textPrimary, fontSize: 15, fontWeight: "800" },
  scroll: { padding: 16, paddingBottom: 48 },
  progressRow: { marginBottom: 18 },
  progressText: {
    color: colors.textSecondary,
    fontSize: 12.5,
    marginBottom: 6,
    fontWeight: "600",
  },
  progressTrack: {
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.surfaceElevated,
    overflow: "hidden",
  },
  progressFill: { height: 8, backgroundColor: colors.primary },
  consultBanner: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    backgroundColor: "rgba(96,165,250,0.12)",
    borderRadius: 10,
    padding: 10,
    marginBottom: 12,
  },
  consultText: { color: "#60A5FA", fontSize: 12, flex: 1 },
  dayBadge: {
    alignSelf: "flex-start",
    backgroundColor: colors.primary,
    borderRadius: 14,
    paddingHorizontal: 12,
    paddingVertical: 5,
    marginBottom: 10,
  },
  dayBadgeText: { color: "#fff", fontWeight: "800", fontSize: 12 },
  title: { color: colors.textPrimary, fontSize: 20, fontWeight: "800" },
  subtitle: { color: colors.textSecondary, fontSize: 13.5, marginTop: 4 },
  visual: {
    width: "100%",
    aspectRatio: 1,
    borderRadius: 14,
    marginTop: 14,
    backgroundColor: colors.surface,
  },
  hint: {
    color: colors.textSecondary,
    fontSize: 11.5,
    marginTop: 8,
    textAlign: "center",
  },
  textBox: {
    backgroundColor: colors.surface,
    borderRadius: 14,
    padding: 14,
    marginTop: 14,
  },
  postText: { color: colors.textPrimary, fontSize: 13.5, lineHeight: 20 },
  hashtags: { color: "#60A5FA", fontSize: 12.5, marginTop: 10 },
  copyBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    backgroundColor: "#0A66C2",
    borderRadius: 26,
    paddingVertical: 14,
    marginTop: 16,
  },
  copyBtnOk: { backgroundColor: "#16A34A" },
  fbBtn: { backgroundColor: "#1877F2", marginTop: 10 },
  copyBtnText: { color: "#fff", fontWeight: "800", fontSize: 13.5 },
  postedBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    borderWidth: 1.5,
    borderColor: colors.primary,
    borderRadius: 26,
    paddingVertical: 12,
    marginTop: 10,
  },
  postedBtnText: { color: colors.primary, fontWeight: "800", fontSize: 12.5 },
  message: {
    color: colors.textSecondary,
    fontSize: 12.5,
    textAlign: "center",
    marginTop: 12,
  },
  doneBox: {
    alignItems: "center",
    backgroundColor: colors.surface,
    borderRadius: 16,
    padding: 28,
    marginTop: 10,
  },
  doneEmoji: { fontSize: 40, marginBottom: 8 },
  doneText: {
    color: colors.textPrimary,
    fontSize: 14.5,
    textAlign: "center",
    fontWeight: "600",
  },
  listHeader: {
    color: colors.textSecondary,
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
    backgroundColor: colors.surface,
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    marginBottom: 6,
  },
  rowDay: { color: colors.textSecondary, fontWeight: "800", width: 32, fontSize: 12.5 },
  rowTitle: { color: colors.textPrimary, flex: 1, fontSize: 13 },
});
