/**
 * ╔══════════════════════════════════════════════════════════════════════╗
 * ║  MesureChâssis — Wizard "Nouvelle Ouverture" — V1.1 PRODUCTION       ║
 * ╠══════════════════════════════════════════════════════════════════════╣
 * ║  Architecture en 3 étapes :                                          ║
 * ║   1. Configuration mur (Maçonnerie + Isolation/Finition dynamique)   ║
 * ║   2. Sélection de la forme (7 formes — sans sous-type ouvrant)       ║
 * ║   3. Cotes adaptatives + feuillures conditionnelles + trait 1m calc  ║
 * ║                                                                      ║
 * ║  Tous les nouveaux champs (masonry_type, gros_oeuvre_mm, insul_mode, ║
 * ║  parement_*, feuillure_*, shape…) sont stockés dans payload.options{}║
 * ║  → rétro-compatibilité 100% du backend. `block_type` mappé proprement║
 * ║  vers les 4 valeurs historiques pour les exports PDF/CSV/XLSX/JSON.  ║
 * ╚══════════════════════════════════════════════════════════════════════╝
 */
import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Image,
  KeyboardAvoidingView,
  Modal,
  Platform,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import * as ImagePicker from "expo-image-picker";
import { useLocalSearchParams, useRouter } from "expo-router";
import {
  RawBaySchemaRect,
  RawBaySchemaTrapeze,
  WallSection,
} from "@/src/components/WindowSchema";
import { api } from "@/src/services/api";
import { enqueueMesure, isOnline } from "@/src/services/offlineQueue";
import { colors } from "@/src/theme";
import { ShapeIcon } from "@/src/components/ShapeIcon";
import { MeasureGuide } from "@/src/components/MeasureGuide";
import ShapeSchemaV2 from "@/src/components/ShapeSchemaV2";
import PerimeterVerification from "@/src/components/PerimeterVerification";
import {
  perimeterPleinCintre,
  perimeterArcSurbaisse,
  perimeterAngle90,
} from "@/src/utils/perimeter";
import { useResponsive } from "@/src/utils/responsive";

// ════════════════════════════════════════════════════════════════════════
// Types & constantes
// ════════════════════════════════════════════════════════════════════════

type Step = 0 | 1 | 2;

type ProjectType = "construction" | "renovation";

/** Type de gros œuvre (maçonnerie). */
type MasonryType = "bloc_beton" | "bloc_terre_cuite" | "brique" | "pierre";

/** Mode d'isolation/finition. */
type InsulationMode = "none" | "iti" | "ite";

/** Type de parement (uniquement si ITE). */
type ParementType = "crepi" | "brique_parement" | "pierre_parement" | "bardage";

/** 14 formes V2 (7 V1 + 7 nouvelles formes complexes). */
type Shape =
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
  | "ovale";

type DiagState = "auto" | "validated" | "manual";

const MASONRIES: { key: MasonryType; label: string; icon: keyof typeof Ionicons.glyphMap }[] = [
  { key: "bloc_beton", label: "Bloc béton", icon: "cube-outline" },
  { key: "bloc_terre_cuite", label: "Bloc Terre cuite", icon: "albums-outline" },
  { key: "brique", label: "Brique", icon: "grid-outline" },
  { key: "pierre", label: "Pierre", icon: "diamond-outline" },
];

const PAREMENTS: { key: ParementType; label: string; icon: keyof typeof Ionicons.glyphMap }[] = [
  { key: "crepi", label: "Crépi", icon: "color-fill-outline" },
  { key: "brique_parement", label: "Brique parement", icon: "grid-outline" },
  { key: "pierre_parement", label: "Pierre", icon: "diamond-outline" },
  { key: "bardage", label: "Bardage", icon: "leaf-outline" },
];

const SHAPES: {
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
  { key: "triangle", letter: "E", label: "TRIANGLE", icon: "trail-sign-outline", desc: "Base + hauteur" },
  { key: "oeil_de_boeuf", letter: "H", label: "ŒIL-DE-BŒUF", icon: "ellipse-outline", desc: "Ouverture circulaire (diamètre)" },
  { key: "coulissant_levant", letter: "K", label: "COULISSANT LEVANT", icon: "swap-horizontal-outline", desc: "Levant-coulissant avec réserve sol" },
  // 🆕 V2 — Formes complexes
  { key: "plein_cintre", letter: "L", label: "PLEIN CINTRE", icon: "radio-button-on-outline", desc: "Arc parfait en demi-cercle au sommet" },
  { key: "arc_surbaisse", letter: "M", label: "ARC SURBAISSÉ", icon: "remove-outline", desc: "Arc applati (flèche < demi-largeur)" },
  { key: "angle_90", letter: "N", label: "ANGLE 90°", icon: "git-branch-outline", desc: "Deux baies à angle droit (coin de mur)" },
  { key: "bow_window", letter: "O", label: "BOW-WINDOW", icon: "infinite-outline", desc: "Baie courbe — plusieurs panneaux" },
  { key: "pentagone", letter: "P", label: "PENTAGONE", icon: "home-outline", desc: "Toit pointu (rectangle + triangle)" },
  { key: "hexagone", letter: "Q", label: "HEXAGONE", icon: "shapes-outline", desc: "6 côtés (rare, abri / véranda)" },
  { key: "ovale", letter: "R", label: "OVALE", icon: "ellipse-outline", desc: "Ellipse (axe horizontal + vertical)" },
];

