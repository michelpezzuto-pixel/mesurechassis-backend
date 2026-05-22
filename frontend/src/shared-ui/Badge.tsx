import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { C, SP, R, FONT } from '@/src/theme';

interface Props {
  label: string;
  color?: string;
}

/** Pastille statut/info, ex. "BROUILLON", "VALIDÉ". Couleur dynamique. */
export default function Badge({ label, color = C.ACCENT }: Props) {
  return (
    <View style={[styles.badge, { backgroundColor: color + '22', borderColor: color }]}>
      <Text style={[styles.txt, { color }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: { alignSelf: 'flex-start', paddingHorizontal: SP.md, paddingVertical: 4, borderRadius: R.pill, borderWidth: 1 },
  txt: { ...FONT.label, fontSize: 11 },
});
