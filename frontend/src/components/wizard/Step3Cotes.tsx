/**
 * Step3Cotes — Wizard Étape 3/3 : cotes adaptatives & intelligentes.
 * Extrait de /app/frontend/app/chantier/[id]/new-mesure.tsx (refacto V3 Phase 2 — juin 2026).
 * 🌍 i18n complet — toutes les chaînes utilisateur passent par `useTranslation` (clés `wizard.step3.*`).
 *
 * NB : ce composant est volumineux (~750 lignes) car il gère la saisie de
 *      cotes pour les 14 formes (rect, porte, trapeze, triangle, œil-de-bœuf,
 *      coulissant_levant, plein_cintre, arc_surbaisse, angle_90, bow_window,
 *      pentagone, hexagone, ovale, polygone). Un découpage par sous-forme est
 *      possible dans une Phase 3, mais nécessiterait un Context pour partager
 *      `s3/setField/err` sans passer des props à chaque sous-composant.
 */
import React from "react";
import { Image, Text, TextInput, TouchableOpacity, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import { useTranslation } from "react-i18next";
import { colors } from "@/src/theme";
import { MeasureGuide } from "@/src/components/MeasureGuide";
import ShapeSchemaV2 from "@/src/components/ShapeSchemaV2";
import ArcLengthVerification from "@/src/components/PerimeterVerification";
import { wizardStyles as styles } from "./wizardStyles";
import { CheckboxRow, CotField, DiagonalField } from "./primitives";
import {
  masonryHasFeuillures,
  parseNum,
  MasonryType,
  Shape,
  SHAPES,
  Step3Data,
} from "./types";

export function Step3Cotes({
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
  const { t } = useTranslation();
  const isRectFamily =
    shape === "rect" ||
    shape === "porte_entree" ||
    shape === "porte_garage" ||
    shape === "coulissant_levant";
  const show1mLevel = shape === "porte_entree" || shape === "coulissant_levant";
  // Feuillures : logique conditionnelle selon la config du mur.
  // 🆕 (juin 2026) — Si wall_config OPTIONNELLE (option 1.B utilisateur) :
  //   • Cas A : masonry_type renseigné → comportement historique
  //     (dépend de masonryHasFeuillures + has_horizontal_cut).
  //   • Cas B : masonry_type == null (mur non renseigné) → on affiche
  //     TOUJOURS les feuillures en champs optionnels — l'utilisateur peut
  //     les saisir ou laisser vide.
  // 🚪 Sur porte de garage / coulissant levant / bow-window, on masque
  //   les feuillures (pas de sens métier).
  const router = useRouter();
  const wallConfigMissing = !s1MasonryType;
  const showFeuillures =
    (wallConfigMissing || (masonryHasFeuillures(s1MasonryType) && !!s1HasHorizontalCut)) &&
    shape !== "porte_garage" &&
    shape !== "coulissant_levant" &&
    shape !== "bow_window";

  const validateDiag = (which: 1 | 2) =>
    setField(which === 1 ? "diag_1_state" : "diag_2_state", "validated");
  const modifyDiag = (which: 1 | 2) => {
    setField(which === 1 ? "diag_1" : "diag_2", "");
    setField(which === 1 ? "diag_1_state" : "diag_2_state", "manual");
  };

  // Label traduit de la forme courante (pour le sous-titre).
  const shapeMeta = SHAPES.find((s) => s.key === shape);
  const shapeLabel = t(`wizard.shapes.${shape}.label`, {
    defaultValue: shapeMeta?.label || shape,
  });

  return (
    <View>
      <Text style={styles.h1}>{t("wizard.step3.title")}</Text>
      <Text style={styles.h2}>
        {t("wizard.step3.subtitle", { shape: shapeLabel })}
      </Text>

      {/* 📐 Guide visuel — montre où prendre les cotes */}
      <MeasureGuide shape={shape} />
      <Text style={styles.guideHint}>{t("wizard.step3.guideHint")}</Text>

      <View ref={labelRef} style={{ marginTop: 14 }}>
        <Text style={[styles.label, labelError && { color: colors.anomaly }]}>
          {t("wizard.step3.labelField")} {labelError && <Text style={styles.errInline}> {t("wizard.step3.labelFieldError")}</Text>}
        </Text>
        <TextInput
          testID="mesure-label-input"
          value={label}
          onChangeText={setLabel}
          placeholder={t("wizard.step3.labelFieldPlaceholder")}
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
          <Text style={styles.errorMsg}>{t("wizard.step3.labelFieldHint")}</Text>
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
              {t("wizard.step3.modeStandard")}
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
              {t("wizard.step3.modeRenovation")}
            </Text>
          </TouchableOpacity>
        </View>
      )}

      {/* Cotes — Trapèze */}
      {shape === "trapeze" && (
        <>
          <CotField testID="input-bay-width" label={t("wizard.step3.width")} value={s3.bay_width}
            onChange={(v) => setField("bay_width", v.replace(",", "."))} error={!!err.bay_width} />
          <CotField testID="input-trap-height-left" label={t("wizard.step3.leftHeight")} value={s3.trap_height_left}
            onChange={(v) => setField("trap_height_left", v.replace(",", "."))} error={!!err.trap_height_left} />
          <CotField testID="input-trap-height-right" label={t("wizard.step3.rightHeight")} value={s3.trap_height_right}
            onChange={(v) => setField("trap_height_right", v.replace(",", "."))} error={!!err.trap_height_right} />
        </>
      )}

      {/* Triangle */}
      {shape === "triangle" && (
        <>
          <CotField testID="input-triangle-base" label={t("wizard.step3.base")} value={s3.triangle_base}
            onChange={(v) => setField("triangle_base", v.replace(",", "."))} error={!!err.triangle_base} />
          <CotField testID="input-triangle-height" label={t("wizard.step3.height")} value={s3.triangle_height}
            onChange={(v) => setField("triangle_height", v.replace(",", "."))} error={!!err.triangle_height} />
        </>
      )}

      {/* Œil-de-bœuf */}
      {shape === "oeil_de_boeuf" && (
        <CotField testID="input-oeil-diameter" label={t("wizard.step3.diameter")} value={s3.oeil_diameter}
          onChange={(v) => setField("oeil_diameter", v.replace(",", "."))} error={!!err.oeil_diameter} />
      )}

      {/* Plein cintre */}
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
          <Text style={styles.helperText}>{t("wizard.step3.helpPleinCintre")}</Text>
          <CotField testID="input-bay-width" label={t("wizard.step3.widthL")} value={s3.bay_width}
            onChange={(v) => setField("bay_width", v.replace(",", "."))} error={!!err.bay_width} />
          <CotField testID="input-arch-h1" label={t("wizard.step3.archH1")} value={s3.arch_h1_appui}
            onChange={(v) => setField("arch_h1_appui", v.replace(",", "."))} error={!!err.arch_h1_appui} />
          <CotField testID="input-arch-h2" label={t("wizard.step3.archH2")} value={s3.arch_h2_total}
            onChange={(v) => setField("arch_h2_total", v.replace(",", "."))} error={!!err.arch_h2_total} />
          <Text style={styles.helperText}>{t("wizard.step3.rulePleinCintre")}</Text>
          <ArcLengthVerification
            testID="input-perimeter-plein-cintre"
            computed={computedPerimeter}
            measuredValue={s3.perimeter_measured}
            onChangeMeasured={(v) => setField("perimeter_measured", v.replace(",", "."))}
          />
        </>
      )}

      {/* Arc surbaissé */}
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
          <Text style={styles.helperText}>{t("wizard.step3.helpArcSurbaisse")}</Text>
          <CotField testID="input-bay-width" label={t("wizard.step3.widthL")} value={s3.bay_width}
            onChange={(v) => setField("bay_width", v.replace(",", "."))} error={!!err.bay_width} />
          <CotField testID="input-arch-h1" label={t("wizard.step3.archH1")} value={s3.arch_h1_appui}
            onChange={(v) => setField("arch_h1_appui", v.replace(",", "."))} error={!!err.arch_h1_appui} />
          <CotField testID="input-arch-h2" label={t("wizard.step3.archH2")} value={s3.arch_h2_total}
            onChange={(v) => setField("arch_h2_total", v.replace(",", "."))} error={!!err.arch_h2_total} />
          <Text style={styles.helperText}>{t("wizard.step3.ruleArcSurbaisse")}</Text>
          <ArcLengthVerification
            testID="input-perimeter-arc-surbaisse"
            computed={computedPerimeter}
            measuredValue={s3.perimeter_measured}
            onChangeMeasured={(v) => setField("perimeter_measured", v.replace(",", "."))}
          />
        </>
      )}

      {/* Angle 90° (pan coupé gauche / droite / les deux) */}
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
          <Text style={styles.helperText}>{t("wizard.step3.helpAngle90")}</Text>

          {/* Sélecteur du côté coupé */}
          <Text style={[styles.sectionLabel, { marginTop: 12 }]}>{t("wizard.step3.cutSide")}</Text>
          <View style={[styles.row2, { marginBottom: 10 }]}>
            {(["left", "right", "both"] as const).map((sd) => {
              const active = s3.angle90_side === sd;
              const sideLabel =
                sd === "left" ? t("wizard.step3.cutSideLeft")
                  : sd === "right" ? t("wizard.step3.cutSideRight")
                  : t("wizard.step3.cutSideBoth");
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
                    {sideLabel}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </View>

          <CotField testID="input-bay-width" label={t("wizard.step3.totalWidthL")} value={s3.bay_width}
            onChange={(v) => setField("bay_width", v.replace(",", "."))} error={!!err.bay_width} />

          <View style={styles.row2}>
            <View style={{ flex: 1 }}>
              <CotField testID="input-angle90-h-left" label={t("wizard.step3.leftHeightHg")} value={s3.angle90_h_left}
                onChange={(v) => setField("angle90_h_left", v.replace(",", "."))} error={!!err.angle90_h_left} />
            </View>
            <View style={{ flex: 1 }}>
              <CotField testID="input-angle90-h-right" label={t("wizard.step3.rightHeightHd")} value={s3.angle90_h_right}
                onChange={(v) => setField("angle90_h_right", v.replace(",", "."))} error={!!err.angle90_h_right} />
            </View>
          </View>

          <Text style={[styles.sectionLabel, { marginTop: 12 }]}>{t("wizard.step3.cutSection")}</Text>
          <View style={styles.row2}>
            <View style={{ flex: 1 }}>
              <CotField testID="input-angle90-cut-w" label={t("wizard.step3.cutWidth")} value={s3.angle90_cut_width}
                onChange={(v) => setField("angle90_cut_width", v.replace(",", "."))} error={!!err.angle90_cut_width} />
            </View>
            <View style={{ flex: 1 }}>
              <CotField testID="input-angle90-cut-h" label={t("wizard.step3.cutHeight")} value={s3.angle90_cut_height}
                onChange={(v) => setField("angle90_cut_height", v.replace(",", "."))} error={!!err.angle90_cut_height} />
            </View>
          </View>
          <CotField testID="input-angle90-angle" label={t("wizard.step3.cutAngle")} value={s3.angle90_angle_deg}
            onChange={(v) => setField("angle90_angle_deg", v.replace(",", "."))} />
          <Text style={styles.helperText}>{t("wizard.step3.ruleAngle90")}</Text>
        </>
      )}

      {/* Bow-Window : module en cours de fabrication */}
      {shape === "bow_window" && (
        <>
          <View style={[styles.inlineHintBox, { marginTop: 8, backgroundColor: "rgba(255,165,0,0.10)", borderColor: "rgba(255,165,0,0.45)", flexDirection: "column", alignItems: "flex-start" }]}>
            <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
              <Ionicons name="construct" size={18} color={colors.warning} />
              <Text style={[styles.inlineHintText, { color: colors.warning, fontWeight: "800", flex: 1 }]}>
                {t("wizard.step3.bowInProgress")}
              </Text>
            </View>
            <Text style={[styles.inlineHintText, { color: colors.textPrimary, marginTop: 8, lineHeight: 18 }]}>
              {t("wizard.step3.bowFeedbackText")}
            </Text>
          </View>
          <TouchableOpacity
            testID="bow-expertise-admin-button"
            onPress={() => router.push("/feedback?to=admin&topic=bow_window")}
            activeOpacity={0.85}
            style={[styles.btn, styles.btnPrimary, { marginTop: 14, marginBottom: 6 }]}
          >
            <Ionicons name="paper-plane" size={18} color="#000" />
            <Text style={styles.btnPrimaryText}>{t("wizard.step3.bowSendButton")}</Text>
          </TouchableOpacity>
          <Text style={[styles.helperText, { fontSize: 11, opacity: 0.55, marginTop: 6 }]}>
            {t("wizard.step3.bowDisabled")}
          </Text>
        </>
      )}

      {/* Pentagone */}
      {shape === "pentagone" && (
        <>
          <Text style={styles.helperText}>{t("wizard.step3.helpPentagone")}</Text>
          <CotField testID="input-bay-width" label={t("wizard.step3.baseWidth")} value={s3.bay_width}
            onChange={(v) => setField("bay_width", v.replace(",", "."))} error={!!err.bay_width} />
          <CotField testID="input-pent-h1" label={t("wizard.step3.pentSideH")} value={s3.pent_side_height}
            onChange={(v) => setField("pent_side_height", v.replace(",", "."))} error={!!err.pent_side_height} />
          <CotField testID="input-pent-h2" label={t("wizard.step3.pentTopH")} value={s3.pent_top_height}
            onChange={(v) => setField("pent_top_height", v.replace(",", "."))} error={!!err.pent_top_height} />
          <Text style={styles.helperText}>{t("wizard.step3.rulePentagone")}</Text>
        </>
      )}

      {/* Hexagone */}
      {shape === "hexagone" && (
        <>
          <Text style={styles.helperText}>{t("wizard.step3.helpHexagone")}</Text>
          <CotField testID="input-bay-width" label={t("wizard.step3.baseWidth")} value={s3.bay_width}
            onChange={(v) => setField("bay_width", v.replace(",", "."))} error={!!err.bay_width} />
          <CotField testID="input-hex-top-width" label={t("wizard.step3.topWidthHex")} value={s3.hex_top_width}
            onChange={(v) => setField("hex_top_width", v.replace(",", "."))} error={!!err.hex_top_width} />
          <CotField testID="input-bay-height" label={t("wizard.step3.totalHeight")} value={s3.bay_height}
            onChange={(v) => setField("bay_height", v.replace(",", "."))} error={!!err.bay_height} />
          <CotField testID="input-hex-side-h" label={t("wizard.step3.verticalSidesH")} value={s3.hex_side_height}
            onChange={(v) => setField("hex_side_height", v.replace(",", "."))} error={!!err.hex_side_height} />
          <Text style={styles.helperText}>{t("wizard.step3.ruleHexagone")}</Text>
        </>
      )}

      {/* Ovale */}
      {shape === "ovale" && (
        <>
          <ShapeSchemaV2
            shape="ovale"
            values={{
              L: parseNum(s3.bay_width) || undefined,
              H: parseNum(s3.bay_height) || undefined,
            }}
          />
          <Text style={styles.helperText}>{t("wizard.step3.helpOvale")}</Text>
          <CotField testID="input-bay-width" label={t("wizard.step3.totalWidthL")} value={s3.bay_width}
            onChange={(v) => setField("bay_width", v.replace(",", "."))} error={!!err.bay_width} />
          <CotField testID="input-bay-height" label={t("wizard.step3.heightH")} value={s3.bay_height}
            onChange={(v) => setField("bay_height", v.replace(",", "."))} error={!!err.bay_height} />
        </>
      )}

      {/* Polygone unifié (3/5/6/8 arêtes) */}
      {shape === "polygone" && (
        <>
          <ShapeSchemaV2
            shape="polygone"
            values={{
              L: parseNum(s3.polygon_bbox_width) || undefined,
              H: parseNum(s3.polygon_bbox_height) || undefined,
              panels: parseInt(s3.polygon_edge_count, 10) || 6,
            }}
          />
          <Text style={styles.helperText}>{t("wizard.step3.helpPolygone")}</Text>

          <Text style={[styles.sectionLabel, { marginTop: 12 }]}>{t("wizard.step3.polygonEdgeCount")}</Text>
          <View style={[styles.row2, { marginBottom: 10, flexWrap: "wrap" }]}>
            {(["3", "5", "6", "8"] as const).map((n) => {
              const active = s3.polygon_edge_count === n;
              const labelMap: Record<string, string> = {
                "3": t("wizard.step3.polygonTriangle"),
                "5": t("wizard.step3.polygonPentagon"),
                "6": t("wizard.step3.polygonHexagon"),
                "8": t("wizard.step3.polygonOctagon"),
              };
              const defaultAngle: Record<string, string> = {
                "3": "60",
                "5": "108",
                "6": "120",
                "8": "135",
              };
              return (
                <TouchableOpacity
                  key={n}
                  testID={`polygon-edges-${n}`}
                  onPress={() => {
                    setField("polygon_edge_count", n);
                    // Réinitialise l'angle par défaut si l'utilisateur n'a
                    // pas encore édité une valeur (ou s'il avait celle d'un
                    // autre polygone).
                    if (!s3.polygon_angle_deg || Object.values(defaultAngle).includes(s3.polygon_angle_deg)) {
                      setField("polygon_angle_deg", defaultAngle[n]);
                    }
                  }}
                  activeOpacity={0.85}
                  style={[
                    styles.modeTab,
                    { minWidth: "47%", marginBottom: 6 },
                    active && styles.modeTabActive,
                  ]}
                >
                  <Text style={[styles.modeTabText, active && styles.modeTabTextActive]}>
                    {labelMap[n]}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </View>

          <CotField
            testID="input-polygon-edge-length"
            label={t("wizard.step3.polygonEdgeLength")}
            value={s3.polygon_edge_length}
            onChange={(v) => setField("polygon_edge_length", v.replace(",", "."))}
            error={!!err.polygon_edge_length}
          />
          <CotField
            testID="input-polygon-angle"
            label={t("wizard.step3.polygonAngle")}
            value={s3.polygon_angle_deg}
            onChange={(v) => setField("polygon_angle_deg", v.replace(",", "."))}
            error={!!err.polygon_angle_deg}
          />

          <Text style={[styles.sectionLabel, { marginTop: 12 }]}>{t("wizard.step3.polygonBbox")}</Text>
          <View style={styles.row2}>
            <View style={{ flex: 1 }}>
              <CotField
                testID="input-polygon-bbox-width"
                label={t("wizard.step3.polygonWidth")}
                value={s3.polygon_bbox_width}
                onChange={(v) => setField("polygon_bbox_width", v.replace(",", "."))}
                error={!!err.polygon_bbox_width}
              />
            </View>
            <View style={{ flex: 1 }}>
              <CotField
                testID="input-polygon-bbox-height"
                label={t("wizard.step3.polygonHeight")}
                value={s3.polygon_bbox_height}
                onChange={(v) => setField("polygon_bbox_height", v.replace(",", "."))}
                error={!!err.polygon_bbox_height}
              />
            </View>
          </View>
          <Text style={styles.helperText}>{t("wizard.step3.rulePolygone")}</Text>
        </>
      )}

      {/* Porte de garage */}
      {shape === "porte_garage" && (
        <>
          <CotField testID="input-bay-width" label={t("wizard.step3.width")} value={s3.bay_width}
            onChange={(v) => setField("bay_width", v.replace(",", "."))} onBlur={onBlurDimension} error={!!err.bay_width} />
          <CotField testID="input-bay-height" label={t("wizard.step3.height")} value={s3.bay_height}
            onChange={(v) => setField("bay_height", v.replace(",", "."))} onBlur={onBlurDimension} error={!!err.bay_height} />
          <Text style={[styles.sectionLabel, { marginTop: 18 }]}>{t("wizard.step3.garageSection")}</Text>
          <Text style={styles.helperText}>{t("wizard.step3.garageHint")}</Text>
          <CotField testID="input-garage-lintel" label={t("wizard.step3.lintel")} value={s3.garage_lintel}
            onChange={(v) => setField("garage_lintel", v.replace(",", "."))} error={!!err.garage_lintel} />
          <View style={styles.row2}>
            <View style={{ flex: 1 }}>
              <CotField testID="input-garage-ecoincon-left" label={t("wizard.step3.ecoinconLeft")} value={s3.garage_ecoincon_left}
                onChange={(v) => setField("garage_ecoincon_left", v.replace(",", "."))} error={!!err.garage_ecoincon_left} />
            </View>
            <View style={{ flex: 1 }}>
              <CotField testID="input-garage-ecoincon-right" label={t("wizard.step3.ecoinconRight")} value={s3.garage_ecoincon_right}
                onChange={(v) => setField("garage_ecoincon_right", v.replace(",", "."))} error={!!err.garage_ecoincon_right} />
            </View>
          </View>
        </>
      )}

      {/* Rect family standard */}
      {isRectFamily && shape !== "porte_garage" && !s3.renovation_mode && (
        <>
          <CotField testID="input-bay-width" label={t("wizard.step3.width")} value={s3.bay_width}
            onChange={(v) => setField("bay_width", v.replace(",", "."))} onBlur={onBlurDimension} error={!!err.bay_width} />
          <CotField testID="input-bay-height" label={t("wizard.step3.height")} value={s3.bay_height}
            onChange={(v) => setField("bay_height", v.replace(",", "."))} onBlur={onBlurDimension} error={!!err.bay_height} />
        </>
      )}

      {/* Rect Vérif Rénovation */}
      {shape === "rect" && s3.renovation_mode && (
        <>
          <View style={styles.row2}>
            <View style={{ flex: 1 }}>
              <CotField testID="input-width-top" label={t("wizard.step3.widthTop")} value={s3.width_top}
                onChange={(v) => setField("width_top", v.replace(",", "."))} error={!!err.width_top} />
            </View>
            <View style={{ flex: 1 }}>
              <CotField testID="input-width-bottom" label={t("wizard.step3.widthBottom")} value={s3.width_bottom}
                onChange={(v) => setField("width_bottom", v.replace(",", "."))} error={!!err.width_bottom} />
            </View>
          </View>
          <View style={styles.row2}>
            <View style={{ flex: 1 }}>
              <CotField testID="input-height-left" label={t("wizard.step3.leftHeight")} value={s3.height_left}
                onChange={(v) => setField("height_left", v.replace(",", "."))} error={!!err.height_left} />
            </View>
            <View style={{ flex: 1 }}>
              <CotField testID="input-height-right" label={t("wizard.step3.rightHeight")} value={s3.height_right}
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
            <Text style={styles.computeBtnText}>{t("wizard.step3.computeDiagonal")}</Text>
          </TouchableOpacity>
          <DiagonalField testID="input-diag-1" label={t("wizard.step3.diag1")} value={s3.diag_1}
            state={s3.diag_1_state}
            onChange={(v) => {
              setField("diag_1", v.replace(",", "."));
              setField("diag_1_state", "manual");
            }}
            onValidate={() => validateDiag(1)} onModify={() => modifyDiag(1)} error={!!err.diag_1} />
          <DiagonalField testID="input-diag-2" label={t("wizard.step3.diag2")} value={s3.diag_2}
            state={s3.diag_2_state}
            onChange={(v) => {
              setField("diag_2", v.replace(",", "."));
              setField("diag_2_state", "manual");
            }}
            onValidate={() => validateDiag(2)} onModify={() => modifyDiag(2)} error={!!err.diag_2} />
        </>
      )}

      {/* Feuillures conditionnelles (Brique/Pierre/Bloc béton) */}
      {showFeuillures && shape !== "oeil_de_boeuf" && (
        <>
          <Text style={[styles.sectionLabel, { marginTop: 22 }]}>{t("wizard.step3.feuillureSection")}</Text>
          <Text style={styles.helperText}>{t("wizard.step3.feuillureHint")}</Text>
          <CotField testID="input-feuillure-left" label={t("wizard.step3.feuillureLeft")} value={s3.feuillure_left_mm}
            onChange={(v) => setField("feuillure_left_mm", v.replace(",", "."))} />
          <CotField testID="input-feuillure-right" label={t("wizard.step3.feuillureRight")} value={s3.feuillure_right_mm}
            onChange={(v) => setField("feuillure_right_mm", v.replace(",", "."))} />
          <CotField testID="input-feuillure-top" label={t("wizard.step3.feuillureTop")} value={s3.feuillure_top_mm}
            onChange={(v) => setField("feuillure_top_mm", v.replace(",", "."))} />
        </>
      )}

      {/* Œil-de-bœuf : feuillure circulaire unique (identique tout autour) */}
      {showFeuillures && shape === "oeil_de_boeuf" && (
        <>
          <Text style={[styles.sectionLabel, { marginTop: 22 }]}>{t("wizard.step3.feuillureCircularSection")}</Text>
          <Text style={styles.helperText}>{t("wizard.step3.feuillureCircularHint")}</Text>
          <CotField
            testID="input-feuillure-circular"
            label={t("wizard.step3.feuillureCircular")}
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

      {/* Allège — par ouverture (rect / trapèze / triangle / œil-de-bœuf) */}
      {(shape === "rect" ||
        shape === "trapeze" ||
        shape === "triangle" ||
        shape === "oeil_de_boeuf") && (
        <>
          <Text style={[styles.sectionLabel, { marginTop: 22 }]}>{t("wizard.step3.breastworkSection")}</Text>
          <CheckboxRow
            testID="opt-breastwork"
            label={t("wizard.step3.breastworkLabel")}
            sub={t("wizard.step3.breastworkSub")}
            value={s3.has_breastwork}
            onChange={(v) => setField("has_breastwork", v)}
          />
          {s3.has_breastwork && (
            <CotField
              testID="input-breastwork-height"
              label={t("wizard.step3.breastworkHeight")}
              value={s3.breastwork_height_mm}
              onChange={(v) =>
                setField("breastwork_height_mm", v.replace(",", "."))
              }
              error={!!err.breastwork_height_mm}
            />
          )}
        </>
      )}

      {/* Trait de niveau 1m + calcul auto réserve sol */}
      {show1mLevel && (
        <>
          <Text style={[styles.sectionLabel, { marginTop: 22 }]}>{t("wizard.step3.floorReserveSection")}</Text>
          <CheckboxRow
            testID="opt-1m-level-mark"
            label={t("wizard.step3.mark1mLabel")}
            sub={t("wizard.step3.mark1mSub")}
            value={s3.has_1m_level_mark}
            onChange={(v) => setField("has_1m_level_mark", v)}
          />
          {s3.has_1m_level_mark ? (
            <>
              <CotField
                testID="input-trait-1m-brut"
                label={t("wizard.step3.mark1mBrut")}
                value={s3.trait_1m_brut_mm}
                onChange={(v) => setField("trait_1m_brut_mm", v.replace(",", "."))}
                error={!!err.trait_1m_brut_mm}
              />
              {computedFloorReserve != null && (
                <View testID="auto-floor-reserve-display" style={styles.computedBox}>
                  <Ionicons name="calculator" size={16} color={colors.success} />
                  <Text style={styles.computedLabel}>{t("wizard.step3.computedFloorReserve")}</Text>
                  <Text style={styles.computedValue}>
                    {computedFloorReserve} mm
                  </Text>
                  <Text style={styles.computedFormula}>{t("wizard.step3.computedFloorReserveFormula")}</Text>
                </View>
              )}
            </>
          ) : (
            <CotField
              testID="input-floor-reserve"
              label={t("wizard.step3.floorReserve")}
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
          label={t("wizard.step3.floorReserve")}
          value={s3.floor_reserve}
          onChange={(v) => setField("floor_reserve", v.replace(",", "."))}
          error={!!err.floor_reserve}
        />
      )}

      {/* Photo */}
      <Text style={[styles.label, { marginTop: 24 }]}>{t("wizard.step3.photoOptional")}</Text>
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
            <Text style={styles.photoBtnText}>{t("wizard.step3.camera")}</Text>
          </TouchableOpacity>
          <TouchableOpacity testID="photo-library-button" onPress={() => pickPhoto("library")} style={styles.photoBtn} activeOpacity={0.7}>
            <Ionicons name="images" size={22} color={colors.primary} />
            <Text style={styles.photoBtnText}>{t("wizard.step3.gallery")}</Text>
          </TouchableOpacity>
        </View>
      )}
    </View>
  );
}
