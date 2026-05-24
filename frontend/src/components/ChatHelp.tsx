import React, { useMemo, useState, useCallback } from "react";
import {
  Modal,
  View,
  Text,
  TouchableOpacity,
  Pressable,
  ScrollView,
  StyleSheet,
  TextInput,
  Platform,
  LayoutAnimation,
  UIManager,
  KeyboardAvoidingView,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { colors } from "@/src/theme";
import faqData from "@/src/data/faq_data.json";

/**
 * Centre d'aide / FAQ — modal accordéon avec barre de recherche.
 *
 * UX :
 *  - Slide-up depuis le bas (presentationStyle "pageSheet" sur iOS, fullScreen sur Android/web)
 *  - 1 seule question ouverte à la fois (accordéon classique)
 *  - Recherche temps réel sur question ET réponse (insensible aux accents/majuscules)
 *  - Animations LayoutAnimation pour l'ouverture des panneaux
 *  - CTA "Contacter le support" en pied de modal (lance le formulaire feedback)
 *
 * Données chargées depuis `/src/data/faq_data.json` (statique, embed dans le bundle).
 */

// Activation de LayoutAnimation sur Android
if (
  Platform.OS === "android" &&
  UIManager.setLayoutAnimationEnabledExperimental
) {
  UIManager.setLayoutAnimationEnabledExperimental(true);
}

type FaqEntry = {
  id: string;
  question: string;
  answer: string;
};

type Props = {
  visible: boolean;
  onClose: () => void;
  /** Optionnel — appelé quand on touche "Contacter le support" */
  onContactSupport?: () => void;
};

/** Normalise une chaîne pour la recherche : minuscules + sans accents. */
const norm = (s: string) =>
  s
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");

export const ChatHelp: React.FC<Props> = ({
  visible,
  onClose,
  onContactSupport,
}) => {
  const [query, setQuery] = useState("");
  const [openId, setOpenId] = useState<string | null>(null);

  const entries = faqData as FaqEntry[];

  const filtered = useMemo(() => {
    const q = norm(query.trim());
    if (!q) return entries;
    return entries.filter(
      (e) => norm(e.question).includes(q) || norm(e.answer).includes(q)
    );
  }, [query, entries]);

  const toggle = useCallback((id: string) => {
    LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
    setOpenId((prev) => (prev === id ? null : id));
  }, []);

  const handleClose = () => {
    setQuery("");
    setOpenId(null);
    onClose();
  };

  return (
    <Modal
      visible={visible}
      animationType="slide"
      onRequestClose={handleClose}
      presentationStyle={Platform.OS === "ios" ? "pageSheet" : "fullScreen"}
      transparent={false}
    >
      <SafeAreaView style={styles.container} edges={["top", "bottom"]}>
        <KeyboardAvoidingView
          behavior={Platform.OS === "ios" ? "padding" : "height"}
          style={{ flex: 1 }}
        >
          {/* Header */}
          <View style={styles.header}>
            <View style={styles.headerLeft}>
              <View style={styles.headerIconWrap}>
                <Ionicons
                  name="help-circle"
                  size={22}
                  color={colors.primary}
                />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.title}>Centre d'aide</Text>
                <Text style={styles.subtitle}>
                  Questions fréquentes · MesureChâssis
                </Text>
              </View>
            </View>
            <TouchableOpacity
              testID="chat-help-close"
              onPress={handleClose}
              activeOpacity={0.7}
              style={styles.closeBtn}
              hitSlop={10}
            >
              <Ionicons name="close" size={22} color={colors.textPrimary} />
            </TouchableOpacity>
          </View>

          {/* Search bar */}
          <View style={styles.searchWrap}>
            <Ionicons
              name="search"
              size={16}
              color={colors.textSecondary}
              style={{ marginRight: 8 }}
            />
            <TextInput
              testID="chat-help-search"
              value={query}
              onChangeText={setQuery}
              placeholder="Rechercher une question…"
              placeholderTextColor={colors.placeholder}
              style={styles.searchInput}
              autoCorrect={false}
              autoCapitalize="none"
              returnKeyType="search"
              clearButtonMode="while-editing"
            />
            {query.length > 0 && Platform.OS !== "ios" && (
              <TouchableOpacity
                onPress={() => setQuery("")}
                hitSlop={10}
                style={{ paddingLeft: 4 }}
              >
                <Ionicons
                  name="close-circle"
                  size={18}
                  color={colors.textSecondary}
                />
              </TouchableOpacity>
            )}
          </View>

          {/* Liste */}
          <ScrollView
            style={styles.list}
            contentContainerStyle={styles.listContent}
            showsVerticalScrollIndicator={false}
            keyboardShouldPersistTaps="handled"
          >
            {filtered.length === 0 ? (
              <View style={styles.empty}>
                <Ionicons
                  name="search-outline"
                  size={36}
                  color={colors.textSecondary}
                />
                <Text style={styles.emptyText}>
                  Aucune question ne correspond à « {query} »
                </Text>
                <TouchableOpacity
                  onPress={() => setQuery("")}
                  style={styles.emptyClearBtn}
                  activeOpacity={0.7}
                >
                  <Text style={styles.emptyClearText}>
                    Effacer la recherche
                  </Text>
                </TouchableOpacity>
              </View>
            ) : (
              filtered.map((entry, idx) => {
                const isOpen = openId === entry.id;
                return (
                  <Pressable
                    key={entry.id}
                    testID={`faq-item-${entry.id}`}
                    onPress={() => toggle(entry.id)}
                    style={({ pressed }) => [
                      styles.item,
                      isOpen && styles.itemOpen,
                      pressed && { opacity: 0.85 },
                    ]}
                  >
                    <View style={styles.itemHeader}>
                      <View style={styles.itemNumber}>
                        <Text style={styles.itemNumberText}>{idx + 1}</Text>
                      </View>
                      <Text
                        style={[
                          styles.itemQuestion,
                          isOpen && { color: colors.primary },
                        ]}
                      >
                        {entry.question}
                      </Text>
                      <Ionicons
                        name={isOpen ? "chevron-up" : "chevron-down"}
                        size={18}
                        color={isOpen ? colors.primary : colors.textSecondary}
                      />
                    </View>
                    {isOpen && (
                      <View style={styles.itemAnswer}>
                        <View style={styles.answerBar} />
                        <Text style={styles.itemAnswerText}>
                          {entry.answer}
                        </Text>
                      </View>
                    )}
                  </Pressable>
                );
              })
            )}

            {/* Compteur en bas */}
            {filtered.length > 0 && (
              <Text style={styles.counter}>
                {filtered.length} question{filtered.length > 1 ? "s" : ""}
                {query ? " correspondante" + (filtered.length > 1 ? "s" : "") : ""}
              </Text>
            )}
          </ScrollView>

          {/* Footer — CTA support */}
          <View style={styles.footer}>
            <Text style={styles.footerHint}>Pas trouvé votre réponse ?</Text>
            <TouchableOpacity
              testID="chat-help-contact-support"
              onPress={() => {
                handleClose();
                onContactSupport?.();
              }}
              activeOpacity={0.85}
              style={styles.footerCta}
            >
              <Ionicons name="chatbubble-ellipses" size={16} color="#000" />
              <Text style={styles.footerCtaText}>CONTACTER LE SUPPORT</Text>
            </TouchableOpacity>
          </View>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </Modal>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  header: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 14,
    paddingTop: 8,
    paddingBottom: 10,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSubtle,
    gap: 8,
  },
  headerLeft: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  headerIconWrap: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.primary,
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
    fontSize: 11,
    marginTop: 1,
    letterSpacing: 0.2,
  },
  closeBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.surface,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
    borderColor: colors.borderSubtle,
  },
  searchWrap: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.surface,
    marginHorizontal: 14,
    marginTop: 12,
    paddingHorizontal: 12,
    height: 44,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
  },
  searchInput: {
    flex: 1,
    color: colors.textPrimary,
    fontSize: 14,
    padding: 0,
    margin: 0,
  },
  list: { flex: 1, marginTop: 10 },
  listContent: { paddingHorizontal: 14, paddingBottom: 30, gap: 8 },
  item: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    overflow: "hidden",
  },
  itemOpen: {
    borderColor: colors.primary,
  },
  itemHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    paddingHorizontal: 12,
    paddingVertical: 14,
    minHeight: 56,
  },
  itemNumber: {
    width: 26,
    height: 26,
    borderRadius: 13,
    backgroundColor: colors.bg,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    alignItems: "center",
    justifyContent: "center",
  },
  itemNumberText: {
    color: colors.textSecondary,
    fontSize: 11,
    fontWeight: "800",
  },
  itemQuestion: {
    flex: 1,
    color: colors.textPrimary,
    fontSize: 14,
    fontWeight: "700",
    lineHeight: 19,
  },
  itemAnswer: {
    flexDirection: "row",
    paddingHorizontal: 12,
    paddingBottom: 14,
    paddingTop: 2,
    gap: 10,
  },
  answerBar: {
    width: 3,
    backgroundColor: colors.primary,
    borderRadius: 2,
    alignSelf: "stretch",
    marginLeft: 12,
  },
  itemAnswerText: {
    flex: 1,
    color: colors.textSecondary,
    fontSize: 13,
    lineHeight: 19,
  },
  counter: {
    textAlign: "center",
    color: colors.textSecondary,
    fontSize: 11,
    marginTop: 12,
    letterSpacing: 0.3,
    opacity: 0.7,
  },
  empty: {
    alignItems: "center",
    paddingTop: 40,
    paddingHorizontal: 20,
    gap: 12,
  },
  emptyText: {
    color: colors.textSecondary,
    fontSize: 13,
    textAlign: "center",
  },
  emptyClearBtn: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.primary,
  },
  emptyClearText: {
    color: colors.primary,
    fontSize: 12,
    fontWeight: "800",
    letterSpacing: 0.4,
  },
  footer: {
    paddingHorizontal: 14,
    paddingTop: 12,
    paddingBottom: 8,
    borderTopWidth: 1,
    borderTopColor: colors.borderSubtle,
    backgroundColor: colors.surface,
    gap: 8,
  },
  footerHint: {
    color: colors.textSecondary,
    fontSize: 12,
    textAlign: "center",
  },
  footerCta: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    backgroundColor: colors.primary,
    paddingVertical: 12,
    borderRadius: 10,
  },
  footerCtaText: {
    color: "#000",
    fontSize: 13,
    fontWeight: "900",
    letterSpacing: 0.8,
  },
});

export default ChatHelp;
