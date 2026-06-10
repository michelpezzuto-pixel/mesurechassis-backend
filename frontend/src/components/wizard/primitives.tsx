/**
 * Composants UI réutilisables du Wizard "Nouvelle Mesure".
 * Extrait de new-mesure.tsx (refacto V3 — juin 2026).
 */
import React from "react";
import { Switch, Text, TextInput, TouchableOpacity, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { colors } from "@/src/theme";
import { wizardStyles as styles } from "./wizardStyles";

// ────────────────────────────────────────────────────────────────────────────────────────
// SegBtn — Bouton segmenté (toggle group)
// ────────────────────────────────────────────────────────────────────────────────────────
export function SegBtn({
  testID,
  icon,
  label,
  active,
  onPress,
}: {
  testID?: string;
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  active: boolean;
  onPress: () => void;
}) {
  return (
    <TouchableOpacity
      testID={testID}
      onPress={onPress}
      activeOpacity={0.85}
      style={[styles.segBtn, active && styles.segBtnActive, { flex: 1 }]}
    >
      <Ionicons name={icon} size={18} color={active ? "#000" : colors.textSecondary} />
      <Text style={[styles.segBtnText, active && { color: "#000" }]}>{label}</Text>
    </TouchableOpacity>
  );
}

// ────────────────────────────────────────────────────────────────────────────────────────
// CheckboxRow — Ligne switch/checkbox avec label et sous-label
// ────────────────────────────────────────────────────────────────────────────────────────
export function CheckboxRow({
  testID,
  label,
  sub,
  value,
  onChange,
}: {
  testID?: string;
  label: string;
  sub?: string;
  value: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <View style={styles.checkboxRow}>
      <View style={{ flex: 1 }}>
        <Text style={styles.checkboxLabel}>{label}</Text>
        {sub && <Text style={styles.checkboxSub}>{sub}</Text>}
      </View>
      <Switch
        testID={testID}
        value={value}
        onValueChange={onChange}
        trackColor={{ false: colors.borderSubtle, true: colors.primary }}
        thumbColor="#fff"
      />
    </View>
  );
}

// ────────────────────────────────────────────────────────────────────────────────────────
// CotField — Saisie d'une cote en mm (anti-corruption iOS autocomplete)
// ────────────────────────────────────────────────────────────────────────────────────────
export function CotField({
  testID,
  label,
  value,
  onChange,
  onBlur,
  error,
}: {
  testID?: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
  onBlur?: () => void;
  error?: boolean;
}) {
  // 🛡️ Anti-corruption (bug iOS autocomplete) : on plafonne strict toute
  // saisie >9999mm (10m mur = impossible en menuiserie). Tronque les chiffres
  // surnuméraires sans crash.
  const handleChange = (v: string) => {
    let cleaned = (v || "").replace(",", ".");
    cleaned = cleaned.replace(/[^0-9.]/g, "");
    const dotIdx = cleaned.indexOf(".");
    if (dotIdx !== -1) {
      cleaned =
        cleaned.slice(0, dotIdx + 1) +
        cleaned.slice(dotIdx + 1).replace(/\./g, "");
    }
    const [int, dec] = cleaned.split(".");
    const safeInt = (int || "").slice(0, 4);
    const safeDec = dec !== undefined ? `.${dec.slice(0, 2)}` : "";
    onChange(safeInt + safeDec);
  };
  return (
    <View style={{ marginTop: 14 }}>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        testID={testID}
        value={value}
        onChangeText={handleChange}
        onBlur={onBlur}
        keyboardType="decimal-pad"
        placeholder="0"
        placeholderTextColor={colors.placeholder}
        maxLength={7}
        autoCorrect={false}
        autoComplete="off"
        textContentType="none"
        style={[styles.input, error && styles.inputError]}
      />
      {error && (
        <Text style={styles.errorMsg} testID={testID ? `${testID}-error` : undefined}>
          ⚠ Cote obligatoire manquante
        </Text>
      )}
    </View>
  );
}

// ────────────────────────────────────────────────────────────────────────────────────────
// DiagonalField — Saisie d'une diagonale avec calcul auto Pythagore
// ────────────────────────────────────────────────────────────────────────────────────────
export function DiagonalField({
  testID,
  label,
  value,
  state,
  onChange,
  onValidate,
  onModify,
  error,
}: {
  testID?: string;
  label: string;
  value: string;
  state: "auto" | "validated" | "manual";
  onChange: (v: string) => void;
  onValidate: () => void;
  onModify: () => void;
  error?: boolean;
}) {
  const isAuto = state === "auto";
  const isValidated = state === "validated";
  return (
    <View style={{ marginTop: 14 }}>
      <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
        <Text style={styles.label}>{label}</Text>
        {isAuto && (
          <View style={styles.autoBadge}>
            <Ionicons name="calculator-outline" size={11} color="#000" />
            <Text style={styles.autoBadgeText}>AUTO PYTHAGORE</Text>
          </View>
        )}
        {isValidated && (
          <View style={styles.validBadge}>
            <Ionicons name="checkmark" size={12} color="#000" />
            <Text style={styles.autoBadgeText}>VALIDÉ</Text>
          </View>
        )}
      </View>
      <View style={{ flexDirection: "row", gap: 8 }}>
        <TextInput
          testID={testID}
          value={value}
          onChangeText={onChange}
          keyboardType="decimal-pad"
          placeholder="0"
          placeholderTextColor={colors.placeholder}
          editable={!isAuto}
          style={[
            styles.input,
            { flex: 1 },
            error && styles.inputError,
            isAuto && { borderColor: colors.primary, color: colors.primary },
            isValidated && { borderColor: colors.success, color: colors.success },
          ]}
        />
        {isAuto && (
          <>
            <TouchableOpacity
              testID={`${testID}-validate`}
              onPress={onValidate}
              activeOpacity={0.8}
              style={[styles.diagBtn, { backgroundColor: colors.success }]}
            >
              <Ionicons name="checkmark" size={18} color="#000" />
            </TouchableOpacity>
            <TouchableOpacity
              testID={`${testID}-modify`}
              onPress={onModify}
              activeOpacity={0.8}
              style={[styles.diagBtn, { backgroundColor: colors.warning }]}
            >
              <Ionicons name="create-outline" size={18} color="#000" />
            </TouchableOpacity>
          </>
        )}
      </View>
    </View>
  );
}

// ────────────────────────────────────────────────────────────────────────────────────────
// InsulationOption — Option d'isolation (sans / ITI / ITE)
// ────────────────────────────────────────────────────────────────────────────────────────
export function InsulationOption({
  testID,
  icon,
  label,
  active,
  onPress,
}: {
  testID: string;
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  active: boolean;
  onPress: () => void;
}) {
  return (
    <TouchableOpacity
      testID={testID}
      onPress={onPress}
      activeOpacity={0.85}
      style={[styles.insulOption, active && styles.insulOptionActive]}
    >
      <Ionicons name={icon} size={20} color={active ? colors.primary : colors.textSecondary} />
      <Text style={[styles.insulOptionLabel, active && { color: colors.primary }]}>{label}</Text>
      <View style={{ flex: 1 }} />
      <Ionicons
        name={active ? "checkmark-circle" : "ellipse-outline"}
        size={20}
        color={active ? colors.primary : colors.borderStrong}
      />
    </TouchableOpacity>
  );
}
