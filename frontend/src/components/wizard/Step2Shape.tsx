/**
 * Step2Shape — Wizard Étape 2/3 : sélection de la forme du châssis.
 * Extrait de new-mesure.tsx (refacto V3 — juin 2026).
 * 🌍 i18n — Labels & descriptions traduits via `wizard.shapes.<key>.label/desc`.
 * 💎 Freemium (juin 2026) — Les formes "premium" sont visibles mais verrouillées
 *    pour les utilisateurs sans abonnement actif. Tap → modal Premium.
 */
import React, { useState } from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useTranslation } from "react-i18next";
import { ShapeIcon } from "@/src/components/ShapeIcon";
import { PremiumLockModal } from "@/src/components/premium/PremiumLockModal";
import { useAuth } from "@/src/context/AuthContext";
import { isFreeShape, isPremiumUser } from "@/src/lib/freemium";
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
  const { company } = useAuth();
  const userIsPremium = isPremiumUser(company);

  // État du modal Premium : si non null, modal affiché pour cette forme.
  const [lockedShapeLabel, setLockedShapeLabel] = useState<string | null>(null);

  const handlePress = (shape: Shape, label: string) => {
    const free = isFreeShape(shape);
    if (free || userIsPremium) {
      onPick(shape);
    } else {
      // Forme premium + utilisateur non premium → afficher modal
      setLockedShapeLabel(label);
    }
  };

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
          const free = isFreeShape(s.key);
          const locked = !free && !userIsPremium;

          return (
            <TouchableOpacity
              key={s.key}
              testID={`shape-${s.key}`}
              onPress={() => handlePress(s.key, label)}
              activeOpacity={0.85}
              style={[
                styles.shapeCard,
                active && styles.shapeCardActive,
                locked && premiumStyles.lockedCard,
              ]}
            >
              <View style={styles.shapeLetterBadge}>
                <Text style={styles.shapeLetter}>{s.letter}</Text>
              </View>
              <View style={styles.shapeIconBox}>
                <ShapeIcon
                  shape={s.key}
                  size={48}
                  color={
                    locked
                      ? colors.textSecondary
                      : active
                      ? colors.primary
                      : colors.textPrimary
                  }
                  strokeWidth={1.8}
                />
              </View>
              <View style={{ flex: 1 }}>
                <View style={premiumStyles.titleRow}>
                  <Text
                    style={[
                      styles.shapeTitle,
                      active && { color: colors.primary },
                      locked && premiumStyles.lockedText,
                    ]}
                  >
                    {label}
                  </Text>
                  {locked && (
                    <View style={premiumStyles.lockBadge}>
                      <Ionicons
                        name="lock-closed"
                        size={11}
                        color="#fff"
                      />
                      <Text style={premiumStyles.lockBadgeText}>
                        {t("premium.badge", { defaultValue: "Premium" })}
                      </Text>
                    </View>
                  )}
                </View>
                <Text
                  style={[
                    styles.shapeDesc,
                    locked && premiumStyles.lockedTextSecondary,
                  ]}
                >
                  {desc}
                </Text>
              </View>
              <Ionicons
                name={locked ? "lock-closed" : "chevron-forward"}
                size={20}
                color={
                  locked
                    ? colors.borderStrong
                    : active
                    ? colors.primary
                    : colors.borderStrong
                }
              />
            </TouchableOpacity>
          );
        })}
      </View>
      <View style={[styles.inlineHintBox, { marginTop: 18 }]}>
        <Ionicons
          name="information-circle"
          size={14}
          color={colors.textSecondary}
        />
        <Text style={styles.inlineHintText}>{t("wizard.step2.hint")}</Text>
      </View>

      <PremiumLockModal
        visible={lockedShapeLabel !== null}
        shapeLabel={lockedShapeLabel ?? undefined}
        onClose={() => setLockedShapeLabel(null)}
      />
    </View>
  );
}

const premiumStyles = StyleSheet.create({
  lockedCard: {
    opacity: 0.75,
    borderStyle: "dashed",
  },
  lockedText: {
    color: colors.textSecondary,
  },
  lockedTextSecondary: {
    color: colors.textSecondary,
    opacity: 0.85,
  },
  titleRow: {
    flexDirection: "row",
    alignItems: "center",
    flexWrap: "wrap",
    gap: 8,
    marginBottom: 2,
  },
  lockBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    backgroundColor: colors.primary,
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 999,
  },
  lockBadgeText: {
    color: "#fff",
    fontSize: 10,
    fontWeight: "700",
    letterSpacing: 0.4,
  },
});
