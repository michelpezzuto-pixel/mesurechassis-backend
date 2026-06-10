/**
 * Step3Cotes — Wizard Étape 3/3 : cotes adaptatives & intelligentes.
 * Extrait de /app/frontend/app/chantier/[id]/new-mesure.tsx (refacto V3 Phase 2 — juin 2026).
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
  const isRectFamily =
    shape === "rect" ||
    shape === "porte_entree" ||
    shape === "porte_garage" ||
    shape === "coulissant_levant";
  const show1mLevel = shape === "porte_entree" || shape === "coulissant_levant";
  // M3 FIX — Feuillures : masquage si "coupe horizontale" est OFF dans Step 1
  // (en plus de la maçonnerie qui doit avoir des feuillures).
  // 🚪 Sur une porte de garage / coulissant levant, les feuillures n'ont
  // PAS de sens (pose en applique ou sous linteau, pas en feuillure), donc
  // on masque la section même si la maçonnerie en a habituellement.
  // 🚧 Bow-window : formulaire désactivé tant que le module n'est pas livré.
  const router = useRouter();
  const showFeuillures =
    masonryHasFeuillures(s1MasonryType) &&
    !!s1HasHorizontalCut &&
    shape !== "porte_garage" &&
    shape !== "coulissant_levant" &&
    shape !== "bow_window";

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
          <ArcLengthVerification
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
          <ArcLengthVerification
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
        </>
      )}

      {/* 🆕 V3 — Bow-Window : module en cours de fabrication (cahier 10/06/2026 v2) */}
      {shape === "bow_window" && (
        <>
          <View style={[styles.inlineHintBox, { marginTop: 8, backgroundColor: "rgba(255,165,0,0.10)", borderColor: "rgba(255,165,0,0.45)", flexDirection: "column", alignItems: "flex-start" }]}>
            <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
              <Ionicons name="construct" size={18} color={colors.warning} />
              <Text style={[styles.inlineHintText, { color: colors.warning, fontWeight: "800", flex: 1 }]}>
                🚧 Ce module est en cours de fabrication.
              </Text>
            </View>
            <Text style={[styles.inlineHintText, { color: colors.textPrimary, marginTop: 8, lineHeight: 18 }]}>
              N&apos;hésitez pas à nous envoyer vos idées ou vos techniques de
              mesure pour compléter ce module.{"\n\n"}
              Comment améliorer la fonction Bow-Window ? Comment vous
              faciliter la tâche en nous indiquant votre expertise dans le
              choix des mesures ?
            </Text>
          </View>
          <TouchableOpacity
            testID="bow-expertise-admin-button"
            onPress={() => router.push("/feedback?to=admin&topic=bow_window")}
            activeOpacity={0.85}
            style={[styles.btn, styles.btnPrimary, { marginTop: 14, marginBottom: 6 }]}
          >
            <Ionicons name="paper-plane" size={18} color="#000" />
            <Text style={styles.btnPrimaryText}>
              ENVOYER VOS REMARQUES / EXPERTISE À L&apos;ADMINISTRATEUR
            </Text>
          </TouchableOpacity>
          <Text style={[styles.helperText, { fontSize: 11, opacity: 0.55, marginTop: 6 }]}>
            ⓘ Le formulaire de saisie est temporairement désactivé. Choisissez
            une autre forme dans l&apos;étape précédente, ou retournez en arrière.
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
          <ShapeSchemaV2
            shape="ovale"
            values={{
              L: parseNum(s3.bay_width) || undefined,
              H: parseNum(s3.bay_height) || undefined,
            }}
          />
          <Text style={styles.helperText}>
            ⬭ Ovale — Forme ellipsoïdale. Saisissez uniquement la largeur
            et la hauteur totales.
          </Text>
          <CotField testID="input-bay-width" label="LARGEUR TOTALE L (mm) *" value={s3.bay_width}
            onChange={(v) => setField("bay_width", v.replace(",", "."))} error={!!err.bay_width} />
          <CotField testID="input-bay-height" label="HAUTEUR TOTALE H (mm) *" value={s3.bay_height}
            onChange={(v) => setField("bay_height", v.replace(",", "."))} error={!!err.bay_height} />
        </>
      )}

      {/* 🆕 V3 — Polygone unifié (3/5/6/8 arêtes) */}
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
          <Text style={styles.helperText}>
            ⬡ Polygone — Choisissez le nombre d&apos;arêtes, puis renseignez
            la longueur de chaque arête et l&apos;angle de chaque sommet.
            Les valeurs par défaut correspondent à un polygone régulier.
          </Text>

          <Text style={[styles.sectionLabel, { marginTop: 12 }]}>NOMBRE D&apos;ARÊTES *</Text>
          <View style={[styles.row2, { marginBottom: 10, flexWrap: "wrap" }]}>
            {(["3", "5", "6", "8"] as const).map((n) => {
              const active = s3.polygon_edge_count === n;
              const labelMap: Record<string, string> = {
                "3": "TRIANGLE (3)",
                "5": "PENTAGONE (5)",
                "6": "HEXAGONE (6)",
                "8": "OCTOGONE (8)",
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
            label="LONGUEUR D'UNE ARÊTE (mm) *"
            value={s3.polygon_edge_length}
            onChange={(v) => setField("polygon_edge_length", v.replace(",", "."))}
            error={!!err.polygon_edge_length}
          />
          <CotField
            testID="input-polygon-angle"
            label="ANGLE D'UN SOMMET (°) *"
            value={s3.polygon_angle_deg}
            onChange={(v) => setField("polygon_angle_deg", v.replace(",", "."))}
            error={!!err.polygon_angle_deg}
          />

          <Text style={[styles.sectionLabel, { marginTop: 12 }]}>HORS-TOUT (boîte englobante)</Text>
          <View style={styles.row2}>
            <View style={{ flex: 1 }}>
              <CotField
                testID="input-polygon-bbox-width"
                label="LARGEUR (mm) *"
                value={s3.polygon_bbox_width}
                onChange={(v) => setField("polygon_bbox_width", v.replace(",", "."))}
                error={!!err.polygon_bbox_width}
              />
            </View>
            <View style={{ flex: 1 }}>
              <CotField
                testID="input-polygon-bbox-height"
                label="HAUTEUR (mm) *"
                value={s3.polygon_bbox_height}
                onChange={(v) => setField("polygon_bbox_height", v.replace(",", "."))}
                error={!!err.polygon_bbox_height}
              />
            </View>
          </View>
          <Text style={styles.helperText}>
            ✓ Pour un polygone régulier : tous les côtés ont la même longueur
            et tous les sommets le même angle. Pour un polygone irrégulier,
            indiquez la valeur moyenne ou contactez le technicien pour
            renseigner chaque arête séparément.
          </Text>
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
            📏 Mesures spécifiques à la pose d&apos;une porte sectionnelle :
            le linteau est la hauteur sous-plafond disponible au-dessus de
            la baie ; les écoinçons sont la largeur de mur plein disponible
            de part et d&apos;autre de la baie pour fixer les rails verticaux
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
            La feuillure d&apos;un œil-de-bœuf est circulaire et identique sur
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
