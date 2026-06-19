/**
 * Yann — Écran de chat avec l'Assistant IA officiel MesureChâssis.
 *
 * Features :
 *   • Chat en plein écran avec bulles utilisateur (à droite) et Yann (à gauche)
 *   • Historique persisté côté serveur (session_id)
 *   • Suggestions de questions pour démarrer
 *   • Quota journalier visible (30 messages/jour pour le MVP)
 *   • Gestion clavier (KeyboardAvoidingView)
 *   • Réponse non-streaming pour le MVP (peut passer en SSE plus tard)
 *
 * 🍎 Conformité Apple : aucun lien externe, aucune mention de prix,
 * Yann est juste un assistant support — pas un upsell.
 */
import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  KeyboardAvoidingView,
  Platform,
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

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  ts: number;
};

const SUGGESTIONS: string[] = [
  "Comment créer mon premier chantier ?",
  "Comment fonctionne le parrainage ?",
  "Quelles sont les différences entre les formules ?",
  "Comment exporter mes mesures en PDF ?",
];

const WELCOME: string =
  "Bonjour ! 👋 Je suis **Yann**, votre assistant IA MesureChâssis. Posez-moi vos questions sur l'application, le métier ou les formules — je vous réponds en temps réel.";

export default function YannScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const listRef = useRef<FlatList<Message>>(null);

  const [messages, setMessages] = useState<Message[]>([
    { id: "welcome", role: "assistant", content: WELCOME, ts: Date.now() },
  ]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [quotaRemaining, setQuotaRemaining] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Charge le quota au montage
  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get<{ remaining: number; limit: number }>("/yann/quota");
        setQuotaRemaining(data.remaining);
      } catch {
        // silent
      }
    })();
  }, []);

  const scrollToEnd = useCallback(() => {
    setTimeout(() => listRef.current?.scrollToEnd({ animated: true }), 80);
  }, []);

  const sendMessage = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || loading) return;
      setError(null);
      setInput("");

      const userMsg: Message = {
        id: `u_${Date.now()}`,
        role: "user",
        content: trimmed,
        ts: Date.now(),
      };
      setMessages((prev) => [...prev, userMsg]);
      scrollToEnd();
      setLoading(true);

      try {
        const { data } = await api.post<{
          reply: string;
          session_id: string;
          quota_remaining: number;
        }>("/yann/chat", { message: trimmed, session_id: sessionId });

        setSessionId(data.session_id);
        setQuotaRemaining(data.quota_remaining);
        setMessages((prev) => [
          ...prev,
          {
            id: `a_${Date.now()}`,
            role: "assistant",
            content: data.reply,
            ts: Date.now(),
          },
        ]);
        scrollToEnd();
      } catch (e: any) {
        const detail =
          e?.response?.data?.detail ?? "Yann n'a pas pu répondre. Réessayez dans un instant.";
        setError(String(detail));
      } finally {
        setLoading(false);
      }
    },
    [loading, sessionId, scrollToEnd],
  );

  const renderItem = useCallback(
    ({ item }: { item: Message }) => {
      const isUser = item.role === "user";
      return (
        <View
          style={[
            styles.bubbleRow,
            isUser ? styles.bubbleRowUser : styles.bubbleRowYann,
          ]}
        >
          {!isUser && (
            <View style={styles.avatar}>
              <Text style={styles.avatarText}>Y</Text>
            </View>
          )}
          <View
            style={[
              styles.bubble,
              isUser ? styles.bubbleUser : styles.bubbleYann,
            ]}
          >
            <Text style={isUser ? styles.bubbleTextUser : styles.bubbleTextYann}>
              {item.content}
            </Text>
          </View>
        </View>
      );
    },
    [],
  );

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      {/* ─── Header ──────────────────────────────────────────────── */}
      <View style={styles.header}>
        <TouchableOpacity
          onPress={() => router.back()}
          style={styles.headerBack}
          accessibilityLabel="Retour"
        >
          <Ionicons name="chevron-back" size={24} color={colors.textPrimary} />
        </TouchableOpacity>
        <View style={styles.headerCenter}>
          <View style={styles.headerAvatar}>
            <Text style={styles.headerAvatarText}>Y</Text>
          </View>
          <View>
            <Text style={styles.headerTitle}>Yann</Text>
            <Text style={styles.headerSub}>
              Assistant IA MesureChâssis
              {quotaRemaining !== null && ` · ${quotaRemaining} msg/j restants`}
            </Text>
          </View>
        </View>
      </View>

      {/* ─── Messages ────────────────────────────────────────────── */}
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        style={{ flex: 1 }}
        keyboardVerticalOffset={Platform.OS === "ios" ? 0 : 0}
      >
        <FlatList
          ref={listRef}
          data={messages}
          keyExtractor={(it) => it.id}
          renderItem={renderItem}
          contentContainerStyle={styles.list}
          onContentSizeChange={scrollToEnd}
        />

        {/* Suggestions de démarrage (uniquement quand 1 seul message = welcome) */}
        {messages.length === 1 && (
          <View style={styles.suggestionsWrap}>
            <Text style={styles.suggestionsTitle}>Exemples de questions :</Text>
            <View style={styles.suggestionsList}>
              {SUGGESTIONS.map((s) => (
                <TouchableOpacity
                  key={s}
                  style={styles.suggestionChip}
                  onPress={() => sendMessage(s)}
                  disabled={loading}
                  activeOpacity={0.7}
                >
                  <Text style={styles.suggestionText}>{s}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        )}

        {/* Indicateur "Yann réfléchit…" */}
        {loading && (
          <View style={styles.typingRow}>
            <ActivityIndicator size="small" color={colors.primary} />
            <Text style={styles.typingText}>Yann réfléchit…</Text>
          </View>
        )}

        {/* Erreur */}
        {!!error && (
          <View style={styles.errorBox}>
            <Ionicons name="alert-circle" size={18} color="#EF4444" />
            <Text style={styles.errorText}>{error}</Text>
          </View>
        )}

        {/* ─── Composer ──────────────────────────────────────────── */}
        <View style={[styles.composer, { paddingBottom: Math.max(insets.bottom, 10) }]}>
          <TextInput
            style={styles.input}
            value={input}
            onChangeText={setInput}
            placeholder="Posez votre question à Yann…"
            placeholderTextColor={colors.textSecondary}
            multiline
            maxLength={2000}
            editable={!loading}
            onSubmitEditing={() => sendMessage(input)}
            returnKeyType="send"
            blurOnSubmit={false}
          />
          <TouchableOpacity
            style={[
              styles.sendBtn,
              (loading || !input.trim()) && styles.sendBtnDisabled,
            ]}
            onPress={() => sendMessage(input)}
            disabled={loading || !input.trim()}
            accessibilityLabel="Envoyer"
          >
            <Ionicons
              name="arrow-up"
              size={22}
              color={loading || !input.trim() ? "#666" : "#000"}
            />
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 8,
    paddingBottom: 10,
    paddingTop: 8,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  headerBack: { padding: 8 },
  headerCenter: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  headerAvatar: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
  },
  headerAvatarText: {
    color: "#000",
    fontWeight: "900",
    fontSize: 18,
  },
  headerTitle: {
    color: colors.textPrimary,
    fontSize: 17,
    fontWeight: "800",
  },
  headerSub: {
    color: colors.textSecondary,
    fontSize: 11,
    marginTop: 1,
  },
  list: {
    paddingHorizontal: 12,
    paddingVertical: 16,
    gap: 10,
  },
  bubbleRow: {
    flexDirection: "row",
    alignItems: "flex-end",
    gap: 8,
    marginBottom: 6,
  },
  bubbleRowUser: { justifyContent: "flex-end" },
  bubbleRowYann: { justifyContent: "flex-start" },
  avatar: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
  },
  avatarText: { color: "#000", fontSize: 14, fontWeight: "900" },
  bubble: {
    maxWidth: "78%",
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 16,
  },
  bubbleUser: {
    backgroundColor: colors.primary,
    borderBottomRightRadius: 4,
  },
  bubbleYann: {
    backgroundColor: colors.surface,
    borderBottomLeftRadius: 4,
    borderWidth: 1,
    borderColor: colors.border,
  },
  bubbleTextUser: {
    color: "#000",
    fontSize: 14.5,
    lineHeight: 20,
    fontWeight: "500",
  },
  bubbleTextYann: {
    color: colors.textPrimary,
    fontSize: 14.5,
    lineHeight: 20,
  },
  suggestionsWrap: {
    paddingHorizontal: 16,
    paddingBottom: 8,
  },
  suggestionsTitle: {
    color: colors.textSecondary,
    fontSize: 12,
    marginBottom: 8,
    fontWeight: "600",
  },
  suggestionsList: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 6,
  },
  suggestionChip: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 16,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  suggestionText: {
    color: colors.textPrimary,
    fontSize: 12.5,
    fontWeight: "600",
  },
  typingRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    paddingHorizontal: 16,
    paddingVertical: 6,
  },
  typingText: { color: colors.textSecondary, fontSize: 12 },
  errorBox: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginHorizontal: 16,
    marginBottom: 8,
    padding: 10,
    backgroundColor: "rgba(239, 68, 68, 0.1)",
    borderWidth: 1,
    borderColor: "rgba(239, 68, 68, 0.4)",
    borderRadius: 10,
  },
  errorText: { color: "#EF4444", fontSize: 12.5, flex: 1 },
  composer: {
    flexDirection: "row",
    gap: 8,
    paddingHorizontal: 12,
    paddingTop: 10,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    backgroundColor: colors.background,
    alignItems: "flex-end",
  },
  input: {
    flex: 1,
    color: colors.textPrimary,
    fontSize: 15,
    backgroundColor: colors.surface,
    borderRadius: 22,
    paddingHorizontal: 16,
    paddingTop: Platform.OS === "ios" ? 12 : 8,
    paddingBottom: Platform.OS === "ios" ? 12 : 8,
    maxHeight: 120,
    borderWidth: 1,
    borderColor: colors.border,
  },
  sendBtn: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
  },
  sendBtnDisabled: {
    backgroundColor: "#2a2a2f",
  },
});
