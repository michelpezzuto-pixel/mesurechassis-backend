/**
 * ShapeSchemaV2 — Schémas SVG adaptatifs pour les 7 nouvelles formes
 *
 * Affiche un schéma simple qui se met à jour selon les valeurs saisies par
 * l'utilisateur. But : que le mesureur visualise IMMÉDIATEMENT où se situent
 * L, H, H1, H2, etc.
 *
 * Utilisation :
 *   <ShapeSchemaV2 shape="plein_cintre" values={{L: 1200, H1: 1800, H2: 2400}} />
 */

import React from "react";
import { View, Text, StyleSheet } from "react-native";
import Svg, {
  Path,
  Line,
  Rect,
  Polygon,
  Ellipse,
  Text as SvgText,
  G,
  Circle,
} from "react-native-svg";

type ShapeKey =
  | "plein_cintre"
  | "arc_surbaisse"
  | "angle_90"
  | "bow_window"
  | "pentagone"
  | "hexagone"
  | "ovale"
  | "polygone";

type Values = {
  L?: number; // Largeur principale (bay_width)
  H?: number; // Hauteur principale (bay_height) — utilisée si pas de Hleft/Hright
  Hleft?: number; // Hauteur gauche (angle_90 asymétrique)
  Hright?: number; // Hauteur droite (angle_90 asymétrique)
  H1?: number; // Hauteur d'appui / côtés
  H2?: number; // Hauteur totale / sommet
  cutW?: number; // Pan coupé largeur (angle 90)
  cutH?: number; // Pan coupé hauteur (angle 90)
  cutSide?: "left" | "right" | "both"; // Côté(s) coupé(s)
  cutAngleDeg?: number; // Angle du pan coupé (par défaut 135°)
  P?: number; // Profondeur projection (bow)
  panels?: number; // Nb pans (3 ou 5)
  Wtop?: number; // Largeur sommet (hexagone)
  Hside?: number; // Hauteur côtés verticaux (hexagone)
};

type Props = {
  shape: ShapeKey;
  values: Values;
  width?: number;
  height?: number;
};

const PALETTE = {
  bg: "#0f1419",
  outline: "#f97316", // orange MesureChâssis
  fill: "rgba(249, 115, 22, 0.15)",
  cote: "#fb923c", // orange clair pour les cotes
  cote_text: "#ffffff",
  helper: "#94a3b8",
};

const COTE_FONT = 11;
const STROKE = 2;

// Helper : safe number
const sn = (v: number | undefined, defaultVal: number = 0): number =>
  typeof v === "number" && !isNaN(v) && v > 0 ? v : defaultVal;

// Helper : fit shape into the SVG box (keep aspect ratio)
function fitToBox(
  shapeWidth: number,
  shapeHeight: number,
  boxWidth: number,
  boxHeight: number,
  padding: number = 30,
) {
  const availW = boxWidth - padding * 2;
  const availH = boxHeight - padding * 2;
  const ratio = Math.min(availW / shapeWidth, availH / shapeHeight);
  return {
    scale: ratio,
    offsetX: (boxWidth - shapeWidth * ratio) / 2,
    offsetY: (boxHeight - shapeHeight * ratio) / 2,
  };
}

export default function ShapeSchemaV2({
  shape,
  values,
  width = 320,
  height = 280,
}: Props) {
  return (
    <View style={[styles.container, { width: "100%", maxWidth: 360 }]}>
      <Svg width={"100%"} height={height} viewBox={`0 0 ${width} ${height}`}>
        {renderShape(shape, values, width, height)}
      </Svg>
    </View>
  );
}

function renderShape(
  shape: ShapeKey,
  values: Values,
  W: number,
  H: number,
) {
  switch (shape) {
    case "plein_cintre":
      return renderPleinCintre(values, W, H);
    case "arc_surbaisse":
      return renderArcSurbaisse(values, W, H);
    case "angle_90":
      return renderAngle90(values, W, H);
    case "bow_window":
      return renderBowWindow(values, W, H);
    case "pentagone":
      return renderPentagone(values, W, H);
    case "hexagone":
      return renderHexagone(values, W, H);
    case "ovale":
      return renderOvale(values, W, H);
    case "polygone":
      return renderPolygone(values, W, H);
    default:
      return null;
  }
}

