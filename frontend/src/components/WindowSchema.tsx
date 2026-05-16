import React from "react";
import { View, StyleSheet } from "react-native";
import Svg, { Defs, G, Line, Path, Pattern, Polygon, Rect, Text as SvgText } from "react-native-svg";
import { colors } from "@/src/theme";

const STROKE = "#52525B";
const BLOCK_GREY = "#6B6B6E";
const BLOCK_DARK = "#3F3F46";
const FLOOR_BROWN = "#5A4632";
const FLOOR_TOP = "#8E7A5E";
const SUBFLOOR = "#C5A878";

function MasonryDefs() {
  return (
    <Defs>
      <Pattern id="brick" x={0} y={0} width={32} height={16} patternUnits="userSpaceOnUse">
        <Rect x={0} y={0} width={32} height={16} fill={BLOCK_GREY} />
        <Line x1={0} y1={0} x2={32} y2={0} stroke={BLOCK_DARK} strokeWidth={0.8} />
        <Line x1={16} y1={0} x2={16} y2={8} stroke={BLOCK_DARK} strokeWidth={0.8} />
        <Line x1={0} y1={8} x2={32} y2={8} stroke={BLOCK_DARK} strokeWidth={0.8} />
        <Line x1={8} y1={8} x2={8} y2={16} stroke={BLOCK_DARK} strokeWidth={0.8} />
        <Line x1={24} y1={8} x2={24} y2={16} stroke={BLOCK_DARK} strokeWidth={0.8} />
      </Pattern>
      <Pattern id="subfloor" x={0} y={0} width={10} height={10} patternUnits="userSpaceOnUse">
        <Rect width={10} height={10} fill={SUBFLOOR} />
        <Line x1={0} y1={0} x2={10} y2={10} stroke="#7C5E3A" strokeWidth={0.6} />
      </Pattern>
    </Defs>
  );
}

/**
 * Raw rectangular masonry bay: concrete blocks + lintel + visible sub-floor cross-section.
 * No window, no door, no decoration. Optional live annotations for H/W/D.
 */
export function RawBaySchemaRect({
  size = 320,
  values,
}: {
  size?: number;
  values?: { bay_height?: string; bay_width?: string; bay_diagonal?: string };
}) {
  const w = size;
  const h = size * 0.78;
  const wallT = 30;
  const lintelT = 28;
  const openX = wallT;
  const openY = lintelT;
  const openW = w - wallT * 2;
  const openH = h - lintelT - 60;
  const floorY = h - 60;
  const fmt = (v?: string) => (v && v.trim().length > 0 ? `${v} mm` : "—");
  return (
    <Svg width={w} height={h}>
      <MasonryDefs />
      <Rect x={0} y={0} width={wallT} height={floorY} fill="url(#brick)" stroke={BLOCK_DARK} strokeWidth={1} />
      <Rect x={w - wallT} y={0} width={wallT} height={floorY} fill="url(#brick)" stroke={BLOCK_DARK} strokeWidth={1} />
      <Rect x={0} y={0} width={w} height={lintelT} fill="url(#brick)" stroke={BLOCK_DARK} strokeWidth={1} />
      <Rect x={0} y={floorY} width={w} height={60} fill={FLOOR_BROWN} />
      <Rect x={openX} y={floorY} width={openW} height={14} fill="url(#subfloor)" stroke={BLOCK_DARK} strokeWidth={0.5} />
      <Line x1={openX} y1={floorY + 14} x2={openX + openW} y2={floorY + 14} stroke={FLOOR_TOP} strokeWidth={2} />
      <Rect x={openX} y={openY} width={openW} height={openH} fill="none" stroke={STROKE} strokeWidth={1.2} strokeDasharray="4,3" opacity={0.6} />
      <Line
        x1={openX + 4}
        y1={openY + 4}
        x2={openX + openW - 4}
        y2={openY + openH - 4}
        stroke={colors.primary}
        strokeWidth={1.2}
        strokeDasharray="5,3"
        opacity={0.85}
      />
      {/* Live annotations */}
      <SvgText x={w / 2} y={openY + 16} fontSize={11} fontWeight="800" fill={colors.primary} textAnchor="middle">
        L: {fmt(values?.bay_width)}
      </SvgText>
      <SvgText
        x={openX + 12}
        y={openY + openH / 2}
        fontSize={11}
        fontWeight="800"
        fill={colors.primary}
        textAnchor="start"
      >
        H: {fmt(values?.bay_height)}
      </SvgText>
      <SvgText
        x={openX + openW - 8}
        y={openY + openH - 16}
        fontSize={11}
        fontWeight="800"
        fill={colors.primary}
        textAnchor="end"
      >
        D: {fmt(values?.bay_diagonal)}
      </SvgText>
    </Svg>
  );
}

/**
 * Raw trapezoidal masonry bay (sloped top), same principle.
 */
