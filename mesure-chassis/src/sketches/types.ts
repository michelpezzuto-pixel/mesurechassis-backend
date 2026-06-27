/**
 * Catalogue officiel des 7 formes de châssis supportées par MesureChassis.
 * Référence visuelle : doc artisan menuisier (line-art noir sur fond clair).
 *
 * NB : Les anciennes formes mentionnées dans une version préliminaire de la
 * MAINTENANCE.md ("ouvrant_1v", "ouvrant_2v", "oscillo_battant", "fixe")
 * sont DÉPRÉCIÉES — utiliser uniquement les 7 clés ci-dessous.
 */

export type ChassisShape =
  | 'rectangulaire'   // Fenêtre fixe rectangulaire (4 carreaux)
  | 'trapeze'         // Trapèze (sommet incliné, 2 vantaux verticaux)
  | 'triangulaire'    // Triangle (2 vantaux séparés par axe vertical)
  | 'oeil_de_boeuf'   // Œil de bœuf (ovale avec croix centrale)
  | 'porte'           // Porte simple (verticale étroite + poignée)
  | 'porte_garage'    // Porte de garage (large + lames horizontales)
  | 'coulissant';     // Coulissant (2 vantaux + flèche directionnelle)

export const CHASSIS_LABEL: Record<ChassisShape, string> = {
  rectangulaire:  'Fenêtre fixe rectangulaire',
  trapeze:        'Trapèze',
  triangulaire:   'Triangulaire',
  oeil_de_boeuf:  'Œil de bœuf',
  porte:          'Porte',
  porte_garage:   'Porte de garage',
  coulissant:     'Coulissant',
};

export const CHASSIS_SHORT: Record<ChassisShape, string> = {
  rectangulaire:  'Rectangulaire',
  trapeze:        'Trapèze',
  triangulaire:   'Triangle',
  oeil_de_boeuf:  'Œil de bœuf',
  porte:          'Porte',
  porte_garage:   'Garage',
  coulissant:     'Coulissant',
};

export interface ChassisSketchProps {
  /** Largeur en pixels — défaut 100 */
  width?: number;
  /** Hauteur en pixels — défaut 100 (sauf porte/garage qui sont plus hauts) */
  height?: number;
  /** Couleur du trait — défaut 'currentColor' (hérite du Text parent) */
  stroke?: string;
  /** Épaisseur du trait — défaut 1.5 */
  strokeWidth?: number;
}
