import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Modal,
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
import { api } from "@/src/services/api";
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

  // ─── Mot de passe oublié (modal) ───
  const [forgotOpen, setForgotOpen] = useState(false);
  const [forgotStep, setForgotStep] = useState<"request" | "reset">("request");
  const [forgotEmail, setForgotEmail] = useState("");
  const [forgotCode, setForgotCode] = useState("");
  const [forgotNewPassword, setForgotNewPassword] = useState("");
  const [forgotSubmitting, setForgotSubmitting] = useState(false);
  const [forgotBetaCode, setForgotBetaCode] = useState<string | null>(null);

  const requestResetCode = async () => {
    const em = forgotEmail.trim().toLowerCase();
    if (!em || !em.includes("@")) {
      Alert.alert("Email invalide", "Veuillez saisir une adresse email valide.");
      return;
    }
    setForgotSubmitting(true);
    setForgotBetaCode(null);
    try {
      const r = await api.post("/auth/forgot-password", { email: em });
      const code = (r.data as any)?.beta_reset_code as string | undefined;
      if (code) {
        // Mode BETA : on affiche le code à l'écran (Resend non branché)
        setForgotBetaCode(code);
      }
      setForgotStep("reset");
    } catch (e: any) {
      Alert.alert(
        "Erreur",
        e?.response?.data?.detail || "Impossible d'envoyer le code. Réessayez.",
      );
    } finally {
      setForgotSubmitting(false);
    }
  };

  const doResetPassword = async () => {
    if (!forgotCode || forgotCode.length !== 6) {
      Alert.alert("Code invalide", "Veuillez saisir les 6 chiffres reçus.");
      return;
    }
    if (forgotNewPassword.length < 6) {
      Alert.alert("Mot de passe trop court", "Au moins 6 caractères.");
      return;
    }
    setForgotSubmitting(true);
    try {
      await api.post("/auth/reset-password", {
        email: forgotEmail.trim().toLowerCase(),
        code: forgotCode.trim(),
        new_password: forgotNewPassword,
      });
      Alert.alert(
        "✅ Mot de passe modifié",
        "Vous pouvez maintenant vous reconnecter avec votre nouveau mot de passe.",
      );
      // Pré-remplit l'email sur l'écran login + ferme
      setEmail(forgotEmail.trim().toLowerCase());
      setPassword("");
      closeForgot();
    } catch (e: any) {
      Alert.alert(
        "Erreur",
        e?.response?.data?.detail || "Code invalide ou expiré.",
      );
    } finally {
      setForgotSubmitting(false);
    }
  };

  const openForgot = () => {
    setForgotEmail(email || "");
    setForgotStep("request");
    setForgotCode("");
    setForgotNewPassword("");
    setForgotBetaCode(null);
    setForgotOpen(true);
  };

  const closeForgot = () => {
    setForgotOpen(false);
    setForgotEmail("");
    setForgotCode("");
    setForgotNewPassword("");
    setForgotBetaCode(null);
    setForgotStep("request");
  };

  // État post-signup : permet d'afficher l'écran "Vérifiez votre email"
  const [pendingVerification, setPendingVerification] = useState<{
    email: string;
    link?: string;
  } | null>(null);

  useEffect(() => {
    if (!loading && user) router.replace("/dashboard");
  }, [user, loading, router]);

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
              <Ionicons name="arrow-up" size={36} color={colors.primary} />
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

          {mode === "login" && (
            <TouchableOpacity
              testID="forgot-password-link"
              onPress={openForgot}
              activeOpacity={0.7}
              style={{ alignItems: "center", marginTop: 14, padding: 8 }}
            >
              <Text style={{ color: colors.primary, fontSize: 13, fontWeight: "700", letterSpacing: 0.4 }}>
                Mot de passe oublié ?
              </Text>
            </TouchableOpacity>
          )}
            </>
          )}
        </ScrollView>
      </KeyboardAvoidingView>

      {/* ────── MODAL Mot de passe oublié ────── */}
      <Modal
        visible={forgotOpen}
        animationType="slide"
        transparent
        onRequestClose={closeForgot}
      >
        <View style={styles.modalBackdrop}>
          <KeyboardAvoidingView
            behavior={Platform.OS === "ios" ? "padding" : "height"}
            style={{ width: "100%", maxWidth: 460 }}
          >
            <View style={styles.modalCard}>
              <View style={styles.modalHeader}>
                <View style={styles.modalIconWrap}>
                  <Ionicons name="key" size={20} color={colors.primary} />
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={styles.modalTitle}>
                    {forgotStep === "request"
                      ? "Mot de passe oublié"
                      : "Saisir le code reçu"}
                  </Text>
                  <Text style={styles.modalSubtitle}>
                    {forgotStep === "request"
                      ? "Saisissez votre email pour recevoir un code"
                      : `Code envoyé à ${forgotEmail}`}
                  </Text>
                </View>
                <TouchableOpacity
                  onPress={closeForgot}
                  hitSlop={10}
                  style={styles.modalClose}
                >
                  <Ionicons name="close" size={20} color={colors.textPrimary} />
                </TouchableOpacity>
              </View>

              {forgotStep === "request" ? (
                <>
                  <TextInput
                    testID="forgot-email-input"
                    value={forgotEmail}
                    onChangeText={setForgotEmail}
                    placeholder="vous@entreprise.fr"
                    placeholderTextColor={colors.placeholder}
                    autoCapitalize="none"
                    autoCorrect={false}
                    keyboardType="email-address"
                    style={styles.modalInput}
                  />
                  <TouchableOpacity
                    testID="forgot-send-button"
                    onPress={requestResetCode}
                    disabled={forgotSubmitting}
                    style={[styles.primaryBtn, { marginTop: 12 }]}
                    activeOpacity={0.85}
                  >
                    {forgotSubmitting ? (
                      <ActivityIndicator color="#000" />
                    ) : (
                      <Text style={styles.primaryBtnText}>RECEVOIR LE CODE</Text>
                    )}
                  </TouchableOpacity>
                  <Text style={styles.modalHint}>
                    Vous recevrez un code à 6 chiffres valable 30 minutes.
                  </Text>
                </>
              ) : (
                <>
                  {forgotBetaCode && (
                    <View style={styles.betaCodeBox}>
                      <Text style={styles.betaCodeLabel}>
                        ⚠️ Email indisponible — Code de secours :
                      </Text>
                      <Text style={styles.betaCodeValue}>{forgotBetaCode}</Text>
                      <Text style={styles.betaCodeHint}>
                        L'envoi d'email a échoué. Utilisez ce code de secours.
                      </Text>
                    </View>
                  )}
                  {!forgotBetaCode && (
                    <View style={styles.mailInfoBox}>
                      <Ionicons
                        name="mail-outline"
                        size={18}
                        color={colors.primary}
                      />
                      <Text style={styles.mailInfoText}>
                        Consultez votre boîte mail. Vérifiez aussi les
                        spams/courriers indésirables.
                      </Text>
                    </View>
                  )}
                  <TextInput
                    testID="forgot-code-input"
                    value={forgotCode}
                    onChangeText={(v) => setForgotCode(v.replace(/\D/g, "").slice(0, 6))}
                    placeholder="123456"
                    placeholderTextColor={colors.placeholder}
                    keyboardType="number-pad"
                    style={[styles.modalInput, { fontSize: 22, letterSpacing: 8, textAlign: "center" }]}
                    maxLength={6}
                  />
                  <Text style={styles.modalLabel}>Nouveau mot de passe</Text>
                  <TextInput
                    testID="forgot-new-password-input"
                    value={forgotNewPassword}
                    onChangeText={setForgotNewPassword}
                    placeholder="Min. 6 caractères"
                    placeholderTextColor={colors.placeholder}
                    secureTextEntry
                    style={styles.modalInput}
                  />
                  <TouchableOpacity
                    testID="forgot-reset-button"
                    onPress={doResetPassword}
                    disabled={forgotSubmitting}
                    style={[styles.primaryBtn, { marginTop: 12 }]}
                    activeOpacity={0.85}
                  >
                    {forgotSubmitting ? (
                      <ActivityIndicator color="#000" />
                    ) : (
                      <Text style={styles.primaryBtnText}>
                        RÉINITIALISER LE MOT DE PASSE
                      </Text>
                    )}
                  </TouchableOpacity>
                  <TouchableOpacity
                    onPress={() => setForgotStep("request")}
                    style={{ marginTop: 10, alignItems: "center" }}
                  >
                    <Text style={{ color: colors.textSecondary, fontSize: 12 }}>
                      Renvoyer un code
                    </Text>
                  </TouchableOpacity>
                </>
              )}
            </View>
          </KeyboardAvoidingView>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: colors.bg },
  center: { alignItems: "center", justifyContent: "center" },
  scroll: { padding: 24, paddingBottom: 60 },
  brandWrap: { alignItems: "center", marginTop: 16, marginBottom: 32 },
  logoBox: {
    width: 72,
    height: 72,
    borderRadius: 16,
    backgroundColor: "#0C0C0E",
    borderWidth: 3,
    borderColor: colors.primary,
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

  // ────── Modal Mot de passe oublié ──────
  modalBackdrop: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.75)",
    alignItems: "center",
    justifyContent: "center",
    padding: 20,
  },
  modalCard: {
    backgroundColor: colors.surface,
    borderRadius: 16,
    padding: 18,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
  },
  modalHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    marginBottom: 16,
  },
  modalIconWrap: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.bg,
    borderWidth: 1,
    borderColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
  },
  modalTitle: {
    color: colors.textPrimary,
    fontSize: 16,
    fontWeight: "900",
    letterSpacing: 0.3,
  },
  modalSubtitle: {
    color: colors.textSecondary,
    fontSize: 12,
    marginTop: 2,
  },
  modalClose: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: colors.bg,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
    borderColor: colors.borderSubtle,
  },
  modalInput: {
    backgroundColor: colors.bg,
    color: colors.textPrimary,
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 14,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    marginTop: 8,
  },
  modalLabel: {
    color: colors.textSecondary,
    fontSize: 11,
    fontWeight: "700",
    letterSpacing: 0.5,
    textTransform: "uppercase",
    marginTop: 14,
  },
  modalHint: {
    color: colors.textSecondary,
    fontSize: 11,
    marginTop: 10,
    textAlign: "center",
    fontStyle: "italic",
  },
  betaCodeBox: {
    backgroundColor: "rgba(255, 107, 26, 0.10)",
    borderWidth: 1,
    borderColor: "rgba(255, 107, 26, 0.45)",
    borderRadius: 12,
    padding: 12,
    marginBottom: 12,
    alignItems: "center",
  },
  betaCodeLabel: {
    color: colors.primary,
    fontSize: 11,
    fontWeight: "800",
    letterSpacing: 0.6,
  },
  betaCodeValue: {
    color: colors.primary,
    fontSize: 28,
    fontWeight: "900",
    letterSpacing: 8,
    marginTop: 6,
  },
  betaCodeHint: {
    color: colors.textSecondary,
    fontSize: 10,
    marginTop: 4,
    fontStyle: "italic",
    textAlign: "center",
  },
  mailInfoBox: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    backgroundColor: "rgba(255, 165, 0, 0.08)",
    borderWidth: 1,
    borderColor: "rgba(255, 165, 0, 0.30)",
    borderRadius: 10,
    paddingVertical: 10,
    paddingHorizontal: 12,
    marginBottom: 12,
  },
  mailInfoText: {
    flex: 1,
    color: colors.textPrimary,
    fontSize: 12,
    lineHeight: 17,
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
