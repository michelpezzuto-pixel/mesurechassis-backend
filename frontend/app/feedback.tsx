/**
 * /feedback — Page unique de feedback :
 *   • Pour TOUS les rôles : panneau dépliable « Nouveau message » +
 *     historique des retours.
 *   • Admin → voit tous les retours de la société + peut supprimer + mailto.
 *   • Commercial/Technicien → voit uniquement ses propres retours.
 *
 * À la soumission, POST /feedbacks → email envoyé à info@mesurechassis.com
 * via Resend + l'entrée est ajoutée au tableau immédiatement (optimistic UI).
 */
import React, { useCallback, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  KeyboardAvoidingView,
  LayoutAnimation,
  Linking,
  Platform,
  RefreshControl,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  UIManager,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useFocusEffect, usePathname, useRouter } from "expo-router";
import { useTranslation } from "react-i18next";
import { api } from "@/src/services/api";
import { useAuth } from "@/src/context/AuthContext";
import { colors } from "@/src/theme";

if (
  Platform.OS === "android" &&
  UIManager.setLayoutAnimationEnabledExperimental
) {
  UIManager.setLayoutAnimationEnabledExperimental(true);
}

type Feedback = {
  id: string;
  user_id: string;
  user_email?: string;
  user_name?: string;
  user_comment: string;
  page_context?: string | null;
  created_at: string;
};

