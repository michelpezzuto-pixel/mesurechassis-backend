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
import { api, PDF_URL, getToken } from "@/src/services/api";
import { colors, blockMeta, statusMeta } from "@/src/theme";

/**
 * Aperçu du Récapitulatif de Mesure PDF.
 *
 * FICHE TECHNIQUE de validation des cotes — PAS un devis commercial.
 *
 * Architecture par plateforme :
 *  • WEB : iframe affichant le PDF généré côté backend.
 *  • iOS / Android (Expo Go) : on NE charge PAS de Blob (crash garanti
 *    avec `globalThis.__turboModuleProxy is not a function`). On affiche
 *    à la place un RÉSUMÉ STRUCTURÉ du chantier (chantier + config mur +
 *    liste des châssis avec leurs cotes) → l'utilisateur valide visuellement
 *    avant de toucher PARTAGER pour télécharger le PDF complet.
 */
export default function PdfPreview() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [chantier, setChantier] = useState<any | null>(null);
  const [mesures, setMesures] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // ── Loaders ─────────────────────────────────────────────────────────
  const fetchSummary = useCallback(async () => {
    if (!id) return;
    try {
      const [c, m] = await Promise.all([
        api.get(`/chantiers/${id}`),
        api.get(`/chantiers/${id}/mesures`),
      ]);
      setChantier(c.data);
      setMesures(Array.isArray(m.data) ? m.data : []);
    } catch (e: any) {
      // Non bloquant — le PDF reste partageable
      setChantier(null);
      setMesures([]);
    }
  }, [id]);

  const fetchPdfBlobForWeb = useCallback(async () => {
    if (!id) return;
    if (Platform.OS !== "web") return;
    try {
      const token = await getToken();
      const r = await fetch(PDF_URL(String(id)), {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const blob = await r.blob();
      setBlobUrl(URL.createObjectURL(blob));
    } catch (e: any) {
      setError(e?.message || "Impossible de charger le PDF web.");
    }
  }, [id]);

  useEffect(() => {
    (async () => {
      setLoading(true);
      setError(null);
      await fetchSummary();
      if (Platform.OS === "web") {
        await fetchPdfBlobForWeb();
      }
      setLoading(false);
    })();
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

  // ── Share ───────────────────────────────────────────────────────────
  const handleShare = async () => {
    const fileName = `Recapitulatif_MesureChassis_${id}.pdf`;
    try {
      if (Platform.OS === "web") {
        if (!blobUrl) return;
        const r = await fetch(blobUrl);
        const blob = await r.blob();
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
          UTI: "com.adobe.pdf",
        });
      }
    } catch (e: any) {
      Alert.alert("Erreur", e?.message || "Partage impossible.");
    }
  };

  // ── Helpers d'affichage ─────────────────────────────────────────────
  const shapeLabel = (m: any): string => {
    const bt = m.block_type as keyof typeof blockMeta;
    return blockMeta[bt]?.label || bt || "Châssis";
  };

  const fmt = (v: any): string =>
    v == null || v === "" ? "—" : `${Math.round(Number(v))}`;

  const masonryLabels: Record<string, string> = {
    bloc_beton: "Bloc béton",
    bloc_terre_cuite: "Bloc terre cuite",
    brique: "Brique",
    pierre: "Pierre",
  };

  const insulationLabels: Record<string, string> = {
    none: "Mur plein sans isolation",
    iti: "Isolation Intérieure (ITI)",
    ite: "Isolation Extérieure (ITE)",
  };

  // ── Render ──────────────────────────────────────────────────────────
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
            Récapitulatif de Mesure
          </Text>
          <Text style={styles.subtitle}>Fiche technique de validation</Text>
        </View>
        <View style={{ width: 70 }} />
      </View>

      <View style={styles.actionsBar}>
        <TouchableOpacity
          testID="pdf-share-button"
          onPress={handleShare}
          disabled={loading}
          activeOpacity={0.85}
          style={[
            styles.actionBtn,
            styles.actionPrimary,
            loading && { opacity: 0.4 },
          ]}
        >
          <Ionicons name="share-social" size={18} color="#000" />
          <Text style={styles.actionPrimaryText}>PARTAGER</Text>
        </TouchableOpacity>
      </View>

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator color={colors.primary} size="large" />
          <Text style={styles.help}>Chargement du récapitulatif…</Text>
        </View>
      ) : error ? (
        <View style={styles.center}>
          <Ionicons name="alert-circle" size={48} color={colors.anomaly} />
          <Text style={styles.error}>{error}</Text>
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
        <ScrollView
          contentContainerStyle={styles.scrollBody}
          showsVerticalScrollIndicator={false}
        >
          {/* Bloc CHANTIER */}
          {chantier && (
            <View style={styles.card}>
              <View style={styles.cardHeaderRow}>
                <Ionicons name="home" size={18} color={colors.primary} />
                <Text style={styles.cardHeaderText}>CHANTIER</Text>
              </View>
              <Text style={styles.clientName} numberOfLines={2}>
                {chantier.client_name || "Sans nom"}
              </Text>
              <Text style={styles.address}>
                {chantier.address}
                {chantier.postal_code || chantier.city
                  ? ` · ${[chantier.postal_code, chantier.city]
                      .filter(Boolean)
                      .join(" ")}`
                  : ""}
              </Text>
              <View style={styles.chipRow}>
                <View
                  style={[
                    styles.chip,
                    {
                      backgroundColor:
                        (statusMeta as any)[chantier.status]?.bg ||
                        colors.surface,
                    },
                  ]}
                >
                  <Text
                    style={[
                      styles.chipText,
                      {
                        color:
                          (statusMeta as any)[chantier.status]?.color ||
                          colors.textPrimary,
                      },
                    ]}
                  >
                    {(statusMeta as any)[chantier.status]?.label ||
                      chantier.status}
                  </Text>
                </View>
                <View style={styles.chip}>
                  <Ionicons
                    name="cube"
                    size={12}
                    color={colors.textSecondary}
                  />
                  <Text style={styles.chipText}>
                    {mesures.length} ouverture{mesures.length > 1 ? "s" : ""}
                  </Text>
                </View>
              </View>
            </View>
          )}

          {/* Bloc CONFIG MUR */}
          {chantier?.wall_config &&
            (chantier.wall_config.masonry_type ||
              chantier.wall_config.insulation_mode) && (
              <View style={styles.card}>
                <View style={styles.cardHeaderRow}>
                  <Ionicons name="layers" size={18} color={colors.primary} />
                  <Text style={styles.cardHeaderText}>STRUCTURE DU MUR</Text>
                </View>
                <View style={styles.kvList}>
                  {chantier.wall_config.project_type && (
                    <KV
                      label="Type"
                      value={
                        chantier.wall_config.project_type === "renovation"
                          ? "Rénovation"
                          : "Construction neuve"
                      }
                    />
                  )}
                  {chantier.wall_config.masonry_type && (
                    <KV
                      label="Maçonnerie"
                      value={
                        masonryLabels[chantier.wall_config.masonry_type] ||
                        chantier.wall_config.masonry_type
                      }
                    />
                  )}
                  {chantier.wall_config.gros_oeuvre_mm != null && (
                    <KV
                      label="Gros œuvre"
                      value={`${chantier.wall_config.gros_oeuvre_mm} mm`}
                    />
                  )}
                  {chantier.wall_config.insulation_mode && (
                    <KV
                      label="Isolation"
                      value={
                        insulationLabels[chantier.wall_config.insulation_mode] ||
                        chantier.wall_config.insulation_mode
                      }
                    />
                  )}
                  {chantier.wall_config.iti_thickness_mm != null && (
                    <KV
                      label="Ép. ITI"
                      value={`${chantier.wall_config.iti_thickness_mm} mm`}
                    />
                  )}
                  {chantier.wall_config.ite_insul_thickness_mm != null && (
                    <KV
                      label="Ép. ITE"
                      value={`${chantier.wall_config.ite_insul_thickness_mm} mm`}
                    />
                  )}
                </View>
              </View>
            )}

          {/* Bloc OUVERTURES */}
          <View style={styles.card}>
            <View style={styles.cardHeaderRow}>
              <Ionicons name="grid" size={18} color={colors.primary} />
              <Text style={styles.cardHeaderText}>
                OUVERTURES ({mesures.length})
              </Text>
            </View>
            {mesures.length === 0 ? (
              <Text style={styles.help}>Aucune mesure enregistrée.</Text>
            ) : (
              mesures.map((m, i) => {
                const isTrap = m.block_type === "trapeze";
                const isDoor =
                  m.block_type === "porte_entree" ||
                  m.block_type === "porte_garage" ||
                  m.block_type === "coulissant_levant";
                return (
                  <View key={m.id || i} style={styles.mesureItem}>
                    <View style={styles.mesureHeader}>
                      <Text style={styles.mesureLabel} numberOfLines={1}>
                        {m.label || `Châssis ${i + 1}`}
                      </Text>
                      <Text style={styles.mesureShape}>{shapeLabel(m)}</Text>
                    </View>
                    <View style={styles.dimsRow}>
                      <DimChip label="L" value={fmt(m.bay_width)} unit="mm" />
                      {isTrap ? (
                        <>
                          <DimChip
                            label="H gauche"
                            value={fmt(m.height_left)}
                            unit="mm"
                          />
                          <DimChip
                            label="H droite"
                            value={fmt(m.height_right)}
                            unit="mm"
                          />
                        </>
                      ) : (
                        <DimChip
                          label="H"
                          value={fmt(m.bay_height)}
                          unit="mm"
                        />
                      )}
                      {!isTrap && m.bay_diagonal_1 != null && (
                        <DimChip
                          label={`D1${m.diag_1_verified ? " ✓" : ""}`}
                          value={fmt(m.bay_diagonal_1)}
                          unit="mm"
                        />
                      )}
                      {!isTrap && m.bay_diagonal_2 != null && (
                        <DimChip
                          label={`D2${m.diag_2_verified ? " ✓" : ""}`}
                          value={fmt(m.bay_diagonal_2)}
                          unit="mm"
                        />
                      )}
                      {isDoor && m.floor_reserve != null && (
                        <DimChip
                          label="Réserve sol"
                          value={fmt(m.floor_reserve)}
                          unit="mm"
                        />
                      )}
                    </View>
                    {Array.isArray(m.alerts) && m.alerts.length > 0 && (
                      <View style={styles.alertRow}>
                        <Ionicons
                          name="warning"
                          size={12}
                          color={colors.alert}
                        />
                        <Text style={styles.alertText} numberOfLines={2}>
                          {m.alerts.join(" · ")}
                        </Text>
                      </View>
                    )}
                  </View>
                );
              })
            )}
          </View>

          {/* Footer CTA */}
          <View style={styles.footerTip}>
            <Ionicons
              name="information-circle"
              size={16}
              color={colors.alert}
            />
            <Text style={styles.footerTipText}>
              Touchez « PARTAGER » pour générer et envoyer le PDF complet via
              Mail, Files, AirDrop ou une autre app.
            </Text>
          </View>
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

// ── Sub-components ────────────────────────────────────────────────────
const KV = ({ label, value }: { label: string; value: string }) => (
  <View style={styles.kvRow}>
    <Text style={styles.kvLabel}>{label}</Text>
    <Text style={styles.kvValue}>{value}</Text>
  </View>
);

const DimChip = ({
  label,
  value,
  unit,
}: {
  label: string;
  value: string;
  unit: string;
}) => (
  <View style={styles.dimChip}>
    <Text style={styles.dimChipLabel}>{label}</Text>
    <Text style={styles.dimChipValue}>
      {value} <Text style={styles.dimChipUnit}>{unit}</Text>
    </Text>
  </View>
);

// ── Styles ────────────────────────────────────────────────────────────
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
  scrollBody: {
    padding: 14,
    gap: 14,
    paddingBottom: 60,
  },
  card: {
    backgroundColor: colors.surface,
    borderRadius: 14,
    padding: 14,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    gap: 8,
  },
  cardHeaderRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginBottom: 2,
  },
  cardHeaderText: {
    color: colors.textSecondary,
    fontWeight: "800",
    fontSize: 11,
    letterSpacing: 1.2,
  },
  clientName: {
    color: colors.textPrimary,
    fontWeight: "900",
    fontSize: 18,
    letterSpacing: 0.2,
  },
  address: {
    color: colors.textSecondary,
    fontSize: 13,
    marginTop: 2,
  },
  chipRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 6,
    marginTop: 8,
  },
  chip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 999,
    backgroundColor: colors.bg,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
  },
  chipText: {
    color: colors.textPrimary,
    fontSize: 11,
    fontWeight: "700",
    letterSpacing: 0.3,
  },
  kvList: { gap: 6 },
  kvRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 4,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.borderSubtle,
  },
  kvLabel: {
    color: colors.textSecondary,
    fontSize: 12,
    fontWeight: "600",
  },
  kvValue: {
    color: colors.textPrimary,
    fontSize: 13,
    fontWeight: "700",
  },
  mesureItem: {
    paddingVertical: 10,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.borderSubtle,
    gap: 8,
  },
  mesureHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    gap: 8,
  },
  mesureLabel: {
    color: colors.textPrimary,
    fontWeight: "900",
    fontSize: 14,
    flex: 1,
  },
  mesureShape: {
    color: colors.primary,
    fontSize: 10,
    fontWeight: "800",
    letterSpacing: 0.5,
    textTransform: "uppercase",
  },
  dimsRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 6,
  },
  dimChip: {
    backgroundColor: colors.bg,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    borderRadius: 8,
    paddingHorizontal: 8,
    paddingVertical: 4,
    minWidth: 70,
  },
  dimChipLabel: {
    color: colors.textSecondary,
    fontSize: 9,
    fontWeight: "700",
    letterSpacing: 0.4,
    textTransform: "uppercase",
  },
  dimChipValue: {
    color: colors.textPrimary,
    fontSize: 13,
    fontWeight: "900",
    marginTop: 1,
  },
  dimChipUnit: {
    color: colors.textSecondary,
    fontSize: 9,
    fontWeight: "600",
  },
  alertRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingTop: 4,
  },
  alertText: {
    color: colors.alert,
    fontSize: 11,
    fontWeight: "600",
    flex: 1,
  },
  footerTip: {
    flexDirection: "row",
    gap: 8,
    padding: 12,
    backgroundColor: colors.surface,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    alignItems: "flex-start",
  },
  footerTipText: {
    flex: 1,
    color: colors.textSecondary,
    fontSize: 12,
    lineHeight: 17,
  },
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
