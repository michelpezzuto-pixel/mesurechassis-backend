import React, { forwardRef } from 'react';
import { StyleSheet, Text, TextInput, TextInputProps, View } from 'react-native';
import { C, SP, R, FONT } from '@/src/theme';

interface Props extends TextInputProps {
  label?: string;
  hint?: string;
  error?: string;
}

/** Champ texte normalisé MesureEscalier (label MAJ + input dark + erreur en rouge). */
const Input = forwardRef<TextInput, Props>(function Input({ label, hint, error, style, ...rest }, ref) {
  return (
    <View style={{ marginBottom: SP.md }}>
      {label && <Text style={styles.label}>{label}</Text>}
      <TextInput
        ref={ref}
        placeholderTextColor={C.GRAY3}
        style={[styles.input, error && styles.inputError, style]}
        {...rest}
      />
      {hint && !error && <Text style={styles.hint}>{hint}</Text>}
      {error && <Text style={styles.error}>{error}</Text>}
    </View>
  );
});

export default Input;

const styles = StyleSheet.create({
  label: { ...FONT.label, marginBottom: SP.sm },
  input: {
    backgroundColor: C.BG_DEEPER, borderWidth: 1, borderColor: C.BORDER, borderRadius: R.md,
    paddingHorizontal: SP.md, paddingVertical: 14, color: C.WHITE, fontSize: 16,
  },
  inputError: { borderColor: C.DANGER },
  hint: { ...FONT.small, marginTop: SP.xs },
  error: { ...FONT.small, color: C.DANGER, marginTop: SP.xs },
});
