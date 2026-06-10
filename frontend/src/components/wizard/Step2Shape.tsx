/**
 * Step2Shape — Wizard Étape 2/3 : sélection de la forme du châssis.
 * Extrait de new-mesure.tsx (refacto V3 — juin 2026).
 * 🌍 i18n — Labels & descriptions traduits via `wizard.shapes.<key>.label/desc`.
 */
import React from "react";
import { Text, TouchableOpacity, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useTranslation } from "react-i18next";
import { ShapeIcon } from "@/src/components/ShapeIcon";
import { colors } from "@/src/theme";
import { wizardStyles as styles } from "./wizardStyles";
import { Shape, SHAPES } from "./types";

export function Step2Shape({
  onPick,
  current,
}: {
  onPick: (s: Shape) => void;
  current: Shape | null;
}) {
  const { t } = useTranslation();
  return (
    <View>
      <Text style={styles.h1}>{t("wizard.step2.title")}</Text>
      <Text style={styles.h2}>{t("wizard.step2.subtitle")}</Text>
      <Text style={styles.helperText}>{t("wizard.step2.helperText")}</Text>
      <View style={{ gap: 10, marginTop: 16 }}>
        {SHAPES.map((s) => {
          const active = current === s.key;
          const label = t(`wizard.shapes.${s.key}.label`, {
            defaultValue: s.label,
          });
          const desc = t(`wizard.shapes.${s.key}.desc`, {
            defaultValue: s.desc,
          });
          return (
            <TouchableOpacity
              key={s.key}
              testID={`shape-${s.key}`}
              onPress={() => onPick(s.key)}
              activeOpacity={0.85}
              style={[styles.shapeCard, active && styles.shapeCardActive]}
            >
              <View style={styles.shapeLetterBadge}>
                <Text style={styles.shapeLetter}>{s.letter}</Text>
              </View>
              <View style={styles.shapeIconBox}>
                <ShapeIcon
                  shape={s.key}
                  size={48}
                  color={active ? colors.primary : colors.textPrimary}
                  strokeWidth={1.8}
                />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={[styles.shapeTitle, active && { color: colors.primary }]}>{label}</Text>
                <Text style={styles.shapeDesc}>{desc}</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color={active ? colors.primary : colors.borderStrong} />
            </TouchableOpacity>
          );
        })}
      </View>
      <View style={[styles.inlineHintBox, { marginTop: 18 }]}>
        <Ionicons name="information-circle" size={14} color={colors.textSecondary} />
        <Text style={styles.inlineHintText}>{t("wizard.step2.hint")}</Text>
      </View>
    </View>
  );
}