function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString("fr-FR", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export default function FeedbackPage() {
  const router = useRouter();
  const pathname = usePathname();
  const { t } = useTranslation();
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  const [items, setItems] = useState<Feedback[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [composerOpen, setComposerOpen] = useState(false);
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Admin → tous les feedbacks de la société. Sinon → feedbacks perso.
  const endpoint = isAdmin ? "/feedbacks" : "/feedbacks/mine";

  const fetchItems = useCallback(async () => {
    try {
      const res = await api.get<Feedback[]>(endpoint);
      setItems(res.data || []);
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [endpoint]);

  useFocusEffect(
    useCallback(() => {
      fetchItems();
    }, [fetchItems]),
  );

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchItems();
  }, [fetchItems]);

  const toggleComposer = useCallback(() => {
    LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
    setComposerOpen((v) => !v);
  }, []);

  const submit = useCallback(async () => {
    const trimmed = comment.trim();
    if (trimmed.length < 5) {
      Alert.alert(
        "Message trop court",
        "Merci de rédiger au moins quelques mots pour expliquer votre retour.",
      );
      return;
    }
    setSubmitting(true);
    try {
      await api.post("/feedbacks", {
        user_comment: trimmed,
        page_context: pathname || "/feedback",
      });
      setComment("");
      setComposerOpen(false);
      // Rafraîchir la liste immédiatement
      await fetchItems();
      Alert.alert(
        "✅ Merci pour votre retour",
        "Votre message a été transmis à l'équipe MesureChâssis. Une copie est conservée ci-dessous.",
      );
    } catch (e: any) {
      Alert.alert(
        "Envoi impossible",
        e?.response?.data?.detail ||
          "Impossible d'envoyer votre retour. Vérifiez votre connexion.",
      );
    } finally {
      setSubmitting(false);
    }
  }, [comment, pathname, fetchItems]);

  /** Admin uniquement — ouvre l'app mail pré-remplie pour répondre. */
  const replyByMail = useCallback(async (fb: Feedback) => {
    if (!fb.user_email) return;
    const subject = encodeURIComponent("Re: Votre retour MesureChâssis");
    const quote = (fb.user_comment || "")
      .split("\n")
      .map((l) => `> ${l}`)
      .join("\n");
    const body = encodeURIComponent(
      `Bonjour,\n\nMerci pour votre retour concernant MesureChâssis.\n\n` +
        `Votre message :\n${quote}\n\n` +
        `Notre réponse :\n[Tapez ici votre réponse]\n\n` +
        `Cordialement,\nL'équipe MesureChâssis`,
    );
    const url = `mailto:${fb.user_email}?subject=${subject}&body=${body}`;
    try {
      const ok = await Linking.canOpenURL(url);
      if (!ok) {
        Alert.alert(
          "Aucune app mail trouvée",
          `Envoyez votre réponse à ${fb.user_email}`,
        );
        return;
      }
      await Linking.openURL(url);
    } catch {
      Alert.alert("Erreur", "Impossible d'ouvrir l'app mail.");
    }
  }, []);

  const removeFb = useCallback(
    async (id: string) => {
      Alert.alert("Supprimer", "Supprimer ce retour ?", [
        { text: "Annuler", style: "cancel" },
        {
          text: "Supprimer",
          style: "destructive",
          onPress: async () => {
            try {
              await api.delete(`/feedbacks/${id}`);
              setItems((s) => s.filter((f) => f.id !== id));
            } catch {
              Alert.alert("Erreur", "Suppression impossible.");
            }
          },
        },
      ]);
    },
    [],
  );

  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      {/* Header */}
      <View style={styles.topBar}>
        <TouchableOpacity
          onPress={() => router.back()}
          style={styles.backBtn}
          hitSlop={8}
        >
          <Ionicons name="chevron-back" size={22} color={colors.textPrimary} />
        </TouchableOpacity>
        <View style={{ flex: 1 }}>
          <Text style={styles.title}>{t("dashboardExtended.feedback")}</Text>
          <Text style={styles.subtitle}>
            {isAdmin
              ? "Tous les retours de votre société"
              : t("screens.feedback.subtitle")}
          </Text>
        </View>
      </View>

      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        style={{ flex: 1 }}
        keyboardVerticalOffset={Platform.OS === "ios" ? 64 : 0}
      >
        {/* === Composer dépliable (Nouveau message) === */}
        <View style={styles.composerWrap}>
          <TouchableOpacity
            testID="composer-toggle"
            onPress={toggleComposer}
            activeOpacity={0.85}
            style={[
              styles.composerHeader,
              composerOpen && styles.composerHeaderOpen,
            ]}
          >
            <View style={{ flexDirection: "row", alignItems: "center", gap: 10 }}>
              <View style={styles.composerIcon}>
                <Ionicons
                  name={composerOpen ? "create" : "create-outline"}
                  size={16}
                  color="#000"
                />
              </View>
              <View>
                <Text style={styles.composerTitle}>{t("screens.feedback.newFeedback")}</Text>
                <Text style={styles.composerHint}>
                  {t("screens.feedback.newFeedbackHint")}
                </Text>
              </View>
            </View>
            <Ionicons
              name={composerOpen ? "chevron-up" : "chevron-down"}
              size={20}
              color={colors.textSecondary}
            />
          </TouchableOpacity>

          {composerOpen && (
            <View style={styles.composerBody}>
              <TextInput
                testID="composer-textarea"
                value={comment}
                onChangeText={setComment}
                placeholder={t("screens.feedback.messagePlaceholder")}
                placeholderTextColor={colors.placeholder}
                multiline
                numberOfLines={6}
                textAlignVertical="top"
                style={styles.textarea}
                maxLength={2000}
              />
              <View style={styles.composerFooter}>
                <Text style={styles.charCount}>
                  {comment.trim().length}/2000
                </Text>
                <TouchableOpacity
                  testID="composer-submit"
                  onPress={submit}
                  disabled={submitting}
                  activeOpacity={0.85}
                  style={[
                    styles.submitBtn,
                    submitting && { opacity: 0.6 },
                  ]}
                >
                  {submitting ? (
                    <ActivityIndicator color="#000" />
                  ) : (
                    <>
                      <Ionicons name="send" size={16} color="#000" />
                      <Text style={styles.submitText}>{t("screens.feedback.send")}</Text>
                    </>
                  )}
                </TouchableOpacity>
              </View>
            </View>
          )}
        </View>

        {/* === Liste === */}
        {loading ? (
          <View style={styles.center}>
            <ActivityIndicator color={colors.primary} />
          </View>
        ) : items.length === 0 ? (
          <View style={[styles.center, { padding: 28 }]}>
            <Ionicons
              name="chatbubble-ellipses-outline"
              size={48}
              color={colors.textSecondary}
            />
            <Text style={styles.emptyTitle}>
              {t("screens.feedback.emptyTitle")}
            </Text>
            <Text style={styles.emptyText}>
              {t("screens.feedback.emptyText")}
            </Text>
          </View>
        ) : (
          <FlatList
            data={items}
            keyExtractor={(item) => item.id}
            contentContainerStyle={styles.listContent}
            refreshControl={
              <RefreshControl
                refreshing={refreshing}
                onRefresh={onRefresh}
                tintColor={colors.primary}
              />
            }
            ItemSeparatorComponent={() => <View style={{ height: 10 }} />}
            renderItem={({ item }) => (
              <View style={styles.card}>
                <View style={styles.cardHeader}>
                  {isAdmin ? (
                    <View style={{ flex: 1 }}>
                      <Text style={styles.cardAuthor} numberOfLines={1}>
                        {item.user_name || t("screens.feedback.user")}
                      </Text>
                      <Text style={styles.cardAuthorEmail} numberOfLines={1}>
                        {item.user_email || "—"}
                      </Text>
                    </View>
                  ) : (
                    <View style={styles.statusPill}>
                      <Ionicons
                        name="checkmark-circle"
                        size={12}
                        color="#16A34A"
                      />
                      <Text style={styles.statusText}>{t("screens.feedback.sent")}</Text>
                    </View>
                  )}
                  <Text style={styles.cardDate}>
                    {formatDate(item.created_at)}
                  </Text>
                </View>
                <Text style={styles.cardComment}>{item.user_comment}</Text>
                {item.page_context ? (
                  <Text style={styles.cardContext}>
                    {t("screens.feedback.from")} :{" "}
                    <Text style={styles.mono}>{item.page_context}</Text>
                  </Text>
                ) : null}
                {isAdmin && item.user_email && (
                  <View style={styles.adminActions}>
                    <TouchableOpacity
                      onPress={() => replyByMail(item)}
                      style={styles.replyBtn}
                      activeOpacity={0.85}
                    >
                      <Ionicons name="mail" size={14} color="#000" />
                      <Text style={styles.replyBtnText}>{t("screens.feedback.replyMail")}</Text>
                    </TouchableOpacity>
                    <TouchableOpacity
                      onPress={() => removeFb(item.id)}
                      style={styles.deleteBtn}
                      activeOpacity={0.85}
                    >
                      <Ionicons name="trash" size={14} color="#fff" />
                      <Text style={styles.deleteBtnText}>SUPPRIMER</Text>
                    </TouchableOpacity>
                  </View>
                )}
              </View>
            )}
          />
        )}
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  topBar: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 12,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSubtle,
  },
  backBtn: {
    width: 40,
    height: 40,
    alignItems: "center",
    justifyContent: "center",
  },
  title: {
    color: colors.textPrimary,
    fontSize: 17,
    fontWeight: "900",
    letterSpacing: 0.3,
  },
  subtitle: {
    color: colors.textSecondary,
    fontSize: 12,
    marginTop: 2,
  },
  // Composer
  composerWrap: {
    margin: 16,
    backgroundColor: colors.surface,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    overflow: "hidden",
  },
  composerHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 14,
    paddingVertical: 14,
  },
  composerHeaderOpen: {
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSubtle,
  },
  composerIcon: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
  },
  composerTitle: {
    color: colors.textPrimary,
    fontWeight: "900",
    letterSpacing: 0.8,
    fontSize: 13,
  },
  composerHint: {
    color: colors.textSecondary,
    fontSize: 11,
    marginTop: 1,
  },
  composerBody: {
    paddingHorizontal: 14,
    paddingTop: 12,
    paddingBottom: 14,
  },
  textarea: {
    minHeight: 120,
    color: colors.textPrimary,
    fontSize: 14,
    lineHeight: 19,
    backgroundColor: colors.bg,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    borderRadius: 10,
    padding: 12,
  },
  composerFooter: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginTop: 10,
  },
  charCount: {
    color: colors.textSecondary,
    fontSize: 11,
  },
  submitBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    backgroundColor: colors.primary,
    borderRadius: 10,
    paddingHorizontal: 18,
    paddingVertical: 11,
  },
  submitText: {
    color: "#000",
    fontWeight: "900",
    letterSpacing: 0.8,
    fontSize: 12,
  },
  // List
  listContent: { paddingHorizontal: 16, paddingBottom: 32 },
  card: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: 14,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
  },
  cardHeader: {
    flexDirection: "row",
    alignItems: "flex-start",
    justifyContent: "space-between",
    marginBottom: 8,
    gap: 10,
  },
  cardAuthor: {
    color: colors.textPrimary,
    fontWeight: "800",
    fontSize: 13,
  },
  cardAuthorEmail: {
    color: colors.textSecondary,
    fontSize: 11,
    marginTop: 1,
  },
  statusPill: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    backgroundColor: "rgba(22, 163, 74, 0.15)",
    borderRadius: 4,
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
  statusText: {
    color: "#16A34A",
    fontSize: 10,
    fontWeight: "900",
    letterSpacing: 0.8,
  },
  cardDate: {
    color: colors.textSecondary,
    fontSize: 11,
    fontWeight: "600",
  },
  cardComment: {
    color: colors.textPrimary,
    fontSize: 14,
    lineHeight: 20,
  },
  cardContext: {
    color: colors.textSecondary,
    fontSize: 11,
    marginTop: 8,
  },
  mono: {
    fontFamily: "monospace",
    color: colors.primary,
  },
  emptyTitle: {
    color: colors.textPrimary,
    fontSize: 16,
    fontWeight: "800",
    marginTop: 12,
  },
  emptyText: {
    color: colors.textSecondary,
    fontSize: 13,
    textAlign: "center",
    marginTop: 8,
    lineHeight: 19,
    maxWidth: 340,
  },
  adminActions: {
    flexDirection: "row",
    gap: 8,
    marginTop: 12,
    flexWrap: "wrap",
  },
  replyBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    backgroundColor: colors.primary,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 6,
  },
  replyBtnText: {
    color: "#000",
    fontWeight: "900",
    letterSpacing: 0.4,
    fontSize: 11,
  },
  deleteBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    backgroundColor: colors.anomaly,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 6,
  },
  deleteBtnText: {
    color: "#fff",
    fontWeight: "800",
    letterSpacing: 0.4,
    fontSize: 11,
  },
});
