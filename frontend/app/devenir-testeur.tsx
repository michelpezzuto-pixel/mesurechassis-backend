import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
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
import { colors } from "@/src/theme";

/**
 * Page PUBLIQUE (sans connexion) : inscription des artisans candidats
 * testeurs Google Play avant le lancement officiel.
 * URL web : /devenir-testeur
 *
 * 🍎 iOS — App Store Guideline 2.2 (Beta Testing) :
 * la fonctionnalité de recrutement de testeurs n'est PAS autorisée
 * sur les builds production iOS. On redirige automatiquement vers
 * l'accueil si l'écran est ouvert depuis iOS.
 */
export default function DevenirTesteur() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [company, setCompany] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 🍎 iOS — redirection automatique vers l'accueil
  useEffect(() => {
    if (Platform.OS === "ios") {
      router.replace("/");
    }
  }, [router]);

  // 🍎 iOS — fenêtre vide pendant la redirection
  if (Platform.OS === "ios") {
    return (
      <SafeAreaView style={styles.flex} edges={["top", "bottom"]}>
        <View style={[styles.flex, { justifyContent: "center", alignItems: "center" }]}>
          <ActivityIndicator color={colors.primary} />
        </View>
      </SafeAreaView>
    );
  }

  const submit = async () => {
    setError(null);
    if (!name.trim()) {
      setError("Veuillez indiquer votre nom.");
      return;
    }
    if (!email.trim() || !email.includes("@")) {
      setError("Veuillez indiquer une adresse email valide (Gmail de préférence).");
      return;
    }
    setSubmitting(true);
    try {
      await api.post("/testers/register", {
        name: name.trim(),
        company: company.trim(),
        email: email.trim(),
        phone: phone.trim(),
      });
      setDone(true);
    } catch (e: any) {
      setError(
        e?.response?.data?.detail || "Une erreur est survenue. Réessayez.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  if (done) {
    return (
      <SafeAreaView style={styles.flex} edges={["top", "bottom"]}>
        <View style={styles.successWrap} testID="tester-success-view">
          <View style={styles.successIcon}>
            <Ionicons name="checkmark" size={48} color="#fff" />
          </View>
          <Text style={styles.successTitle}>Inscription enregistrée !</Text>
          <Text style={styles.successBody}>
            Merci {name.trim()} 🧡{"\n\n"}
            Vous recevrez très prochainement sur{" "}
            <Text style={styles.bold}>{email.trim()}</Text> le lien
            d&apos;invitation Google Play pour installer MesureChâssis en
            avant-première.{"\n\n"}
            📱 Pensez à ouvrir ce lien depuis votre téléphone Android.
          </Text>
          <TouchableOpacity
            testID="tester-back-home"
            style={styles.secondaryBtn}
            onPress={() => router.replace("/")}
          >
            <Text style={styles.secondaryBtnText}>Retour à l&apos;accueil</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.flex} edges={["top", "bottom"]}>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <ScrollView
          contentContainerStyle={styles.scroll}
          keyboardShouldPersistTaps="handled"
        >
          <View style={styles.header}>
            <View style={styles.logoBadge}>
              <Ionicons name="resize-outline" size={30} color="#fff" />
            </View>
            <Text style={styles.title}>
              Mesure<Text style={{ color: colors.primary }}>Châssis</Text>
            </Text>
            <Text style={styles.subtitle}>
              Devenez testeur en avant-première
            </Text>
          </View>

          <Text style={styles.pitch}>
            L&apos;application belge qui digitalise la prise de mesures de
            châssis pour les professionnels de la menuiserie.
          </Text>

          <View style={styles.featList}>
            {[
              "Prise de mesures guidée sur chantier",
              "Gestion des chantiers et des équipes",
              "Exports PDF techniques prêts pour la production",
              "Accès gratuit pendant toute la phase de test",
            ].map((f) => (
              <View key={f} style={styles.featRow}>
                <Ionicons
                  name="checkmark-circle"
                  size={18}
                  color={colors.primary}
                />
                <Text style={styles.featText}>{f}</Text>
              </View>
            ))}
          </View>

          <View style={styles.requireBox}>
            <Ionicons name="information-circle" size={18} color="#FBBF24" />
            <Text style={styles.requireText}>
              Conditions : un téléphone <Text style={styles.bold}>Android</Text>{" "}
              et une adresse <Text style={styles.bold}>Gmail / Google</Text>.
            </Text>
          </View>

          <View style={styles.form}>
            <Text style={styles.label}>Votre nom *</Text>
            <TextInput
              testID="tester-name-input"
              style={styles.input}
              placeholder="Jean Dupont"
              placeholderTextColor={colors.textSecondary}
              value={name}
              onChangeText={setName}
              autoCapitalize="words"
            />

            <Text style={styles.label}>Société (optionnel)</Text>
            <TextInput
              testID="tester-company-input"
              style={styles.input}
              placeholder="Menuiserie Dupont SRL"
              placeholderTextColor={colors.textSecondary}
              value={company}
              onChangeText={setCompany}
              autoCapitalize="words"
            />

            <Text style={styles.label}>Adresse Gmail / Google *</Text>
            <TextInput
              testID="tester-email-input"
              style={styles.input}
              placeholder="vous@gmail.com"
              placeholderTextColor={colors.textSecondary}
              value={email}
              onChangeText={setEmail}
              keyboardType="email-address"
              autoCapitalize="none"
              autoCorrect={false}
            />

            <Text style={styles.label}>Téléphone (optionnel)</Text>
            <TextInput
              testID="tester-phone-input"
              style={styles.input}
              placeholder="+32 470 00 00 00"
              placeholderTextColor={colors.textSecondary}
              value={phone}
              onChangeText={setPhone}
              keyboardType="phone-pad"
            />

            {error && (
              <Text style={styles.error} testID="tester-error-text">
                {error}
              </Text>
            )}

            <TouchableOpacity
              testID="tester-submit-button"
              style={[styles.submitBtn, submitting && { opacity: 0.6 }]}
              onPress={submit}
              disabled={submitting}
            >
              {submitting ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={styles.submitBtnText}>JE DEVIENS TESTEUR</Text>
              )}
            </TouchableOpacity>

            <Text style={styles.gdpr}>
              Vos coordonnées servent uniquement à vous inviter au test et ne
              sont jamais partagées avec des tiers.
            </Text>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: colors.bg },
  scroll: { padding: 24, paddingBottom: 60, maxWidth: 560, width: "100%", alignSelf: "center" },
  header: { alignItems: "center", marginBottom: 18 },
  logoBadge: {
    width: 64,
    height: 64,
    borderRadius: 16,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 12,
  },
  title: { color: colors.textPrimary, fontSize: 30, fontWeight: "800" },
  subtitle: {
    color: colors.primary,
    fontSize: 15,
    fontWeight: "700",
    marginTop: 4,
    textTransform: "uppercase",
    letterSpacing: 1,
  },
  pitch: {
    color: colors.textSecondary,
    fontSize: 15,
    textAlign: "center",
    lineHeight: 22,
    marginBottom: 18,
  },
  featList: { gap: 10, marginBottom: 18 },
  featRow: { flexDirection: "row", alignItems: "center", gap: 10 },
  featText: { color: colors.textPrimary, fontSize: 14, flex: 1 },
  requireBox: {
    flexDirection: "row",
    gap: 10,
    backgroundColor: "rgba(251,191,36,0.08)",
    borderWidth: 1,
    borderColor: "rgba(251,191,36,0.35)",
    borderRadius: 10,
    padding: 12,
    alignItems: "center",
    marginBottom: 22,
  },
  requireText: { color: colors.textPrimary, fontSize: 13, flex: 1, lineHeight: 18 },
  form: { gap: 6 },
  label: { color: colors.textSecondary, fontSize: 13, fontWeight: "600", marginTop: 8 },
  input: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.surfaceElevated,
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: Platform.OS === "ios" ? 14 : 11,
    color: colors.textPrimary,
    fontSize: 15,
  },
  error: { color: "#F87171", fontSize: 13, marginTop: 10 },
  submitBtn: {
    backgroundColor: colors.primary,
    paddingVertical: 16,
    borderRadius: 12,
    alignItems: "center",
    marginTop: 18,
  },
  submitBtnText: { color: "#fff", fontWeight: "800", fontSize: 15, letterSpacing: 0.5 },
  gdpr: {
    color: colors.textSecondary,
    fontSize: 11,
    textAlign: "center",
    marginTop: 14,
    lineHeight: 16,
  },
  bold: { fontWeight: "800", color: colors.textPrimary },
  successWrap: { flex: 1, alignItems: "center", justifyContent: "center", padding: 32 },
  successIcon: {
    width: 88,
    height: 88,
    borderRadius: 44,
    backgroundColor: "#22C55E",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 22,
  },
  successTitle: { color: colors.textPrimary, fontSize: 24, fontWeight: "800", marginBottom: 14 },
  successBody: {
    color: colors.textSecondary,
    fontSize: 15,
    textAlign: "center",
    lineHeight: 23,
    maxWidth: 420,
  },
  secondaryBtn: {
    marginTop: 28,
    borderWidth: 1,
    borderColor: colors.primary,
    borderRadius: 10,
    paddingVertical: 12,
    paddingHorizontal: 24,
  },
  secondaryBtnText: { color: colors.primary, fontWeight: "700" },
});
