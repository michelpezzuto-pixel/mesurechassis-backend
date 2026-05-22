import React from 'react';
import { ActivityIndicator, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { C, SP, R, FONT } from '@/src/theme';

export type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost';

interface Props {
  label: string;
  onPress: () => void;
  variant?: ButtonVariant;
  icon?: keyof typeof Ionicons.glyphMap;
  loading?: boolean;
  disabled?: boolean;
  testID?: string;
  fullWidth?: boolean;
}

/**
 * Bouton standard MesureEscalier — variantes : primary (Vert Pomme), secondary (Card+border),
 * danger (rouge), ghost (transparent). Hauteur >= 48 (touch target Android).
 */
export default function Button({ label, onPress, variant = 'primary', icon, loading, disabled, testID, fullWidth = true }: Props) {
  const styleBtn = [styles.base, styles[variant], !fullWidth && styles.inline, (disabled || loading) && { opacity: 0.5 }];
  const txtColor =
    variant === 'primary' ? C.DARK :
    variant === 'danger' ? C.WHITE :
    variant === 'ghost' ? C.ACCENT :
    C.WHITE;

  return (
    <TouchableOpacity style={styleBtn} onPress={onPress} disabled={disabled || loading} testID={testID} activeOpacity={0.85}>
      {loading ? (
        <ActivityIndicator color={txtColor} />
      ) : (
        <View style={styles.row}>
          {icon && <Ionicons name={icon} size={18} color={txtColor} />}
          <Text style={[styles.txt, { color: txtColor }]}>{label}</Text>
        </View>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  base: { borderRadius: R.md, paddingVertical: 16, paddingHorizontal: SP.lg, alignItems: 'center', justifyContent: 'center', borderWidth: 1, minHeight: 52 },
  inline: { alignSelf: 'flex-start' },
  row: { flexDirection: 'row', alignItems: 'center', gap: SP.sm },
  txt: { ...FONT.button, fontSize: 14 },
  primary: { backgroundColor: C.ACCENT, borderColor: C.ACCENT },
  secondary: { backgroundColor: C.CARD, borderColor: C.BORDER },
  danger: { backgroundColor: C.DANGER, borderColor: C.DANGER },
  ghost: { backgroundColor: 'transparent', borderColor: C.ACCENT },
});
