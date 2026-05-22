/**
 * Modal — Centered modal sheet with dark backdrop.
 * Cross-app reusable (MesureEscalier / MesureChâssis).
 */
import React from 'react';
import {
  Modal as RNModal,
  View, Text, StyleSheet, TouchableOpacity, KeyboardAvoidingView, Platform, Pressable,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { C, SP, R, FONT } from '@/src/theme';

interface Props {
  visible: boolean;
  title?: string;
  onClose: () => void;
  children: React.ReactNode;
  /** Show close X button in top-right corner (default true) */
  showClose?: boolean;
  /** Maximum width of the modal card (default 420) */
  maxWidth?: number;
  /** Allow closing on backdrop tap (default true) */
  dismissOnBackdrop?: boolean;
  testID?: string;
}

export default function Modal({
  visible, title, onClose, children, showClose = true, maxWidth = 420,
  dismissOnBackdrop = true, testID,
}: Props) {
  return (
    <RNModal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.backdrop}
      >
        <Pressable
          style={StyleSheet.absoluteFill}
          onPress={() => dismissOnBackdrop && onClose()}
          testID={testID ? `${testID}-backdrop` : undefined}
        />
        <View style={[styles.card, { maxWidth }]} testID={testID}>
          {(title || showClose) && (
            <View style={styles.header}>
              {!!title && <Text style={styles.title}>{title}</Text>}
              {showClose && (
                <TouchableOpacity onPress={onClose} hitSlop={12} testID={testID ? `${testID}-close` : undefined}>
                  <Ionicons name="close" size={24} color={C.WHITE} />
                </TouchableOpacity>
              )}
            </View>
          )}
          <View style={styles.body}>{children}</View>
        </View>
      </KeyboardAvoidingView>
    </RNModal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.6)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: SP.lg,
  },
  card: {
    width: '100%',
    backgroundColor: C.CARD,
    borderRadius: R.lg,
    borderWidth: 1,
    borderColor: C.BORDER,
    overflow: 'hidden',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: SP.lg,
    paddingTop: SP.lg,
    paddingBottom: SP.md,
    borderBottomWidth: 1,
    borderBottomColor: C.BORDER,
    gap: SP.md,
  },
  title: { ...FONT.h3, flex: 1, fontSize: 16, color: C.WHITE },
  body: { padding: SP.lg, gap: SP.md },
});
