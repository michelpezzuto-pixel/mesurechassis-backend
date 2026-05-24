import React, { useCallback, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  Linking,
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
import { useAuth } from "@/src/context/AuthContext";
import { colors } from "@/src/theme";

type Feedback = {
  id: string;
  user_email: string;
  page_context: string;
  user_comment: string;
  encoded_data_snapshot: Record<string, unknown>;
  created_at: string;
};

export default function AdminFeedbacks() {
  const { user } = useAuth();
  const router = useRouter();
  const [items, setItems] = useState<Feedback[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const res = await api.get<Feedback[]>("/feedbacks");
      setItems(res.data);
    } catch (e: any) {
      if (e?.response?.status === 403) {
        Alert.alert("Accès refusé", "Réservé aux administrateurs.");
        router.replace("/dashboard");
      } else {
        Alert.alert("Erreur", "Chargement impossible.");
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [router]);

  useFocusEffect(
    useCallback(() => {
      if (user && user.role !== "admin") {
        Alert.alert("Accès refusé", "Réservé aux administrateurs.");
        router.replace("/dashboard");
        return;
      }
      fetchData();
    }, [user, router, fetchData])
  );

  const remove = async (id: string) => {
    Alert.alert("Supprimer", "Supprimer ce feedback ?", [
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
  };

  /** Ouvre l'app mail de l'admin avec un brouillon de réponse pré-rempli vers l'utilisateur. */
  const replyByMail = useCallback(async (fb: Feedback) => {
    const subject = encodeURIComponent(
      "Re: Votre retour MesureChâssis",
    );
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
      Alert.alert(
        "Impossible d'ouvrir l'app mail",
        `Envoyez votre réponse à ${fb.user_email}`,
      );
    }
  }, []);

  if (loading) {
    return (
      <View style={[styles.flex, styles.center]}>
        <ActivityIndicator color={colors.primary} size="large" />
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.flex} edges={["bottom"]}>
      <View style={styles.header}>
        <Ionicons name="megaphone" size={24} color={colors.primary} />
        <Text style={styles.title}>FEEDBACKS UTILISATEURS</Text>
      </View>
      <FlatList
        data={items}
        keyExtractor={(i) => i.id}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => {
              setRefreshing(true);
              fetchData();
            }}
            tintColor={colors.primary}
          />
        }
        contentContainerStyle={{ padding: 16, paddingBottom: 40 }}
        ListEmptyComponent={
          <View style={styles.empty}>
            <Ionicons name="chatbubbles-outline" size={48} color={colors.borderStrong} />
            <Text style={styles.emptyText}>Aucun feedback pour le moment</Text>
          </View>
        }
        renderItem={({ item }) => {
          const isOpen = expanded === item.id;
          return (
            <TouchableOpacity
              testID={`feedback-card-${item.id}`}
              activeOpacity={0.8}
              onPress={() => setExpanded(isOpen ? null : item.id)}
              style={styles.card}
            >
              <View style={styles.cardHeader}>
                <View style={styles.contextBadge}>
                  <Text style={styles.contextBadgeText} numberOfLines={1}>
                    {item.page_context}
                  </Text>
                </View>
                <Text style={styles.date}>{item.created_at.slice(0, 10)}</Text>
              </View>
              <Text style={styles.email}>
                <Ionicons name="person-circle-outline" size={12} color={colors.textSecondary} />{" "}
                {item.user_email}
              </Text>
              <Text style={styles.comment} numberOfLines={isOpen ? undefined : 3}>
                {item.user_comment}
              </Text>
              {isOpen && (
                <View style={styles.snapshotBox}>
                  <Text style={styles.snapshotTitle}>SNAPSHOT DONNÉES</Text>
                  <Text style={styles.snapshotJson}>
                    {JSON.stringify(item.encoded_data_snapshot, null, 2)}
                  </Text>
                  <View style={styles.actionsRow}>
                    <TouchableOpacity
                      testID={`feedback-reply-${item.id}`}
                      onPress={() => replyByMail(item)}
                      style={styles.replyBtn}
                      activeOpacity={0.85}
                    >
                      <Ionicons name="mail" size={16} color="#000" />
                      <Text style={styles.replyBtnText}>RÉPONDRE PAR MAIL</Text>
                    </TouchableOpacity>
                    <TouchableOpacity
                      testID={`feedback-delete-${item.id}`}
                      onPress={() => remove(item.id)}
                      style={styles.deleteBtn}
                      activeOpacity={0.85}
                    >
                      <Ionicons name="trash" size={16} color="#fff" />
                      <Text style={styles.deleteBtnText}>SUPPRIMER</Text>
                    </TouchableOpacity>
                  </View>
                </View>
              )}
            </TouchableOpacity>
          );
        }}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: colors.bg },
  center: { alignItems: "center", justifyContent: "center" },
  header: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    padding: 18,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSubtle,
  },
  title: { color: colors.textPrimary, fontWeight: "900", fontSize: 18, letterSpacing: 1 },
  card: {
    backgroundColor: colors.surface,
    borderColor: colors.borderSubtle,
    borderWidth: 1,
    borderRadius: 12,
    padding: 14,
    marginBottom: 10,
  },
  cardHeader: { flexDirection: "row", alignItems: "center", marginBottom: 8 },
  contextBadge: {
    backgroundColor: "#3a2400",
    borderWidth: 1,
    borderColor: colors.primary,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 4,
    maxWidth: "75%",
  },
  contextBadgeText: { color: colors.primary, fontSize: 11, fontWeight: "800", letterSpacing: 0.5 },
  date: { marginLeft: "auto", color: colors.textSecondary, fontSize: 12 },
  email: { color: colors.textSecondary, fontSize: 12, marginBottom: 6 },
  comment: { color: colors.textPrimary, fontSize: 14, lineHeight: 20 },
  snapshotBox: {
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: colors.borderSubtle,
  },
  snapshotTitle: {
    color: colors.textSecondary,
    fontSize: 11,
    fontWeight: "800",
    letterSpacing: 1.5,
    marginBottom: 6,
  },
  snapshotJson: {
    color: colors.textSecondary,
    fontFamily: "monospace" as any,
    fontSize: 11,
    backgroundColor: colors.bg,
    padding: 10,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
  },
  actionsRow: {
    flexDirection: "row",
    gap: 10,
    marginTop: 12,
    flexWrap: "wrap",
  },
  replyBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    backgroundColor: colors.primary,
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 6,
  },
  replyBtnText: {
    color: "#000",
    fontWeight: "900",
    letterSpacing: 0.5,
    fontSize: 12,
  },
  deleteBtn: {
    alignSelf: "flex-start",
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    backgroundColor: colors.anomaly,
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 6,
  },
  deleteBtnText: { color: "#fff", fontWeight: "700", letterSpacing: 0.5, fontSize: 12 },
  empty: { alignItems: "center", padding: 50, gap: 8 },
  emptyText: { color: colors.textSecondary },
});
