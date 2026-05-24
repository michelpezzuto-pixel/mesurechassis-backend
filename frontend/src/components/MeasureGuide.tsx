import React from "react";
import { StyleSheet, View } from "react-native";
import Svg, {
  Rect,
  Ellipse,
  Line,
  Polygon,
  Polyline,
  G,
  Text as SvgText,
} from "react-native-svg";
import type { ShapeKey } from "./ShapeIcon";

/**
 * Guide visuel de prise de cotes — schéma annoté qui montre clairement
 * AU MÉTREUR où prendre chaque mesure pour la forme sélectionnée.
 *
 * IMPLÉMENTATION : tout est en SVG (forme + cotes + étiquettes) afin
 * d'éviter tout mismatch de scaling entre le dessin et les labels HTML.
 */
type Props = {
  shape: ShapeKey;
  strokeColor?: string;
  dimColor?: string;
};

const W = 320;
const H = 240;

/* ── Pointe de flèche ── */
const Arrowhead: React.FC<{
  x: number;
  y: number;
  direction: "up" | "down" | "left" | "right";
  color: string;
}> = ({ x, y, direction, color }) => {
  const s = 4.5;
  let pts = "";
  switch (direction) {
    case "up":
      pts = `${x},${y} ${x - s},${y + s} ${x + s},${y + s}`;
      break;
    case "down":
      pts = `${x},${y} ${x - s},${y - s} ${x + s},${y - s}`;
      break;
    case "left":
      pts = `${x},${y} ${x + s},${y - s} ${x + s},${y + s}`;
      break;
    case "right":
      pts = `${x},${y} ${x - s},${y - s} ${x - s},${y + s}`;
      break;
  }
  return <Polygon points={pts} fill={color} />;
};

/* ── Étiquette de cote intégrée au SVG (pastille orange) ── */
const DimTag: React.FC<{
  x: number;
  y: number;
  text: string;
  color: string;
  bg: string;
}> = ({ x, y, text, color, bg }) => {
  const w = Math.max(18, text.length * 7 + 6);
  const h = 14;
  return (
    <G>
      <Rect
        x={x - w / 2}
        y={y - h / 2}
        width={w}
        height={h}
        rx={2.5}
        ry={2.5}
        fill={bg}
        stroke={color}
        strokeWidth={0.9}
      />
      <SvgText
        x={x}
        y={y + 3.5}
        fill={color}
        fontSize="10"
        fontWeight="bold"
        textAnchor="middle"
      >
        {text}
      </SvgText>
    </G>
  );
};

