/**
 * Picker — Compact pill selector for small option sets.
 * Used for : Stair shape (DROIT/TOURNANT), Floor index (-3..+7), Format export, etc.
 */
import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView } from 'react-native';
import { C, SP, R, FONT } from '@/src/theme';

interface Option<T extends string | number> {
  value: T;
  label: string;
  disabled?: boolean;
}

interface Props<T extends string | number> {
  options: Option<T>[];
  value: T;
  onChange: (value: T) => void;
  /** Horizontal scroll if too many options */
  scrollable?: boolean;
  /** Render as wider buttons (vs compact pills) */
  variant?: 'pill' | 'block';
  testIDPrefix?: string;
}

function PickerInner<T extends string | number>({
  options, value, onChange, scrollable, variant = 'pill', testIDPrefix,
}: Props<T>) {
  const content = (
    <View style={[styles.row, variant === 'block' && { flexWrap: 'wrap', gap: SP.sm }]}>
      {options.map(opt => {
        const active = opt.value === value;
        return (
          <TouchableOpacity
            key={String(opt.value)}
            onPress={() => !opt.disabled && onChange(opt.value)}
            disabled={opt.disabled}
            style={[
              styles.btn,
              variant === 'block' && styles.btnBlock,
              active && styles.btnActive,
              opt.disabled && styles.btnDisabled,
            ]}
            testID={testIDPrefix ? `${testIDPrefix}-${opt.value}` : undefined}
          >
            <Text style={[
              styles.txt,
              active && styles.txtActive,
              opt.disabled && styles.txtDisabled,
            ]}>
              {opt.label}
            </Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );
  if (scrollable) {
    return (
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ paddingHorizontal: 2 }}>
        {content}
      </ScrollView>
    );
  }
  return content;
}

// Type-safe wrapper (TS issues with default-exported generic component)
const Picker = PickerInner as <T extends string | number>(props: Props<T>) => JSX.Element;
export default Picker;

const styles = StyleSheet.create({
  row: { flexDirection: 'row', gap: 6 },
  btn: {
    minWidth: 44,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: R.pill,
    borderWidth: 1,
    borderColor: C.BORDER,
    backgroundColor: C.CARD,
    alignItems: 'center',
    justifyContent: 'center',
  },
  btnBlock: { flex: 1, paddingVertical: 12, borderRadius: R.md },
  btnActive: { backgroundColor: C.ACCENT, borderColor: C.ACCENT },
  btnDisabled: { opacity: 0.35 },
  txt: { ...FONT.label, fontSize: 11, color: C.GRAY3 },
  txtActive: { color: C.DARK },
  txtDisabled: { color: C.GRAY3 },
});
