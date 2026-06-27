/**
 * Catalogue des 7 sketches line-art réutilisables des formes de châssis.
 *
 * Tous les composants :
 *   - Utilisent `react-native-svg` (compatible Expo & React Native)
 *   - Acceptent les props `width`, `height`, `stroke`, `strokeWidth`
 *   - viewBox normalisé : carré 100×100 (sauf porte/garage en 80×120)
 *   - Pas de remplissage (fill="none") — traits noirs uniquement, conforme à la
 *     planche fournie par l'artisan
 *
 * Usage :
 *   import { ChassisSketch } from '@/src/sketches';
 *   <ChassisSketch shape="rectangulaire" width={80} height={80} />
 *
 * Ou import direct :
 *   import { ChassisRectangulaire } from '@/src/sketches';
 *   <ChassisRectangulaire width={80} height={80} />
 */

import React from 'react';
import Svg, { Path, Line, Rect, Ellipse, Polygon } from 'react-native-svg';
import { ChassisShape, ChassisSketchProps } from './types';

// ─── Helper : props par défaut ──────────────────────────────────────────────
const defaults = (p: ChassisSketchProps) => ({
  width: p.width ?? 100,
  height: p.height ?? 100,
  stroke: p.stroke ?? 'currentColor',
  strokeWidth: p.strokeWidth ?? 1.5,
});

// ─── 1. Fenêtre fixe rectangulaire ──────────────────────────────────────────
//     Cadre extérieur + cadre intérieur double + croix centrale (4 carreaux)
export function ChassisRectangulaire(p: ChassisSketchProps) {
  const { width, height, stroke, strokeWidth } = defaults(p);
  return (
    <Svg width={width} height={height} viewBox="0 0 100 100" fill="none">
      {/* Cadre extérieur épais (double trait) */}
      <Rect x={10} y={5}  width={80} height={90} stroke={stroke} strokeWidth={strokeWidth} />
      <Rect x={14} y={9}  width={72} height={82} stroke={stroke} strokeWidth={strokeWidth} />
      {/* Croix centrale formant 4 carreaux */}
      <Line x1={50} y1={9}  x2={50} y2={91} stroke={stroke} strokeWidth={strokeWidth} />
      <Line x1={14} y1={50} x2={86} y2={50} stroke={stroke} strokeWidth={strokeWidth} />
    </Svg>
  );
}

// ─── 2. Trapèze ─────────────────────────────────────────────────────────────
//     Rectangle dont le sommet est incliné (toit en pente)
//     Deux vantaux verticaux séparés par un montant
export function ChassisTrapeze(p: ChassisSketchProps) {
  const { width, height, stroke, strokeWidth } = defaults(p);
  return (
    <Svg width={width} height={height} viewBox="0 0 100 100" fill="none">
      {/* Cadre extérieur en trapèze (sommet gauche bas → sommet droit haut) */}
      <Polygon points="10,15 90,5 90,95 10,95" stroke={stroke} strokeWidth={strokeWidth} />
      {/* Cadre intérieur (légèrement réduit) */}
      <Polygon points="14,18 86,9 86,91 14,91" stroke={stroke} strokeWidth={strokeWidth} />
      {/* Montant vertical central */}
      <Line x1={50} y1={12} x2={50} y2={91} stroke={stroke} strokeWidth={strokeWidth} />
    </Svg>
  );
}

// ─── 3. Triangulaire ────────────────────────────────────────────────────────
//     Triangle isocèle pointe en haut, deux vantaux séparés par axe vertical
export function ChassisTriangulaire(p: ChassisSketchProps) {
  const { width, height, stroke, strokeWidth } = defaults(p);
  return (
    <Svg width={width} height={height} viewBox="0 0 100 100" fill="none">
      {/* Triangle extérieur */}
      <Polygon points="50,5 90,95 10,95" stroke={stroke} strokeWidth={strokeWidth} />
      {/* Triangle intérieur (cadre) */}
      <Polygon points="50,12 85,91 15,91" stroke={stroke} strokeWidth={strokeWidth} />
      {/* Axe central vertical */}
      <Line x1={50} y1={12} x2={50} y2={91} stroke={stroke} strokeWidth={strokeWidth} />
    </Svg>
  );
}

// ─── 4. Œil de bœuf ─────────────────────────────────────────────────────────
//     Ellipse verticale + ellipse intérieure + croix centrale
export function ChassisOeilDeBoeuf(p: ChassisSketchProps) {
  const { width, height, stroke, strokeWidth } = defaults(p);
  return (
    <Svg width={width} height={height} viewBox="0 0 100 100" fill="none">
      {/* Ellipse extérieure */}
      <Ellipse cx={50} cy={50} rx={35} ry={45} stroke={stroke} strokeWidth={strokeWidth} />
      {/* Ellipse intérieure (cadre) */}
      <Ellipse cx={50} cy={50} rx={31} ry={41} stroke={stroke} strokeWidth={strokeWidth} />
      {/* Croix centrale */}
      <Line x1={50} y1={9}  x2={50} y2={91} stroke={stroke} strokeWidth={strokeWidth} />
      <Line x1={19} y1={50} x2={81} y2={50} stroke={stroke} strokeWidth={strokeWidth} />
    </Svg>
  );
}

