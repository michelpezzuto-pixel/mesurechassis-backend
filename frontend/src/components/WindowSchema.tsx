import React from "react";
import { View, Text, TextInput, StyleSheet, Platform } from "react-native";
import Svg, { Rect, Line, Polygon, Path } from "react-native-svg";
import { colors } from "@/src/theme";

export type MeasurementValues = Record<string, string>;

type FieldDef = {
  key: string;
  label: string;
  position: { top?: number; bottom?: number; left?: number; right?: number };
};

const SVG_SIZE = 280;
const STROKE = "#52525B";

function InputOverlay({
  testID,
  position,
  value,
  onChange,
  placeholder,
}: {
  testID: string;
  position: FieldDef["position"];
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
}) {
  return (
    <View
      style={[styles.inputWrapper, position]}
      pointerEvents="box-none"
    >
      <Text style={styles.inputLabel}>{placeholder}</Text>
      <TextInput
        testID={testID}
        value={value}
        onChangeText={onChange}
        placeholder="mm"
        placeholderTextColor={colors.placeholder}
        keyboardType={Platform.OS === "ios" ? "decimal-pad" : "numeric"}
        style={styles.input}
      />
    </View>
  );
}

function FrameBox() {
  return (
    <Svg width={SVG_SIZE} height={SVG_SIZE}>
      <Rect
        x={40}
        y={40}
        width={SVG_SIZE - 80}
        height={SVG_SIZE - 80}
        stroke={STROKE}
        strokeWidth={4}
        fill="transparent"
      />
      <Line x1={40} y1={SVG_SIZE / 2} x2={SVG_SIZE - 40} y2={SVG_SIZE / 2} stroke={STROKE} strokeWidth={1} strokeDasharray="4,4" />
      <Line x1={SVG_SIZE / 2} y1={40} x2={SVG_SIZE / 2} y2={SVG_SIZE - 40} stroke={STROKE} strokeWidth={1} strokeDasharray="4,4" />
      <Line x1={40} y1={40} x2={SVG_SIZE - 40} y2={SVG_SIZE - 40} stroke={colors.primary} strokeWidth={1.5} strokeDasharray="3,3" opacity={0.7} />
      <Line x1={SVG_SIZE - 40} y1={40} x2={40} y2={SVG_SIZE - 40} stroke={colors.primary} strokeWidth={1.5} strokeDasharray="3,3" opacity={0.7} />
    </Svg>
  );
}

function SlidingFrame() {
  return (
    <Svg width={SVG_SIZE} height={SVG_SIZE}>
      <Rect x={40} y={40} width={SVG_SIZE - 80} height={SVG_SIZE - 80} stroke={STROKE} strokeWidth={4} fill="transparent" />
      <Line x1={SVG_SIZE / 2} y1={40} x2={SVG_SIZE / 2} y2={SVG_SIZE - 40} stroke={STROKE} strokeWidth={3} />
      <Line x1={40} y1={SVG_SIZE / 4 + 20} x2={SVG_SIZE - 40} y2={SVG_SIZE / 4 + 20} stroke={STROKE} strokeWidth={1} strokeDasharray="3,3" />
      <Line x1={40} y1={(3 * SVG_SIZE) / 4 - 20} x2={SVG_SIZE - 40} y2={(3 * SVG_SIZE) / 4 - 20} stroke={STROKE} strokeWidth={1} strokeDasharray="3,3" />
    </Svg>
  );
}

function DoorFrame() {
  return (
    <Svg width={SVG_SIZE} height={SVG_SIZE}>
      <Rect x={70} y={20} width={SVG_SIZE - 140} height={SVG_SIZE - 40} stroke={STROKE} strokeWidth={4} fill="transparent" />
      <Rect x={SVG_SIZE - 90} y={SVG_SIZE / 2 - 8} width={8} height={20} fill={colors.primary} />
    </Svg>
  );
}

function TrapezeFrame() {
  return (
    <Svg width={SVG_SIZE} height={SVG_SIZE}>
      <Polygon
        points={`60,${SVG_SIZE - 40} ${SVG_SIZE - 60},${SVG_SIZE - 40} ${SVG_SIZE - 60},60 60,140`}
        stroke={STROKE}
        strokeWidth={4}
        fill="transparent"
      />
      <Path
        d={`M 60 140 L ${SVG_SIZE - 60} 60`}
        stroke={colors.primary}
        strokeWidth={1.5}
        strokeDasharray="3,3"
        opacity={0.7}
      />
    </Svg>
  );
}

export function StandardSchema({
  values,
  onChange,
}: {
  values: MeasurementValues;
  onChange: (key: string, v: string) => void;
}) {
  const fields: FieldDef[] = [
    { key: "width_top", label: "L. haut", position: { top: 0, left: SVG_SIZE / 2 - 50 } },
    { key: "width_middle", label: "L. milieu", position: { top: SVG_SIZE / 2 - 25, left: SVG_SIZE / 2 - 50 } },
    { key: "width_bottom", label: "L. bas", position: { top: SVG_SIZE - 50, left: SVG_SIZE / 2 - 50 } },
    { key: "height_left", label: "H. gauche", position: { top: SVG_SIZE / 2 - 25, left: -10 } },
    { key: "height_middle", label: "H. milieu", position: { top: SVG_SIZE / 2 + 30, left: SVG_SIZE / 2 - 50 } },
    { key: "height_right", label: "H. droite", position: { top: SVG_SIZE / 2 - 25, right: -10 } },
    { key: "diag_1", label: "Diag 1 ↘", position: { top: 80, right: 0 } },
    { key: "diag_2", label: "Diag 2 ↙", position: { top: 80, left: 0 } },
  ];
  return (
    <SchemaContainer>
      <FrameBox />
      {fields.map((f) => (
        <InputOverlay
          key={f.key}
          testID={`schema-input-${f.key}`}
          position={f.position}
          value={values[f.key] ?? ""}
          onChange={(v) => onChange(f.key, v)}
          placeholder={f.label}
        />
      ))}
    </SchemaContainer>
  );
}

