import React, { useEffect } from 'react';
import { View, ActivityIndicator, StyleSheet } from 'react-native';
import { Redirect } from 'expo-router';
import { useAuth } from '@/src/auth';
import { C } from '@/src/theme';

// EAS cache-bust marker — v1.0.3 / build 4 (2026-06)
// Forces Emergent to generate a fresh code snapshot so the ArucoDetector.podspec
// fix (removed SWIFT_OBJC_INTEROP_MODE='objcxx') actually reaches the build server.
export default function Index() {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <View style={styles.c}>
        <ActivityIndicator color={C.ACCENT} size="large" />
      </View>
    );
  }
  if (!user) return <Redirect href="/login" />;
  return <Redirect href="/dashboard" />;
}

const styles = StyleSheet.create({
  c: { flex: 1, backgroundColor: C.DARK, alignItems: 'center', justifyContent: 'center' },
});
