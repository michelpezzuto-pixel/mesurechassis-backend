/**
 * AppointmentPicker — Modal plein écran avec calendrier MOIS COMPLET +
 * sélection de l'heure et des minutes.
 *
 * Avant : on utilisait `<input type="date">` (web) qui était illisible en dark mode,
 * et `@react-native-community/datetimepicker` (natif) qui s'affichait en mini-overlay.
 *
 * Maintenant : un seul comportement cross-platform, design propre, calendrier en
 * français, navigation entre les mois, sélecteurs heure/minute clairs.
 */
import React, { useEffect, useMemo, useState } from "react";
import {
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { Calendar, LocaleConfig } from "react-native-calendars";
import { colors } from "@/src/theme";

// Locale FR pour react-native-calendars
LocaleConfig.locales["fr"] = {
  monthNames: [
    "Janvier",
    "Février",
    "Mars",
    "Avril",
    "Mai",
    "Juin",
    "Juillet",
    "Août",
    "Septembre",
    "Octobre",
    "Novembre",
    "Décembre",
  ],
  monthNamesShort: [
    "Janv.",
    "Févr.",
    "Mars",
    "Avr.",
    "Mai",
    "Juin",
    "Juil.",
    "Août",
    "Sept.",
    "Oct.",
    "Nov.",
    "Déc.",
  ],
  dayNames: [
    "Dimanche",
    "Lundi",
    "Mardi",
    "Mercredi",
    "Jeudi",
    "Vendredi",
    "Samedi",
  ],
  dayNamesShort: ["Dim.", "Lun.", "Mar.", "Mer.", "Jeu.", "Ven.", "Sam."],
  today: "Aujourd'hui",
};
LocaleConfig.defaultLocale = "fr";

export type AppointmentPickerProps = {
  visible: boolean;
  /** Valeur ISO "YYYY-MM-DDTHH:mm" ou null. */
  value: string | null;
  onClose: () => void;
  /** Renvoie la nouvelle valeur ISO "YYYY-MM-DDTHH:mm". */
  onConfirm: (iso: string) => void;
  /** Label optionnel ("Date du rendez-vous", etc.) — défaut : "Choisir un créneau". */
  title?: string;
};

const HOURS = Array.from({ length: 24 }, (_, i) => i);
const MINUTES = [0, 15, 30, 45];

function pad2(n: number): string {
  return n < 10 ? `0${n}` : String(n);
}

export default function AppointmentPicker({
  visible,
  value,
  onClose,
  onConfirm,
  title,
}: AppointmentPickerProps) {
  // Initial date : value si fournie, sinon aujourd'hui à 09:00
  const initial = useMemo(() => {
    if (value) {
      const d = new Date(value);
      if (!isNaN(d.getTime())) return d;
    }
    const now = new Date();
    now.setHours(9, 0, 0, 0);
    return now;
  }, [value]);

  const [selectedDate, setSelectedDate] = useState<Date>(initial);
  const [hour, setHour] = useState<number>(initial.getHours());
  const [minute, setMinute] = useState<number>(
    MINUTES.reduce(
      (prev, cur) =>
        Math.abs(cur - initial.getMinutes()) <
        Math.abs(prev - initial.getMinutes())
          ? cur
          : prev,
      0,
    ),
  );

  // Reset quand la modal se réouvre
  useEffect(() => {
    if (visible) {
      setSelectedDate(initial);
      setHour(initial.getHours());
      setMinute(
        MINUTES.reduce(
          (prev, cur) =>
            Math.abs(cur - initial.getMinutes()) <
            Math.abs(prev - initial.getMinutes())
              ? cur
              : prev,
          0,
        ),
      );
    }
  }, [visible, initial]);

  const dateKey = useMemo(() => {
    const y = selectedDate.getFullYear();
    const m = pad2(selectedDate.getMonth() + 1);
    const d = pad2(selectedDate.getDate());
    return `${y}-${m}-${d}`;
  }, [selectedDate]);

  const summary = useMemo(() => {
    const d = new Date(selectedDate);
    d.setHours(hour, minute, 0, 0);
    return d.toLocaleString("fr-FR", {
      weekday: "long",
      day: "2-digit",
      month: "long",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }, [selectedDate, hour, minute]);

  const handleConfirm = () => {
    const y = selectedDate.getFullYear();
    const m = pad2(selectedDate.getMonth() + 1);
    const d = pad2(selectedDate.getDate());
    const iso = `${y}-${m}-${d}T${pad2(hour)}:${pad2(minute)}`;
    onConfirm(iso);
    onClose();
  };

  return (
    <Modal
      visible={visible}
      animationType="slide"
      transparent={false}
      presentationStyle="fullScreen"
      onRequestClose={onClose}
    >
      <View style={styles.container}>
        {/* Header */}
        <View style={styles.header}>
          <TouchableOpacity
            onPress={onClose}
            style={styles.headerBtn}
            hitSlop={8}
            testID="appointment-cancel"
          >
            <Ionicons name="close" size={26} color={colors.textPrimary} />
          </TouchableOpacity>
          <Text style={styles.title} numberOfLines={1}>
            {title || "Choisir un créneau"}
          </Text>
          <View style={styles.headerBtn} />
        </View>

        <ScrollView
          contentContainerStyle={{ paddingBottom: 30 }}
          keyboardShouldPersistTaps="handled"
        >
          {/* Résumé du choix actuel */}
          <View style={styles.summaryBox}>
            <Ionicons name="calendar" size={18} color={colors.primary} />
            <Text style={styles.summaryText} numberOfLines={2}>
              {summary}
            </Text>
          </View>

          {/* Calendrier mois complet */}
          <View style={styles.calendarWrap}>
            <Calendar
              key={dateKey}
              current={dateKey}
              onDayPress={(day) => {
                const next = new Date(day.timestamp);
                // Préserver l'heure et la minute sélectionnées
                next.setHours(hour, minute, 0, 0);
                setSelectedDate(next);
              }}
              markedDates={{
                [dateKey]: {
                  selected: true,
                  selectedColor: colors.primary,
                  selectedTextColor: "#000",
                },
              }}
              firstDay={1} // Lundi
              hideExtraDays={true}
              theme={{
                backgroundColor: colors.surface,
                calendarBackground: colors.surface,
                textSectionTitleColor: colors.textSecondary,
                dayTextColor: colors.textPrimary,
                todayTextColor: colors.primary,
                arrowColor: colors.primary,
                monthTextColor: colors.textPrimary,
                textMonthFontWeight: "800",
                textMonthFontSize: 18,
                textDayFontSize: 16,
                textDayFontWeight: "600",
                textDayHeaderFontSize: 12,
                textDayHeaderFontWeight: "700",
                disabledArrowColor: colors.textSecondary,
              }}
              style={styles.calendar}
            />
          </View>

          {/* Sélection heure & minute */}
          <View style={styles.timeBlock}>
            <Text style={styles.sectionLabel}>HEURE</Text>
            <View style={styles.timeRow}>
              <View style={styles.timeCol}>
                <Text style={styles.timeSubLabel}>Heure</Text>
                <ScrollView
                  showsVerticalScrollIndicator={false}
                  style={styles.scrollPicker}
                  contentContainerStyle={{ paddingVertical: 8 }}
                >
                  {HOURS.map((h) => (
                    <Pressable
                      key={`h-${h}`}
                      onPress={() => setHour(h)}
                      style={[
                        styles.scrollPickerItem,
                        h === hour && styles.scrollPickerItemActive,
                      ]}
                      testID={`appointment-hour-${h}`}
                    >
                      <Text
                        style={[
                          styles.scrollPickerText,
                          h === hour && styles.scrollPickerTextActive,
                        ]}
                      >
                        {pad2(h)}
                      </Text>
                    </Pressable>
                  ))}
                </ScrollView>
              </View>

              <Text style={styles.timeSeparator}>:</Text>

              <View style={styles.timeCol}>
                <Text style={styles.timeSubLabel}>Minutes</Text>
                <View style={{ gap: 8 }}>
                  {MINUTES.map((m) => (
                    <Pressable
                      key={`m-${m}`}
                      onPress={() => setMinute(m)}
                      style={[
                        styles.minutePill,
                        m === minute && styles.minutePillActive,
                      ]}
                      testID={`appointment-minute-${m}`}
                    >
                      <Text
                        style={[
                          styles.minutePillText,
                          m === minute && styles.minutePillTextActive,
                        ]}
                      >
                        {pad2(m)}
                      </Text>
                    </Pressable>
                  ))}
                </View>
              </View>
            </View>
          </View>
        </ScrollView>

        {/* CTA confirmer */}
        <View style={styles.footer}>
          <TouchableOpacity
            testID="appointment-confirm"
            onPress={handleConfirm}
            activeOpacity={0.85}
            style={styles.confirmBtn}
          >
            <Ionicons name="checkmark-circle" size={20} color="#000" />
            <Text style={styles.confirmText}>VALIDER LE CRÉNEAU</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 12,
    paddingVertical: Platform.OS === "ios" ? 14 : 10,
    paddingTop: Platform.OS === "ios" ? 50 : 14,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSubtle,
  },
  headerBtn: { width: 40, height: 40, alignItems: "center", justifyContent: "center" },
  title: {
    flex: 1,
    color: colors.textPrimary,
    fontWeight: "900",
    fontSize: 16,
    textAlign: "center",
    letterSpacing: 0.4,
  },
  summaryBox: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    backgroundColor: "rgba(255, 107, 26, 0.12)",
    borderWidth: 1,
    borderColor: "rgba(255, 107, 26, 0.35)",
    borderRadius: 12,
    paddingVertical: 12,
    paddingHorizontal: 16,
    marginHorizontal: 16,
    marginTop: 12,
  },
  summaryText: {
    flex: 1,
    color: colors.textPrimary,
    fontWeight: "700",
    fontSize: 14,
    lineHeight: 19,
  },
  calendarWrap: {
    marginHorizontal: 12,
    marginTop: 16,
    borderRadius: 14,
    overflow: "hidden",
    borderWidth: 1,
    borderColor: colors.borderSubtle,
  },
  calendar: { paddingBottom: 6 },
  timeBlock: { paddingHorizontal: 16, marginTop: 22 },
  sectionLabel: {
    color: colors.textSecondary,
    fontWeight: "800",
    letterSpacing: 1,
    fontSize: 11,
    marginBottom: 12,
  },
  timeRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 12,
    backgroundColor: colors.surface,
    borderRadius: 14,
    padding: 14,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
  },
  timeCol: { flex: 1 },
  timeSubLabel: {
    color: colors.textSecondary,
    fontSize: 11,
    fontWeight: "700",
    letterSpacing: 0.8,
    marginBottom: 8,
  },
  scrollPicker: {
    height: 180,
    backgroundColor: colors.bg,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
  },
  scrollPickerItem: {
    paddingVertical: 8,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 6,
    marginHorizontal: 6,
    marginVertical: 1,
  },
  scrollPickerItemActive: {
    backgroundColor: colors.primary,
  },
  scrollPickerText: {
    color: colors.textPrimary,
    fontSize: 18,
    fontWeight: "700",
    fontVariant: ["tabular-nums"],
  },
  scrollPickerTextActive: { color: "#000", fontWeight: "900" },
  timeSeparator: {
    color: colors.textPrimary,
    fontSize: 30,
    fontWeight: "900",
    paddingTop: 36,
  },
  minutePill: {
    paddingVertical: 12,
    paddingHorizontal: 14,
    borderRadius: 10,
    backgroundColor: colors.bg,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    alignItems: "center",
  },
  minutePillActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  minutePillText: { color: colors.textPrimary, fontSize: 16, fontWeight: "700" },
  minutePillTextActive: { color: "#000", fontWeight: "900" },
  footer: {
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: Platform.OS === "ios" ? 28 : 16,
    borderTopWidth: 1,
    borderTopColor: colors.borderSubtle,
    backgroundColor: colors.bg,
  },
  confirmBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
    backgroundColor: colors.primary,
    paddingVertical: 14,
    borderRadius: 14,
  },
  confirmText: {
    color: "#000",
    fontSize: 14,
    fontWeight: "900",
    letterSpacing: 1.2,
  },
});