// 🆕 V3 — POLYGONE régulier (3 / 5 / 6 / 8 arêtes). On centre le polygone
//    dans la bbox L × H demandée. La 1ère arête est placée en bas pour que
//    le repère soit familier (côté largeur = base).
function renderPolygone(v: Values, W: number, H: number) {
  const n = Math.max(3, Math.min(8, sn(v.panels, 6)));
  const Wtot = sn(v.L, 1500);
  const Htot = sn(v.H, 1500);
  const fit = fitToBox(Wtot, Htot, W, H, 50);
  const cx = fit.offsetX + (Wtot * fit.scale) / 2;
  const cy = fit.offsetY + (Htot * fit.scale) / 2;
  const radius = Math.min(Wtot * fit.scale, Htot * fit.scale) / 2;
  // Rotation : on veut une arête plate en bas pour pair, ou un sommet en
  // haut pour impair. Angle initial = -90° (sommet haut) ou ajustement.
  const startAngle = n % 2 === 0 ? Math.PI / n - Math.PI / 2 : -Math.PI / 2;
  const pts: string[] = [];
  for (let i = 0; i < n; i++) {
    const a = startAngle + (2 * Math.PI * i) / n;
    const px = cx + radius * Math.cos(a);
    const py = cy + radius * Math.sin(a);
    pts.push(`${px.toFixed(1)},${py.toFixed(1)}`);
  }
  return (
    <G>
      <Polygon
        points={pts.join(" ")}
        fill={PALETTE.fill}
        stroke={PALETTE.outline}
        strokeWidth={STROKE}
      />
      {/* Cote largeur (sous le polygone) */}
      <Line
        x1={fit.offsetX}
        y1={fit.offsetY + Htot * fit.scale + 18}
        x2={fit.offsetX + Wtot * fit.scale}
        y2={fit.offsetY + Htot * fit.scale + 18}
        stroke={PALETTE.cote}
        strokeWidth={1.5}
      />
      <SvgText
        x={cx}
        y={fit.offsetY + Htot * fit.scale + 33}
        fill={PALETTE.cote_text}
        fontSize={COTE_FONT}
        textAnchor="middle"
        fontWeight="bold"
      >
        L = {Math.round(Wtot)} mm
      </SvgText>
      {/* Cote hauteur (à droite) */}
      <Line
        x1={fit.offsetX + Wtot * fit.scale + 14}
        y1={fit.offsetY}
        x2={fit.offsetX + Wtot * fit.scale + 14}
        y2={fit.offsetY + Htot * fit.scale}
        stroke={PALETTE.cote}
        strokeWidth={1.5}
      />
      <SvgText
        x={fit.offsetX + Wtot * fit.scale + 18}
        y={cy + 4}
        fill={PALETTE.cote_text}
        fontSize={COTE_FONT}
        fontWeight="bold"
      >
        H = {Math.round(Htot)}
      </SvgText>
      {/* Label nombre d'arêtes au centre */}
      <SvgText
        x={cx}
        y={cy + 5}
        fill={PALETTE.outline}
        fontSize={COTE_FONT}
        textAnchor="middle"
        fontWeight="bold"
      >
        {n} arêtes
      </SvgText>
    </G>
  );
}

