/**
 * PlanSketch — Vue en plan (top-down) de l'escalier selon `shape_key`.
 *
 * Représentations simplifiées :
 *  - droit : rectangle vertical (largeur × reculement) + lignes de nez de marches
 *  - quart_bas : L (palier balancé en bas)
 *  - quart_haut : L inversé (palier balancé en haut)
 *  - double_quart : U (2 paliers)
 *  - helicoidal : cercle + secteurs angulaires (rond)
 *
 * Cotations : largeur totale, largeur de marche, jour entre volées le cas échéant.
 */
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import Svg, { Rect, Line, Circle, Path, G, Text as SvgText, Polygon, Polyline } from 'react-native-svg';
import { C, FONT, SP } from './theme';

export type ShapeKey = 'droit' | 'quart_bas' | 'quart_haut' | 'double_quart' | 'helicoidal';

interface Props {
  shapeKey: ShapeKey;
  n: number;
  reculement: number;     // mm — longueur dispo
  largeurVolee: number;   // mm — largeur utile escalier
  jourEscalier: number;   // mm — espace entre les 2 volées en tournant
  height?: number;
}

const ACCENT = C.ACCENT;
const PADDING = 32;

function fmt(mm: number): string {
  return `${Math.round(mm)} mm`;
}

function PlanSketchInner({
  shapeKey,
  n,
  reculement,
  largeurVolee,
  jourEscalier,
  height = 320,
}: Props) {
  const W = 360;
  const H = height;

  // Compute scale: bounding box depends on shape
  let bboxW = largeurVolee + 80;
  let bboxH = reculement + 80;
  if (shapeKey === 'quart_bas' || shapeKey === 'quart_haut') {
    // L-shape : roughly square with side = reculement * 0.7
    const side = Math.max(reculement * 0.7, largeurVolee * 2 + jourEscalier);
    bboxW = side + 80;
    bboxH = side + 80;
  } else if (shapeKey === 'double_quart') {
    const side = Math.max(largeurVolee * 2 + jourEscalier, reculement * 0.5);
    bboxW = side + 80;
    bboxH = side + 80;
  } else if (shapeKey === 'helicoidal') {
    const diam = largeurVolee * 2.2;
    bboxW = diam + 80;
    bboxH = diam + 80;
  }
  const scale = Math.min((W - PADDING * 2) / bboxW, (H - PADDING * 2) / bboxH);

  return (
    <View style={styles.wrap}>
      <Svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}>
        {/* Background */}
        <Rect x={0} y={0} width={W} height={H} fill={C.BG_DEEPER} rx={12} />

        {shapeKey === 'droit' && (
          <DroitView
            W={W} H={H} scale={scale}
            n={n} reculement={reculement} largeurVolee={largeurVolee}
          />
        )}
        {(shapeKey === 'quart_bas' || shapeKey === 'quart_haut') && (
          <QuartView
            W={W} H={H} scale={scale} variant={shapeKey}
            n={n} reculement={reculement}
            largeurVolee={largeurVolee} jourEscalier={jourEscalier}
          />
        )}
        {shapeKey === 'double_quart' && (
          <DoubleQuartView
            W={W} H={H} scale={scale}
            n={n} reculement={reculement}
            largeurVolee={largeurVolee} jourEscalier={jourEscalier}
          />
        )}
        {shapeKey === 'helicoidal' && (
          <HelicoidalView
            W={W} H={H} n={n} largeurVolee={largeurVolee}
          />
        )}

        {/* Compass */}
        <G x={W - 50} y={30}>
          <Circle cx={0} cy={0} r={18} fill="transparent" stroke={C.GRAY3} strokeWidth={1} />
          <Line x1={0} y1={-14} x2={0} y2={14} stroke={C.GRAY3} strokeWidth={1} />
          <Line x1={-14} y1={0} x2={14} y2={0} stroke={C.GRAY3} strokeWidth={1} />
          <SvgText x={0} y={-20} fontSize={10} fill={C.GRAY3} textAnchor="middle">N</SvgText>
        </G>
      </Svg>

      <Text style={styles.legend}>
        Vue en plan (de dessus) · {n} marches · L. volée {fmt(largeurVolee)}
        {shapeKey !== 'droit' && shapeKey !== 'helicoidal' && ` · Jour ${fmt(jourEscalier)}`}
      </Text>
    </View>
  );
}

