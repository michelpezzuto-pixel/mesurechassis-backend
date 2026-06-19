import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Image,
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
import { useTranslation } from "react-i18next";
import { setLanguage, SUPPORTED_LANGUAGES, SupportedLanguage } from "@/src/i18n";
import { api } from "@/src/services/api";
import { colors } from "@/src/theme";

const FLAGS: Record<SupportedLanguage, string> = {
  fr: "🇫🇷",
  nl: "🇧🇪",
  en: "🇬🇧",
};

const ROLES: { value: Role; label: string; icon: keyof typeof Ionicons.glyphMap; desc: string }[] = [
  { value: "admin", label: "Admin", icon: "shield-checkmark", desc: "Pilotage & feedbacks" },
  { value: "commercial", label: "Commercial", icon: "briefcase", desc: "Devis & clients" },
  { value: "technician", label: "Technicien", icon: "construct", desc: "Mesures terrain" },
];

export default function SignIn() {
  const { user, loading, signIn, signUp } = useAuth();
  const router = useRouter();
  const { t, i18n } = useTranslation();
  const currentLang = (i18n.language?.split("-")[0] || "fr") as SupportedLanguage;
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  // Œil show/hide pour les mots de passe (login, register, reset)
  const [showPassword, setShowPassword] = useState(false);
  const [showResetPassword, setShowResetPassword] = useState(false);
  const [name, setName] = useState("");
  const [companyName, setCompanyName] = useState("");
  // 🆕 Build 9 — Code parrainage optionnel saisi à l'inscription
  const [referralCode, setReferralCode] = useState("");
  const [referralStatus, setReferralStatus] = useState<{
    valid: boolean;
    parrain_name?: string;
    error?: string;
  } | null>(null);
  // Lot D — type de compte choisi à l'inscription :
  //   "artisan"   : auto-entrepreneur seul, artisan_mode=true automatique
  //   "entreprise": société avec équipe (Admin + commerciaux + techniciens)
  //   "pro"       : Entreprise Pro (équipe étendue, fonctions avancées)
  //
  // 🆕 V3 (juin 2026) — Séparation explicite des 3 profils à l'inscription
  // pour matcher les 3 plans Stripe (Artisan Solo / Entreprise / Entreprise Pro).
  // 🍎 iOS — App Store Guidelines 3.1.1 & 3.1.3(c) : on n'affiche AUCUN choix
  // de plan / profil business sur iOS. L'inscription est strictement
  // individuelle ("artisan" par défaut). Les utilisateurs qui veulent une
  // organisation/équipe doivent passer par mesurechassis.com.
  const [accountType, setAccountType] = useState<"artisan" | "entreprise" | "pro">(
    "artisan",
  );
  const isIOS = Platform.OS === "ios";
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
    if (
      mode === "register" &&
      (accountType === "entreprise" || accountType === "pro") &&
      !companyName.trim()
    ) {
      Alert.alert(
        "Nom de l'entreprise requis",
        "Pour un compte Entreprise, saisissez le nom de votre société.",
      );
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
          (accountType === "entreprise" || accountType === "pro")
            ? companyName.trim() || undefined
            : companyName.trim() || undefined,
          accountType,
          // 🆕 Build 9 — Code parrainage optionnel
          referralCode.trim() || undefined,
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
        keyboardVerticalOffset={Platform.OS === "ios" ? 0 : 0}
        style={styles.flex}
      >
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          <View style={styles.langRow}>
            {SUPPORTED_LANGUAGES.map((lng) => {
              const active = currentLang === lng;
              return (
                <TouchableOpacity
                  key={lng}
                  testID={`auth-lang-${lng}`}
                  onPress={() => void setLanguage(lng)}
                  activeOpacity={0.85}
                  style={[styles.langPill, active && styles.langPillActive]}
                >
                  <Text style={styles.langFlag}>{FLAGS[lng]}</Text>
                  <Text
                    style={[styles.langCode, active && styles.langCodeActive]}
                  >
                    {lng.toUpperCase()}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </View>

          <View style={styles.brandWrap}>
            <Image
              source={require("../assets/images/icon.png")}
              style={styles.brandLogo}
              resizeMode="contain"
            />
            <Text style={styles.brand}>MESURECHÂSSIS</Text>
            <Text style={styles.tagline}>{t("auth.appTagline")}</Text>
          </View>

          <View style={styles.tabs}>
            <TouchableOpacity
              testID="login-tab"
              onPress={() => setMode("login")}
              style={[styles.tab, mode === "login" && styles.tabActive]}
              activeOpacity={0.7}
            >
              <Text style={[styles.tabText, mode === "login" && styles.tabTextActive]}>
                {t("auth.login")}
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              testID="register-tab"
              onPress={() => setMode("register")}
              style={[styles.tab, mode === "register" && styles.tabActive]}
              activeOpacity={0.7}
            >
              <Text style={[styles.tabText, mode === "register" && styles.tabTextActive]}>
                {t("auth.register")}
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
              {/* 🆕 V3 — Sélection du profil avec 3 plans (Artisan / Entreprise / Pro).
               * Les prix sont affichés sur Web/Android mais MASQUÉS sur iOS
               * (App Store 3.1.1 — pas de mention de paiement externe).
               *
               * 🍎 iOS — App Store 3.1.1 + 3.1.3(c) : la sélection
               * Entreprise/Pro est entièrement masquée. Sur iOS, on force
               * un compte individuel ("artisan") sans aucune mention
               * d'abonnement ni d'organisation. */}
              {!isIOS && (
                <>
              <Text style={styles.label}>{t("auth.chooseProfile")}</Text>
              {([
                {
                  key: "artisan" as const,
                  icon: "person" as const,
                  title: t("auth.profile.artisan.title"),
                  desc: t("auth.profile.artisan.desc"),
                  price: "24,99 €/mois",
                },
                {
                  key: "entreprise" as const,
                  icon: "business" as const,
                  title: t("auth.profile.entreprise.title"),
                  desc: t("auth.profile.entreprise.desc"),
                  price: "59,99 €/mois",
                  badge: t("auth.profile.entreprise.badge"),
                },
                {
                  key: "pro" as const,
                  icon: "rocket" as const,
                  title: t("auth.profile.pro.title"),
                  desc: t("auth.profile.pro.desc"),
                  price: "89,99 €/mois",
                },
              ]).map((opt) => {
                const active = accountType === opt.key;
                return (
                  <TouchableOpacity
                    key={opt.key}
                    testID={`account-type-${opt.key}`}
                    onPress={() => setAccountType(opt.key)}
                    activeOpacity={0.85}
                    style={[
                      styles.profileCard,
                      active && styles.profileCardActive,
                    ]}
                  >
                    <View
                      style={[
                        styles.typeIconWrap,
                        active && styles.typeIconWrapActive,
                      ]}
                    >
                      <Ionicons
                        name={opt.icon}
                        size={22}
                        color={active ? "#000" : colors.textSecondary}
                      />
                    </View>
                    <View style={{ flex: 1 }}>
                      <View style={styles.profileTitleRow}>
                        <Text
                          style={[
                            styles.typeTitle,
                            active && styles.typeTitleActive,
                          ]}
                        >
                          {opt.title}
                        </Text>
                        {opt.badge && (
                          <View style={styles.profileBadge}>
                            <Text style={styles.profileBadgeText}>{opt.badge}</Text>
                          </View>
                        )}
                      </View>
                      <Text style={styles.typeDesc}>{opt.desc}</Text>
                      {Platform.OS === "web" && (
                        <Text
                          style={[
                            styles.profilePrice,
                            active && { color: colors.primary },
                          ]}
                        >
                          {t("auth.profile.freeTrialPrefix")} {opt.price}
                        </Text>
                      )}
                    </View>
                    <Ionicons
                      name={active ? "checkmark-circle" : "ellipse-outline"}
                      size={22}
                      color={active ? colors.primary : colors.borderStrong}
                    />
                  </TouchableOpacity>
                );
              })}
                </>
              )}

              <Text style={styles.label}>
                {isIOS
                  ? "Votre nom"
                  : accountType === "artisan"
                  ? "Votre nom complet"
                  : "Nom complet (Master Admin)"}
              </Text>
              <TextInput
                testID="register-name-input"
                value={name}
                onChangeText={setName}
                placeholder={
                  accountType === "artisan"
                    ? "ex. Jean Dupont"
                    : "ex. Marc Dubois"
                }
                placeholderTextColor={colors.placeholder}
                style={styles.input}
              />

              {/* 🍎 iOS — App Store 3.1.1/3.1.3(c) : aucun champ d'inscription
               * business/entreprise. Compte purement individuel. */}
              {isIOS ? null : accountType === "artisan" ? (
                <>
                  <Text style={styles.label}>
                    Nom commercial (optionnel)
                  </Text>
                  <TextInput
                    testID="register-company-input"
                    value={companyName}
                    onChangeText={setCompanyName}
                    placeholder="ex. JD Menuiserie"
                    placeholderTextColor={colors.placeholder}
                    style={styles.input}
                  />
                </>
              ) : (
                <>
                  <Text style={styles.label}>
                    Nom de l&apos;entreprise{" "}
                    <Text style={{ color: colors.alert }}>*</Text>
                  </Text>
                  <TextInput
                    testID="register-company-input"
                    value={companyName}
                    onChangeText={setCompanyName}
                    placeholder="ex. Menuiseries Dubois SARL"
                    placeholderTextColor={colors.placeholder}
                    style={styles.input}
                  />
                </>
              )}

              {/* 🆕 Build 9 — Code parrainage (optionnel) */}
              <Text style={styles.label}>Code parrainage (optionnel)</Text>
              <View style={styles.referralRow}>
                <TextInput
                  testID="register-referral-input"
                  value={referralCode}
                  onChangeText={(v) => {
                    const upper = v.toUpperCase().replace(/\s/g, "-");
                    setReferralCode(upper);
                    setReferralStatus(null);
                  }}
                  placeholder="ex. JEAN-MENUISERIE"
                  placeholderTextColor={colors.placeholder}
                  autoCapitalize="characters"
                  autoCorrect={false}
                  maxLength={24}
                  style={[
                    styles.input,
                    { flex: 1 },
                    referralStatus?.valid && {
                      borderColor: colors.success,
                      backgroundColor: "#0b2a14",
                    },
                    referralStatus && !referralStatus.valid && {
                      borderColor: colors.anomaly,
                    },
                  ]}
                />
                <TouchableOpacity
                  testID="validate-referral-btn"
                  disabled={!referralCode.trim()}
                  onPress={async () => {
                    try {
                      const { data } = await api.post<{
                        valid: boolean;
                        parrain_name?: string;
                        error?: string;
                      }>("/referral/validate", { code: referralCode.trim() });
                      setReferralStatus(data);
                    } catch {
                      setReferralStatus({ valid: false, error: "Réseau" });
                    }
                  }}
                  style={[
                    styles.validateBtn,
                    !referralCode.trim() && { opacity: 0.4 },
                  ]}
                >
                  <Ionicons
                    name={
                      referralStatus?.valid
                        ? "checkmark-circle"
                        : "search"
                    }
                    size={20}
                    color={referralStatus?.valid ? colors.success : colors.primary}
                  />
                </TouchableOpacity>
              </View>
              {referralStatus?.valid && (
                <Text style={[styles.helpHint, { color: colors.success }]}>
                  ✓ Code valide — vous serez parrainé par{" "}
                  <Text style={{ fontWeight: "900" }}>
                    {referralStatus.parrain_name}
                  </Text>
                </Text>
              )}
              {referralStatus && !referralStatus.valid && referralCode.trim() && (
                <Text style={[styles.helpHint, { color: colors.anomaly }]}>
                  ✗ Code introuvable — vérifiez l&apos;orthographe avec votre parrain
                </Text>
              )}

              {/* 🍎 iOS — masqué : l'app iOS ne mentionne ni Admin
               *  ni Entreprise ni Pro (App Store 3.1.1/3.1.3(c)). */}
              {!isIOS && (
              <View style={styles.infoBox}>
                <Ionicons
                  name="information-circle"
                  size={16}
                  color={colors.primary}
                />
                <Text style={styles.infoBoxText}>
                  {accountType === "artisan" ? (
                    <>
                      <Text style={styles.bold}>Mode Artisan Solo</Text> : un
                      compte unique, ultra-simple. Tous les accès sont
                      activés (mesures + chantiers + exports).
                    </>
                  ) : accountType === "pro" ? (
                    <>
                      <Text style={styles.bold}>Mode Entreprise Pro</Text> :
                      vous serez Admin. Équipe étendue (6 utilisateurs inclus)
                      et fonctions avancées.
                    </>
                  ) : (
                    <>
                      <Text style={styles.bold}>Mode Entreprise</Text> :
                      vous serez Admin. Les Commerciaux et Techniciens
                      sont invités par email depuis l&apos;écran « Équipe ».
                    </>
                  )}
                </Text>
              </View>
              )}
            </>
          )}

          <Text style={styles.label}>{t("auth.email")}</Text>
          <TextInput
            testID="login-email-input"
            value={email}
            onChangeText={setEmail}
            placeholder={isIOS ? "vous@exemple.com" : "prenom.nom@entreprise.fr"}
            placeholderTextColor={colors.placeholder}
            keyboardType="email-address"
            autoCapitalize="none"
            style={styles.input}
          />
          <Text style={styles.label}>{t("auth.password")}</Text>
          <View style={styles.passwordWrap}>
            <TextInput
              testID="login-password-input"
              value={password}
              onChangeText={setPassword}
              placeholder="••••••••"
              placeholderTextColor={colors.placeholder}
              secureTextEntry={!showPassword}
              autoCapitalize="none"
              autoCorrect={false}
              style={styles.passwordInput}
            />
            <TouchableOpacity
              onPress={() => setShowPassword((v) => !v)}
              style={styles.eyeBtn}
              activeOpacity={0.6}
              accessibilityLabel={showPassword ? "Masquer le mot de passe" : "Afficher le mot de passe"}
            >
              <Ionicons
                name={showPassword ? "eye-off-outline" : "eye-outline"}
                size={22}
                color={colors.textSecondary}
              />
            </TouchableOpacity>
          </View>

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
                {mode === "login" ? t("auth.signIn").toUpperCase() : t("auth.signUp").toUpperCase()}
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
                {t("auth.forgotPassword")}
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
                    placeholder={isIOS ? "vous@exemple.com" : "vous@entreprise.fr"}
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
                        L&apos;envoi d&apos;email a échoué. Utilisez ce code de secours.
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
                  <View style={[styles.passwordWrap, { backgroundColor: colors.bg }]}>
                    <TextInput
                      testID="forgot-new-password-input"
                      value={forgotNewPassword}
                      onChangeText={setForgotNewPassword}
                      placeholder="Min. 6 caractères"
                      placeholderTextColor={colors.placeholder}
                      secureTextEntry={!showResetPassword}
                      autoCapitalize="none"
                      autoCorrect={false}
                      style={styles.passwordInput}
                    />
                    <TouchableOpacity
                      onPress={() => setShowResetPassword((v) => !v)}
                      style={styles.eyeBtn}
                      activeOpacity={0.6}
                    >
                      <Ionicons
                        name={showResetPassword ? "eye-off-outline" : "eye-outline"}
                        size={22}
                        color={colors.textSecondary}
                      />
                    </TouchableOpacity>
                  </View>
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
  langRow: {
    flexDirection: "row",
    justifyContent: "center",
    gap: 8,
    marginTop: 4,
    marginBottom: 4,
  },
  langPill: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    backgroundColor: colors.surface,
    minHeight: 40,
  },
  langPillActive: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  langFlag: { fontSize: 18 },
  langCode: {
    color: colors.textSecondary,
    fontSize: 12,
    fontWeight: "900",
    letterSpacing: 0.5,
  },
  langCodeActive: { color: "#000" },
  brandWrap: { alignItems: "center", marginTop: 16, marginBottom: 32 },
  brandLogo: {
    width: 84,
    height: 84,
    marginBottom: 12,
  },
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
  // ----- Champ mot de passe avec œil show/hide -----
  passwordWrap: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.inputBg,
    borderColor: colors.borderSubtle,
    borderWidth: 2,
    borderRadius: 8,
    minHeight: 56,
    paddingHorizontal: 14,
  },
  passwordInput: {
    flex: 1,
    color: colors.textPrimary,
    fontSize: 16,
    fontWeight: "600",
    minHeight: 52,
    paddingVertical: 0,
  },
  eyeBtn: {
    paddingHorizontal: 8,
    paddingVertical: 8,
    minHeight: 44,
    minWidth: 44,
    justifyContent: "center",
    alignItems: "center",
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
  // Lot D — Sélecteur Artisan/Entreprise
  typeRow: {
    flexDirection: "row",
    gap: 10,
    marginBottom: 8,
  },
  typeCard: {
    flex: 1,
    backgroundColor: colors.surface,
    borderWidth: 1.5,
    borderColor: colors.borderSubtle,
    borderRadius: 12,
    paddingVertical: 14,
    paddingHorizontal: 10,
    alignItems: "center",
    minHeight: 110,
  },
  typeCardActive: {
    borderColor: colors.primary,
    backgroundColor: "rgba(255, 107, 26, 0.08)",
  },
  typeIconWrap: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: colors.bg,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 8,
  },
  typeIconWrapActive: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  typeTitle: {
    color: colors.textPrimary,
    fontSize: 14,
    fontWeight: "900",
    letterSpacing: 0.3,
  },
  typeTitleActive: {
    color: colors.primary,
  },
  typeDesc: {
    color: colors.textSecondary,
    fontSize: 11,
    marginTop: 4,
    lineHeight: 14,
  },
  // 🆕 V3 — Cartes verticales pour les 3 profils (Artisan/Entreprise/Pro)
  profileCard: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    backgroundColor: colors.surface,
    borderWidth: 1.5,
    borderColor: colors.borderSubtle,
    borderRadius: 12,
    paddingVertical: 14,
    paddingHorizontal: 14,
    marginBottom: 10,
  },
  profileCardActive: {
    borderColor: colors.primary,
    backgroundColor: "rgba(255, 107, 26, 0.08)",
  },
  profileTitleRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  profileBadge: {
    backgroundColor: colors.primary,
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
  },
  profileBadgeText: {
    color: "#000",
    fontSize: 9,
    fontWeight: "900",
    letterSpacing: 0.5,
  },
  profilePrice: {
    color: colors.textSecondary,
    fontSize: 12,
    fontWeight: "700",
    marginTop: 4,
  },
  // 🆕 Build 9 — Styles du champ "Code parrainage" à l'inscription
  referralRow: {
    flexDirection: "row",
    gap: 8,
    alignItems: "center",
  },
  validateBtn: {
    width: 48,
    height: 48,
    borderRadius: 10,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    alignItems: "center",
    justifyContent: "center",
  },
  helpHint: {
    fontSize: 12,
    marginTop: 6,
    fontWeight: "600",
    lineHeight: 16,
  },
});
