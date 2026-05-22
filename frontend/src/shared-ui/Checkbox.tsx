/**
 * Checkbox — Standard list-row checkbox with icon + label.
 * Reusable across MesureEscalier / MesureChâssis.
 */
import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { C, SP, R, FONT } from '@/src/theme';

interface Props {
  label: string;
  checked: boolean;
  onToggle: () => void;
  icon?: keyof typeof Ionicons.glyphMap;
  hint?: string;
  testID?: string;
}

export default function Checkbox({ label, checked, onToggle, icon, hint, testID }: Props) {
  return (
    <TouchableOpacity style={styles.row} onPress={onToggle} activeOpacity={0.7} testID={testID}>
      {icon && <Ionicons name={icon} size={18} color={checked ? C.ACCENT : C.GRAY3} />}
      <View style={{ flex: 1 }}>
        <Text style={[styles.label, !checked && { color: C.GRAY3 }]}>{label}</Text>
        {!!hint && <Text style={styles.hint}>{hint}</Text>}
      </View>
      <View style={[styles.box, checked && styles.boxOn]}>
        {checked && <Ionicons name="checkmark" size={14} color={C.DARK} />}
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SP.md,
    paddingVertical: 12,
  },
  label: { ...FONT.body, fontSize: 13 },
  hint: { ...FONT.small, fontSize: 11, marginTop: 2 },
  box: {
    width: 22, height: 22, borderRadius: 6,
    borderWidth: 1.5, borderColor: C.GRAY3,
    alignItems: 'center', justifyContent: 'center',
  },
  boxOn: { backgroundColor: C.ACCENT, borderColor: C.ACCENT },
});
