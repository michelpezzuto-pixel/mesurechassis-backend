import React, { useEffect, useState } from "react";
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
      Alert.alert("Nom invalide", "Le nom doit faire au moins 2 caractères.");
      return;
    }
    if (email.trim() && (!email.includes("@") || !email.includes("."))) {
      Alert.alert("Email invalide", "Vérifiez le format de votre email.");
      return;
    }
    if (wantsPasswordChange) {
      if (newPassword.length < 8) {
        Alert.alert(
          "Mot de passe trop court",
          "Le nouveau mot de passe doit faire au moins 8 caractères.",
        );
        return;
      }
      if (newPassword !== confirmPassword) {
        Alert.alert(
          "Confirmation incorrecte",
          "Le mot de passe et sa confirmation ne correspondent pas.",
        );
        return;
      }
    }
    if (sensitiveChange && !currentPassword) {
      Alert.alert(
        "Mot de passe actuel requis",
        "Pour changer votre email ou mot de passe, vous devez saisir votre mot de passe actuel.",
      );
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
        "✅ Informations mises à jour",
        emailChanged
          ? "Vos informations ont été enregistrées. Pensez à utiliser votre nouvel email pour vos prochaines connexions."
          : "Vos informations ont été enregistrées avec succès.",
        [{ text: "OK", onPress: () => router.back() }],
      );
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      Alert.alert(
        "Erreur",
        typeof detail === "string"
          ? detail
          : "Impossible de mettre à jour vos informations.",
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
          <Text style={styles.headerTitle}>Mes informations</Text>
          <View style={{ width: 26 }} />
        </View>

        <ScrollView
          style={styles.scroll}
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled"
        >
          {/* ===== IDENTITÉ ===== */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Identité</Text>

            <Text style={styles.label}>Nom affiché</Text>
            <TextInput
              style={styles.input}
              value={name}
              onChangeText={setName}
              placeholder="Votre nom"
              placeholderTextColor={colors.textSecondary}
              autoCapitalize="words"
              maxLength={80}
            />

            <Text style={styles.label}>Téléphone</Text>
            <TextInput
              style={styles.input}
              value={phone}
              onChangeText={setPhone}
              placeholder="+32 4XX XX XX XX"
              placeholderTextColor={colors.textSecondary}
              keyboardType="phone-pad"
              maxLength={30}
            />
          </View>

          {/* ===== EMAIL ===== */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Email de connexion</Text>
            <TextInput
              style={styles.input}
              value={email}
              onChangeText={setEmail}
              placeholder="votre@email.com"
              placeholderTextColor={colors.textSecondary}
              autoCapitalize="none"
              keyboardType="email-address"
              autoCorrect={false}
            />
            {emailChanged && (
              <Text style={styles.warnText}>
                ⚠️ Changement d&apos;email — confirmation du mot de passe requise
                ci-dessous.
              </Text>
            )}
          </View>

          {/* ===== MOT DE PASSE ===== */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Mot de passe</Text>
            <Text style={styles.hint}>
              Laissez vide pour ne pas changer votre mot de passe actuel.
            </Text>

            <Text style={styles.label}>Nouveau mot de passe</Text>
            <TextInput
              style={styles.input}
              value={newPassword}
              onChangeText={setNewPassword}
              placeholder="Min. 8 caractères"
              placeholderTextColor={colors.textSecondary}
              secureTextEntry
              autoCapitalize="none"
              maxLength={120}
            />

            {newPassword.length > 0 && (
              <>
                <Text style={styles.label}>Confirmer le mot de passe</Text>
                <TextInput
                  style={styles.input}
                  value={confirmPassword}
                  onChangeText={setConfirmPassword}
                  placeholder="Saisissez à nouveau"
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
                🔒 Confirmation d&apos;identité
              </Text>
              <Text style={styles.hint}>
                Pour modifier votre email ou mot de passe, saisissez votre
                mot de passe actuel.
              </Text>
              <Text style={styles.label}>Mot de passe actuel</Text>
              <TextInput
                style={styles.input}
                value={currentPassword}
                onChangeText={setCurrentPassword}
                placeholder="Votre mot de passe actuel"
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
                <Text style={styles.saveBtnText}>
                  Enregistrer mes modifications
                </Text>
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
