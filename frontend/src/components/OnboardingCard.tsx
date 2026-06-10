/**
 * OnboardingCard
 * --------------
 * Carte "Premiers pas" affichée sur le Dashboard pour les nouveaux
 * Admin d'entreprise qui n'ont pas encore :
 *   1. Invité un commercial
 *   2. Invité un technicien (recommandé)
 *   3. Créé leur premier chantier
 *
 * Chaque étape est marquée comme "✓" dès qu'elle est complétée.
 * Le bouton "Masquer cette aide" persiste le choix dans AsyncStorage.
 */
import React from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { colors } from "@/src/theme";

type TeamMember = { id: string; role: string; name: string };

type Props = {
  teamMembers: TeamMember[];
  hasChantier: boolean;
  onGoTeam: () => void;
  onNewChantier: () => void;
  onDismiss: () => void;
  t: (key: string, opts?: Record<string, unknown>) => string;
};

export default function OnboardingCard({
  teamMembers,
  hasChantier,
  onGoTeam,
  onNewChantier,
  onDismiss,
  t,
}: Props) {
  const hasCommercial = teamMembers.some((m) => m.role === "commercial");
  const hasTech = teamMembers.some((m) => m.role === "technician");

  return (
    <View style={styles.card} testID="onboarding-card">
      <View style={styles.header}>
        <Text style={styles.title}>{t("onboarding.title")}</Text>
        <TouchableOpacity
          testID="onboarding-skip"
          onPress={onDismiss}
          style={styles.closeBtn}
          activeOpacity={0.7}
          hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
        >
          <Ionicons name="close" size={18} color={colors.textSecondary} />
        </TouchableOpacity>
      </View>
      <Text style={styles.sub}>{t("onboarding.subtitle")}</Text>

      {/* Étape 1 — Commercial */}
      <Step
        done={hasCommercial}
        num="1"
        title={t("onboarding.step1Title")}
        desc={t("onboarding.step1Desc")}
        ctaLabel={t("onboarding.step1Btn")}
        ctaIcon="people"
        onPress={onGoTeam}
        testID="onboarding-step1-btn"
      />

      {/* Étape 2 — Technicien */}
      <Step
        done={hasTech}
        num="2"
        title={t("onboarding.step2Title")}
        desc={t("onboarding.step2Desc")}
        ctaLabel={t("onboarding.step2Btn")}
        ctaIcon="construct"
        onPress={onGoTeam}
        testID="onboarding-step2-btn"
      />

      {/* Étape 3 — Premier chantier */}
      <Step
        done={hasChantier}
        num="3"
        title={t("onboarding.step3Title")}
        desc={t("onboarding.step3Desc")}
        ctaLabel={t("onboarding.step3Btn")}
        ctaIcon="add-circle"
        onPress={onNewChantier}
        testID="onboarding-step3-btn"
      />

      <TouchableOpacity
        testID="onboarding-hide-link"
        onPress={onDismiss}
        activeOpacity={0.7}
        style={styles.skipLink}
      >
        <Text style={styles.skipLinkText}>{t("onboarding.skip")}</Text>
      </TouchableOpacity>
    </View>
  );
}

type StepProps = {
  done: boolean;
  num: string;
  title: string;
  desc: string;
  ctaLabel: string;
  ctaIcon: keyof typeof Ionicons.glyphMap;
  onPress: () => void;
  testID?: string;
};
function Step({ done, num, title, desc, ctaLabel, ctaIcon, onPress, testID }: StepProps) {
  return (
    <View style={styles.step}>
      <View style={[styles.badge, done && styles.badgeDone]}>
        {done ? (
          <Ionicons name="checkmark" size={14} color="#000" />
        ) : (
          <Text style={styles.badgeNum}>{num}</Text>
        )}
      </View>
      <View style={{ flex: 1 }}>
        <Text style={styles.stepTitle}>{title}</Text>
        <Text style={styles.stepDesc}>{desc}</Text>
        {!done && (
          <TouchableOpacity
            testID={testID}
            onPress={onPress}
            activeOpacity={0.85}
            style={styles.stepBtn}
          >
            <Ionicons name={ctaIcon} size={14} color={colors.primary} />
            <Text style={styles.stepBtnText}>{ctaLabel}</Text>
          </TouchableOpacity>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: colors.primary,
    padding: 16,
    marginBottom: 16,
    gap: 12,
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  title: {
    color: colors.textPrimary,
    fontWeight: "900",
    fontSize: 16,
    letterSpacing: 0.3,
  },
  closeBtn: { padding: 4 },
  sub: {
    color: colors.textSecondary,
    fontSize: 13,
    lineHeight: 18,
    marginTop: -4,
  },
  step: {
    flexDirection: "row",
    gap: 12,
    alignItems: "flex-start",
  },
  badge: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: colors.bg,
    borderWidth: 2,
    borderColor: colors.borderSubtle,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 2,
  },
  badgeDone: {
    backgroundColor: colors.success,
    borderColor: colors.success,
  },
  badgeNum: {
    color: colors.textPrimary,
    fontWeight: "900",
    fontSize: 13,
  },
  stepTitle: {
    color: colors.textPrimary,
    fontWeight: "800",
    fontSize: 14,
  },
  stepDesc: {
    color: colors.textSecondary,
    fontSize: 12,
    lineHeight: 17,
    marginTop: 2,
  },
  stepBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    alignSelf: "flex-start",
    backgroundColor: colors.bg,
    borderWidth: 1,
    borderColor: colors.primary,
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderRadius: 8,
    marginTop: 8,
  },
  stepBtnText: {
    color: colors.primary,
    fontWeight: "800",
    fontSize: 12,
    letterSpacing: 0.3,
  },
  skipLink: {
    alignItems: "center",
    paddingVertical: 4,
  },
  skipLinkText: {
    color: colors.textSecondary,
    fontSize: 12,
    fontStyle: "italic",
  },
});
