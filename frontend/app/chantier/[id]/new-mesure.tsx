/**
 * ╔══════════════════════════════════════════════════════════════════════╗
 * ║  MesureChâssis — Wizard "Nouvelle Ouverture" — V1 (7 formes)         ║
 * ╠══════════════════════════════════════════════════════════════════════╣
 * ║  Architecture en 3 étapes :                                          ║
 * ║   1. Configuration globale (Type projet, Façade, Seuils, Options)    ║
 * ║   2. Sélection de la forme (7 formes)                                ║
 * ║   3. Cotes adaptatives selon la forme + finitions                    ║
 * ║                                                                      ║
 * ║  Tous les nouveaux champs (project_type, facade_type, shape,         ║
 * ║  opening_subtype, garage_*, triangle_*, oeil_diameter…) sont stockés ║
 * ║  dans payload.options{} pour rester rétro-compatible avec le backend ║
 * ║  existant. `block_type` est conservé pour compat exports/CSV/PDF.    ║
 * ╚══════════════════════════════════════════════════════════════════════╝
 */
import React, { useEffect, useMemo, useState } from "react";
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

// ════════════════════════════════════════════════════════════════════════
// Types & constantes
// ════════════════════════════════════════════════════════════════════════

type Step = 0 | 1 | 2;

/** Type de projet — adapte le wording / défauts des étapes suivantes. */
type ProjectType = "construction" | "renovation";

/** Type de façade (étape 1). */
type FacadeType =
  | "brique"
  | "pierre"
  | "crepi"
  | "bardage_bois"
  | "beton"
  | "ite_enduit"
  | "iti";

/** 7 formes de la V1. */
type Shape =
  | "rect" // A — Carré / Rectangle
  | "porte_entree" // B — Porte d'entrée
  | "porte_garage" // C — Porte de garage
  | "trapeze" // D — Trapèze
  | "triangle" // E — Triangle
  | "oeil_de_boeuf" // H — Œil-de-bœuf
  | "coulissant_levant"; // K — Coulissant levant

/** Sous-type d'ouvrant (rect uniquement). */
type OpeningSubtype = "fixe" | "ouvrant" | "oscillo_battant" | "coulissant";

/** Type de paroi (étape 3, héritée). */
type WallType = "ite" | "iti" | "brique_parement" | "crepi_simple";
type DiagState = "auto" | "validated" | "manual";

const FACADES: { key: FacadeType; label: string; icon: keyof typeof Ionicons.glyphMap }[] = [
  { key: "brique", label: "Brique apparente", icon: "grid-outline" },
  { key: "pierre", label: "Pierre", icon: "diamond-outline" },
  { key: "crepi", label: "Crépi", icon: "color-fill-outline" },
  { key: "bardage_bois", label: "Bardage bois", icon: "leaf-outline" },
  { key: "beton", label: "Béton", icon: "cube-outline" },
  { key: "ite_enduit", label: "ITE-Enduit", icon: "albums-outline" },
  { key: "iti", label: "ITI", icon: "layers-outline" },
];

const SHAPES: {
  key: Shape;
  letter: string;
  label: string;
  icon: keyof typeof Ionicons.glyphMap;
  desc: string;
}[] = [
  {
    key: "rect",
    letter: "A",
    label: "CARRÉ / RECTANGLE",
    icon: "square-outline",
    desc: "Fenêtre standard (fixe, ouvrant, oscillo-battant, coulissant)",
  },
  {
    key: "porte_entree",
    letter: "B",
    label: "PORTE D'ENTRÉE",
    icon: "exit-outline",
    desc: "Avec réserve sol & trait de niveau 1m",
  },
  {
    key: "porte_garage",
    letter: "C",
    label: "PORTE DE GARAGE",
    icon: "car-outline",
    desc: "Avec linteau et écoinçons",
  },
  {
    key: "trapeze",
    letter: "D",
    label: "TRAPÈZE",
    icon: "triangle-outline",
    desc: "Hauteur gauche ≠ Hauteur droite",
  },
  {
    key: "triangle",
    letter: "E",
    label: "TRIANGLE",
    icon: "trail-sign-outline",
    desc: "Base + hauteur",
  },
  {
    key: "oeil_de_boeuf",
    letter: "H",
    label: "ŒIL-DE-BŒUF",
    icon: "ellipse-outline",
    desc: "Ouverture circulaire (diamètre)",
  },
  {
    key: "coulissant_levant",
    letter: "K",
    label: "COULISSANT LEVANT",
    icon: "swap-horizontal-outline",
    desc: "Levant-coulissant avec réserve sol",
  },
];

const OPENING_SUBTYPES: { key: OpeningSubtype; label: string; icon: keyof typeof Ionicons.glyphMap }[] = [
  { key: "fixe", label: "Fixe", icon: "stop-outline" },
  { key: "ouvrant", label: "Ouvrant", icon: "open-outline" },
  { key: "oscillo_battant", label: "Oscillo-battant", icon: "sync-outline" },
  { key: "coulissant", label: "Coulissant", icon: "swap-horizontal-outline" },
];

// ════════════════════════════════════════════════════════════════════════
// État des étapes
// ════════════════════════════════════════════════════════════════════════

type Step1Data = {
  project_type: ProjectType;
  facade_type: FacadeType | null;
  sill_already_installed: boolean | null; // null = pas encore choisi
  sill_thickness_mm: string;
  has_breastwork: boolean;
  has_horizontal_cut: boolean;
};

const initStep1 = (): Step1Data => ({
  project_type: "renovation",
  facade_type: null,
  sill_already_installed: null,
  sill_thickness_mm: "",
  has_breastwork: false,
  has_horizontal_cut: false,
});

type Step3Data = {
  // Cotes principales (toutes les formes)
  bay_width: string;
  bay_height: string;
  diag_1: string;
  diag_1_state: DiagState;
  diag_2: string;
  diag_2_state: DiagState;
  // Mode rénovation (rect)
  renovation_mode: boolean;
  width_top: string;
  width_bottom: string;
  height_left: string;
  height_right: string;
  // Trapèze
  trap_height_left: string;
  trap_height_right: string;
  // Triangle
  triangle_base: string;
  triangle_height: string;
  // Œil-de-bœuf
  oeil_diameter: string;
  // Porte de garage
  garage_lintel: string;
  garage_ecoincon_left: string;
  garage_ecoincon_right: string;
  // Portes & coulissant levant
  floor_reserve: string;
  has_1m_level_mark: boolean;
  // Rect — sous-type d'ouvrant
  opening_subtype: OpeningSubtype | null;
  // Conception maçonnerie (hérité)
  bloc_thickness: string;
  wall_type: WallType | null;
  insulation_thickness: string;
  finish_outer: string;
  finish_inner: string;
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
  opening_subtype: "fixe",
  bloc_thickness: "",
  wall_type: null,
  insulation_thickness: "",
  finish_outer: "",
  finish_inner: "",
});