// 1. PLEIN CINTRE — Rectangle + demi-cercle au sommet (R = L/2)
function renderPleinCintre(v: Values, W: number, H: number) {
  const L = sn(v.L, 1200);
  const H1 = sn(v.H1, 1800);
  const radius = L / 2;
  const totalShapeH = H1 + radius;

  const fit = fitToBox(L, totalShapeH, W, H, 40);
  const x0 = fit.offsetX;
  const y0 = fit.offsetY;
  const sW = L * fit.scale;
  const sH = H1 * fit.scale;
  const sR = radius * fit.scale;

  // arc demi-cercle au sommet
  const arcStart = `${x0} ${y0 + sR}`;
  const arcEnd = `${x0 + sW} ${y0 + sR}`;
  const path = `M ${x0} ${y0 + sR + sH} L ${x0} ${y0 + sR} A ${sR} ${sR} 0 0 1 ${arcEnd.split(" ")[0]} ${arcEnd.split(" ")[1]} L ${x0 + sW} ${y0 + sR + sH} Z`;

  return (
    <G>
      <Path d={path} fill={PALETTE.fill} stroke={PALETTE.outline} strokeWidth={STROKE} />

      {/* Cote L (largeur en bas) */}
      <Line x1={x0} y1={y0 + sR + sH + 18} x2={x0 + sW} y2={y0 + sR + sH + 18} stroke={PALETTE.cote} strokeWidth={1.5} />
      <SvgText x={x0 + sW / 2} y={y0 + sR + sH + 33} fill={PALETTE.cote_text} fontSize={COTE_FONT} textAnchor="middle" fontWeight="bold">L = {Math.round(v.L || 0)} mm</SvgText>

      {/* Cote H1 (côté droit, jusqu'à l'appui) */}
      <Line x1={x0 + sW + 14} y1={y0 + sR} x2={x0 + sW + 14} y2={y0 + sR + sH} stroke={PALETTE.cote} strokeWidth={1.5} />
      <SvgText x={x0 + sW + 20} y={y0 + sR + sH / 2 + 4} fill={PALETTE.cote_text} fontSize={COTE_FONT} fontWeight="bold">H1 = {Math.round(v.H1 || 0)}</SvgText>

      {/* Cote H2 (côté gauche, jusqu'au sommet) */}
      <Line x1={x0 - 14} y1={y0} x2={x0 - 14} y2={y0 + sR + sH} stroke={PALETTE.cote} strokeWidth={1.5} />
      <SvgText x={x0 - 60} y={y0 + (sR + sH) / 2 + 4} fill={PALETTE.cote_text} fontSize={COTE_FONT} fontWeight="bold">H2 = {Math.round(v.H2 || 0)}</SvgText>

    </G>
  );
}

// 2. ARC SURBAISSÉ — Rectangle + arc moins haut (flèche < L/2)
function renderArcSurbaisse(v: Values, W: number, H: number) {
  const L = sn(v.L, 1500);
  const H1 = sn(v.H1, 1800);
  const H2 = sn(v.H2, 2100);
  const fleche = Math.max(0, H2 - H1);
  const totalShapeH = H1 + fleche;

  const fit = fitToBox(L, totalShapeH, W, H, 50);
  const x0 = fit.offsetX;
  const y0 = fit.offsetY;
  const sW = L * fit.scale;
  const sH = H1 * fit.scale;
  const sF = fleche * fit.scale;

  // Arc surbaissé : path quadratique
  const path = `M ${x0} ${y0 + sF + sH} L ${x0} ${y0 + sF} Q ${x0 + sW / 2} ${y0 - sF + sF} ${x0 + sW} ${y0 + sF} L ${x0 + sW} ${y0 + sF + sH} Z`;

  return (
    <G>
      <Path d={path} fill={PALETTE.fill} stroke={PALETTE.outline} strokeWidth={STROKE} />

      {/* L */}
      <Line x1={x0} y1={y0 + sF + sH + 18} x2={x0 + sW} y2={y0 + sF + sH + 18} stroke={PALETTE.cote} strokeWidth={1.5} />
      <SvgText x={x0 + sW / 2} y={y0 + sF + sH + 33} fill={PALETTE.cote_text} fontSize={COTE_FONT} textAnchor="middle" fontWeight="bold">L = {Math.round(v.L || 0)} mm</SvgText>

      {/* H1 */}
      <Line x1={x0 + sW + 14} y1={y0 + sF} x2={x0 + sW + 14} y2={y0 + sF + sH} stroke={PALETTE.cote} strokeWidth={1.5} />
      <SvgText x={x0 + sW + 20} y={y0 + sF + sH / 2 + 4} fill={PALETTE.cote_text} fontSize={COTE_FONT} fontWeight="bold">H1 = {Math.round(v.H1 || 0)}</SvgText>

      {/* H2 */}
      <Line x1={x0 - 14} y1={y0} x2={x0 - 14} y2={y0 + sF + sH} stroke={PALETTE.cote} strokeWidth={1.5} />
      <SvgText x={x0 - 60} y={y0 + (sF + sH) / 2 + 4} fill={PALETTE.cote_text} fontSize={COTE_FONT} fontWeight="bold">H2 = {Math.round(v.H2 || 0)}</SvgText>

      {/* Flèche f */}
      <SvgText x={x0 + sW / 2} y={y0 + sF / 2 + 4} fill={PALETTE.helper} fontSize={COTE_FONT - 1} textAnchor="middle">f = {Math.round(fleche)} mm</SvgText>
    </G>
  );
}

