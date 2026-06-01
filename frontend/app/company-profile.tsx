import React, { useCallback, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Image,
  KeyboardAvoidingView,
  Modal,
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
import * as ImagePicker from "expo-image-picker";
import { useFocusEffect, useRouter } from "expo-router";
import { api } from "@/src/services/api";
import { useAuth } from "@/src/context/AuthContext";
import { colors } from "@/src/theme";
import FeedbackButton from "@/src/components/FeedbackButton";

type Plan = "free" | "trial" | "pro";

type Profile = {
  company_id: string;
  name?: string;
  artisan_mode?: boolean;
  account_type?: "artisan" | "entreprise";
  logo_base64?: string | null;
  subscription_status?: string;
  subscription_expires_at?: string | null;
  plan?: Plan;
  chantiers_lifetime_count?: number;
  cancel_at_period_end?: boolean;
  cancelled_at?: string | null;
  /** 🚧 Quand True → Beta Gratuite, paywall masqué côté UI. */
  beta_mode?: boolean;
};

const FREE_LIMIT = 3;
const SUPPORT_EMAIL = "info@mesurechassis.com";

function formatDate(iso?: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("fr-FR", {
      day: "2-digit",
      month: "long",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

function planMeta(plan: Plan | undefined): { label: string; bg: string; fg: string } {
  switch (plan) {
    case "pro":
      return { label: "PRO", bg: "#0b3b1c", fg: "#34d399" };
    case "free":
      return { label: "FREE", bg: "#3a1010", fg: colors.anomaly };
    default:
      return { label: "ESSAI", bg: "#2a1c08", fg: colors.warning };
  }
}

export default function CompanyProfile() {
  const router = useRouter();
  const { user, company, refreshCompany, logout } = useAuth();
  const [name, setName] = useState("");
  const [artisanMode, setArtisanMode] = useState(false);
  /** Logo entreprise data URL (PNG/JPG base64) — affiché en PDF. */
  const [logoBase64, setLogoBase64] = useState<string | null>(null);
  const [uploadingLogo, setUploadingLogo] = useState(false);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  // Lot E — RGPD soft-delete
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deletePassword, setDeletePassword] = useState("");
  const [deleteConfirmText, setDeleteConfirmText] = useState("");
  const [deleteOptin, setDeleteOptin] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // C5 — Bascule Artisan ↔ Entreprise
  const [switchOpen, setSwitchOpen] = useState(false);
  const [switching, setSwitching] = useState(false);

  // M1 — Modale de contact support (remplace mailto)
  const [supportOpen, setSupportOpen] = useState(false);
  const [supportSubject, setSupportSubject] = useState("");
  const [supportMessage, setSupportMessage] = useState("");
  const [supportSending, setSupportSending] = useState(false);

  /** Envoie une demande de support au backend (Resend → info@). */
  const sendSupport = useCallback(async () => {
    const msg = supportMessage.trim();
    if (msg.length < 5) {
      Alert.alert("Message trop court", "Détaillez un peu plus votre demande.");
      return;
    }
    setSupportSending(true);
    try {
      await api.post("/support/contact", {
        subject: supportSubject.trim() || "Demande de support",
        message: msg,
      });
      setSupportOpen(false);
      setSupportSubject("");
      setSupportMessage("");
      Alert.alert(
        "✅ Demande envoyée",
        "Merci ! Nous vous répondrons sous 24h à votre adresse email."
      );
    } catch (e: any) {
      Alert.alert(
        "Envoi impossible",
        e?.response?.data?.detail || "Réessayez plus tard."
      );
    } finally {
      setSupportSending(false);
    }
  }, [supportSubject, supportMessage]);

  /** C5 — Bascule Artisan ↔ Entreprise via /api/company/switch-account-type. */
  const doSwitchAccountType = useCallback(async () => {
    const current = (profile?.account_type || "entreprise").toLowerCase();
    const target = current === "artisan" ? "entreprise" : "artisan";
    setSwitching(true);
    try {
      const res = await api.post<Profile>("/company/switch-account-type", {
        account_type: target,
      });
      setProfile(res.data);
      setSwitchOpen(false);
      await refreshCompany();
      Alert.alert(
        "✅ Formule modifiée",
        target === "artisan"
          ? "Vous êtes désormais en formule Artisan (24,99 €/mois)."
          : "Vous êtes désormais en formule Entreprise (54,99 €/mois). La gestion d'équipe est débloquée."
      );
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      Alert.alert(
        "Bascule impossible",
        typeof detail === "string"
          ? detail
          : "Une erreur est survenue. Réessayez."
      );
    } finally {
      setSwitching(false);
    }
  }, [profile?.account_type, refreshCompany]);

  const fetchProfile = useCallback(async () => {
    try {
      const res = await api.get<Profile>("/company/profile");
      setName(res.data?.name ?? "");
      setArtisanMode(!!res.data?.artisan_mode);
      setLogoBase64(res.data?.logo_base64 ?? null);
      setProfile(res.data);
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

  /** Sélectionne un logo depuis la galerie et l'enregistre en base64 dans la company. */
  const pickLogo = useCallback(async () => {
    try {
      // iOS/Android nécessitent la permission galerie. En web pas besoin.
      if (Platform.OS !== "web") {
        const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
        if (!perm.granted) {
          Alert.alert(
            "Accès refusé",
            "Autorisez l'accès à la galerie pour choisir un logo.",
          );
          return;
        }
      }
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        // allowsEditing désactivé : le bouton système "Redimensionner" prêtait
        // à confusion. L'utilisateur sélectionne directement son image et on
        // gère la taille via le contrôle 500 KB en aval.
        allowsEditing: false,
        quality: 0.85,
        base64: true,
      });
      if (result.canceled || !result.assets?.[0]) return;
      const asset = result.assets[0];
      const mime = asset.mimeType || "image/png";
      const dataUrl = `data:${mime};base64,${asset.base64}`;
      // Sanity check : 500 KB max ≈ ~700_000 chars b64
      if ((asset.base64?.length ?? 0) > 800_000) {
        Alert.alert(
          "Logo trop volumineux",
          "Le logo doit faire moins de ~500 KB. Choisissez une image plus petite ou recadrez-la.",
        );
        return;
      }
      setUploadingLogo(true);
      await api.patch("/company/profile", { logo_base64: dataUrl });
      setLogoBase64(dataUrl);
      await refreshCompany();
      Alert.alert(
        "✅ Logo enregistré",
        "Votre logo apparaîtra désormais en haut des PDF générés.",
      );
    } catch (e: any) {
      Alert.alert(
        "Erreur",
        e?.response?.data?.detail ||
          "Impossible d'enregistrer le logo. Réessayez.",
      );
    } finally {
      setUploadingLogo(false);
    }
  }, [refreshCompany]);

  const removeLogo = useCallback(() => {
    Alert.alert(
      "Supprimer le logo ?",
      "Les PDF générés n'auront plus de logo personnalisé.",
      [
        { text: "Annuler", style: "cancel" },
        {
          text: "Supprimer",
          style: "destructive",
          onPress: async () => {
            try {
              setUploadingLogo(true);
              await api.patch("/company/profile", { logo_base64: "" });
              setLogoBase64(null);
              await refreshCompany();
            } catch {
              Alert.alert("Erreur", "Suppression impossible.");
            } finally {
              setUploadingLogo(false);
            }
          },
        },
      ],
    );
  }, [refreshCompany]);

  /** Lot E — Soft-delete RGPD du compte courant. */
  const doDeleteAccount = useCallback(async () => {
    if (!deletePassword.trim()) {
      Alert.alert("Mot de passe requis", "Saisissez votre mot de passe.");
      return;
    }
    if (deleteConfirmText.trim().toUpperCase() !== "SUPPRIMER") {
      Alert.alert(
        "Confirmation invalide",
        "Tapez SUPPRIMER en majuscules pour confirmer.",
      );
      return;
    }
    setDeleting(true);
    try {
      const res = await api.delete("/auth/me", {
        data: {
          password: deletePassword,
          confirm_text: deleteConfirmText.trim().toUpperCase(),
          marketing_optin: deleteOptin,
        },
      });
      const msg =
        (res?.data as any)?.message ||
        "Compte supprimé. Toutes vos données ont été anonymisées.";
      setDeleteOpen(false);
      setDeletePassword("");
      setDeleteConfirmText("");
      setDeleteOptin(false);
      Alert.alert("✅ Compte supprimé", msg, [
        {
          text: "OK",
          onPress: async () => {
            try {
              await logout();
            } catch {
              /* ignore */
            }
          },
        },
      ]);
    } catch (e: any) {
      Alert.alert(
        "Suppression impossible",
        e?.response?.data?.detail || "Une erreur s'est produite.",
      );
    } finally {
      setDeleting(false);
    }
  }, [
    deletePassword,
    deleteConfirmText,
    deleteOptin,
    logout,
  ]);

  const save = async () => {
    setSaving(true);
    try {
      await api.patch("/company/profile", {
        name: name.trim() || null,
        artisan_mode: artisanMode,
        logo_base64: logoBase64,
      });
      await refreshCompany();
      await fetchProfile();
      Alert.alert(
        "✅ Profil société mis à jour",
        artisanMode
          ? "Mode Artisan Unique activé — vous avez désormais accès à toutes les fonctionnalités."
          : "Mode Artisan Unique désactivé."
      );
    } catch (e: any) {
      const msg =
        e?.response?.status === 403
          ? "Réservé à l'administrateur de la société."
          : "Enregistrement impossible.";
      Alert.alert("Erreur", msg);
    } finally {
      setSaving(false);
    }
  };

  const doCancel = async () => {
    setCancelling(true);
    try {
      const res = await api.post<Profile>("/company/subscription/cancel");
      setProfile(res.data);
      await refreshCompany();
      setConfirmOpen(false);
      Alert.alert(
        "Annulation programmée",
        `Votre accès Pro reste actif jusqu'au ${formatDate(
          res.data.subscription_expires_at
        )}. Après cette date, l'écran de verrouillage s'activera automatiquement.`
      );
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      const msg =
        typeof detail === "string"
          ? detail
          : e?.response?.status === 403
            ? "Seul l'administrateur peut annuler l'abonnement."
            : "Annulation impossible.";
      Alert.alert("Erreur", msg);
    } finally {
      setCancelling(false);
    }
  };

  const doReactivate = async () => {
    setCancelling(true);
    try {
      const res = await api.post<Profile>("/company/subscription/reactivate");
      setProfile(res.data);
      await refreshCompany();
      Alert.alert("✅ Abonnement réactivé", "L'annulation a été annulée.");
    } catch {
      Alert.alert("Erreur", "Réactivation impossible.");
    } finally {
      setCancelling(false);
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
  const plan = (profile?.plan ?? "trial") as Plan;
  const meta = planMeta(plan);
  const used = profile?.chantiers_lifetime_count ?? 0;
  const cancelScheduled = !!profile?.cancel_at_period_end;
  const expiresLabel = formatDate(profile?.subscription_expires_at);
  // 🚧 BETA GRATUITE : flag global (backend BETA_MODE) → masque paywall/freemium.
  const betaMode = !!profile?.beta_mode;
  // Le bouton "Se désabonner" est dispo : admin + accès actif (trial ou pro) + pas déjà annulé
  // → désactivé en mode beta : remplacé par un bouton "Donner mon avis / Contacter le support".
  const canUnsubscribe =
    !betaMode &&
    isAdmin &&
    !cancelScheduled &&
    profile?.subscription_status !== "suspended" &&
    (plan === "pro" || plan === "trial" || profile?.subscription_status === "active");
  // Pour Free : afficher l'usage des chantiers (désactivé en mode beta)
  const isFree = !betaMode && plan === "free";
  const remaining = Math.max(0, FREE_LIMIT - used);
  const overLimit = isFree && used >= FREE_LIMIT;

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
          {/* === BLOC ABONNEMENT === */}
          <View style={styles.card}>
            <View style={styles.rowBetween}>
              <Text style={styles.section}>ABONNEMENT & FACTURATION</Text>
              {betaMode ? (
                <View style={styles.betaBadge}>
                  <Ionicons name="rocket" size={12} color="#34d399" />
                  <Text style={styles.betaBadgeText}>BETA GRATUITE</Text>
                </View>
              ) : (
                <View
                  style={[
                    styles.planBadge,
                    { backgroundColor: meta.bg, borderColor: meta.fg },
                  ]}
                >
                  <Text style={[styles.planBadgeText, { color: meta.fg }]}>
                    {meta.label}
                  </Text>
                </View>
              )}
            </View>

            {betaMode ? (
              <>
                <Text style={styles.betaIntro}>
                  🎉 Profitez de l'accès complet à MesureChâssis pendant la
                  phase de test. Aucun paiement n'est requis.
                </Text>
                <Text style={styles.betaFeedback}>
                  Vos retours nous aident à grandir ! Signalez-nous la moindre
                  idée via{" "}
                  <Text style={styles.bold}>{SUPPORT_EMAIL}</Text> 💬
                </Text>
                {isAdmin && (
                  <TouchableOpacity
                    testID="contact-support-button"
                    onPress={() => setSupportOpen(true)}
                    activeOpacity={0.85}
                    style={[styles.btn, styles.btnPrimary, { marginTop: 14 }]}
                  >
                    <Ionicons name="mail" size={20} color="#000" />
                    <Text style={styles.btnPrimaryText}>
                      DONNER MON AVIS / CONTACTER LE SUPPORT
                    </Text>
                  </TouchableOpacity>
                )}
              </>
            ) : (
              <>
                <View style={styles.kvRow}>
                  <Text style={styles.kvLabel}>Statut</Text>
                  <Text style={styles.kvValue}>
                    {profile?.subscription_status?.toUpperCase() ?? "—"}
                  </Text>
                </View>
                <View style={styles.kvRow}>
                  <Text style={styles.kvLabel}>
                    {cancelScheduled ? "Accès Pro jusqu'au" : "Expiration"}
                  </Text>
                  <Text style={styles.kvValue}>{expiresLabel}</Text>
                </View>
              </>
            )}

            {isFree && (
              <View style={styles.freeUsageBox}>
                <View style={styles.row}>
                  <Ionicons
                    name={overLimit ? "lock-closed" : "alert-circle"}
                    size={18}
                    color={overLimit ? colors.anomaly : colors.warning}
                  />
                  <Text style={styles.freeUsageTitle}>
                    Plan Freemium — {used}/{FREE_LIMIT} chantiers utilisés
                  </Text>
                </View>
                <Text style={styles.freeUsageBody}>
                  {overLimit
                    ? "Limite atteinte. Les exports (PDF/Excel/CSV/JSON) sont verrouillés. " +
                      "Supprimer un chantier ne réinitialise PAS le compteur (anti-fraude). " +
                      "Passez en Pro pour débloquer."
                    : `Il vous reste ${remaining} chantier(s) avant la limite Freemium. ` +
                      `Les exports techniques sont déjà verrouillés sur ce plan.`}
                </Text>
              </View>
            )}

            {cancelScheduled && (
              <View style={styles.cancelBox}>
                <View style={styles.row}>
                  <Ionicons name="time-outline" size={18} color={colors.warning} />
                  <Text style={styles.cancelBoxTitle}>
                    Annulation programmée
                  </Text>
                </View>
                <Text style={styles.cancelBoxBody}>
                  Votre accès Pro reste actif jusqu'au{" "}
                  <Text style={styles.bold}>{expiresLabel}</Text>. À cette date,
                  l'écran de verrouillage plein-écran sera activé automatiquement.
                </Text>
                {isAdmin && (
                  <TouchableOpacity
                    testID="reactivate-subscription-button"
                    onPress={doReactivate}
                    disabled={cancelling}
                    activeOpacity={0.85}
                    style={[styles.btn, styles.btnGhost, { marginTop: 12 }]}
                  >
                    {cancelling ? (
                      <ActivityIndicator color={colors.textPrimary} />
                    ) : (
                      <>
                        <Ionicons
                          name="refresh"
                          size={18}
                          color={colors.textPrimary}
                        />
                        <Text style={styles.btnGhostText}>
                          RÉACTIVER L'ABONNEMENT
                        </Text>
                      </>
                    )}
                  </TouchableOpacity>
                )}
              </View>
            )}

            {canUnsubscribe && (
              <TouchableOpacity
                testID="unsubscribe-button"
                onPress={() => setConfirmOpen(true)}
                disabled={cancelling}
                activeOpacity={0.85}
                style={[styles.btn, styles.btnDanger, { marginTop: 14 }]}
              >
                <Ionicons name="close-circle" size={20} color="#fff" />
                <Text style={styles.btnDangerText}>SE DÉSABONNER</Text>
              </TouchableOpacity>
            )}

            {!isAdmin && (
              <Text style={styles.warnNote}>
                ⚠ Seul l'administrateur principal peut gérer la facturation.
              </Text>
            )}
          </View>

          {/* === IDENTITÉ === */}
          <View style={styles.card}>
            <Text style={styles.section}>IDENTITÉ</Text>
            <Text style={styles.label}>ID Société</Text>
            <View style={styles.badge}>
              <Ionicons
                name="business-outline"
                size={14}
                color={colors.textSecondary}
              />
              <Text style={styles.badgeText}>
                {company?.company_id ?? "default"}
              </Text>
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

          {/* === LOGO ENTREPRISE === */}
          <View style={styles.card}>
            <Text style={styles.section}>LOGO ENTREPRISE</Text>
            <Text style={styles.help}>
              Apposé en haut de vos{" "}
              <Text style={styles.bold}>PDF de mesurage</Text> (document
              interne uniquement). Formats recommandés : PNG/JPG, ratio 16:9,
              fond clair.
            </Text>

            <View style={styles.logoBox}>
              {logoBase64 ? (
                <Image
                  source={{ uri: logoBase64 }}
                  style={styles.logoPreview}
                  resizeMode="contain"
                />
              ) : (
                <View style={styles.logoEmpty}>
                  <Ionicons
                    name="image-outline"
                    size={36}
                    color={colors.textSecondary}
                  />
                  <Text style={styles.logoEmptyText}>Aucun logo</Text>
                </View>
              )}
            </View>

            <View style={styles.logoActions}>
              <TouchableOpacity
                testID="company-logo-pick"
                onPress={pickLogo}
                disabled={!isAdmin || uploadingLogo}
                activeOpacity={0.85}
                style={[
                  styles.logoBtnPrimary,
                  (!isAdmin || uploadingLogo) && { opacity: 0.5 },
                ]}
              >
                {uploadingLogo ? (
                  <ActivityIndicator color="#000" />
                ) : (
                  <>
                    <Ionicons
                      name={logoBase64 ? "swap-horizontal" : "cloud-upload"}
                      size={16}
                      color="#000"
                    />
                    <Text style={styles.logoBtnPrimaryText}>
                      {logoBase64 ? "REMPLACER" : "CHOISIR UN LOGO"}
                    </Text>
                  </>
                )}
              </TouchableOpacity>

              {logoBase64 && (
                <TouchableOpacity
                  testID="company-logo-remove"
                  onPress={removeLogo}
                  disabled={!isAdmin || uploadingLogo}
                  activeOpacity={0.85}
                  style={[
                    styles.logoBtnGhost,
                    (!isAdmin || uploadingLogo) && { opacity: 0.5 },
                  ]}
                >
                  <Ionicons
                    name="trash-outline"
                    size={16}
                    color={colors.alert}
                  />
                  <Text style={styles.logoBtnGhostText}>SUPPRIMER</Text>
                </TouchableOpacity>
              )}
            </View>

            {!isAdmin && (
              <Text style={styles.warnNote}>
                ⓘ Seul l'administrateur peut modifier le logo.
              </Text>
            )}
          </View>

          {/* === TYPE DE COMPTE (C5 — Bascule Artisan/Entreprise) === */}
          <View style={styles.card}>
            <Text style={styles.section}>TYPE DE COMPTE</Text>
            <Text style={styles.help}>
              Choisissez la formule adaptée à votre activité. Vous pouvez
              changer à tout moment.
            </Text>

            <View style={styles.accountTypeBox}>
              <View
                style={[
                  styles.accountTypeIcon,
                  {
                    backgroundColor:
                      profile?.account_type === "artisan"
                        ? "rgba(255, 107, 26, 0.18)"
                        : "rgba(59, 130, 246, 0.18)",
                  },
                ]}
              >
                <Ionicons
                  name={
                    profile?.account_type === "artisan" ? "person" : "business"
                  }
                  size={20}
                  color={
                    profile?.account_type === "artisan"
                      ? colors.primary
                      : "#3B82F6"
                  }
                />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.accountTypeTitle}>
                  {profile?.account_type === "artisan"
                    ? "Compte Artisan"
                    : "Compte Entreprise"}
                </Text>
                <Text style={styles.accountTypeDesc}>
                  {profile?.account_type === "artisan"
                    ? "Compte solo, 1 utilisateur unique — 24,99 €/mois"
                    : "Admin + Commercial + Technicien inclus — 54,99 €/mois (+4,99 €/utilisateur supplémentaire)"}
                </Text>
              </View>
            </View>

            {isAdmin && (
              <TouchableOpacity
                testID="switch-account-type-button"
                onPress={() => setSwitchOpen(true)}
                activeOpacity={0.85}
                style={[styles.btn, styles.btnGhost, { marginTop: 14 }]}
              >
                <Ionicons
                  name="swap-horizontal"
                  size={18}
                  color={colors.textPrimary}
                />
                <Text style={styles.btnGhostText}>
                  {profile?.account_type === "artisan"
                    ? "PASSER EN COMPTE ENTREPRISE (54,99 €/mois)"
                    : "PASSER EN COMPTE ARTISAN (24,99 €/mois)"}
                </Text>
              </TouchableOpacity>
            )}
            {!isAdmin && (
              <Text style={styles.warnNote}>
                ⓘ Seul l'administrateur peut modifier la formule.
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

          {/* === MES INFOS PERSONNELLES === */}
          <View style={styles.card}>
            <View style={styles.row}>
              <Ionicons name="person-circle-outline" size={18} color={colors.primary} />
              <Text style={styles.dangerTitle}>MES INFORMATIONS</Text>
            </View>
            <Text style={styles.help}>
              Modifier votre nom, email, téléphone ou mot de passe de connexion.
            </Text>
            <TouchableOpacity
              testID="open-my-info"
              onPress={() => router.push("/me")}
              activeOpacity={0.85}
              style={[styles.logoBtnPrimary, { marginTop: 12 }]}
            >
              <Ionicons name="create-outline" size={16} color="#000" />
              <Text style={styles.logoBtnPrimaryText}>MODIFIER MES INFOS</Text>
            </TouchableOpacity>
          </View>

          {/* === MON ABONNEMENT === */}
          <View style={styles.card}>
            <View style={styles.row}>
              <Ionicons name="card-outline" size={18} color={colors.primary} />
              <Text style={styles.dangerTitle}>MON ABONNEMENT</Text>
            </View>
            <Text style={styles.help}>
              Consulter votre plan, gérer votre moyen de paiement, télécharger
              vos factures ou changer de formule.
            </Text>
            <TouchableOpacity
              testID="open-subscription"
              onPress={() => router.push("/subscription")}
              activeOpacity={0.85}
              style={[styles.logoBtnPrimary, { marginTop: 12 }]}
            >
              <Ionicons name="diamond-outline" size={16} color="#000" />
              <Text style={styles.logoBtnPrimaryText}>VOIR MES PLANS</Text>
            </TouchableOpacity>
          </View>

          {/* === LOT E — ZONE DANGER : Suppression du compte (RGPD) === */}
          <View style={[styles.card, styles.dangerCard]}>
            <View style={styles.dangerHeader}>
              <Ionicons name="warning" size={18} color={colors.alert} />
              <Text style={styles.dangerTitle}>ZONE DANGER</Text>
            </View>
            <Text style={styles.help}>
              Vous pouvez supprimer définitivement votre compte. Toutes vos
              données personnelles seront anonymisées conformément au{" "}
              <Text style={styles.bold}>RGPD</Text>. Cette action est{" "}
              <Text style={styles.bold}>irréversible</Text>.
            </Text>
            <TouchableOpacity
              testID="open-delete-account"
              onPress={() => setDeleteOpen(true)}
              activeOpacity={0.85}
              style={styles.dangerBtn}
            >
              <Ionicons name="trash-bin" size={16} color="#fff" />
              <Text style={styles.dangerBtnText}>SUPPRIMER MON COMPTE</Text>
            </TouchableOpacity>
          </View>

          {/* === FEEDBACK BUTTON === */}
          <FeedbackButton />
        </ScrollView>

        {/* === Modal Confirmation Désabonnement === */}
        <Modal
          visible={confirmOpen}
          transparent
          animationType="fade"
          onRequestClose={() => setConfirmOpen(false)}
        >
          <View style={styles.modalBackdrop}>
            <View style={styles.modalCard}>
              <View style={styles.modalIconWrap}>
                <Ionicons
                  name="warning"
                  size={36}
                  color={colors.warning}
                />
              </View>
              <Text style={styles.modalTitle}>CONFIRMER LE DÉSABONNEMENT</Text>
              <Text style={styles.modalBody}>
                Votre accès Pro restera actif jusqu'au{" "}
                <Text style={styles.bold}>{expiresLabel}</Text>.
                {"\n\n"}
                Après cette date, l'écran de verrouillage plein-écran sera
                activé automatiquement. Vous pourrez réactiver l'abonnement à
                tout moment avant l'expiration.
              </Text>
              <View style={styles.modalActions}>
                <TouchableOpacity
                  testID="cancel-unsubscribe-button"
                  onPress={() => setConfirmOpen(false)}
                  disabled={cancelling}
                  activeOpacity={0.85}
                  style={[styles.btn, styles.btnGhost, { flex: 1 }]}
                >
                  <Text style={styles.btnGhostText}>ANNULER</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  testID="confirm-unsubscribe-button"
                  onPress={doCancel}
                  disabled={cancelling}
                  activeOpacity={0.85}
                  style={[styles.btn, styles.btnDanger, { flex: 1 }]}
                >
                  {cancelling ? (
                    <ActivityIndicator color="#fff" />
                  ) : (
                    <Text style={styles.btnDangerText}>CONFIRMER</Text>
                  )}
                </TouchableOpacity>
              </View>
            </View>
          </View>
        </Modal>

        {/* === Modal Suppression de compte (RGPD) === */}
        <Modal
          visible={deleteOpen}
          transparent
          animationType="fade"
          onRequestClose={() => setDeleteOpen(false)}
        >
          <View style={styles.modalBackdrop}>
            <View style={styles.modalCard}>
              <View style={styles.modalHead}>
                <Ionicons name="warning" size={20} color={colors.alert} />
                <Text style={styles.modalTitle}>SUPPRIMER MON COMPTE</Text>
              </View>
              <Text style={styles.modalBody}>
                Cette action est <Text style={styles.bold}>irréversible</Text>.
                Toutes vos données personnelles seront anonymisées
                conformément au RGPD.
              </Text>

              <Text style={styles.labelSmall}>Votre mot de passe</Text>
              <TextInput
                testID="delete-password-input"
                value={deletePassword}
                onChangeText={setDeletePassword}
                placeholder="Mot de passe actuel"
                placeholderTextColor={colors.placeholder}
                secureTextEntry
                style={styles.input}
              />

              <Text style={styles.labelSmall}>
                Tapez <Text style={styles.bold}>SUPPRIMER</Text> pour confirmer
              </Text>
              <TextInput
                testID="delete-confirm-input"
                value={deleteConfirmText}
                onChangeText={setDeleteConfirmText}
                placeholder="SUPPRIMER"
                placeholderTextColor={colors.placeholder}
                autoCapitalize="characters"
                style={styles.input}
              />

              <TouchableOpacity
                testID="delete-optin-toggle"
                onPress={() => setDeleteOptin((v) => !v)}
                activeOpacity={0.75}
                style={styles.optinRow}
              >
                <View
                  style={[
                    styles.checkbox,
                    deleteOptin && styles.checkboxChecked,
                  ]}
                >
                  {deleteOptin && (
                    <Ionicons name="checkmark" size={16} color="#000" />
                  )}
                </View>
                <Text style={styles.optinText}>
                  Je souhaite continuer à recevoir des offres commerciales
                  de MesureChâssis (mon email sera conservé uniquement à cette
                  fin).
                </Text>
              </TouchableOpacity>
              <Text style={styles.optinHint}>
                Si vous décochez cette case, votre email sera effacé
                strictement conformément au RGPD.
              </Text>

              <View style={styles.modalActions}>
                <TouchableOpacity
                  testID="cancel-delete-account"
                  onPress={() => {
                    setDeleteOpen(false);
                    setDeletePassword("");
                    setDeleteConfirmText("");
                  }}
                  disabled={deleting}
                  activeOpacity={0.85}
                  style={[styles.btn, styles.btnGhost, { flex: 1 }]}
                >
                  <Text style={styles.btnGhostText}>ANNULER</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  testID="confirm-delete-account"
                  onPress={doDeleteAccount}
                  disabled={deleting}
                  activeOpacity={0.85}
                  style={[styles.btn, styles.btnDanger, { flex: 1 }]}
                >
                  {deleting ? (
                    <ActivityIndicator color="#fff" />
                  ) : (
                    <Text style={styles.btnDangerText}>SUPPRIMER</Text>
                  )}
                </TouchableOpacity>
              </View>
            </View>
          </View>
        </Modal>

        {/* === C5 — Modal Bascule Artisan ↔ Entreprise === */}
        <Modal
          visible={switchOpen}
          transparent
          animationType="fade"
          onRequestClose={() => setSwitchOpen(false)}
        >
          <View style={styles.modalBackdrop}>
            <View style={styles.modalCard}>
              <View style={styles.modalIconWrap}>
                <Ionicons
                  name="swap-horizontal"
                  size={36}
                  color={colors.primary}
                />
              </View>
              <Text style={styles.modalTitle}>
                {profile?.account_type === "artisan"
                  ? "PASSER EN COMPTE ENTREPRISE"
                  : "PASSER EN COMPTE ARTISAN"}
              </Text>

              {profile?.account_type === "artisan" ? (
                <Text style={styles.modalBody}>
                  Vous allez passer en formule{" "}
                  <Text style={styles.bold}>Entreprise — 54,99 €/mois</Text>.
                  {"\n\n"}
                  ✅ Vous débloquez la gestion d'équipe (Commercial + Technicien
                  inclus, +4,99 €/utilisateur supplémentaire).
                  {"\n\n"}
                  ✅ Vous conservez tous vos chantiers et vos données.
                </Text>
              ) : (
                <Text style={styles.modalBody}>
                  Vous allez passer en formule{" "}
                  <Text style={styles.bold}>Artisan — 24,99 €/mois</Text>.
                  {"\n\n"}
                  ✅ Vous{" "}
                  <Text style={styles.bold}>conservez tous vos chantiers</Text>{" "}
                  ainsi que les noms des personnes ayant pris les mesures.
                  {"\n\n"}
                  ⚠ Vous{" "}
                  <Text style={styles.bold}>
                    perdez toutes les fonctionnalités dédiées aux équipes
                  </Text>{" "}
                  (gestion des collaborateurs, transmission commerciale,
                  validation technicien…).
                  {"\n\n"}
                  ✅ Vous obtenez{" "}
                  <Text style={styles.bold}>
                    toutes les fonctionnalités de l'Artisan
                  </Text>{" "}
                  (relevé, exports techniques, PDF, etc.).
                  {"\n\n"}
                  ℹ Si des collaborateurs sont actifs dans votre équipe,
                  supprimez-les d'abord depuis la page Équipe.
                </Text>
              )}

              <View style={styles.modalActions}>
                <TouchableOpacity
                  testID="cancel-switch-account"
                  onPress={() => setSwitchOpen(false)}
                  disabled={switching}
                  activeOpacity={0.85}
                  style={[styles.btn, styles.btnGhost, { flex: 1 }]}
                >
                  <Text style={styles.btnGhostText}>ANNULER</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  testID="confirm-switch-account"
                  onPress={doSwitchAccountType}
                  disabled={switching}
                  activeOpacity={0.85}
                  style={[styles.btn, styles.btnPrimary, { flex: 1.3 }]}
                >
                  {switching ? (
                    <ActivityIndicator color="#000" />
                  ) : (
                    <Text style={styles.btnPrimaryText}>CONFIRMER</Text>
                  )}
                </TouchableOpacity>
              </View>
            </View>
          </View>
        </Modal>

        {/* === M1 — Modal Contact Support === */}
        <Modal
          visible={supportOpen}
          transparent
          animationType="slide"
          onRequestClose={() => setSupportOpen(false)}
        >
          <KeyboardAvoidingView
            behavior={Platform.OS === "ios" ? "padding" : undefined}
            style={styles.modalBackdrop}
          >
            <View style={styles.modalCard}>
              <View style={styles.modalIconWrap}>
                <Ionicons name="mail" size={32} color={colors.primary} />
              </View>
              <Text style={styles.modalTitle}>CONTACTER LE SUPPORT</Text>
              <Text style={styles.modalBody}>
                Décrivez votre demande, nous vous répondrons à votre adresse
                email sous 24h.
              </Text>

              <Text style={[styles.labelSmall, { textAlign: "left" }]}>
                Sujet (facultatif)
              </Text>
              <TextInput
                testID="support-subject-input"
                value={supportSubject}
                onChangeText={setSupportSubject}
                placeholder="Ex : Question facturation, bug constaté…"
                placeholderTextColor={colors.placeholder}
                maxLength={200}
                style={styles.input}
              />

              <Text style={[styles.labelSmall, { textAlign: "left" }]}>
                Votre message
              </Text>
              <TextInput
                testID="support-message-input"
                value={supportMessage}
                onChangeText={setSupportMessage}
                placeholder="Détaillez ici votre demande, votre retour ou votre suggestion…"
                placeholderTextColor={colors.placeholder}
                multiline
                numberOfLines={6}
                maxLength={5000}
                style={[
                  styles.input,
                  {
                    minHeight: 120,
                    textAlignVertical: "top",
                    paddingTop: 12,
                  },
                ]}
              />
              <Text style={styles.optinHint}>
                {supportMessage.length}/5000 caractères
              </Text>

              <View style={styles.modalActions}>
                <TouchableOpacity
                  testID="cancel-support"
                  onPress={() => setSupportOpen(false)}
                  disabled={supportSending}
                  activeOpacity={0.85}
                  style={[styles.btn, styles.btnGhost, { flex: 1 }]}
                >
                  <Text style={styles.btnGhostText}>ANNULER</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  testID="send-support"
                  onPress={sendSupport}
                  disabled={supportSending}
                  activeOpacity={0.85}
                  style={[styles.btn, styles.btnPrimary, { flex: 1.3 }]}
                >
                  {supportSending ? (
                    <ActivityIndicator color="#000" />
                  ) : (
                    <>
                      <Ionicons name="send" size={16} color="#000" />
                      <Text style={styles.btnPrimaryText}>ENVOYER</Text>
                    </>
                  )}
                </TouchableOpacity>
              </View>
            </View>
          </KeyboardAvoidingView>
        </Modal>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: colors.bg },
  center: { alignItems: "center", justifyContent: "center" },
  row: { flexDirection: "row", alignItems: "center", gap: 8 },
  rowBetween: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 8,
  },
  topBar: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSubtle,
  },
  topTitle: {
    color: colors.textPrimary,
    fontWeight: "900",
    letterSpacing: 1.2,
    fontSize: 13,
  },
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
  // === Type de compte (lecture seule) ===
  accountTypeBox: {
    flexDirection: "row",
    alignItems: "center",
    gap: 14,
    marginTop: 14,
    padding: 14,
    backgroundColor: colors.bg,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
  },
  accountTypeIcon: {
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: "center",
    justifyContent: "center",
  },
  accountTypeTitle: {
    color: colors.textPrimary,
    fontWeight: "900",
    fontSize: 14,
    letterSpacing: 0.3,
  },
  accountTypeDesc: {
    color: colors.textSecondary,
    fontSize: 12,
    marginTop: 4,
    lineHeight: 17,
  },
  // === Logo entreprise ===
  logoBox: {
    marginTop: 14,
    backgroundColor: colors.bg,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    borderStyle: "dashed",
    borderRadius: 12,
    minHeight: 130,
    alignItems: "center",
    justifyContent: "center",
    padding: 10,
  },
  logoPreview: {
    width: "100%",
    height: 110,
  },
  logoEmpty: {
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
  },
  logoEmptyText: {
    color: colors.textSecondary,
    fontSize: 12,
    letterSpacing: 0.4,
  },
  logoActions: {
    flexDirection: "row",
    gap: 10,
    marginTop: 12,
  },
  logoBtnPrimary: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    backgroundColor: colors.primary,
    borderRadius: 10,
    paddingVertical: 12,
  },
  logoBtnPrimaryText: {
    color: "#000",
    fontWeight: "900",
    letterSpacing: 0.6,
    fontSize: 12,
  },
  logoBtnGhost: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    backgroundColor: "transparent",
    borderWidth: 1,
    borderColor: colors.alert,
    borderRadius: 10,
    paddingVertical: 12,
    paddingHorizontal: 14,
  },
  logoBtnGhostText: {
    color: colors.alert,
    fontWeight: "800",
    letterSpacing: 0.6,
    fontSize: 12,
  },
  // === Lot E — Suppression de compte (Zone Danger) ===
  dangerCard: {
    borderColor: "rgba(239, 68, 68, 0.35)",
    backgroundColor: "rgba(239, 68, 68, 0.06)",
  },
  dangerHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginBottom: 10,
  },
  dangerTitle: {
    color: colors.alert,
    fontSize: 13,
    fontWeight: "900",
    letterSpacing: 1.2,
  },
  dangerBtn: {
    marginTop: 14,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    backgroundColor: colors.alert,
    borderRadius: 10,
    paddingVertical: 12,
  },
  dangerBtnText: {
    color: "#fff",
    fontSize: 13,
    fontWeight: "900",
    letterSpacing: 0.8,
  },
  labelSmall: {
    color: colors.textSecondary,
    fontSize: 11,
    fontWeight: "700",
    letterSpacing: 0.5,
    marginTop: 12,
    marginBottom: 6,
  },
  optinRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 10,
    marginTop: 14,
    padding: 12,
    backgroundColor: colors.bg,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
  },
  checkbox: {
    width: 22,
    height: 22,
    borderRadius: 5,
    borderWidth: 2,
    borderColor: colors.borderStrong,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.bg,
  },
  checkboxChecked: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  optinText: {
    flex: 1,
    color: colors.textPrimary,
    fontSize: 12,
    lineHeight: 17,
  },
  optinHint: {
    color: colors.textSecondary,
    fontSize: 11,
    fontStyle: "italic",
    marginTop: 6,
    marginBottom: 4,
  },
  btn: {
    minHeight: 52,
    borderRadius: 12,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    paddingHorizontal: 14,
  },
  btnPrimary: { backgroundColor: colors.primary },
  btnPrimaryText: { color: "#000", fontWeight: "900", letterSpacing: 1 },
  btnDanger: { backgroundColor: colors.anomaly },
  btnDangerText: {
    color: "#fff",
    fontWeight: "900",
    letterSpacing: 1,
    fontSize: 13,
  },
  btnGhost: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderStrong,
  },
  btnGhostText: {
    color: colors.textPrimary,
    fontWeight: "800",
    letterSpacing: 0.8,
    fontSize: 13,
  },
  planBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 6,
    borderWidth: 1,
  },
  planBadgeText: { fontSize: 11, fontWeight: "900", letterSpacing: 1 },
  betaBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: "#34d399",
    backgroundColor: "#0b3b1c",
  },
  betaBadgeText: {
    fontSize: 11,
    fontWeight: "900",
    letterSpacing: 1,
    color: "#34d399",
  },
  betaIntro: {
    color: colors.textPrimary,
    fontSize: 13,
    lineHeight: 19,
    marginTop: 14,
  },
  betaFeedback: {
    color: colors.textSecondary,
    fontSize: 12,
    lineHeight: 18,
    marginTop: 8,
    fontStyle: "italic",
  },
  kvRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 8,
    borderTopWidth: 1,
    borderTopColor: colors.borderSubtle,
  },
  kvLabel: { color: colors.textSecondary, fontSize: 12 },
  kvValue: { color: colors.textPrimary, fontSize: 13, fontWeight: "700" },
  freeUsageBox: {
    backgroundColor: "#1f0a0a",
    borderColor: colors.anomaly,
    borderWidth: 1,
    borderRadius: 10,
    padding: 12,
    marginTop: 12,
  },
  freeUsageTitle: {
    color: colors.anomaly,
    fontWeight: "900",
    fontSize: 13,
    letterSpacing: 0.5,
  },
  freeUsageBody: {
    color: colors.textPrimary,
    fontSize: 12,
    lineHeight: 17,
    marginTop: 6,
  },
  cancelBox: {
    backgroundColor: "#2a1c08",
    borderColor: colors.warning,
    borderWidth: 1,
    borderRadius: 10,
    padding: 12,
    marginTop: 12,
  },
  cancelBoxTitle: {
    color: colors.warning,
    fontWeight: "900",
    fontSize: 13,
    letterSpacing: 0.5,
  },
  cancelBoxBody: {
    color: colors.textPrimary,
    fontSize: 12,
    lineHeight: 17,
    marginTop: 6,
  },
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
    borderWidth: 1,
    borderColor: colors.borderStrong,
    padding: 22,
    width: "100%",
    maxWidth: 460,
  },
  modalIconWrap: { alignItems: "center", marginBottom: 12 },
  modalTitle: {
    color: colors.textPrimary,
    fontWeight: "900",
    fontSize: 15,
    letterSpacing: 1,
    textAlign: "center",
    marginBottom: 10,
  },
  modalBody: {
    color: colors.textSecondary,
    fontSize: 13,
    lineHeight: 19,
    textAlign: "center",
  },
  modalActions: { flexDirection: "row", gap: 10, marginTop: 18 },
});
