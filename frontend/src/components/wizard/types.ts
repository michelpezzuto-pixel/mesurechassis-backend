/**
 * Types, constantes et helpers du Wizard "Nouvelle Mesure".
 * Extrait de /app/frontend/app/chantier/[id]/new-mesure.tsx
 * pour réduire la taille du fichier monolithique (refacto V3 — juin 2026).
 */
import { Ionicons } from "@expo/vector-icons";

export type Step = 0 | 1 | 2;
export type ProjectType = "construction" | "renovation";

/** Type de gros œuvre (maçonnerie). */
export type MasonryType = "bloc_beton" | "bloc_terre_cuite" | "brique" | "pierre";

/** Mode d'isolation/finition. */
export type InsulationMode = "none" | "iti" | "ite";

/** Type de parement (uniquement si ITE). */
export type ParementType = "crepi" | "brique_parement" | "pierre_parement" | "bardage";

/** 14 formes V3 (juin 2026). */
export type Shape =
  | "rect"
  | "porte_entree"
  | "porte_garage"
  | "trapeze"
  | "triangle"
  | "oeil_de_boeuf"
  | "coulissant_levant"
  // 🆕 V2 — Formes complémentaires (juin 2026)
  | "plein_cintre"
  | "arc_surbaisse"
  | "angle_90"
  | "bow_window"
  | "pentagone"
  | "hexagone"
  | "ovale"
  // 🆕 V3 — Polygone unifié (cahier 09/06/2026)
  | "polygone";

export type DiagState = "auto" | "validated" | "manual";

export const MASONRIES: { key: MasonryType; label: string; icon: keyof typeof Ionicons.glyphMap }[] = [
  { key: "bloc_beton", label: "Bloc béton", icon: "cube-outline" },
  { key: "bloc_terre_cuite", label: "Bloc Terre cuite", icon: "albums-outline" },
  { key: "brique", label: "Brique", icon: "grid-outline" },
  { key: "pierre", label: "Pierre", icon: "diamond-outline" },
];

export const PAREMENTS: { key: ParementType; label: string; icon: keyof typeof Ionicons.glyphMap }[] = [
  { key: "crepi", label: "Crépi", icon: "color-fill-outline" },
  { key: "brique_parement", label: "Brique parement", icon: "grid-outline" },
  { key: "pierre_parement", label: "Pierre", icon: "diamond-outline" },
  { key: "bardage", label: "Bardage", icon: "leaf-outline" },
];

export const SHAPES: {
  key: Shape;
  letter: string;
  label: string;
  icon: keyof typeof Ionicons.glyphMap;
  desc: string;
}[] = [
  { key: "rect", letter: "A", label: "CARRÉ / RECTANGLE", icon: "square-outline", desc: "Baie standard rectangulaire" },
  { key: "porte_entree", letter: "B", label: "PORTE D'ENTRÉE", icon: "exit-outline", desc: "Avec réserve sol & trait niveau 1m" },
  { key: "porte_garage", letter: "C", label: "PORTE DE GARAGE", icon: "car-outline", desc: "Avec linteau et écoinçons" },
  { key: "trapeze", letter: "D", label: "TRAPÈZE", icon: "triangle-outline", desc: "Hauteur gauche ≠ Hauteur droite" },
  { key: "oeil_de_boeuf", letter: "H", label: "ŒIL-DE-BŒUF", icon: "ellipse-outline", desc: "Ouverture circulaire (diamètre)" },
  { key: "coulissant_levant", letter: "K", label: "COULISSANT LEVANT", icon: "swap-horizontal-outline", desc: "Levant-coulissant avec réserve sol" },
  // 🆕 V2 — Formes complexes
  { key: "plein_cintre", letter: "L", label: "PLEIN CINTRE", icon: "radio-button-on-outline", desc: "Arc parfait en demi-cercle au sommet" },
  { key: "arc_surbaisse", letter: "M", label: "ARC SURBAISSÉ", icon: "remove-outline", desc: "Arc applati (flèche < demi-largeur)" },
  { key: "angle_90", letter: "N", label: "PAN COUPÉ", icon: "git-branch-outline", desc: "Châssis avec coin coupé en oblique" },
  { key: "bow_window", letter: "O", label: "BOW-WINDOW", icon: "infinite-outline", desc: "Baie courbe — plusieurs panneaux" },
  // 🆕 V3 — Polygone unifié (remplace Triangle / Pentagone / Hexagone / Octogone)
  { key: "polygone", letter: "P", label: "POLYGONE", icon: "shapes-outline", desc: "Forme polygonale (3 à 8 arêtes — sommets éditables)" },
  { key: "ovale", letter: "R", label: "OVALE", icon: "ellipse-outline", desc: "Ellipse (axe horizontal + vertical)" },
];

