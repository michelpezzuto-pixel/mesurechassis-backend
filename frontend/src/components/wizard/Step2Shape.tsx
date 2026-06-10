/**
 * Step2Shape — Wizard Étape 2/3 : sélection de la forme du châssis.
 * Extrait de new-mesure.tsx (refacto V3 — juin 2026).
 */
import React from "react";
import { Text, TouchableOpacity, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
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
  return (
    <View>
      <Text style={styles.h1}>SÉLECTION DE LA MENUISERIE</Text>
      <Text style={styles.h2}>Étape 2/3 · Choisissez la forme exacte du châssis</Text>
      <Text style={styles.helperText}>
        Le type d&apos;ouvrant (Fixe, Ouvrant, Oscillo-battant, Coulissant) sera défini en atelier via
        le libellé / référence saisi à l&apos;étape suivante.
      </Text>
      <View style={{ gap: 10, marginTop: 16 }}>
        {SHAPES.map((s) => {
          const active = current === s.key;
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
                <Text style={[styles.shapeTitle, active && { color: colors.primary }]}>{s.label}</Text>
                <Text style={styles.shapeDesc}>{s.desc}</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color={active ? colors.primary : colors.borderStrong} />
            </TouchableOpacity>
          );
        })}
      </View>
      <View style={[styles.inlineHintBox, { marginTop: 18 }]}>
        <Ionicons name="information-circle" size={14} color={colors.textSecondary} />
        <Text style={styles.inlineHintText}>
          Sélectionnez la forme correspondant le mieux à votre châssis. Pour
          un polygone (triangle, pentagone, hexagone, octogone), choisissez
          « POLYGONE » puis indiquez le nombre d&apos;arêtes.
        </Text>
      </View>
    </View>
  );
}
