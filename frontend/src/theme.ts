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

// === Statuts métier — pipeline 3 étapes consolidé ===========================
// À vérifier (orange) → En fabrication (bleu) → Terminé / Livré (vert)
// Les anciens statuts (devis_a_faire, technique_a_valider, en_commande,
// en_fabrication, cloture) sont mappés vers la nouvelle palette.
export const statusMeta: Record<
  string,
  { label: string; color: string; bg: string; stage: "verify" | "fab" | "done" }
> = {
  // Étape 1 — À VÉRIFIER (orange)
  devis_a_faire: { label: "À vérifier", color: "#FF9F0A", bg: "#3a2400", stage: "verify" },
  technique_a_valider: { label: "À vérifier", color: "#FF9F0A", bg: "#3a2400", stage: "verify" },
  a_verifier: { label: "À vérifier", color: "#FF9F0A", bg: "#3a2400", stage: "verify" },
  // Étape 2 — EN FABRICATION (bleu)
  en_commande: { label: "En fabrication", color: "#3B82F6", bg: "#0c1f3a", stage: "fab" },
  en_fabrication: { label: "En fabrication", color: "#3B82F6", bg: "#0c1f3a", stage: "fab" },
  // Étape 3 — TERMINÉ / LIVRÉ (vert)
  cloture: { label: "Terminé / Livré", color: "#32D74B", bg: "#0e3315", stage: "done" },
  termine: { label: "Terminé / Livré", color: "#32D74B", bg: "#0e3315", stage: "done" },
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
