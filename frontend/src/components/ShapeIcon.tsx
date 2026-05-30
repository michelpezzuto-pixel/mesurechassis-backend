import React from "react";
import Svg, {
  Path,
  Rect,
  Ellipse,
  Line,
  Polygon,
  Polyline,
  G,
} from "react-native-svg";

/**
 * Icônes line-art réalistes des 7 formes de menuiserie.
 *
 * Style : trait fin (1.6) noir au repos (`#101010`), orange (`#FF6B1A` / colors.primary)
 * quand sélectionné. Aucun remplissage — pur dessin de plan d'architecte.
 *
 * Toutes les icônes sont dessinées dans une viewBox 64×64 et le composant
 * gère le scaling via la prop `size`.
 */
export type ShapeKey =
  | "rect"
  | "porte_entree"
  | "porte_garage"
  | "trapeze"
  | "triangle"
  | "oeil_de_boeuf"
  | "coulissant_levant";

/**
 * Récupère la VRAIE forme d'une mesure depuis ses options ou par fallback
 * sur block_type. Privilégie `options.shape` qui contient la valeur exacte
 * (porte_entree, porte_garage, triangle, trapeze…), car block_type est
 * une catégorie générique ("porte" couvre porte d'entrée + garage,
 * "trapeze" couvre trapèze + triangle).
 */
export function blockTypeToShape(
  blockType?: string | null,
  options?: Record<string, any> | null,
): ShapeKey {
  // Priorité 1 : la forme exacte stockée dans options.shape
  const optShape = options?.shape;
  if (optShape) {
    switch (optShape) {
      case "rect":
      case "porte_entree":
      case "porte_garage":
      case "trapeze":
      case "triangle":
      case "oeil_de_boeuf":
      case "coulissant_levant":
        return optShape;
    }
  }
  // Priorité 2 : fallback sur block_type (catégorie générique)
  switch (blockType) {
    case "rect":
    case "standard":
      return "rect";
    case "porte":
    case "porte_entree":
      return "porte_entree";
    case "porte_garage":
      return "porte_garage";
    case "trapeze":
      return "trapeze";
    case "triangle":
      return "triangle";
    case "oeil_de_boeuf":
    case "oeil_boeuf":
      return "oeil_de_boeuf";
    case "coulissant":
    case "coulissant_levant":
      return "coulissant_levant";
    default:
      return "rect"; // fallback safe
  }
}

type Props = {
  shape: ShapeKey;
  size?: number;
  /** Couleur du trait. Default noir profond. */
  color?: string;
  /** Épaisseur du trait. Default 1.6. */
  strokeWidth?: number;
};

const DEFAULT_COLOR = "#101010";

