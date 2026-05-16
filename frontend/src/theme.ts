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

export const statusMeta: Record<
  string,
  { label: string; color: string; bg: string }
> = {
  devis_a_faire: { label: "Devis à faire", color: "#FFCC00", bg: "#3a2e00" },
  technique_a_valider: { label: "Technique à valider", color: "#FF9F0A", bg: "#3a2400" },
  cloture: { label: "Clôturé", color: "#32D74B", bg: "#0e3315" },
};

export const blockMeta: Record<string, { label: string; icon: string }> = {
  standard: { label: "Standard", icon: "square-outline" },
  coulissant: { label: "Coulissant", icon: "swap-horizontal" },
  porte: { label: "Porte", icon: "exit-outline" },
  trapeze: { label: "Trapèze", icon: "triangle-outline" },
};
