import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  Platform,
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

type Tester = {
  id: string;
  name: string;
  company: string;
  email: string;
  phone: string;
  status: "new" | "invited";
  created_at: string;
};

/** Vue ADMIN : candidats testeurs Google Play inscrits via /devenir-testeur. */
export default function AdminTesters() {
  const router = useRouter();
  const [testers, setTesters] = useState<Tester[]>([]);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  const fetchTesters = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get<{ total: number; testers: Tester[] }>(
        "/testers",
      );
      setTesters(res.data.testers);
    } catch {
      // silencieux : la liste reste vide
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchTesters();
  }, [fetchTesters]);

  const copyAllEmails = async () => {
    const emails = testers.map((t) => t.email).join("\n");
    await Clipboard.setStringAsync(emails);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  const markInvited = async (t: Tester) => {
    await api.patch(`/testers/${t.id}/invited`);
    void fetchTesters();
  };

  const removeTester = (t: Tester) => {
    const doDelete = async () => {
      await api.delete(`/testers/${t.id}`);
      void fetchTesters();
    };
    if (Platform.OS === "web") {
      // eslint-disable-next-line no-alert
      if (window.confirm(`Supprimer ${t.email} ?`)) void doDelete();
    } else {
      Alert.alert("Supprimer", `Supprimer ${t.email} ?`, [
        { text: "Annuler", style: "cancel" },
        { text: "Supprimer", style: "destructive", onPress: () => void doDelete() },
      ]);
    }
  };

  const newCount = testers.filter((t) => t.status === "new").length;

  return (
    <SafeAreaView style={styles.flex} edges={["top", "bottom"]}>
      <View style={styles.topBar}>
        <TouchableOpacity
          testID="testers-back-button"
          onPress={() => router.back()}
          hitSlop={10}
        >
          <Ionicons name="arrow-back" size={22} color={colors.textPrimary} />
        </TouchableOpacity>
        <Text style={styles.topTitle}>TESTEURS GOOGLE PLAY</Text>
        <TouchableOpacity
          testID="testers-refresh-button"
          onPress={() => void fetchTesters()}
          hitSlop={10}
        >
          <Ionicons name="refresh" size={20} color={colors.primary} />
        </TouchableOpacity>
      </View>

      {/* Compteur objectif Google */}
      <View style={styles.statsRow}>
        <View style={styles.statBox} testID="testers-total-box">
          <Text style={styles.statValue}>{testers.length}</Text>
          <Text style={styles.statLabel}>inscrits</Text>
        </View>
        <View style={styles.statBox}>
          <Text style={[styles.statValue, { color: "#FBBF24" }]}>
            {newCount}
          </Text>
          <Text style={styles.statLabel}>à ajouter</Text>
        </View>
        <View style={styles.statBox}>
          <Text
            style={[
              styles.statValue,
              { color: testers.length >= 12 ? "#22C55E" : "#F87171" },
            ]}
          >
            {testers.length >= 12 ? "✓" : `${12 - testers.length}`}
          </Text>
          <Text style={styles.statLabel}>
            {testers.length >= 12 ? "objectif 12 OK" : "manquants /12"}
          </Text>
        </View>
      </View>

      <TouchableOpacity
        testID="testers-copy-all-button"
        style={[styles.copyBtn, copied && { backgroundColor: "#22C55E" }]}
        onPress={() => void copyAllEmails()}
        disabled={testers.length === 0}
      >
        <Ionicons name={copied ? "checkmark" : "copy-outline"} size={18} color="#fff" />
        <Text style={styles.copyBtnText}>
          {copied
            ? "Emails copiés !"
            : `Copier les ${testers.length} emails (pour Play Console)`}
        </Text>
      </TouchableOpacity>

      {loading ? (
        <ActivityIndicator color={colors.primary} style={{ marginTop: 40 }} />
      ) : testers.length === 0 ? (
        <View style={styles.emptyWrap}>
          <Ionicons name="people-outline" size={42} color={colors.textSecondary} />
          <Text style={styles.emptyText}>
            Aucun candidat pour le moment.{"\n"}Partagez la page publique :
          </Text>
          <Text style={styles.emptyLink}>mesurechassis — /devenir-testeur</Text>
        </View>
      ) : (
        <FlatList
          data={testers}
          keyExtractor={(t) => t.id}
          contentContainerStyle={{ padding: 16, paddingBottom: 50 }}
          renderItem={({ item }) => (
            <View style={styles.card} testID={`tester-card-${item.email}`}>
              <View style={{ flex: 1 }}>
                <View style={styles.cardHeader}>
                  <Text style={styles.cardName}>{item.name}</Text>
                  {item.status === "invited" ? (
                    <View style={styles.badgeInvited}>
                      <Text style={styles.badgeInvitedText}>AJOUTÉ</Text>
                    </View>
                  ) : (
                    <View style={styles.badgeNew}>
                      <Text style={styles.badgeNewText}>NOUVEAU</Text>
                    </View>
                  )}
                </View>
                <Text style={styles.cardEmail} selectable>
                  {item.email}
                </Text>
                {!!item.company && (
                  <Text style={styles.cardMeta}>{item.company}</Text>
                )}
                {!!item.phone && <Text style={styles.cardMeta}>{item.phone}</Text>}
              </View>
              <View style={styles.cardActions}>
                {item.status === "new" && (
                  <TouchableOpacity
                    testID={`tester-invited-${item.email}`}
                    onPress={() => void markInvited(item)}
                    hitSlop={8}
                  >
                    <Ionicons name="checkmark-circle-outline" size={24} color="#22C55E" />
                  </TouchableOpacity>
                )}
                <TouchableOpacity
                  testID={`tester-delete-${item.email}`}
                  onPress={() => removeTester(item)}
                  hitSlop={8}
                >
                  <Ionicons name="trash-outline" size={22} color="#F87171" />
                </TouchableOpacity>
              </View>
            </View>
          )}
        />
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
  statsRow: { flexDirection: "row", gap: 10, paddingHorizontal: 16 },
  statBox: {
    flex: 1,
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: 14,
    alignItems: "center",
  },
  statValue: { color: colors.textPrimary, fontSize: 22, fontWeight: "800" },
  statLabel: { color: colors.textSecondary, fontSize: 11, marginTop: 2, textAlign: "center" },
  copyBtn: {
    flexDirection: "row",
    gap: 8,
    backgroundColor: colors.primary,
    margin: 16,
    marginBottom: 4,
    paddingVertical: 13,
    borderRadius: 10,
    alignItems: "center",
    justifyContent: "center",
  },
  copyBtnText: { color: "#fff", fontWeight: "800", fontSize: 13 },
  emptyWrap: { alignItems: "center", marginTop: 60, gap: 12, paddingHorizontal: 30 },
  emptyText: { color: colors.textSecondary, textAlign: "center", lineHeight: 20 },
  emptyLink: { color: colors.primary, fontWeight: "700" },
  card: {
    flexDirection: "row",
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: 14,
    marginBottom: 10,
    alignItems: "center",
  },
  cardHeader: { flexDirection: "row", alignItems: "center", gap: 8 },
  cardName: { color: colors.textPrimary, fontWeight: "700", fontSize: 15 },
  cardEmail: { color: colors.primary, fontSize: 13, marginTop: 2 },
  cardMeta: { color: colors.textSecondary, fontSize: 12, marginTop: 2 },
  badgeNew: {
    backgroundColor: "rgba(251,191,36,0.15)",
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 6,
  },
  badgeNewText: { color: "#FBBF24", fontSize: 10, fontWeight: "800" },
  badgeInvited: {
    backgroundColor: "rgba(34,197,94,0.15)",
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 6,
  },
  badgeInvitedText: { color: "#22C55E", fontSize: 10, fontWeight: "800" },
  cardActions: { gap: 14, alignItems: "center", marginLeft: 10 },
});