// ── Helper sub-views ────────────────────────────────────────────────────────

function DroitView({ W, H, scale, n, reculement, largeurVolee }: any) {
  const w = largeurVolee * scale;
  const h = reculement * scale;
  const cx = W / 2;
  const cy = H / 2;
  const x0 = cx - w / 2;
  const y0 = cy - h / 2;
  const stepH = h / n;
  const lines = [];
  for (let i = 1; i < n; i++) {
    lines.push(
      <Line key={i} x1={x0} y1={y0 + stepH * i} x2={x0 + w} y2={y0 + stepH * i}
            stroke={C.ACCENT} strokeWidth={1} opacity={0.85} />,
    );
  }
  // Arrow up = direction de la montée
  return (
    <G>
      <Rect x={x0} y={y0} width={w} height={h} fill="rgba(140,198,63,0.06)" stroke={ACCENT} strokeWidth={1.5} />
      {lines}
      {/* Step numbers (every 3) */}
      {Array.from({ length: n }, (_, i) => i).filter(i => (i + 1) % 3 === 0).map(i => (
        <SvgText key={`lbl-${i}`} x={x0 + w + 6} y={y0 + stepH * (i + 0.5) + 3} fontSize={9} fill={C.GRAY3}>
          {i + 1}
        </SvgText>
      ))}
      {/* Direction arrow (montée vers le haut) */}
      <Polygon
        points={`${cx - 6},${y0 + 15} ${cx + 6},${y0 + 15} ${cx},${y0 + 5}`}
        fill={ACCENT}
      />
      <SvgText x={cx} y={y0 + 28} fontSize={9} fill={C.ACCENT} textAnchor="middle">MONTÉE</SvgText>

      {/* Width cotation (bottom) */}
      <Line x1={x0} y1={y0 + h + 14} x2={x0 + w} y2={y0 + h + 14} stroke={C.GRAY3} strokeWidth={0.8} />
      <Line x1={x0} y1={y0 + h + 10} x2={x0} y2={y0 + h + 18} stroke={C.GRAY3} strokeWidth={0.8} />
      <Line x1={x0 + w} y1={y0 + h + 10} x2={x0 + w} y2={y0 + h + 18} stroke={C.GRAY3} strokeWidth={0.8} />
      <SvgText x={cx} y={y0 + h + 26} fontSize={10} fill={C.WHITE} textAnchor="middle">{fmt(largeurVolee)}</SvgText>

      {/* Length cotation (right) */}
      <Line x1={x0 + w + 30} y1={y0} x2={x0 + w + 30} y2={y0 + h} stroke={C.GRAY3} strokeWidth={0.8} />
      <SvgText x={x0 + w + 38} y={y0 + h / 2 + 3} fontSize={10} fill={C.WHITE} transform={`rotate(90 ${x0 + w + 38} ${y0 + h / 2 + 3})`}>
        {fmt(reculement)}
      </SvgText>
    </G>
  );
}

