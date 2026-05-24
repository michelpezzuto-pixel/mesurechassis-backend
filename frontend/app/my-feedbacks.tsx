/**
 * /my-feedbacks — Historique des retours soumis par l'utilisateur courant.
 *
 * Accessible à tous les rôles (admin, commercial, technicien). L'utilisateur
 * voit ses propres soumissions (sujet, date, message) et peut en envoyer un
 * nouveau via le composant FeedbackButton.
 */
import React, { useCallback, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  RefreshControl,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useFocusEffect, useRouter } from "expo-router";
import { api } from "@/src/services/api";
import { colors } from "@/src/theme";
import FeedbackButton from "@/src/components/FeedbackButton";

type Feedback = {
  id: string;
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

export default function MyFeedbacks() {
  const router = useRouter();
  const [items, setItems] = useState<Feedback[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchItems = useCallback(async () => {
    try {
      const res = await api.get<Feedback[]>("/feedbacks/mine");
      setItems(res.data || []);
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      fetchItems();
    }, [fetchItems]),
  );

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchItems();
  }, [fetchItems]);

  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      {/* Header */}
      <View style={styles.topBar}>
        <TouchableOpacity
          onPress={() => router.back()}
          style={styles.backBtn}
          hitSlop={8}
        >
          <Ionicons
            name="chevron-back"
            size={22}
            color={colors.textPrimary}
          />
        </TouchableOpacity>
        <View style={{ flex: 1 }}>
          <Text style={styles.title}>Mes retours</Text>
          <Text style={styles.subtitle}>
            Historique des messages envoyés au support
          </Text>
        </View>
      </View>

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator color={colors.primary} />
        </View>
      ) : items.length === 0 ? (
        <View style={[styles.center, { padding: 24 }]}>
          <Ionicons
            name="chatbubble-ellipses-outline"
            size={48}
            color={colors.textSecondary}
          />
          <Text style={styles.emptyTitle}>Aucun retour pour l'instant</Text>
          <Text style={styles.emptyText}>
            Utilisez le bouton ci-dessous pour suggérer une amélioration ou
            signaler un problème. Un copie sera envoyée à l'équipe MesureChâssis.
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
                <View style={styles.statusPill}>
                  <Ionicons
                    name="checkmark-circle"
                    size={12}
                    color="#16A34A"
                  />
                  <Text style={styles.statusText}>ENVOYÉ</Text>
                </View>
                <Text style={styles.cardDate}>
                  {formatDate(item.created_at)}
                </Text>
              </View>
              <Text style={styles.cardComment}>{item.user_comment}</Text>
              {item.page_context ? (
                <Text style={styles.cardContext}>
                  Depuis : <Text style={styles.mono}>{item.page_context}</Text>
                </Text>
              ) : null}
            </View>
          )}
        />
      )}

      {/* CTA — Soumettre un nouveau retour */}
      <View style={styles.footer}>
        <FeedbackButton />
      </View>
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
  listContent: { padding: 16, paddingBottom: 32 },
  card: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: 14,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
  },
  cardHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 8,
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
  footer: {
    paddingHorizontal: 16,
    paddingTop: 8,
    paddingBottom: 12,
    borderTopWidth: 1,
    borderTopColor: colors.borderSubtle,
  },
});
