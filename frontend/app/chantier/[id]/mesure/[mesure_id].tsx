/**
 * 👁️ Page de consultation d'une mesure (LECTURE SEULE).
 *
 * SPEC v3 (cahier des charges 10/06/2026) :
 *  - Doit afficher EXACTEMENT toutes les données saisies par le commercial.
 *  - Aucune information technique ne doit manquer.
 *  - Pas de tirets « — » à la place des valeurs : si la donnée n'a pas été
 *    saisie, on masque carrément la ligne (au lieu d'afficher un tiret).
 *  - Le verrou « Mode consultation » reste affiché.
 *
 * Sections affichées (dans l'ordre de saisie) :
 *  1. Photo (ou placeholder)
 *  2. Identification : libellé, type, forme
 *  3. Structure du mur : maçonnerie, gros œuvre, isolation, parement
 *  4. Cotes principales : largeur, hauteur(s), diagonales selon la forme
 *  5. Cotes spécifiques à la forme :
 *      - Arc (plein cintre / arc surbaissé) : H1, H2, arc calculé/mesuré
 *      - Pan coupé (angle 90°) : côté(s), Hg, Hd, pan L/H, angle
 *      - Polygone : nb arêtes, longueur, angle sommet, bbox
 *      - Trapèze : 3 largeurs (haut/milieu/bas) + 3 hauteurs (gauche/milieu/droite)
 *      - Œil-de-bœuf : diamètre
 *      - Porte d'entrée : trait 1m, réserve sol
 *      - Bow-window : nombre de panneaux, projection
 *  6. Feuillures
 *  7. Notes & alertes
 */
import React, { useEffect, useMemo, useState } from "react";
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
  bay_width?: number | null;
  bay_height?: number | null;
  bay_diagonal?: number | null;
  bay_diagonal_1?: number | null;
  bay_diagonal_2?: number | null;
  diag_1_verified?: boolean | null;
  diag_2_verified?: boolean | null;
  height_left?: number | null;
  height_middle?: number | null;
  height_right?: number | null;
  width_top?: number | null;
  width_middle?: number | null;
  width_bottom?: number | null;
  height_quarter_left?: number | null;
  height_quarter_right?: number | null;
  height_small?: number | null;
  height_large?: number | null;
  width_small?: number | null;
  width_intermediate?: number | null;
  floor_reserve?: number | null;
  bloc_thickness?: number | null;
  wall_type?: string | null;
  insulation_thickness?: number | null;
  finish_outer?: number | null;
  finish_inner?: number | null;
  slope_angle_deg?: number | null;
  photo_url?: string | null;
  notes?: string | null;
  options?: Record<string, any> | null;
  alerts?: string[] | null;
};

const BLOCK_LABELS: Record<string, string> = {
  fenetre: "Fenêtre",
  porte_fenetre: "Porte-fenêtre",
  porte: "Porte",
  porte_garage: "Porte de garage",
  porte_entree: "Porte d'entrée",
  baie_vitree: "Baie vitrée",
  velux: "Vélux",
};

const SHAPE_LABELS: Record<string, string> = {
  rect: "Rectangle / Carré",
  rectangle: "Rectangle",
  trapeze: "Trapèze",
  triangle: "Triangle",
  oeil_de_boeuf: "Œil-de-bœuf",
  coulissant_levant: "Coulissant levant",
  arc: "Arc",
  arc_surbaisse: "Arc surbaissé",
  plein_cintre: "Plein cintre",
  angle_90: "Pan coupé",
  bow_window: "Bow-Window",
  pentagone: "Pentagone",
  hexagone: "Hexagone",
  rond: "Rond",
  ovale: "Ovale",
  polygone: "Polygone",
  porte_garage: "Porte de garage",
  porte_entree: "Porte d'entrée",
};

const MASONRY_LABELS: Record<string, string> = {
  pierre: "Pierre",
  bloc_beton: "Bloc béton",
  brique: "Brique",
  beton_arme: "Béton armé",
  bois: "Bois",
  metal: "Métal",
};
const WALL_TYPE_LABELS: Record<string, string> = {
  full_no_insulation: "Mur plein sans isolation",
  ite: "Isolation par l'extérieur (ITE)",
  iti: "Isolation par l'intérieur (ITI)",
  brique_parement: "Brique de parement",
  crepi_simple: "Crépi simple",
  crepi_double: "Crépi double",
  bardage: "Bardage",
  enduit: "Enduit",
};