// ════════════════════════════════════════════════════════════════════════
// State shapes
// ════════════════════════════════════════════════════════════════════════
export type Step1Data = {
  project_type: ProjectType;
  // Maçonnerie
  masonry_type: MasonryType | null;
  gros_oeuvre_mm: string;
  // Isolation
  insulation_mode: InsulationMode | null;
  iti_thickness_mm: string;
  // ITE
  ite_insul_thickness_mm: string;
  parement_type: ParementType | null;
  // ITE-Crépi
  crepi_thickness_mm: string;
  // ITE-Brique/Pierre
  coulisse_thickness_mm: string;
  brique_pierre_thickness_mm: string;
  // ITE-Bardage
  structure_lame_air_mm: string;
  // Statut Seuils
  sill_already_installed: boolean | null;
  sill_thickness_mm: string;
  // Options
  has_breastwork: boolean;
  has_horizontal_cut: boolean;
};

export const initStep1 = (): Step1Data => ({
  project_type: "renovation",
  masonry_type: null,
  gros_oeuvre_mm: "",
  insulation_mode: null,
  iti_thickness_mm: "",
  ite_insul_thickness_mm: "",
  parement_type: null,
  crepi_thickness_mm: "",
  coulisse_thickness_mm: "",
  brique_pierre_thickness_mm: "",
  structure_lame_air_mm: "",
  sill_already_installed: null,
  sill_thickness_mm: "",
  has_breastwork: false,
  has_horizontal_cut: false,
});

export type Step3Data = {
  bay_width: string;
  bay_height: string;
  diag_1: string;
  diag_1_state: DiagState;
  diag_2: string;
  diag_2_state: DiagState;
  renovation_mode: boolean;
  width_top: string;
  width_bottom: string;
  height_left: string;
  height_right: string;
  trap_height_left: string;
  trap_height_right: string;
  triangle_base: string;
  triangle_height: string;
  oeil_diameter: string;
  garage_lintel: string;
  garage_ecoincon_left: string;
  garage_ecoincon_right: string;
  // Réserve sol — uniquement porte_entree, porte_garage, coulissant_levant
  floor_reserve: string;
  // 🆕 Trait niveau 1m — quand activé, on saisit la mesure brute et on
  // calcule auto la réserve sol via : reserve = brut - 1000
  has_1m_level_mark: boolean;
  trait_1m_brut_mm: string;
  // 🆕 Feuillures — conditionnelles selon masonry_type (Brique / Pierre / Bloc béton)
  feuillure_left_mm: string;
  feuillure_right_mm: string;
  feuillure_top_mm: string;
  // 🆕 Allège — par-mesure (uniquement formes : rect, trapeze, triangle, oeil)
  has_breastwork: boolean;
  breastwork_height_mm: string;
  // 🆕 V2 — Champs spécifiques aux 7 nouvelles formes
  // 1. Plein cintre & Arc surbaissé
  arch_h1_appui: string; // Hauteur d'appui (côtés droits)
  arch_h2_total: string; // Hauteur totale (au sommet)
  // 3. Angle 90° (coupe d'angle)
  angle90_cut_width: string; // Largeur du pan coupé
  angle90_cut_height: string; // Hauteur du pan coupé
  angle90_side: "left" | "right" | "both"; // Côté(s) coupé(s)
  angle90_angle_deg: string; // Angle du pan (135° par défaut, éditable)
  angle90_h_left: string; // Hauteur gauche (asymétrique)
  angle90_h_right: string; // Hauteur droite (asymétrique)
  // 🆕 V3 — Polygone unifié (3/5/6/8 arêtes)
  polygon_edge_count: "3" | "5" | "6" | "8";
  polygon_edge_length: string; // Longueur uniforme de chaque arête (mm)
  polygon_angle_deg: string;   // Angle de chaque sommet (°) — éditable
  polygon_bbox_width: string;  // Largeur hors-tout (mm)
  polygon_bbox_height: string; // Hauteur hors-tout (mm)
  // 🆕 Vérification PÉRIMÈTRE (formes arc + angle)
  perimeter_measured: string; // Mesure ruban faite par le mesureur (mm)
  // 4. Bow-Window
  bow_panel_count: "3" | "5" | ""; // Nombre de pans
  bow_depth_projection: string; // Profondeur de projection
  // 5. Pentagone (haut pan coupé / toit pointu)
  pent_side_height: string; // Hauteur des côtés verticaux (H1)
  pent_top_height: string; // Hauteur totale au sommet (H2)
  // 6. Hexagone (haut + bas pan coupé)
  hex_top_width: string; // Largeur sommet
  hex_side_height: string; // Hauteur des parties verticales
  // 7. Ovale — utilise bay_width (L) et bay_height (H) déjà existants
};

