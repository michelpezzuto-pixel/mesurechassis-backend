/**
 * Scan ArUco — web/Android fallback (informative screen).
 * The iOS implementation lives in scan-aruco.ios.tsx and uses
 * react-native-vision-camera + a native frame processor.
 */
import React from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

export default function ScanArucoFallback() {
  const router = useRouter();
  const insets = useSafeAreaInsets();

  return (
    <View style={[styles.root, { paddingTop: insets.top }]}>
      <TouchableOpacity onPress={() => router.back()} style={styles.close} hitSlop={12}>
        <Ionicons name="close" size={28} color="#fff" />
      </TouchableOpacity>
      <View style={styles.center}>
        <Ionicons name="camera-outline" size={64} color="#94a3b8" />
        <Text style={styles.title}>Scanner ArUco</Text>
        <Text style={styles.subtitle}>
          Cette fonctionnalité nécessite la version iOS installée via TestFlight
          (build développement). Elle n'est pas disponible dans le preview web
          ni dans Expo Go.
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#0f172a' },
  close: { position: 'absolute', top: 12, right: 16, zIndex: 10, padding: 8 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 24 },
  title: { color: '#fff', fontSize: 22, fontWeight: '700', marginTop: 16 },
  subtitle: { color: '#94a3b8', fontSize: 14, textAlign: 'center', marginTop: 12, lineHeight: 20 },
});
