/**
 * perimeter.ts — Calcul du périmètre total des formes complexes.
 *
 * Le but : permettre au mesureur de vérifier sur le terrain avec son mètre
 * ruban en faisant le tour COMPLET de la baie. La valeur calculée par
 * l'application sert de point de comparaison.
 *
 * Toutes les fonctions renvoient un périmètre en millimètres (mm), arrondi
 * à l'entier le plus proche. Renvoient `null` si les données sont
 * incomplètes ou incohérentes.
 */

/**
 * Plein cintre — Demi-cercle parfait au sommet (R = L/2).
 *
 * Contour total = 2 × H1 (les deux jambages verticaux)
 *               + L (la base horizontale)
 *               + π × L / 2 (le demi-cercle au sommet)
 */
export function perimeterPleinCintre(
  L: number | null | undefined,
  H1: number | null | undefined,
): number | null {
  if (!L || !H1 || L <= 0 || H1 <= 0) return null;
  const arc = Math.PI * (L / 2);
  return Math.round(2 * H1 + L + arc);
}

/**
 * Arc surbaissé — Arc applati (flèche f < L/2).
 *
 * Géométrie : segment de cercle de corde L et flèche f.
 *   - Rayon R = (L² + 4f²) / (8f)
 *   - Angle au centre θ = 2 × asin(L / (2R))
 *   - Longueur de l'arc = R × θ
 *
 * Contour total = 2 × H1 + L + longueur de l'arc.
 *
 * H2 = hauteur totale (au sommet de l'arc).
 * f = H2 - H1.
 */
export function perimeterArcSurbaisse(
  L: number | null | undefined,
  H1: number | null | undefined,
  H2: number | null | undefined,
): number | null {
  if (!L || !H1 || !H2 || L <= 0 || H1 <= 0 || H2 <= 0) return null;
  const fleche = H2 - H1;
  if (fleche <= 0 || fleche >= L / 2) return null;
  const R = (L * L + 4 * fleche * fleche) / (8 * fleche);
  const theta = 2 * Math.asin(L / (2 * R));
  const arc = R * theta;
  return Math.round(2 * H1 + L + arc);
}

/**
 * Angle 90° — Châssis rectangulaire avec un (ou deux) pan(s) coupé(s).
 *
 * Paramètres :
 *   - L            : largeur totale du cadre (mm)
 *   - Hleft, Hright : hauteurs gauche et droite (mm). Si symétrique, mettre
 *                    la même valeur dans les deux.
 *   - cutW, cutH    : dimensions du pan coupé (largeur × hauteur)
 *   - side          : 'right' | 'left' | 'both'
 *
 * Le pan coupé crée une oblique de longueur √(cutW² + cutH²) qui remplace
 * un coin (cutW horizontal + cutH vertical retirés).
 *
 *   Périmètre nominal d'un rectangle = 2L + 2H
 *   Pour chaque côté coupé : on retire (cutW + cutH) et on ajoute √(cutW²+cutH²)
 *
 * En cas de hauteur asymétrique, on prend H_left pour le jambage gauche et
 * H_right pour le jambage droit. La base reste L et le sommet est
 * légèrement oblique (entre H_left et H_right). Pour rester simple, on
 * approxime le sommet par une ligne droite de longueur
 *   √(L² + (Hleft − Hright)²)
 * ce qui est exact pour une géométrie en trapèze.
 */
export function perimeterAngle90(
  L: number | null | undefined,
  Hleft: number | null | undefined,
  Hright: number | null | undefined,
  cutW: number | null | undefined,
  cutH: number | null | undefined,
  side: "left" | "right" | "both",
): number | null {
  if (!L || !Hleft || !Hright || L <= 0 || Hleft <= 0 || Hright <= 0) {
    return null;
  }
  const cW = cutW || 0;
  const cH = cutH || 0;
  if (cW <= 0 || cH <= 0) return null;
  // garde-fou : le pan ne peut pas dépasser le cadre
  if (cW >= L) return null;
  if (cH >= Math.min(Hleft, Hright)) return null;

  // Base (en bas) — toujours pleine longueur L
  const base = L;
  // Sommet — légère oblique si Hleft ≠ Hright (sinon = L)
  const topSpan = Math.sqrt(L * L + Math.pow(Hleft - Hright, 2));

  // Jambages :
  //  - côté gauche = Hleft, sauf si pan à gauche (on retire cH)
  //  - côté droit  = Hright, sauf si pan à droite (on retire cH)
  const leftVert = side === "left" || side === "both" ? Hleft - cH : Hleft;
  const rightVert =
    side === "right" || side === "both" ? Hright - cH : Hright;

  // Sommet effectif après coupe :
  //  - 1 pan : on retire cW du sommet et on ajoute l'oblique
  //  - 2 pans : on retire 2 × cW et on ajoute 2 obliques
  const oblique = Math.sqrt(cW * cW + cH * cH);
  let topEffective: number;
  let obliqueTotal: number;
  if (side === "both") {
    topEffective = Math.max(0, topSpan - 2 * cW);
    obliqueTotal = 2 * oblique;
  } else {
    topEffective = Math.max(0, topSpan - cW);
    obliqueTotal = oblique;
  }

  const total = base + leftVert + rightVert + topEffective + obliqueTotal;
  return Math.round(total);
}

/**
 * Tolérance pour la vérification mesurée vs calculée.
 * Sur le terrain, ±1 % ou ±15 mm minimum (le mètre ruban a une précision
 * limitée et l'arc peut être légèrement déformé par le ruban).
 */
export function withinTolerance(
  measured: number,
  computed: number,
): boolean {
  const diff = Math.abs(measured - computed);
  const tol = Math.max(15, computed * 0.01);
  return diff <= tol;
}

/** Formate un périmètre en mm pour l'affichage (ex. "7 250 mm"). */
export function formatPerimeter(mm: number | null): string {
  if (mm === null || !Number.isFinite(mm)) return "—";
  return `${mm.toLocaleString("fr-FR")} mm`;
}
