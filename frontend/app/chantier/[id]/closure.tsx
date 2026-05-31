import React, { useCallback, useState } from "react";
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
import * as Print from "expo-print";
import * as Sharing from "expo-sharing";
import { useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { api, buildAuthHeaders, PDF_URL } from "@/src/services/api";
import { useAuth } from "@/src/context/AuthContext";
import { colors, blockMeta, statusMeta, NEXT_STATUS, CLOSURE_BUTTON_LABEL_BY_STATUS, CLOSURE_BUTTON_LABEL, CLOSURE_DESCRIPTION_BY_STATUS } from "@/src/theme";

type Chantier = {
  id: string;
  client_name: string;
  address: string;
  status: string;
  created_at: string;
};

type Mesure = {
  id: string;
  block_type: string;
  label: string;
  alerts?: string[];
  slope_angle_deg?: number | null;
  [k: string]: any;
};

export default function Closure() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const [chantier, setChantier] = useState<Chantier | null>(null);
  const [mesures, setMesures] = useState<Mesure[]>([]);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const { artisanMode, company } = useAuth();

  const fetchAll = useCallback(async () => {
    try {
      const [c, m] = await Promise.all([
        api.get<Chantier>(`/chantiers/${id}`),
        api.get<Mesure[]>(`/chantiers/${id}/mesures`),
      ]);
      setChantier(c.data);
      setMesures(m.data);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useFocusEffect(
    useCallback(() => {
      fetchAll();
    }, [fetchAll])
  );

  const exportPDF = async () => {
    setExporting(true);
    try {
      const headers = await buildAuthHeaders();
      const r = await fetch(PDF_URL(String(id)), { headers });
      const blob = await r.blob();
      // Convert blob -> base64 -> file URI usable by Sharing
      const reader = new FileReader();
      reader.onload = async () => {
        const base64data = (reader.result as string).split(",")[1];
        const FS = await import("expo-file-system/legacy");
        const fileUri = `${FS.cacheDirectory}chantier-${id}.pdf`;
        await FS.writeAsStringAsync(fileUri, base64data, {
          encoding: FS.EncodingType.Base64,
        });
        if (await Sharing.isAvailableAsync()) {
          await Sharing.shareAsync(fileUri, { mimeType: "application/pdf" });
        } else {
          Alert.alert("PDF prêt", `Fichier : ${fileUri}`);
        }
      };
      reader.readAsDataURL(blob);
    } catch (e) {
      // Fallback to expo-print with simple HTML
      try {
        const html = buildHtml(chantier!, mesures);
        const { uri } = await Print.printToFileAsync({ html });
        if (await Sharing.isAvailableAsync()) await Sharing.shareAsync(uri);
      } catch {
        Alert.alert("Erreur", "Export PDF indisponible.");
      }
    } finally {
      setExporting(false);
    }
  };

  const exportJSON = async () => {
    try {
      const res = await api.get(`/chantiers/${id}/export.json`);
      const FS = await import("expo-file-system/legacy");
      const fileUri = `${FS.cacheDirectory}chantier-${id}.json`;
      await FS.writeAsStringAsync(fileUri, JSON.stringify(res.data, null, 2));
      if (await Sharing.isAvailableAsync()) {
        await Sharing.shareAsync(fileUri, { mimeType: "application/json" });
      } else {
        Alert.alert("JSON prêt", `Fichier : ${fileUri}`);
      }
    } catch {
      Alert.alert("Erreur", "Export JSON impossible.");
    }
  };

  const exportXLSX = async () => {
    try {
      const headers = await buildAuthHeaders();
      const r = await fetch(
        `${process.env.EXPO_PUBLIC_BACKEND_URL}/api/chantiers/${id}/export.xlsx`,
        { headers }
      );
      if (!r.ok) throw new Error("xlsx failed");
      const blob = await r.blob();
      const reader = new FileReader();
      reader.onload = async () => {
        const b64 = (reader.result as string).split(",")[1];
        const FS = await import("expo-file-system/legacy");
        const fileUri = `${FS.cacheDirectory}chantier-${id}.xlsx`;
        await FS.writeAsStringAsync(fileUri, b64, { encoding: FS.EncodingType.Base64 });
        if (await Sharing.isAvailableAsync()) {
          await Sharing.shareAsync(fileUri, {
            mimeType:
              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
          });
        } else {
          Alert.alert("Excel prêt", `Fichier : ${fileUri}`);
        }
      };
      reader.readAsDataURL(blob);
    } catch {
      Alert.alert("Erreur", "Export Excel impossible.");
    }
  };

  // ---- Closure handler ----
  // Workflow différencié :
  //  • Mode Artisan / Solo : pipeline 4-étapes adapté au flux solo :
  //       devis_a_faire        → a_mesurer            (commande validée, mesurage en cours)
  //       a_mesurer            → technique_a_valider  (mesures finies, encodage bureau)
  //       technique_a_valider  → en_fabrication       (encodage validé, envoi en fab)
  //       en_fabrication       → cloture              (chantier livré)
  //  • Mode Entreprise : pipeline équipe (Admin → Commercial → Technicien).
  const currentStage = chantier ? statusMeta[chantier.status]?.stage : null;
  const isArtisanAccount =
    (company?.account_type || "").toLowerCase() === "artisan";
  const isArtisanFlow = artisanMode || isArtisanAccount;

  // NEXT_STATUS spécifique au mode Artisan (4 étapes : ne saute aucun statut)
  const ARTISAN_NEXT_STATUS: Record<string, string> = {
    devis_a_faire: "a_mesurer",
    a_mesurer: "technique_a_valider",
    technique_a_valider: "en_fabrication",
    en_fabrication: "cloture",
  };
  // Labels & descriptions clairs en mode Artisan (un seul utilisateur joue
  // tous les rôles, terminologie adaptée à son contexte solo).
  const ARTISAN_LABELS: Record<string, string> = {
    devis_a_faire: "✅ Coordonnées validées, démarrer le mesurage",
    a_mesurer: "📐 Mesures terminées, passer à l'encodage bureau",
    technique_a_valider: "💻 Encodage bureau validé, envoyer en fabrication",
    en_fabrication: "🏁 Marquer comme terminé / livré",
  };
  const ARTISAN_DESCRIPTIONS: Record<string, string> = {
    devis_a_faire:
      "Les coordonnées du client sont prêtes. Le chantier passera en « À mesurer ».",
    a_mesurer:
      "Toutes les ouvertures sont mesurées. Le chantier passera en « Encodage bureau » pour saisir la commande au calme au bureau.",
    technique_a_valider:
      "L'encodage de la commande est terminé. Le chantier passera en « En fabrication ».",
    en_fabrication:
      "Le chantier est terminé et livré au client. Il sera archivé.",
  };

  const nextStatus = chantier
    ? isArtisanFlow
      ? ARTISAN_NEXT_STATUS[chantier.status] || null
      : NEXT_STATUS[chantier.status]
    : null;
  const nextLabel = chantier
    ? isArtisanFlow
      ? ARTISAN_LABELS[chantier.status] || "🚩 Étape suivante"
      : CLOSURE_BUTTON_LABEL_BY_STATUS[chantier.status] ||
        (currentStage ? CLOSURE_BUTTON_LABEL[currentStage] : null)
    : null;
  const nextDescription = chantier
    ? isArtisanFlow
      ? ARTISAN_DESCRIPTIONS[chantier.status]
      : CLOSURE_DESCRIPTION_BY_STATUS[chantier.status]
    : null;

  const performClosure = useCallback(async () => {
    if (!nextStatus) return;
    try {
      await api.patch(`/chantiers/${id}`, { status: nextStatus });
      if (Platform.OS === "web") {
        router.replace("/dashboard");
      } else {
        const isFinal = nextStatus === "cloture";
        Alert.alert(
          isFinal ? "✅ Chantier terminé / livré" : "✅ Étape validée",
          isFinal
            ? "Le chantier est marqué 'Terminé / Livré'. Le PDF, CSV et JSON sont prêts pour export."
            : "Le statut du chantier vient d'avancer dans le pipeline. Vous serez redirigé vers le Dashboard.",
          [{ text: "OK", onPress: () => router.replace("/dashboard") }]
        );
      }
    } catch (e: any) {
      const msg =
        e?.response?.status === 403
          ? "Vous n'avez pas les droits pour cette action."
          : "Action impossible.";
      Alert.alert("Erreur", msg);
    }
  }, [id, router, nextStatus]);

  const cloturer = () => {
    if (!nextStatus || !chantier) return;
    const description =
      CLOSURE_DESCRIPTION_BY_STATUS[chantier.status] ||
      `Le chantier passera en « ${statusMeta[nextStatus]?.label ?? nextStatus} ».`;
    const confirmText =
      nextStatus === "cloture"
        ? "Marquer ce chantier comme « Terminé / Livré » ?\n\nIl sera archivé en lecture seule. Vous pourrez toujours consulter les mesures et les exports."
        : description;
    if (Platform.OS === "web") {
      const ok = typeof window !== "undefined" && window.confirm(confirmText);
      if (ok) performClosure();
      return;
    }
    Alert.alert(
      nextStatus === "cloture"
        ? "Clôturer définitivement ?"
        : "Confirmer la transition ?",
      confirmText,
      [
        { text: "Annuler", style: "cancel" },
        {
          text:
            nextStatus === "cloture"
              ? "Oui, clôturer"
              : "Oui, confirmer",
          style: "destructive",
          onPress: performClosure,
        },
      ]
    );
  };

  if (loading || !chantier) {
    return (
      <View style={[styles.flex, styles.center]}>
        <ActivityIndicator color={colors.primary} size="large" />
      </View>
    );
  }

  const totalAlerts = mesures.reduce((acc, m) => acc + (m.alerts?.length ?? 0), 0);
  const meta = statusMeta[chantier.status];

  return (
    <SafeAreaView style={styles.flex} edges={["bottom"]}>
      <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 60 }}>
        <View style={styles.summaryCard}>
          <Text style={styles.cardSection}>RÉSUMÉ</Text>
          <Text style={styles.clientName}>{chantier.client_name}</Text>
          <Text style={styles.addr}>{chantier.address}</Text>
          {meta && (
            <View style={[styles.badge, { backgroundColor: meta.bg }]}>
              <Text style={[styles.badgeText, { color: meta.color }]}>{meta.label}</Text>
            </View>
          )}
        </View>

        <View style={styles.statsRow}>
          <View style={styles.statCard}>
            <Text style={styles.statValue}>{mesures.length}</Text>
            <Text style={styles.statLabel}>Ouvertures</Text>
          </View>
          <View style={styles.statCard}>
            <Text style={[styles.statValue, totalAlerts > 0 && { color: colors.alert }]}>
              {totalAlerts}
            </Text>
            <Text style={styles.statLabel}>Alertes</Text>
          </View>
        </View>

        <Text style={styles.section}>DÉTAIL DES MESURES</Text>
        {mesures.length === 0 && (
          <Text style={styles.empty}>Aucune mesure enregistrée.</Text>
        )}
        {mesures.map((m, idx) => {
          const block = blockMeta[m.block_type] ?? { label: m.block_type, icon: "square-outline" };
          return (
            <View key={m.id} style={styles.mesureCard}>
              <Text style={styles.mesureTitle}>
                #{idx + 1} · {m.label}
              </Text>
              <Text style={styles.mesureType}>{block.label}</Text>
              <View style={styles.gridDim}>
                {dimensionFields(m).map((d) => (
                  <View key={d.label} style={styles.dimItem}>
                    <Text style={styles.dimLabel}>{d.label}</Text>
                    <Text style={styles.dimValue}>
                      {typeof d.value === "number" ? `${d.value} mm` : String(d.value)}
                    </Text>
                  </View>
                ))}
              </View>
              {m.slope_angle_deg != null && (
                <Text style={styles.slope}>Pente : {m.slope_angle_deg}°</Text>
              )}
              {m.alerts && m.alerts.length > 0 && (
                <View style={styles.alertsBox}>
                  {m.alerts.map((a, i) => (
                    <Text key={i} style={styles.alertText}>
                      {a}
                    </Text>
                  ))}
                </View>
              )}
            </View>
          );
        })}

        <View style={styles.actions}>
          {/* === Exports déplacés vers la page Détail Chantier === */}
          {/* SIGNATURE BLOCK REMOVED — application gère uniquement des mesures brutes. */}

          {nextStatus && nextLabel && (
            <>
              {nextDescription && (
                <View style={styles.transitionInfoBox}>
                  <Ionicons
                    name="information-circle"
                    size={20}
                    color={colors.primary}
                  />
                  <Text style={styles.transitionInfoText}>
                    {nextDescription}
                  </Text>
                </View>
              )}
              <TouchableOpacity
                testID="confirm-closure-button"
                onPress={cloturer}
                style={[styles.btn, styles.btnDanger]}
                activeOpacity={0.85}
              >
                <Ionicons name="flag" size={20} color="#fff" />
                <Text style={styles.btnDangerText}>{nextLabel}</Text>
              </TouchableOpacity>
            </>
          )}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

function dimensionFields(m: any): { label: string; value: number | string }[] {
  const out: { label: string; value: number | string }[] = [];
  const map: [string, string][] = [
    ["bay_height", "Hauteur (baie)"],
    ["bay_width", "Largeur (baie)"],
    ["bay_diagonal", "Diagonale"],
    ["floor_reserve", "Réserve Sol Fini"],
    ["bloc_thickness", "Épais. Bloc Béton"],
    ["insulation_thickness", "Épais. Isolant"],
    ["finish_outer", "Finition ext."],
    ["finish_inner", "Finition int."],
    // Legacy
    ["width_top", "L. haut"],
    ["width_middle", "L. milieu"],
    ["width_bottom", "L. bas"],
    ["height_left", "H. gauche"],
    ["height_middle", "H. milieu"],
    ["height_right", "H. droite"],
    ["diag_1", "Diag 1"],
    ["diag_2", "Diag 2"],
    ["height_quarter_left", "H. ¼ G"],
    ["height_quarter_right", "H. ¼ D"],
    ["height_small", "H. petite"],
    ["height_large", "H. grande"],
    ["width_small", "L. petite"],
    ["width_intermediate", "L. inter."],
  ];
  for (const [k, l] of map) if (m[k] != null) out.push({ label: l, value: m[k] });
  if (m.wall_type) {
    out.push({
      label: "Type paroi",
      value:
        m.wall_type === "ite"
          ? "ITE"
          : m.wall_type === "iti"
          ? "ITI"
          : "Crépi simple",
    });
  }
  return out;
}

function buildHtml(c: Chantier, ms: Mesure[]) {
  return `<html><body style="font-family:Helvetica"><h1>MesureChâssis</h1><h2>${c.client_name}</h2><p>${c.address}</p><hr/>${ms
    .map(
      (m, i) =>
        `<h3>#${i + 1} ${m.label} (${m.block_type})</h3><pre>${JSON.stringify(m, null, 2)}</pre>`
    )
    .join("")}</body></html>`;
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: colors.bg },
  center: { alignItems: "center", justifyContent: "center" },
  summaryCard: {
    backgroundColor: colors.surface,
    padding: 18,
    borderRadius: 12,
    borderColor: colors.borderSubtle,
    borderWidth: 1,
  },
  cardSection: {
    color: colors.textSecondary,
    fontSize: 11,
    letterSpacing: 1.5,
    fontWeight: "800",
  },
  clientName: { color: colors.textPrimary, fontSize: 22, fontWeight: "900", marginTop: 6 },
  addr: { color: colors.textSecondary, marginTop: 2, fontSize: 13 },
  badge: { alignSelf: "flex-start", paddingHorizontal: 10, paddingVertical: 5, borderRadius: 4, marginTop: 12 },
  badgeText: { fontWeight: "800", letterSpacing: 0.8, fontSize: 11, textTransform: "uppercase" },
  statsRow: { flexDirection: "row", marginTop: 14, gap: 12 },
  statCard: {
    flex: 1,
    backgroundColor: colors.surface,
    padding: 14,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
  },
  statValue: { color: colors.primary, fontSize: 26, fontWeight: "900" },
  statLabel: { color: colors.textSecondary, fontSize: 11, fontWeight: "700", textTransform: "uppercase" },
  section: {
    marginTop: 22,
    color: colors.textSecondary,
    fontSize: 12,
    letterSpacing: 1.5,
    fontWeight: "800",
    marginBottom: 8,
  },
  empty: { color: colors.textSecondary, fontStyle: "italic" },
  mesureCard: {
    backgroundColor: colors.surface,
    borderColor: colors.borderSubtle,
    borderWidth: 1,
    borderRadius: 10,
    padding: 14,
    marginBottom: 10,
  },
  mesureTitle: { color: colors.textPrimary, fontWeight: "900", fontSize: 15 },
  mesureType: { color: colors.textSecondary, fontSize: 12, marginTop: 2, marginBottom: 8 },
  gridDim: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  dimItem: {
    backgroundColor: colors.bg,
    borderColor: colors.borderSubtle,
    borderWidth: 1,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 6,
  },
  dimLabel: { color: colors.textSecondary, fontSize: 10, textTransform: "uppercase" },
  dimValue: { color: colors.textPrimary, fontWeight: "800", fontSize: 13 },
  slope: { marginTop: 8, color: colors.primary, fontWeight: "700" },
  alertsBox: {
    marginTop: 10,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: colors.borderSubtle,
    gap: 4,
  },
  alertText: { color: colors.alert, fontSize: 12, fontWeight: "700" },
  actions: { marginTop: 24, gap: 10 },
  btn: {
    minHeight: 64,
    borderRadius: 8,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
  },
  btnPrimary: { backgroundColor: colors.primary },
  btnPrimaryText: { color: "#000", fontWeight: "900", letterSpacing: 1 },
  btnSecondary: { borderWidth: 2, borderColor: colors.borderStrong },
  btnSecondaryText: { color: colors.textPrimary, fontWeight: "800", letterSpacing: 1 },
  btnDanger: { backgroundColor: "#7a1d1d" },
  btnDangerText: { color: "#fff", fontWeight: "900", letterSpacing: 1 },
  transitionInfoBox: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 10,
    padding: 14,
    marginBottom: 12,
    backgroundColor: "rgba(255, 107, 26, 0.08)",
    borderLeftWidth: 3,
    borderLeftColor: colors.primary,
    borderRadius: 8,
  },
  transitionInfoText: {
    flex: 1,
    color: colors.textPrimary,
    fontSize: 13,
    lineHeight: 19,
  },
  sigCard: {
    marginTop: 14,
    padding: 16,
    backgroundColor: colors.surface,
    borderColor: colors.borderSubtle,
    borderWidth: 1,
    borderRadius: 12,
  },
  sigHeader: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 10 },
  sigTitle: { color: colors.textPrimary, fontWeight: "900", letterSpacing: 1.2, fontSize: 13 },
  sigHelp: { color: colors.textSecondary, marginBottom: 10, fontSize: 13 },
  sigPreview: {
    width: "100%",
    height: 160,
    backgroundColor: "#F4F1EA",
    borderRadius: 8,
    marginBottom: 8,
  },
  sigDate: { color: colors.textSecondary, fontSize: 12, marginBottom: 6 },
});
