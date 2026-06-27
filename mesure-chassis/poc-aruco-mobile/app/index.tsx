import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Linking,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import {
  Camera,
  useCameraDevice,
  useCameraPermission,
  useFrameProcessor,
} from 'react-native-vision-camera';
import { runOnJS } from 'react-native-worklets';

import MarkerOverlay from '../src/components/MarkerOverlay';
import { detectAruco, type ArucoResult } from '../src/lib/aruco-frame-processor';

export default function CameraScreen() {
  const insets = useSafeAreaInsets();
  const device = useCameraDevice('back');
  const { hasPermission, requestPermission } = useCameraPermission();

  const [result, setResult] = useState<ArucoResult>({
    markers: [],
    frameWidth: 0,
    frameHeight: 0,
  });
  const [layoutSize, setLayoutSize] = useState({ width: 0, height: 0 });
  const [fps, setFps] = useState(0);

  useEffect(() => {
    if (!hasPermission) {
      requestPermission();
    }
  }, [hasPermission, requestPermission]);

  // JS-side updater, called from the worklet via runOnJS
  const updateResult = useCallback((r: ArucoResult, currentFps: number) => {
    setResult(r);
    setFps(currentFps);
  }, []);

  const frameProcessor = useFrameProcessor(
    (frame) => {
      'worklet';
      const now = Date.now();
      // Throttle overlay updates to ~12 fps to keep JS thread responsive
      // (detection still runs every frame for accuracy testing).
      // Worklet-scoped state lives on `globalThis` (each worklet runtime
      // has its own global), so this stays isolated from the JS thread.
      // @ts-ignore
      if (globalThis.__lastArucoCall == null) globalThis.__lastArucoCall = 0;
      // @ts-ignore
      const last = globalThis.__lastArucoCall as number;

      const r = detectAruco(frame);

      if (now - last < 80) return;
      // @ts-ignore
      globalThis.__lastArucoCall = now;

      const dt = now - last;
      const currentFps = dt > 0 ? Math.round(1000 / dt) : 0;
      runOnJS(updateResult)(r, currentFps);
    },
    [updateResult],
  );

  if (!hasPermission) {
    return (
      <View style={[styles.center, { paddingTop: insets.top }]}>
        <Text style={styles.title}>Camera access required</Text>
        <Text style={styles.subtitle}>
          This POC needs your camera to detect ArUco markers.
        </Text>
        <Pressable
          style={styles.button}
          onPress={async () => {
            const granted = await requestPermission();
            if (!granted && Platform.OS === 'ios') {
              Linking.openSettings();
            }
          }}
        >
          <Text style={styles.buttonText}>Grant camera access</Text>
        </Pressable>
      </View>
    );
  }

  if (device == null) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color="#fff" />
        <Text style={styles.subtitle}>Looking for back camera…</Text>
      </View>
    );
  }

  return (
    <View
      style={styles.container}
      onLayout={(e) =>
        setLayoutSize({
          width: e.nativeEvent.layout.width,
          height: e.nativeEvent.layout.height,
        })
      }
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
        viewWidth={layoutSize.width}
        viewHeight={layoutSize.height}
      />

      {/* HUD */}
      <View style={[styles.hud, { top: insets.top + 12 }]}>
        <Text style={styles.hudText}>ArUco DICT_4X4_50</Text>
        <Text style={styles.hudText}>
          Detected: <Text style={styles.hudHighlight}>{result.markers.length}</Text>
        </Text>
        <Text style={styles.hudText}>
          {result.frameWidth}×{result.frameHeight} • ~{fps} fps
        </Text>
      </View>

      {/* IDs strip */}
      <View style={[styles.idStrip, { bottom: insets.bottom + 16 }]}>
        {result.markers.length === 0 ? (
          <Text style={styles.idStripEmpty}>No marker detected</Text>
        ) : (
          result.markers.map((m) => (
            <View key={`${m.id}-${m.corners[0]?.x ?? 0}`} style={styles.idChip}>
              <Text style={styles.idChipText}>#{m.id}</Text>
            </View>
          ))
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#000' },
  center: {
    flex: 1,
    backgroundColor: '#000',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  title: { color: '#fff', fontSize: 20, fontWeight: '600', marginBottom: 8 },
  subtitle: { color: '#aaa', fontSize: 14, textAlign: 'center', marginBottom: 24 },
  button: {
    backgroundColor: '#2563eb',
    paddingHorizontal: 24,
    paddingVertical: 14,
    borderRadius: 12,
  },
  buttonText: { color: '#fff', fontSize: 16, fontWeight: '600' },
  hud: {
    position: 'absolute',
    left: 16,
    backgroundColor: 'rgba(0,0,0,0.55)',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 10,
  },
  hudText: { color: '#fff', fontSize: 12, marginVertical: 1 },
  hudHighlight: { color: '#22d3ee', fontWeight: '700' },
  idStrip: {
    position: 'absolute',
    left: 16,
    right: 16,
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    justifyContent: 'center',
  },
  idStripEmpty: {
    color: '#fff',
    fontSize: 13,
    backgroundColor: 'rgba(0,0,0,0.55)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 999,
  },
  idChip: {
    backgroundColor: 'rgba(34,211,238,0.9)',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 999,
  },
  idChipText: { color: '#000', fontWeight: '700', fontSize: 13 },
});
