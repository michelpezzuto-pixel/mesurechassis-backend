import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useLocalSearchParams, useRouter } from "expo-router";
import { JSON_URL, getToken } from "@/src/services/api";
import { colors } from "@/src/theme";

/**
 * Aperçu de l'export JSON d'un chantier — utile pour l'intégration
 * machines CNC / API tierces. Affiche un extrait formatté du JSON
 * + bouton Partager (Web Share API ou expo-sharing).
 */
export default function JsonPreview() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const [text, setText] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchJson = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const token = await getToken();
      const r = await fetch(JSON_URL(String(id)), {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      setText(JSON.stringify(data, null, 2));
    } catch (e: any) {
      setError(e?.message || "Génération JSON impossible.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchJson();
  }, [fetchJson]);

  const handleShare = async () => {
    if (!text || !id) return;
    const fileName = `MesureChassis_${id}.json`;
    try {
      if (Platform.OS === "web") {
        const blob = new Blob([text], { type: "application/json" });
        const navAny: any = navigator;
        const file = new File([blob], fileName, { type: "application/json" });
        if (
          navAny.share &&
          (!navAny.canShare || navAny.canShare({ files: [file] }))
        ) {
          await navAny.share({
            title: "Export JSON MesureChâssis",
            text: "Données structurées pour intégration logiciel.",
            files: [file],
          });
          return;
        }
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = fileName;
        document.body.appendChild(a);
        a.click();
        a.remove();
        setTimeout(() => URL.revokeObjectURL(url), 0);
      } else {
        const FS: any = await import("expo-file-system/legacy");
        const Sharing = await import("expo-sharing");
        const dest = `${FS.cacheDirectory}${fileName}`;
        await FS.writeAsStringAsync(dest, text);
        await Sharing.shareAsync(dest, {
          dialogTitle: "Partager l'export JSON",
          mimeType: "application/json",
        });
      }
    } catch (e: any) {
      Alert.alert("Erreur", e?.message || "Partage impossible.");
    }
  };

  const preview = text
    ? text.length > 4000
      ? text.slice(0, 4000) + "\n\n[...] (" + text.length + " caractères au total)"
      : text
    : "";

  return (
    <SafeAreaView style={styles.flex} edges={["top", "bottom"]}>
      <View style={styles.topBar}>
        <TouchableOpacity
          testID="json-back-button"
          onPress={() => router.back()}
          activeOpacity={0.7}
          style={styles.backBtn}
          hitSlop={10}
        >
          <Ionicons name="chevron-back" size={22} color={colors.textPrimary} />
          <Text style={styles.backText}>RETOUR</Text>
        </TouchableOpacity>
        <View style={styles.titleBox}>
          <Text style={styles.title} numberOfLines={1}>Export JSON</Text>
          <Text style={styles.subtitle}>Intégration CNC / API</Text>
        </View>
        <View style={{ width: 70 }} />
      </View>

      <View style={styles.actionsBar}>
        <TouchableOpacity
          testID="json-share-button"
          onPress={handleShare}
          disabled={!text}
          activeOpacity={0.85}
          style={[
            styles.actionBtn,
            styles.actionPrimary,
            !text && { opacity: 0.4 },
          ]}
        >
          <Ionicons name="share-social" size={18} color="#000" />
          <Text style={styles.actionPrimaryText}>PARTAGER</Text>
        </TouchableOpacity>
      </View>

      <ScrollView style={styles.viewer} contentContainerStyle={{ padding: 14 }}>
        {loading ? (
          <View style={styles.center}>
            <ActivityIndicator color={colors.primary} size="large" />
            <Text style={styles.help}>Génération JSON...</Text>
          </View>
        ) : error ? (
          <View style={styles.center}>
            <Ionicons name="alert-circle" size={48} color={colors.anomaly} />
            <Text style={styles.errorText}>{error}</Text>
            <TouchableOpacity
              onPress={fetchJson}
              style={[styles.actionBtn, styles.actionPrimary]}
            >
              <Text style={styles.actionPrimaryText}>RÉESSAYER</Text>
            </TouchableOpacity>
          </View>
        ) : (
          <Text style={styles.code} selectable>{preview}</Text>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: colors.bg },
  topBar: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSubtle,
    gap: 8,
  },
  backBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 2,
    paddingHorizontal: 4,
    paddingVertical: 6,
    width: 80,
  },
  backText: {
    color: colors.textPrimary,
    fontWeight: "800",
    fontSize: 13,
    letterSpacing: 0.5,
  },
  titleBox: { flex: 1, alignItems: "center" },
  title: {
    color: colors.textPrimary,
    fontWeight: "900",
    fontSize: 14,
    letterSpacing: 0.3,
  },
  subtitle: {
    color: colors.textSecondary,
    fontSize: 10,
    marginTop: 2,
  },
  actionsBar: {
    flexDirection: "row",
    gap: 8,
    padding: 12,
    backgroundColor: colors.surface,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSubtle,
  },
  actionBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 8,
    flex: 1,
  },
  actionPrimary: { backgroundColor: colors.primary },
  actionPrimaryText: {
    color: "#000",
    fontWeight: "900",
    fontSize: 13,
    letterSpacing: 0.8,
  },
  viewer: { flex: 1, backgroundColor: "#000" },
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: 20,
    gap: 10,
  },
  help: { color: colors.textSecondary, fontSize: 13, textAlign: "center" },
  errorText: {
    color: colors.anomaly,
    fontSize: 14,
    fontWeight: "700",
    textAlign: "center",
  },
  code: {
    fontFamily: Platform.select({
      ios: "Menlo",
      android: "monospace",
      default: "monospace",
    }) as any,
    color: "#A1F0A1",
    fontSize: 11,
    lineHeight: 16,
  },
});
