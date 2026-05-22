import React from 'react';
import { StyleSheet, Text, View, ViewProps } from 'react-native';
import { C, SP, R, FONT } from '@/src/theme';

interface Props extends ViewProps {
  title?: string;
  variant?: 'default' | 'accent' | 'danger';
}

/** Card standard MesureEscalier — fond carte, bord, padding. Variante accent ou danger pour mettre en avant. */
export default function Card({ title, variant = 'default', children, style, ...rest }: Props) {
  const variantStyle = variant === 'accent' ? styles.accent : variant === 'danger' ? styles.danger : styles.def;
  return (
    <View style={[styles.base, variantStyle, style]} {...rest}>
      {title && <Text style={styles.title}>{title}</Text>}
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  base: { borderRadius: R.lg, padding: SP.lg, borderWidth: 1, marginBottom: SP.md },
  def: { backgroundColor: C.CARD, borderColor: C.BORDER },
  accent: { backgroundColor: C.ACCENT_BG, borderColor: C.ACCENT, borderLeftWidth: 3 },
  danger: { backgroundColor: C.DANGER_BG, borderColor: C.DANGER, borderLeftWidth: 3 },
  title: { ...FONT.label, color: C.ACCENT, marginBottom: SP.md },
});