export function CoulissantSchema({
  values,
  onChange,
}: {
  values: MeasurementValues;
  onChange: (key: string, v: string) => void;
}) {
  const fields: FieldDef[] = [
    { key: "width_top", label: "L. haut", position: { top: 0, left: SVG_SIZE / 2 - 50 } },
    { key: "width_middle", label: "L. milieu", position: { top: SVG_SIZE / 2 - 25, left: SVG_SIZE / 2 - 50 } },
    { key: "width_bottom", label: "L. bas", position: { top: SVG_SIZE - 50, left: SVG_SIZE / 2 - 50 } },
    { key: "height_left", label: "H. gauche", position: { top: 50, left: -10 } },
    { key: "height_quarter_left", label: "H. 1/4 G", position: { top: 110, left: -10 } },
    { key: "height_middle", label: "H. milieu", position: { top: SVG_SIZE / 2 - 25, left: SVG_SIZE / 2 - 50 } },
    { key: "height_quarter_right", label: "H. 1/4 D", position: { top: 110, right: -10 } },
    { key: "height_right", label: "H. droite", position: { top: 50, right: -10 } },
  ];
  return (
    <SchemaContainer>
      <SlidingFrame />
      {fields.map((f) => (
        <InputOverlay
          key={f.key}
          testID={`schema-input-${f.key}`}
          position={f.position}
          value={values[f.key] ?? ""}
          onChange={(v) => onChange(f.key, v)}
          placeholder={f.label}
        />
      ))}
    </SchemaContainer>
  );
}

export function PorteSchema({
  values,
  onChange,
}: {
  values: MeasurementValues;
  onChange: (key: string, v: string) => void;
}) {
  const fields: FieldDef[] = [
    { key: "width_top", label: "L. haut", position: { top: 0, left: SVG_SIZE / 2 - 50 } },
    { key: "width_middle", label: "L. milieu", position: { top: SVG_SIZE / 2 - 25, left: SVG_SIZE / 2 - 50 } },
    { key: "width_bottom", label: "L. bas", position: { top: SVG_SIZE - 50, left: SVG_SIZE / 2 - 50 } },
    { key: "height_left", label: "H. gauche", position: { top: SVG_SIZE / 2 - 25, left: -10 } },
    { key: "height_right", label: "H. droite", position: { top: SVG_SIZE / 2 - 25, right: -10 } },
    { key: "diag_1", label: "Diag 1", position: { top: 60, left: 30 } },
    { key: "diag_2", label: "Diag 2", position: { top: SVG_SIZE - 100, right: 30 } },
  ];
  return (
    <SchemaContainer>
      <DoorFrame />
      {fields.map((f) => (
        <InputOverlay
          key={f.key}
          testID={`schema-input-${f.key}`}
          position={f.position}
          value={values[f.key] ?? ""}
          onChange={(v) => onChange(f.key, v)}
          placeholder={f.label}
        />
      ))}
    </SchemaContainer>
  );
}

export function TrapezeSchema({
  values,
  onChange,
}: {
  values: MeasurementValues;
  onChange: (key: string, v: string) => void;
}) {
  const fields: FieldDef[] = [
    { key: "width_small", label: "L. petite (haut)", position: { top: 30, left: SVG_SIZE / 2 - 50 } },
    { key: "width_intermediate", label: "L. inter. (bas)", position: { top: SVG_SIZE - 30, left: SVG_SIZE / 2 - 50 } },
    { key: "height_small", label: "H. petite (G)", position: { top: SVG_SIZE / 2 - 25, left: -10 } },
    { key: "height_large", label: "H. grande (D)", position: { top: SVG_SIZE / 2 - 25, right: -10 } },
  ];
  return (
    <SchemaContainer>
      <TrapezeFrame />
      {fields.map((f) => (
        <InputOverlay
          key={f.key}
          testID={`schema-input-${f.key}`}
          position={f.position}
          value={values[f.key] ?? ""}
          onChange={(v) => onChange(f.key, v)}
          placeholder={f.label}
        />
      ))}
    </SchemaContainer>
  );
}

function SchemaContainer({ children }: { children: React.ReactNode }) {
  return <View style={styles.wrapper}>{children}</View>;
}

const styles = StyleSheet.create({
  wrapper: {
    width: SVG_SIZE,
    height: SVG_SIZE,
    alignSelf: "center",
    backgroundColor: colors.bg,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    position: "relative",
    marginVertical: 8,
  },
  inputWrapper: {
    position: "absolute",
    width: 100,
    backgroundColor: colors.bg,
    borderWidth: 2,
    borderColor: colors.primary,
    borderRadius: 6,
    padding: 4,
  },
  inputLabel: {
    color: colors.textSecondary,
    fontSize: 9,
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: 0.5,
    textAlign: "center",
  },
  input: {
    color: colors.textPrimary,
    fontSize: 14,
    fontWeight: "800",
    textAlign: "center",
    paddingVertical: 2,
  },
});