// 3. ANGLE 90° — Rectangle avec UN ou DEUX pans coupés (haut gauche / haut droit / les deux).
//    Supporte des hauteurs gauche/droite indépendantes.
//    Affiche les libellés DANS la zone du pan coupé pour une compréhension immédiate.
function renderAngle90(v: Values, W: number, H: number) {
  const Wtot = sn(v.L, 1500);
  // Hauteurs asymétriques possibles. Si non fournies, on retombe sur v.H.
  const Hleft = sn(v.Hleft, sn(v.H, 1500));
  const Hright = sn(v.Hright, sn(v.H, 1500));
  const cW = Math.min(sn(v.cutW, 400), Wtot - 1);
  const Hmin = Math.min(Hleft, Hright);
  const cH = Math.min(sn(v.cutH, 400), Hmin - 1);
  const side = v.cutSide || "right";
  const angleDeg = sn(v.cutAngleDeg, 135);

  const HtotDraw = Math.max(Hleft, Hright);
  const fit = fitToBox(Wtot, HtotDraw, W, H, 55);
  const x0 = fit.offsetX;
  const y0 = fit.offsetY;
  const sW = Wtot * fit.scale;
  const sHleft = Hleft * fit.scale;
  const sHright = Hright * fit.scale;
  const scW = cW * fit.scale;
  const scH = cH * fit.scale;

  // On dessine en partant du haut-gauche, en parcourant le contour dans le sens
  // horaire. Le sommet est éventuellement coupé à gauche et/ou à droite.
  // Coordonnées y : 0 = haut du SVG. Plus y est grand, plus on est bas.
  const baseY = y0 + Math.max(sHleft, sHright); // ligne du sol
  const topLeftY = baseY - sHleft;
  const topRightY = baseY - sHright;

  const cutLeft = side === "left" || side === "both";
  const cutRight = side === "right" || side === "both";

  // Points du polygone (sens horaire à partir du coin haut-gauche)
  const pts: string[] = [];
  if (cutLeft) {
    pts.push(`${x0},${topLeftY + scH}`);
    pts.push(`${x0 + scW},${topLeftY}`);
  } else {
    pts.push(`${x0},${topLeftY}`);
  }
  if (cutRight) {
    pts.push(`${x0 + sW - scW},${topRightY}`);
    pts.push(`${x0 + sW},${topRightY + scH}`);
  } else {
    pts.push(`${x0 + sW},${topRightY}`);
  }
  pts.push(`${x0 + sW},${baseY}`);
  pts.push(`${x0},${baseY}`);

  return (
    <G>
      <Polygon
        points={pts.join(" ")}
        fill={PALETTE.fill}
        stroke={PALETTE.outline}
        strokeWidth={STROKE}
      />

      {/* Largeur totale L (en bas) */}
      <Line x1={x0} y1={baseY + 18} x2={x0 + sW} y2={baseY + 18} stroke={PALETTE.cote} strokeWidth={1.5} />
      <SvgText x={x0 + sW / 2} y={baseY + 33} fill={PALETTE.cote_text} fontSize={COTE_FONT} textAnchor="middle" fontWeight="bold">L = {Math.round(v.L || 0)} mm</SvgText>

      {/* Hauteur GAUCHE */}
      <Line x1={x0 - 14} y1={topLeftY + (cutLeft ? scH : 0)} x2={x0 - 14} y2={baseY} stroke={PALETTE.cote} strokeWidth={1.5} />
      <SvgText x={x0 - 60} y={(topLeftY + baseY) / 2 + 4} fill={PALETTE.cote_text} fontSize={COTE_FONT} fontWeight="bold">Hg = {Math.round(Hleft)}</SvgText>

      {/* Hauteur DROITE */}
      <Line x1={x0 + sW + 14} y1={topRightY + (cutRight ? scH : 0)} x2={x0 + sW + 14} y2={baseY} stroke={PALETTE.cote} strokeWidth={1.5} />
      <SvgText x={x0 + sW + 18} y={(topRightY + baseY) / 2 + 4} fill={PALETTE.cote_text} fontSize={COTE_FONT} fontWeight="bold">Hd = {Math.round(Hright)}</SvgText>

      {/* Annotations DANS la zone du pan coupé — pan GAUCHE */}
      {cutLeft && (
        <G>
          {/* triangle d'aide pour bien visualiser la zone coupée */}
          <Polygon
            points={`${x0},${topLeftY + scH} ${x0 + scW},${topLeftY} ${x0},${topLeftY}`}
            fill="rgba(255,107,26,0.18)"
            stroke="rgba(255,107,26,0.5)"
            strokeWidth={1}
            strokeDasharray="3,2"
          />
          {/* Largeur du pan (en haut) */}
          <SvgText x={x0 + scW / 2} y={topLeftY - 6} fill={PALETTE.cote_text} fontSize={COTE_FONT - 1} textAnchor="middle" fontWeight="bold">
            Pan L = {Math.round(cW)}
          </SvgText>
          {/* Hauteur du pan (sur le côté) */}
          <SvgText x={x0 - 4} y={topLeftY + scH / 2 + 3} fill={PALETTE.cote_text} fontSize={COTE_FONT - 1} textAnchor="end" fontWeight="bold">
            Pan H = {Math.round(cH)}
          </SvgText>
          {/* Angle */}
          <SvgText x={x0 + scW * 0.6} y={topLeftY + scH * 0.6} fill={PALETTE.outline} fontSize={COTE_FONT - 1} fontWeight="bold">
            {Math.round(angleDeg)}°
          </SvgText>
        </G>
      )}

      {/* Annotations DANS la zone du pan coupé — pan DROIT */}
      {cutRight && (
        <G>
          <Polygon
            points={`${x0 + sW - scW},${topRightY} ${x0 + sW},${topRightY + scH} ${x0 + sW},${topRightY}`}
            fill="rgba(255,107,26,0.18)"
            stroke="rgba(255,107,26,0.5)"
            strokeWidth={1}
            strokeDasharray="3,2"
          />
          <SvgText x={x0 + sW - scW / 2} y={topRightY - 6} fill={PALETTE.cote_text} fontSize={COTE_FONT - 1} textAnchor="middle" fontWeight="bold">
            Pan L = {Math.round(cW)}
          </SvgText>
          <SvgText x={x0 + sW + 4} y={topRightY + scH / 2 + 3} fill={PALETTE.cote_text} fontSize={COTE_FONT - 1} fontWeight="bold">
            Pan H = {Math.round(cH)}
          </SvgText>
          <SvgText x={x0 + sW - scW * 0.6 - 18} y={topRightY + scH * 0.6} fill={PALETTE.outline} fontSize={COTE_FONT - 1} fontWeight="bold">
            {Math.round(angleDeg)}°
          </SvgText>
        </G>
      )}
    </G>
  );
}

