/**
 * 👁️ Page de consultation d'une mesure (LECTURE SEULE).
 *
 * Accessible à l'Admin (et tout rôle qui n'a pas les droits d'édition) pour
 * visualiser une ouverture sans pouvoir la modifier.
 *
 * Affiche : photo, label, forme/type, dimensions, options, notes.
 */
import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Image,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useLocalSearchParams, useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { api } from "@/src/services/api";
import { colors } from "@/src/theme";
import { ShapeIcon } from "@/src/components/ShapeIcon";

type Mesure = {
  id: string;
  label: string;
  block_type: string;
  largeur_mm?: number;
  hauteur_mm?: number;
  hauteur_min_mm?: number;
  hauteur_max_mm?: number;
  diagonale_a_mm?: number;
  diagonale_b_mm?: number;
  slope_angle_deg?: number;
  photo_url?: string;
  notes?: string;
  options?: Record<string, any>;
  alerts?: string[];
};

const blockLabels: Record<string, string> = {
  fenetre: "Fenêtre",
  porte_fenetre: "Porte-fenêtre",
  porte: "Porte",
  porte_garage: "Porte de garage",
  porte_entree: "Porte d'entrée",
  baie_vitree: "Baie vitrée",
  velux: "Vélux",
};

const shapeLabels: Record<string, string> = {
  rect: "Rectangle / Carré",
  rectangle: "Rectangle",
  trapeze: "Trapèze",
  triangle: "Triangle",
  oeil_de_boeuf: "Œil-de-bœuf",
  coulissant_levant: "Coulissant levant",
  arc: "Arc",
  arc_surbaisse: "Arc surbaissé",
  plein_cintre: "Plein cintre",
  angle_90: "Angle 90°",
  bow_window: "Bow-Window",
  pentagone: "Pentagone (toit pointu)",
  hexagone: "Hexagone",
  rond: "Rond",
  ovale: "Ovale",
  porte_garage: "Porte de garage",
  porte_entree: "Porte d'entrée",
};

function fmtDim(mm?: number): string {
  if (mm == null || isNaN(mm)) return "—";
  return `${mm} mm`;
}

