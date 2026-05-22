import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { C, SP, R, FONT } from '@/src/theme';

interface Props {
  label: string;
  value: string | number;
  ok?: boolean; // false → texte rouge
}

/** Bloc KPI compact (label haut, valeur grosse). */
export default function KPI({ label, value, ok }: Props) {
  return (
    <View style={styles.kpi}>
      <Text style={styles.label}>{label}</Text>
      <Text style={[styles.value, ok === false && { color: C.DANGER }]}>{String(value)}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  kpi: { flex: 1, backgroundColor: C.BG_DEEPER, padding: SP.md, borderRadius: R.md, alignItems: 'center', borderWidth: 1, borderColor: C.BORDER },
  label: { ...FONT.small, fontSize: 11 },
  value: { ...FONT.h3, marginTop: 4, color: C.ACCENT },
});
