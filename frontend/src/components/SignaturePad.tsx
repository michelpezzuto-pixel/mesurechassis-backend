import React, { useRef, useState, useCallback } from "react";
import {
  GestureResponderEvent,
  PanResponder,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { captureRef } from "react-native-view-shot";
import Svg, { Path } from "react-native-svg";
import { Ionicons } from "@expo/vector-icons";
import { colors } from "@/src/theme";

const PAD_HEIGHT = 200;

export type SignaturePadHandle = {
  capture: () => Promise<string | null>;
  clear: () => void;
  isEmpty: () => boolean;
};

type Props = {
  initial?: string | null;
  onChange?: (hasContent: boolean) => void;
};

export default function SignaturePad({ onChange }: Props) {
  const [paths, setPaths] = useState<string[]>([]);
  const currentRef = useRef<string>("");
  const viewRef = useRef<View>(null);

  const commit = useCallback(() => {
    if (currentRef.current.length > 0) {
      setPaths((p) => {
        const next = [...p, currentRef.current];
        onChange?.(next.length > 0);
        return next;
      });
      currentRef.current = "";
    }
  }, [onChange]);

  const panResponder = useRef(
    PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onMoveShouldSetPanResponder: () => true,
      onPanResponderGrant: (e: GestureResponderEvent) => {
        const { locationX, locationY } = e.nativeEvent;
        currentRef.current = `M ${locationX.toFixed(1)} ${locationY.toFixed(1)}`;
      },
      onPanResponderMove: (e: GestureResponderEvent) => {
        const { locationX, locationY } = e.nativeEvent;
        currentRef.current += ` L ${locationX.toFixed(1)} ${locationY.toFixed(1)}`;
        // force re-render with the active path appended visually
        setPaths((prev) => [...prev]);
      },
      onPanResponderRelease: () => commit(),
      onPanResponderTerminate: () => commit(),
    })
  ).current;

  const clear = () => {
    setPaths([]);
    currentRef.current = "";
    onChange?.(false);
  };

  const capture = async (): Promise<string | null> => {
    if (paths.length === 0 && currentRef.current.length === 0) return null;
    try {
      const uri = await captureRef(viewRef, {
        format: "png",
        quality: 0.8,
        result: "data-uri",
      });
      return uri;
    } catch {
      return null;
    }
  };

  // Expose imperative methods via a sibling ref pattern
  (SignaturePad as any).capture = capture;
  (SignaturePad as any).clear = clear;

  return (
    <View>
      <View
        ref={viewRef}
        collapsable={false}
        style={styles.pad}
        {...panResponder.panHandlers}
      >
        <Svg width="100%" height={PAD_HEIGHT}>
          {paths.map((d, i) => (
            <Path key={i} d={d} stroke={colors.textPrimary} strokeWidth={2.5} fill="none" strokeLinecap="round" strokeLinejoin="round" />
          ))}
          {currentRef.current.length > 0 && (
            <Path d={currentRef.current} stroke={colors.textPrimary} strokeWidth={2.5} fill="none" strokeLinecap="round" strokeLinejoin="round" />
          )}
        </Svg>
        {paths.length === 0 && currentRef.current.length === 0 && (
          <View pointerEvents="none" style={styles.placeholder}>
            <Ionicons name="create-outline" size={28} color={colors.borderStrong} />
            <Text style={styles.placeholderText}>Signez ici avec votre doigt</Text>
          </View>
        )}
      </View>
      <View style={styles.toolbar}>
        <TouchableOpacity
          testID="signature-clear"
          onPress={clear}
          style={styles.clearBtn}
          activeOpacity={0.7}
        >
          <Ionicons name="refresh" size={16} color={colors.textPrimary} />
          <Text style={styles.clearText}>Effacer</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

// Exported wrapper with imperative ref (preferred API)
export function useSignaturePad() {
  const [hasContent, setHasContent] = useState(false);
  const captureFn = useRef<() => Promise<string | null>>(async () => null);
  const clearFn = useRef<() => void>(() => {});
  return {
    hasContent,
    setHasContent,
    captureRef: captureFn,
    clearRef: clearFn,
  };
}

const styles = StyleSheet.create({
  pad: {
    width: "100%",
    height: PAD_HEIGHT,
    backgroundColor: "#F4F1EA",
    borderRadius: 10,
    borderWidth: 2,
    borderColor: colors.borderStrong,
    overflow: "hidden",
  },
  placeholder: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
  },
  placeholderText: { color: colors.borderStrong, fontStyle: "italic" },
  toolbar: { flexDirection: "row", justifyContent: "flex-end", marginTop: 8 },
  clearBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    backgroundColor: colors.surface,
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
  },
  clearText: { color: colors.textPrimary, fontWeight: "700", fontSize: 13 },
});
