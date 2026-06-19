import React, { useEffect, useState } from "react";
import { LanguagePicker } from "@/src/components/LanguagePicker";
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import { useTranslation } from "react-i18next";
import { api } from "@/src/services/api";
import { useAuth } from "@/src/context/AuthContext";
import { colors } from "@/src/theme";

/**
 * Écran « Mes infos personnelles » — permet à l'utilisateur connecté
 * de modifier son nom, son email, son téléphone et son mot de passe.
 *
 * 🔒 Sécurité :
 *  - Le changement d'email ou de mot de passe exige la saisie du
 *    mot de passe actuel (protection contre vol de session).
 *  - Validations côté UI + backend.
 */
export default function MyInfoScreen() {
  const router = useRouter();
  const { t } = useTranslation();
  const { user, refreshUser } = useAuth();

  const [name, setName] = useState(user?.name || "");
  const [email, setEmail] = useState(user?.email || "");
  const [phone, setPhone] = useState((user && (user as { phone?: string }).phone) || "");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setName(user?.name || "");
    setEmail(user?.email || "");
    setPhone((user && (user as { phone?: string }).phone) || "");
  }, [user]);

  const emailChanged =
    email.trim().toLowerCase() !== (user?.email || "").toLowerCase();
  const wantsPasswordChange = newPassword.length > 0;
  const sensitiveChange = emailChanged || wantsPasswordChange;

  const handleSave = async () => {
    // Validations UI
    if (name.trim().length < 2) {
      Alert.alert(t("screens.me.alerts.nameInvalid"), t("screens.me.alerts.nameInvalidMsg"));
      return;
    }
    if (email.trim() && (!email.includes("@") || !email.includes("."))) {
      Alert.alert(t("screens.me.alerts.emailInvalid"), t("screens.me.alerts.emailInvalidMsg"));
      return;
    }
    if (wantsPasswordChange) {
      if (newPassword.length < 8) {
        Alert.alert(t("screens.me.alerts.passwordShort"), t("screens.me.alerts.passwordShortMsg"));
        return;
      }
      if (newPassword !== confirmPassword) {
        Alert.alert(t("screens.me.alerts.confirmKO"), t("screens.me.alerts.confirmKOMsg"));
        return;
      }
    }
    if (sensitiveChange && !currentPassword) {
      Alert.alert(t("screens.me.alerts.currentRequired"), t("screens.me.alerts.currentRequiredMsg"));
      return;
    }

    const payload: any = {
      name: name.trim(),
      phone: phone.trim(),
    };
    if (emailChanged) payload.email = email.trim().toLowerCase();
    if (wantsPasswordChange) payload.new_password = newPassword;
    if (sensitiveChange) payload.current_password = currentPassword;

    setSaving(true);
    try {
      await api.patch("/auth/me", payload);
      try {
        await refreshUser();
      } catch {
        // best effort
      }
      Alert.alert(
        t("screens.me.alerts.saved"),
        emailChanged
          ? t("screens.me.alerts.savedEmailChange")
          : t("screens.me.alerts.savedDefault"),
        [{ text: t("common.ok"), onPress: () => router.back() }],
      );
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      Alert.alert(
        t("common.error"),
        typeof detail === "string" ? detail : t("screens.me.alerts.errorDefault"),
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top", "bottom"]}>
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        style={{ flex: 1 }}
      >
        <View style={styles.header}>
          <TouchableOpacity
            onPress={() => router.back()}
            style={styles.backBtn}
            hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
          >
            <Ionicons name="chevron-back" size={26} color={colors.textPrimary} />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>{t("screens.me.title")}</Text>
          <View style={{ width: 26 }} />
        </View>

        <ScrollView
          style={styles.scroll}
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled"
        >
          {/* 🆕 V3 — Sélecteur de langue (FR/NL/EN) */}
          <LanguagePicker />

          {/* 🆕 Build 9 — Accès au système de parrainage */}
          <TouchableOpacity
            testID="open-referral-btn"
            onPress={() => router.push("/referral")}
            activeOpacity={0.85}
            style={styles.referralCard}
          >
            <View style={styles.referralIcon}>
              <Ionicons name="gift" size={22} color={colors.primary} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.referralTitle}>{t("screens.me.referralCard")}</Text>
              <Text style={styles.referralDesc}>
                {t("screens.me.referralDesc")}
              </Text>
            </View>
            <Ionicons name="chevron-forward" size={22} color={colors.textSecondary} />
          </TouchableOpacity>

          {/* 🆕 Build 9 — Accès direct au Centre d'aide / FAQ */}
          <TouchableOpacity
            testID="open-help-btn"
            onPress={() => router.push("/help")}
            activeOpacity={0.85}
            style={styles.referralCard}
          >
            <View style={[styles.referralIcon, { backgroundColor: "rgba(59, 130, 246, 0.16)" }]}>
              <Ionicons name="help-circle" size={22} color="#3B82F6" />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.referralTitle}>Centre d&apos;aide</Text>
              <Text style={styles.referralDesc}>
                FAQ, guide des formules, parrainage, prise de mesures…
              </Text>
            </View>
            <Ionicons name="chevron-forward" size={22} color={colors.textSecondary} />
          </TouchableOpacity>

          {/* ===== IDENTITÉ ===== */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>{t("screens.me.identity")}</Text>

            <Text style={styles.label}>{t("screens.me.displayName")}</Text>
            <TextInput
              style={styles.input}
              value={name}
              onChangeText={setName}
              placeholder={t("screens.me.namePlaceholder")}
              placeholderTextColor={colors.textSecondary}
              autoCapitalize="words"
              maxLength={80}
            />

            <Text style={styles.label}>{t("screens.me.phone")}</Text>
            <TextInput
              style={styles.input}
              value={phone}
              onChangeText={setPhone}
              placeholder={t("screens.me.phonePlaceholder")}
              placeholderTextColor={colors.textSecondary}
              keyboardType="phone-pad"
              maxLength={30}
            />
          </View>

          {/* ===== EMAIL ===== */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>{t("screens.me.loginEmail")}</Text>
            <TextInput
              style={styles.input}
              value={email}
              onChangeText={setEmail}
              placeholder={t("screens.me.emailPlaceholder")}
              placeholderTextColor={colors.textSecondary}
              autoCapitalize="none"
              keyboardType="email-address"
              autoCorrect={false}
            />
            {emailChanged && (
              <Text style={styles.warnText}>
                {t("screens.me.emailChangedWarn")}
              </Text>
            )}
          </View>

          {/* ===== MOT DE PASSE ===== */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>{t("screens.me.password")}</Text>
            <Text style={styles.hint}>{t("screens.me.passwordHint")}</Text>

            <Text style={styles.label}>{t("screens.me.newPassword")}</Text>
            <TextInput
              style={styles.input}
              value={newPassword}
              onChangeText={setNewPassword}
              placeholder={t("screens.me.newPasswordPlaceholder")}
              placeholderTextColor={colors.textSecondary}
              secureTextEntry
              autoCapitalize="none"
              maxLength={120}
            />

            {newPassword.length > 0 && (
              <>
                <Text style={styles.label}>{t("screens.me.confirmPassword")}</Text>
                <TextInput
                  style={styles.input}
                  value={confirmPassword}
                  onChangeText={setConfirmPassword}
                  placeholder={t("screens.me.confirmPlaceholder")}
                  placeholderTextColor={colors.textSecondary}
                  secureTextEntry
                  autoCapitalize="none"
                  maxLength={120}
                />
              </>
            )}
          </View>

          {/* ===== CONFIRMATION D'IDENTITÉ ===== */}
          {sensitiveChange && (
            <View style={[styles.section, styles.sectionSensitive]}>
              <Text style={styles.sectionTitle}>
                {t("screens.me.confirmIdentity")}
              </Text>
              <Text style={styles.hint}>{t("screens.me.confirmIdentityHint")}</Text>
              <Text style={styles.label}>{t("screens.me.currentPassword")}</Text>
              <TextInput
                style={styles.input}
                value={currentPassword}
                onChangeText={setCurrentPassword}
                placeholder={t("screens.me.currentPasswordPlaceholder")}
                placeholderTextColor={colors.textSecondary}
                secureTextEntry
                autoCapitalize="none"
                maxLength={120}
              />
            </View>
          )}

          {/* ===== SAVE BUTTON ===== */}
          <TouchableOpacity
            style={[styles.saveBtn, saving && { opacity: 0.6 }]}
            onPress={handleSave}
            disabled={saving}
            activeOpacity={0.85}
          >
            {saving ? (
              <ActivityIndicator color="#000" />
            ) : (
              <>
                <Ionicons
                  name="checkmark-circle"
                  size={20}
                  color="#000"
                />
                <Text style={styles.saveBtnText}>{t("screens.me.saveBtn")}</Text>
              </>
            )}
          </TouchableOpacity>

          <View style={{ height: 32 }} />
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  // 🆕 Build 9 — Carte d'accès au parrainage
  referralCard: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    backgroundColor: colors.surface,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    padding: 14,
    marginBottom: 12,
  },
  referralIcon: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: "rgba(255, 107, 26, 0.08)",
    alignItems: "center",
    justifyContent: "center",
  },
  referralTitle: {
    color: colors.textPrimary,
    fontSize: 14,
    fontWeight: "800",
  },
  referralDesc: {
    color: colors.textSecondary,
    fontSize: 12,
    marginTop: 2,
    lineHeight: 16,
  },
  safe: { flex: 1, backgroundColor: colors.bg },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.borderSubtle,
  },
  backBtn: { padding: 4 },
  headerTitle: {
    color: colors.textPrimary,
    fontSize: 17,
    fontWeight: "600",
  },
  scroll: { flex: 1 },
  scrollContent: { padding: 16 },
  section: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.borderSubtle,
  },
  sectionSensitive: {
    borderColor: colors.warning,
    borderWidth: 1,
  },
  sectionTitle: {
    color: colors.textPrimary,
    fontSize: 15,
    fontWeight: "700",
    marginBottom: 12,
  },
  label: {
    color: colors.textSecondary,
    fontSize: 13,
    fontWeight: "500",
    marginTop: 10,
    marginBottom: 6,
  },
  input: {
    backgroundColor: colors.inputBg,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.borderSubtle,
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: Platform.OS === "ios" ? 14 : 10,
    color: colors.textPrimary,
    fontSize: 15,
  },
  hint: {
    color: colors.textSecondary,
    fontSize: 12,
    marginBottom: 4,
    lineHeight: 17,
  },
  warnText: {
    color: colors.warning,
    fontSize: 12,
    marginTop: 8,
    lineHeight: 17,
  },
  saveBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    backgroundColor: colors.primary,
    paddingVertical: 16,
    borderRadius: 12,
    marginTop: 8,
  },
  saveBtnText: {
    color: "#000",
    fontSize: 16,
    fontWeight: "700",
  },
});