/** Formate une valeur numérique en mm. Renvoie null si la valeur est absente. */
function fmtMm(v: number | null | undefined): string | null {
  if (v == null || !Number.isFinite(v)) return null;
  return `${Math.round(v).toLocaleString("fr-FR")} mm`;
}

/** Convertit une valeur boolean en libellé visuel. */
function fmtBool(v: boolean | null | undefined): string | null {
  if (v == null) return null;
  return v ? "✓ Oui" : "✗ Non";
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
        if (!cancelled) setMesure(res.data);
      } catch {
        /* silent */
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [mesure_id]);

  const trueShape = useMemo(() => {
    if (!mesure) return "rect";
    return (
      mesure.options?.shape ||
      (mesure.block_type === "porte_garage"
        ? "porte_garage"
        : mesure.block_type === "porte_entree"
          ? "porte_entree"
          : "rect")
    );
  }, [mesure]);

  if (loading) {
    return (
      <SafeAreaView style={[styles.safe, styles.center]}>
        <ActivityIndicator color={colors.primary} />
      </SafeAreaView>
    );
  }
  if (!mesure) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
            <Ionicons name="chevron-back" size={24} color={colors.textPrimary} />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Mesure introuvable</Text>
          <View style={{ width: 36 }} />
        </View>
      </SafeAreaView>
    );
  }

  const opt: Record<string, any> = mesure.options || {};
  const blockLabel = BLOCK_LABELS[mesure.block_type] ?? mesure.block_type;
  const shapeLabel = SHAPE_LABELS[trueShape] ?? trueShape;

  return (
    <SafeAreaView style={styles.safe} edges={["top", "left", "right"]}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn} activeOpacity={0.7}>
          <Ionicons name="chevron-back" size={24} color={colors.textPrimary} />
        </TouchableOpacity>
        <Text style={styles.headerTitle} numberOfLines={1}>
          👁️ {mesure.label || "Mesure"}
        </Text>
        <View style={{ width: 36 }} />
      </View>

      <View style={styles.lockBanner}>
        <Ionicons name="eye-outline" size={16} color={colors.warning} />
        <Text style={styles.lockBannerText}>
          Mode consultation. Vous ne pouvez pas modifier cette mesure.
        </Text>
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        {/* ── 1. Photo ─────────────────────────────────── */}
        {mesure.photo_url ? (
          <View style={styles.photoWrap}>
            <Image source={{ uri: mesure.photo_url }} style={styles.photo} />
          </View>
        ) : (
          <View style={styles.photoPlaceholder}>
            <ShapeIcon shape={trueShape as any} size={80} color={colors.textSecondary} strokeWidth={1.5} />
            <Text style={styles.photoPlaceholderText}>Pas de photo</Text>
          </View>
        )}

        {/* ── 2. Identification ─────────────────────────── */}
        <Section title="Identification">
          <Row label="Nom de l'ouverture" value={mesure.label} />
          <Row label="Type" value={blockLabel} />
          <Row label="Forme" value={shapeLabel} />
          <Row label="Inclinaison" value={mesure.slope_angle_deg != null ? `${mesure.slope_angle_deg}°` : null} />
        </Section>

        {/* ── 3. Structure du mur ───────────────────────── */}
        {(opt.masonry_type || mesure.bloc_thickness != null || mesure.wall_type || mesure.insulation_thickness != null) && (
          <Section title="Structure du mur">
            <Row label="Maçonnerie" value={MASONRY_LABELS[opt.masonry_type] || opt.masonry_type || null} />
            <Row label="Gros œuvre" value={fmtMm(mesure.bloc_thickness)} />
            <Row label="Type de mur" value={WALL_TYPE_LABELS[mesure.wall_type || ""] || mesure.wall_type || null} />
            <Row label="Épais. isolation" value={fmtMm(mesure.insulation_thickness)} />
            <Row label="Finition ext." value={fmtMm(mesure.finish_outer)} />
            <Row label="Finition int." value={fmtMm(mesure.finish_inner)} />
            <Row label="Parement" value={opt.parement_type ? String(opt.parement_type) : null} />
            <Row label="Épais. parement" value={fmtMm(opt.parement_thickness_mm)} />
          </Section>
        )}

        {/* ── 4. Cotes principales (selon la forme) ─────── */}
        <Section title="Cotes principales">
          <Row label="Largeur" value={fmtMm(mesure.bay_width)} />
          <Row label="Hauteur" value={fmtMm(mesure.bay_height)} />
          <Row label="Diagonale 1" value={fmtMm(mesure.bay_diagonal_1 || mesure.bay_diagonal)} />
          <Row label="Diagonale 1 vérifiée" value={fmtBool(mesure.diag_1_verified)} />
          <Row label="Diagonale 2" value={fmtMm(mesure.bay_diagonal_2)} />
          <Row label="Diagonale 2 vérifiée" value={fmtBool(mesure.diag_2_verified)} />
          <Row label="Réserve sol" value={fmtMm(mesure.floor_reserve)} />
        </Section>

        {/* ── 5a. TRAPÈZE — 3 largeurs + 3 hauteurs ─────── */}
        {trueShape === "trapeze" && (
          <Section title="Cotes trapèze">
            <Row label="Largeur haut" value={fmtMm(mesure.width_top)} />
            <Row label="Largeur milieu" value={fmtMm(mesure.width_middle)} />
            <Row label="Largeur bas" value={fmtMm(mesure.width_bottom)} />
            <Row label="Hauteur gauche" value={fmtMm(mesure.height_left)} />
            <Row label="Hauteur milieu" value={fmtMm(mesure.height_middle)} />
            <Row label="Hauteur droite" value={fmtMm(mesure.height_right)} />
            <Row label="Hauteur quart gauche" value={fmtMm(mesure.height_quarter_left)} />
            <Row label="Hauteur quart droite" value={fmtMm(mesure.height_quarter_right)} />
          </Section>
        )}

        {/* ── 5b. ARC — Plein cintre & Arc surbaissé ────── */}
        {(trueShape === "plein_cintre" || trueShape === "arc_surbaisse") && (
          <Section title="Cotes arc">
            <Row label="Hauteur d'appui H1" value={fmtMm(opt.arch_h1_appui_mm)} />
            <Row label="Hauteur totale H2" value={fmtMm(opt.arch_h2_total_mm)} />
            <Row label="Longueur de l'arc (calculée)" value={fmtMm(opt.arc_computed_mm)} />
            <Row label="Longueur de l'arc (mesurée ruban)" value={fmtMm(opt.arc_measured_mm || opt.perimeter_measured_mm)} />
          </Section>
        )}

        {/* ── 5c. ANGLE 90° / PAN COUPÉ ─────────────────── */}
        {trueShape === "angle_90" && (
          <Section title="Cotes pan coupé">
            <Row
              label="Côté(s) coupé(s)"
              value={
                opt.angle90_side === "left"
                  ? "Gauche"
                  : opt.angle90_side === "both"
                    ? "Les deux"
                    : opt.angle90_side === "right"
                      ? "Droite"
                      : null
              }
            />
            <Row label="Hauteur gauche" value={fmtMm(opt.angle90_h_left_mm || mesure.height_left)} />
            <Row label="Hauteur droite" value={fmtMm(opt.angle90_h_right_mm || mesure.height_right)} />
            <Row label="Largeur du pan" value={fmtMm(opt.angle90_cut_width_mm)} />
            <Row label="Hauteur du pan" value={fmtMm(opt.angle90_cut_height_mm)} />
            <Row label="Angle du pan" value={opt.angle90_angle_deg != null ? `${opt.angle90_angle_deg}°` : null} />
          </Section>
        )}

        {/* ── 5d. POLYGONE ──────────────────────────────── */}
        {trueShape === "polygone" && (
          <Section title="Cotes polygone">
            <Row label="Nombre d'arêtes" value={opt.polygon_edge_count != null ? String(opt.polygon_edge_count) : null} />
            <Row label="Longueur d'une arête" value={fmtMm(opt.polygon_edge_length_mm)} />
            <Row label="Angle d'un sommet" value={opt.polygon_angle_deg != null ? `${opt.polygon_angle_deg}°` : null} />
            <Row label="Largeur hors-tout" value={fmtMm(opt.polygon_bbox_width_mm)} />
            <Row label="Hauteur hors-tout" value={fmtMm(opt.polygon_bbox_height_mm)} />
          </Section>
        )}

        {/* ── 5e. ŒIL-DE-BŒUF ───────────────────────────── */}
        {trueShape === "oeil_de_boeuf" && (
          <Section title="Cotes œil-de-bœuf">
            <Row label="Diamètre" value={fmtMm(opt.diameter_mm || mesure.bay_width)} />
          </Section>
        )}

        {/* ── 5f. OVALE ─────────────────────────────────── */}
        {trueShape === "ovale" && (
          <Section title="Cotes ovale">
            <Row label="Largeur totale" value={fmtMm(mesure.bay_width)} />
            <Row label="Hauteur totale" value={fmtMm(mesure.bay_height)} />
            <Row label="Rayon X (auto)" value={fmtMm(opt.ovale_radius_x_mm)} />
            <Row label="Rayon Y (auto)" value={fmtMm(opt.ovale_radius_y_mm)} />
          </Section>
        )}

        {/* ── 5g. BOW-WINDOW ────────────────────────────── */}
        {trueShape === "bow_window" && (
          <Section title="Cotes bow-window">
            <Row label="Nombre de pans" value={opt.bow_panels != null ? String(opt.bow_panels) : null} />
            <Row label="Projection (P)" value={fmtMm(opt.bow_projection_mm)} />
          </Section>
        )}

        {/* ── 5h. PORTE D'ENTRÉE / COULISSANT LEVANT ─────── */}
        {(trueShape === "porte_entree" || trueShape === "coulissant_levant") && (
          <Section title="Cotes spécifiques">
            <Row label="Trait niveau 1m" value={fmtMm(opt.trait_1m_brut_mm)} />
            <Row label="Réserve sol" value={fmtMm(mesure.floor_reserve)} />
            <Row label="Hauteur sous linteau" value={fmtMm(opt.lintel_height_mm)} />
          </Section>
        )}

        {/* ── 6. Feuillures ─────────────────────────────── */}
        {(opt.feuillure_haut_mm != null ||
          opt.feuillure_bas_mm != null ||
          opt.feuillure_gauche_mm != null ||
          opt.feuillure_droite_mm != null) && (
          <Section title="Feuillures">
            <Row label="Haut" value={fmtMm(opt.feuillure_haut_mm)} />
            <Row label="Bas" value={fmtMm(opt.feuillure_bas_mm)} />
            <Row label="Gauche" value={fmtMm(opt.feuillure_gauche_mm)} />
            <Row label="Droite" value={fmtMm(opt.feuillure_droite_mm)} />
          </Section>
        )}

        {/* ── 7. Notes & alertes ────────────────────────── */}
        {!!mesure.notes && (
          <Section title="Notes">
            <Text style={styles.notesText}>{mesure.notes}</Text>
          </Section>
        )}
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

