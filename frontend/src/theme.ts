// MesureEscalier — Design tokens
export const C = {
  DARK: '#1A1E2A',
  BG_DEEPER: '#0F1320',
  CARD: '#232838',
  BORDER: '#2D3446',
  GRAY1: '#F5F5F7',
  GRAY2: '#E0E0E6',
  GRAY3: '#9098A8',
  WHITE: '#FFFFFF',
  TEXT_DARK: '#111827',
  ACCENT: '#8CC63F',
  ACCENT_DARK: '#6FA32E',
  ACCENT_BG: 'rgba(140, 198, 63, 0.15)',
  DANGER: '#EF4444',
  DANGER_BG: 'rgba(239, 68, 68, 0.12)',
  WARN: '#F59E0B',
  INFO: '#3B82F6',
};

export const SP = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 };

export const R = { sm: 6, md: 8, lg: 12, xl: 16, pill: 999 };

export const FONT = {
  h1: { fontSize: 28, fontWeight: '900' as const, color: C.WHITE, letterSpacing: 0.5 },
  h2: { fontSize: 22, fontWeight: '800' as const, color: C.WHITE, letterSpacing: 0.3 },
  h3: { fontSize: 18, fontWeight: '700' as const, color: C.WHITE },
  body: { fontSize: 15, fontWeight: '400' as const, color: C.WHITE },
  small: { fontSize: 13, fontWeight: '400' as const, color: C.GRAY3 },
  label: { fontSize: 12, fontWeight: '700' as const, color: C.GRAY3, letterSpacing: 1, textTransform: 'uppercase' as const },
  button: { fontSize: 15, fontWeight: '800' as const, letterSpacing: 1, textTransform: 'uppercase' as const },
};

export const STATUS_LABELS: Record<string, string> = {
  brouillon: 'Brouillon',
  a_mesurer: 'À mesurer',
  a_verifier: 'À vérifier',
  valide: 'Validé',
  en_fabrication: 'En fabrication',
  termine: 'Terminé',
};

export const STATUS_COLOR: Record<string, string> = {
  brouillon: '#9098A8',
  a_mesurer: '#F59E0B',
  a_verifier: '#3B82F6',
  valide: '#8CC63F',
  en_fabrication: '#A855F7',
  termine: '#22C55E',
};