const parseNum = (s: string) => {
  const n = parseFloat(s.replace(",", "."));
  return Number.isFinite(n) ? n : null;
};

/**
 * Mapping shape → block_type (backend compat).
 * Le backend ne connaît que 4 block_types historiques.
 * Toutes les nouvelles formes sont mappées + détaillées via options.shape.
 */
const shapeToBlockType = (s: Shape): "standard" | "coulissant" | "porte" | "trapeze" => {
  switch (s) {
    case "rect":
    case "oeil_de_boeuf":
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

/** Reverse-mapping pour l'edit mode. */
const inferShape = (m: any): Shape => {
  const fromOpts = (m?.options?.shape as Shape) || null;
  if (fromOpts) return fromOpts;
  // Fallback selon block_type historique
  const bt = m?.block_type;
  if (bt === "trapeze") return "trapeze";
  if (bt === "porte") return "porte_entree";
  if (bt === "coulissant") return "rect"; // ancien coulissant → rect+sous-type
  return "rect";
};

// ════════════════════════════════════════════════════════════════════════
// Composant principal
// ════════════════════════════════════════════════════════════════════════

export default function NewMesureWizard() {
  const { id, mesure_id } = useLocalSearchParams<{ id: string; mesure_id?: string }>();
  const editingId = (mesure_id as string) || null;
  const router = useRouter();

  const [step, setStep] = useState<Step>(0);
  const [shape, setShape] = useState<Shape | null>(null);
  const [label, setLabel] = useState("");
  const [photo, setPhoto] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [loadingEdit, setLoadingEdit] = useState(!!editingId);

  const [s1, setS1] = useState<Step1Data>(initStep1());
  const [s1Err, setS1Err] = useState<Record<string, boolean>>({});

  const [s3, setS3] = useState<Step3Data>(initStep3());
  const [s3Err, setS3Err] = useState<Record<string, boolean>>({});

  const [reportOpen, setReportOpen] = useState(false);
  const [reportText, setReportText] = useState("");
  const [reportSending, setReportSending] = useState(false);

  const setS1Field = <K extends keyof Step1Data>(k: K, v: Step1Data[K]) =>
    setS1((p) => ({ ...p, [k]: v }));
  const setS3Field = <K extends keyof Step3Data>(k: K, v: Step3Data[K]) =>
    setS3((p) => ({ ...p, [k]: v }));

  // ────── Edit mode loader ──────────────────────────────────────────────
  useEffect(() => {
    if (!editingId) return;
    (async () => {
      try {
        const r = await api.get(`/mesures/${editingId}`);
        const m = r.data as any;
        const inferred = inferShape(m);
        setShape(inferred);
        setLabel(m.label || "");
        setPhoto(m.photo_url || null);
        const opts = m.options || {};
        const toStr = (v: any) => (v == null || v === "" ? "" : String(v));
        setS1({
          project_type: opts.project_type || (m.renovation_mode ? "renovation" : "construction"),
          facade_type: opts.facade_type || null,
          sill_already_installed:
            opts.sill_already_installed == null ? null : !!opts.sill_already_installed,
          sill_thickness_mm: toStr(opts.sill_thickness_mm),
          has_breastwork: !!opts.has_breastwork,
          has_horizontal_cut: !!opts.has_horizontal_cut,
        });
        const isTrap = inferred === "trapeze";
        const isReno = !!m.renovation_mode;
        setS3((prev) => ({
          ...prev,
          bay_width: isTrap ? toStr(m.bay_width) : isReno ? "" : toStr(m.bay_width),
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
          floor_reserve: toStr(m.floor_reserve),
          has_1m_level_mark: !!opts.has_1m_level_mark,
          opening_subtype: opts.opening_subtype || "fixe",
          bloc_thickness: toStr(m.bloc_thickness),
          wall_type: m.wall_type || null,
          insulation_thickness: toStr(m.insulation_thickness),
          finish_outer: toStr(m.finish_outer),
          finish_inner: toStr(m.finish_inner),
        }));
        // Edit : on commence à l'étape 1 mais shape déjà connu
        setStep(0);
      } catch {
        Alert.alert("Erreur", "Mesure introuvable.");
        router.back();
      } finally {
        setLoadingEdit(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editingId]);

  // ────── Pythagore (rect, porte, coulissant — pas trap/triangle/oeil) ──
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
      if (force || (prev.diag_1_state !== "validated" && prev.diag_1.trim().length === 0)) {
        next = { ...next, diag_1: String(d), diag_1_state: "auto" };
      }
      if (force || (prev.diag_2_state !== "validated" && prev.diag_2.trim().length === 0)) {
        next = { ...next, diag_2: String(d), diag_2_state: "auto" };
      }
      return next;
    });
  };

  const canComputeDiag = useMemo(
    () => usesDiagonals(shape) && !!parseNum(s3.bay_width) && !!parseNum(s3.bay_height),
    [shape, s3.bay_width, s3.bay_height]
  );

  // ────── Validations ───────────────────────────────────────────────────
  const validateStep1 = (): boolean => {
    const err: Record<string, boolean> = {};
    if (!s1.facade_type) err.facade_type = true;
    if (s1.sill_already_installed == null) err.sill_already_installed = true;
    if (s1.sill_already_installed === false && !parseNum(s1.sill_thickness_mm)) {
      err.sill_thickness_mm = true;
    }
    setS1Err(err);
    return Object.keys(err).length === 0;
  };

  const validateStep3 = (): boolean => {
    if (!shape) return false;
    const err: Record<string, boolean> = {};
    if (!label.trim()) {
      Alert.alert("Libellé manquant", "Indiquez un libellé (ex. Salon).");
      return false;
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
    } else {
      // rect / porte_entree / coulissant_levant
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
      if (
        (shape === "porte_entree" || shape === "coulissant_levant") &&
        !parseNum(s3.floor_reserve)
      ) {
        err.floor_reserve = true;
      }
    }
    if (!parseNum(s3.bloc_thickness)) err.bloc_thickness = true;
    if (!s3.wall_type) err.wall_type = true;
    setS3Err(err);
    return Object.keys(err).length === 0;
  };

  // ────── Photo helpers ─────────────────────────────────────────────────
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

  // ────── Submit ────────────────────────────────────────────────────────
  const submit = async () => {
    if (!shape || !validateStep3()) return;
    setSaving(true);

    // Construit le payload
    const opts: Record<string, unknown> = {
      // Étape 1
      project_type: s1.project_type,
      facade_type: s1.facade_type,
      sill_already_installed: s1.sill_already_installed,
      sill_thickness_mm: s1.sill_already_installed === false ? parseNum(s1.sill_thickness_mm) : null,
      has_breastwork: s1.has_breastwork,
      has_horizontal_cut: s1.has_horizontal_cut,
      // Étape 2 — forme + sous-type
      shape,
    };
    if (shape === "rect") opts.opening_subtype = s3.opening_subtype;
    if (shape === "porte_entree" || shape === "coulissant_levant") {
      opts.has_1m_level_mark = s3.has_1m_level_mark;
    }
    if (shape === "triangle") {
      opts.triangle_base_mm = parseNum(s3.triangle_base);
      opts.triangle_height_mm = parseNum(s3.triangle_height);
    }
    if (shape === "oeil_de_boeuf") {
      opts.oeil_diameter_mm = parseNum(s3.oeil_diameter);
    }
    if (shape === "porte_garage") {
      opts.garage_lintel_mm = parseNum(s3.garage_lintel);
      opts.garage_ecoincon_left_mm = parseNum(s3.garage_ecoincon_left);
      opts.garage_ecoincon_right_mm = parseNum(s3.garage_ecoincon_right);
    }

    const payload: Record<string, unknown> = {
      chantier_id: id,
      block_type: shapeToBlockType(shape),
      label: label.trim(),
      photo_url: photo,
      bay_width: parseNum(s3.bay_width),
      options: opts,
    };

    if (shape === "trapeze") {
      payload.height_left = parseNum(s3.trap_height_left);
      payload.height_right = parseNum(s3.trap_height_right);
    } else if (shape === "triangle") {
      // Mappé en trapèze avec base=width, hauteur=height_left=height_right
      payload.bay_width = parseNum(s3.triangle_base);
      payload.height_left = parseNum(s3.triangle_height);
      payload.height_right = parseNum(s3.triangle_height);
    } else if (shape === "oeil_de_boeuf") {
      // Mappé : largeur=hauteur=diamètre
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
    } else {
      payload.bay_height = parseNum(s3.bay_height);
      payload.bay_diagonal_1 = parseNum(s3.diag_1);
      payload.bay_diagonal_2 = parseNum(s3.diag_2);
      payload.diag_1_verified = s3.diag_1_state !== "auto";
      payload.diag_2_verified = s3.diag_2_state !== "auto";
    }

    payload.bloc_thickness = parseNum(s3.bloc_thickness);
    payload.wall_type = s3.wall_type;
    if (shape === "porte_entree" || shape === "porte_garage" || shape === "coulissant_levant") {
      payload.floor_reserve = parseNum(s3.floor_reserve);
    }
    if (s3.insulation_thickness) payload.insulation_thickness = parseNum(s3.insulation_thickness);
    if (s3.finish_outer) payload.finish_outer = parseNum(s3.finish_outer);
    if (s3.finish_inner) payload.finish_inner = parseNum(s3.finish_inner);

    try {
      const online = await isOnline();
      if (!online && !editingId) {
        await enqueueMesure(payload);
        Alert.alert("Hors ligne", "Mesure ajoutée à la file de synchro.", [
          { text: "OK", onPress: () => router.back() },
        ]);
        return;
      }
      if (editingId) {
        await api.patch(`/mesures/${editingId}`, payload);
      } else {
        await api.post("/mesures", payload);
      }
      router.back();
    } catch {
      if (editingId) {
        Alert.alert("Erreur", "Mise à jour impossible.");
      } else {
        await enqueueMesure(payload);
        Alert.alert("Réseau indisponible", "Mesure mise en file d'attente.", [
          { text: "OK", onPress: () => router.back() },
        ]);
      }
    } finally {
      setSaving(false);
    }
  };

  // ────── Quick report ───────────────────────────────────────────────────
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

  // ────── Navigation entre étapes ────────────────────────────────────────
  const goNextFromStep1 = () => {
    if (!validateStep1()) return;
    setStep(1);
  };

  const onPickShape = (sh: Shape) => {
    setShape(sh);
    setStep(2);
  };

  const canGoBack = step > 0;
  const goBack = () => {
    if (step === 0) {
      router.back();
    } else {
      setStep((step - 1) as Step);
    }
  };

  if (loadingEdit) {
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
        {/* ── Top bar : steps + signaler ────────────────────────────── */}
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
          contentContainerStyle={{ padding: 16, paddingBottom: 200 }}
          keyboardShouldPersistTaps="handled"
        >
          {step === 0 && (
            <Step1Config s1={s1} setField={setS1Field} err={s1Err} />
          )}
          {step === 1 && (
            <Step2Shape onPick={onPickShape} current={shape} />
          )}
          {step === 2 && shape && (
            <Step3Cotes
              shape={shape}
              label={label}
              setLabel={setLabel}
              s3={s3}
              setField={setS3Field}
              err={s3Err}
              photo={photo}
              setPhoto={setPhoto}
              pickPhoto={pickPhoto}
              onBlurDimension={() => computeDiagonals(false)}
              onComputeDiagonals={() => computeDiagonals(true)}
              canComputeDiag={canComputeDiag}
            />
          )}
        </ScrollView>

        {/* ── Footer nav ──────────────────────────────────────────── */}
        <View style={styles.footer}>
          {canGoBack && (
            <TouchableOpacity
              testID="wizard-back"
              onPress={goBack}
              style={[styles.btn, styles.btnSecondary]}
              activeOpacity={0.7}
            >
              <Ionicons name="arrow-back" size={20} color={colors.textPrimary} />
              <Text style={styles.btnSecondaryText}>RETOUR</Text>
            </TouchableOpacity>
          )}
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

      {/* ── Modal de signalement ──────────────────────────────────── */}
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
// Étape 1 — Configuration globale
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
      <Text style={styles.h1}>CONFIGURATION DU CHANTIER</Text>
      <Text style={styles.h2}>Étape 1/3 · Contexte technique de l'ouverture</Text>

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

      {/* Type de façade */}
      <Text style={[styles.sectionLabel, { marginTop: 22 }]}>
        TYPE DE FAÇADE * {err.facade_type && <Text style={styles.errInline}> ⚠</Text>}
      </Text>
      <View style={styles.facadeGrid}>
        {FACADES.map((f) => {
          const active = s1.facade_type === f.key;
          return (
            <TouchableOpacity
              key={f.key}
              testID={`facade-${f.key}`}
              onPress={() => setField("facade_type", f.key)}
              activeOpacity={0.85}
              style={[
                styles.facadeCard,
                active && styles.facadeCardActive,
                err.facade_type && !active && { borderColor: colors.anomaly },
              ]}
            >
              <Ionicons
                name={f.icon}
                size={22}
                color={active ? colors.primary : colors.textSecondary}
              />
              <Text style={[styles.facadeLabel, active && { color: colors.primary }]}>
                {f.label}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>

      {/* Statut des seuils */}
      <Text style={[styles.sectionLabel, { marginTop: 22 }]}>
        STATUT DES SEUILS *
        {err.sill_already_installed && <Text style={styles.errInline}> ⚠</Text>}
      </Text>
      <Text style={styles.helperText}>Les seuils sont-ils déjà posés sur ce chantier ?</Text>
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
        <View style={styles.inlineHintBox}>
          <Ionicons name="information-circle" size={14} color={colors.warning} />
          <Text style={styles.inlineHintText}>
            Indiquez l'épaisseur prévue pour anticiper la cote finale.
          </Text>
        </View>
      )}
      {s1.sill_already_installed === false && (
        <CotField
          testID="input-sill-thickness"
          label="ÉPAISSEUR FUTURE DU SEUIL (mm) *"
          value={s1.sill_thickness_mm}
          onChange={(v) => setField("sill_thickness_mm", v.replace(",", "."))}
          error={!!err.sill_thickness_mm}
        />
      )}

      {/* Options globales */}
      <Text style={[styles.sectionLabel, { marginTop: 22 }]}>OPTIONS GLOBALES</Text>
      <CheckboxRow
        testID="opt-breastwork"
        label="Allège"
        sub="Maçonnerie sous la baie (facultatif)"
        value={s1.has_breastwork}
        onChange={(v) => setField("has_breastwork", v)}
      />
      <CheckboxRow
        testID="opt-horizontal-cut"
        label="Coupe horizontale (Retour de butée)"
        sub="Présence d'un retour de butée horizontal"
        value={s1.has_horizontal_cut}
        onChange={(v) => setField("has_horizontal_cut", v)}
      />
    </View>
  );
}

// ════════════════════════════════════════════════════════════════════════
// Étape 2 — Sélection de la forme
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
                <Ionicons
                  name={s.icon}
                  size={32}
                  color={active ? colors.primary : colors.textPrimary}
                />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={[styles.shapeTitle, active && { color: colors.primary }]}>
                  {s.label}
                </Text>
                <Text style={styles.shapeDesc}>{s.desc}</Text>
              </View>
              <Ionicons
                name="chevron-forward"
                size={20}
                color={active ? colors.primary : colors.borderStrong}
              />
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
// Étape 3 — Cotes adaptatives
// ════════════════════════════════════════════════════════════════════════
function Step3Cotes({
  shape,
  label,
  setLabel,
  s3,
  setField,
  err,
  photo,
  setPhoto,
  pickPhoto,
  onBlurDimension,
  onComputeDiagonals,
  canComputeDiag,
}: {
  shape: Shape;
  label: string;
  setLabel: (v: string) => void;
  s3: Step3Data;
  setField: <K extends keyof Step3Data>(k: K, v: Step3Data[K]) => void;
  err: Record<string, boolean>;
  photo: string | null;
  setPhoto: (v: string | null) => void;
  pickPhoto: (s: "camera" | "library") => void;
  onBlurDimension: () => void;
  onComputeDiagonals: () => void;
  canComputeDiag: boolean;
}) {
  const isRectFamily =
    shape === "rect" ||
    shape === "porte_entree" ||
    shape === "porte_garage" ||
    shape === "coulissant_levant";
  const showSubtype = shape === "rect";
  const show1mLevel = shape === "porte_entree" || shape === "coulissant_levant";
  const showFloorReserve =
    shape === "porte_entree" || shape === "porte_garage" || shape === "coulissant_levant";
  const Sketch =
    shape === "trapeze" || shape === "triangle" ? RawBaySchemaTrapeze : RawBaySchemaRect;

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

      <Text style={[styles.label, { marginTop: 14 }]}>Libellé de l'ouverture *</Text>
      <TextInput
        testID="mesure-label-input"
        value={label}
        onChangeText={setLabel}
        placeholder="ex. Salon, Chambre 1, Porte d'entrée..."
        placeholderTextColor={colors.placeholder}
        style={styles.input}
      />

      {/* ── Rect : sous-type d'ouvrant ─────────────────────────────── */}
      {showSubtype && (
        <>
          <Text style={[styles.sectionLabel, { marginTop: 18 }]}>TYPE D'OUVRANT</Text>
          <View style={styles.openingGrid}>
            {OPENING_SUBTYPES.map((o) => {
              const active = s3.opening_subtype === o.key;
              return (
                <TouchableOpacity
                  key={o.key}
                  testID={`subtype-${o.key}`}
                  onPress={() => setField("opening_subtype", o.key)}
                  activeOpacity={0.85}
                  style={[styles.openingCard, active && styles.openingCardActive]}
                >
                  <Ionicons
                    name={o.icon}
                    size={20}
                    color={active ? colors.primary : colors.textSecondary}
                  />
                  <Text style={[styles.openingLabel, active && { color: colors.primary }]}>
                    {o.label}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </View>
        </>
      )}

      {/* ── Rect family : toggle Standard / Vérif. Rénovation ──────── */}
      {shape === "rect" && (
        <View style={styles.modeToggle}>
          <TouchableOpacity
            testID="mode-standard-tab"
            onPress={() => setField("renovation_mode", false)}
            activeOpacity={0.8}
            style={[styles.modeTab, !s3.renovation_mode && styles.modeTabActive]}
          >
            <Ionicons
              name="resize-outline"
              size={14}
              color={!s3.renovation_mode ? "#000" : colors.textSecondary}
            />
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
            <Ionicons
              name="construct-outline"
              size={14}
              color={s3.renovation_mode ? "#000" : colors.textSecondary}
            />
            <Text style={[styles.modeTabText, s3.renovation_mode && styles.modeTabTextActive]}>
              VÉRIF. RÉNOVATION
            </Text>
          </TouchableOpacity>
        </View>
      )}

      <View style={styles.sketchBox}>
        <Sketch
          values={{
            bay_width: s3.bay_width,
            bay_height: s3.bay_height,
            bay_diagonal: s3.diag_1,
          }}
        />
      </View>

      {/* ── Trapèze ────────────────────────────────────────────────── */}
      {shape === "trapeze" && (
        <>
          <CotField
            testID="input-bay-width"
            label="LARGEUR (mm) *"
            value={s3.bay_width}
            onChange={(v) => setField("bay_width", v.replace(",", "."))}
            error={!!err.bay_width}
          />
          <CotField
            testID="input-trap-height-left"
            label="HAUTEUR GAUCHE (mm) *"
            value={s3.trap_height_left}
            onChange={(v) => setField("trap_height_left", v.replace(",", "."))}
            error={!!err.trap_height_left}
          />
          <CotField
            testID="input-trap-height-right"
            label="HAUTEUR DROITE (mm) *"
            value={s3.trap_height_right}
            onChange={(v) => setField("trap_height_right", v.replace(",", "."))}
            error={!!err.trap_height_right}
          />
        </>
      )}

      {/* ── Triangle ───────────────────────────────────────────────── */}
      {shape === "triangle" && (
        <>
          <CotField
            testID="input-triangle-base"
            label="BASE (mm) *"
            value={s3.triangle_base}
            onChange={(v) => setField("triangle_base", v.replace(",", "."))}
            error={!!err.triangle_base}
          />
          <CotField
            testID="input-triangle-height"
            label="HAUTEUR (mm) *"
            value={s3.triangle_height}
            onChange={(v) => setField("triangle_height", v.replace(",", "."))}
            error={!!err.triangle_height}
          />
        </>
      )}

      {/* ── Œil-de-bœuf ────────────────────────────────────────────── */}
      {shape === "oeil_de_boeuf" && (
        <CotField
          testID="input-oeil-diameter"
          label="DIAMÈTRE (mm) *"
          value={s3.oeil_diameter}
          onChange={(v) => setField("oeil_diameter", v.replace(",", "."))}
          error={!!err.oeil_diameter}
        />
      )}

      {/* ── Porte de garage ───────────────────────────────────────── */}
      {shape === "porte_garage" && (
        <>
          <CotField
            testID="input-bay-width"
            label="LARGEUR (mm) *"
            value={s3.bay_width}
            onChange={(v) => setField("bay_width", v.replace(",", "."))}
            onBlur={onBlurDimension}
            error={!!err.bay_width}
          />
          <CotField
            testID="input-bay-height"
            label="HAUTEUR (mm) *"
            value={s3.bay_height}
            onChange={(v) => setField("bay_height", v.replace(",", "."))}
            onBlur={onBlurDimension}
            error={!!err.bay_height}
          />
          <Text style={[styles.sectionLabel, { marginTop: 18 }]}>SPÉCIFIQUES PORTE DE GARAGE</Text>
          <CotField
            testID="input-garage-lintel"
            label="LINTEAU (mm) *"
            value={s3.garage_lintel}
            onChange={(v) => setField("garage_lintel", v.replace(",", "."))}
            error={!!err.garage_lintel}
          />
          <View style={styles.row2}>
            <View style={{ flex: 1 }}>
              <CotField
                testID="input-garage-ecoincon-left"
                label="ÉCOINÇON GAUCHE (mm) *"
                value={s3.garage_ecoincon_left}
                onChange={(v) => setField("garage_ecoincon_left", v.replace(",", "."))}
                error={!!err.garage_ecoincon_left}
              />
            </View>
            <View style={{ flex: 1 }}>
              <CotField
                testID="input-garage-ecoincon-right"
                label="ÉCOINÇON DROIT (mm) *"
                value={s3.garage_ecoincon_right}
                onChange={(v) => setField("garage_ecoincon_right", v.replace(",", "."))}
                error={!!err.garage_ecoincon_right}
              />
            </View>
          </View>
        </>
      )}

      {/* ── Rect / Porte / Coulissant levant : standard ─────────────── */}
      {isRectFamily && shape !== "porte_garage" && !s3.renovation_mode && (
        <>
          <CotField
            testID="input-bay-width"
            label="LARGEUR (mm) *"
            value={s3.bay_width}
            onChange={(v) => setField("bay_width", v.replace(",", "."))}
            onBlur={onBlurDimension}
            error={!!err.bay_width}
          />
          <CotField
            testID="input-bay-height"
            label="HAUTEUR (mm) *"
            value={s3.bay_height}
            onChange={(v) => setField("bay_height", v.replace(",", "."))}
            onBlur={onBlurDimension}
            error={!!err.bay_height}
          />
        </>
      )}

      {/* ── Rect : Vérif Rénovation 4 cotes ─────────────────────────── */}
      {shape === "rect" && s3.renovation_mode && (
        <>
          <View style={styles.row2}>
            <View style={{ flex: 1 }}>
              <CotField
                testID="input-width-top"
                label="LARGEUR HAUT (mm) *"
                value={s3.width_top}
                onChange={(v) => setField("width_top", v.replace(",", "."))}
                error={!!err.width_top}
              />
            </View>
            <View style={{ flex: 1 }}>
              <CotField
                testID="input-width-bottom"
                label="LARGEUR BAS (mm) *"
                value={s3.width_bottom}
                onChange={(v) => setField("width_bottom", v.replace(",", "."))}
                error={!!err.width_bottom}
              />
            </View>
          </View>
          <View style={styles.row2}>
            <View style={{ flex: 1 }}>
              <CotField
                testID="input-height-left"
                label="HAUTEUR GAUCHE (mm) *"
                value={s3.height_left}
                onChange={(v) => setField("height_left", v.replace(",", "."))}
                error={!!err.height_left}
              />
            </View>
            <View style={{ flex: 1 }}>
              <CotField
                testID="input-height-right"
                label="HAUTEUR DROITE (mm) *"
                value={s3.height_right}
                onChange={(v) => setField("height_right", v.replace(",", "."))}
                error={!!err.height_right}
              />
            </View>
          </View>
          {(() => {
            const wt = parseNum(s3.width_top) ?? 0;
            const wb = parseNum(s3.width_bottom) ?? 0;
            const hl = parseNum(s3.height_left) ?? 0;
            const hr = parseNum(s3.height_right) ?? 0;
            const dW = Math.abs(wt - wb);
            const dH = Math.abs(hl - hr);
            const trigger = wt && wb && hl && hr && (dW > 10 || dH > 10);
            return trigger ? (
              <View testID="out-of-level-alert" style={styles.alertBox}>
                <Ionicons name="warning" size={16} color={colors.warning} />
                <View style={{ flex: 1, marginLeft: 8 }}>
                  <Text style={styles.alertTitle}>⚠️ Écart de niveau {">"} 10mm détecté</Text>
                  <Text style={styles.alertSub}>
                    Δ Largeur : {dW.toFixed(0)} mm · Δ Hauteur : {dH.toFixed(0)} mm — Attention à
                    la pose.
                  </Text>
                </View>
              </View>
            ) : null;
          })()}
        </>
      )}

      {/* ── Diagonales (rect family hors trap/triangle/oeil) ────────── */}
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
          <DiagonalField
            testID="input-diag-1"
            label="DIAGONALE 1 (mm) *"
            value={s3.diag_1}
            state={s3.diag_1_state}
            onChange={(v) => {
              setField("diag_1", v.replace(",", "."));
              setField("diag_1_state", "manual");
            }}
            onValidate={() => validateDiag(1)}
            onModify={() => modifyDiag(1)}
            error={!!err.diag_1}
          />
          <DiagonalField
            testID="input-diag-2"
            label="DIAGONALE 2 (mm) *"
            value={s3.diag_2}
            state={s3.diag_2_state}
            onChange={(v) => {
              setField("diag_2", v.replace(",", "."));
              setField("diag_2_state", "manual");
            }}
            onValidate={() => validateDiag(2)}
            onModify={() => modifyDiag(2)}
            error={!!err.diag_2}
          />
        </>
      )}

      {/* ── Réserve sol (portes + coulissant levant) ────────────────── */}
      {showFloorReserve && (
        <CotField
          testID="input-floor-reserve"
          label="RÉSERVE SOL FINI (mm) *"
          value={s3.floor_reserve}
          onChange={(v) => setField("floor_reserve", v.replace(",", "."))}
          error={!!err.floor_reserve}
        />
      )}

      {/* ── Trait de niveau 1m (portes & coulissant levant) ────────── */}
      {show1mLevel && (
        <CheckboxRow
          testID="opt-1m-level-mark"
          label="Trait de niveau 1m"
          sub="Présent — utile pour le calcul de réserve"
          value={s3.has_1m_level_mark}
          onChange={(v) => setField("has_1m_level_mark", v)}
        />
      )}

      {/* ── Conception maçonnerie (toutes formes) ───────────────────── */}
      <Text style={[styles.sectionLabel, { marginTop: 24 }]}>CONCEPTION MAÇONNERIE</Text>
      <CotField
        testID="input-bloc-thickness"
        label="ÉPAISSEUR BLOC BÉTON (mm) *"
        value={s3.bloc_thickness}
        onChange={(v) => setField("bloc_thickness", v.replace(",", "."))}
        error={!!err.bloc_thickness}
      />

      <Text style={[styles.label, { marginTop: 18 }]}>
        Type de paroi * <Text style={styles.indicSuffix}>(INDICATIF)</Text>
      </Text>
      <View style={styles.wallGrid}>
        {(
          [
            { key: "ite", label: "ITE", sub: "Isolation Extérieure", variant: "ite" },
            { key: "iti", label: "ITI", sub: "Isolation Intérieure", variant: "iti" },
            {
              key: "brique_parement",
              label: "BRIQUE",
              sub: "Brique de parement",
              variant: "crepi",
            },
            { key: "crepi_simple", label: "CRÉPI", sub: "Crépi simple", variant: "crepi" },
          ] as const
        ).map((w) => {
          const active = s3.wall_type === w.key;
          return (
            <TouchableOpacity
              key={w.key}
              testID={`wall-type-${w.key}`}
              onPress={() => setField("wall_type", w.key as WallType)}
              activeOpacity={0.8}
              style={[
                styles.wallCard,
                active && styles.wallCardActive,
                err.wall_type && !active && styles.wallCardError,
              ]}
            >
              <WallSection variant={w.variant as any} size={64} />
              <Text style={[styles.wallLabel, active && { color: colors.primary }]}>
                {w.label}
              </Text>
              <Text style={styles.wallSub}>{w.sub}</Text>
              <Text style={styles.wallIndic}>(INDICATIF)</Text>
            </TouchableOpacity>
          );
        })}
      </View>

      {(s3.wall_type === "ite" || s3.wall_type === "iti") && (
        <>
          <CotField
            testID="input-insulation-thickness"
            label="ÉPAISSEUR ISOLANT (mm)"
            value={s3.insulation_thickness}
            onChange={(v) => setField("insulation_thickness", v.replace(",", "."))}
          />
          <CotField
            testID="input-finish-outer"
            label="FINITION EXTÉRIEURE (mm)"
            value={s3.finish_outer}
            onChange={(v) => setField("finish_outer", v.replace(",", "."))}
          />
          <CotField
            testID="input-finish-inner"
            label="FINITION INTÉRIEURE (mm)"
            value={s3.finish_inner}
            onChange={(v) => setField("finish_inner", v.replace(",", "."))}
          />
        </>
      )}

      {/* ── Photo (toutes formes) ──────────────────────────────────── */}
      <Text style={[styles.label, { marginTop: 24 }]}>Photo (optionnel)</Text>
      {photo ? (
        <View>
          <Image source={{ uri: photo }} style={styles.photo} />
          <TouchableOpacity
            testID="remove-photo-button"
            onPress={() => setPhoto(null)}
            style={styles.removePhoto}
          >
            <Ionicons name="trash" size={16} color="#fff" />
          </TouchableOpacity>
        </View>
      ) : (
        <View style={styles.photoRow}>
          <TouchableOpacity
            testID="photo-camera-button"
            onPress={() => pickPhoto("camera")}
            style={styles.photoBtn}
            activeOpacity={0.7}
          >
            <Ionicons name="camera" size={22} color={colors.primary} />
            <Text style={styles.photoBtnText}>Caméra</Text>
          </TouchableOpacity>
          <TouchableOpacity
            testID="photo-library-button"
            onPress={() => pickPhoto("library")}
            style={styles.photoBtn}
            activeOpacity={0.7}
          >
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
function SegBtn({
  testID,
  icon,
  label,
  active,
  onPress,
}: {
  testID?: string;
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
      style={[styles.segBtn, active && styles.segBtnActive, { flex: 1 }]}
    >
      <Ionicons name={icon} size={18} color={active ? "#000" : colors.textSecondary} />
      <Text style={[styles.segBtnText, active && { color: "#000" }]}>{label}</Text>
    </TouchableOpacity>
  );
}

function CheckboxRow({
  testID,
  label,
  sub,
  value,
  onChange,
}: {
  testID?: string;
  label: string;
  sub?: string;
  value: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <View style={styles.checkboxRow}>
      <View style={{ flex: 1 }}>
        <Text style={styles.checkboxLabel}>{label}</Text>
        {sub && <Text style={styles.checkboxSub}>{sub}</Text>}
      </View>
      <Switch
        testID={testID}
        value={value}
        onValueChange={onChange}
        trackColor={{ false: colors.borderSubtle, true: colors.primary }}
        thumbColor="#fff"
      />
    </View>
  );
}

function CotField({
  testID,
  label,
  value,
  onChange,
  onBlur,
  error,
}: {
  testID?: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
  onBlur?: () => void;
  error?: boolean;
}) {
  return (
    <View style={{ marginTop: 14 }}>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        testID={testID}
        value={value}
        onChangeText={onChange}
        onBlur={onBlur}
        keyboardType="decimal-pad"
        placeholder="0"
        placeholderTextColor={colors.placeholder}
        style={[styles.input, error && styles.inputError]}
      />
      {error && (
        <Text style={styles.errorMsg} testID={testID ? `${testID}-error` : undefined}>
          ⚠ Cote obligatoire manquante
        </Text>
      )}
    </View>
  );
}

function DiagonalField({
  testID,
  label,
  value,
  state,
  onChange,
  onValidate,
  onModify,
  error,
}: {
  testID?: string;
  label: string;
  value: string;
  state: DiagState;
  onChange: (v: string) => void;
  onValidate: () => void;
  onModify: () => void;
  error?: boolean;
}) {
  const isAuto = state === "auto";
  const isValidated = state === "validated";
  return (
    <View style={{ marginTop: 14 }}>
      <View
        style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}
      >
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
        <TextInput
          testID={testID}
          value={value}
          onChangeText={onChange}
          keyboardType="decimal-pad"
          placeholder="0"
          placeholderTextColor={colors.placeholder}
          editable={!isAuto}
          style={[
            styles.input,
            { flex: 1 },
            error && styles.inputError,
            isAuto && { borderColor: colors.primary, color: colors.primary },
            isValidated && { borderColor: colors.success, color: colors.success },
          ]}
        />
        {isAuto && (
          <>
            <TouchableOpacity
              testID={`${testID}-validate`}
              onPress={onValidate}
              activeOpacity={0.8}
              style={[styles.diagBtn, { backgroundColor: colors.success }]}
            >
              <Ionicons name="checkmark" size={18} color="#000" />
            </TouchableOpacity>
            <TouchableOpacity
              testID={`${testID}-modify`}
              onPress={onModify}
              activeOpacity={0.8}
              style={[styles.diagBtn, { backgroundColor: colors.warning }]}
            >
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
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 10,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSubtle,
  },
  stepRow: { flexDirection: "row", gap: 8 },
  stepPill: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: colors.surfaceElevated,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
    borderColor: colors.borderSubtle,
  },
  stepPillActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  stepPillText: { color: colors.textSecondary, fontWeight: "800", fontSize: 12 },
  reportBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
    backgroundColor: "#2a1010",
    borderWidth: 1,
    borderColor: colors.anomaly,
  },
  reportBtnText: { color: colors.anomaly, fontSize: 11, fontWeight: "700" },

  h1: { color: colors.textPrimary, fontSize: 18, fontWeight: "800", letterSpacing: 0.5 },
  h2: { color: colors.textSecondary, fontSize: 12, marginTop: 2 },
  sectionLabel: {
    color: colors.textSecondary,
    fontSize: 11,
    fontWeight: "900",
    letterSpacing: 0.8,
    marginBottom: 8,
  },
  errInline: { color: colors.anomaly, fontWeight: "900" },
  helperText: { color: colors.placeholder, fontSize: 12, marginBottom: 8 },
  label: {
    color: colors.textSecondary,
    fontSize: 11,
    fontWeight: "700",
    letterSpacing: 0.6,
    marginBottom: 6,
  },
  input: {
    backgroundColor: colors.inputBg,
    color: colors.textPrimary,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.borderStrong,
    paddingHorizontal: 12,
    paddingVertical: Platform.OS === "ios" ? 14 : 10,
    fontSize: 16,
    minHeight: 48,
  },
  inputError: { borderColor: colors.anomaly, backgroundColor: "#1a0808" },
  errorMsg: {
    color: colors.anomaly,
    fontSize: 11,
    fontWeight: "800",
    marginTop: 4,
    letterSpacing: 0.4,
  },
  indicSuffix: {
    color: colors.textSecondary,
    fontSize: 10,
    fontWeight: "700",
    letterSpacing: 0.5,
  },
  wallIndic: {
    color: colors.placeholder,
    fontSize: 9,
    fontWeight: "700",
    marginTop: 3,
    letterSpacing: 0.6,
  },
  row2: { flexDirection: "row", gap: 10 },

  // Étape 1 — Segmented buttons
  segBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    backgroundColor: colors.surface,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    paddingVertical: 12,
    paddingHorizontal: 8,
    minHeight: 48,
  },
  segBtnActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  segBtnText: {
    color: colors.textSecondary,
    fontWeight: "800",
    fontSize: 12,
    letterSpacing: 0.4,
    textAlign: "center",
    flexShrink: 1,
  },

  // Étape 1 — Façades grid
  facadeGrid: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  facadeCard: {
    width: "47%",
    backgroundColor: colors.surface,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    paddingVertical: 14,
    paddingHorizontal: 10,
    alignItems: "center",
    gap: 6,
  },
  facadeCardActive: { borderColor: colors.primary, backgroundColor: "#1a0e05" },
  facadeLabel: {
    color: colors.textPrimary,
    fontWeight: "800",
    fontSize: 12,
    textAlign: "center",
    letterSpacing: 0.3,
  },

  // Étape 1 — hint box
  inlineHintBox: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    marginTop: 8,
    padding: 10,
    borderRadius: 8,
    backgroundColor: "#2a1c08",
    borderWidth: 1,
    borderColor: colors.warning,
  },
  inlineHintText: { color: colors.textSecondary, fontSize: 11, flex: 1, lineHeight: 15 },

  // Étape 1 — Checkbox rows
  checkboxRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    paddingVertical: 12,
    paddingHorizontal: 14,
    borderRadius: 10,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    marginTop: 8,
  },
  checkboxLabel: { color: colors.textPrimary, fontSize: 14, fontWeight: "700" },
  checkboxSub: { color: colors.textSecondary, fontSize: 11, marginTop: 2 },

  // Étape 2 — Shape cards
  shapeCard: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    backgroundColor: colors.surface,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    padding: 14,
    minHeight: 84,
  },
  shapeCardActive: { borderColor: colors.primary, backgroundColor: "#1a0e05" },
  shapeLetterBadge: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
  },
  shapeLetter: { color: "#000", fontWeight: "900", fontSize: 12 },
  shapeIconBox: { width: 36, alignItems: "center" },
  shapeTitle: { color: colors.textPrimary, fontWeight: "900", fontSize: 14, letterSpacing: 0.4 },
  shapeDesc: { color: colors.textSecondary, fontSize: 11, marginTop: 2, lineHeight: 15 },

  // Étape 3 — Opening subtypes
  openingGrid: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  openingCard: {
    width: "47%",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    backgroundColor: colors.surface,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    paddingVertical: 12,
  },
  openingCardActive: { borderColor: colors.primary, backgroundColor: "#1a0e05" },
  openingLabel: { color: colors.textPrimary, fontWeight: "800", fontSize: 12 },

  // Étape 3 — Mode toggle
  modeToggle: {
    flexDirection: "row",
    gap: 6,
    marginTop: 14,
    padding: 4,
    backgroundColor: colors.surface,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
  },
  modeTab: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    paddingVertical: 10,
    borderRadius: 8,
  },
  modeTabActive: { backgroundColor: colors.primary },
  modeTabText: {
    color: colors.textSecondary,
    fontSize: 11,
    fontWeight: "900",
    letterSpacing: 0.6,
  },
  modeTabTextActive: { color: "#000" },

  alertBox: {
    flexDirection: "row",
    alignItems: "flex-start",
    marginTop: 14,
    padding: 12,
    borderRadius: 10,
    backgroundColor: "#2a1c08",
    borderWidth: 1,
    borderColor: colors.warning,
  },
  alertTitle: { color: colors.warning, fontWeight: "900", fontSize: 13 },
  alertSub: { color: colors.textSecondary, fontSize: 11, marginTop: 2 },

  sketchBox: {
    marginTop: 16,
    alignItems: "center",
    backgroundColor: colors.surface,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    paddingVertical: 12,
  },

  autoBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    backgroundColor: colors.primary,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
  },
  validBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    backgroundColor: colors.success,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
  },
  autoBadgeText: { color: "#000", fontSize: 10, fontWeight: "900", letterSpacing: 0.5 },
  diagBtn: {
    width: 48,
    height: 48,
    borderRadius: 10,
    alignItems: "center",
    justifyContent: "center",
  },
  computeBtn: {
    marginTop: 12,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    paddingVertical: 12,
    paddingHorizontal: 14,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.primary,
    backgroundColor: "#1a0e05",
  },
  computeBtnText: { color: colors.primary, fontWeight: "900", fontSize: 13, letterSpacing: 0.8 },

  photo: { width: "100%", height: 180, borderRadius: 12, marginTop: 8 },
  removePhoto: {
    position: "absolute",
    top: 16,
    right: 8,
    backgroundColor: "rgba(0,0,0,0.7)",
    padding: 6,
    borderRadius: 14,
  },
  photoRow: { flexDirection: "row", gap: 8, marginTop: 8 },
  photoBtn: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    paddingVertical: 14,
    borderRadius: 10,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
  },
  photoBtnText: { color: colors.primary, fontWeight: "700", fontSize: 13 },

  wallGrid: { flexDirection: "row", flexWrap: "wrap", gap: 10, marginTop: 6 },
  wallCard: {
    width: "47%",
    backgroundColor: colors.surface,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    padding: 12,
    alignItems: "center",
  },
  wallCardActive: { borderColor: colors.primary, backgroundColor: "#1a0e05" },
  wallCardError: { borderColor: colors.anomaly },
  wallLabel: {
    color: colors.textPrimary,
    fontWeight: "900",
    fontSize: 14,
    marginTop: 6,
    letterSpacing: 0.8,
  },
  wallSub: { color: colors.textSecondary, fontSize: 10, marginTop: 2, textAlign: "center" },

  footer: {
    flexDirection: "row",
    gap: 10,
    padding: 16,
    borderTopWidth: 1,
    borderTopColor: colors.borderSubtle,
    backgroundColor: colors.bg,
  },
  btn: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    minHeight: 52,
    borderRadius: 12,
    paddingHorizontal: 16,
  },
  btnPrimary: { backgroundColor: colors.primary },
  btnPrimaryText: { color: "#000", fontWeight: "900", fontSize: 14, letterSpacing: 0.8 },
  btnSecondary: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
  },
  btnSecondaryText: {
    color: colors.textPrimary,
    fontWeight: "800",
    fontSize: 13,
    letterSpacing: 0.5,
  },

  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.7)",
    justifyContent: "center",
    padding: 20,
  },
  modalCard: {
    backgroundColor: colors.surface,
    borderRadius: 16,
    padding: 18,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
  },
  modalTitle: { color: colors.textPrimary, fontWeight: "800", fontSize: 16 },
  modalSub: { color: colors.textSecondary, fontSize: 12, marginTop: 4, marginBottom: 12 },
  reportInput: {
    backgroundColor: colors.inputBg,
    color: colors.textPrimary,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.borderStrong,
    padding: 12,
    minHeight: 100,
    textAlignVertical: "top",
    fontSize: 14,
  },
});