export default function MesureViewScreen() {
  const { id, mesure_id } = useLocalSearchParams<{
    id: string;
    mesure_id: string;
  }>();
  const router = useRouter();
  const [mesure, setMesure] = useState<Mesure | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await api.get<Mesure>(`/mesures/${mesure_id}`);
        if (!cancelled) {
          setMesure(res.data);
        }
      } catch {
        // silent
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [mesure_id]);

  if (loading) {
    return (
      <SafeAreaView
        style={[styles.safe, { justifyContent: "center", alignItems: "center" }]}
      >
        <ActivityIndicator color={colors.primary} />
      </SafeAreaView>
    );
  }

  if (!mesure) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.header}>
          <TouchableOpacity
            onPress={() => router.back()}
            style={styles.backBtn}
            activeOpacity={0.7}
          >
            <Ionicons name="chevron-back" size={24} color={colors.textPrimary} />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Mesure introuvable</Text>
          <View style={{ width: 36 }} />
        </View>
      </SafeAreaView>
    );
  }

  const trueShape: string =
    mesure.options?.shape ||
    (mesure.block_type === "porte_garage"
      ? "porte_garage"
      : mesure.block_type === "porte_entree"
        ? "porte_entree"
        : "rectangle");
  const blockLabel = blockLabels[mesure.block_type] ?? mesure.block_type;
  const shapeLabel = shapeLabels[trueShape] ?? trueShape;

  const opt = mesure.options || {};

  return (
    <SafeAreaView style={styles.safe} edges={["top", "left", "right"]}>
      <View style={styles.header}>
        <TouchableOpacity
          onPress={() => router.back()}
          style={styles.backBtn}
          activeOpacity={0.7}
        >
          <Ionicons name="chevron-back" size={24} color={colors.textPrimary} />
        </TouchableOpacity>
        <Text style={styles.headerTitle} numberOfLines={1}>
          👁️ {mesure.label || "Mesure"}
        </Text>
        <View style={{ width: 36 }} />
      </View>

      {/* 🔒 Bandeau "Lecture seule" */}
      <View style={styles.lockBanner}>
        <Ionicons name="eye-outline" size={16} color={colors.warning} />
        <Text style={styles.lockBannerText}>
          Mode consultation. Vous ne pouvez pas modifier cette mesure.
        </Text>
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        {/* Photo */}
        {mesure.photo_url ? (
          <View style={styles.photoWrap}>
            <Image source={{ uri: mesure.photo_url }} style={styles.photo} />
          </View>
        ) : (
          <View style={styles.photoPlaceholder}>
            <ShapeIcon
              shape={trueShape as any}
              size={80}
              color={colors.textSecondary}
              strokeWidth={1.5}
            />
            <Text style={styles.photoPlaceholderText}>Pas de photo</Text>
          </View>
        )}

        {/* Identité */}
        <Section title="Identification">
          <Row label="Nom de l'ouverture" value={mesure.label || "—"} />
          <Row label="Type" value={blockLabel} />
          <Row label="Forme" value={shapeLabel} />
          {mesure.slope_angle_deg != null && (
            <Row label="Inclinaison" value={`${mesure.slope_angle_deg}°`} />
          )}
        </Section>

        {/* Dimensions */}
        <Section title="Dimensions">
          <Row label="Largeur" value={fmtDim(mesure.largeur_mm)} />
          {mesure.hauteur_mm != null ? (
            <Row label="Hauteur" value={fmtDim(mesure.hauteur_mm)} />
          ) : (
            <>
              {mesure.hauteur_min_mm != null && (
                <Row
                  label="Hauteur min"
                  value={fmtDim(mesure.hauteur_min_mm)}
                />
              )}
              {mesure.hauteur_max_mm != null && (
                <Row
                  label="Hauteur max"
                  value={fmtDim(mesure.hauteur_max_mm)}
                />
              )}
            </>
          )}
          {mesure.diagonale_a_mm != null && (
            <Row
              label="Diagonale A"
              value={fmtDim(mesure.diagonale_a_mm)}
            />
          )}
          {mesure.diagonale_b_mm != null && (
            <Row
              label="Diagonale B"
              value={fmtDim(mesure.diagonale_b_mm)}
            />
          )}
        </Section>

        {/* Détails du mur */}
        {(opt.masonry_type ||
          opt.gros_oeuvre_mm ||
          opt.insul_mode ||
          opt.parement_type) && (
          <Section title="Configuration du mur">
            {opt.masonry_type && (
              <Row label="Maçonnerie" value={String(opt.masonry_type)} />
            )}
            {opt.gros_oeuvre_mm != null && (
              <Row
                label="Gros œuvre"
                value={fmtDim(Number(opt.gros_oeuvre_mm))}
              />
            )}
            {opt.insul_mode && (
              <Row label="Isolation" value={String(opt.insul_mode)} />
            )}
            {opt.parement_type && (
              <Row label="Parement" value={String(opt.parement_type)} />
            )}
            {opt.parement_thickness_mm != null && (
              <Row
                label="Épais. parement"
                value={fmtDim(Number(opt.parement_thickness_mm))}
              />
            )}
          </Section>
        )}

        {/* Feuillures */}
        {(opt.feuillure_haut_mm != null ||
          opt.feuillure_bas_mm != null ||
          opt.feuillure_gauche_mm != null ||
          opt.feuillure_droite_mm != null) && (
          <Section title="Feuillures">
            {opt.feuillure_haut_mm != null && (
              <Row label="Haut" value={fmtDim(Number(opt.feuillure_haut_mm))} />
            )}
            {opt.feuillure_bas_mm != null && (
              <Row label="Bas" value={fmtDim(Number(opt.feuillure_bas_mm))} />
            )}
            {opt.feuillure_gauche_mm != null && (
              <Row
                label="Gauche"
                value={fmtDim(Number(opt.feuillure_gauche_mm))}
              />
            )}
            {opt.feuillure_droite_mm != null && (
              <Row
                label="Droite"
                value={fmtDim(Number(opt.feuillure_droite_mm))}
              />
            )}
          </Section>
        )}

        {/* Notes */}
        {mesure.notes ? (
          <Section title="Notes">
            <Text style={styles.notesText}>{mesure.notes}</Text>
          </Section>
        ) : null}

        {/* Alertes */}
        {mesure.alerts && mesure.alerts.length > 0 && (
          <Section title="⚠️ Alertes">
            {mesure.alerts.map((a, i) => (
              <Text key={i} style={styles.alertText}>
                • {a}
              </Text>
            ))}
          </Section>
        )}

        <View style={{ height: 24 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

// ────────────────────────────────────────────────────────────────────────
// Composants helpers
// ────────────────────────────────────────────────────────────────────────
function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      <View style={styles.sectionBody}>{children}</View>
    </View>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={styles.rowValue}>{value}</Text>
    </View>
  );
}

// ────────────────────────────────────────────────────────────────────────
// Styles
// ────────────────────────────────────────────────────────────────────────
const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 14,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    backgroundColor: colors.card,
  },
  backBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: "center",
    justifyContent: "center",
  },
  headerTitle: {
    flex: 1,
    textAlign: "center",
    color: colors.textPrimary,
    fontSize: 16,
    fontWeight: "800",
  },
  lockBanner: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    backgroundColor: colors.warning + "1A",
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: colors.warning + "55",
  },
  lockBannerText: {
    color: colors.warning,
    fontSize: 13,
    fontWeight: "600",
    flex: 1,
  },
  content: { padding: 14, paddingBottom: 30 },
  photoWrap: {
    width: "100%",
    aspectRatio: 4 / 3,
    backgroundColor: colors.card,
    borderRadius: 12,
    overflow: "hidden",
    marginBottom: 14,
  },
  photo: { width: "100%", height: "100%", resizeMode: "cover" },
  photoPlaceholder: {
    width: "100%",
    aspectRatio: 4 / 3,
    backgroundColor: colors.card,
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 14,
    borderWidth: 1,
    borderColor: colors.border,
    borderStyle: "dashed",
  },
  photoPlaceholderText: {
    color: colors.textSecondary,
    marginTop: 6,
    fontSize: 12,
  },
  section: {
    marginBottom: 14,
    backgroundColor: colors.card,
    borderRadius: 12,
    overflow: "hidden",
    borderWidth: 1,
    borderColor: colors.border,
  },
  sectionTitle: {
    color: colors.textSecondary,
    fontSize: 12,
    fontWeight: "800",
    letterSpacing: 0.6,
    textTransform: "uppercase",
    paddingHorizontal: 14,
    paddingTop: 12,
    paddingBottom: 8,
    backgroundColor: colors.background + "55",
  },
  sectionBody: { paddingHorizontal: 14, paddingVertical: 8 },
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: colors.border + "55",
    gap: 10,
  },
  rowLabel: { color: colors.textSecondary, fontSize: 13 },
  rowValue: {
    color: colors.textPrimary,
    fontSize: 14,
    fontWeight: "700",
    textAlign: "right",
    flexShrink: 1,
  },
  notesText: {
    color: colors.textPrimary,
    fontSize: 14,
    lineHeight: 20,
    paddingVertical: 4,
  },
  alertText: {
    color: colors.warning,
    fontSize: 13,
    lineHeight: 18,
    paddingVertical: 3,
  },
});
