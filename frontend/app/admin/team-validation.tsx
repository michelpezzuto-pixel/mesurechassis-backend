/**
 * 🚦 Écran admin — Validation des membres (Double-Phase)
 *
 * Le gérant voit ici tous les ouvriers de son équipe qui attendent
 * son approbation. Il peut approuver ou rejeter en 1 tap.
 *
 * Cet écran est purement préventif : il est fonctionnel dès aujourd'hui
 * mais n'aura d'impact réel que le jour où PAYWALL_ENFORCE_VALIDATION=true.
 */
import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  RefreshControl,
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

type PendingMember = {
  id: string;
  email: string;
  name?: string;
  role?: string;
  validation_requested_at?: string;
  created_at?: string;
};

export default function TeamValidationScreen() {
  const router = useRouter();
  const [pending, setPending] = useState<PendingMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const { data } = await api.get<{ pending: PendingMember[]; count: number }>(
        "/team/pending-validation",
      );
      setPending(data.pending || []);
    } catch (e: any) {
      const msg = e?.response?.data?.detail || "Erreur de chargement";
      Alert.alert("Erreur", typeof msg === "string" ? msg : "Erreur inconnue");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const approve = async (u: PendingMember) => {
    Alert.alert(
      "Approuver ce membre ?",
      `Confirmer l'approbation de ${u.name || u.email} ?`,
      [
        { text: "Annuler", style: "cancel" },
        {
          text: "✅ Approuver",
          onPress: async () => {
            setBusy(u.id);
            try {
              await api.post(`/team/validate/${u.id}`, {});
              Alert.alert("✅ Approuvé", "Le membre est notifié par email.");
              setPending((p) => p.filter((x) => x.id !== u.id));
            } catch (e: any) {
              const d = e?.response?.data?.detail;
              Alert.alert(
                "Erreur",
                typeof d === "string" ? d : "Impossible d'approuver.",
              );
            } finally {
              setBusy(null);
            }
          },
        },
      ],
    );
  };

  const reject = async (u: PendingMember) => {
    Alert.alert(
      "Rejeter ce membre ?",
      `Cette personne (${u.email}) ne fera pas partie de votre équipe.`,
      [
        { text: "Annuler", style: "cancel" },
        {
          text: "🚫 Rejeter",
          style: "destructive",
          onPress: async () => {
            setBusy(u.id);
            try {
              await api.post(`/team/reject/${u.id}`, {});
              setPending((p) => p.filter((x) => x.id !== u.id));
            } catch (_e: any) {
              Alert.alert("Erreur", "Impossible de rejeter.");
            } finally {
              setBusy(null);
            }
          },
        },
      ],
    );
  };

  const renderItem = ({ item }: { item: PendingMember }) => (
    <View style={styles.card}>
      <View style={styles.info}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>
            {(item.name || item.email)[0].toUpperCase()}
          </Text>
        </View>
        <View style={{ flex: 1 }}>
          <Text style={styles.name}>{item.name || "Sans nom"}</Text>
          <Text style={styles.email}>{item.email}</Text>
          {item.role ? (
            <Text style={styles.role}>Rôle demandé : {item.role}</Text>
          ) : null}
        </View>
      </View>
      <View style={styles.actions}>
        <TouchableOpacity
          style={[styles.btnReject, busy === item.id && { opacity: 0.5 }]}
          onPress={() => reject(item)}
          disabled={busy === item.id}
        >
          <Ionicons name="close-circle" size={18} color="#fff" />
          <Text style={styles.btnText}>Rejeter</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.btnApprove, busy === item.id && { opacity: 0.5 }]}
          onPress={() => approve(item)}
          disabled={busy === item.id}
        >
          <Ionicons name="checkmark-circle" size={18} color="#fff" />
          <Text style={styles.btnText}>Approuver</Text>
        </TouchableOpacity>
      </View>
    </View>
  );

  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.back}>
          <Ionicons name="chevron-back" size={28} color={colors.text} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Validation d&apos;équipe</Text>
        <View style={{ width: 28 }} />
      </View>

      <View style={styles.banner}>
        <Ionicons name="information-circle" size={20} color={colors.primary} />
        <Text style={styles.bannerText}>
          Approuvez les membres de votre équipe pour valider leur rattachement
          à votre structure de facturation.
        </Text>
      </View>

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator color={colors.primary} size="large" />
        </View>
      ) : pending.length === 0 ? (
        <View style={styles.center}>
          <Ionicons name="checkmark-done-circle" size={72} color="#22C55E" />
          <Text style={styles.emptyTitle}>Aucune demande en attente</Text>
          <Text style={styles.emptySub}>
            Tous les membres de votre équipe sont validés.
          </Text>
        </View>
      ) : (
        <FlatList
          data={pending}
          keyExtractor={(x) => x.id}
          renderItem={renderItem}
          contentContainerStyle={{ padding: 16, gap: 12 }}
          refreshControl={
            <RefreshControl refreshing={false} onRefresh={load} />
          }
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#F9FAFB" },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 12,
    paddingBottom: 8,
    backgroundColor: "#fff",
    borderBottomWidth: 1,
    borderBottomColor: "#E5E7EB",
  },
  back: { padding: 6 },
  headerTitle: { fontSize: 17, fontWeight: "700", color: "#111827" },
  banner: {
    flexDirection: "row",
    gap: 10,
    padding: 14,
    backgroundColor: "#FFF7ED",
    borderBottomWidth: 1,
    borderBottomColor: "#FED7AA",
    alignItems: "flex-start",
  },
  bannerText: { flex: 1, fontSize: 13, color: "#9A3412", lineHeight: 18 },
  center: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: 24,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: "700",
    color: "#111827",
    marginTop: 12,
  },
  emptySub: { fontSize: 14, color: "#6B7280", marginTop: 6, textAlign: "center" },
  card: {
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 14,
    borderWidth: 1,
    borderColor: "#E5E7EB",
    gap: 12,
  },
  info: { flexDirection: "row", alignItems: "center", gap: 12 },
  avatar: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: colors.primary,
    justifyContent: "center",
    alignItems: "center",
  },
  avatarText: { color: "#fff", fontSize: 18, fontWeight: "700" },
  name: { fontSize: 15, fontWeight: "700", color: "#111827" },
  email: { fontSize: 13, color: "#6B7280", marginTop: 2 },
  role: { fontSize: 12, color: "#9CA3AF", marginTop: 4 },
  actions: { flexDirection: "row", gap: 8 },
  btnReject: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    backgroundColor: "#EF4444",
    padding: 10,
    borderRadius: 10,
  },
  btnApprove: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    backgroundColor: "#22C55E",
    padding: 10,
    borderRadius: 10,
  },
  btnText: { color: "#fff", fontWeight: "700", fontSize: 14 },
});