export const MeasureGuide: React.FC<Props> = ({
  shape,
  strokeColor = "#FFFFFF",
  dimColor = "#FF6B1A",
}) => {
  const dim = {
    stroke: dimColor,
    strokeWidth: 1.2,
    fill: "none" as const,
    strokeLinecap: "round" as const,
  };
  const main = {
    stroke: strokeColor,
    strokeWidth: 1.6,
    fill: "none" as const,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
  };
  const TAG_BG = "#0c0c0c";

  const Wrap = (children: React.ReactNode) => (
    <View style={styles.container}>
      <Svg
        width="100%"
        height="100%"
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="xMidYMid meet"
      >
        {children}
      </Svg>
    </View>
  );

  /* ────────── 1. CARRÉ / RECTANGLE ────────── */
  if (shape === "rect") {
    return Wrap(
      <>
        <Rect x={90} y={50} width={140} height={140} {...main} />
        <Rect x={97} y={57} width={126} height={126} {...main} />
        {/* Cote LARGEUR */}
        <Line x1={90} y1={36} x2={230} y2={36} {...dim} />
        <Arrowhead x={90} y={36} direction="left" color={dimColor} />
        <Arrowhead x={230} y={36} direction="right" color={dimColor} />
        <DimTag x={160} y={26} text="L" color={dimColor} bg={TAG_BG} />
        {/* Cote HAUTEUR */}
        <Line x1={250} y1={50} x2={250} y2={190} {...dim} />
        <Arrowhead x={250} y={50} direction="up" color={dimColor} />
        <Arrowhead x={250} y={190} direction="down" color={dimColor} />
        <DimTag x={272} y={120} text="H" color={dimColor} bg={TAG_BG} />
        {/* Diagonales */}
        <Line x1={97} y1={57} x2={223} y2={183} {...dim} strokeDasharray="4 3" />
        <Line x1={223} y1={57} x2={97} y2={183} {...dim} strokeDasharray="4 3" />
        <DimTag x={130} y={120} text="D1" color={dimColor} bg={TAG_BG} />
        <DimTag x={190} y={120} text="D2" color={dimColor} bg={TAG_BG} />
      </>
    );
  }

  /* ────────── 2. TRAPÈZE ────────── */
  if (shape === "trapeze") {
    return Wrap(
      <>
        <Polygon points="80,200 80,80 220,40 220,200" {...main} />
        <Polygon points="87,193 87,87 213,49 213,193" {...main} />
        {/* L (base) */}
        <Line x1={80} y1={215} x2={220} y2={215} {...dim} />
        <Arrowhead x={80} y={215} direction="left" color={dimColor} />
        <Arrowhead x={220} y={215} direction="right" color={dimColor} />
        <DimTag x={150} y={225} text="L" color={dimColor} bg={TAG_BG} />
        {/* Hg */}
        <Line x1={62} y1={80} x2={62} y2={200} {...dim} />
        <Arrowhead x={62} y={80} direction="up" color={dimColor} />
        <Arrowhead x={62} y={200} direction="down" color={dimColor} />
        <DimTag x={42} y={140} text="Hg" color={dimColor} bg={TAG_BG} />
        {/* Hd */}
        <Line x1={238} y1={40} x2={238} y2={200} {...dim} />
        <Arrowhead x={238} y={40} direction="up" color={dimColor} />
        <Arrowhead x={238} y={200} direction="down" color={dimColor} />
        <DimTag x={258} y={120} text="Hd" color={dimColor} bg={TAG_BG} />
        {/* Pente */}
        <Line x1={75} y1={75} x2={215} y2={35} {...dim} />
        <Arrowhead x={75} y={75} direction="left" color={dimColor} />
        <Arrowhead x={215} y={35} direction="right" color={dimColor} />
        <DimTag x={145} y={22} text="Pente" color={dimColor} bg={TAG_BG} />
      </>
    );
  }

  /* ────────── 3. TRIANGLE ────────── */
  if (shape === "triangle") {
    return Wrap(
      <>
        <Polygon points="160,40 230,200 90,200" {...main} />
        <Polygon points="160,52 220,193 100,193" {...main} />
        <Line x1={90} y1={215} x2={230} y2={215} {...dim} />
        <Arrowhead x={90} y={215} direction="left" color={dimColor} />
        <Arrowhead x={230} y={215} direction="right" color={dimColor} />
        <DimTag x={160} y={225} text="Base" color={dimColor} bg={TAG_BG} />
        <Line x1={250} y1={40} x2={250} y2={200} {...dim} />
        <Arrowhead x={250} y={40} direction="up" color={dimColor} />
        <Arrowhead x={250} y={200} direction="down" color={dimColor} />
        <DimTag x={272} y={120} text="H" color={dimColor} bg={TAG_BG} />
        <Line x1={155} y1={45} x2={85} y2={200} {...dim} strokeDasharray="4 3" />
        <DimTag x={95} y={110} text="P" color={dimColor} bg={TAG_BG} />
      </>
    );
  }

  /* ────────── 4. ŒIL DE BŒUF ────────── */
  if (shape === "oeil_de_boeuf") {
    return Wrap(
      <>
        <Ellipse cx={160} cy={120} rx={70} ry={80} {...main} />
        <Ellipse cx={160} cy={120} rx={60} ry={70} {...main} />
        <Line x1={90} y1={120} x2={230} y2={120} {...dim} />
        <Arrowhead x={90} y={120} direction="left" color={dimColor} />
        <Arrowhead x={230} y={120} direction="right" color={dimColor} />
        <DimTag x={160} y={108} text="Ø L" color={dimColor} bg={TAG_BG} />
        <Line x1={160} y1={40} x2={160} y2={200} {...dim} />
        <Arrowhead x={160} y={40} direction="up" color={dimColor} />
        <Arrowhead x={160} y={200} direction="down" color={dimColor} />
        <DimTag x={195} y={150} text="Ø H" color={dimColor} bg={TAG_BG} />
      </>
    );
  }

  /* ────────── 5. PORTE D'ENTRÉE ────────── */
  if (shape === "porte_entree") {
    return Wrap(
      <>
        <Rect x={120} y={40} width={80} height={160} {...main} />
        <Rect x={127} y={47} width={66} height={146} {...main} />
        <Line x1={186} y1={115} x2={186} y2={128} stroke={strokeColor} strokeWidth={2.2} strokeLinecap="round" />
        {/* L */}
        <Line x1={120} y1={26} x2={200} y2={26} {...dim} />
        <Arrowhead x={120} y={26} direction="left" color={dimColor} />
        <Arrowhead x={200} y={26} direction="right" color={dimColor} />
        <DimTag x={160} y={16} text="L" color={dimColor} bg={TAG_BG} />
        {/* H */}
        <Line x1={220} y1={40} x2={220} y2={200} {...dim} />
        <Arrowhead x={220} y={40} direction="up" color={dimColor} />
        <Arrowhead x={220} y={200} direction="down" color={dimColor} />
        <DimTag x={245} y={120} text="H" color={dimColor} bg={TAG_BG} />
        {/* Réserve sol */}
        <Line x1={120} y1={215} x2={200} y2={215} {...dim} strokeDasharray="3 3" />
        <DimTag x={160} y={225} text="RS" color={dimColor} bg={TAG_BG} />
      </>
    );
  }

  /* ────────── 6. PORTE DE GARAGE ────────── */
  if (shape === "porte_garage") {
    return Wrap(
      <>
        <Rect x={70} y={50} width={180} height={150} {...main} />
        <Rect x={77} y={57} width={166} height={136} {...main} />
        <Line x1={77} y1={100} x2={243} y2={100} {...main} />
        <Line x1={77} y1={150} x2={243} y2={150} {...main} />
        <Line x1={70} y1={36} x2={250} y2={36} {...dim} />
        <Arrowhead x={70} y={36} direction="left" color={dimColor} />
        <Arrowhead x={250} y={36} direction="right" color={dimColor} />
        <DimTag x={160} y={26} text="L" color={dimColor} bg={TAG_BG} />
        <Line x1={268} y1={50} x2={268} y2={200} {...dim} />
        <Arrowhead x={268} y={50} direction="up" color={dimColor} />
        <Arrowhead x={268} y={200} direction="down" color={dimColor} />
        <DimTag x={290} y={125} text="H" color={dimColor} bg={TAG_BG} />
        <Line x1={70} y1={215} x2={250} y2={215} {...dim} strokeDasharray="3 3" />
        <DimTag x={160} y={225} text="RS" color={dimColor} bg={TAG_BG} />
      </>
    );
  }

  /* ────────── 7. COULISSANT LEVANT ────────── */
  if (shape === "coulissant_levant") {
    return Wrap(
      <>
        <Rect x={50} y={60} width={220} height={140} {...main} />
        <Rect x={57} y={67} width={206} height={126} {...main} />
        <Rect x={64} y={74} width={96} height={112} {...main} />
        <Rect x={160} y={74} width={96} height={112} {...main} />
        <Line x1={72} y1={123} x2={72} y2={137} stroke={strokeColor} strokeWidth={2.2} strokeLinecap="round" />
        <Polyline points="225,130 205,130" stroke={strokeColor} strokeWidth={1.5} fill="none" />
        <Polyline points="210,125 205,130 210,135" stroke={strokeColor} strokeWidth={1.5} fill="none" />
        {/* L */}
        <Line x1={50} y1={46} x2={270} y2={46} {...dim} />
        <Arrowhead x={50} y={46} direction="left" color={dimColor} />
        <Arrowhead x={270} y={46} direction="right" color={dimColor} />
        <DimTag x={160} y={36} text="L" color={dimColor} bg={TAG_BG} />
        {/* H */}
        <Line x1={288} y1={60} x2={288} y2={200} {...dim} />
        <Arrowhead x={288} y={60} direction="up" color={dimColor} />
        <Arrowhead x={288} y={200} direction="down" color={dimColor} />
        <DimTag x={308} y={130} text="H" color={dimColor} bg={TAG_BG} />
        {/* RS */}
        <Line x1={50} y1={215} x2={270} y2={215} {...dim} strokeDasharray="3 3" />
        <DimTag x={160} y={225} text="RS" color={dimColor} bg={TAG_BG} />
      </>
    );
  }

  return null;
};

const styles = StyleSheet.create({
  container: {
    width: "100%",
    aspectRatio: W / H,
    backgroundColor: "#0c0c0c",
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#1f1f1f",
    overflow: "hidden",
    marginVertical: 8,
  },
});

export default MeasureGuide;
