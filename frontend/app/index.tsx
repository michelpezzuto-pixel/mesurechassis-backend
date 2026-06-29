import React, { useEffect } from 'react';
import { View, ActivityIndicator, StyleSheet } from 'react-native';
import { Redirect } from 'expo-router';
import { useAuth } from '@/src/auth';
import { C } from '@/src/theme';

// EAS cache-bust marker — v1.0.4 / build 5 (2026-06-29)
// Snapshot must include: ArucoDetector.podspec fix (SWIFT_OBJC_INTEROP_MODE removed),
// security audit Option A (JWT rotation, tenant isolation, CORS allow-list), and
// CORS_ORIGINS env var with both preview + .emergent.host production domains.
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
