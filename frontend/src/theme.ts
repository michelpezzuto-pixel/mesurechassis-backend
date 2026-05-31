export const colors = {
  bg: "#0C0C0E",
  surface: "#18181B",
  surfaceElevated: "#27272A",
  inputBg: "#000000",
  primary: "#FF5A00",
  primaryPressed: "#CC4800",
  anomaly: "#FF3B30",
  warning: "#FFCC00",
  alert: "#FF9F0A",
  success: "#32D74B",
  textPrimary: "#FFFFFF",
  textSecondary: "#A1A1AA",
  placeholder: "#52525B",
  borderSubtle: "#3F3F46",
  borderStrong: "#52525B",
};

// === Pipeline 4 étapes ======================================================
// 1. À mesurer (gris) — créé par l'admin, en attente de prise de cotes
// 2. À vérifier par le technicien (orange) — commercial a clôturé sa partie
// 3. En fabrication (bleu) — technicien a validé les cotes
// 4. Terminé / Livré (vert) — production / pose terminée
//
// Mapping des statuts internes (rétrocompatibilité avec l'existant) :
//   - "a_mesurer", "devis_a_faire"       → étape 1 (measure)
//   - "technique_a_valider", "a_verifier" → étape 2 (verify)
//   - "en_commande", "en_fabrication"    → étape 3 (fab)
//   - "cloture", "termine"               → étape 4 (done)
export type ChantierStage = "measure" | "verify" | "fab" | "done";

export const statusMeta: Record<
  string,
  { label: string; color: string; bg: string; stage: ChantierStage }
> = {
  // Étape 1 — À MESURER (gris)
  a_mesurer: {
    label: "À mesurer",
    color: "#A1A1AA",
    bg: "#27272A",
    stage: "measure",
  },
  // Étape 1bis — DEVIS À FAIRE (créé par Admin, à transmettre au Commercial)
  devis_a_faire: {
    label: "Devis à faire",
    color: "#F59E0B",
    bg: "#3a2400",
    stage: "measure",
  },
  // Étape 2 — À VÉRIFIER PAR LE TECHNICIEN (orange)
  technique_a_valider: {
    label: "À vérifier par le technicien",
    color: "#FF9F0A",
    bg: "#3a2400",
    stage: "verify",
  },
  a_verifier: {
    label: "À vérifier par le technicien",
    color: "#FF9F0A",
    bg: "#3a2400",
    stage: "verify",
  },
  // Étape 3 — EN FABRICATION (bleu)
  en_commande: {
    label: "En fabrication",
    color: "#3B82F6",
    bg: "#0c1f3a",
    stage: "fab",
  },
  en_fabrication: {
    label: "En fabrication",
    color: "#3B82F6",
    bg: "#0c1f3a",
    stage: "fab",
  },
  // Étape 4 — TERMINÉ / LIVRÉ (vert)
  cloture: {
    label: "Terminé / Livré",
    color: "#32D74B",
    bg: "#0e3315",
    stage: "done",
  },
  termine: {
    label: "Terminé / Livré",
    color: "#32D74B",
    bg: "#0e3315",
    stage: "done",
  },
};

// Transitions du pipeline : statut actuel → statut suivant après "Clôturer"
// Workflow Admin/Commercial/Technicien :
//   devis_a_faire (Admin a saisi coordonnées) → a_mesurer (transmis au Commercial)
//   a_mesurer (Commercial a pris les mesures) → technique_a_valider (transmis au Technicien)
//   technique_a_valider (Technicien valide) → en_fabrication
//   en_fabrication (Technicien finalise) → cloture
export const NEXT_STATUS: Record<string, string> = {
  devis_a_faire: "a_mesurer",
  a_mesurer: "technique_a_valider",
  technique_a_valider: "en_fabrication",
  a_verifier: "en_fabrication",
  en_commande: "cloture",
  en_fabrication: "cloture",
  // "cloture" / "termine" → pas de transition (déjà final)
};

