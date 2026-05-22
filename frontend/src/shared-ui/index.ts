/**
 * @shared-ui — Bibliothèque de composants UI réutilisables.
 *
 * Apps cibles : MesureEscalier · MesureChâssis · (futures sister apps métier)
 *
 * USAGE :
 *   import { Button, Card, Input, Modal, Picker, Checkbox, ScreenHeader, Badge, KPI }
 *     from '@/src/shared-ui';
 *
 * Charte graphique : Dark #1A1E2A / Vert Pomme #8CC63F (cf. theme.ts).
 *
 * RÈGLE DE PORTABILITÉ : aucun composant ne doit dépendre du métier (pas d'import
 * d'API, de modèles ou de logique stairs). Tout passe par props.
 */

export { default as Button } from './Button';
export { default as Card } from './Card';
export { default as Input } from './Input';
export { default as ScreenHeader } from './ScreenHeader';
export { default as Badge } from './Badge';
export { default as KPI } from './KPI';
export { default as Modal } from './Modal';
export { default as Picker } from './Picker';
export { default as Checkbox } from './Checkbox';

// Re-export du design system (couleurs, espacements, typographie)
export { C, SP, R, FONT, STATUS_LABELS, STATUS_COLOR } from '@/src/theme';