// ════════════════════════════════════════════════════════════════════════
// State shapes
// ════════════════════════════════════════════════════════════════════════
type Step1Data = {
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

const initStep1 = (): Step1Data => ({
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

type Step3Data = {
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

const initStep3 = (): Step3Data => ({
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
  perimeter_measured: "",
  bow_panel_count: "",
  bow_depth_projection: "",
  pent_side_height: "",
  pent_top_height: "",
  hex_top_width: "",
  hex_side_height: "",
});

const parseNum = (s: string) => {
  const n = parseFloat(s.replace(",", "."));
  return Number.isFinite(n) ? n : null;
};

const shapeToBlockType = (s: Shape): "standard" | "coulissant" | "porte" | "trapeze" => {
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

const inferShape = (m: any): Shape => {
  const fromOpts = (m?.options?.shape as Shape) || null;
  if (fromOpts) return fromOpts;
  const bt = m?.block_type;
  if (bt === "trapeze") return "trapeze";
  if (bt === "porte") return "porte_entree";
  if (bt === "coulissant") return "rect";
  return "rect";
};

// Feuillures requises pour ces maçonneries
const masonryHasFeuillures = (m: MasonryType | null): boolean =>
  m === "brique" || m === "pierre" || m === "bloc_beton";

// ════════════════════════════════════════════════════════════════════════
// Composant principal
// ════════════════════════════════════════════════════════════════════════

export default function NewMesureWizard() {
  const { id, mesure_id, edit_wall_config } = useLocalSearchParams<{ id: string; mesure_id?: string; edit_wall_config?: string }>();
  const editingId = (mesure_id as string) || null;
  const wallEditOnly = edit_wall_config === "1";
  const router = useRouter();
  const { isTablet } = useResponsive();

  const [step, setStep] = useState<Step>(0);
  const [shape, setShape] = useState<Shape | null>(null);
  const [label, setLabel] = useState("");
  const [labelError, setLabelError] = useState(false);
  const [photo, setPhoto] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  // Loading initial : édition OU chargement de la wall_config du chantier
  const [loadingInit, setLoadingInit] = useState(true);
  // 🏗️ Si le chantier a déjà une wall_config → on saute l'étape 1
  //    (configuration mur déjà faite une fois pour tout le chantier).
  const [wallConfigLocked, setWallConfigLocked] = useState(false);

  const [s1, setS1] = useState<Step1Data>(initStep1());
  const [s1Err, setS1Err] = useState<Record<string, boolean>>({});

  const [s3, setS3] = useState<Step3Data>(initStep3());
  const [s3Err, setS3Err] = useState<Record<string, boolean>>({});

  const [reportOpen, setReportOpen] = useState(false);
  const [reportText, setReportText] = useState("");
  const [reportSending, setReportSending] = useState(false);

  // refs pour scrollTo automatique sur erreur libellé
  const scrollRef = useRef<ScrollView>(null);
  const labelRef = useRef<View>(null);

  const setS1Field = <K extends keyof Step1Data>(k: K, v: Step1Data[K]) =>
    setS1((p) => ({ ...p, [k]: v }));
  const setS3Field = <K extends keyof Step3Data>(k: K, v: Step3Data[K]) =>
    setS3((p) => ({ ...p, [k]: v }));

  /** Hydrate `s1` depuis une `wall_config` chargée depuis le chantier. */
  const hydrateS1FromWallConfig = (opts: any) => {
    if (!opts || typeof opts !== "object") return;
    const toStr = (v: any) => (v == null || v === "" ? "" : String(v));
    setS1({
      project_type: opts.project_type || "renovation",
      masonry_type: opts.masonry_type || null,
      gros_oeuvre_mm: toStr(opts.gros_oeuvre_mm),
      insulation_mode: opts.insulation_mode || null,
      iti_thickness_mm: toStr(opts.iti_thickness_mm),
      ite_insul_thickness_mm: toStr(opts.ite_insul_thickness_mm),
      parement_type: opts.parement_type || null,
      crepi_thickness_mm: toStr(opts.crepi_thickness_mm),
      coulisse_thickness_mm: toStr(opts.coulisse_thickness_mm),
      brique_pierre_thickness_mm: toStr(opts.brique_pierre_thickness_mm),
      structure_lame_air_mm: toStr(opts.structure_lame_air_mm),
      sill_already_installed:
        opts.sill_already_installed == null ? null : !!opts.sill_already_installed,
      sill_thickness_mm: toStr(opts.sill_thickness_mm),
      has_breastwork: !!opts.has_breastwork,
      has_horizontal_cut: !!opts.has_horizontal_cut,
    });
  };

  // ────── Init loader : charge wall_config du chantier + edit éventuel ──
  useEffect(() => {
    (async () => {
      try {
        // 1) Charge le chantier pour récupérer wall_config (si présent)
        let chantierWallConfig: any = null;
        try {
          const cr = await api.get(`/chantiers/${id}`);
          const raw = (cr.data as any)?.wall_config;
          // 🔒 On considère le wall_config "significatif" SEULEMENT s'il a
          // au moins masonry_type ET insulation_mode renseignés. Un objet
          // vide {} (truthy en JS) ne doit PAS déclencher le skip.
          if (
            raw &&
            typeof raw === "object" &&
            !!raw.masonry_type &&
            !!raw.insulation_mode
          ) {
            chantierWallConfig = raw;
          }
        } catch {
          /* noop — chantier introuvable, on continue avec une config vide */
        }
        if (chantierWallConfig) {
          hydrateS1FromWallConfig(chantierWallConfig);
          setWallConfigLocked(true);
        }
        // 🎯 Mode "Modifier la structure du mur" : on FORCE l'Étape 1 même
        // si wall_config existe (l'utilisateur veut justement la corriger).
        if (wallEditOnly) {
          setWallConfigLocked(false);
          setStep(0);
          setLoading(false);
          return;
        }

        // 2) Si on est en edit mode : charge la mesure existante
        if (editingId) {
          try {
            const r = await api.get(`/mesures/${editingId}`);
            const m = r.data as any;
            const inferred = inferShape(m);
            setShape(inferred);
            setLabel(m.label || "");
            setPhoto(m.photo_url || null);
            const opts = m.options || {};
            const toStr = (v: any) => (v == null || v === "" ? "" : String(v));
            // S'il n'y a pas de wall_config sur le chantier mais que la mesure
            // possède une copie des champs maçonnerie, on hydrate quand même.
            if (!chantierWallConfig) hydrateS1FromWallConfig(opts);
            const isTrap = inferred === "trapeze";
            const isReno = !!m.renovation_mode;
            setS3((prev) => ({
              ...prev,
              bay_width: toStr(m.bay_width),
              bay_height: isReno || isTrap ? "" : toStr(m.bay_height),
              diag_1: toStr(m.bay_diagonal_1),
              diag_1_state: m.bay_diagonal_1 ? "validated" : "manual",
              diag_2: toStr(m.bay_diagonal_2),
              diag_2_state: m.bay_diagonal_2 ? "validated" : "manual",
              renovation_mode: isReno,
              width_top: toStr(m.width_top),
              width_bottom: toStr(m.width_bottom),
              height_left: isReno ? toStr(m.height_left) : "",
              height_right: isReno ? toStr(m.height_right) : "",
              trap_height_left: isTrap ? toStr(m.height_left) : "",
              trap_height_right: isTrap ? toStr(m.height_right) : "",
              triangle_base: toStr(opts.triangle_base_mm),
              triangle_height: toStr(opts.triangle_height_mm),
              oeil_diameter: toStr(opts.oeil_diameter_mm),
              garage_lintel: toStr(opts.garage_lintel_mm),
              garage_ecoincon_left: toStr(opts.garage_ecoincon_left_mm),
              garage_ecoincon_right: toStr(opts.garage_ecoincon_right_mm),
              // 🆕 V2 — Rechargement des 7 nouvelles formes
              arch_h1_appui: toStr(opts.arch_h1_appui_mm),
              arch_h2_total: toStr(opts.arch_h2_total_mm),
              angle90_cut_width: toStr(opts.angle90_cut_width_mm),
              angle90_cut_height: toStr(opts.angle90_cut_height_mm),
              angle90_side:
                opts.angle90_side === "left" || opts.angle90_side === "both"
                  ? opts.angle90_side
                  : "right",
              angle90_angle_deg: toStr(opts.angle90_angle_deg) || "135",
              angle90_h_left: toStr(opts.angle90_h_left_mm || m.height_left),
              angle90_h_right: toStr(
                opts.angle90_h_right_mm || m.height_right || m.bay_height,
              ),
              perimeter_measured: toStr(opts.perimeter_measured_mm),
              bow_panel_count: opts.bow_panel_count === 5 ? "5" : (opts.bow_panel_count === 3 ? "3" : ""),
              bow_depth_projection: toStr(opts.bow_depth_projection_mm),
              pent_side_height: toStr(opts.pent_side_height_mm),
              pent_top_height: toStr(opts.pent_top_height_mm),
              hex_top_width: toStr(opts.hex_top_width_mm),
              hex_side_height: toStr(opts.hex_side_height_mm),
              floor_reserve: toStr(m.floor_reserve),
              has_1m_level_mark: !!opts.has_1m_level_mark,
              trait_1m_brut_mm: toStr(opts.trait_1m_brut_mm),
              feuillure_left_mm: toStr(opts.feuillure_left_mm),
              feuillure_right_mm: toStr(opts.feuillure_right_mm),
              feuillure_top_mm: toStr(opts.feuillure_top_mm),
              has_breastwork: !!opts.has_breastwork,
              breastwork_height_mm: toStr(opts.breastwork_height_mm),
            }));
            // En édition : on saute directement à l'étape 3 (cotes) — la
            // forme est déjà connue et la wall_config est globale.
            setStep(2);
          } catch {
            Alert.alert("Erreur", "Mesure introuvable.");
            router.back();
            return;
          }
        } else if (chantierWallConfig) {
          // Création d'un NOUVEAU châssis sur un chantier déjà configuré
          // → on saute l'étape 1 et on commence directement par la
          // sélection de la forme.
          setStep(1);
        }
      } finally {
        setLoadingInit(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editingId, id]);

  // ────── Pythagore ──────────────────────────────────────────────────
  const usesDiagonals = (sh: Shape | null) =>
    sh === "rect" || sh === "porte_entree" || sh === "porte_garage" || sh === "coulissant_levant";

  const computeDiagonals = (force = false) => {
    if (!usesDiagonals(shape)) return;
    const w = parseNum(s3.bay_width);
    const h = parseNum(s3.bay_height);
    if (!w || !h || w <= 0 || h <= 0) return;
    const d = Math.round(Math.sqrt(w * w + h * h));
    setS3((prev) => {
      let next = prev;
      if (force || (prev.diag_1_state !== "validated" && prev.diag_1.trim().length === 0))
        next = { ...next, diag_1: String(d), diag_1_state: "auto" };
      if (force || (prev.diag_2_state !== "validated" && prev.diag_2.trim().length === 0))
        next = { ...next, diag_2: String(d), diag_2_state: "auto" };
      return next;
    });
  };

  const canComputeDiag = useMemo(
    () => usesDiagonals(shape) && !!parseNum(s3.bay_width) && !!parseNum(s3.bay_height),
    [shape, s3.bay_width, s3.bay_height]
  );

  // Calcul auto réserve sol si trait 1m activé
  const computedFloorReserve = useMemo(() => {
    if (!s3.has_1m_level_mark) return null;
    const brut = parseNum(s3.trait_1m_brut_mm);
    if (!brut) return null;
    return brut - 1000;
  }, [s3.has_1m_level_mark, s3.trait_1m_brut_mm]);

  // 🆕 V2 — Périmètre calculé pour les formes complexes. Réagit en
  //    temps réel aux changements de cotes, permet au mesureur de
  //    vérifier sa mesure ruban contre la valeur géométrique.
  const computedPerimeter = useMemo(() => {
    if (shape === "plein_cintre") {
      return perimeterPleinCintre(
        parseNum(s3.bay_width),
        parseNum(s3.arch_h1_appui),
      );
    }
    if (shape === "arc_surbaisse") {
      return perimeterArcSurbaisse(
        parseNum(s3.bay_width),
        parseNum(s3.arch_h1_appui),
        parseNum(s3.arch_h2_total),
      );
    }
    if (shape === "angle_90") {
      const Hleft = parseNum(s3.angle90_h_left) || parseNum(s3.bay_height);
      const Hright = parseNum(s3.angle90_h_right) || parseNum(s3.bay_height);
      return perimeterAngle90(
        parseNum(s3.bay_width),
        Hleft,
        Hright,
        parseNum(s3.angle90_cut_width),
        parseNum(s3.angle90_cut_height),
        s3.angle90_side,
      );
    }
    return null;
  }, [
    shape,
    s3.bay_width,
    s3.bay_height,
    s3.arch_h1_appui,
    s3.arch_h2_total,
    s3.angle90_cut_width,
    s3.angle90_cut_height,
    s3.angle90_h_left,
    s3.angle90_h_right,
    s3.angle90_side,
  ]);

  // ────── Validations ────────────────────────────────────────────────
  const validateStep1 = (): boolean => {
    const err: Record<string, boolean> = {};
    if (!s1.masonry_type) err.masonry_type = true;
    if (!parseNum(s1.gros_oeuvre_mm)) err.gros_oeuvre_mm = true;
    if (!s1.insulation_mode) err.insulation_mode = true;
    if (s1.insulation_mode === "iti" && !parseNum(s1.iti_thickness_mm)) err.iti_thickness_mm = true;
    if (s1.insulation_mode === "ite") {
      if (!s1.parement_type) err.parement_type = true;
      if (!parseNum(s1.ite_insul_thickness_mm)) err.ite_insul_thickness_mm = true;
      if (s1.parement_type === "crepi" && !parseNum(s1.crepi_thickness_mm))
        err.crepi_thickness_mm = true;
      if (
        (s1.parement_type === "brique_parement" || s1.parement_type === "pierre_parement") &&
        (!parseNum(s1.coulisse_thickness_mm) || !parseNum(s1.brique_pierre_thickness_mm))
      ) {
        if (!parseNum(s1.coulisse_thickness_mm)) err.coulisse_thickness_mm = true;
        if (!parseNum(s1.brique_pierre_thickness_mm)) err.brique_pierre_thickness_mm = true;
      }
      if (s1.parement_type === "bardage" && !parseNum(s1.structure_lame_air_mm))
        err.structure_lame_air_mm = true;
    }
    if (s1.sill_already_installed == null) err.sill_already_installed = true;
    // C6 FIX : si seuil "non posé", on accepte une valeur vide (= pas de seuil,
    // épaisseur = 0). Cela débloque les châssis sans seuil (porte de garage,
    // certains coulissants, etc.) ou les rénovations où le menuisier ne pose
    // pas de seuil.
    setS1Err(err);
    return Object.keys(err).length === 0;
  };

  const focusLabel = () => {
    setLabelError(true);
    try {
      labelRef.current?.measureInWindow?.((_x, y) => {
        scrollRef.current?.scrollTo({ y: Math.max(0, y - 120), animated: true });
      });
    } catch {
      /* noop */
    }
  };

  const validateStep3 = (): boolean => {
    if (!shape) return false;
    const err: Record<string, boolean> = {};
    let ok = true;
    // 🔴 Libellé obligatoire — focus + rouge vif si oublié
    if (!label.trim()) {
      focusLabel();
      Alert.alert(
        "Libellé manquant",
        "Indiquez le libellé / référence du châssis (ex. Salon, Chambre 1, Porte d'entrée…)."
      );
      ok = false;
    } else {
      setLabelError(false);
    }

    if (shape === "trapeze") {
      if (!parseNum(s3.bay_width)) err.bay_width = true;
      if (!parseNum(s3.trap_height_left)) err.trap_height_left = true;
      if (!parseNum(s3.trap_height_right)) err.trap_height_right = true;
    } else if (shape === "triangle") {
      if (!parseNum(s3.triangle_base)) err.triangle_base = true;
      if (!parseNum(s3.triangle_height)) err.triangle_height = true;
    } else if (shape === "oeil_de_boeuf") {
      if (!parseNum(s3.oeil_diameter)) err.oeil_diameter = true;
    } else if (shape === "porte_garage") {
      if (!parseNum(s3.bay_width)) err.bay_width = true;
      if (!parseNum(s3.bay_height)) err.bay_height = true;
      if (!parseNum(s3.garage_lintel)) err.garage_lintel = true;
      if (!parseNum(s3.garage_ecoincon_left)) err.garage_ecoincon_left = true;
      if (!parseNum(s3.garage_ecoincon_right)) err.garage_ecoincon_right = true;
    } else if (shape === "plein_cintre") {
      // 🆕 V2 — Plein cintre : L, H1 (appui), H2 (sommet). R = L/2, H2 ≥ H1 + R
      const L = parseNum(s3.bay_width);
      const H1 = parseNum(s3.arch_h1_appui);
      const H2 = parseNum(s3.arch_h2_total);
      if (!L) err.bay_width = true;
      if (!H1) err.arch_h1_appui = true;
      if (!H2) err.arch_h2_total = true;
      // Validation métier : H2 ≥ H1 + R où R = L/2
      if (L && H1 && H2) {
        const R = L / 2;
        if (H2 < H1 + R) {
          err.arch_h2_total = true;
          Alert.alert(
            "Cotes incohérentes — Plein cintre",
            `La hauteur totale (H2 = ${H2}mm) doit être ≥ Hauteur d'appui (H1 = ${H1}mm) + Rayon (L/2 = ${R}mm).\n\nMinimum attendu : H2 ≥ ${H1 + R}mm`
          );
        }
      }
    } else if (shape === "arc_surbaisse") {
      // 🆕 V2 — Arc surbaissé : L, H1, H2. Flèche f = H2 - H1, f < L/2
      const L = parseNum(s3.bay_width);
      const H1 = parseNum(s3.arch_h1_appui);
      const H2 = parseNum(s3.arch_h2_total);
      if (!L) err.bay_width = true;
      if (!H1) err.arch_h1_appui = true;
      if (!H2) err.arch_h2_total = true;
      // Validation métier : flèche f < L/2 (sinon c'est un plein cintre ou plus haut)
      if (L && H1 && H2) {
        const fleche = H2 - H1;
        const demiL = L / 2;
        if (fleche <= 0) {
          err.arch_h2_total = true;
          Alert.alert(
            "Cotes incohérentes — Arc surbaissé",
            `La hauteur totale (H2 = ${H2}mm) doit être > Hauteur d'appui (H1 = ${H1}mm).`
          );
        } else if (fleche >= demiL) {
          err.arch_h2_total = true;
          Alert.alert(
            "Cotes incohérentes — Arc surbaissé",
            `La flèche (f = H2 - H1 = ${fleche}mm) doit être strictement inférieure à L/2 (= ${demiL}mm).\n\nSi la flèche est ≥ L/2, utilisez plutôt la forme « Plein cintre ».`
          );
        }
      }
    } else if (shape === "angle_90") {
      // 🆕 V2 — Angle 90° : Largeur, Hauteurs gauche/droite (asymétriques), Pan coupé, Côté, Angle
      const W = parseNum(s3.bay_width);
      const Hleft = parseNum(s3.angle90_h_left);
      const Hright = parseNum(s3.angle90_h_right);
      const cutW = parseNum(s3.angle90_cut_width);
      const cutH = parseNum(s3.angle90_cut_height);
      if (!W) err.bay_width = true;
      if (!Hleft) err.angle90_h_left = true;
      if (!Hright) err.angle90_h_right = true;
      if (!cutW) err.angle90_cut_width = true;
      if (!cutH) err.angle90_cut_height = true;
      // Validation métier : le pan coupé ne peut pas dépasser le cadre
      if (W && cutW && cutW >= W) {
        err.angle90_cut_width = true;
        Alert.alert(
          "Cotes incohérentes — Pan coupé",
          `La largeur du pan coupé (${cutW}mm) doit être strictement inférieure à la largeur totale (${W}mm).`
        );
      }
      const minH = Math.min(Hleft || 0, Hright || 0);
      if (minH && cutH && cutH >= minH) {
        err.angle90_cut_height = true;
        Alert.alert(
          "Cotes incohérentes — Pan coupé",
          `La hauteur du pan coupé (${cutH}mm) doit être strictement inférieure à la plus petite hauteur (${minH}mm).`
        );
      }
    } else if (shape === "bow_window") {
      // 🆕 V2 — Bow-Window : Largeur totale, Profondeur, Nb pans (3 ou 5)
      const W = parseNum(s3.bay_width);
      const H = parseNum(s3.bay_height);
      const P = parseNum(s3.bow_depth_projection);
      if (!W) err.bay_width = true;
      if (!H) err.bay_height = true;
      if (!P) err.bow_depth_projection = true;
      if (!s3.bow_panel_count) {
        err.bow_panel_count = true;
        Alert.alert(
          "Choix requis — Bow-Window",
          "Sélectionnez le nombre de pans (3 ou 5)."
        );
      }
      // Validation métier : profondeur doit être cohérente (P < W/2 généralement)
      if (W && P && P >= W / 2) {
        err.bow_depth_projection = true;
        Alert.alert(
          "Cotes incohérentes — Bow-Window",
          `La profondeur de projection (${P}mm) doit être inférieure à la moitié de la largeur (${W / 2}mm) pour un Bow-Window réaliste.`
        );
      }
    } else if (shape === "pentagone") {
      // 🆕 V2 — Pentagone : Largeur base, H côtés (H1), H totale au sommet (H2). H2 > H1
      const L = parseNum(s3.bay_width);
      const H1 = parseNum(s3.pent_side_height);
      const H2 = parseNum(s3.pent_top_height);
      if (!L) err.bay_width = true;
      if (!H1) err.pent_side_height = true;
      if (!H2) err.pent_top_height = true;
      if (H1 && H2 && H2 <= H1) {
        err.pent_top_height = true;
        Alert.alert(
          "Cotes incohérentes — Pentagone",
          `La hauteur totale au sommet (H2 = ${H2}mm) doit être strictement supérieure à la hauteur des côtés (H1 = ${H1}mm).`
        );
      }
    } else if (shape === "hexagone") {
      // 🆕 V2 — Hexagone : Largeur base, Largeur sommet, Hauteur totale, H verticales
      const Wbase = parseNum(s3.bay_width);
      const Wtop = parseNum(s3.hex_top_width);
      const H = parseNum(s3.bay_height);
      const Hside = parseNum(s3.hex_side_height);
      if (!Wbase) err.bay_width = true;
      if (!Wtop) err.hex_top_width = true;
      if (!H) err.bay_height = true;
      if (!Hside) err.hex_side_height = true;
      // Validation métier : la hauteur des côtés verticaux ne peut pas dépasser
      // la hauteur totale, et la largeur sommet doit être < largeur base
      if (Hside && H && Hside >= H) {
        err.hex_side_height = true;
        Alert.alert(
          "Cotes incohérentes — Hexagone",
          `La hauteur des parties verticales (${Hside}mm) doit être strictement inférieure à la hauteur totale (${H}mm).`
        );
      }
      if (Wbase && Wtop && Wtop >= Wbase) {
        err.hex_top_width = true;
        Alert.alert(
          "Cotes incohérentes — Hexagone",
          `La largeur du sommet (${Wtop}mm) doit être strictement inférieure à la largeur de la base (${Wbase}mm).`
        );
      }
    } else if (shape === "ovale") {
      // 🆕 V2 — Ovale : Largeur totale (L) et Hauteur totale (H). Pas d'autre contrainte.
      if (!parseNum(s3.bay_width)) err.bay_width = true;
      if (!parseNum(s3.bay_height)) err.bay_height = true;
    } else {
      if (s3.renovation_mode && shape === "rect") {
        if (!parseNum(s3.width_top)) err.width_top = true;
        if (!parseNum(s3.width_bottom)) err.width_bottom = true;
        if (!parseNum(s3.height_left)) err.height_left = true;
        if (!parseNum(s3.height_right)) err.height_right = true;
      } else {
        if (!parseNum(s3.bay_width)) err.bay_width = true;
        if (!parseNum(s3.bay_height)) err.bay_height = true;
        if (!parseNum(s3.diag_1)) err.diag_1 = true;
        if (!parseNum(s3.diag_2)) err.diag_2 = true;
        if (s3.diag_1_state === "auto") err.diag_1 = true;
        if (s3.diag_2_state === "auto") err.diag_2 = true;
      }
      // Portes & coulissant levant : réserve sol obligatoire (sauf si trait 1m calcule).
      // ⚠️ On utilise `parseNum(...) === null` au lieu de `!parseNum(...)`
      // car `!0` vaut `true` et empêchait la valeur ZÉRO (= rénovation où
      // le sol fini est confondu avec la baie). Désormais 0 est accepté.
      if (
        (shape === "porte_entree" || shape === "coulissant_levant") &&
        !s3.has_1m_level_mark &&
        parseNum(s3.floor_reserve) === null
      ) {
        err.floor_reserve = true;
      }
      // Si trait 1m activé : la mesure brute est obligatoire
      if (
        (shape === "porte_entree" || shape === "coulissant_levant") &&
        s3.has_1m_level_mark &&
        parseNum(s3.trait_1m_brut_mm) === null
      ) {
        err.trait_1m_brut_mm = true;
      }
    }
    // Porte garage : réserve sol obligatoire (mais 0 reste valide).
    if (shape === "porte_garage" && parseNum(s3.floor_reserve) === null) {
      err.floor_reserve = true;
    }
    // Allège : si cochée, la hauteur est obligatoire (uniquement pour
    // les formes qui peuvent en avoir).
    if (
      s3.has_breastwork &&
      (shape === "rect" ||
        shape === "trapeze" ||
        shape === "triangle" ||
        shape === "oeil_de_boeuf") &&
      !parseNum(s3.breastwork_height_mm)
    ) {
      err.breastwork_height_mm = true;
    }
    setS3Err(err);
    return ok && Object.keys(err).length === 0;
  };

  // ────── Photo helpers ──────────────────────────────────────────────
  const pickPhoto = async (source: "camera" | "library") => {
    const fn =
      source === "camera"
        ? ImagePicker.requestCameraPermissionsAsync
        : ImagePicker.requestMediaLibraryPermissionsAsync;
    const perm = await fn();
    if (!perm.granted) {
      Alert.alert("Permission refusée", "Activez l'accès dans les réglages.");
      return;
    }
    const launcher =
      source === "camera" ? ImagePicker.launchCameraAsync : ImagePicker.launchImageLibraryAsync;
    const res = await launcher({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 0.5,
      base64: true,
    });
    if (!res.canceled && res.assets[0]) {
      const a = res.assets[0];
      setPhoto(a.base64 ? `data:image/jpeg;base64,${a.base64}` : a.uri);
    }
  };

  // ────── Submit ────────────────────────────────────────────────────
  const submit = async () => {
    if (!shape || !validateStep3()) return;
    setSaving(true);
    const opts: Record<string, unknown> = {
      // Étape 1
      project_type: s1.project_type,
      masonry_type: s1.masonry_type,
      gros_oeuvre_mm: parseNum(s1.gros_oeuvre_mm),
      insulation_mode: s1.insulation_mode,
      iti_thickness_mm: s1.insulation_mode === "iti" ? parseNum(s1.iti_thickness_mm) : null,
      ite_insul_thickness_mm:
        s1.insulation_mode === "ite" ? parseNum(s1.ite_insul_thickness_mm) : null,
      parement_type: s1.insulation_mode === "ite" ? s1.parement_type : null,
      crepi_thickness_mm:
        s1.insulation_mode === "ite" && s1.parement_type === "crepi"
          ? parseNum(s1.crepi_thickness_mm)
          : null,
      coulisse_thickness_mm:
        s1.insulation_mode === "ite" &&
        (s1.parement_type === "brique_parement" || s1.parement_type === "pierre_parement")
          ? parseNum(s1.coulisse_thickness_mm)
          : null,
      brique_pierre_thickness_mm:
        s1.insulation_mode === "ite" &&
        (s1.parement_type === "brique_parement" || s1.parement_type === "pierre_parement")
          ? parseNum(s1.brique_pierre_thickness_mm)
          : null,
      structure_lame_air_mm:
        s1.insulation_mode === "ite" && s1.parement_type === "bardage"
          ? parseNum(s1.structure_lame_air_mm)
          : null,
      sill_already_installed: s1.sill_already_installed,
      sill_thickness_mm:
        s1.sill_already_installed === false ? parseNum(s1.sill_thickness_mm) : null,
      // Allège — désormais par-mesure (Étape 3). Uniquement pour
      // Rectangle / Trapèze / Triangle / Œil-de-bœuf. Forcée à false
      // pour les portes et coulissants (jamais d'allège).
      has_breastwork: (
        shape === "porte_entree" ||
        shape === "porte_garage" ||
        shape === "coulissant_levant"
      ) ? false : s3.has_breastwork,
      breastwork_height_mm:
        s3.has_breastwork &&
        (shape === "rect" ||
          shape === "trapeze" ||
          shape === "triangle" ||
          shape === "oeil_de_boeuf")
          ? parseNum(s3.breastwork_height_mm)
          : null,
      has_horizontal_cut: s1.has_horizontal_cut,
      // Étape 2
      shape,
      // Étape 3 — Feuillures (si maçonnerie requiert)
      feuillure_left_mm: masonryHasFeuillures(s1.masonry_type)
        ? parseNum(s3.feuillure_left_mm)
        : null,
      feuillure_right_mm: masonryHasFeuillures(s1.masonry_type)
        ? parseNum(s3.feuillure_right_mm)
        : null,
      feuillure_top_mm: masonryHasFeuillures(s1.masonry_type)
        ? parseNum(s3.feuillure_top_mm)
        : null,
      // Trait 1m
      has_1m_level_mark: s3.has_1m_level_mark,
      trait_1m_brut_mm: s3.has_1m_level_mark ? parseNum(s3.trait_1m_brut_mm) : null,
    };
    if (shape === "triangle") {
      opts.triangle_base_mm = parseNum(s3.triangle_base);
      opts.triangle_height_mm = parseNum(s3.triangle_height);
    }
    if (shape === "oeil_de_boeuf") opts.oeil_diameter_mm = parseNum(s3.oeil_diameter);
    if (shape === "porte_garage") {
      opts.garage_lintel_mm = parseNum(s3.garage_lintel);
      opts.garage_ecoincon_left_mm = parseNum(s3.garage_ecoincon_left);
      opts.garage_ecoincon_right_mm = parseNum(s3.garage_ecoincon_right);
    }
    // 🆕 V2 — Sauvegarde des cotes spécifiques aux 7 nouvelles formes
    if (shape === "plein_cintre" || shape === "arc_surbaisse") {
      opts.arch_h1_appui_mm = parseNum(s3.arch_h1_appui);
      opts.arch_h2_total_mm = parseNum(s3.arch_h2_total);
      if (shape === "plein_cintre") {
        opts.arch_radius_mm = (parseNum(s3.bay_width) ?? 0) / 2;
      } else if (shape === "arc_surbaisse") {
        const H1 = parseNum(s3.arch_h1_appui) ?? 0;
        const H2 = parseNum(s3.arch_h2_total) ?? 0;
        opts.arch_fleche_mm = H2 - H1;
      }
    }
    if (shape === "angle_90") {
      opts.angle90_cut_width_mm = parseNum(s3.angle90_cut_width);
      opts.angle90_cut_height_mm = parseNum(s3.angle90_cut_height);
      opts.angle90_side = s3.angle90_side;
      opts.angle90_angle_deg = parseNum(s3.angle90_angle_deg) || 135;
      opts.angle90_h_left_mm = parseNum(s3.angle90_h_left);
      opts.angle90_h_right_mm = parseNum(s3.angle90_h_right);
    }
    // 🆕 V2 — Périmètre (calculé + mesuré au ruban) pour vérification technique.
    //    Le `computedPerimeter` est issu du même useMemo qui alimente le
    //    composant <PerimeterVerification> ; on persiste les deux valeurs
    //    pour l'audit côté exports / vérification technicien.
    if (
      shape === "plein_cintre" ||
      shape === "arc_surbaisse" ||
      shape === "angle_90"
    ) {
      const measured = parseNum(s3.perimeter_measured);
      if (measured !== null) opts.perimeter_measured_mm = measured;
      if (computedPerimeter !== null) {
        opts.perimeter_computed_mm = computedPerimeter;
      }
    }
    if (shape === "bow_window") {
      opts.bow_panel_count = parseInt(s3.bow_panel_count || "3", 10);
      opts.bow_depth_projection_mm = parseNum(s3.bow_depth_projection);
    }
    if (shape === "pentagone") {
      opts.pent_side_height_mm = parseNum(s3.pent_side_height);
      opts.pent_top_height_mm = parseNum(s3.pent_top_height);
    }
    if (shape === "hexagone") {
      opts.hex_top_width_mm = parseNum(s3.hex_top_width);
      opts.hex_side_height_mm = parseNum(s3.hex_side_height);
    }
    if (shape === "ovale") {
      const L = parseNum(s3.bay_width) ?? 0;
      const H = parseNum(s3.bay_height) ?? 0;
      opts.ovale_radius_x_mm = L / 2;
      opts.ovale_radius_y_mm = H / 2;
    }

    const payload: Record<string, unknown> = {
      chantier_id: id,
      block_type: shapeToBlockType(shape),
      label: label.trim(),
      photo_url: photo,
      bay_width: parseNum(s3.bay_width),
      // Mappage backend des champs maçonnerie (pour les exports historiques)
      bloc_thickness: parseNum(s1.gros_oeuvre_mm),
      wall_type:
        s1.insulation_mode === "ite"
          ? s1.parement_type === "crepi"
            ? "crepi_simple"
            : s1.parement_type === "brique_parement" || s1.parement_type === "pierre_parement"
              ? "brique_parement"
              : "ite"
          : s1.insulation_mode === "iti"
            ? "iti"
            : "crepi_simple",
      insulation_thickness:
        s1.insulation_mode === "iti"
          ? parseNum(s1.iti_thickness_mm)
          : s1.insulation_mode === "ite"
            ? parseNum(s1.ite_insul_thickness_mm)
            : null,
      finish_outer:
        s1.parement_type === "crepi"
          ? parseNum(s1.crepi_thickness_mm)
          : s1.parement_type === "brique_parement" || s1.parement_type === "pierre_parement"
            ? parseNum(s1.brique_pierre_thickness_mm)
            : null,
      options: opts,
    };

    if (shape === "trapeze") {
      payload.height_left = parseNum(s3.trap_height_left);
      payload.height_right = parseNum(s3.trap_height_right);
    } else if (shape === "triangle") {
      payload.bay_width = parseNum(s3.triangle_base);
      payload.height_left = parseNum(s3.triangle_height);
      payload.height_right = parseNum(s3.triangle_height);
    } else if (shape === "oeil_de_boeuf") {
      payload.bay_width = parseNum(s3.oeil_diameter);
      payload.bay_height = parseNum(s3.oeil_diameter);
    } else if (shape === "rect" && s3.renovation_mode) {
      payload.renovation_mode = true;
      payload.width_top = parseNum(s3.width_top);
      payload.width_bottom = parseNum(s3.width_bottom);
      payload.height_left = parseNum(s3.height_left);
      payload.height_right = parseNum(s3.height_right);
      const wt = parseNum(s3.width_top) || 0;
      const wb = parseNum(s3.width_bottom) || 0;
      const hl = parseNum(s3.height_left) || 0;
      const hr = parseNum(s3.height_right) || 0;
      payload.bay_width = Math.round((wt + wb) / 2) || null;
      payload.bay_height = Math.round((hl + hr) / 2) || null;
    } else if (shape === "angle_90") {
      // Pour la rétro-compatibilité avec l'API et les exports historiques,
      // on calcule bay_height comme le max des deux hauteurs (cadre englobant).
      const Hleft = parseNum(s3.angle90_h_left) || 0;
      const Hright = parseNum(s3.angle90_h_right) || 0;
      payload.bay_height = Math.max(Hleft, Hright) || null;
      payload.height_left = Hleft || null;
      payload.height_right = Hright || null;
    } else {
      payload.bay_height = parseNum(s3.bay_height);
      payload.bay_diagonal_1 = parseNum(s3.diag_1);
      payload.bay_diagonal_2 = parseNum(s3.diag_2);
      payload.diag_1_verified = s3.diag_1_state !== "auto";
      payload.diag_2_verified = s3.diag_2_state !== "auto";
    }

    // Réserve sol — trait 1m calc auto OU saisie manuelle
    if (
      shape === "porte_entree" ||
      shape === "porte_garage" ||
      shape === "coulissant_levant"
    ) {
      const reserve = s3.has_1m_level_mark
        ? computedFloorReserve
        : parseNum(s3.floor_reserve);
      payload.floor_reserve = reserve;
    }

    try {
      const online = await isOnline();
      if (!online && !editingId) {
        await enqueueMesure(payload);
        Alert.alert("Hors ligne", "Mesure ajoutée à la file de synchro.", [
          { text: "OK", onPress: () => router.back() },
        ]);
        return;
      }
      // 🔒 SAFETY NET — on retente la sauvegarde du wall_config juste avant
      // d'enregistrer la mesure. Si le PATCH initial à l'étape 1→2 a échoué
      // (réseau transitoire, etc.) ou si on est en mode édition d'une mesure
      // antérieure à la fonctionnalité, on assure ici la persistance.
      if (!editingId) {
        await persistWallConfig();
      }
      if (editingId) await api.patch(`/mesures/${editingId}`, payload);
      else await api.post("/mesures", payload);
      router.back();
    } catch (err: any) {
      if (editingId) {
        Alert.alert("Erreur", "Mise à jour impossible.");
      } else {
        await enqueueMesure(payload);
        // Log discret pour faciliter le debug en prod (pas d'alerte tech au user)
        const status = err?.response?.status;
        const reason =
          status === undefined
            ? "réseau / timeout"
            : `HTTP ${status}`;
        // eslint-disable-next-line no-console
        console.warn(
          "[new-mesure] Save failed →",
          reason,
          err?.response?.data || err?.message,
        );
        Alert.alert(
          "Sauvegarde différée",
          "Votre mesure a été enregistrée localement et sera envoyée automatiquement dès que la connexion sera stable. Aucune perte de données.",
          [{ text: "OK", onPress: () => router.back() }],
        );
      }
    } finally {
      setSaving(false);
    }
  };

  // ────── Report ─────────────────────────────────────────────────────
  const sendReport = async () => {
    if (!reportText.trim()) return;
    setReportSending(true);
    try {
      await api.post("/feedbacks", {
        page_context: `wizard:step${step + 1}:${shape ?? "none"}`,
        user_comment: reportText.trim(),
        encoded_data_snapshot: { chantier_id: id, shape, label, s1, s3 },
      });
      setReportOpen(false);
      setReportText("");
      Alert.alert("Merci !", "Votre signalement a été envoyé.");
    } catch {
      Alert.alert("Erreur", "Envoi impossible.");
    } finally {
      setReportSending(false);
    }
  };

  // ────── Navigation ─────────────────────────────────────────────────
  /** Construit le payload wall_config depuis l'état s1 courant. */
  const buildWallConfigPayload = () => ({
    project_type: s1.project_type,
    masonry_type: s1.masonry_type,
    gros_oeuvre_mm: parseNum(s1.gros_oeuvre_mm),
    insulation_mode: s1.insulation_mode,
    iti_thickness_mm: parseNum(s1.iti_thickness_mm),
    ite_insul_thickness_mm: parseNum(s1.ite_insul_thickness_mm),
    parement_type: s1.parement_type,
    crepi_thickness_mm: parseNum(s1.crepi_thickness_mm),
    coulisse_thickness_mm: parseNum(s1.coulisse_thickness_mm),
    brique_pierre_thickness_mm: parseNum(s1.brique_pierre_thickness_mm),
    structure_lame_air_mm: parseNum(s1.structure_lame_air_mm),
    sill_already_installed: s1.sill_already_installed,
    sill_thickness_mm: parseNum(s1.sill_thickness_mm),
    has_breastwork: s1.has_breastwork,
    has_horizontal_cut: s1.has_horizontal_cut,
  });

  /** Sauvegarde silencieuse du wall_config (idempotent). Renvoie true si OK. */
  const persistWallConfig = async (): Promise<boolean> => {
    try {
      await api.patch(
        `/chantiers/${id}/wall-config`,
        buildWallConfigPayload()
      );
      setWallConfigLocked(true);
      return true;
    } catch (e) {
      return false;
    }
  };

  const goNextFromStep1 = async () => {
    if (!validateStep1()) return;
    // 🏗️ Sauvegarde la wall_config sur le chantier (1 seule fois pour
    // tout le chantier). Si la sauvegarde échoue, on AVERTIT l'utilisateur
    // (mais on continue pour ne pas bloquer le métreur). Le submit final
    // retentera également la sauvegarde (idempotent).
    const ok = await persistWallConfig();
    if (!ok) {
      Alert.alert(
        "Configuration non sauvegardée",
        "La configuration du mur n'a pas pu être enregistrée sur le serveur. " +
          "Vous pouvez continuer, elle sera re-tentée au moment d'enregistrer le châssis.",
      );
    }
    // 🎯 Mode "Modifier la structure du mur" : on a fait notre job, retour
    // direct à la fiche chantier (pas de navigation vers l'étape 2).
    if (wallEditOnly) {
      Alert.alert(
        "Configuration enregistrée",
        "La structure du mur a été mise à jour pour ce chantier.",
        [{ text: "OK", onPress: () => router.back() }],
      );
      return;
    }
    setStep(1);
  };
  const onPickShape = (sh: Shape) => {
    setShape(sh);
    setStep(2);
  };
  const goBack = () => {
    // 🏗️ Si la config mur est verrouillée (déjà sauvée pour le chantier),
    //    on saute l'étape 1 lors du retour aussi : étape 2 → quitte.
    if (step === 2) {
      setStep(1);
    } else if (step === 1) {
      if (wallConfigLocked) {
        router.back();
      } else {
        setStep(0);
      }
    } else {
      router.back();
    }
  };

  if (loadingInit) {
    return (
      <SafeAreaView style={[styles.flex, { justifyContent: "center", alignItems: "center" }]}>
        <ActivityIndicator color={colors.primary} />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.flex} edges={["bottom"]}>
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        style={styles.flex}
      >
        <View style={styles.topBar}>
          <View style={styles.stepRow}>
            {[0, 1, 2].map((i) => (
              <View
                key={i}
                testID={`step-pill-${i + 1}`}
                style={[styles.stepPill, i <= step && styles.stepPillActive]}
              >
                <Text style={[styles.stepPillText, i <= step && { color: "#000" }]}>{i + 1}</Text>
              </View>
            ))}
          </View>
          <TouchableOpacity
            testID="open-report-modal"
            onPress={() => setReportOpen(true)}
            style={styles.reportBtn}
            activeOpacity={0.7}
          >
            <Ionicons name="alert-circle-outline" size={14} color={colors.anomaly} />
            <Text style={styles.reportBtnText}>Signaler un problème</Text>
          </TouchableOpacity>
        </View>

        <ScrollView
          ref={scrollRef}
          contentContainerStyle={{
            padding: 16,
            paddingBottom: 200,
            maxWidth: isTablet ? 900 : "100%",
            width: "100%",
            alignSelf: "center",
          }}
          keyboardShouldPersistTaps="handled"
        >
          {step === 0 && <Step1Config s1={s1} setField={setS1Field} err={s1Err} />}
          {step === 1 && <Step2Shape onPick={onPickShape} current={shape} />}
          {step === 2 && shape && (
            <Step3Cotes
              shape={shape}
              label={label}
              setLabel={(v) => {
                setLabel(v);
                if (labelError && v.trim()) setLabelError(false);
              }}
              labelError={labelError}
              labelRef={labelRef}
              s1MasonryType={s1.masonry_type}
              s1HasHorizontalCut={s1.has_horizontal_cut}
              s3={s3}
              setField={setS3Field}
              err={s3Err}
              photo={photo}
              setPhoto={setPhoto}
              pickPhoto={pickPhoto}
              onBlurDimension={() => computeDiagonals(false)}
              onComputeDiagonals={() => computeDiagonals(true)}
              canComputeDiag={canComputeDiag}
              computedFloorReserve={computedFloorReserve}
              computedPerimeter={computedPerimeter}
            />
          )}
        </ScrollView>

        <View style={styles.footer}>
          <TouchableOpacity
            testID="wizard-back"
            onPress={goBack}
            style={[styles.btn, styles.btnSecondary]}
            activeOpacity={0.7}
          >
            <Ionicons name="arrow-back" size={20} color={colors.textPrimary} />
            <Text style={styles.btnSecondaryText}>RETOUR</Text>
          </TouchableOpacity>
          {step === 0 && (
            <TouchableOpacity
              testID="wizard-next-to-step2"
              onPress={goNextFromStep1}
              style={[styles.btn, styles.btnPrimary]}
              activeOpacity={0.85}
            >
              <Text style={styles.btnPrimaryText}>SUIVANT</Text>
              <Ionicons name="arrow-forward" size={20} color="#000" />
            </TouchableOpacity>
          )}
          {step === 2 && (
            <TouchableOpacity
              testID="wizard-submit"
              onPress={submit}
              disabled={saving}
              style={[styles.btn, styles.btnPrimary]}
              activeOpacity={0.85}
            >
              {saving ? (
                <ActivityIndicator color="#000" />
              ) : (
                <>
                  <Ionicons name="checkmark-circle" size={22} color="#000" />
                  <Text style={styles.btnPrimaryText}>ENREGISTRER</Text>
                </>
              )}
            </TouchableOpacity>
          )}
        </View>
      </KeyboardAvoidingView>

      <Modal visible={reportOpen} transparent animationType="fade" onRequestClose={() => setReportOpen(false)}>
        <KeyboardAvoidingView
          behavior={Platform.OS === "ios" ? "padding" : "height"}
          style={styles.modalOverlay}
        >
          <View style={styles.modalCard}>
            <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
              <Ionicons name="alert-circle" size={20} color={colors.anomaly} />
              <Text style={styles.modalTitle}>Signaler un problème</Text>
            </View>
            <Text style={styles.modalSub}>
              Décrivez ce qui ne va pas — envoyé à l'admin avec le contexte.
            </Text>
            <TextInput
              testID="report-text-input"
              value={reportText}
              onChangeText={setReportText}
              multiline
              numberOfLines={4}
              placeholder="Ex: la diagonale auto-calculée est fausse..."
              placeholderTextColor={colors.placeholder}
              style={styles.reportInput}
            />
            <View style={{ flexDirection: "row", gap: 8, marginTop: 12 }}>
              <TouchableOpacity
                onPress={() => setReportOpen(false)}
                style={[styles.btn, styles.btnSecondary, { flex: 1, minHeight: 48 }]}
                activeOpacity={0.7}
              >
                <Text style={styles.btnSecondaryText}>ANNULER</Text>
              </TouchableOpacity>
              <TouchableOpacity
                testID="report-submit"
                onPress={sendReport}
                disabled={reportSending}
                style={[styles.btn, styles.btnPrimary, { flex: 1, minHeight: 48 }]}
                activeOpacity={0.85}
              >
                {reportSending ? (
                  <ActivityIndicator color="#000" />
                ) : (
                  <Text style={styles.btnPrimaryText}>ENVOYER</Text>
                )}
              </TouchableOpacity>
            </View>
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </SafeAreaView>
  );
}

// ════════════════════════════════════════════════════════════════════════
// Étape 1 — Configurateur de Mur Dynamique
// ════════════════════════════════════════════════════════════════════════
function Step1Config({
  s1,
  setField,
  err,
}: {
  s1: Step1Data;
  setField: <K extends keyof Step1Data>(k: K, v: Step1Data[K]) => void;
  err: Record<string, boolean>;
}) {
  return (
    <View>
      <Text style={styles.h1}>CONFIGURATION DU MUR</Text>
      <Text style={styles.h2}>Étape 1/3 · Structure de la maison (fait 1 seule fois)</Text>

      {/* Type de projet */}
      <Text style={[styles.sectionLabel, { marginTop: 22 }]}>TYPE DE PROJET *</Text>
      <View style={styles.row2}>
        <SegBtn
          testID="project-construction"
          icon="home-outline"
          label="Nouvelle Construction"
          active={s1.project_type === "construction"}
          onPress={() => setField("project_type", "construction")}
        />
        <SegBtn
          testID="project-renovation"
          icon="construct-outline"
          label="Rénovation"
          active={s1.project_type === "renovation"}
          onPress={() => setField("project_type", "renovation")}
        />
      </View>

      {/* Maçonnerie */}
      <Text style={[styles.sectionLabel, { marginTop: 22 }]}>
        TYPE DE MAÇONNERIE * {err.masonry_type && <Text style={styles.errInline}> ⚠</Text>}
      </Text>
      <View style={styles.facadeGrid}>
        {MASONRIES.map((m) => {
          const active = s1.masonry_type === m.key;
          return (
            <TouchableOpacity
              key={m.key}
              testID={`masonry-${m.key}`}
              onPress={() => setField("masonry_type", m.key)}
              activeOpacity={0.85}
              style={[
                styles.facadeCard,
                active && styles.facadeCardActive,
                err.masonry_type && !active && { borderColor: colors.anomaly },
              ]}
            >
              <Ionicons name={m.icon} size={22} color={active ? colors.primary : colors.textSecondary} />
              <Text style={[styles.facadeLabel, active && { color: colors.primary }]}>
                {m.label}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>

      {/* Épaisseur Gros Œuvre */}
      {s1.masonry_type && (
        <CotField
          testID="input-gros-oeuvre"
          label="ÉPAISSEUR DU GROS ŒUVRE (mm) *"
          value={s1.gros_oeuvre_mm}
          onChange={(v) => setField("gros_oeuvre_mm", v.replace(",", "."))}
          error={!!err.gros_oeuvre_mm}
        />
      )}

      {/* Isolation & Finition */}
      <Text style={[styles.sectionLabel, { marginTop: 22 }]}>
        ISOLATION & FINITION * {err.insulation_mode && <Text style={styles.errInline}> ⚠</Text>}
      </Text>
      <View style={{ gap: 8 }}>
        <InsulationOption
          testID="insul-none"
          active={s1.insulation_mode === "none"}
          icon="reader-outline"
          label="Mur plein sans isolation"
          onPress={() => setField("insulation_mode", "none")}
        />
        <InsulationOption
          testID="insul-iti"
          active={s1.insulation_mode === "iti"}
          icon="layers-outline"
          label="Isolation Intérieure (ITI)"
          onPress={() => setField("insulation_mode", "iti")}
        />
        {s1.insulation_mode === "iti" && (
          <CotField
            testID="input-iti-thickness"
            label="ÉPAISSEUR ISOLANT INT. (mm) *"
            value={s1.iti_thickness_mm}
            onChange={(v) => setField("iti_thickness_mm", v.replace(",", "."))}
            error={!!err.iti_thickness_mm}
          />
        )}
        <InsulationOption
          testID="insul-ite"
          active={s1.insulation_mode === "ite"}
          icon="albums-outline"
          label="Isolation Extérieure (ITE)"
          onPress={() => setField("insulation_mode", "ite")}
        />
        {s1.insulation_mode === "ite" && (
          <>
            <Text style={[styles.sectionLabel, { marginTop: 10 }]}>
              TYPE DE PAREMENT * {err.parement_type && <Text style={styles.errInline}> ⚠</Text>}
            </Text>
            <View style={styles.facadeGrid}>
              {PAREMENTS.map((p) => {
                const active = s1.parement_type === p.key;
                return (
                  <TouchableOpacity
                    key={p.key}
                    testID={`parement-${p.key}`}
                    onPress={() => setField("parement_type", p.key)}
                    activeOpacity={0.85}
                    style={[
                      styles.facadeCard,
                      active && styles.facadeCardActive,
                      err.parement_type && !active && { borderColor: colors.anomaly },
                    ]}
                  >
                    <Ionicons name={p.icon} size={22} color={active ? colors.primary : colors.textSecondary} />
                    <Text style={[styles.facadeLabel, active && { color: colors.primary }]}>
                      {p.label}
                    </Text>
                  </TouchableOpacity>
                );
              })}
            </View>
            <CotField
              testID="input-ite-insul-thickness"
              label="ÉPAISSEUR ISOLANT (mm) *"
              value={s1.ite_insul_thickness_mm}
              onChange={(v) => setField("ite_insul_thickness_mm", v.replace(",", "."))}
              error={!!err.ite_insul_thickness_mm}
            />
            {s1.parement_type === "crepi" && (
              <CotField
                testID="input-crepi-thickness"
                label="ÉPAISSEUR CRÉPI (mm) *"
                value={s1.crepi_thickness_mm}
                onChange={(v) => setField("crepi_thickness_mm", v.replace(",", "."))}
                error={!!err.crepi_thickness_mm}
              />
            )}
            {(s1.parement_type === "brique_parement" || s1.parement_type === "pierre_parement") && (
              <>
                <CotField
                  testID="input-coulisse-thickness"
                  label="ÉPAISSEUR COULISSE / VIDE (mm) *"
                  value={s1.coulisse_thickness_mm}
                  onChange={(v) => setField("coulisse_thickness_mm", v.replace(",", "."))}
                  error={!!err.coulisse_thickness_mm}
                />
                <CotField
                  testID="input-brique-pierre-thickness"
                  label={`ÉPAISSEUR ${s1.parement_type === "brique_parement" ? "BRIQUE" : "PIERRE"} (mm) *`}
                  value={s1.brique_pierre_thickness_mm}
                  onChange={(v) => setField("brique_pierre_thickness_mm", v.replace(",", "."))}
                  error={!!err.brique_pierre_thickness_mm}
                />
              </>
            )}
            {s1.parement_type === "bardage" && (
              <CotField
                testID="input-structure-lame-air"
                label="ÉPAISSEUR STRUCTURE / LAME D'AIR (mm) *"
                value={s1.structure_lame_air_mm}
                onChange={(v) => setField("structure_lame_air_mm", v.replace(",", "."))}
                error={!!err.structure_lame_air_mm}
              />
            )}
          </>
        )}
      </View>

      {/* Statut Seuils */}
      <Text style={[styles.sectionLabel, { marginTop: 22 }]}>
        STATUT DES SEUILS *
        {err.sill_already_installed && <Text style={styles.errInline}> ⚠</Text>}
      </Text>
      <View style={styles.row2}>
        <SegBtn
          testID="sill-yes"
          icon="checkmark-circle-outline"
          label="Oui, déjà posés"
          active={s1.sill_already_installed === true}
          onPress={() => setField("sill_already_installed", true)}
        />
        <SegBtn
          testID="sill-no"
          icon="close-circle-outline"
          label="Non, à venir"
          active={s1.sill_already_installed === false}
          onPress={() => setField("sill_already_installed", false)}
        />
      </View>
      {s1.sill_already_installed === false && (
        <CotField
          testID="input-sill-thickness"
          label="ÉPAISSEUR FUTURE DU SEUIL (mm)"
          value={s1.sill_thickness_mm}
          onChange={(v) => setField("sill_thickness_mm", v.replace(",", "."))}
          error={!!err.sill_thickness_mm}
        />
      )}
      {s1.sill_already_installed === false && (
        <Text style={styles.helpHint}>
          💡 Laissez vide ou indiquez 0 si aucun seuil ne sera posé
          (porte de garage, certains coulissants, rénovation sans seuil).
        </Text>
      )}

      <Text style={[styles.sectionLabel, { marginTop: 22 }]}>OPTIONS GLOBALES</Text>
      <CheckboxRow
        testID="opt-horizontal-cut"
        label="Coupe horizontale (Retour de butée)"
        sub="Présence d'un retour de butée horizontal"
        value={s1.has_horizontal_cut}
        onChange={(v) => setField("has_horizontal_cut", v)}
      />
      <Text style={styles.helpHint}>
        💡 L'option « Allège » est désormais saisie par ouverture
        (étape « Cotes »), car elle peut varier d'une baie à l'autre.
      </Text>
    </View>
  );
}

function InsulationOption({
  testID,
  icon,
  label,
  active,
  onPress,
}: {
  testID: string;
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  active: boolean;
  onPress: () => void;
}) {
  return (
    <TouchableOpacity
      testID={testID}
      onPress={onPress}
      activeOpacity={0.85}
      style={[styles.insulOption, active && styles.insulOptionActive]}
    >
      <Ionicons name={icon} size={20} color={active ? colors.primary : colors.textSecondary} />
      <Text style={[styles.insulOptionLabel, active && { color: colors.primary }]}>{label}</Text>
      <View style={{ flex: 1 }} />
      <Ionicons
        name={active ? "checkmark-circle" : "ellipse-outline"}
        size={20}
        color={active ? colors.primary : colors.borderStrong}
      />
    </TouchableOpacity>
  );
}

// ════════════════════════════════════════════════════════════════════════
// Étape 2 — Sélection de la forme (épurée)
// ════════════════════════════════════════════════════════════════════════
function Step2Shape({
  onPick,
  current,
}: {
  onPick: (s: Shape) => void;
  current: Shape | null;
}) {
  return (
    <View>
      <Text style={styles.h1}>SÉLECTION DE LA MENUISERIE</Text>
      <Text style={styles.h2}>Étape 2/3 · Choisissez la forme exacte du châssis</Text>
      <Text style={styles.helperText}>
        Le type d'ouvrant (Fixe, Ouvrant, Oscillo-battant, Coulissant) sera défini en atelier via
        le libellé / référence saisi à l'étape suivante.
      </Text>
      <View style={{ gap: 10, marginTop: 16 }}>
        {SHAPES.map((s) => {
          const active = current === s.key;
          return (
            <TouchableOpacity
              key={s.key}
              testID={`shape-${s.key}`}
              onPress={() => onPick(s.key)}
              activeOpacity={0.85}
              style={[styles.shapeCard, active && styles.shapeCardActive]}
            >
              <View style={styles.shapeLetterBadge}>
                <Text style={styles.shapeLetter}>{s.letter}</Text>
              </View>
              <View style={styles.shapeIconBox}>
                <ShapeIcon
                  shape={s.key}
                  size={48}
                  color={active ? colors.primary : colors.textPrimary}
                  strokeWidth={1.8}
                />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={[styles.shapeTitle, active && { color: colors.primary }]}>{s.label}</Text>
                <Text style={styles.shapeDesc}>{s.desc}</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color={active ? colors.primary : colors.borderStrong} />
            </TouchableOpacity>
          );
        })}
      </View>
      <View style={[styles.inlineHintBox, { marginTop: 18 }]}>
        <Ionicons name="information-circle" size={14} color={colors.textSecondary} />
        <Text style={styles.inlineHintText}>
          Les formes complexes (Plein cintre, Arc surbaissé, Angle 90°, Bow-Window) seront
          disponibles en V2.
        </Text>
      </View>
    </View>
  );
}

// ════════════════════════════════════════════════════════════════════════
// Étape 3 — Cotes adaptatives & intelligentes
// ════════════════════════════════════════════════════════════════════════
function Step3Cotes({
  shape,
  label,
  setLabel,
  labelError,
  labelRef,
  s1MasonryType,
  s1HasHorizontalCut,
  s3,
  setField,
  err,
  photo,
  setPhoto,
  pickPhoto,
  onBlurDimension,
  onComputeDiagonals,
  canComputeDiag,
  computedFloorReserve,
  computedPerimeter,
}: {
  shape: Shape;
  label: string;
  setLabel: (v: string) => void;
  labelError: boolean;
  labelRef: React.RefObject<View>;
  s1MasonryType: MasonryType | null;
  s1HasHorizontalCut: boolean;
  s3: Step3Data;
  setField: <K extends keyof Step3Data>(k: K, v: Step3Data[K]) => void;
  err: Record<string, boolean>;
  photo: string | null;
  setPhoto: (v: string | null) => void;
  pickPhoto: (s: "camera" | "library") => void;
  onBlurDimension: () => void;
  onComputeDiagonals: () => void;
  canComputeDiag: boolean;
  computedFloorReserve: number | null;
  computedPerimeter: number | null;
}) {
  const isRectFamily =
    shape === "rect" ||
    shape === "porte_entree" ||
    shape === "porte_garage" ||
    shape === "coulissant_levant";
  const show1mLevel = shape === "porte_entree" || shape === "coulissant_levant";
  const showFloorReserve =
    shape === "porte_entree" || shape === "porte_garage" || shape === "coulissant_levant";
  // M3 FIX — Feuillures : masquage si "coupe horizontale" est OFF dans Step 1
  // (en plus de la maçonnerie qui doit avoir des feuillures).
  // 🚪 Sur une porte de garage / coulissant levant, les feuillures n'ont
  // PAS de sens (pose en applique ou sous linteau, pas en feuillure), donc
  // on masque la section même si la maçonnerie en a habituellement.
  const showFeuillures =
    masonryHasFeuillures(s1MasonryType) &&
    !!s1HasHorizontalCut &&
    shape !== "porte_garage" &&
    shape !== "coulissant_levant";
  const Sketch = shape === "trapeze" || shape === "triangle" ? RawBaySchemaTrapeze : RawBaySchemaRect;

  const validateDiag = (which: 1 | 2) =>
    setField(which === 1 ? "diag_1_state" : "diag_2_state", "validated");
  const modifyDiag = (which: 1 | 2) => {
    setField(which === 1 ? "diag_1" : "diag_2", "");
    setField(which === 1 ? "diag_1_state" : "diag_2_state", "manual");
  };

  return (
    <View>
      <Text style={styles.h1}>PRISE DE COTES</Text>
      <Text style={styles.h2}>
        Étape 3/3 · {SHAPES.find((s) => s.key === shape)?.label}
      </Text>

      {/* 📐 Guide visuel — montre où prendre les cotes */}
      <MeasureGuide shape={shape} />
      <Text style={styles.guideHint}>
        ↑ Repérez les cotes à mesurer sur le schéma, puis renseignez-les ci-dessous.
      </Text>

      <View ref={labelRef} style={{ marginTop: 14 }}>
        <Text style={[styles.label, labelError && { color: colors.anomaly }]}>
          LIBELLÉ / RÉFÉRENCE DU CHÂSSIS * {labelError && <Text style={styles.errInline}> ⚠ OBLIGATOIRE</Text>}
        </Text>
        <TextInput
          testID="mesure-label-input"
          value={label}
          onChangeText={setLabel}
          placeholder="ex. Salon, Chambre 1, Porte d'entrée, Réf. F-001..."
          placeholderTextColor={colors.placeholder}
          style={[
            styles.input,
            labelError && {
              borderColor: colors.anomaly,
              borderWidth: 2,
              backgroundColor: "#1a0808",
            },
          ]}
        />
        {labelError && (
          <Text style={styles.errorMsg}>
            ⚠ Indiquez un libellé / référence pour identifier ce châssis.
          </Text>
        )}
      </View>

      {/* Toggle Rénovation pour Rectangle uniquement */}
      {shape === "rect" && (
        <View style={styles.modeToggle}>
          <TouchableOpacity
            testID="mode-standard-tab"
            onPress={() => setField("renovation_mode", false)}
            activeOpacity={0.8}
            style={[styles.modeTab, !s3.renovation_mode && styles.modeTabActive]}
          >
            <Ionicons name="resize-outline" size={14} color={!s3.renovation_mode ? "#000" : colors.textSecondary} />
            <Text style={[styles.modeTabText, !s3.renovation_mode && styles.modeTabTextActive]}>
              MODE STANDARD
            </Text>
          </TouchableOpacity>
          <TouchableOpacity
            testID="mode-renovation-tab"
            onPress={() => setField("renovation_mode", true)}
            activeOpacity={0.8}
            style={[styles.modeTab, s3.renovation_mode && styles.modeTabActive]}
          >
            <Ionicons name="construct-outline" size={14} color={s3.renovation_mode ? "#000" : colors.textSecondary} />
            <Text style={[styles.modeTabText, s3.renovation_mode && styles.modeTabTextActive]}>
              VÉRIF. RÉNOVATION
            </Text>
          </TouchableOpacity>
        </View>
      )}

      {/* Cotes — Trapèze */}
      {shape === "trapeze" && (
        <>
          <CotField testID="input-bay-width" label="LARGEUR (mm) *" value={s3.bay_width}
            onChange={(v) => setField("bay_width", v.replace(",", "."))} error={!!err.bay_width} />
          <CotField testID="input-trap-height-left" label="HAUTEUR GAUCHE (mm) *" value={s3.trap_height_left}
            onChange={(v) => setField("trap_height_left", v.replace(",", "."))} error={!!err.trap_height_left} />
          <CotField testID="input-trap-height-right" label="HAUTEUR DROITE (mm) *" value={s3.trap_height_right}
            onChange={(v) => setField("trap_height_right", v.replace(",", "."))} error={!!err.trap_height_right} />
        </>
      )}

      {/* Triangle */}
      {shape === "triangle" && (
        <>
          <CotField testID="input-triangle-base" label="BASE (mm) *" value={s3.triangle_base}
            onChange={(v) => setField("triangle_base", v.replace(",", "."))} error={!!err.triangle_base} />
          <CotField testID="input-triangle-height" label="HAUTEUR (mm) *" value={s3.triangle_height}
            onChange={(v) => setField("triangle_height", v.replace(",", "."))} error={!!err.triangle_height} />
        </>
      )}

      {/* Œil-de-bœuf */}
      {shape === "oeil_de_boeuf" && (
        <CotField testID="input-oeil-diameter" label="DIAMÈTRE (mm) *" value={s3.oeil_diameter}
          onChange={(v) => setField("oeil_diameter", v.replace(",", "."))} error={!!err.oeil_diameter} />
      )}

      {/* 🆕 V2 — Plein cintre */}
      {shape === "plein_cintre" && (
        <>
          <ShapeSchemaV2
            shape="plein_cintre"
            values={{
              L: parseNum(s3.bay_width) || undefined,
              H1: parseNum(s3.arch_h1_appui) || undefined,
              H2: parseNum(s3.arch_h2_total) || undefined,
            }}
          />
          <Text style={styles.helperText}>
            ⭕ Plein cintre — Arc en demi-cercle au sommet.
            La hauteur de gauche est identique à la hauteur de droite.
          </Text>
          <CotField testID="input-bay-width" label="LARGEUR L (mm) *" value={s3.bay_width}
            onChange={(v) => setField("bay_width", v.replace(",", "."))} error={!!err.bay_width} />
          <CotField testID="input-arch-h1" label="HAUTEUR D'APPUI H1 (mm) *" value={s3.arch_h1_appui}
            onChange={(v) => setField("arch_h1_appui", v.replace(",", "."))} error={!!err.arch_h1_appui} />
          <CotField testID="input-arch-h2" label="HAUTEUR TOTALE H2 (mm) *" value={s3.arch_h2_total}
            onChange={(v) => setField("arch_h2_total", v.replace(",", "."))} error={!!err.arch_h2_total} />
          <Text style={styles.helperText}>
            ✓ Règle : H2 = H1 + L/2 (le sommet du demi-cercle dépasse l&apos;appui de L/2).
          </Text>
          <PerimeterVerification
            testID="input-perimeter-plein-cintre"
            computed={computedPerimeter}
            measuredValue={s3.perimeter_measured}
            onChangeMeasured={(v) => setField("perimeter_measured", v.replace(",", "."))}
          />
        </>
      )}

      {/* 🆕 V2 — Arc surbaissé */}
      {shape === "arc_surbaisse" && (
        <>
          <ShapeSchemaV2
            shape="arc_surbaisse"
            values={{
              L: parseNum(s3.bay_width) || undefined,
              H1: parseNum(s3.arch_h1_appui) || undefined,
              H2: parseNum(s3.arch_h2_total) || undefined,
            }}
          />
          <Text style={styles.helperText}>
            🌗 Arc surbaissé — Arc applati (moins haut qu&apos;un demi-cercle).
            La hauteur de gauche est identique à la hauteur de droite.
          </Text>
          <CotField testID="input-bay-width" label="LARGEUR L (mm) *" value={s3.bay_width}
            onChange={(v) => setField("bay_width", v.replace(",", "."))} error={!!err.bay_width} />
          <CotField testID="input-arch-h1" label="HAUTEUR D'APPUI H1 (mm) *" value={s3.arch_h1_appui}
            onChange={(v) => setField("arch_h1_appui", v.replace(",", "."))} error={!!err.arch_h1_appui} />
          <CotField testID="input-arch-h2" label="HAUTEUR TOTALE H2 (mm) *" value={s3.arch_h2_total}
            onChange={(v) => setField("arch_h2_total", v.replace(",", "."))} error={!!err.arch_h2_total} />
          <Text style={styles.helperText}>
            ✓ Règle : H2 doit être {">"} H1 et la montée (H2 − H1) doit être {"<"} L/2.
          </Text>
          <PerimeterVerification
            testID="input-perimeter-arc-surbaisse"
            computed={computedPerimeter}
            measuredValue={s3.perimeter_measured}
            onChangeMeasured={(v) => setField("perimeter_measured", v.replace(",", "."))}
          />
        </>
      )}

      {/* 🆕 V2 — Angle 90° (pan coupé gauche / droite / les deux) */}
      {shape === "angle_90" && (
        <>
          <ShapeSchemaV2
            shape="angle_90"
            values={{
              L: parseNum(s3.bay_width) || undefined,
              Hleft: parseNum(s3.angle90_h_left) || undefined,
              Hright: parseNum(s3.angle90_h_right) || undefined,
              cutW: parseNum(s3.angle90_cut_width) || undefined,
              cutH: parseNum(s3.angle90_cut_height) || undefined,
              cutSide: s3.angle90_side,
              cutAngleDeg: parseNum(s3.angle90_angle_deg) || 135,
            }}
          />
          <Text style={styles.helperText}>
            ◣ Pan coupé — Châssis avec un (ou deux) coin(s) coupé(s) en oblique.
            La zone hachurée orange sur le schéma indique le pan coupé.
          </Text>

          {/* Sélecteur du côté coupé */}
          <Text style={[styles.sectionLabel, { marginTop: 12 }]}>CÔTÉ(S) COUPÉ(S) *</Text>
          <View style={[styles.row2, { marginBottom: 10 }]}>
            {(["left", "right", "both"] as const).map((sd) => {
              const active = s3.angle90_side === sd;
              const label =
                sd === "left" ? "GAUCHE" : sd === "right" ? "DROITE" : "LES DEUX";
              return (
                <TouchableOpacity
                  key={sd}
                  testID={`angle90-side-${sd}`}
                  onPress={() => setField("angle90_side", sd)}
                  activeOpacity={0.85}
                  style={[
                    styles.modeTab,
                    { flex: 1 },
                    active && styles.modeTabActive,
                  ]}
                >
                  <Text style={[styles.modeTabText, active && styles.modeTabTextActive]}>
                    {label}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </View>

          <CotField testID="input-bay-width" label="LARGEUR TOTALE L (mm) *" value={s3.bay_width}
            onChange={(v) => setField("bay_width", v.replace(",", "."))} error={!!err.bay_width} />

          <View style={styles.row2}>
            <View style={{ flex: 1 }}>
              <CotField testID="input-angle90-h-left" label="HAUTEUR GAUCHE Hg (mm) *" value={s3.angle90_h_left}
                onChange={(v) => setField("angle90_h_left", v.replace(",", "."))} error={!!err.angle90_h_left} />
            </View>
            <View style={{ flex: 1 }}>
              <CotField testID="input-angle90-h-right" label="HAUTEUR DROITE Hd (mm) *" value={s3.angle90_h_right}
                onChange={(v) => setField("angle90_h_right", v.replace(",", "."))} error={!!err.angle90_h_right} />
            </View>
          </View>

          <Text style={[styles.sectionLabel, { marginTop: 12 }]}>PAN COUPÉ</Text>
          <View style={styles.row2}>
            <View style={{ flex: 1 }}>
              <CotField testID="input-angle90-cut-w" label="LARGEUR DU PAN (mm) *" value={s3.angle90_cut_width}
                onChange={(v) => setField("angle90_cut_width", v.replace(",", "."))} error={!!err.angle90_cut_width} />
            </View>
            <View style={{ flex: 1 }}>
              <CotField testID="input-angle90-cut-h" label="HAUTEUR DU PAN (mm) *" value={s3.angle90_cut_height}
                onChange={(v) => setField("angle90_cut_height", v.replace(",", "."))} error={!!err.angle90_cut_height} />
            </View>
          </View>
          <CotField testID="input-angle90-angle" label="ANGLE DU PAN (°) — 135° par défaut" value={s3.angle90_angle_deg}
            onChange={(v) => setField("angle90_angle_deg", v.replace(",", "."))} />
          <Text style={styles.helperText}>
            ✓ Règle : Le pan coupé doit être {"<"} dimensions du cadre.
            L&apos;angle est généralement de 135° (oblique à 45°), mais ajustable selon votre mesure.
          </Text>

          <PerimeterVerification
            testID="input-perimeter-angle-90"
            computed={computedPerimeter}
            measuredValue={s3.perimeter_measured}
            onChangeMeasured={(v) => setField("perimeter_measured", v.replace(",", "."))}
          />
        </>
      )}

      {/* 🆕 V2 — Bow-Window */}
      {shape === "bow_window" && (
        <>
          <Text style={styles.helperText}>
            🌐 Bow-Window — Baie courbe en saillie composée de plusieurs pans.
            Choisissez le nombre de pans (3 ou 5).
          </Text>
          <Text style={[styles.sectionLabel, { marginTop: 8 }]}>NOMBRE DE PANS *</Text>
          <View style={[styles.row2, { marginBottom: 12 }]}>
            <TouchableOpacity
              testID="bow-panel-3"
              onPress={() => setField("bow_panel_count", "3")}
              activeOpacity={0.8}
              style={[
                styles.modeTab,
                { flex: 1 },
                s3.bow_panel_count === "3" && styles.modeTabActive,
                !!err.bow_panel_count && { borderColor: "#ef4444", borderWidth: 2 },
              ]}
            >
              <Text style={[styles.modeTabText, s3.bow_panel_count === "3" && styles.modeTabTextActive]}>
                3 PANS
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              testID="bow-panel-5"
              onPress={() => setField("bow_panel_count", "5")}
              activeOpacity={0.8}
              style={[
                styles.modeTab,
                { flex: 1 },
                s3.bow_panel_count === "5" && styles.modeTabActive,
                !!err.bow_panel_count && { borderColor: "#ef4444", borderWidth: 2 },
              ]}
            >
              <Text style={[styles.modeTabText, s3.bow_panel_count === "5" && styles.modeTabTextActive]}>
                5 PANS
              </Text>
            </TouchableOpacity>
          </View>
          <CotField testID="input-bay-width" label="LARGEUR TOTALE (mm) *" value={s3.bay_width}
            onChange={(v) => setField("bay_width", v.replace(",", "."))} error={!!err.bay_width} />
          <CotField testID="input-bay-height" label="HAUTEUR TOTALE (mm) *" value={s3.bay_height}
            onChange={(v) => setField("bay_height", v.replace(",", "."))} error={!!err.bay_height} />
          <CotField testID="input-bow-depth" label="PROFONDEUR DE PROJECTION P (mm) *" value={s3.bow_depth_projection}
            onChange={(v) => setField("bow_depth_projection", v.replace(",", "."))} error={!!err.bow_depth_projection} />
          <Text style={styles.helperText}>
            ✓ Règle : Profondeur P {"<"} Largeur / 2 pour une saillie réaliste.
          </Text>
        </>
      )}

      {/* 🆕 V2 — Pentagone */}
      {shape === "pentagone" && (
        <>
          <Text style={styles.helperText}>
            ⬠ Pentagone — Forme à toit pointu (rectangle + triangle au sommet).
            H1 = hauteur des côtés verticaux ; H2 = hauteur totale au sommet.
          </Text>
          <CotField testID="input-bay-width" label="LARGEUR BASE (mm) *" value={s3.bay_width}
            onChange={(v) => setField("bay_width", v.replace(",", "."))} error={!!err.bay_width} />
          <CotField testID="input-pent-h1" label="HAUTEUR CÔTÉS H1 (mm) *" value={s3.pent_side_height}
            onChange={(v) => setField("pent_side_height", v.replace(",", "."))} error={!!err.pent_side_height} />
          <CotField testID="input-pent-h2" label="HAUTEUR SOMMET H2 (mm) *" value={s3.pent_top_height}
            onChange={(v) => setField("pent_top_height", v.replace(",", "."))} error={!!err.pent_top_height} />
          <Text style={styles.helperText}>
            ✓ Règle : H2 (sommet) doit être {">"} H1 (côtés).
          </Text>
        </>
      )}

      {/* 🆕 V2 — Hexagone */}
      {shape === "hexagone" && (
        <>
          <Text style={styles.helperText}>
            ⬡ Hexagone — Forme avec haut ET bas pan coupé (6 côtés).
          </Text>
          <CotField testID="input-bay-width" label="LARGEUR BASE (mm) *" value={s3.bay_width}
            onChange={(v) => setField("bay_width", v.replace(",", "."))} error={!!err.bay_width} />
          <CotField testID="input-hex-top-width" label="LARGEUR SOMMET (mm) *" value={s3.hex_top_width}
            onChange={(v) => setField("hex_top_width", v.replace(",", "."))} error={!!err.hex_top_width} />
          <CotField testID="input-bay-height" label="HAUTEUR TOTALE (mm) *" value={s3.bay_height}
            onChange={(v) => setField("bay_height", v.replace(",", "."))} error={!!err.bay_height} />
          <CotField testID="input-hex-side-h" label="HAUTEUR CÔTÉS VERTICAUX (mm) *" value={s3.hex_side_height}
            onChange={(v) => setField("hex_side_height", v.replace(",", "."))} error={!!err.hex_side_height} />
          <Text style={styles.helperText}>
            ✓ Règles : Largeur sommet {"<"} Largeur base ; Hauteur côtés {"<"} Hauteur totale.
          </Text>
        </>
      )}

      {/* 🆕 V2 — Ovale */}
      {shape === "ovale" && (
        <>
          <Text style={styles.helperText}>
            ⬭ Ovale — Forme ellipsoïdale.
            Rayon horizontal = L/2 ; Rayon vertical = H/2.
          </Text>
          <CotField testID="input-bay-width" label="LARGEUR L (mm) *" value={s3.bay_width}
            onChange={(v) => setField("bay_width", v.replace(",", "."))} error={!!err.bay_width} />
          <CotField testID="input-bay-height" label="HAUTEUR H (mm) *" value={s3.bay_height}
            onChange={(v) => setField("bay_height", v.replace(",", "."))} error={!!err.bay_height} />
        </>
      )}

      {/* Porte de garage */}
      {shape === "porte_garage" && (
        <>
          <CotField testID="input-bay-width" label="LARGEUR (mm) *" value={s3.bay_width}
            onChange={(v) => setField("bay_width", v.replace(",", "."))} onBlur={onBlurDimension} error={!!err.bay_width} />
          <CotField testID="input-bay-height" label="HAUTEUR (mm) *" value={s3.bay_height}
            onChange={(v) => setField("bay_height", v.replace(",", "."))} onBlur={onBlurDimension} error={!!err.bay_height} />
          <Text style={[styles.sectionLabel, { marginTop: 18 }]}>SPÉCIFIQUES PORTE DE GARAGE</Text>
          <Text style={styles.helperText}>
            📏 Mesures spécifiques à la pose d'une porte sectionnelle :
            le linteau est la hauteur sous-plafond disponible au-dessus de
            la baie ; les écoinçons sont la largeur de mur plein disponible
            de part et d'autre de la baie pour fixer les rails verticaux
            (minimum 100 mm recommandé).
          </Text>
          <CotField testID="input-garage-lintel" label="LINTEAU (mm) *" value={s3.garage_lintel}
            onChange={(v) => setField("garage_lintel", v.replace(",", "."))} error={!!err.garage_lintel} />
          <View style={styles.row2}>
            <View style={{ flex: 1 }}>
              <CotField testID="input-garage-ecoincon-left" label="ÉCOINÇON GAUCHE (mm) *" value={s3.garage_ecoincon_left}
                onChange={(v) => setField("garage_ecoincon_left", v.replace(",", "."))} error={!!err.garage_ecoincon_left} />
            </View>
            <View style={{ flex: 1 }}>
              <CotField testID="input-garage-ecoincon-right" label="ÉCOINÇON DROIT (mm) *" value={s3.garage_ecoincon_right}
                onChange={(v) => setField("garage_ecoincon_right", v.replace(",", "."))} error={!!err.garage_ecoincon_right} />
            </View>
          </View>
        </>
      )}

      {/* Rect family standard */}
      {isRectFamily && shape !== "porte_garage" && !s3.renovation_mode && (
        <>
          <CotField testID="input-bay-width" label="LARGEUR (mm) *" value={s3.bay_width}
            onChange={(v) => setField("bay_width", v.replace(",", "."))} onBlur={onBlurDimension} error={!!err.bay_width} />
          <CotField testID="input-bay-height" label="HAUTEUR (mm) *" value={s3.bay_height}
            onChange={(v) => setField("bay_height", v.replace(",", "."))} onBlur={onBlurDimension} error={!!err.bay_height} />
        </>
      )}

      {/* Rect Vérif Rénovation */}
      {shape === "rect" && s3.renovation_mode && (
        <>
          <View style={styles.row2}>
            <View style={{ flex: 1 }}>
              <CotField testID="input-width-top" label="LARGEUR HAUT (mm) *" value={s3.width_top}
                onChange={(v) => setField("width_top", v.replace(",", "."))} error={!!err.width_top} />
            </View>
            <View style={{ flex: 1 }}>
              <CotField testID="input-width-bottom" label="LARGEUR BAS (mm) *" value={s3.width_bottom}
                onChange={(v) => setField("width_bottom", v.replace(",", "."))} error={!!err.width_bottom} />
            </View>
          </View>
          <View style={styles.row2}>
            <View style={{ flex: 1 }}>
              <CotField testID="input-height-left" label="HAUTEUR GAUCHE (mm) *" value={s3.height_left}
                onChange={(v) => setField("height_left", v.replace(",", "."))} error={!!err.height_left} />
            </View>
            <View style={{ flex: 1 }}>
              <CotField testID="input-height-right" label="HAUTEUR DROITE (mm) *" value={s3.height_right}
                onChange={(v) => setField("height_right", v.replace(",", "."))} error={!!err.height_right} />
            </View>
          </View>
        </>
      )}

      {/* Diagonales */}
      {isRectFamily && !s3.renovation_mode && (
        <>
          <TouchableOpacity
            testID="compute-diagonal-button"
            onPress={onComputeDiagonals}
            disabled={!canComputeDiag}
            activeOpacity={0.8}
            style={[styles.computeBtn, !canComputeDiag && { opacity: 0.4 }]}
          >
            <Ionicons name="calculator-outline" size={18} color={colors.primary} />
            <Text style={styles.computeBtnText}>CALCULER LA DIAGONALE</Text>
          </TouchableOpacity>
          <DiagonalField testID="input-diag-1" label="DIAGONALE 1 (mm) *" value={s3.diag_1}
            state={s3.diag_1_state}
            onChange={(v) => {
              setField("diag_1", v.replace(",", "."));
              setField("diag_1_state", "manual");
            }}
            onValidate={() => validateDiag(1)} onModify={() => modifyDiag(1)} error={!!err.diag_1} />
          <DiagonalField testID="input-diag-2" label="DIAGONALE 2 (mm) *" value={s3.diag_2}
            state={s3.diag_2_state}
            onChange={(v) => {
              setField("diag_2", v.replace(",", "."));
              setField("diag_2_state", "manual");
            }}
            onValidate={() => validateDiag(2)} onModify={() => modifyDiag(2)} error={!!err.diag_2} />
        </>
      )}

      {/* 🆕 Feuillures conditionnelles (Brique/Pierre/Bloc béton) */}
      {showFeuillures && shape !== "oeil_de_boeuf" && (
        <>
          <Text style={[styles.sectionLabel, { marginTop: 22 }]}>FEUILLURES (optionnel)</Text>
          <Text style={styles.helperText}>
            Mesurez les feuillures de la baie selon la spécificité de votre maçonnerie.
          </Text>
          <CotField testID="input-feuillure-left" label="FEUILLURE GAUCHE (mm)" value={s3.feuillure_left_mm}
            onChange={(v) => setField("feuillure_left_mm", v.replace(",", "."))} />
          <CotField testID="input-feuillure-right" label="FEUILLURE DROITE (mm)" value={s3.feuillure_right_mm}
            onChange={(v) => setField("feuillure_right_mm", v.replace(",", "."))} />
          <CotField testID="input-feuillure-top" label="FEUILLURE HAUTE (mm)" value={s3.feuillure_top_mm}
            onChange={(v) => setField("feuillure_top_mm", v.replace(",", "."))} />
        </>
      )}

      {/* 🆕 Œil-de-bœuf : feuillure circulaire unique (identique tout autour) */}
      {showFeuillures && shape === "oeil_de_boeuf" && (
        <>
          <Text style={[styles.sectionLabel, { marginTop: 22 }]}>FEUILLURE (optionnel)</Text>
          <Text style={styles.helperText}>
            La feuillure d'un œil-de-bœuf est circulaire et identique sur
            toute la périphérie. Une seule mesure suffit.
          </Text>
          <CotField
            testID="input-feuillure-circular"
            label="FEUILLURE CIRCULAIRE (mm)"
            value={s3.feuillure_left_mm}
            onChange={(v) => {
              // On stocke la même valeur dans les 3 champs pour garder
              // une compatibilité totale avec les exports historiques
              // (PDF, XLSX, etc.) qui parcourent les 3 champs distincts.
              const clean = v.replace(",", ".");
              setField("feuillure_left_mm", clean);
              setField("feuillure_right_mm", clean);
              setField("feuillure_top_mm", clean);
            }}
          />
        </>
      )}

      {/* 🆕 Allège — par ouverture (rect / trapèze / triangle / œil-de-bœuf) */}
      {(shape === "rect" ||
        shape === "trapeze" ||
        shape === "triangle" ||
        shape === "oeil_de_boeuf") && (
        <>
          <Text style={[styles.sectionLabel, { marginTop: 22 }]}>ALLÈGE</Text>
          <CheckboxRow
            testID="opt-breastwork"
            label="Cette ouverture a une allège"
            sub="Maçonnerie sous la baie (varie selon les ouvertures)"
            value={s3.has_breastwork}
            onChange={(v) => setField("has_breastwork", v)}
          />
          {s3.has_breastwork && (
            <CotField
              testID="input-breastwork-height"
              label="HAUTEUR DE L'ALLÈGE (mm) *"
              value={s3.breastwork_height_mm}
              onChange={(v) =>
                setField("breastwork_height_mm", v.replace(",", "."))
              }
              error={!!err.breastwork_height_mm}
            />
          )}
        </>
      )}

      {/* 🆕 Trait de niveau 1m + calcul auto réserve sol */}
      {show1mLevel && (
        <>
          <Text style={[styles.sectionLabel, { marginTop: 22 }]}>RÉSERVE SOL FINI</Text>
          <CheckboxRow
            testID="opt-1m-level-mark"
            label="Trait de niveau 1m"
            sub="Active le calcul automatique via mesure brute"
            value={s3.has_1m_level_mark}
            onChange={(v) => setField("has_1m_level_mark", v)}
          />
          {s3.has_1m_level_mark ? (
            <>
              <CotField
                testID="input-trait-1m-brut"
                label="MESURE DU TRAIT AU SOL BRUT (mm) *"
                value={s3.trait_1m_brut_mm}
                onChange={(v) => setField("trait_1m_brut_mm", v.replace(",", "."))}
                error={!!err.trait_1m_brut_mm}
              />
              {computedFloorReserve != null && (
                <View testID="auto-floor-reserve-display" style={styles.computedBox}>
                  <Ionicons name="calculator" size={16} color={colors.success} />
                  <Text style={styles.computedLabel}>RÉSERVE SOL CALCULÉE :</Text>
                  <Text style={styles.computedValue}>
                    {computedFloorReserve} mm
                  </Text>
                  <Text style={styles.computedFormula}>(brut − 1000 mm)</Text>
                </View>
              )}
            </>
          ) : (
            <CotField
              testID="input-floor-reserve"
              label="RÉSERVE SOL FINI (mm) *"
              value={s3.floor_reserve}
              onChange={(v) => setField("floor_reserve", v.replace(",", "."))}
              error={!!err.floor_reserve}
            />
          )}
        </>
      )}

      {/* Porte garage : réserve sol manuelle */}
      {shape === "porte_garage" && (
        <CotField
          testID="input-floor-reserve"
          label="RÉSERVE SOL FINI (mm) *"
          value={s3.floor_reserve}
          onChange={(v) => setField("floor_reserve", v.replace(",", "."))}
          error={!!err.floor_reserve}
        />
      )}

      {/* Photo */}
      <Text style={[styles.label, { marginTop: 24 }]}>Photo (optionnel)</Text>
      {photo ? (
        <View>
          <Image source={{ uri: photo }} style={styles.photo} />
          <TouchableOpacity testID="remove-photo-button" onPress={() => setPhoto(null)} style={styles.removePhoto}>
            <Ionicons name="trash" size={16} color="#fff" />
          </TouchableOpacity>
        </View>
      ) : (
        <View style={styles.photoRow}>
          <TouchableOpacity testID="photo-camera-button" onPress={() => pickPhoto("camera")} style={styles.photoBtn} activeOpacity={0.7}>
            <Ionicons name="camera" size={22} color={colors.primary} />
            <Text style={styles.photoBtnText}>Caméra</Text>
          </TouchableOpacity>
          <TouchableOpacity testID="photo-library-button" onPress={() => pickPhoto("library")} style={styles.photoBtn} activeOpacity={0.7}>
            <Ionicons name="images" size={22} color={colors.primary} />
            <Text style={styles.photoBtnText}>Galerie</Text>
          </TouchableOpacity>
        </View>
      )}
    </View>
  );
}

// ════════════════════════════════════════════════════════════════════════
// Sub-components
// ════════════════════════════════════════════════════════════════════════
function SegBtn({ testID, icon, label, active, onPress }: any) {
  return (
    <TouchableOpacity testID={testID} onPress={onPress} activeOpacity={0.85}
      style={[styles.segBtn, active && styles.segBtnActive, { flex: 1 }]}>
      <Ionicons name={icon} size={18} color={active ? "#000" : colors.textSecondary} />
      <Text style={[styles.segBtnText, active && { color: "#000" }]}>{label}</Text>
    </TouchableOpacity>
  );
}

function CheckboxRow({ testID, label, sub, value, onChange }: any) {
  return (
    <View style={styles.checkboxRow}>
      <View style={{ flex: 1 }}>
        <Text style={styles.checkboxLabel}>{label}</Text>
        {sub && <Text style={styles.checkboxSub}>{sub}</Text>}
      </View>
      <Switch testID={testID} value={value} onValueChange={onChange}
        trackColor={{ false: colors.borderSubtle, true: colors.primary }} thumbColor="#fff" />
    </View>
  );
}

function CotField({ testID, label, value, onChange, onBlur, error }: any) {
  // 🛡️ Anti-corruption (bug iOS autocomplete) : on plafonne strict toute
  // saisie >9999mm (10m mur = impossible en menuiserie). Tronque les chiffres
  // surnuméraires sans crash.
  const handleChange = (v: string) => {
    let cleaned = (v || "").replace(",", ".");
    // Garde uniquement chiffres + un point décimal
    cleaned = cleaned.replace(/[^0-9.]/g, "");
    const dotIdx = cleaned.indexOf(".");
    if (dotIdx !== -1) {
      cleaned =
        cleaned.slice(0, dotIdx + 1) +
        cleaned.slice(dotIdx + 1).replace(/\./g, "");
    }
    // Plafond à 4 chiffres entiers (≤ 9999mm)
    const [int, dec] = cleaned.split(".");
    const safeInt = (int || "").slice(0, 4);
    const safeDec = dec !== undefined ? `.${dec.slice(0, 2)}` : "";
    onChange(safeInt + safeDec);
  };
  return (
    <View style={{ marginTop: 14 }}>
      <Text style={styles.label}>{label}</Text>
      <TextInput testID={testID} value={value} onChangeText={handleChange} onBlur={onBlur}
        keyboardType="decimal-pad" placeholder="0" placeholderTextColor={colors.placeholder}
        maxLength={7}
        autoCorrect={false}
        autoComplete="off"
        textContentType="none"
        style={[styles.input, error && styles.inputError]} />
      {error && (
        <Text style={styles.errorMsg} testID={testID ? `${testID}-error` : undefined}>
          ⚠ Cote obligatoire manquante
        </Text>
      )}
    </View>
  );
}

function DiagonalField({ testID, label, value, state, onChange, onValidate, onModify, error }: any) {
  const isAuto = state === "auto";
  const isValidated = state === "validated";
  return (
    <View style={{ marginTop: 14 }}>
      <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
        <Text style={styles.label}>{label}</Text>
        {isAuto && (
          <View style={styles.autoBadge}>
            <Ionicons name="calculator-outline" size={11} color="#000" />
            <Text style={styles.autoBadgeText}>AUTO PYTHAGORE</Text>
          </View>
        )}
        {isValidated && (
          <View style={styles.validBadge}>
            <Ionicons name="checkmark" size={12} color="#000" />
            <Text style={styles.autoBadgeText}>VALIDÉ</Text>
          </View>
        )}
      </View>
      <View style={{ flexDirection: "row", gap: 8 }}>
        <TextInput testID={testID} value={value} onChangeText={onChange}
          keyboardType="decimal-pad" placeholder="0" placeholderTextColor={colors.placeholder}
          editable={!isAuto}
          style={[styles.input, { flex: 1 }, error && styles.inputError,
            isAuto && { borderColor: colors.primary, color: colors.primary },
            isValidated && { borderColor: colors.success, color: colors.success }]} />
        {isAuto && (
          <>
            <TouchableOpacity testID={`${testID}-validate`} onPress={onValidate} activeOpacity={0.8}
              style={[styles.diagBtn, { backgroundColor: colors.success }]}>
              <Ionicons name="checkmark" size={18} color="#000" />
            </TouchableOpacity>
            <TouchableOpacity testID={`${testID}-modify`} onPress={onModify} activeOpacity={0.8}
              style={[styles.diagBtn, { backgroundColor: colors.warning }]}>
              <Ionicons name="create-outline" size={18} color="#000" />
            </TouchableOpacity>
          </>
        )}
      </View>
    </View>
  );
}

// ════════════════════════════════════════════════════════════════════════
// Styles
// ════════════════════════════════════════════════════════════════════════
const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: colors.bg },
  topBar: {
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    paddingHorizontal: 16, paddingTop: 12, paddingBottom: 10,
    borderBottomWidth: 1, borderBottomColor: colors.borderSubtle,
  },
  stepRow: { flexDirection: "row", gap: 8 },
  stepPill: {
    width: 28, height: 28, borderRadius: 14,
    backgroundColor: colors.surfaceElevated,
    alignItems: "center", justifyContent: "center",
    borderWidth: 1, borderColor: colors.borderSubtle,
  },
  stepPillActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  stepPillText: { color: colors.textSecondary, fontWeight: "800", fontSize: 12 },
  reportBtn: {
    flexDirection: "row", alignItems: "center", gap: 4,
    paddingHorizontal: 10, paddingVertical: 6, borderRadius: 8,
    backgroundColor: "#2a1010", borderWidth: 1, borderColor: colors.anomaly,
  },
  reportBtnText: { color: colors.anomaly, fontSize: 11, fontWeight: "700" },
  h1: { color: colors.textPrimary, fontSize: 18, fontWeight: "800", letterSpacing: 0.5 },
  h2: { color: colors.textSecondary, fontSize: 12, marginTop: 2 },
  sectionLabel: { color: colors.textSecondary, fontSize: 11, fontWeight: "900", letterSpacing: 0.8, marginBottom: 8 },
  errInline: { color: colors.anomaly, fontWeight: "900" },
  helperText: { color: colors.placeholder, fontSize: 12, marginBottom: 8, marginTop: 4, lineHeight: 16 },
  guideHint: {
    color: colors.textSecondary,
    fontSize: 11,
    fontStyle: "italic",
    textAlign: "center",
    marginTop: -2,
    marginBottom: 4,
    paddingHorizontal: 8,
  },
  label: { color: colors.textSecondary, fontSize: 11, fontWeight: "700", letterSpacing: 0.6, marginBottom: 6 },
  input: {
    backgroundColor: colors.inputBg, color: colors.textPrimary, borderRadius: 10,
    borderWidth: 1, borderColor: colors.borderStrong,
    paddingHorizontal: 12, paddingVertical: Platform.OS === "ios" ? 14 : 10,
    fontSize: 16, minHeight: 48,
  },
  inputError: { borderColor: colors.anomaly, backgroundColor: "#1a0808" },
  errorMsg: { color: colors.anomaly, fontSize: 11, fontWeight: "800", marginTop: 4, letterSpacing: 0.4 },
  row2: { flexDirection: "row", gap: 10 },
  segBtn: {
    flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 6,
    backgroundColor: colors.surface, borderRadius: 10, borderWidth: 1, borderColor: colors.borderSubtle,
    paddingVertical: 12, paddingHorizontal: 8, minHeight: 48,
  },
  segBtnActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  segBtnText: { color: colors.textSecondary, fontWeight: "800", fontSize: 12, letterSpacing: 0.4, textAlign: "center", flexShrink: 1 },
  facadeGrid: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  facadeCard: {
    width: "47%", backgroundColor: colors.surface, borderRadius: 10,
    borderWidth: 1, borderColor: colors.borderSubtle,
    paddingVertical: 14, paddingHorizontal: 10, alignItems: "center", gap: 6,
  },
  facadeCardActive: { borderColor: colors.primary, backgroundColor: "#1a0e05" },
  facadeLabel: { color: colors.textPrimary, fontWeight: "800", fontSize: 12, textAlign: "center", letterSpacing: 0.3 },
  insulOption: {
    flexDirection: "row", alignItems: "center", gap: 10,
    backgroundColor: colors.surface, borderRadius: 10,
    borderWidth: 1, borderColor: colors.borderSubtle,
    paddingVertical: 14, paddingHorizontal: 14, minHeight: 50,
  },
  insulOptionActive: { borderColor: colors.primary, backgroundColor: "#1a0e05" },
  insulOptionLabel: { color: colors.textPrimary, fontWeight: "800", fontSize: 13 },
  inlineHintBox: {
    flexDirection: "row", alignItems: "center", gap: 6, marginTop: 8,
    padding: 10, borderRadius: 8, backgroundColor: "#2a1c08",
    borderWidth: 1, borderColor: colors.warning,
  },
  inlineHintText: { color: colors.textSecondary, fontSize: 11, flex: 1, lineHeight: 15 },
  checkboxRow: {
    flexDirection: "row", alignItems: "center", gap: 12,
    paddingVertical: 12, paddingHorizontal: 14, borderRadius: 10,
    backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.borderSubtle, marginTop: 8,
  },
  checkboxLabel: { color: colors.textPrimary, fontSize: 14, fontWeight: "700" },
  checkboxSub: { color: colors.textSecondary, fontSize: 11, marginTop: 2 },
  shapeCard: {
    flexDirection: "row", alignItems: "center", gap: 10,
    backgroundColor: colors.surface, borderRadius: 12,
    borderWidth: 1, borderColor: colors.borderSubtle, padding: 14, minHeight: 84,
  },
  shapeCardActive: { borderColor: colors.primary, backgroundColor: "#1a0e05" },
  shapeLetterBadge: { width: 28, height: 28, borderRadius: 14, backgroundColor: colors.primary, alignItems: "center", justifyContent: "center" },
  shapeLetter: { color: "#000", fontWeight: "900", fontSize: 12 },
  shapeIconBox: { width: 56, height: 56, alignItems: "center", justifyContent: "center" },
  shapeTitle: { color: colors.textPrimary, fontWeight: "900", fontSize: 14, letterSpacing: 0.4 },
  shapeDesc: { color: colors.textSecondary, fontSize: 11, marginTop: 2, lineHeight: 15 },
  modeToggle: {
    flexDirection: "row", gap: 6, marginTop: 14, padding: 4,
    backgroundColor: colors.surface, borderRadius: 10,
    borderWidth: 1, borderColor: colors.borderSubtle,
  },
  modeTab: { flex: 1, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 6, paddingVertical: 10, borderRadius: 8 },
  modeTabActive: { backgroundColor: colors.primary },
  modeTabText: { color: colors.textSecondary, fontSize: 11, fontWeight: "900", letterSpacing: 0.6 },
  modeTabTextActive: { color: "#000" },
  sketchBox: { marginTop: 16, alignItems: "center", backgroundColor: colors.surface, borderRadius: 12, borderWidth: 1, borderColor: colors.borderSubtle, paddingVertical: 12 },
  autoBadge: { flexDirection: "row", alignItems: "center", gap: 4, backgroundColor: colors.primary, paddingHorizontal: 8, paddingVertical: 3, borderRadius: 6 },
  validBadge: { flexDirection: "row", alignItems: "center", gap: 4, backgroundColor: colors.success, paddingHorizontal: 8, paddingVertical: 3, borderRadius: 6 },
  autoBadgeText: { color: "#000", fontSize: 10, fontWeight: "900", letterSpacing: 0.5 },
  diagBtn: { width: 48, height: 48, borderRadius: 10, alignItems: "center", justifyContent: "center" },
  computeBtn: {
    marginTop: 12, flexDirection: "row", alignItems: "center", justifyContent: "center",
    gap: 8, paddingVertical: 12, paddingHorizontal: 14, borderRadius: 10,
    borderWidth: 1, borderColor: colors.primary, backgroundColor: "#1a0e05",
  },
  computeBtnText: { color: colors.primary, fontWeight: "900", fontSize: 13, letterSpacing: 0.8 },
  computedBox: {
    flexDirection: "row", alignItems: "center", flexWrap: "wrap", gap: 6,
    marginTop: 12, padding: 12, borderRadius: 10,
    backgroundColor: "#0b3b1c", borderWidth: 1, borderColor: colors.success,
  },
  computedLabel: { color: colors.success, fontWeight: "900", fontSize: 11, letterSpacing: 0.5 },
  computedValue: { color: colors.success, fontWeight: "900", fontSize: 18 },
  computedFormula: { color: colors.textSecondary, fontSize: 11, fontStyle: "italic" },
  photo: { width: "100%", height: 180, borderRadius: 12, marginTop: 8 },
  removePhoto: { position: "absolute", top: 16, right: 8, backgroundColor: "rgba(0,0,0,0.7)", padding: 6, borderRadius: 14 },
  photoRow: { flexDirection: "row", gap: 8, marginTop: 8 },
  photoBtn: { flex: 1, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 6, paddingVertical: 14, borderRadius: 10, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.borderSubtle },
  photoBtnText: { color: colors.primary, fontWeight: "700", fontSize: 13 },
  footer: { flexDirection: "row", gap: 10, padding: 16, borderTopWidth: 1, borderTopColor: colors.borderSubtle, backgroundColor: colors.bg },
  btn: { flex: 1, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8, minHeight: 52, borderRadius: 12, paddingHorizontal: 16 },
  btnPrimary: { backgroundColor: colors.primary },
  btnPrimaryText: { color: "#000", fontWeight: "900", fontSize: 14, letterSpacing: 0.8 },
  btnSecondary: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.borderSubtle },
  btnSecondaryText: { color: colors.textPrimary, fontWeight: "800", fontSize: 13, letterSpacing: 0.5 },
  modalOverlay: { flex: 1, backgroundColor: "rgba(0,0,0,0.7)", justifyContent: "center", padding: 20 },
  modalCard: { backgroundColor: colors.surface, borderRadius: 16, padding: 18, borderWidth: 1, borderColor: colors.borderSubtle },
  modalTitle: { color: colors.textPrimary, fontWeight: "800", fontSize: 16 },
  modalSub: { color: colors.textSecondary, fontSize: 12, marginTop: 4, marginBottom: 12 },
  reportInput: { backgroundColor: colors.inputBg, color: colors.textPrimary, borderRadius: 10, borderWidth: 1, borderColor: colors.borderStrong, padding: 12, minHeight: 100, textAlignVertical: "top", fontSize: 14 },
});