export const ShapeIcon: React.FC<Props> = ({
  shape,
  size = 56,
  color = DEFAULT_COLOR,
  strokeWidth = 1.8,
}) => {
  const common = {
    stroke: color,
    strokeWidth,
    fill: "none",
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
  };

  switch (shape) {
    /* ────────── Fenêtre fixe rectangulaire (4 carreaux) ────────── */
    case "rect":
      return (
        <Svg width={size} height={size} viewBox="0 0 64 64">
          <Rect x="14" y="10" width="36" height="44" rx="0.5" {...common} />
          <Rect x="17" y="13" width="30" height="38" rx="0.5" {...common} />
          <Line x1="32" y1="13" x2="32" y2="51" {...common} />
          <Line x1="17" y1="32" x2="47" y2="32" {...common} />
        </Svg>
      );

    /* ────────── Trapèze (toit en pente + 1 mullion vertical) ────────── */
    case "trapeze":
      return (
        <Svg width={size} height={size} viewBox="0 0 64 64">
          {/* Cadre extérieur trapézoïdal */}
          <Polygon points="13,54 13,18 51,8 51,54" {...common} />
          {/* Cadre intérieur trapézoïdal (offset 3px) */}
          <Polygon points="16,51 16,21 48,12 48,51" {...common} />
          {/* Mullion vertical à 60% */}
          <Line x1="35" y1="14" x2="35" y2="51" {...common} />
        </Svg>
      );

    /* ────────── Triangulaire (isocèle + mullion vertical) ────────── */
    case "triangle":
      return (
        <Svg width={size} height={size} viewBox="0 0 64 64">
          {/* Triangle extérieur */}
          <Polygon points="32,8 54,54 10,54" {...common} />
          {/* Triangle intérieur (épaisseur de cadre) */}
          <Polygon points="32,13 51,52 13,52" {...common} />
          {/* Mullion vertical descendant du sommet */}
          <Line x1="32" y1="13" x2="32" y2="52" {...common} />
        </Svg>
      );

    /* ────────── Œil de bœuf (ovale + croix) ────────── */
    case "oeil_de_boeuf":
      return (
        <Svg width={size} height={size} viewBox="0 0 64 64">
          {/* Ovale extérieur */}
          <Ellipse cx="32" cy="32" rx="20" ry="24" {...common} />
          {/* Ovale intérieur */}
          <Ellipse cx="32" cy="32" rx="17" ry="21" {...common} />
          {/* Croix centrale */}
          <Line x1="15" y1="32" x2="49" y2="32" {...common} />
          <Line x1="32" y1="11" x2="32" y2="53" {...common} />
        </Svg>
      );

    /* ────────── Porte d'entrée (cadre + battant + poignée + seuil) ────────── */
    case "porte_entree":
      return (
        <Svg width={size} height={size} viewBox="0 0 64 64">
          {/* Cadre dormant extérieur */}
          <Rect x="18" y="6" width="28" height="50" rx="0.5" {...common} />
          {/* Cadre dormant intérieur */}
          <Rect x="20" y="8" width="24" height="46" rx="0.5" {...common} />
          {/* Battant (panneau) */}
          <Rect x="23" y="11" width="18" height="40" rx="0.5" {...common} />
          {/* Poignée (verticale petite) */}
          <Line x1="38" y1="31" x2="38" y2="37" {...common} strokeWidth={strokeWidth + 0.6} />
          {/* Seuil bas */}
          <Line x1="20" y1="54" x2="44" y2="54" {...common} />
        </Svg>
      );

    /* ────────── Porte de garage sectionnelle (3 panneaux horizontaux) ────────── */
    case "porte_garage":
      return (
        <Svg width={size} height={size} viewBox="0 0 64 64">
          {/* Cadre extérieur */}
          <Rect x="8" y="10" width="48" height="46" rx="0.5" {...common} />
          {/* Cadre intérieur */}
          <Rect x="11" y="13" width="42" height="40" rx="0.5" {...common} />
          {/* 2 séparateurs horizontaux (3 panneaux) */}
          <Line x1="11" y1="26.5" x2="53" y2="26.5" {...common} />
          <Line x1="11" y1="40" x2="53" y2="40" {...common} />
          {/* Charnières latérales (4 petits cercles/traits) */}
          <Line x1="13" y1="24" x2="13" y2="29" {...common} strokeWidth={strokeWidth + 0.3} />
          <Line x1="13" y1="37.5" x2="13" y2="42.5" {...common} strokeWidth={strokeWidth + 0.3} />
          <Line x1="51" y1="24" x2="51" y2="29" {...common} strokeWidth={strokeWidth + 0.3} />
          <Line x1="51" y1="37.5" x2="51" y2="42.5" {...common} strokeWidth={strokeWidth + 0.3} />
        </Svg>
      );

    /* ────────── Coulissant (2 vantaux + poignée gauche + flèche droite) ────────── */
    case "coulissant_levant":
      return (
        <Svg width={size} height={size} viewBox="0 0 64 64">
          {/* Cadre dormant extérieur */}
          <Rect x="6" y="12" width="52" height="40" rx="0.5" {...common} />
          {/* Cadre dormant intérieur */}
          <Rect x="9" y="15" width="46" height="34" rx="0.5" {...common} />
          {/* Vantail gauche */}
          <Rect x="12" y="18" width="19" height="28" rx="0.5" {...common} />
          {/* Vantail droit */}
          <Rect x="33" y="18" width="19" height="28" rx="0.5" {...common} />
          {/* Poignée gauche (vertical handle) */}
          <Line x1="15" y1="29" x2="15" y2="35" {...common} strokeWidth={strokeWidth + 0.6} />
          {/* Flèche droite indiquant le coulissement (←) sur le vantail droit */}
          <Polyline points="46,32 40,32" {...common} />
          <Polyline points="42,29 40,32 42,35" {...common} />
        </Svg>
      );

    default:
      return null;
  }
};

export default ShapeIcon;
