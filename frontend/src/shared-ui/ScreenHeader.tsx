import React from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { C, SP, FONT } from '@/src/theme';

interface Props {
  title: string;
  showBack?: boolean;
  rightSlot?: React.ReactNode;
  onBack?: () => void;
}

/** En-tête d'écran standard — flèche back gauche, titre centré, slot droit (icône/badge). */
export default function ScreenHeader({ title, showBack = true, rightSlot, onBack }: Props) {
  const router = useRouter();
  return (
    <View style={styles.topbar}>
      {showBack ? (
        <TouchableOpacity onPress={onBack || (() => router.back())} testID="shared-header-back" hitSlop={10}>
          <Ionicons name="arrow-back" size={24} color={C.WHITE} />
        </TouchableOpacity>
      ) : <View style={{ width: 24 }} />}
      <Text style={styles.title} numberOfLines={1}>{title}</Text>
      <View style={styles.right}>{rightSlot || <View style={{ width: 24 }} />}</View>
    </View>
  );
}

const styles = StyleSheet.create({
  topbar: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', padding: SP.lg, borderBottomWidth: 1, borderBottomColor: C.BORDER, gap: SP.md },
  title: { ...FONT.h3, fontSize: 16, flex: 1, textAlign: 'center' },
  right: { minWidth: 24, alignItems: 'flex-end' },
});
