/**
 * LanguagePicker — Sélecteur de langue compact (FR / NL / EN).
 *
 * Utilisé dans l'écran "Profil utilisateur" (me.tsx). Au changement,
 * la préférence est persistée dans AsyncStorage (clé `mc.lang`) et
 * appliquée immédiatement à toute l'app via i18next.
 */
import React from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useTranslation } from "react-i18next";
import { colors } from "@/src/theme";
import { setLanguage, SupportedLanguage, SUPPORTED_LANGUAGES } from "@/src/i18n";

const LABELS: Record<SupportedLanguage, { code: string; flag: string; label: string }> = {
  fr: { code: "FR", flag: "🇫🇷", label: "Français" },
  nl: { code: "NL", flag: "🇧🇪", label: "Nederlands" },
  en: { code: "EN", flag: "🇬🇧", label: "English" },
};

export function LanguagePicker() {
  const { t, i18n } = useTranslation();
  const current = (i18n.language?.split("-")[0] || "fr") as SupportedLanguage;

  return (
    <View style={styles.wrap}>
      <View style={styles.headerRow}>
        <Ionicons name="globe-outline" size={18} color={colors.primary} />
        <Text style={styles.title}>{t("settings.language")}</Text>
      </View>
      <Text style={styles.hint}>{t("settings.languageHint")}</Text>
      <View style={styles.row}>
        {SUPPORTED_LANGUAGES.map((lng) => {
          const meta = LABELS[lng];
          const active = current === lng;
          return (
            <TouchableOpacity
              key={lng}
              testID={`lang-${lng}`}
              onPress={() => setLanguage(lng)}
              activeOpacity={0.85}
              style={[styles.pill, active && styles.pillActive]}
            >
              <Text style={styles.flag}>{meta.flag}</Text>
              <Text style={[styles.pillCode, active && styles.pillCodeActive]}>
                {meta.code}
              </Text>
              <Text style={[styles.pillLabel, active && styles.pillLabelActive]}>
                {meta.label}
              </Text>
              {active && (
                <Ionicons
                  name="checkmark-circle"
                  size={16}
                  color="#000"
                  style={{ marginLeft: 4 }}
                />
              )}
            </TouchableOpacity>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    padding: 14,
    marginBottom: 12,
  },
  headerRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  title: {
    color: colors.textPrimary,
    fontWeight: "800",
    fontSize: 14,
    letterSpacing: 0.4,
  },
  hint: {
    color: colors.textSecondary,
    fontSize: 12,
    marginTop: 4,
    marginBottom: 10,
  },
  row: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  pill: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    backgroundColor: colors.bg,
    minHeight: 40,
  },
  pillActive: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  flag: {
    fontSize: 16,
  },
  pillCode: {
    color: colors.textSecondary,
    fontWeight: "900",
    fontSize: 12,
    letterSpacing: 0.5,
  },
  pillCodeActive: { color: "#000" },
  pillLabel: {
    color: colors.textPrimary,
    fontSize: 12,
    fontWeight: "700",
  },
  pillLabelActive: { color: "#000" },
});
