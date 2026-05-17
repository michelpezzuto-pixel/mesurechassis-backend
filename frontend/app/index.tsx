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
import { useAuth, Role } from "@/src/context/AuthContext";
import { colors } from "@/src/theme";

const ROLES: { value: Role; label: string; icon: keyof typeof Ionicons.glyphMap; desc: string }[] = [
  { value: "admin", label: "Admin", icon: "shield-checkmark", desc: "Pilotage & feedbacks" },
  { value: "commercial", label: "Commercial", icon: "briefcase", desc: "Devis & clients" },
  { value: "technician", label: "Technicien", icon: "construct", desc: "Mesures terrain" },
];

export default function SignIn() {
  const { user, loading, signIn, signUp } = useAuth();
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  // État post-signup : permet d'afficher l'écran "Vérifiez votre email"
  const [pendingVerification, setPendingVerification] = useState<{
    email: string;
    link?: string;
  } | null>(null);

  useEffect(() => {
    if (!loading && user) router.replace("/dashboard");
  }, [user, loading, router]);

  const fillDemo = (kind: Role) => {
    if (kind === "admin") {
      setEmail("admin@mesurechassis.fr");
      setPassword("admin123");
    } else if (kind === "commercial") {
      setEmail("commercial@mesurechassis.fr");
      setPassword("commercial123");
    } else {
      setEmail("tech@mesurechassis.fr");
      setPassword("tech123");
    }
    setMode("login");
  };

  const onSubmit = async () => {
    if (!email.trim() || !password.trim()) {
      Alert.alert("Champs requis", "Email et mot de passe sont obligatoires.");
      return;
    }
    if (mode === "register" && !name.trim()) {
      Alert.alert("Champs requis", "Le nom complet est obligatoire.");
      return;
    }
    setSubmitting(true);
    try {
      if (mode === "login") {
        await signIn(email.trim(), password);
        router.replace("/dashboard");
      } else {
        // Master Admin signup — pas de token immédiat, on attend la vérification email.
        const res = await signUp(
          name.trim(),
          email.trim(),
          password,
          companyName.trim() || undefined
        );
        setPendingVerification({
          email: email.trim(),
          link: res.verification_link,
        });
      }
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      // Email non vérifié → bascule vers l'écran de vérification
      if (e?.response?.status === 403 && detail?.code === "email_not_verified") {
        setPendingVerification({ email: email.trim() });
        return;
      }
      const msg =
        typeof detail === "string"
          ? detail
          : "Connexion impossible. Vérifiez vos identifiants.";
      Alert.alert("Erreur", msg);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <View style={[styles.flex, styles.center]}>
        <ActivityIndicator color={colors.primary} size="large" />
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.flex} edges={["top", "bottom"]}>
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        style={styles.flex}
      >
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          <View style={styles.brandWrap}>
            <View style={styles.logoBox}>
              <Ionicons name="resize" size={32} color="#000" />
            </View>
            <Text style={styles.brand}>MESURECHÂSSIS</Text>
            <Text style={styles.tagline}>Mesures terrain · Menuiseries pro</Text>
          </View>

          <View style={styles.tabs}>
            <TouchableOpacity
              testID="login-tab"
              onPress={() => setMode("login")}
              style={[styles.tab, mode === "login" && styles.tabActive]}
              activeOpacity={0.7}
            >
              <Text style={[styles.tabText, mode === "login" && styles.tabTextActive]}>
                Connexion
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              testID="register-tab"
              onPress={() => setMode("register")}
              style={[styles.tab, mode === "register" && styles.tabActive]}
              activeOpacity={0.7}
            >
              <Text style={[styles.tabText, mode === "register" && styles.tabTextActive]}>
                Inscription
              </Text>
            </TouchableOpacity>
          </View>

          {pendingVerification ? (
            <View style={styles.pendingPanel}>
              <View style={styles.pendingIconWrap}>
                <Ionicons name="mail-unread" size={40} color={colors.primary} />
              </View>
              <Text style={styles.pendingTitle}>
                VÉRIFIEZ VOTRE EMAIL
              </Text>
              <Text style={styles.pendingBody}>
                Un email de vérification a été envoyé à{"\n"}
                <Text style={styles.pendingEmail}>
                  {pendingVerification.email}
                </Text>
                {"\n\n"}
                Cliquez sur le lien reçu pour activer votre compte et accéder
                au dashboard.
              </Text>
              {pendingVerification.link && (
                <>
                  <View style={styles.devLinkBox}>
                    <Text style={styles.devLinkLabel}>
                      🔧 DÉMO — Lien fourni (mode dev) :
                    </Text>
                    <Text
                      testID="dev-verification-link"
                      selectable
                      style={styles.devLinkValue}
                    >
                      {pendingVerification.link}
                    </Text>
                  </View>
                  <TouchableOpacity
                    testID="open-verification-link"
                    activeOpacity={0.85}
                    onPress={() =>
                      router.push(pendingVerification.link as any)
                    }
                    style={styles.primaryBtn}
                  >
                    <Text style={styles.primaryBtnText}>
                      OUVRIR LE LIEN MAINTENANT
                    </Text>
                  </TouchableOpacity>
                </>
              )}
              <TouchableOpacity
                onPress={() => {
                  setPendingVerification(null);
                  setMode("login");
                }}
                style={styles.ghostBtn}
                activeOpacity={0.7}
              >
                <Text style={styles.ghostBtnText}>← Retour à la connexion</Text>
              </TouchableOpacity>
            </View>
          ) : (
            <>
          {mode === "register" && (
            <>
              <Text style={styles.label}>Nom complet (Master Admin)</Text>
              <TextInput
                testID="register-name-input"
                value={name}
                onChangeText={setName}
                placeholder="ex. Marc Dubois"
                placeholderTextColor={colors.placeholder}
                style={styles.input}
              />
              <Text style={styles.label}>
                Nom de la société (optionnel — votre nom par défaut)
              </Text>
              <TextInput
                testID="register-company-input"
                value={companyName}
                onChangeText={setCompanyName}
                placeholder="ex. Menuiseries Dubois SARL"
                placeholderTextColor={colors.placeholder}
                style={styles.input}
              />
              <View style={styles.infoBox}>
                <Ionicons
                  name="information-circle"
                  size={16}
                  color={colors.primary}
                />
                <Text style={styles.infoBoxText}>
                  L'inscription crée un compte{" "}
                  <Text style={styles.bold}>Master Admin</Text> pour une
                  nouvelle société. Les Commerciaux et Techniciens sont
                  invités par l'Admin depuis l'application (écran Équipe).
                </Text>
              </View>
            </>
          )}

          <Text style={styles.label}>Email</Text>
          <TextInput
            testID="login-email-input"
            value={email}
            onChangeText={setEmail}
            placeholder="prenom.nom@entreprise.fr"
            placeholderTextColor={colors.placeholder}
            keyboardType="email-address"
            autoCapitalize="none"
            style={styles.input}
          />
          <Text style={styles.label}>Mot de passe</Text>
          <TextInput
            testID="login-password-input"
            value={password}
            onChangeText={setPassword}
            placeholder="••••••••"
            placeholderTextColor={colors.placeholder}
            secureTextEntry
            style={styles.input}
          />

          <TouchableOpacity
            testID="login-submit-button"
            onPress={onSubmit}
            disabled={submitting}
            style={styles.primaryBtn}
            activeOpacity={0.8}
          >
            {submitting ? (
              <ActivityIndicator color="#000" />
            ) : (
              <Text style={styles.primaryBtnText}>
                {mode === "login" ? "SE CONNECTER" : "CRÉER LE COMPTE"}
              </Text>
            )}
          </TouchableOpacity>

          <View style={styles.demoBlock}>
            <Text style={styles.demoTitle}>Comptes de démo</Text>
            <View style={styles.demoRow}>
              {ROLES.map((r) => (
                <TouchableOpacity
                  key={r.value}
                  testID={`demo-${r.value}`}
                  onPress={() => fillDemo(r.value)}
                  style={styles.demoBtn}
                  activeOpacity={0.7}
                >
                  <Ionicons name={r.icon} size={18} color={colors.primary} />
                  <Text style={styles.demoBtnText}>{r.label}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
            </>
          )}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: colors.bg },
  center: { alignItems: "center", justifyContent: "center" },
  scroll: { padding: 24, paddingBottom: 60 },
  brandWrap: { alignItems: "center", marginTop: 16, marginBottom: 32 },
  logoBox: {
    width: 64,
    height: 64,
    borderRadius: 12,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 12,
  },
  brand: {
    color: colors.textPrimary,
    fontSize: 28,
    fontWeight: "900",
    letterSpacing: 1.5,
  },
  tagline: { color: colors.textSecondary, marginTop: 4, fontSize: 13, letterSpacing: 0.8 },
  tabs: {
    flexDirection: "row",
    backgroundColor: colors.surface,
    borderRadius: 8,
    padding: 4,
    marginBottom: 22,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
  },
  tab: { flex: 1, paddingVertical: 14, alignItems: "center", borderRadius: 6 },
  tabActive: { backgroundColor: colors.primary },
  tabText: {
    color: colors.textSecondary,
    fontWeight: "800",
    textTransform: "uppercase",
    letterSpacing: 0.6,
  },
  tabTextActive: { color: "#000" },
  label: {
    color: colors.textSecondary,
    fontSize: 12,
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: 1.2,
    marginBottom: 6,
    marginTop: 12,
  },
  input: {
    backgroundColor: colors.inputBg,
    borderColor: colors.borderSubtle,
    borderWidth: 2,
    borderRadius: 8,
    color: colors.textPrimary,
    minHeight: 56,
    paddingHorizontal: 14,
    fontSize: 16,
    fontWeight: "600",
  },
  roleRow: { flexDirection: "row", gap: 8 },
  roleCard: {
    flex: 1,
    backgroundColor: colors.surface,
    borderRadius: 8,
    borderWidth: 2,
    borderColor: colors.borderSubtle,
    paddingVertical: 16,
    alignItems: "center",
    gap: 6,
  },
  roleCardActive: { borderColor: colors.primary, backgroundColor: "#1a0e00" },
  roleLabel: {
    color: colors.textSecondary,
    fontWeight: "700",
    fontSize: 12,
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  roleLabelActive: { color: colors.textPrimary },
  primaryBtn: {
    minHeight: 64,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 8,
    marginTop: 22,
  },
  primaryBtnText: {
    color: "#000",
    fontSize: 17,
    fontWeight: "900",
    letterSpacing: 1.2,
  },
  demoBlock: { marginTop: 32 },
  demoTitle: {
    color: colors.textSecondary,
    fontSize: 11,
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: 1.2,
    textAlign: "center",
    marginBottom: 12,
  },
  demoRow: { flexDirection: "row", gap: 8 },
  demoBtn: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    minHeight: 48,
    borderRadius: 8,
    gap: 6,
  },
  demoBtnText: {
    color: colors.textPrimary,
    fontWeight: "700",
    fontSize: 12,
    textTransform: "uppercase",
  },
  // ----- Pending verification panel -----
  pendingPanel: { alignItems: "center", paddingTop: 8 },
  pendingIconWrap: {
    width: 80,
    height: 80,
    borderRadius: 40,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#2a1c08",
    borderWidth: 2,
    borderColor: colors.primary,
    marginBottom: 14,
  },
  pendingTitle: {
    color: colors.textPrimary,
    fontWeight: "900",
    letterSpacing: 1.2,
    fontSize: 16,
    marginBottom: 12,
  },
  pendingBody: {
    color: colors.textSecondary,
    fontSize: 13,
    lineHeight: 19,
    textAlign: "center",
    marginBottom: 16,
  },
  pendingEmail: { color: colors.primary, fontWeight: "900" },
  devLinkBox: {
    backgroundColor: colors.surface,
    borderColor: colors.borderStrong,
    borderWidth: 1,
    borderRadius: 8,
    padding: 12,
    width: "100%",
    marginBottom: 12,
  },
  devLinkLabel: {
    color: colors.warning,
    fontWeight: "800",
    fontSize: 11,
    letterSpacing: 0.6,
    marginBottom: 6,
  },
  devLinkValue: {
    color: colors.textPrimary,
    fontSize: 11,
    fontFamily: Platform.select({ ios: "Menlo", android: "monospace", default: "monospace" }),
  },
  ghostBtn: { paddingVertical: 12, paddingHorizontal: 16, marginTop: 6 },
  ghostBtnText: {
    color: colors.textSecondary,
    fontSize: 13,
    fontWeight: "700",
  },
  infoBox: {
    flexDirection: "row",
    gap: 8,
    backgroundColor: colors.surface,
    borderLeftWidth: 3,
    borderLeftColor: colors.primary,
    padding: 10,
    borderRadius: 6,
    marginTop: 6,
    marginBottom: 6,
  },
  infoBoxText: { color: colors.textSecondary, fontSize: 12, flex: 1, lineHeight: 17 },
  bold: { color: colors.textPrimary, fontWeight: "800" },
});