// ─────────────────────────────────────────────────────────────────────────
// Composants helpers
// ─────────────────────────────────────────────────────────────────────────

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  // On filtre les enfants Row qui n'ont pas de valeur (children[?].props.value = null)
  // pour éviter d'afficher une section quasi vide. Si AUCUN Row n'a de valeur,
  // on masque carrément la section.
  const arr = React.Children.toArray(children);
  const visibleChildren = arr.filter((c: any) => {
    if (!c || !c.props) return true;
    // C'est un Row : on garde si la valeur n'est pas null/vide
    if ("value" in c.props) {
      return c.props.value != null && c.props.value !== "";
    }
    return true;
  });
  if (visibleChildren.length === 0) return null;
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      <View style={styles.sectionBody}>{visibleChildren}</View>
    </View>
  );
}

function Row({ label, value }: { label: string; value: string | null | undefined }) {
  // Conformément au cahier des charges 10/06/2026 : on n'affiche JAMAIS
  // un tiret « — » à la place d'une valeur absente. Soit on a la donnée,
  // soit la ligne est masquée.
  if (value == null || value === "") return null;
  return (
    <View style={styles.row}>
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={styles.rowValue}>{value}</Text>
    </View>
  );
}

// ─────────────────────────────────────────────────────────────────────────
// Styles
// ─────────────────────────────────────────────────────────────────────────
const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  center: { justifyContent: "center", alignItems: "center" },
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
