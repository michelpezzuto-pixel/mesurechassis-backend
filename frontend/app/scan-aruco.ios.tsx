/**
 * Scan ArUco (iOS) — ultra-minimal POC.
 *
 *  • Live back-camera preview
 *  • ArUco DICT_4X4_50 detection on every frame (native OpenCV via
 *    `aruco-detector` Expo module)
 *  • Cyan bounding boxes + marker IDs overlay
 *  • HUD: detected count + resolution + ~fps + bottom strip of IDs
 *
 * No pose estimation, no calibration, no measurement, no DXF — strictly
 * detection-only as agreed for POC validation.
 */
import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator, Linking, Platform, Pressable, StyleSheet, Text, View,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import {
  Camera, useCameraDevice, useCameraPermission, useFrameProcessor,
} from 'react-native-vision-camera';
import { Worklets } from 'react-native-worklets-core';

import MarkerOverlay from '@/src/components/MarkerOverlay';
import { detectAruco, type ArucoResult } from '@/src/lib/aruco';

export default function ScanArucoiOS() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const device = useCameraDevice('back');
  const { hasPermission, requestPermission } = useCameraPermission();

  const [result, setResult] = useState<ArucoResult>({
    markers: [], frameWidth: 0, frameHeight: 0,
  });
  const [fps, setFps] = useState(0);
  const [layout, setLayout] = useState({ width: 0, height: 0 });

  useEffect(() => {
    if (!hasPermission) requestPermission();
  }, [hasPermission, requestPermission]);

  // JS-thread updater, called from the worklet via a Worklets-Core dispatcher.
  const updateResult = useCallback((r: ArucoResult, currentFps: number) => {
    setResult(r);
    setFps(currentFps);
  }, []);
  const updateResultJS = Worklets.createRunOnJS(updateResult);

  const frameProcessor = useFrameProcessor((frame) => {
    'worklet';
    const now = Date.now();
    // Each worklet runtime gets its own globalThis, so this lives in-worklet.
    // @ts-ignore
    if (globalThis.__lastArucoCall == null) globalThis.__lastArucoCall = 0;
    // @ts-ignore
    const last = globalThis.__lastArucoCall as number;

    const r = detectAruco(frame);

    // Throttle JS dispatches to ~12 fps so the React tree stays smooth.
    if (now - last < 80) return;
    // @ts-ignore
    globalThis.__lastArucoCall = now;
    const dt = now - last;
    updateResultJS(r, dt > 0 ? Math.round(1000 / dt) : 0);
  }, [updateResultJS]);

  // ── No permission yet ───────────────────────────────────────────────
  if (!hasPermission) {
    return (
      <View style={[styles.root, { paddingTop: insets.top + 16 }]}>
        <Pressable onPress={() => router.back()} style={styles.close} hitSlop={12}>
          <Ionicons name="close" size={28} color="#fff" />
        </Pressable>
        <View style={styles.center}>
          <Ionicons name="camera-outline" size={64} color="#94a3b8" />
          <Text style={styles.title}>Accès caméra requis</Text>
          <Text style={styles.subtitle}>
            Pour détecter les marqueurs ArUco collés sur les marches.
          </Text>
          <Pressable
            onPress={async () => {
              const ok = await requestPermission();
              if (!ok && Platform.OS === 'ios') Linking.openSettings();
            }}
            style={styles.cta}
          >
            <Text style={styles.ctaTxt}>Autoriser la caméra</Text>
          </Pressable>
        </View>
      </View>
    );
  }

  // ── No back camera (e.g. simulator) ─────────────────────────────────
  if (device == null) {
    return (
      <View style={[styles.root, styles.center]}>
        <ActivityIndicator color="#22d3ee" />
        <Text style={styles.subtitle}>Recherche de la caméra arrière…</Text>
      </View>
    );
  }

  return (
    <View
      style={styles.root}
      onLayout={(e) => setLayout({
        width: e.nativeEvent.layout.width,
        height: e.nativeEvent.layout.height,
      })}
    >
      <Camera
        style={StyleSheet.absoluteFill}
        device={device}
        isActive={true}
        frameProcessor={frameProcessor}
        pixelFormat="yuv"
        photo={false}
        video={false}
      />

      <MarkerOverlay
        markers={result.markers}
        frameWidth={result.frameWidth}
        frameHeight={result.frameHeight}
        viewWidth={layout.width}
        viewHeight={layout.height}
      />

      {/* Top HUD */}
      <View style={[styles.hud, { top: insets.top + 12 }]}>
        <Text style={styles.hudText}>ArUco DICT_4X4_50</Text>
        <Text style={styles.hudText}>
          Détectés : <Text style={styles.hudHighlight}>{result.markers.length}</Text>
        </Text>
        <Text style={styles.hudText}>
          {result.frameWidth}×{result.frameHeight} • ~{fps} fps
        </Text>
      </View>

      {/* Close button */}
      <Pressable
        onPress={() => router.back()}
        style={[styles.close, { top: insets.top + 12 }]}
        hitSlop={12}
      >
        <Ionicons name="close" size={28} color="#fff" />
      </Pressable>

      {/* Bottom strip of detected IDs */}
      <View style={[styles.idStrip, { bottom: insets.bottom + 20 }]}>
        {result.markers.length === 0 ? (
          <Text style={styles.idStripEmpty}>Aucun marqueur détecté — vise tes ArUco</Text>
        ) : (
          result.markers.map((m, i) => (
            <View key={`${m.id}-${i}`} style={styles.idChip}>
              <Text style={styles.idChipText}>#{m.id}</Text>
            </View>
          ))
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#000' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 24 },
  title: { color: '#fff', fontSize: 22, fontWeight: '700', marginTop: 16 },
  subtitle: { color: '#94a3b8', fontSize: 14, textAlign: 'center', marginTop: 12, lineHeight: 20 },
  cta: { marginTop: 24, backgroundColor: '#2563eb', paddingHorizontal: 24, paddingVertical: 14, borderRadius: 12 },
  ctaTxt: { color: '#fff', fontSize: 16, fontWeight: '600' },
  hud: {
    position: 'absolute', left: 16,
    backgroundColor: 'rgba(0,0,0,0.6)',
    paddingHorizontal: 12, paddingVertical: 8, borderRadius: 10,
  },
  hudText: { color: '#fff', fontSize: 12, marginVertical: 1 },
  hudHighlight: { color: '#22d3ee', fontWeight: '700' },
  close: {
    position: 'absolute', right: 16, zIndex: 10,
    width: 40, height: 40, borderRadius: 20,
    backgroundColor: 'rgba(0,0,0,0.6)',
    justifyContent: 'center', alignItems: 'center',
  },
  idStrip: {
    position: 'absolute', left: 16, right: 16,
    flexDirection: 'row', flexWrap: 'wrap', gap: 8, justifyContent: 'center',
  },
  idStripEmpty: {
    color: '#fff', fontSize: 13,
    backgroundColor: 'rgba(0,0,0,0.6)',
    paddingHorizontal: 14, paddingVertical: 8, borderRadius: 999,
  },
  idChip: { backgroundColor: 'rgba(34,211,238,0.92)', paddingHorizontal: 12, paddingVertical: 5, borderRadius: 999 },
  idChipText: { color: '#000', fontWeight: '700', fontSize: 13 },
});