// Libellé du bouton "clôture" selon le STATUT actuel (plus précis que par stage)
export const CLOSURE_BUTTON_LABEL_BY_STATUS: Record<string, string> = {
  devis_a_faire: "🚩 Transmettre au commercial pour mesurage",
  a_mesurer: "🚩 Clôturer la prise de cotes",
  technique_a_valider: "🚩 Valider et envoyer en fabrication",
  a_verifier: "🚩 Valider et envoyer en fabrication",
  en_commande: "🚩 Marquer comme terminé / livré",
  en_fabrication: "🚩 Marquer comme terminé / livré",
};

// Description sous le bouton — explique CONCRÈTEMENT ce qui se passe
// après le clic. Permet à l'utilisateur de bien comprendre la transition
// (qui reçoit le chantier ensuite et quelle est l'étape suivante).
export const CLOSURE_DESCRIPTION_BY_STATUS: Record<string, string> = {
  devis_a_faire:
    "Les coordonnées du client sont prêtes. Le chantier passera en « À mesurer » et sera transmis au commercial pour le relevé.",
  a_mesurer:
    "Toutes les ouvertures ont été mesurées. Le chantier passera en « À vérifier par le technicien » pour validation avant fabrication.",
  technique_a_valider:
    "Les mesures sont validées. Le chantier passera en « En fabrication ».",
  a_verifier:
    "Les mesures sont validées. Le chantier passera en « En fabrication ».",
  en_commande:
    "Le chantier est terminé/livré au client. Il sera archivé.",
  en_fabrication:
    "Le chantier est terminé/livré au client. Il sera archivé.",
};

// Compat ancienne API (par stage)
export const CLOSURE_BUTTON_LABEL: Record<string, string> = {
  measure: "🚩 Clôturer la prise de cotes",
  verify: "🚩 Valider et envoyer en fabrication",
  fab: "🚩 Marquer comme terminé / livré",
};

// Qui peut faire la clôture/transition selon le statut courant ?
// Renvoie la liste des rôles autorisés pour faire avancer le pipeline.
export const ROLES_ALLOWED_TO_CLOSE: Record<string, string[]> = {
  devis_a_faire: ["admin"],
  a_mesurer: ["commercial", "admin"],
  technique_a_valider: ["technician"],
  a_verifier: ["technician"],
  en_commande: ["technician"],
  en_fabrication: ["technician"],
};

export const READY_FOR_EXPORT_BADGE = {
  label: "✓ Prêt pour Export",
  color: "#32D74B",
  bg: "#0e3315",
};

export const blockMeta: Record<string, { label: string; icon: string }> = {
  standard: { label: "Standard", icon: "square-outline" },
  coulissant: { label: "Coulissant", icon: "swap-horizontal" },
  porte: { label: "Porte", icon: "exit-outline" },
  trapeze: { label: "Trapèze", icon: "triangle-outline" },
};

// Labels précis par forme (options.shape) — affichés en priorité dans la liste
// des mesures. block_type étant générique ("porte" = porte d'entrée OU
// porte de garage), on lit options.shape pour distinguer.
export const shapeMeta: Record<string, { label: string }> = {
  rect: { label: "Rectangle / Carré" },
  porte_entree: { label: "Porte d'entrée" },
  porte_garage: { label: "Porte de garage" },
  trapeze: { label: "Trapèze" },
  triangle: { label: "Triangle" },
  oeil_de_boeuf: { label: "Œil-de-bœuf" },
  coulissant_levant: { label: "Coulissant levant" },
};

/**
 * Retourne le libellé contextuel d'un statut selon le type de compte.
 * En mode Artisan, "technique_a_valider" est renommé en "Encodage bureau"
 * (pas de technicien dédié, l'artisan saisit lui-même la commande).
 */
export function getStatusLabel(
  status: string,
  accountType?: string | null,
): string {
  const isArtisan = (accountType || "").toLowerCase() === "artisan";
  if (isArtisan) {
    const ARTISAN_LABELS: Record<string, string> = {
      devis_a_faire: "Coordonnées validées",
      a_mesurer: "À mesurer",
      technique_a_valider: "Encodage bureau",
      a_verifier: "Encodage bureau",
      en_fabrication: "En fabrication",
      en_commande: "En fabrication",
      cloture: "Terminé / Livré",
      termine: "Terminé / Livré",
    };
    if (ARTISAN_LABELS[status]) return ARTISAN_LABELS[status];
  }
  return statusMeta[status]?.label ?? status;
}