// ─── 5. Porte ───────────────────────────────────────────────────────────────
//     Verticale étroite + cadre intérieur + poignée à droite + seuil bas
export function ChassisPorte(p: ChassisSketchProps) {
  const { width, height, stroke, strokeWidth } = defaults(p);
  return (
    <Svg width={width} height={height} viewBox="0 0 80 120" fill="none">
      {/* Cadre extérieur porte */}
      <Rect x={10} y={5}  width={60} height={108} stroke={stroke} strokeWidth={strokeWidth} />
      {/* Panneau intérieur */}
      <Rect x={16} y={11} width={48} height={92}  stroke={stroke} strokeWidth={strokeWidth} />
      {/* Poignée (côté droit, à mi-hauteur) */}
      <Line x1={58} y1={60} x2={58} y2={72} stroke={stroke} strokeWidth={strokeWidth + 0.5} strokeLinecap="round" />
      <Line x1={56} y1={60} x2={60} y2={60} stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" />
      {/* Seuil bas */}
      <Line x1={10} y1={113} x2={70} y2={113} stroke={stroke} strokeWidth={strokeWidth} />
      <Rect x={14} y={107} width={52} height={6} stroke={stroke} strokeWidth={strokeWidth} />
    </Svg>
  );
}

// ─── 6. Porte de garage ─────────────────────────────────────────────────────
//     Large rectangulaire + lames horizontales équidistantes (sectional)
export function ChassisPorteGarage(p: ChassisSketchProps) {
  const { width, height, stroke, strokeWidth } = defaults(p);
  return (
    <Svg width={width} height={height} viewBox="0 0 120 100" fill="none">
      {/* Cadre extérieur garage */}
      <Rect x={10} y={5}  width={100} height={90} stroke={stroke} strokeWidth={strokeWidth} />
      {/* Cadre intérieur */}
      <Rect x={14} y={9}  width={92}  height={82} stroke={stroke} strokeWidth={strokeWidth} />
      {/* 3 lames horizontales (sections) */}
      <Line x1={14} y1={30} x2={106} y2={30} stroke={stroke} strokeWidth={strokeWidth} />
      <Line x1={14} y1={50} x2={106} y2={50} stroke={stroke} strokeWidth={strokeWidth} />
      <Line x1={14} y1={70} x2={106} y2={70} stroke={stroke} strokeWidth={strokeWidth} />
      {/* Petits cercles charnières gauche */}
      <Rect x={11} y={28}  width={3} height={4} stroke={stroke} strokeWidth={strokeWidth - 0.3} />
      <Rect x={11} y={48}  width={3} height={4} stroke={stroke} strokeWidth={strokeWidth - 0.3} />
      <Rect x={11} y={68}  width={3} height={4} stroke={stroke} strokeWidth={strokeWidth - 0.3} />
      {/* Symétriques droite */}
      <Rect x={106} y={28} width={3} height={4} stroke={stroke} strokeWidth={strokeWidth - 0.3} />
      <Rect x={106} y={48} width={3} height={4} stroke={stroke} strokeWidth={strokeWidth - 0.3} />
      <Rect x={106} y={68} width={3} height={4} stroke={stroke} strokeWidth={strokeWidth - 0.3} />
    </Svg>
  );
}

// ─── 7. Coulissant ──────────────────────────────────────────────────────────
//     Deux vantaux côte à côte, poignée gauche, flèche directionnelle droite
export function ChassisCoulissant(p: ChassisSketchProps) {
  const { width, height, stroke, strokeWidth } = defaults(p);
  return (
    <Svg width={width} height={height} viewBox="0 0 120 100" fill="none">
      {/* Cadre extérieur */}
      <Rect x={6}  y={5}  width={108} height={90} stroke={stroke} strokeWidth={strokeWidth} />
      <Rect x={10} y={9}  width={100} height={82} stroke={stroke} strokeWidth={strokeWidth} />
      {/* Vantail gauche */}
      <Rect x={14} y={13} width={44}  height={74} stroke={stroke} strokeWidth={strokeWidth} />
      {/* Vantail droit */}
      <Rect x={62} y={13} width={44}  height={74} stroke={stroke} strokeWidth={strokeWidth} />
      {/* Poignée vantail gauche (côté intérieur droit du vantail) */}
      <Line x1={52} y1={45} x2={52} y2={57} stroke={stroke} strokeWidth={strokeWidth + 0.5} strokeLinecap="round" />
      {/* Flèche directionnelle vers la gauche, sur le vantail droit */}
      <Line x1={92} y1={50} x2={76} y2={50} stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" />
      <Path d="M 76,50 L 81,45 M 76,50 L 81,55" stroke={stroke} strokeWidth={strokeWidth} fill="none" strokeLinecap="round" />
    </Svg>
  );
}

// ─── Registry + helper sélecteur ────────────────────────────────────────────
export const CHASSIS_SKETCHES: Record<ChassisShape, React.FC<ChassisSketchProps>> = {
  rectangulaire:  ChassisRectangulaire,
  trapeze:        ChassisTrapeze,
  triangulaire:   ChassisTriangulaire,
  oeil_de_boeuf:  ChassisOeilDeBoeuf,
  porte:          ChassisPorte,
  porte_garage:   ChassisPorteGarage,
  coulissant:     ChassisCoulissant,
};

/**
 * Composant générique : choisit le sketch par shape key.
 * Préférez celui-ci dans les listes/dictionnaires plutôt qu'un switch.
 */
export function ChassisSketch(
  props: ChassisSketchProps & { shape: ChassisShape },
) {
  const Cmp = CHASSIS_SKETCHES[props.shape];
  if (!Cmp) return null;
  return <Cmp {...props} />;
}

export * from './types';
