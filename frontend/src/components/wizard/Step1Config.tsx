/**
 * Step1Config — Wizard Étape 1/3 : configuration du mur (maçonnerie + isolation).
 * Extrait de new-mesure.tsx (refacto V3 — juin 2026).
 */
import React from "react";
import { Text, TouchableOpacity, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
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
  return (
    <View>
      <Text style={styles.h1}>CONFIGURATION DU MUR</Text>
      <Text style={styles.h2}>Étape 1/3 · Structure de la maison (fait 1 seule fois)</Text>

      {/* Type de projet */}
      <Text style={[styles.sectionLabel, { marginTop: 22 }]}>TYPE DE PROJET *</Text>
      <View style={styles.row2}>
        <SegBtn
          testID="project-construction"
          icon="home-outline"
          label="Nouvelle Construction"
          active={s1.project_type === "construction"}
          onPress={() => setField("project_type", "construction")}
        />
        <SegBtn
          testID="project-renovation"
          icon="construct-outline"
          label="Rénovation"
          active={s1.project_type === "renovation"}
          onPress={() => setField("project_type", "renovation")}
        />
      </View>

      {/* Maçonnerie */}
      <Text style={[styles.sectionLabel, { marginTop: 22 }]}>
        TYPE DE MAÇONNERIE * {err.masonry_type && <Text style={styles.errInline}> ⚠</Text>}
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
              <Text style={[styles.facadeLabel, active && { color: colors.primary }]}>{m.label}</Text>
            </TouchableOpacity>
          );
        })}
      </View>

      {/* Épaisseur Gros Œuvre */}
      {s1.masonry_type && (
        <CotField
          testID="input-gros-oeuvre"
          label="ÉPAISSEUR DU GROS ŒUVRE (mm) *"
          value={s1.gros_oeuvre_mm}
          onChange={(v) => setField("gros_oeuvre_mm", v.replace(",", "."))}
          error={!!err.gros_oeuvre_mm}
        />
      )}

      {/* Isolation & Finition */}
      <Text style={[styles.sectionLabel, { marginTop: 22 }]}>
        ISOLATION & FINITION * {err.insulation_mode && <Text style={styles.errInline}> ⚠</Text>}
      </Text>
      <View style={{ gap: 8 }}>
        <InsulationOption
          testID="insul-none"
          active={s1.insulation_mode === "none"}
          icon="reader-outline"
          label="Mur plein sans isolation"
          onPress={() => setField("insulation_mode", "none")}
        />
        <InsulationOption
          testID="insul-iti"
          active={s1.insulation_mode === "iti"}
          icon="layers-outline"
          label="Isolation Intérieure (ITI)"
          onPress={() => setField("insulation_mode", "iti")}
        />
        {s1.insulation_mode === "iti" && (
          <CotField
            testID="input-iti-thickness"
            label="ÉPAISSEUR ISOLANT INT. (mm) *"
            value={s1.iti_thickness_mm}
            onChange={(v) => setField("iti_thickness_mm", v.replace(",", "."))}
            error={!!err.iti_thickness_mm}
          />
        )}
        <InsulationOption
          testID="insul-ite"
          active={s1.insulation_mode === "ite"}
          icon="albums-outline"
          label="Isolation Extérieure (ITE)"
          onPress={() => setField("insulation_mode", "ite")}
        />
        {s1.insulation_mode === "ite" && (
          <>
            <Text style={[styles.sectionLabel, { marginTop: 10 }]}>
              TYPE DE PAREMENT * {err.parement_type && <Text style={styles.errInline}> ⚠</Text>}
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
                    <Text style={[styles.facadeLabel, active && { color: colors.primary }]}>{p.label}</Text>
                  </TouchableOpacity>
                );
              })}
            </View>
            <CotField
              testID="input-ite-insul-thickness"
              label="ÉPAISSEUR ISOLANT (mm) *"
              value={s1.ite_insul_thickness_mm}
              onChange={(v) => setField("ite_insul_thickness_mm", v.replace(",", "."))}
              error={!!err.ite_insul_thickness_mm}
            />
            {s1.parement_type === "crepi" && (
              <CotField
                testID="input-crepi-thickness"
                label="ÉPAISSEUR CRÉPI (mm) *"
                value={s1.crepi_thickness_mm}
                onChange={(v) => setField("crepi_thickness_mm", v.replace(",", "."))}
                error={!!err.crepi_thickness_mm}
              />
            )}
            {(s1.parement_type === "brique_parement" || s1.parement_type === "pierre_parement") && (
              <>
                <CotField
                  testID="input-coulisse-thickness"
                  label="ÉPAISSEUR COULISSE / VIDE (mm) *"
                  value={s1.coulisse_thickness_mm}
                  onChange={(v) => setField("coulisse_thickness_mm", v.replace(",", "."))}
                  error={!!err.coulisse_thickness_mm}
                />
                <CotField
                  testID="input-brique-pierre-thickness"
                  label={`ÉPAISSEUR ${s1.parement_type === "brique_parement" ? "BRIQUE" : "PIERRE"} (mm) *`}
                  value={s1.brique_pierre_thickness_mm}
                  onChange={(v) => setField("brique_pierre_thickness_mm", v.replace(",", "."))}
                  error={!!err.brique_pierre_thickness_mm}
                />
              </>
            )}
            {s1.parement_type === "bardage" && (
              <CotField
                testID="input-structure-lame-air"
                label="ÉPAISSEUR STRUCTURE / LAME D'AIR (mm) *"
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
        STATUT DES SEUILS *
        {err.sill_already_installed && <Text style={styles.errInline}> ⚠</Text>}
      </Text>
      <View style={styles.row2}>
        <SegBtn
          testID="sill-yes"
          icon="checkmark-circle-outline"
          label="Oui, déjà posés"
          active={s1.sill_already_installed === true}
          onPress={() => setField("sill_already_installed", true)}
        />
        <SegBtn
          testID="sill-no"
          icon="close-circle-outline"
          label="Non, à venir"
          active={s1.sill_already_installed === false}
          onPress={() => setField("sill_already_installed", false)}
        />
      </View>
      {s1.sill_already_installed === false && (
        <CotField
          testID="input-sill-thickness"
          label="ÉPAISSEUR FUTURE DU SEUIL (mm)"
          value={s1.sill_thickness_mm}
          onChange={(v) => setField("sill_thickness_mm", v.replace(",", "."))}
          error={!!err.sill_thickness_mm}
        />
      )}
      {s1.sill_already_installed === false && (
        <Text style={styles.helpHint}>
          💡 Laissez vide ou indiquez 0 si aucun seuil ne sera posé
          (porte de garage, certains coulissants, rénovation sans seuil).
        </Text>
      )}

      <Text style={[styles.sectionLabel, { marginTop: 22 }]}>OPTIONS GLOBALES</Text>
      <CheckboxRow
        testID="opt-horizontal-cut"
        label="Coupe horizontale (Retour de butée)"
        sub="Présence d'un retour de butée horizontal"
        value={s1.has_horizontal_cut}
        onChange={(v) => setField("has_horizontal_cut", v)}
      />
      <Text style={styles.helpHint}>
        💡 L&apos;option « Allège » est désormais saisie par ouverture
        (étape « Cotes »), car elle peut varier d&apos;une baie à l&apos;autre.
      </Text>
    </View>
  );
}