function QuartView({ W, H, scale, variant, n, reculement, largeurVolee, jourEscalier }: any) {
  // L shape : 2 volées perpendiculaires, palier balancé au coin
  // Compute proportions: 2/3 of steps on long branch, 1/3 short branch
  const longLen = reculement * 0.7;
  const shortLen = longLen * 0.55;
  const cx = W / 2;
  const cy = H / 2;
  const wV = largeurVolee * scale; // largeur volée
  const longSc = longLen * scale;
  const shortSc = shortLen * scale;
  // L shape orientation: quart_bas = palier en bas-gauche, quart_haut = palier en haut-gauche
  const isBas = variant === 'quart_bas';
  const corner = { x: cx - longSc / 2, y: isBas ? cy + shortSc / 2 : cy - shortSc / 2 };
  // Long branch goes vertically (down→up)
  const longRect = { x: corner.x, y: isBas ? corner.y - longSc : corner.y, w: wV, h: longSc };
  // Short branch goes horizontally
  const shortRect = { x: corner.x, y: isBas ? corner.y - wV : corner.y, w: shortSc, h: wV };
  // Step lines on long branch (vertical)
  const nLong = Math.round(n * 0.65);
  const nShort = n - nLong - 3; // 3 marches balancées dans le coin
  const stepLong = longRect.h / Math.max(nLong, 1);
  const stepShort = shortRect.w / Math.max(nShort, 1);
  return (
    <G>
      <Rect x={longRect.x} y={longRect.y} width={longRect.w} height={longRect.h}
            fill="rgba(140,198,63,0.06)" stroke={ACCENT} strokeWidth={1.5} />
      <Rect x={shortRect.x} y={shortRect.y} width={shortRect.w} height={shortRect.h}
            fill="rgba(140,198,63,0.06)" stroke={ACCENT} strokeWidth={1.5} />
      {/* Long branch step lines */}
      {Array.from({ length: nLong - 1 }, (_, i) => (
        <Line key={`l-${i}`}
              x1={longRect.x} y1={longRect.y + stepLong * (i + 1)}
              x2={longRect.x + longRect.w} y2={longRect.y + stepLong * (i + 1)}
              stroke={ACCENT} strokeWidth={1} opacity={0.7} />
      ))}
      {/* Short branch step lines */}
      {Array.from({ length: nShort - 1 }, (_, i) => (
        <Line key={`s-${i}`}
              x1={shortRect.x + stepShort * (i + 1)} y1={shortRect.y}
              x2={shortRect.x + stepShort * (i + 1)} y2={shortRect.y + shortRect.h}
              stroke={ACCENT} strokeWidth={1} opacity={0.7} />
      ))}
      {/* Balancing radial lines at corner (3 marches dansantes) */}
      <BalanceFan
        cx={isBas ? corner.x + wV / 2 : corner.x + wV / 2}
        cy={isBas ? corner.y - wV / 2 : corner.y + wV / 2}
        r={wV * 0.95}
        nFan={3}
        flip={!isBas}
      />
      {/* Cotations */}
      <SvgText x={longRect.x + longRect.w / 2} y={longRect.y - 6}
               fontSize={10} fill={C.WHITE} textAnchor="middle">{fmt(largeurVolee)}</SvgText>
      <SvgText x={shortRect.x + shortRect.w + 6} y={shortRect.y + shortRect.h / 2 + 3}
               fontSize={9} fill={C.GRAY3}>L. volée</SvgText>
    </G>
  );
}

function BalanceFan({ cx, cy, r, nFan, flip }: any) {
  // 3 lignes radiales depuis le centre formant un éventail de balancement
  const angles = [25, 50, 75]; // degrees from horizontal
  return (
    <G>
      {angles.map((deg, i) => {
        const a = (flip ? 180 - deg : deg) * Math.PI / 180;
        const x = cx + Math.cos(a) * r;
        const y = cy - Math.sin(a) * r;
        return <Line key={i} x1={cx} y1={cy} x2={x} y2={y} stroke={ACCENT} strokeWidth={1.2} opacity={0.85} />;
      })}
      <Circle cx={cx} cy={cy} r={3} fill={ACCENT} />
    </G>
  );
}

