import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Platform,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useLocalSearchParams, useRouter } from "expo-router";
import { PDF_URL, getToken } from "@/src/services/api";
import { colors } from "@/src/theme";

export default function PdfPreview() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPdf = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const token = await getToken();
      const r = await fetch(PDF_URL(String(id)), {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const blob = await r.blob();
      const u = URL.createObjectURL(blob);
      setBlobUrl(u);
    } catch (e: any) {
      setError(e?.message || "Impossible de charger le PDF.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchPdf();
    return () => {
      if (blobUrl) {
        try { URL.revokeObjectURL(blobUrl); } catch { /* noop */ }
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const handlePrint = () => {
    if (Platform.OS !== "web" || !blobUrl) return;
    try {
      const win = window.open(blobUrl, "_blank");
      if (win) {
        win.addEventListener("load", () => {
          try { win.print(); } catch { /* noop */ }
        });
      } else {
        Alert.alert("Pop-up bloqué", "Autorisez les pop-ups pour imprimer.");
      }
    } catch {
      Alert.alert("Erreur", "Impression impossible.");
    }
  };

  const handleShare = async () => {
    if (!blobUrl) return;
    try {
      if (Platform.OS === "web" && (navigator as any).share) {
        const r = await fetch(blobUrl);
        const blob = await r.blob();
        const file = new File([blob], `MesureChassis_${id}.pdf`, { type: "application/pdf" });
        await (navigator as any).share({
          title: "Devis MesureChâssis",
          text: "Veuillez trouver le devis.",
          files: [file],
        });
      } else {
        // Native share via expo-sharing
        const FS: any = await import("expo-file-system/legacy");
        const Sharing = await import("expo-sharing");
        const safe = `MesureChassis_${id}.pdf`;
        const dest = `${FS.cacheDirectory}${safe}`;
        const token = await getToken();
        await FS.downloadAsync(PDF_URL(String(id)), dest, {
          headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        });
        await Sharing.shareAsync(dest, { dialogTitle: "Partager le devis", mimeType: "application/pdf" });
      }
    } catch (e: any) {
      Alert.alert("Erreur", e?.message || "Partage impossible.");
    }
  };

  const handleDownload = () => {
    if (Platform.OS !== "web" || !blobUrl) return;
    const a = document.createElement("a");
    a.href = blobUrl;
    a.download = `MesureChassis_${id}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
  };

  return (
    <SafeAreaView style={styles.flex} edges={["top", "bottom"]}>
      <View style={styles.topBar}>
        <TouchableOpacity
          testID="pdf-back-button"
          onPress={() => router.back()}
          activeOpacity={0.7}
          style={styles.backBtn}
          hitSlop={10}
        >
          <Ionicons name="arrow-back" size={20} color={colors.textPrimary} />
          <Text style={styles.backText}>Retour au chantier</Text>
        </TouchableOpacity>
        <TouchableOpacity
          testID="pdf-close-button"
          onPress={() => router.back()}
          activeOpacity={0.7}
          hitSlop={10}
          style={{ padding: 4 }}
        >
          <Ionicons name="close" size={22} color={colors.textPrimary} />
        </TouchableOpacity>
      </View>

      <View style={styles.actionsBar}>
        <TouchableOpacity
          testID="pdf-share-button"
          onPress={handleShare}
          disabled={!blobUrl}
          activeOpacity={0.85}
          style={[styles.actionBtn, styles.actionPrimary, !blobUrl && { opacity: 0.4 }]}
        >
          <Ionicons name="share-social" size={18} color="#000" />
          <Text style={styles.actionPrimaryText}>PARTAGER</Text>
        </TouchableOpacity>
        {Platform.OS === "web" && (
          <TouchableOpacity
            testID="pdf-print-button"
            onPress={handlePrint}
            disabled={!blobUrl}
            activeOpacity={0.85}
            style={[styles.actionBtn, styles.actionSecondary, !blobUrl && { opacity: 0.4 }]}
          >
            <Ionicons name="print" size={18} color={colors.textPrimary} />
            <Text style={styles.actionSecondaryText}>IMPRIMER</Text>
          </TouchableOpacity>
        )}
        {Platform.OS === "web" && (
          <TouchableOpacity
            testID="pdf-download-button"
            onPress={handleDownload}
            disabled={!blobUrl}
            activeOpacity={0.85}
            style={[styles.actionBtn, styles.actionSecondary, !blobUrl && { opacity: 0.4 }]}
          >
            <Ionicons name="download" size={18} color={colors.textPrimary} />
            <Text style={styles.actionSecondaryText}>TÉLÉCHARGER</Text>
          </TouchableOpacity>
        )}
      </View>

      <View style={styles.viewer}>
        {loading ? (
          <View style={styles.center}>
            <ActivityIndicator color={colors.primary} size="large" />
            <Text style={styles.help}>Génération du devis...</Text>
          </View>
        ) : error ? (
          <View style={styles.center}>
            <Ionicons name="alert-circle" size={48} color={colors.anomaly} />
            <Text style={styles.error}>{error}</Text>
            <TouchableOpacity onPress={fetchPdf} style={[styles.actionBtn, styles.actionPrimary]}>
              <Text style={styles.actionPrimaryText}>RÉESSAYER</Text>
            </TouchableOpacity>
          </View>
        ) : Platform.OS === "web" && blobUrl ? (
          // @ts-ignore — web iframe via createElement
          React.createElement("iframe", {
            src: blobUrl,
            style: { flex: 1, width: "100%", height: "100%", border: "none", backgroundColor: "#fff" },
            title: "PDF Devis",
          })
        ) : (
          <View style={styles.center}>
            <Ionicons name="document" size={48} color={colors.textSecondary} />
            <Text style={styles.help}>Touchez "PARTAGER" pour ouvrir le PDF dans une autre app.</Text>
          </View>
        )}
      </View>
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
  },
  backBtn: { flexDirection: "row", alignItems: "center", gap: 6, paddingHorizontal: 4, paddingVertical: 6 },
  backText: { color: colors.textPrimary, fontWeight: "800", fontSize: 13, letterSpacing: 0.3 },
  actionsBar: {
    flexDirection: "row",
    flexWrap: "wrap",
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
    gap: 6,
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 8,
  },
  actionPrimary: { backgroundColor: colors.primary },
  actionPrimaryText: { color: "#000", fontWeight: "900", fontSize: 12, letterSpacing: 0.8 },
  actionSecondary: { backgroundColor: "transparent", borderWidth: 1, borderColor: colors.borderSubtle },
  actionSecondaryText: { color: colors.textPrimary, fontWeight: "800", fontSize: 12, letterSpacing: 0.8 },
  viewer: { flex: 1 },
  center: { flex: 1, alignItems: "center", justifyContent: "center", padding: 20, gap: 10 },
  help: { color: colors.textSecondary, fontSize: 13, textAlign: "center" },
  error: { color: colors.anomaly, fontSize: 14, fontWeight: "700", textAlign: "center" },
});
