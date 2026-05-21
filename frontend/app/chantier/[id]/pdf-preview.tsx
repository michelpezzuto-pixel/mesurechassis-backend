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

/**
 * Aperçu du Récapitulatif de Mesure PDF.
 * Ceci est une FICHE TECHNIQUE de validation des cotes —
 * PAS un devis commercial. Le bouton "Partager" est l'unique action
 * proposée (avec un retour vers le chantier).
 */
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
      // 🍏 EXPO GO iOS — `URL.createObjectURL` + `Blob` natifs déclenchent
      // "globalThis.__turboModuleProxy is not a function (it is undefined)".
      // On NE PRÉ-CHARGE PAS le PDF sur natif : on attend le clic PARTAGER
      // qui utilise expo-file-system pour télécharger directement en cache.
      if (Platform.OS !== "web") {
        setBlobUrl(null);
        return;
      }
      const token = await getToken();
      const r = await fetch(PDF_URL(String(id)), {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const blob = await r.blob();
      const u = URL.createObjectURL(blob);
      setBlobUrl(u);
    } catch (e: any) {
      setError(e?.message || "Impossible de charger le récapitulatif.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchPdf();
    return () => {
      if (blobUrl && Platform.OS === "web") {
        try {
          URL.revokeObjectURL(blobUrl);
        } catch {
          /* noop */
        }
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const handleShare = async () => {
    if (!blobUrl) return;
    const fileName = `Recapitulatif_MesureChassis_${id}.pdf`;
    try {
      if (Platform.OS === "web") {
        const r = await fetch(blobUrl);
        const blob = await r.blob();
        // Tente Web Share API si dispo + supportée pour les fichiers
        const navAny: any = navigator;
        const file = new File([blob], fileName, { type: "application/pdf" });
        if (
          navAny.share &&
          (!navAny.canShare || navAny.canShare({ files: [file] }))
        ) {
          await navAny.share({
            title: "Récapitulatif de Mesure",
            text: "Fiche technique de validation des cotes.",
            files: [file],
          });
          return;
        }
        // Fallback : download forcé
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
        const token = await getToken();
        await FS.downloadAsync(PDF_URL(String(id)), dest, {
          headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        });
        await Sharing.shareAsync(dest, {
          dialogTitle: "Partager le récapitulatif",
          mimeType: "application/pdf",
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
          testID="pdf-back-button"
          onPress={() => router.back()}
          activeOpacity={0.7}
          style={styles.backBtn}
          hitSlop={10}
        >
          <Ionicons name="chevron-back" size={22} color={colors.textPrimary} />
          <Text style={styles.backText}>RETOUR</Text>
        </TouchableOpacity>
        <View style={styles.titleBox}>
          <Text style={styles.title} numberOfLines={1}>
            Récapitulatif de Mesure PDF
          </Text>
          <Text style={styles.subtitle}>Fiche technique de validation</Text>
        </View>
        <View style={{ width: 70 }} />
      </View>

      <View style={styles.actionsBar}>
        <TouchableOpacity
          testID="pdf-share-button"
          onPress={handleShare}
          disabled={!blobUrl}
          activeOpacity={0.85}
          style={[
            styles.actionBtn,
            styles.actionPrimary,
            !blobUrl && { opacity: 0.4 },
          ]}
        >
          <Ionicons name="share-social" size={18} color="#000" />
          <Text style={styles.actionPrimaryText}>PARTAGER</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.viewer}>
        {loading ? (
          <View style={styles.center}>
            <ActivityIndicator color={colors.primary} size="large" />
            <Text style={styles.help}>Génération du récapitulatif...</Text>
          </View>
        ) : error ? (
          <View style={styles.center}>
            <Ionicons name="alert-circle" size={48} color={colors.anomaly} />
            <Text style={styles.error}>{error}</Text>
            <TouchableOpacity
              onPress={fetchPdf}
              style={[styles.actionBtn, styles.actionPrimary]}
            >
              <Text style={styles.actionPrimaryText}>RÉESSAYER</Text>
            </TouchableOpacity>
          </View>
        ) : Platform.OS === "web" && blobUrl ? (
          // @ts-ignore — web iframe via createElement
          React.createElement("iframe", {
            src: blobUrl,
            style: {
              flex: 1,
              width: "100%",
              height: "100%",
              border: "none",
              backgroundColor: "#fff",
            },
            title: "Récapitulatif de Mesure PDF",
          })
        ) : (
          <View style={styles.center}>
            <Ionicons name="document-text" size={64} color={colors.primary} />
            <Text style={[styles.help, { fontSize: 15, fontWeight: "700", color: colors.textPrimary, marginTop: 8 }]}>
              Récapitulatif prêt
            </Text>
            <Text style={styles.help}>
              Touchez « PARTAGER » pour ouvrir le PDF avec Mail, Files, AirDrop ou une autre app.
            </Text>
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
    letterSpacing: 0.2,
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
  viewer: { flex: 1 },
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: 20,
    gap: 10,
  },
  help: {
    color: colors.textSecondary,
    fontSize: 13,
    textAlign: "center",
  },
  error: {
    color: colors.anomaly,
    fontSize: 14,
    fontWeight: "700",
    textAlign: "center",
  },
});