function DoubleQuartView({ W, H, scale, n, reculement, largeurVolee, jourEscalier }: any) {
  // U shape : 2 volées parallèles + 1 palier au sommet, avec jour au milieu
  const cx = W / 2;
  const cy = H / 2;
  const wV = largeurVolee * scale;
  const jour = jourEscalier * scale;
  const longLen = reculement * 0.5;
  const longSc = longLen * scale;
  const totalW = wV * 2 + jour;
  const x0 = cx - totalW / 2;
  // Left volée going up, right volée going down (back), top palier
  return (
    <G>
      {/* Left volée */}
      <Rect x={x0} y={cy - longSc / 2} width={wV} height={longSc}
            fill="rgba(140,198,63,0.06)" stroke={ACCENT} strokeWidth={1.5} />
      {/* Right volée */}
      <Rect x={x0 + wV + jour} y={cy - longSc / 2} width={wV} height={longSc}
            fill="rgba(140,198,63,0.06)" stroke={ACCENT} strokeWidth={1.5} />
      {/* Top palier */}
      <Rect x={x0} y={cy - longSc / 2 - wV} width={totalW} height={wV}
            fill="rgba(140,198,63,0.06)" stroke={ACCENT} strokeWidth={1.5} />
      {/* Step lines on both volées */}
      {Array.from({ length: Math.round(n / 2) - 1 }, (_, i) => {
        const step = longSc / (n / 2);
        const y = cy - longSc / 2 + step * (i + 1);
        return (
          <G key={i}>
            <Line x1={x0} y1={y} x2={x0 + wV} y2={y} stroke={ACCENT} strokeWidth={1} opacity={0.7} />
            <Line x1={x0 + wV + jour} y1={y} x2={x0 + totalW} y2={y} stroke={ACCENT} strokeWidth={1} opacity={0.7} />
          </G>
        );
      })}
      {/* Jour cotation */}
      <SvgText x={cx} y={cy + 4} fontSize={10} fill={C.WARN} textAnchor="middle">
        JOUR {fmt(jourEscalier)}
      </SvgText>
      {/* Width cotation */}
      <SvgText x={cx} y={cy + longSc / 2 + 20} fontSize={10} fill={C.WHITE} textAnchor="middle">
        L. totale {fmt(largeurVolee * 2 + jourEscalier)}
      </SvgText>
    </G>
  );
}

function HelicoidalView({ W, H, n, largeurVolee }: any) {
  const cx = W / 2;
  const cy = H / 2;
  const rOuter = Math.min(W, H) / 2.5;
  const rInner = rOuter * 0.4;
  // Marches radiales : 360°/n
  const arc = 360 / n;
  const lines = [];
  for (let i = 0; i < n; i++) {
    const angle = (i * arc * Math.PI) / 180;
    const x1 = cx + Math.cos(angle) * rInner;
    const y1 = cy + Math.sin(angle) * rInner;
    const x2 = cx + Math.cos(angle) * rOuter;
    const y2 = cy + Math.sin(angle) * rOuter;
    lines.push(<Line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke={ACCENT} strokeWidth={1.2} />);
  }
  return (
    <G>
      <Circle cx={cx} cy={cy} r={rOuter} fill="rgba(140,198,63,0.06)" stroke={ACCENT} strokeWidth={1.5} />
      <Circle cx={cx} cy={cy} r={rInner} fill={C.BG_DEEPER} stroke={ACCENT} strokeWidth={1.5} />
      {lines}
      <SvgText x={cx} y={cy + 4} fontSize={10} fill={C.WHITE} textAnchor="middle">⌀ {fmt(largeurVolee * 2.2)}</SvgText>
    </G>
  );
}

const styles = StyleSheet.create({
  wrap: { alignItems: 'center' },
  legend: { ...FONT.small, fontSize: 11, marginTop: SP.sm, textAlign: 'center' },
});

// React.memo : ne re-render que si une vraie prop a changé (toggle / forme / largeur / jour)
const PlanSketch = React.memo(PlanSketchInner);
export default PlanSketch;