// 4. BOW-WINDOW — Vue de dessus (largeur, profondeur)
function renderBowWindow(v: Values, W: number, H: number) {
  const Wtot = sn(v.L, 3000);
  const P = sn(v.P, 600);
  const panels = v.panels === 5 ? 5 : 3;
  const totalShapeH = P + 200; // espace pour la base + cotes

  const fit = fitToBox(Wtot, totalShapeH, W, H, 50);
  const x0 = fit.offsetX;
  const y0 = fit.offsetY + 30;
  const sW = Wtot * fit.scale;
  const sP = P * fit.scale;

  // Vue de DESSUS : ligne droite en bas (mur intérieur) + facettes en saillie
  const baseY = y0 + sP + 20;
  const apexY = y0 + 20;

  // Génération des points selon le nombre de pans
  const pts: { x: number; y: number }[] = [];
  if (panels === 3) {
    pts.push({ x: x0, y: baseY });
    pts.push({ x: x0 + sW * 0.2, y: apexY });
    pts.push({ x: x0 + sW * 0.8, y: apexY });
    pts.push({ x: x0 + sW, y: baseY });
  } else {
    // 5 pans
    pts.push({ x: x0, y: baseY });
    pts.push({ x: x0 + sW * 0.12, y: y0 + sP * 0.5 + 20 });
    pts.push({ x: x0 + sW * 0.3, y: apexY });
    pts.push({ x: x0 + sW * 0.7, y: apexY });
    pts.push({ x: x0 + sW * 0.88, y: y0 + sP * 0.5 + 20 });
    pts.push({ x: x0 + sW, y: baseY });
  }

  const pathPts = pts.map((p) => `${p.x},${p.y}`).join(" ");
  const closedPath = `${pathPts} ${x0 + sW},${baseY} ${x0},${baseY}`;

  return (
    <G>
      {/* Mur (ligne droite) */}
      <Line x1={x0 - 20} y1={baseY} x2={x0 + sW + 20} y2={baseY} stroke={PALETTE.helper} strokeWidth={2} strokeDasharray="5,3" />
      <SvgText x={x0 + sW + 25} y={baseY + 4} fill={PALETTE.helper} fontSize={COTE_FONT - 1}>mur</SvgText>

      {/* Facettes du bow */}
      <Polygon points={closedPath} fill={PALETTE.fill} stroke={PALETTE.outline} strokeWidth={STROKE} />

      {/* Cote L */}
      <Line x1={x0} y1={baseY + 28} x2={x0 + sW} y2={baseY + 28} stroke={PALETTE.cote} strokeWidth={1.5} />
      <SvgText x={x0 + sW / 2} y={baseY + 43} fill={PALETTE.cote_text} fontSize={COTE_FONT} textAnchor="middle" fontWeight="bold">L = {Math.round(v.L || 0)} mm</SvgText>

      {/* Cote P (profondeur) */}
      <Line x1={x0 + sW + 14} y1={apexY} x2={x0 + sW + 14} y2={baseY} stroke={PALETTE.cote} strokeWidth={1.5} />
      <SvgText x={x0 + sW + 18} y={(apexY + baseY) / 2 + 4} fill={PALETTE.cote_text} fontSize={COTE_FONT} fontWeight="bold">P = {Math.round(v.P || 0)}</SvgText>

      {/* Indicateur nb pans */}
      <SvgText x={x0 + sW / 2} y={apexY - 8} fill={PALETTE.helper} fontSize={COTE_FONT - 1} textAnchor="middle">{panels} pans (vue dessus)</SvgText>
    </G>
  );
}

