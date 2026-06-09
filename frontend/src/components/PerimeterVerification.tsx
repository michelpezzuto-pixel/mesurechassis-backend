/**
 * ArcLengthVerification — Champ de vérification de la longueur de l'arc.
 *
 * Le mesureur suit la courbe de l'arc avec son mètre ruban et saisit la
 * valeur mesurée. Le composant compare avec la valeur calculée et affiche
 * un état visuel :
 *   - ⏳ "À VÉRIFIER" tant que rien n'est saisi
 *   - ✓ "VÉRIFIÉ" (vert) si la valeur est dans la tolérance
 *   - ✗ "ÉCART" (rouge) si la valeur est hors tolérance
 */

import React from "react";
import {
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { colors } from "@/src/theme";
import { formatPerimeter, withinTolerance } from "@/src/utils/perimeter";

type Props = {
  /** Longueur de l'arc calculée par l'app (mm). `null` si cotes incomplètes. */
  computed: number | null;
  /** Valeur mesurée saisie par le mesureur (texte brut, peut être vide). */
  measuredValue: string;
  /** Callback à chaque modification de la saisie. */
  onChangeMeasured: (v: string) => void;
  /** testID pour les tests E2E. */
  testID?: string;
};

export default function ArcLengthVerification({
  computed,
  measuredValue,
  onChangeMeasured,
  testID,
}: Props) {
  const measured = parseFloat(measuredValue.replace(",", "."));
  const hasMeasure = measuredValue.trim().length > 0 && Number.isFinite(measured);
  const hasComputed = computed !== null && computed > 0;

  let status: "pending" | "ok" | "ko" = "pending";
  let diffStr = "";
  if (hasMeasure && hasComputed) {
    const ok = withinTolerance(measured, computed!);
    status = ok ? "ok" : "ko";
    const diff = Math.round(measured - computed!);
    const sign = diff >= 0 ? "+" : "";
    diffStr = `${sign}${diff} mm`;
  }

  // Réinitialise la saisie quand l'utilisateur clique sur "Modifier"
  const onReset = () => onChangeMeasured("");

  return (
    <View style={styles.wrap}>
      <View style={styles.header}>
        <Ionicons name="analytics-outline" size={16} color={colors.primary} />
        <Text style={styles.title}>VÉRIFICATION DE L&apos;ARC</Text>
      </View>

      <Text style={styles.hint}>
        Suivez la courbe de l&apos;arc avec votre mètre ruban (uniquement la
        partie courbe, pas les jambages ni la base) puis saisissez votre
        mesure ci-dessous. L&apos;application compare avec la valeur
        géométrique calculée.
      </Text>

      <View style={styles.row}>
        <View style={{ flex: 1 }}>
          <Text style={styles.label}>CALCULÉ (app)</Text>
          <View style={[styles.cell, styles.cellComputed]}>
            <Ionicons
              name="calculator-outline"
              size={16}
              color={colors.primary}
            />
            <Text style={styles.cellTextComputed}>
              {formatPerimeter(computed)}
            </Text>
          </View>
        </View>
        <View style={{ flex: 1 }}>
          <Text style={styles.label}>MESURÉ (ruban)</Text>
          <TextInput
            testID={testID || "input-perimeter-measured"}
            value={measuredValue}
            onChangeText={onChangeMeasured}
            keyboardType="decimal-pad"
            placeholder="0"
            placeholderTextColor={colors.placeholder}
            style={[
              styles.input,
              status === "ok" && styles.inputOk,
              status === "ko" && styles.inputKo,
            ]}
          />
        </View>
      </View>

      {/* Bandeau d'état */}
      {status === "pending" && hasComputed && (
        <View style={[styles.badge, styles.badgePending]}>
          <Ionicons name="time-outline" size={14} color={colors.warning} />
          <Text style={[styles.badgeText, { color: colors.warning }]}>
            À VÉRIFIER — Saisissez votre mesure au ruban
          </Text>
        </View>
      )}
      {status === "ok" && (
        <View style={[styles.badge, styles.badgeOk]}>
          <Ionicons name="checkmark-circle" size={14} color={colors.success} />
          <Text style={[styles.badgeText, { color: colors.success }]}>
            VÉRIFIÉ — Écart {diffStr} (tolérance respectée)
          </Text>
          <TouchableOpacity onPress={onReset} hitSlop={6}>
            <Ionicons name="create-outline" size={16} color={colors.success} />
          </TouchableOpacity>
        </View>
      )}
      {status === "ko" && (
        <View style={[styles.badge, styles.badgeKo]}>
          <Ionicons name="warning" size={14} color={colors.anomaly} />
          <Text style={[styles.badgeText, { color: colors.anomaly }]}>
            ÉCART {diffStr} — Re-vérifiez vos cotes ou votre mesure ruban
          </Text>
          <TouchableOpacity onPress={onReset} hitSlop={6}>
            <Ionicons name="create-outline" size={16} color={colors.anomaly} />
          </TouchableOpacity>
        </View>
      )}
      {!hasComputed && (
        <Text style={styles.notReady}>
          ⓘ Renseignez d&apos;abord les cotes ci-dessus pour calculer la longueur de l&apos;arc.
        </Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    marginTop: 18,
    padding: 12,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "rgba(255,107,26,0.35)",
    backgroundColor: "rgba(255,107,26,0.05)",
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    marginBottom: 6,
  },
  title: {
    color: colors.primary,
    fontWeight: "900",
    fontSize: 12,
    letterSpacing: 0.8,
  },
  hint: {
    color: colors.textSecondary,
    fontSize: 11,
    lineHeight: 15,
    marginBottom: 10,
  },
  row: {
    flexDirection: "row",
    gap: 10,
  },
  label: {
    color: colors.textSecondary,
    fontSize: 10,
    fontWeight: "800",
    letterSpacing: 0.6,
    marginBottom: 4,
  },
  cell: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    paddingHorizontal: 10,
    minHeight: 46,
    borderRadius: 8,
    borderWidth: 1,
  },
  cellComputed: {
    borderColor: colors.primary,
    backgroundColor: "rgba(255,107,26,0.1)",
  },
  cellTextComputed: {
    color: colors.primary,
    fontWeight: "900",
    fontSize: 15,
  },
  input: {
    backgroundColor: colors.inputBg,
    color: colors.textPrimary,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.borderStrong,
    paddingHorizontal: 10,
    minHeight: 46,
    fontSize: 15,
    fontWeight: "700",
  },
  inputOk: { borderColor: colors.success, color: colors.success },
  inputKo: { borderColor: colors.anomaly, color: colors.anomaly },
  badge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginTop: 10,
    paddingVertical: 8,
    paddingHorizontal: 10,
    borderRadius: 8,
    borderWidth: 1,
  },
  badgePending: {
    borderColor: colors.warning,
    backgroundColor: "rgba(255,165,0,0.08)",
  },
  badgeOk: {
    borderColor: colors.success,
    backgroundColor: "rgba(0,200,80,0.08)",
  },
  badgeKo: {
    borderColor: colors.anomaly,
    backgroundColor: "rgba(255,30,30,0.08)",
  },
  badgeText: {
    flex: 1,
    fontSize: 11,
    fontWeight: "800",
    letterSpacing: 0.3,
  },
  notReady: {
    marginTop: 8,
    color: colors.textSecondary,
    fontSize: 11,
    fontStyle: "italic",
  },
});