export const initStep3 = (): Step3Data => ({
  bay_width: "",
  bay_height: "",
  diag_1: "",
  diag_1_state: "manual",
  diag_2: "",
  diag_2_state: "manual",
  renovation_mode: false,
  width_top: "",
  width_bottom: "",
  height_left: "",
  height_right: "",
  trap_height_left: "",
  trap_height_right: "",
  triangle_base: "",
  triangle_height: "",
  oeil_diameter: "",
  garage_lintel: "",
  garage_ecoincon_left: "",
  garage_ecoincon_right: "",
  floor_reserve: "",
  has_1m_level_mark: false,
  trait_1m_brut_mm: "",
  feuillure_left_mm: "",
  feuillure_right_mm: "",
  feuillure_top_mm: "",
  has_breastwork: false,
  breastwork_height_mm: "",
  // 🆕 V2 — Init des champs spécifiques aux 7 nouvelles formes
  arch_h1_appui: "",
  arch_h2_total: "",
  angle90_cut_width: "",
  angle90_cut_height: "",
  angle90_side: "right",
  angle90_angle_deg: "135",
  angle90_h_left: "",
  angle90_h_right: "",
  polygon_edge_count: "6",
  polygon_edge_length: "",
  polygon_angle_deg: "120",
  polygon_bbox_width: "",
  polygon_bbox_height: "",
  perimeter_measured: "",
  bow_panel_count: "",
  bow_depth_projection: "",
  pent_side_height: "",
  pent_top_height: "",
  hex_top_width: "",
  hex_side_height: "",
});

export const parseNum = (s: string) => {
  const n = parseFloat(s.replace(",", "."));
  return Number.isFinite(n) ? n : null;
};

export const shapeToBlockType = (s: Shape): "standard" | "coulissant" | "porte" | "trapeze" => {
  switch (s) {
    case "rect":
    case "oeil_de_boeuf":
    // 🆕 V2 — Toutes les nouvelles formes complexes utilisent "standard"
    //    comme block_type de base (avec options.shape pour préciser).
    case "plein_cintre":
    case "arc_surbaisse":
    case "angle_90":
    case "bow_window":
    case "pentagone":
    case "hexagone":
    case "ovale":
    case "polygone":
      return "standard";
    case "porte_entree":
    case "porte_garage":
      return "porte";
    case "trapeze":
    case "triangle":
      return "trapeze";
    case "coulissant_levant":
      return "coulissant";
  }
};

export const inferShape = (m: any): Shape => {
  const fromOpts = (m?.options?.shape as Shape) || null;
  if (fromOpts) return fromOpts;
  const bt = m?.block_type;
  if (bt === "trapeze") return "trapeze";
  if (bt === "porte") return "porte_entree";
  if (bt === "coulissant") return "rect";
  return "rect";
};

// Feuillures requises pour ces maçonneries
export const masonryHasFeuillures = (m: MasonryType | null): boolean =>
  m === "brique" || m === "pierre" || m === "bloc_beton";