// 5. PENTAGONE — Rectangle + triangle au sommet
function renderPentagone(v: Values, W: number, H: number) {
  const L = sn(v.L, 1200);
  const H1 = sn(v.H1, 1500);
  const H2 = sn(v.H2, 2100);

  const fit = fitToBox(L, H2, W, H, 45);
  const x0 = fit.offsetX;
  const y0 = fit.offsetY;
  const sW = L * fit.scale;
  const sH1 = H1 * fit.scale;
  const sH2 = H2 * fit.scale;
  const triH = sH2 - sH1; // hauteur du triangle au sommet

  // Polygone : (bas-gauche) (bas-droite) (haut-droite-rectangle) (sommet) (haut-gauche-rectangle)
  const pts = `${x0},${y0 + sH2} ${x0 + sW},${y0 + sH2} ${x0 + sW},${y0 + triH} ${x0 + sW / 2},${y0} ${x0},${y0 + triH}`;

  return (
    <G>
      <Polygon points={pts} fill={PALETTE.fill} stroke={PALETTE.outline} strokeWidth={STROKE} />

      {/* L */}
      <Line x1={x0} y1={y0 + sH2 + 18} x2={x0 + sW} y2={y0 + sH2 + 18} stroke={PALETTE.cote} strokeWidth={1.5} />
      <SvgText x={x0 + sW / 2} y={y0 + sH2 + 33} fill={PALETTE.cote_text} fontSize={COTE_FONT} textAnchor="middle" fontWeight="bold">L = {Math.round(v.L || 0)} mm</SvgText>

      {/* H1 (côté droit) */}
      <Line x1={x0 + sW + 14} y1={y0 + triH} x2={x0 + sW + 14} y2={y0 + sH2} stroke={PALETTE.cote} strokeWidth={1.5} />
      <SvgText x={x0 + sW + 20} y={y0 + (triH + sH2) / 2 + 4} fill={PALETTE.cote_text} fontSize={COTE_FONT} fontWeight="bold">H1 = {Math.round(v.H1 || 0)}</SvgText>

      {/* H2 (côté gauche) */}
      <Line x1={x0 - 14} y1={y0} x2={x0 - 14} y2={y0 + sH2} stroke={PALETTE.cote} strokeWidth={1.5} />
      <SvgText x={x0 - 60} y={y0 + sH2 / 2 + 4} fill={PALETTE.cote_text} fontSize={COTE_FONT} fontWeight="bold">H2 = {Math.round(v.H2 || 0)}</SvgText>
    </G>
  );
}

