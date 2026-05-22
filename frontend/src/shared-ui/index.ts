/**
 * @shared-ui — Bibliothèque de composants UI réutilisables MesureEscalier.
 *
 * USAGE (dans toute future app sister Volets/Stores/etc.) :
 *   import { Button, Card, Input, ScreenHeader, Badge, SP, R, FONT, C } from '@shared-ui';
 *
 * Tous les composants respectent la charte Dark #1A1E2A / Vert Pomme #8CC63F.
 */

export { default as Button } from './Button';
export { default as Card } from './Card';
export { default as Input } from './Input';
export { default as ScreenHeader } from './ScreenHeader';
export { default as Badge } from './Badge';
export { default as KPI } from './KPI';

// Re-export du design system (couleurs, espacements, typographie)
export { C, SP, R, FONT, STATUS_LABELS, STATUS_COLOR } from '@/src/theme';
