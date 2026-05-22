// 2D SVG stair elevation sketch
import React from 'react';
import Svg, { Line, Polyline, Rect, Text as SvgText, G } from 'react-native-svg';
import { C } from './theme';

interface Props {
  trueHeight: number;
  reculement: number;
  n: number;
  h: number;
  g: number;
  width?: number;
  height?: number;
  tremieL?: number;
  tremieW?: number;
  limonLength?: number;
}

export default function StairSketch({
  trueHeight, reculement, n, h, g, width = 320, height = 220, tremieL = 0, limonLength,
}: Props) {
  const m = 30;
  const aw = width - 2 * m;
  const ah = height - 2 * m;
  const scale = Math.min(aw / Math.max(reculement, 1), ah / Math.max(trueHeight, 1));
  const sw = reculement * scale;
  const sh = trueHeight * scale;
  const x0 = m;
  const y0 = height - m; // baseline (floor)

  // Steps polyline
  const pts: string[] = [`${x0},${y0}`];
  let cx = x0;
  let cy = y0;
  const hp = sh / n;
  const gp = sw / Math.max(n - 1, 1);
  for (let i = 0; i < n; i++) {
    cy -= hp;
    pts.push(`${cx},${cy}`);
    cx += gp;
    pts.push(`${cx},${cy}`);
  }

  const tremiePx = tremieL > 0 ? tremieL * scale : 0;

  return (
    <Svg width={width} height={height} testID="svg-stair-sketch">
      <Rect x={0} y={0} width={width} height={height} fill={C.CARD} rx={8} />
      {/* Floor line */}
      <Line x1={x0 - 12} y1={y0} x2={x0 + sw + 12} y2={y0} stroke={C.GRAY3} strokeWidth={1.5} />
      {/* Ceiling */}
      <Line x1={x0 - 12} y1={y0 - sh} x2={x0 + sw + 12} y2={y0 - sh} stroke={C.GRAY3} strokeWidth={1} strokeDasharray="4,3" />
      {/* Hypotenuse (slope = limon) */}
      <Line x1={x0} y1={y0} x2={x0 + sw} y2={y0 - sh} stroke={C.ACCENT} strokeWidth={1.5} strokeOpacity={0.6} strokeDasharray="3,3" />
      {limonLength && limonLength > 0 && (
        <SvgText x={x0 + sw / 2 + 8} y={y0 - sh / 2 + 4} fill={C.ACCENT} fontSize="10" fontWeight="bold">
          Limon {Math.round(limonLength)}
        </SvgText>
      )}
      {/* Steps polyline */}
      <Polyline points={pts.join(' ')} fill="none" stroke={C.ACCENT} strokeWidth={2} />
      {/* Trémie */}
      {tremiePx > 0 && (
        <G>
          <Line x1={x0 + sw - tremiePx} y1={y0 - sh} x2={x0 + sw} y2={y0 - sh} stroke={C.WARN} strokeWidth={2.5} />
          <SvgText x={x0 + sw - tremiePx / 2} y={y0 - sh - 6} fill={C.WARN} fontSize="10" textAnchor="middle">
            Trémie
          </SvgText>
        </G>
      )}
      {/* Labels */}
      <SvgText x={x0 + sw / 2} y={y0 + 18} fill={C.GRAY1} fontSize="11" textAnchor="middle" fontWeight="bold">
        Reculement {Math.round(reculement)} mm
      </SvgText>
      <SvgText x={x0 - 8} y={y0 - sh / 2} fill={C.GRAY1} fontSize="11" textAnchor="end" fontWeight="bold">
        H {Math.round(trueHeight)}
      </SvgText>
      <SvgText x={x0 + sw / 2} y={y0 - sh - 14} fill={C.ACCENT} fontSize="11" textAnchor="middle" fontWeight="bold">
        {n} marches · h {Math.round(h)} · g {Math.round(g)}
      </SvgText>
    </Svg>
  );
}