// 6. HEXAGONE — 6 côtés avec haut + bas coupé
function renderHexagone(v: Values, W: number, H: number) {
  const Wbase = sn(v.L, 1500);
  const Wtop = Math.min(sn(v.Wtop, 800), Wbase - 1);
  const Htot = sn(v.H, 2000);
  const Hside = Math.min(sn(v.Hside, 1200), Htot - 1);

  const fit = fitToBox(Wbase, Htot, W, H, 45);
  const x0 = fit.offsetX;
  const y0 = fit.offsetY;
  const sW = Wbase * fit.scale;
  const sWtop = Wtop * fit.scale;
  const sH = Htot * fit.scale;
  const sHside = Hside * fit.scale;

  const topInset = (sW - sWtop) / 2;
  const sideTopY = (sH - sHside) / 2;
  const sideBotY = sideTopY + sHside;

  // Polygone hexagonal
  const pts = `${x0 + topInset},${y0} ${x0 + sW - topInset},${y0} ${x0 + sW},${y0 + sideTopY} ${x0 + sW},${y0 + sideBotY} ${x0 + sW - topInset},${y0 + sH} ${x0 + topInset},${y0 + sH} ${x0},${y0 + sideBotY} ${x0},${y0 + sideTopY}`;

  return (
    <G>
      <Polygon points={pts} fill={PALETTE.fill} stroke={PALETTE.outline} strokeWidth={STROKE} />

      {/* Largeur base */}
      <Line x1={x0} y1={y0 + sH + 18} x2={x0 + sW} y2={y0 + sH + 18} stroke={PALETTE.cote} strokeWidth={1.5} />
      <SvgText x={x0 + sW / 2} y={y0 + sH + 33} fill={PALETTE.cote_text} fontSize={COTE_FONT} textAnchor="middle" fontWeight="bold">L base = {Math.round(v.L || 0)} mm</SvgText>

      {/* Largeur sommet */}
      <Line x1={x0 + topInset} y1={y0 - 14} x2={x0 + sW - topInset} y2={y0 - 14} stroke={PALETTE.cote} strokeWidth={1.5} />
      <SvgText x={x0 + sW / 2} y={y0 - 18} fill={PALETTE.cote_text} fontSize={COTE_FONT} textAnchor="middle" fontWeight="bold">L sommet = {Math.round(Wtop)}</SvgText>

      {/* Hauteur totale */}
      <Line x1={x0 + sW + 14} y1={y0} x2={x0 + sW + 14} y2={y0 + sH} stroke={PALETTE.cote} strokeWidth={1.5} />
      <SvgText x={x0 + sW + 18} y={y0 + sH / 2 + 4} fill={PALETTE.cote_text} fontSize={COTE_FONT} fontWeight="bold">H = {Math.round(v.H || 0)}</SvgText>

      {/* Hauteur des côtés verticaux */}
      <Line x1={x0 - 14} y1={y0 + sideTopY} x2={x0 - 14} y2={y0 + sideBotY} stroke={PALETTE.helper} strokeWidth={1.5} />
      <SvgText x={x0 - 60} y={y0 + (sideTopY + sideBotY) / 2 + 4} fill={PALETTE.helper} fontSize={COTE_FONT - 1}>Hside={Math.round(Hside)}</SvgText>
    </G>
  );
}

