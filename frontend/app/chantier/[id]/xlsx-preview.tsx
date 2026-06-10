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
import { XLSX_URL, buildAuthHeaders } from "@/src/services/api";
import { colors } from "@/src/theme";

/**
 * Aperçu de l'export Excel d'un chantier.
 * Les .xlsx ne sont pas prévisualisables nativement — on affiche
 * un résumé des métadonnées du fichier + un bouton Partager qui
 * déclenche la Web Share API (ou un téléchargement en fallback).
 */
export default function XlsxPreview() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const [size, setSize] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [blobUrl, setBlobUrl] = useState<string | null>(null);

  const fetchFile = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      // 🍏 EXPO GO iOS — `r.blob()` + `Blob.size` natifs déclenchent
      // "globalThis.__turboModuleProxy is not a function". On NE PRÉ-CHARGE
      // PAS le fichier sur natif : on attend le clic PARTAGER qui utilise
      // expo-file-system pour télécharger directement en cache.
      if (Platform.OS !== "web") {
        setSize(null);
        setBlobUrl(null);
        return;
      }
      const headers = await buildAuthHeaders();
      const r = await fetch(XLSX_URL(String(id)), { headers });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const blob = await r.blob();
      setSize(blob.size);
      setBlobUrl(URL.createObjectURL(blob));
    } catch (e: any) {
      setError(e?.message || "Génération Excel impossible.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchFile();
    return () => {
      if (blobUrl && Platform.OS === "web") {
        try { URL.revokeObjectURL(blobUrl); } catch { /* noop */ }
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const handleShare = async () => {
    if (!id) return;
    const fileName = `Atelier_MesureChassis_${id}.xlsx`;
    try {
      if (Platform.OS === "web") {
        if (!blobUrl) return;
        const r = await fetch(blobUrl);
        const blob = await r.blob();
        const navAny: any = navigator;
        const file = new File([blob], fileName, {
          type:
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        });
        if (
          navAny.share &&
          (!navAny.canShare || navAny.canShare({ files: [file] }))
        ) {
          await navAny.share({
            title: "Export Excel atelier",
            text: "Fichier Excel pour atelier / machines de découpe.",
            files: [file],
          });
          return;
        }
        const a = document.createElement("a");
        a.href = blobUrl;
        a.download = fileName;
        document.body.appendChild(a);
        a.click();
        a.remove();
      } else {
        const FS: any = await import("expo-file-system/legacy");
        const Sharing = await import("expo-sharing");
        const dest = `${FS.cacheDirectory}${fileName}`;
        const headers = await buildAuthHeaders();
        await FS.downloadAsync(XLSX_URL(String(id)), dest, { headers });
        await Sharing.shareAsync(dest, {
          dialogTitle: "Partager l'export Excel",
          mimeType:
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        });
      }
    } catch (e: any) {
      Alert.alert("Erreur", e?.message || "Partage impossible.");
    }
  };

  return (
    <SafeAreaView style={styles.flex} edges={["top", "bottom"]}>
      <View style={styles.topBar}>
        <TouchableOpacity
          testID="xlsx-back-button"
          onPress={() => router.back()}
          activeOpacity={0.7}
          style={styles.backBtn}
          hitSlop={10}
        >
          <Ionicons name="chevron-back" size={22} color={colors.textPrimary} />
          <Text style={styles.backText}>RETOUR</Text>
        </TouchableOpacity>
        <View style={styles.titleBox}>
          <Text style={styles.title} numberOfLines={1}>Export Excel</Text>
          <Text style={styles.subtitle}>Tableau atelier / découpe</Text>
        </View>
        <View style={{ width: 70 }} />
      </View>

      <View style={styles.actionsBar}>
        <TouchableOpacity
          testID="xlsx-share-button"
          onPress={handleShare}
          disabled={loading || !!error}
          activeOpacity={0.85}
          style={[
            styles.actionBtn,
            styles.actionPrimary,
            (loading || !!error) && { opacity: 0.4 },
          ]}
        >
          <Ionicons name="share-social" size={18} color="#000" />
          <Text style={styles.actionPrimaryText}>PARTAGER</Text>
        </TouchableOpacity>
      </View>

      <ScrollView contentContainerStyle={styles.viewer}>
        {loading ? (
          <View style={styles.center}>
            <ActivityIndicator color={colors.primary} size="large" />
            <Text style={styles.help}>Génération du fichier Excel...</Text>
          </View>
        ) : error ? (
          <View style={styles.center}>
            <Ionicons name="alert-circle" size={48} color={colors.anomaly} />
            <Text style={styles.error}>{error}</Text>
            <TouchableOpacity
              onPress={fetchFile}
              style={[styles.actionBtn, styles.actionPrimary]}
            >
              <Text style={styles.actionPrimaryText}>RÉESSAYER</Text>
            </TouchableOpacity>
          </View>
        ) : (
          <View style={styles.summary}>
            <View style={styles.iconBig}>
              <Ionicons name="grid" size={56} color="#22C55E" />
            </View>
            <Text style={styles.fileTitle}>Fichier Excel prêt</Text>
            <Text style={styles.fileMeta}>Format : .xlsx (Microsoft Excel)</Text>
            <Text style={styles.fileMeta}>
              Taille : {size != null ? `${(size / 1024).toFixed(1)} Ko` : "—"}
            </Text>
            <Text style={styles.fileMeta}>2 feuilles : Chantier + Mesures + Photos</Text>
            <View style={styles.tipBox}>
              <Ionicons name="information-circle" size={18} color={colors.alert} />
              <Text style={styles.tipText}>
                Touchez « PARTAGER » pour ouvrir le fichier dans Excel, Numbers,
                Google Sheets ou l&apos;envoyer par e-mail.
              </Text>
            </View>
          </View>
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
  viewer: { flexGrow: 1, padding: 20 },
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: 20,
    gap: 10,
  },
  help: { color: colors.textSecondary, fontSize: 13, textAlign: "center" },
  error: {
    color: colors.anomaly,
    fontSize: 14,
    fontWeight: "700",
    textAlign: "center",
  },
  summary: { alignItems: "center", paddingTop: 30, gap: 8 },
  iconBig: {
    width: 96,
    height: 96,
    borderRadius: 48,
    backgroundColor: "#0e3315",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 12,
  },
  fileTitle: {
    color: colors.textPrimary,
    fontWeight: "900",
    fontSize: 18,
    marginBottom: 4,
  },
  fileMeta: { color: colors.textSecondary, fontSize: 13 },
  tipBox: {
    flexDirection: "row",
    gap: 8,
    backgroundColor: colors.surface,
    padding: 12,
    borderRadius: 8,
    marginTop: 20,
    alignItems: "flex-start",
    maxWidth: 360,
  },
  tipText: {
    color: colors.textSecondary,
    fontSize: 12,
    lineHeight: 17,
    flex: 1,
  },
});
