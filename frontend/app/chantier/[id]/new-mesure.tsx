/**
 * ╔══════════════════════════════════════════════════════════════════════╗
 * ║  MesureChâssis — Wizard "Nouvelle Ouverture" — V3 PRODUCTION         ║
 * ╠══════════════════════════════════════════════════════════════════════╣
 * ║  Architecture en 3 étapes :                                          ║
 * ║   1. Configuration mur (Maçonnerie + Isolation/Finition dynamique)   ║
 * ║   2. Sélection de la forme (14 formes — sans sous-type ouvrant)      ║
 * ║   3. Cotes adaptatives + feuillures conditionnelles + trait 1m calc  ║
 * ║                                                                      ║
 * ║  Tous les nouveaux champs (masonry_type, gros_oeuvre_mm, insul_mode, ║
 * ║  parement_*, feuillure_*, shape…) sont stockés dans payload.options{}║
 * ║  → rétro-compatibilité 100% du backend. `block_type` mappé proprement║
 * ║  vers les 4 valeurs historiques pour les exports PDF/CSV/XLSX/JSON.  ║
 * ║                                                                      ║
 * ║  🆕 V3 (juin 2026) — Refactorisation modulaire :                      ║
 * ║   • Types/constantes/helpers → /src/components/wizard/types.ts        ║
 * ║   • Styles partagés          → /src/components/wizard/wizardStyles.ts ║
 * ║   • Primitives UI            → /src/components/wizard/primitives.tsx  ║
 * ║   • Étape 1/3                → /src/components/wizard/Step1Config.tsx ║
 * ║   • Étape 2/3                → /src/components/wizard/Step2Shape.tsx  ║
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
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import * as ImagePicker from "expo-image-picker";
import { useLocalSearchParams, useRouter } from "expo-router";
import { api } from "@/src/services/api";
import { enqueueMesure, isOnline } from "@/src/services/offlineQueue";
import { colors } from "@/src/theme";
import {
  arcLengthPleinCintre,
  arcLengthArcSurbaisse,
} from "@/src/utils/perimeter";
import { useResponsive } from "@/src/utils/responsive";
// 🆕 V3 — Composants refactorisés (séparés du fichier monolithique)
import { wizardStyles as styles } from "@/src/components/wizard/wizardStyles";
import CafeJetonModal, { CafeJeton } from "@/src/components/CafeJetonModal";
import { Step1Config } from "@/src/components/wizard/Step1Config";
import { Step2Shape } from "@/src/components/wizard/Step2Shape";
import { Step3Cotes } from "@/src/components/wizard/Step3Cotes";
import {
  initStep1,
  initStep3,
  inferShape,
  masonryHasFeuillures,
  parseNum,
  shapeToBlockType,
  Shape,
  Step1Data,
  Step3Data,
  MasonryType,
} from "@/src/components/wizard/types";


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
  // ☕ Priorité 4 — Jeton café gagné après création d'une ouverture
  // (uniquement pour les comptes issus d'un QR code station partenaire).
  const [cafeJeton, setCafeJeton] = useState<CafeJeton | null>(null);
  const [cafeStationName, setCafeStationName] = useState("");
  // Loading initial : édition OU chargement de la wall_config du chantier
  const [loadingInit, setLoadingInit] = useState(true);
  // 🏗️ Si le chantier a déjà une wall_config → on saute l'étape 1
  //    (configuration mur déjà faite une fois pour tout le chantier).
  const [wallConfigLocked, setWallConfigLocked] = useState(false);

  // 🆕 Import CDC — Mode "validation d'une mesure importée par IA".
  //   Si la mesure courante a `options.imported_from_spec === true` ET
  //   n'est pas encore validée sur place (`options.validated_on_site !== true`),
  //   on affiche un bandeau orange et on change le bouton "ENREGISTRER" → "VALIDER".
  const [isImportedMode, setIsImportedMode] = useState(false);
  // Preserve les options "non gérées par le wizard" (ex: imported_from_spec,
  // theoretical_*, spec_notes) pour les ré-injecter au submit (merge).
  const [importedOptionsBackup, setImportedOptionsBackup] = useState<Record<string, any> | null>(null);

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
          setLoadingInit(false);
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
            // 🆕 Import CDC — Détection mode "validation d'une mesure IA"
            const importedNotYetValidated =
              !!opts.imported_from_spec && !opts.validated_on_site;
            setIsImportedMode(importedNotYetValidated);
            // 💾 Backup des options spécifiques IA pour les ré-injecter au submit
            //    (sinon elles seraient perdues car le wizard reconstruit `opts` from scratch)
            setImportedOptionsBackup({
              imported_from_spec: !!opts.imported_from_spec,
              spec_notes: opts.spec_notes || "",
              theoretical_width_mm: opts.theoretical_width_mm ?? null,
              theoretical_height_mm: opts.theoretical_height_mm ?? null,
              spec_draft_id: opts.spec_draft_id || null,
            });
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
              perimeter_measured: toStr(opts.arc_measured_mm || opts.perimeter_measured_mm),
              polygon_edge_count: (["3", "5", "6", "8"].includes(String(opts.polygon_edge_count))
                ? String(opts.polygon_edge_count)
                : "6") as "3" | "5" | "6" | "8",
              polygon_edge_length: toStr(opts.polygon_edge_length_mm),
              polygon_angle_deg: toStr(opts.polygon_angle_deg) || "120",
              polygon_bbox_width: toStr(opts.polygon_bbox_width_mm || (m.shape === "polygone" ? m.bay_width : null)),
              polygon_bbox_height: toStr(opts.polygon_bbox_height_mm || (m.shape === "polygone" ? m.bay_height : null)),
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

  // 🆕 V3 — Longueur de l'arc calculée pour les formes arc. Réagit en
  //    temps réel aux changements de cotes, permet au mesureur de
  //    vérifier sa mesure ruban contre la valeur géométrique.
  //    NOTE : on ne calcule PLUS de périmètre total pour angle_90
  //    (cahier des charges 09/06/2026).
  const computedPerimeter = useMemo(() => {
    if (shape === "plein_cintre") {
      return arcLengthPleinCintre(parseNum(s3.bay_width));
    }
    if (shape === "arc_surbaisse") {
      return arcLengthArcSurbaisse(
        parseNum(s3.bay_width),
        parseNum(s3.arch_h1_appui),
        parseNum(s3.arch_h2_total),
      );
    }
    return null;
  }, [
    shape,
    s3.bay_width,
    s3.arch_h1_appui,
    s3.arch_h2_total,
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
      // 🆕 V3 — Bow-Window : module en cours de fabrication.
      //    On bloque la sauvegarde tant que le module n'est pas livré
      //    (cahier des charges 10/06/2026).
      err.bay_width = true;
      Alert.alert(
        "Bow-Window — Module en cours de fabrication",
        "Cette forme n'est pas encore disponible. Merci d'envoyer un feedback via les boutons dédiés ou de choisir une autre forme.",
      );
    } else if (shape === "bow_window_OLD") {
      // 🚧 Bloc de validation legacy (désactivé — voir bow_window ci-dessus).
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
    } else if (shape === "polygone") {
      // 🆕 V3 — Polygone : 4 cotes obligatoires
      if (!parseNum(s3.polygon_edge_length)) err.polygon_edge_length = true;
      if (!parseNum(s3.polygon_angle_deg)) err.polygon_angle_deg = true;
      if (!parseNum(s3.polygon_bbox_width)) err.polygon_bbox_width = true;
      if (!parseNum(s3.polygon_bbox_height)) err.polygon_bbox_height = true;
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
    // 🆕 V3 — Longueur de l'arc (calculée + mesurée au ruban) pour
    //    vérification technique sur les formes arc UNIQUEMENT.
    //    L'angle_90 n'a plus de vérification périmètre (cahier des
    //    charges 09/06/2026).
    if (shape === "plein_cintre" || shape === "arc_surbaisse") {
      const measured = parseNum(s3.perimeter_measured);
      if (measured !== null) opts.arc_measured_mm = measured;
      if (computedPerimeter !== null) {
        opts.arc_computed_mm = computedPerimeter;
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
    // 🆕 V3 — Polygone unifié
    if (shape === "polygone") {
      opts.polygon_edge_count = parseInt(s3.polygon_edge_count, 10);
      opts.polygon_edge_length_mm = parseNum(s3.polygon_edge_length);
      opts.polygon_angle_deg = parseNum(s3.polygon_angle_deg);
      opts.polygon_bbox_width_mm = parseNum(s3.polygon_bbox_width);
      opts.polygon_bbox_height_mm = parseNum(s3.polygon_bbox_height);
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

    // 🆕 Import CDC — Si on est en mode "validation d'une mesure IA",
    //   on marque la mesure comme validée sur place ET on ré-injecte les
    //   métadonnées IA backupées au chargement (sinon elles seraient perdues).
    if (isImportedMode && importedOptionsBackup) {
      (payload.options as Record<string, any>).imported_from_spec = true;
      (payload.options as Record<string, any>).spec_notes = importedOptionsBackup.spec_notes || "";
      (payload.options as Record<string, any>).theoretical_width_mm = importedOptionsBackup.theoretical_width_mm;
      (payload.options as Record<string, any>).theoretical_height_mm = importedOptionsBackup.theoretical_height_mm;
      (payload.options as Record<string, any>).spec_draft_id = importedOptionsBackup.spec_draft_id;
      // 🚦 Marquage de la validation sur place (passage du badge orange "À valider" au cercle vert "V")
      (payload.options as Record<string, any>).validated_on_site = true;
      (payload.options as Record<string, any>).validated_at = new Date().toISOString();
    } else if (importedOptionsBackup) {
      // Cas : mesure déjà validée précédemment — on conserve l'historique
      (payload.options as Record<string, any>).imported_from_spec = importedOptionsBackup.imported_from_spec;
      (payload.options as Record<string, any>).spec_notes = importedOptionsBackup.spec_notes || "";
      (payload.options as Record<string, any>).theoretical_width_mm = importedOptionsBackup.theoretical_width_mm;
      (payload.options as Record<string, any>).theoretical_height_mm = importedOptionsBackup.theoretical_height_mm;
      (payload.options as Record<string, any>).validated_on_site = true;
    }

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
    } else if (shape === "polygone") {
      // 🆕 V3 — Polygone : on mappe les hors-tout (bbox) sur bay_width / bay_height
      payload.bay_width = parseNum(s3.polygon_bbox_width);
      payload.bay_height = parseNum(s3.polygon_bbox_height);
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
      if (editingId) {
        await api.patch(`/mesures/${editingId}`, payload);
      } else {
        const created = await api.post("/mesures", payload);
        // ☕ Priorité 4 — Tentative de gain d'un jeton café (silencieux).
        // Ne bloque JAMAIS l'enregistrement : en cas d'échec réseau ou de
        // compte non tagué campagne, on ferme simplement le wizard.
        try {
          const r = await api.post("/cafe/earn", {
            mesure_id: created.data?.id,
          });
          if (r.data?.eligible && r.data?.jeton) {
            setCafeJeton(r.data.jeton);
            setCafeStationName(r.data.station?.name || "");
            return; // router.back() différé à la fermeture de la pop-up ☕
          }
        } catch {
          /* silencieux — pas de jeton, flux normal */
        }
      }
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

        {/* 🆕 Import CDC — Bandeau orange "À VALIDER" quand mesure issue d'un cahier des charges IA */}
        {isImportedMode && (
          <View style={importBannerStyles.banner}>
            <Ionicons name="sparkles" size={18} color="#FF9F0A" />
            <View style={{ flex: 1 }}>
              <Text style={importBannerStyles.title}>
                Mesure issue du cahier des charges
              </Text>
              <Text style={importBannerStyles.subtitle}>
                {importedOptionsBackup?.theoretical_width_mm && importedOptionsBackup?.theoretical_height_mm
                  ? `Cotes théoriques : ${importedOptionsBackup.theoretical_width_mm} × ${importedOptionsBackup.theoretical_height_mm} mm. Vérifiez et ajustez sur place, puis Validez.`
                  : "Vérifiez les cotes théoriques pré-remplies, ajustez si besoin, puis Validez."}
              </Text>
            </View>
          </View>
        )}

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
              style={[
                styles.btn,
                isImportedMode ? importBannerStyles.btnValidate : styles.btnPrimary,
              ]}
              activeOpacity={0.85}
            >
              {saving ? (
                <ActivityIndicator color={isImportedMode ? "#fff" : "#000"} />
              ) : (
                <>
                  <Ionicons
                    name="checkmark-circle"
                    size={22}
                    color={isImportedMode ? "#fff" : "#000"}
                  />
                  <Text
                    style={[
                      styles.btnPrimaryText,
                      isImportedMode && { color: "#fff" },
                    ]}
                  >
                    {isImportedMode ? "VALIDER" : "ENREGISTRER"}
                  </Text>
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
              Décrivez ce qui ne va pas — envoyé à l&apos;admin avec le contexte.
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

      {/* ☕ Priorité 4 — Pop-up « Vous avez gagné un café ! » */}
      <CafeJetonModal
        visible={!!cafeJeton}
        jeton={cafeJeton}
        stationName={cafeStationName}
        onClose={() => {
          setCafeJeton(null);
          router.back();
        }}
      />
    </SafeAreaView>
  );
}

// 🆕 Import CDC — Styles locaux pour le bandeau "À VALIDER" et le bouton "VALIDER" vert
const importBannerStyles = StyleSheet.create({
  banner: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 10,
    backgroundColor: "#FF9F0A15",
    borderColor: "#FF9F0A66",
    borderWidth: 1,
    paddingHorizontal: 14,
    paddingVertical: 10,
    marginHorizontal: 14,
    marginTop: 10,
    borderRadius: 10,
  },
  title: {
    color: "#FF9F0A",
    fontWeight: "900",
    fontSize: 13,
    letterSpacing: 0.4,
  },
  subtitle: {
    color: "#FFCC7A",
    fontSize: 12,
    lineHeight: 16,
    marginTop: 2,
  },
  // Bouton VALIDER vert plein
  btnValidate: {
    backgroundColor: "#10B981",
  },
});