// 7. OVALE — Ellipse
function renderOvale(v: Values, W: number, H: number) {
  const L = sn(v.L, 1500);
  const Htot = sn(v.H, 1000);

  const fit = fitToBox(L, Htot, W, H, 60);
  const cx = W / 2;
  const cy = H / 2;
  const rx = (L * fit.scale) / 2;
  const ry = (Htot * fit.scale) / 2;

  return (
    <G>
      <Ellipse cx={cx} cy={cy} rx={rx} ry={ry} fill={PALETTE.fill} stroke={PALETTE.outline} strokeWidth={STROKE} />

      {/* Centre */}
      <Circle cx={cx} cy={cy} r={3} fill={PALETTE.outline} />

      {/* L (axe horizontal) */}
      <Line x1={cx - rx} y1={cy + ry + 18} x2={cx + rx} y2={cy + ry + 18} stroke={PALETTE.cote} strokeWidth={1.5} />
      <SvgText x={cx} y={cy + ry + 33} fill={PALETTE.cote_text} fontSize={COTE_FONT} textAnchor="middle" fontWeight="bold">L = {Math.round(v.L || 0)} mm</SvgText>

      {/* H (axe vertical) */}
      <Line x1={cx + rx + 14} y1={cy - ry} x2={cx + rx + 14} y2={cy + ry} stroke={PALETTE.cote} strokeWidth={1.5} />
      <SvgText x={cx + rx + 18} y={cy + 4} fill={PALETTE.cote_text} fontSize={COTE_FONT} fontWeight="bold">H = {Math.round(v.H || 0)}</SvgText>

      {/* Rayons indicatifs */}
      <Line x1={cx} y1={cy} x2={cx + rx} y2={cy} stroke={PALETTE.helper} strokeWidth={1} strokeDasharray="3,3" />
      <SvgText x={cx + rx / 2} y={cy - 5} fill={PALETTE.helper} fontSize={COTE_FONT - 1} textAnchor="middle">Rx=L/2</SvgText>
      <Line x1={cx} y1={cy} x2={cx} y2={cy + ry} stroke={PALETTE.helper} strokeWidth={1} strokeDasharray="3,3" />
      <SvgText x={cx + 5} y={cy + ry / 2 + 4} fill={PALETTE.helper} fontSize={COTE_FONT - 1}>Ry=H/2</SvgText>
    </G>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: PALETTE.bg,
    borderRadius: 12,
    padding: 12,
    marginVertical: 10,
    alignSelf: "center",
    borderWidth: 1,
    borderColor: "rgba(249,115,22,0.2)",
  },
});
