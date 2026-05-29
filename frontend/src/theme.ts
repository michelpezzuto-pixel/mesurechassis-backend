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
  devis_a_faire: {
    label: "À mesurer",
    color: "#A1A1AA",
    bg: "#27272A",
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
// Workflow Admin : a_mesurer → devis_a_faire → technique_a_valider → en_fabrication
// (l'Admin transmet d'abord au commercial avant la validation technique)
export const NEXT_STATUS: Record<string, string> = {
  a_mesurer: "devis_a_faire",
  devis_a_faire: "technique_a_valider",
  technique_a_valider: "en_fabrication",
  a_verifier: "en_fabrication",
  en_commande: "cloture",
  en_fabrication: "cloture",
  // "cloture" / "termine" → pas de transition (déjà final)
};

// Libellé du bouton "clôture" selon l'étape suivante
export const CLOSURE_BUTTON_LABEL: Record<string, string> = {
  measure: "🚩 Clôturer la prise de cotes",
  verify: "🚩 Valider et envoyer en fabrication",
  fab: "🚩 Marquer comme terminé / livré",
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
