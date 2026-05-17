import React, { useCallback, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useFocusEffect, useRouter } from "expo-router";
import { api } from "@/src/services/api";
import { useAuth } from "@/src/context/AuthContext";
import { colors } from "@/src/theme";

export default function CompanyProfile() {
  const router = useRouter();
  const { user, company, refreshCompany } = useAuth();
  const [name, setName] = useState("");
  const [artisanMode, setArtisanMode] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const fetchProfile = useCallback(async () => {
    try {
      const res = await api.get("/company/profile");
      setName(res.data?.name ?? "");
      setArtisanMode(!!res.data?.artisan_mode);
    } catch {
      Alert.alert("Erreur", "Impossible de charger le profil société.");
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      fetchProfile();
    }, [fetchProfile])
  );

  const save = async () => {
    setSaving(true);
    try {
      await api.patch("/company/profile", {
        name: name.trim() || null,
        artisan_mode: artisanMode,
      });
      await refreshCompany();
      Alert.alert(
        "✅ Profil société mis à jour",
        artisanMode
          ? "Mode Artisan Unique activé — vous avez désormais accès à toutes les fonctionnalités."
          : "Mode Artisan Unique désactivé."
      );
    } catch (e: any) {
      const msg = e?.response?.status === 403
        ? "Réservé à l'administrateur de la société."
        : "Enregistrement impossible.";
      Alert.alert("Erreur", msg);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <View style={[styles.flex, styles.center]}>
        <ActivityIndicator color={colors.primary} size="large" />
      </View>
    );
  }

  const isAdmin = user?.role === "admin";

  return (
    <SafeAreaView style={styles.flex} edges={["top", "bottom"]}>
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        style={styles.flex}
      >
        <View style={styles.topBar}>
          <TouchableOpacity onPress={() => router.back()} hitSlop={10}>
            <Ionicons name="arrow-back" size={22} color={colors.textPrimary} />
          </TouchableOpacity>
          <Text style={styles.topTitle}>PROFIL SOCIÉTÉ</Text>
          <View style={{ width: 22 }} />
        </View>

        <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 120 }}>
          <View style={styles.card}>
            <Text style={styles.section}>IDENTITÉ</Text>
            <Text style={styles.label}>ID Société</Text>
            <View style={styles.badge}>
              <Ionicons name="business-outline" size={14} color={colors.textSecondary} />
              <Text style={styles.badgeText}>{company?.company_id ?? "default"}</Text>
            </View>

            <Text style={[styles.label, { marginTop: 16 }]}>Nom commercial</Text>
            <TextInput
              testID="company-name-input"
              value={name}
              onChangeText={setName}
              placeholder="Ex. Menuiserie Dupont SARL"
              placeholderTextColor={colors.placeholder}
              editable={isAdmin}
              style={[styles.input, !isAdmin && { opacity: 0.6 }]}
            />
          </View>

          <View style={styles.card}>
            <Text style={styles.section}>MODE ARTISAN UNIQUE</Text>
            <Text style={styles.help}>
              Activez ce mode si vous êtes <Text style={styles.bold}>seul à utiliser
              l'application</Text> (artisan indépendant). Vous accéderez
              instantanément à <Text style={styles.bold}>toutes les fonctionnalités</Text>
              {" "}sans restriction de rôle : saisie client, mesures terrain,
              statistiques, exports techniques (PDF/Excel/JSON).
            </Text>

            <View style={styles.toggleRow}>
              <View style={{ flex: 1 }}>
                <Text style={styles.toggleLabel}>Activer le mode artisan</Text>
                <Text style={styles.toggleSub}>
                  {artisanMode ? "✅ Accès total" : "⛔ Restrictions par rôle"}
                </Text>
              </View>
              <Switch
                testID="artisan-mode-switch"
                value={artisanMode}
                onValueChange={setArtisanMode}
                disabled={!isAdmin}
                trackColor={{ false: colors.borderStrong, true: colors.primary }}
                thumbColor={artisanMode ? "#fff" : "#f4f3f4"}
              />
            </View>

            {!isAdmin && (
              <Text style={styles.warnNote}>
                ⚠ Seul l'administrateur de la société peut modifier ce paramètre.
              </Text>
            )}
          </View>

          {isAdmin && (
            <TouchableOpacity
              testID="company-save-button"
              onPress={save}
              disabled={saving}
              activeOpacity={0.85}
              style={[styles.btn, styles.btnPrimary]}
            >
              {saving ? (
                <ActivityIndicator color="#000" />
              ) : (
                <>
                  <Ionicons name="checkmark-circle" size={22} color="#000" />
                  <Text style={styles.btnPrimaryText}>ENREGISTRER</Text>
                </>
              )}
            </TouchableOpacity>
          )}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: colors.bg },
  center: { alignItems: "center", justifyContent: "center" },
  topBar: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSubtle,
  },
  topTitle: { color: colors.textPrimary, fontWeight: "900", letterSpacing: 1.2, fontSize: 13 },
  card: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    borderColor: colors.borderSubtle,
    borderWidth: 1,
    padding: 16,
    marginBottom: 14,
  },
  section: {
    color: colors.textSecondary,
    fontSize: 11,
    letterSpacing: 1.5,
    fontWeight: "800",
    marginBottom: 12,
  },
  label: {
    color: colors.textSecondary,
    fontSize: 11,
    fontWeight: "700",
    letterSpacing: 0.6,
    marginBottom: 6,
  },
  input: {
    backgroundColor: colors.inputBg,
    color: colors.textPrimary,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.borderStrong,
    paddingHorizontal: 12,
    paddingVertical: Platform.OS === "ios" ? 14 : 10,
    fontSize: 16,
    minHeight: 48,
  },
  badge: {
    alignSelf: "flex-start",
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    backgroundColor: colors.bg,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
  },
  badgeText: { color: colors.textPrimary, fontWeight: "700", fontSize: 12 },
  help: { color: colors.textSecondary, fontSize: 13, lineHeight: 19 },
  bold: { color: colors.textPrimary, fontWeight: "800" },
  toggleRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    marginTop: 14,
    paddingTop: 14,
    borderTopWidth: 1,
    borderTopColor: colors.borderSubtle,
  },
  toggleLabel: { color: colors.textPrimary, fontWeight: "800", fontSize: 14 },
  toggleSub: { color: colors.textSecondary, fontSize: 12, marginTop: 2 },
  warnNote: {
    color: colors.warning,
    fontSize: 12,
    marginTop: 10,
    fontWeight: "700",
  },
  btn: {
    minHeight: 56,
    borderRadius: 12,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
  },
  btnPrimary: { backgroundColor: colors.primary },
  btnPrimaryText: { color: "#000", fontWeight: "900", letterSpacing: 1 },
});