export function RawBaySchemaTrapeze({
  size = 320,
  values,
}: {
  size?: number;
  values?: { bay_height?: string; bay_width?: string; bay_diagonal?: string };
}) {
  const w = size;
  const h = size * 0.78;
  const wallT = 30;
  const lintelLow = 22;
  const lintelHigh = 90;
  const floorY = h - 60;
  const fmt = (v?: string) => (v && v.trim().length > 0 ? `${v} mm` : "—");
  return (
    <Svg width={w} height={h}>
      <MasonryDefs />
      <Rect x={0} y={lintelLow} width={wallT} height={floorY - lintelLow} fill="url(#brick)" stroke={BLOCK_DARK} strokeWidth={1} />
      <Rect x={w - wallT} y={lintelHigh} width={wallT} height={floorY - lintelHigh} fill="url(#brick)" stroke={BLOCK_DARK} strokeWidth={1} />
      <Polygon
        points={`0,0 ${w},0 ${w},${lintelHigh} 0,${lintelLow}`}
        fill="url(#brick)"
        stroke={BLOCK_DARK}
        strokeWidth={1}
      />
      <Rect x={0} y={floorY} width={w} height={60} fill={FLOOR_BROWN} />
      <Rect x={wallT} y={floorY} width={w - wallT * 2} height={14} fill="url(#subfloor)" stroke={BLOCK_DARK} strokeWidth={0.5} />
      <Line x1={wallT} y1={floorY + 14} x2={w - wallT} y2={floorY + 14} stroke={FLOOR_TOP} strokeWidth={2} />
      <Path
        d={`M ${wallT} ${lintelLow} L ${w - wallT} ${lintelHigh} L ${w - wallT} ${floorY} L ${wallT} ${floorY} Z`}
        fill="none"
        stroke={STROKE}
        strokeWidth={1.2}
        strokeDasharray="4,3"
        opacity={0.6}
      />
      <SvgText x={w / 2} y={(lintelLow + lintelHigh) / 2 + 28} fontSize={11} fontWeight="800" fill={colors.primary} textAnchor="middle">
        L: {fmt(values?.bay_width)}
      </SvgText>
      <SvgText x={wallT + 10} y={(lintelLow + floorY) / 2} fontSize={11} fontWeight="800" fill={colors.primary}>
        H: {fmt(values?.bay_height)}
      </SvgText>
      <SvgText x={w - wallT - 8} y={floorY - 10} fontSize={11} fontWeight="800" fill={colors.primary} textAnchor="end">
        D: {fmt(values?.bay_diagonal)}
      </SvgText>
    </Svg>
  );
}

/**
 * Wall-section visual for the ITE / ITI / CRÉPI cards on Step 3.
 */
export function WallSection({
  variant,
  size = 80,
}: {
  variant: "ite" | "iti" | "crepi";
  size?: number;
}) {
  const w = size;
  const h = size;
  // Layers (left → right): outer | wall | inner
  const layers =
    variant === "ite"
      ? [
          { color: "#C9A36B", width: 18, label: "C" },
          { color: BLOCK_GREY, width: 28, label: "B" },
          { color: SUBFLOOR, width: 12, label: "F" },
        ]
      : variant === "iti"
      ? [
          { color: "#C9A36B", width: 14, label: "C" },
          { color: BLOCK_GREY, width: 28, label: "B" },
          { color: SUBFLOOR, width: 18, label: "I" },
        ]
      : [
          { color: "#C9A36B", width: 14, label: "C" },
          { color: BLOCK_GREY, width: 32, label: "B" },
          { color: "#C9A36B", width: 14, label: "C" },
        ];
  const total = layers.reduce((acc, l) => acc + l.width, 0);
  const scale = (w - 8) / total;
  let x = 4;
  return (
    <Svg width={w} height={h}>
      {layers.map((l) => {
        const lw = l.width * scale;
        const el = (
          <Rect
            key={l.label + x}
            x={x}
            y={10}
            width={lw}
            height={h - 20}
            fill={l.color}
            stroke={BLOCK_DARK}
            strokeWidth={0.8}
          />
        );
        x += lw;
        return el;
      })}
    </Svg>
  );
}

// --- Legacy schemas kept for backward compat (no longer used in the wizard) ---
export type MeasurementValues = Record<string, string>;

const SchemaContainer = ({ children }: { children: React.ReactNode }) => (
  <View style={legacyStyles.wrapper}>{children}</View>
);

export const StandardSchema = ({ values }: { values: MeasurementValues; onChange: (k: string, v: string) => void }) => (
  <SchemaContainer><RawBaySchemaRect /></SchemaContainer>
);
export const CoulissantSchema = StandardSchema;
export const PorteSchema = StandardSchema;
export const TrapezeSchema = ({ values }: { values: MeasurementValues; onChange: (k: string, v: string) => void }) => (
  <SchemaContainer><RawBaySchemaTrapeze /></SchemaContainer>
);

const legacyStyles = StyleSheet.create({
  wrapper: {
    alignSelf: "center",
    backgroundColor: colors.bg,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    padding: 6,
    marginVertical: 8,
  },
});
