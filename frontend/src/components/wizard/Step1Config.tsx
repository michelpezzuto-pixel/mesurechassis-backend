/**
 * Step1Config — Wizard Étape 1/3 : configuration du mur (maçonnerie + isolation).
 * Extrait de new-mesure.tsx (refacto V3 — juin 2026).
 */
import React from "react";
import { Text, TouchableOpacity, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useTranslation } from "react-i18next";
import { colors } from "@/src/theme";
import { wizardStyles as styles } from "./wizardStyles";
import { CheckboxRow, CotField, InsulationOption, SegBtn } from "./primitives";
import { MASONRIES, PAREMENTS, Step1Data } from "./types";

export function Step1Config({
  s1,
  setField,
  err,
}: {
  s1: Step1Data;
  setField: <K extends keyof Step1Data>(k: K, v: Step1Data[K]) => void;
  err: Record<string, boolean>;
}) {
  const { t } = useTranslation();
  // Helper : récupère le libellé traduit d'une maçonnerie depuis le JSON i18n.
  const masonryLabel = (key: string) =>
    t(`wizard.step1.masonry.${key}`, { defaultValue: key });
  const parementLabel = (key: string) =>
    t(`wizard.step1.parement.${key}`, { defaultValue: key });

  return (
    <View>
      <Text style={styles.h1}>{t("wizard.step1.title")}</Text>
      <Text style={styles.h2}>{t("wizard.step1.subtitle")}</Text>

      {/* Type de projet */}
      <Text style={[styles.sectionLabel, { marginTop: 22 }]}>
        {t("wizard.step1.projectType")}
      </Text>
      <View style={styles.row2}>
        <SegBtn
          testID="project-construction"
          icon="home-outline"
          label={t("wizard.step1.construction")}
          active={s1.project_type === "construction"}
          onPress={() => setField("project_type", "construction")}
        />
        <SegBtn
          testID="project-renovation"
          icon="construct-outline"
          label={t("wizard.step1.renovation")}
          active={s1.project_type === "renovation"}
          onPress={() => setField("project_type", "renovation")}
        />
      </View>

      {/* Maçonnerie */}
      <Text style={[styles.sectionLabel, { marginTop: 22 }]}>
        {t("wizard.step1.masonryType")} {err.masonry_type && <Text style={styles.errInline}> ⚠</Text>}
      </Text>
      <View style={styles.facadeGrid}>
        {MASONRIES.map((m) => {
          const active = s1.masonry_type === m.key;
          return (
            <TouchableOpacity
              key={m.key}
              testID={`masonry-${m.key}`}
              onPress={() => setField("masonry_type", m.key)}
              activeOpacity={0.85}
              style={[
                styles.facadeCard,
                active && styles.facadeCardActive,
                err.masonry_type && !active && { borderColor: colors.anomaly },
              ]}
            >
              <Ionicons name={m.icon} size={22} color={active ? colors.primary : colors.textSecondary} />
              <Text style={[styles.facadeLabel, active && { color: colors.primary }]}>
                {masonryLabel(m.key)}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>

      {/* Épaisseur Gros Œuvre */}
      {s1.masonry_type && (
        <CotField
          testID="input-gros-oeuvre"
          label={t("wizard.step1.grosOeuvre")}
          value={s1.gros_oeuvre_mm}
          onChange={(v) => setField("gros_oeuvre_mm", v.replace(",", "."))}
          error={!!err.gros_oeuvre_mm}
        />
      )}

      {/* Isolation & Finition */}
      <Text style={[styles.sectionLabel, { marginTop: 22 }]}>
        {t("wizard.step1.insulation")} {err.insulation_mode && <Text style={styles.errInline}> ⚠</Text>}
      </Text>
      <View style={{ gap: 8 }}>
        <InsulationOption
          testID="insul-none"
          active={s1.insulation_mode === "none"}
          icon="reader-outline"
          label={t("wizard.step1.insulNone")}
          onPress={() => setField("insulation_mode", "none")}
        />
        <InsulationOption
          testID="insul-iti"
          active={s1.insulation_mode === "iti"}
          icon="layers-outline"
          label={t("wizard.step1.insulIti")}
          onPress={() => setField("insulation_mode", "iti")}
        />
        {s1.insulation_mode === "iti" && (
          <CotField
            testID="input-iti-thickness"
            label={t("wizard.step1.itiThickness")}
            value={s1.iti_thickness_mm}
            onChange={(v) => setField("iti_thickness_mm", v.replace(",", "."))}
            error={!!err.iti_thickness_mm}
          />
        )}
        <InsulationOption
          testID="insul-ite"
          active={s1.insulation_mode === "ite"}
          icon="albums-outline"
          label={t("wizard.step1.insulIte")}
          onPress={() => setField("insulation_mode", "ite")}
        />
        {s1.insulation_mode === "ite" && (
          <>
            <Text style={[styles.sectionLabel, { marginTop: 10 }]}>
              {t("wizard.step1.parementType")} {err.parement_type && <Text style={styles.errInline}> ⚠</Text>}
            </Text>
            <View style={styles.facadeGrid}>
              {PAREMENTS.map((p) => {
                const active = s1.parement_type === p.key;
                return (
                  <TouchableOpacity
                    key={p.key}
                    testID={`parement-${p.key}`}
                    onPress={() => setField("parement_type", p.key)}
                    activeOpacity={0.85}
                    style={[
                      styles.facadeCard,
                      active && styles.facadeCardActive,
                      err.parement_type && !active && { borderColor: colors.anomaly },
                    ]}
                  >
                    <Ionicons name={p.icon} size={22} color={active ? colors.primary : colors.textSecondary} />
                    <Text style={[styles.facadeLabel, active && { color: colors.primary }]}>
                      {parementLabel(p.key)}
                    </Text>
                  </TouchableOpacity>
                );
              })}
            </View>
            <CotField
              testID="input-ite-insul-thickness"
              label={t("wizard.step1.iteInsul")}
              value={s1.ite_insul_thickness_mm}
              onChange={(v) => setField("ite_insul_thickness_mm", v.replace(",", "."))}
              error={!!err.ite_insul_thickness_mm}
            />
            {s1.parement_type === "crepi" && (
              <CotField
                testID="input-crepi-thickness"
                label={t("wizard.step1.crepiThickness")}
                value={s1.crepi_thickness_mm}
                onChange={(v) => setField("crepi_thickness_mm", v.replace(",", "."))}
                error={!!err.crepi_thickness_mm}
              />
            )}
            {(s1.parement_type === "brique_parement" || s1.parement_type === "pierre_parement") && (
              <>
                <CotField
                  testID="input-coulisse-thickness"
                  label={t("wizard.step1.coulisseThickness")}
                  value={s1.coulisse_thickness_mm}
                  onChange={(v) => setField("coulisse_thickness_mm", v.replace(",", "."))}
                  error={!!err.coulisse_thickness_mm}
                />
                <CotField
                  testID="input-brique-pierre-thickness"
                  label={
                    s1.parement_type === "brique_parement"
                      ? t("wizard.step1.briqueThickness")
                      : t("wizard.step1.pierreThickness")
                  }
                  value={s1.brique_pierre_thickness_mm}
                  onChange={(v) => setField("brique_pierre_thickness_mm", v.replace(",", "."))}
                  error={!!err.brique_pierre_thickness_mm}
                />
              </>
            )}
            {s1.parement_type === "bardage" && (
              <CotField
                testID="input-structure-lame-air"
                label={t("wizard.step1.bardageThickness")}
                value={s1.structure_lame_air_mm}
                onChange={(v) => setField("structure_lame_air_mm", v.replace(",", "."))}
                error={!!err.structure_lame_air_mm}
              />
            )}
          </>
        )}
      </View>

      {/* Statut Seuils */}
      <Text style={[styles.sectionLabel, { marginTop: 22 }]}>
        {t("wizard.step1.sillStatus")}
        {err.sill_already_installed && <Text style={styles.errInline}> ⚠</Text>}
      </Text>
      <View style={styles.row2}>
        <SegBtn
          testID="sill-yes"
          icon="checkmark-circle-outline"
          label={t("wizard.step1.sillYes")}
          active={s1.sill_already_installed === true}
          onPress={() => setField("sill_already_installed", true)}
        />
        <SegBtn
          testID="sill-no"
          icon="close-circle-outline"
          label={t("wizard.step1.sillNo")}
          active={s1.sill_already_installed === false}
          onPress={() => setField("sill_already_installed", false)}
        />
      </View>
      {s1.sill_already_installed === false && (
        <CotField
          testID="input-sill-thickness"
          label={t("wizard.step1.sillThickness")}
          value={s1.sill_thickness_mm}
          onChange={(v) => setField("sill_thickness_mm", v.replace(",", "."))}
          error={!!err.sill_thickness_mm}
        />
      )}
      {s1.sill_already_installed === false && (
        <Text style={styles.helpHint}>{t("wizard.step1.sillHint")}</Text>
      )}

      <Text style={[styles.sectionLabel, { marginTop: 22 }]}>
        {t("wizard.step1.globalOptions")}
      </Text>
      <CheckboxRow
        testID="opt-horizontal-cut"
        label={t("wizard.step1.horizontalCut")}
        sub={t("wizard.step1.horizontalCutSub")}
        value={s1.has_horizontal_cut}
        onChange={(v) => setField("has_horizontal_cut", v)}
      />
      <Text style={styles.helpHint}>{t("wizard.step1.allegeHint")}</Text>
    </View>
  );
}
