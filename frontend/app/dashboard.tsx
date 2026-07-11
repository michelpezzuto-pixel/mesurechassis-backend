import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  KeyboardAvoidingView,
  Modal,
  Platform,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useFocusEffect, useRouter } from "expo-router";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { api } from "@/src/services/api";
import { useAuth } from "@/src/context/AuthContext";
import { useTranslation } from "react-i18next";
import { subscribeQueueSize, syncQueue, enqueueChantier, isNetworkError } from "@/src/services/offlineQueue";
import { colors, statusMeta, getStatusLabelI18n, READY_FOR_EXPORT_BADGE } from "@/src/theme";
import { useResponsive } from "@/src/utils/responsive";
import FilleulInviteBanner from "@/src/components/FilleulInviteBanner";
import ChatHelp from "@/src/components/ChatHelp";
import AppointmentPicker from "@/src/components/AppointmentPicker";
import OnboardingCard from "@/src/components/OnboardingCard";
import { AddressAutocomplete } from "@/src/components/AddressAutocomplete";

type Chantier = {
  id: string;
  client_name: string;
  address: string;
  status: string;
  created_at: string;
};

// Filtres alignés sur le pipeline 4-étapes (filtrage côté client par stage).
// 🆕 V3 — Les labels sont désormais traduits via i18n dans le composant.
//   La constante statique a été remplacée par un FILTERS local dans Dashboard.

export default function Dashboard() {
  const { user, signOut, company } = useAuth();
  const router = useRouter();
  const { t } = useTranslation();
  // 🆕 V3 — Filtres traduits dynamiquement via i18n (au lieu d'une constante statique)
  const FILTERS: { key: "all" | "measure" | "verify" | "fab" | "done"; labelKey: string }[] = [
    { key: "all", labelKey: "dashboard.filters.all" },
    { key: "measure", labelKey: "dashboard.filters.toMeasure" },
    { key: "verify", labelKey: "dashboard.filters.validated" },
    { key: "fab", labelKey: "dashboard.filters.inProduction" },
    { key: "done", labelKey: "dashboard.filters.done" },
  ];
  const [items, setItems] = useState<Chantier[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [filter, setFilter] = useState("all");
  const [q, setQ] = useState("");
  const [newModal, setNewModal] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const { isTablet } = useResponsive();
  const [newFirstName, setNewFirstName] = useState("");
  const [newLastName, setNewLastName] = useState("");
  const [newAddr, setNewAddr] = useState("");
  const [newPostal, setNewPostal] = useState("");
  const [newCity, setNewCity] = useState("");
  // 📞 (juin 2026) Coordonnées client — obligatoires à la création manuelle.
  //   Un scan CDC ultérieur peut écraser ces valeurs (auto-remplissage IA).
  const [newPhone, setNewPhone] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [newAppt, setNewAppt] = useState<string>(""); // raw datetime-local string e.g. "2026-06-25T14:30"
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [newNotes, setNewNotes] = useState("");
  const [creating, setCreating] = useState(false);
  const [pendingCount, setPendingCount] = useState(0);
  // 👥 RBAC Entreprise : sélecteur de Commercial à l'assignation
  const [teamMembers, setTeamMembers] = useState<
    { id: string; name: string; email: string; role: string }[]
  >([]);
  const [newAssignedTo, setNewAssignedTo] = useState<string>("");
  const [showAssigneePicker, setShowAssigneePicker] = useState(false);
  // En mode Entreprise (compte non-artisan), l'Admin DOIT choisir un
  // Commercial à la création. En mode Artisan / Solo : skip.
  const isArtisanAccount =
    (company?.account_type || "").toLowerCase() === "artisan";
  const mustAssignToCommercial = user?.role === "admin" && !isArtisanAccount;

  // 🚀 Onboarding "Premiers pas" — pour les nouveaux Admin Entreprise.
  // Affiche une carte avec 2 étapes : inviter commercial / technicien.
  // Masqué dès que l'utilisateur clique sur "Masquer".
  // Persistance via AsyncStorage clé `mc.onboarding.dismissed`.
  // ⚠️ Si l'admin a supprimé tous ses commerciaux/techniciens et que la
  // carte avait été masquée, on la ré-affiche automatiquement.
  const ONBOARDING_KEY = "mc.onboarding.dismissed";
  const [onboardingHidden, setOnboardingHidden] = useState(true);
  useEffect(() => {
    void (async () => {
      try {
        const v = await AsyncStorage.getItem(ONBOARDING_KEY);
        setOnboardingHidden(v === "1");
      } catch {
        setOnboardingHidden(false);
      }
    })();
  }, []);
  // Reset auto si l'admin perd ses commerciaux/techniciens
  useEffect(() => {
    if (user?.role !== "admin" || isArtisanAccount) return;
    const hasCommercial = teamMembers.some((m) => m.role === "commercial");
    const hasTech = teamMembers.some((m) => m.role === "technician");
    if (!hasCommercial || !hasTech) {
      // Force la réapparition de la carte d'onboarding
      setOnboardingHidden(false);
      AsyncStorage.removeItem(ONBOARDING_KEY).catch(() => {
        /* noop */
      });
    }
  }, [teamMembers, user?.role, isArtisanAccount]);
  const dismissOnboarding = async () => {
    setOnboardingHidden(true);
    try {
      await AsyncStorage.setItem(ONBOARDING_KEY, "1");
    } catch {
      /* noop */
    }
  };

  useEffect(() => {
    return subscribeQueueSize(setPendingCount);
  }, []);

  const canCreate = user?.role === "admin" || user?.role === "commercial";

  // 🔐 Outils internes plateforme (Campagne, LinkedIn, Testeurs) : visibles
  // UNIQUEMENT pour le propriétaire de MesureChâssis, jamais pour les
  // admins clients (confidentialité prospects + Apple Review).
  const PLATFORM_OWNER_EMAILS = [
    "info@mesurechassis.com",
    "artisan@mesurechassis.fr",
    "michelpezzuto@hotmail.com",
    "michelpezzuto@gmail.com",
  ];
  const isPlatformOwner =
    user?.role === "admin" &&
    !!user?.email &&
    PLATFORM_OWNER_EMAILS.includes(user.email.toLowerCase());

  // ☕ Priorité 4 — Bouton « Mes cafés » visible UNIQUEMENT si le compte est
  // issu d'un QR code de station partenaire (fetch silencieux au montage).
  const [hasCafeStation, setHasCafeStation] = useState(false);
  useEffect(() => {
    (async () => {
      try {
        const r = await api.get<{ station: { id: string } | null }>("/cafe/me");
        setHasCafeStation(!!r.data?.station);
      } catch {
        setHasCafeStation(false);
      }
    })();
  }, []);

  const fetchData = useCallback(async () => {
    try {
      const params: Record<string, string> = {};
      // Le filtre par stage est appliqué côté client (un stage = plusieurs
      // statuts internes). Seule la recherche texte est envoyée au backend.
      if (q.trim()) params.q = q.trim();
      const res = await api.get<Chantier[]>("/chantiers", { params });
      const all = res.data;
      // 🔒 RBAC dashboard : le Technicien NE VOIT PAS les chantiers encore
      // en phase commerciale (devis_a_faire, a_mesurer). Seuls les
      // commerciaux peuvent y accéder. Le tech ne reprend la main qu'à
      // partir de "technique_a_valider".
      const isTech = user?.role === "technician";
      const visibleAll = isTech
        ? all.filter(
            (c) => c.status !== "devis_a_faire" && c.status !== "a_mesurer",
          )
        : all;
      const filtered =
        filter === "all"
          ? visibleAll
          : visibleAll.filter(
              (c) => (statusMeta[c.status]?.stage ?? "verify") === filter,
            );
      setItems(filtered);
    } catch (e: any) {
      // 🍎 402 abonnement expiré → PaywallScreen (AuthContext) prend le relais.
      // 🔐 401 session expirée → déconnexion auto globale (onAuthExpired).
      // Dans les deux cas : aucune alerte générique par-dessus.
      const st = e?.response?.status;
      if (st !== 402 && st !== 401) {
        Alert.alert("Erreur", "Chargement impossible.");
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [filter, q, user?.role]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // 👥 Charge l'équipe (commerciaux disponibles) pour le sélecteur Admin
  const fetchTeam = useCallback(async () => {
    if (!mustAssignToCommercial) return;
    try {
      const res = await api.get<
        { id: string; name: string; email: string; role: string }[]
      >("/users");
      setTeamMembers(res.data || []);
    } catch (e) {
      // eslint-disable-next-line no-console
      console.warn("[Dashboard] fetchTeam failed:", e);
    }
  }, [mustAssignToCommercial]);

  useEffect(() => {
    fetchTeam();
  }, [fetchTeam]);

  // Refetch à chaque ouverture du modal — couvre le cas où un commercial
  // est créé après l'ouverture initiale du dashboard.
  useEffect(() => {
    if (newModal && mustAssignToCommercial) {
      fetchTeam();
    }
  }, [newModal, mustAssignToCommercial, fetchTeam]);

  useFocusEffect(
    useCallback(() => {
      // Refetch les chantiers + l'équipe à chaque retour sur le dashboard
      // (couvre le cas où l'utilisateur vient de créer un commercial ou un
      // technicien depuis l'écran /admin/team).
      fetchData();
      fetchTeam();
    }, [fetchData, fetchTeam])
  );

  const onRefresh = () => {
    setRefreshing(true);
    fetchData();
  };

  const createChantier = async () => {
    if (!newLastName.trim() || !newAddr.trim()) {
      Alert.alert("Champs requis", "Nom du client et adresse sont obligatoires.");
      return;
    }
    // 📞 (juin 2026) Téléphone + email désormais OBLIGATOIRES à la création manuelle.
    // Ils pourront être écrasés automatiquement plus tard par un scan CDC IA.
    if (!newPhone.trim() || !newEmail.trim()) {
      Alert.alert(
        "Coordonnées requises",
        "Le téléphone et l'email du client sont obligatoires. Ils pourront être mis à jour automatiquement plus tard si vous scannez un cahier des charges.",
      );
      return;
    }
    // Validation email basique
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(newEmail.trim())) {
      Alert.alert("Email invalide", "Merci de renseigner une adresse email valide (ex. jean.dupont@example.com).");
      return;
    }
    // 🔒 RBAC : Admin Entreprise DOIT assigner à un Commercial
    if (mustAssignToCommercial && !newAssignedTo) {
      Alert.alert(
        "Assignation requise",
        "Veuillez sélectionner un Commercial avant de créer le chantier.",
      );
      return;
    }
    setCreating(true);
    const payload: Record<string, any> = {
      first_name: newFirstName.trim() || undefined,
      last_name: newLastName.trim(),
      address: newAddr.trim(),
      postal_code: newPostal.trim() || undefined,
      city: newCity.trim() || undefined,
      client_phone: newPhone.trim(),
      client_email: newEmail.trim(),
      appointment_at: newAppt ? new Date(newAppt).toISOString() : undefined,
      notes: newNotes.trim() || undefined,
    };
    if (newAssignedTo) {
      payload.assigned_to = newAssignedTo;
    }
    const resetForm = () => {
      setNewModal(false);
      setNewFirstName("");
      setNewLastName("");
      setNewAddr("");
      setNewPostal("");
      setNewCity("");
      setNewPhone("");
      setNewEmail("");
      setNewAppt("");
      setNewNotes("");
      setNewAssignedTo("");
    };
    try {
      const res = await api.post<Chantier>("/chantiers", payload);
      resetForm();
      // 🔒 RBAC : l'Admin Entreprise = observateur. On revient au dashboard
      //    (avec liste rafraîchie) plutôt que d'ouvrir directement le chantier
      //    (qu'il ne peut de toute façon pas modifier). Le Commercial assigné
      //    prendra la main lui-même.
      if (mustAssignToCommercial) {
        fetchData(); // rafraîchit la liste pour voir le nouveau chantier
        return;
      }
      router.push(`/chantier/${res.data.id}`);
    } catch (e: any) {
      // Limite Freemium atteinte (anti-fraud lifetime)
      if (e?.response?.status === 402) {
        const detail = e?.response?.data?.detail;
        if (detail?.code === "free_plan_limit") {
          // 🍎 iOS App Store 3.1.1 — pas de CTA "Voir l'abonnement"
          // (ce qui mènerait à un écran de paiement). On donne juste
          // l'info — l'utilisateur peut souscrire depuis mesurechassis.com.
          const buttons: any[] =
            Platform.OS === "ios"
              ? [{ text: "OK", style: "cancel" }]
              : [
                  { text: "Plus tard", style: "cancel" },
                  {
                    text: "Voir l'abonnement",
                    onPress: () => router.push("/company-profile"),
                  },
                ];
          Alert.alert(
            "🔒 Limite Freemium atteinte",
            `${detail.message}\n\n(${detail.used}/${detail.limit} chantiers — la suppression ne réinitialise pas le compteur).` +
              (Platform.OS === "ios"
                ? "\n\nPour passer à un plan supérieur, rendez-vous sur mesurechassis.com."
                : ""),
            buttons,
          );
          setCreating(false);
          return;
        }
      }
      if (isNetworkError(e)) {
        // Hors-ligne : on stocke le chantier en file d'attente locale.
        await enqueueChantier(payload);
        resetForm();
        await fetchData();
        Alert.alert(
          "📥 Hors-ligne",
          "Chantier enregistré localement. Il sera synchronisé automatiquement dès le retour de la connexion.",
        );
      } else {
        Alert.alert("Erreur", "Création impossible.");
      }
    } finally {
      setCreating(false);
    }
  };

  const logout = async () => {
    await signOut();
    router.replace("/");
  };

  const renderItem = ({ item }: { item: Chantier }) => {
    const meta = statusMeta[item.status] ?? {
      label: item.status,
      color: "#fff",
      bg: "#333",
      stage: "verify" as const,
    };
    // Libellé contextuel selon le type de compte (Artisan = terminologie solo)
    const statusLabel = getStatusLabelI18n(item.status, company?.account_type, t);
    const isDone = meta.stage === "done";
    return (
      <TouchableOpacity
        testID={`project-card-${item.id}`}
        onPress={() => router.push(`/chantier/${item.id}`)}
        activeOpacity={0.7}
        style={styles.card}
      >
        <View style={styles.cardHeader}>
          <View style={{ flex: 1 }}>
            <Text style={styles.cardTitle} numberOfLines={1}>
              {item.client_name}
            </Text>
            <Text style={styles.cardAddr} numberOfLines={1}>
              <Ionicons name="location-outline" size={12} color={colors.textSecondary} />{" "}
              {item.address}
            </Text>
          </View>
          <Ionicons name="chevron-forward" size={20} color={colors.textSecondary} />
        </View>
        <View style={styles.badgeRow}>
          <View style={[styles.badge, { backgroundColor: meta.bg }]}>
            <View style={[styles.badgeDot, { backgroundColor: meta.color }]} />
            <Text style={[styles.badgeText, { color: meta.color }]}>{statusLabel}</Text>
          </View>
          {isDone && (
            <View style={[styles.badge, styles.exportReadyBadge]}>
              <Ionicons name="checkmark-circle" size={12} color={READY_FOR_EXPORT_BADGE.color} />
              <Text style={[styles.badgeText, { color: READY_FOR_EXPORT_BADGE.color, marginLeft: 4 }]}>
                Prêt pour Export
              </Text>
            </View>
          )}
        </View>
      </TouchableOpacity>
    );
  };

  return (
    <SafeAreaView style={styles.container} edges={["top", "bottom"]}>
      {/* ────── Rangée 1 : identité utilisateur ────── */}
      <View style={styles.topBar}>
        <View style={{ flex: 1 }}>
          <Text style={styles.welcome}>{t("dashboardExtended.hello")}</Text>
          <Text style={styles.userName} numberOfLines={1}>
            {user?.name}
          </Text>
          <View style={styles.roleChipsRow}>
            <View style={styles.roleChip}>
              <Ionicons
                name={
                  user?.role === "admin"
                    ? "shield-checkmark"
                    : user?.role === "commercial"
                      ? "briefcase"
                      : user?.role === "technician"
                        ? "construct"
                        : "person"
                }
                size={11}
                color={colors.primary}
              />
              <Text style={styles.roleChipText}>
                {t(`roles.${user?.role || "artisan"}`, { defaultValue: t("roles.artisan") })}
              </Text>
            </View>
            {user?.company_id && user.company_id !== "default" && (
              <Text style={styles.companyTag} numberOfLines={1}>
                · {user.company_id}
              </Text>
            )}
          </View>
        </View>
        <TouchableOpacity
          testID="logout-button"
          onPress={logout}
          style={styles.logoutBtn}
          activeOpacity={0.7}
        >
          <Ionicons name="log-out-outline" size={22} color={colors.textPrimary} />
        </TouchableOpacity>
      </View>

      {/* ────── Rangée 2 : actions ────── */}
      {/* Boutons en flex:1 pour occuper toute la largeur (pas de zone vide à
          gauche). Sur les comptes Artisan, le bouton "Équipe" est masqué et
          les 3 restants se redistribuent automatiquement. */}
      {/* Barre horizontale scrollable : évite les labels tronqués quand
          plusieurs boutons (Équipe/Stats/Campagne/Stations/Mes cafés…) */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={styles.actionsBarWrap}
        contentContainerStyle={styles.actionsBar}
      >
        {/* L'Équipe n'est dispo que pour les comptes Entreprise. Un Artisan
            solo n'a pas de sous-comptes à gérer. */}
        {user?.role === "admin" && company?.account_type !== "artisan" && (
          <TouchableOpacity
            testID="admin-team-button"
            onPress={() => router.push("/admin/team")}
            style={styles.actionBtn}
            activeOpacity={0.7}
          >
            <Ionicons name="people-outline" size={18} color={colors.primary} />
            <Text style={styles.actionBtnText} numberOfLines={1}>{t("dashboardExtended.team")}</Text>
          </TouchableOpacity>
        )}
        {user?.role === "admin" && (
          <TouchableOpacity
            testID="admin-stats-button"
            onPress={() => router.push("/admin/stats")}
            style={styles.actionBtn}
            activeOpacity={0.7}
          >
            <Ionicons name="stats-chart" size={18} color={colors.primary} />
            <Text style={styles.actionBtnText} numberOfLines={1}>{t("dashboardExtended.stats")}</Text>
          </TouchableOpacity>
        )}
        {/* Testeurs Google Play : outil de pré-lancement, géré depuis le web
            uniquement (l'admin copie les emails vers Play Console).
            🔐 Outil interne — visible UNIQUEMENT pour le propriétaire. */}
        {isPlatformOwner && Platform.OS === "web" && (
          <TouchableOpacity
            testID="admin-testers-button"
            onPress={() => router.push("/admin/testers" as never)}
            style={styles.actionBtn}
            activeOpacity={0.7}
          >
            <Ionicons name="flask-outline" size={18} color={colors.primary} />
            <Text style={styles.actionBtnText} numberOfLines={1}>Testeurs</Text>
          </TouchableOpacity>
        )}
        {/* 🚦 Validation équipe (Double-Phase) — Le gérant approuve/rejette
            les ouvriers rattachés à sa structure. Visible pour tous les admins. */}
        {user?.role === "admin" && (
          <TouchableOpacity
            testID="admin-team-validation-button"
            onPress={() =>
              router.push("/admin/team-validation" as never)
            }
            style={styles.actionBtn}
            activeOpacity={0.7}
          >
            <Ionicons
              name="shield-checkmark-outline"
              size={18}
              color={colors.primary}
            />
            <Text style={styles.actionBtnText} numberOfLines={1}>
              Validation équipe
            </Text>
          </TouchableOpacity>
        )}
        {/* Campagne emailing prospection — 🔐 outil interne, visible
            UNIQUEMENT pour le propriétaire de la plateforme. */}
        {isPlatformOwner && (
          <TouchableOpacity
            testID="admin-campagne-button"
            onPress={() => router.push("/admin/campagne" as never)}
            style={styles.actionBtn}
            activeOpacity={0.7}
          >
            <Ionicons name="megaphone-outline" size={18} color={colors.primary} />
            <Text style={styles.actionBtnText} numberOfLines={1}>Campagne</Text>
          </TouchableOpacity>
        )}
        {isPlatformOwner && (
          <TouchableOpacity
            testID="admin-linkedin-button"
            onPress={() => router.push("/admin/linkedin" as never)}
            style={styles.actionBtn}
            activeOpacity={0.7}
          >
            <Ionicons name="logo-linkedin" size={18} color={colors.primary} />
            <Text style={styles.actionBtnText} numberOfLines={1}>LinkedIn</Text>
          </TouchableOpacity>
        )}
        {/* ☕ Priorité 4 — Pilotage stations Jeton Café (propriétaire uniquement) */}
        {isPlatformOwner && (
          <TouchableOpacity
            testID="admin-stations-button"
            onPress={() => router.push("/admin/stations" as never)}
            style={styles.actionBtn}
            activeOpacity={0.7}
          >
            <Ionicons name="cafe-outline" size={18} color={colors.primary} />
            <Text style={styles.actionBtnText} numberOfLines={1}>Stations</Text>
          </TouchableOpacity>
        )}
        {/* ☕ Priorité 4 — Mes cafés (artisans tagués campagne station) */}
        {hasCafeStation && (
          <TouchableOpacity
            testID="mes-cafes-button"
            onPress={() => router.push("/mes-cafes" as never)}
            style={styles.actionBtn}
            activeOpacity={0.7}
          >
            <Ionicons name="cafe" size={18} color="#10B981" />
            <Text style={styles.actionBtnText} numberOfLines={1}>Mes cafés</Text>
          </TouchableOpacity>
        )}
        {/* Feedback — bouton unique pour tous les rôles (admin/commercial/technicien).
            Ouvre la page /feedback qui inclut un formulaire dépliable de
            nouveau message ET l'historique des retours (tous pour admin,
            personnels pour les autres rôles). */}
        <TouchableOpacity
          testID="feedback-button"
          onPress={() => router.push("/feedback")}
          style={styles.actionBtn}
          activeOpacity={0.7}
        >
          <Ionicons
            name="chatbubble-ellipses-outline"
            size={18}
            color={colors.primary}
          />
          <Text style={styles.actionBtnText} numberOfLines={1}>{t("dashboardExtended.feedback")}</Text>
        </TouchableOpacity>
        {user?.role === "admin" && (
          <TouchableOpacity
            testID="company-profile-button"
            onPress={() => router.push("/company-profile")}
            style={styles.actionBtn}
            activeOpacity={0.7}
          >
            <Ionicons name="settings-outline" size={18} color={colors.primary} />
            <Text style={styles.actionBtnText} numberOfLines={1}>{t("dashboardExtended.profileBtn")}</Text>
          </TouchableOpacity>
        )}
      </ScrollView>

      {/* 🆕 Build 9 — Incite le filleul à parrainer (disparaît dès 1er parrainage) */}
      <FilleulInviteBanner />

      <View style={styles.searchWrap}>
        <Ionicons name="search" size={18} color={colors.textSecondary} />
        <TextInput
          testID="search-input"
          value={q}
          onChangeText={setQ}
          placeholder={t("dashboard.search")}
          placeholderTextColor={colors.placeholder}
          style={styles.searchInput}
          returnKeyType="search"
          onSubmitEditing={fetchData}
        />
        {q.length > 0 && (
          <TouchableOpacity onPress={() => setQ("")}>
            <Ionicons name="close-circle" size={18} color={colors.textSecondary} />
          </TouchableOpacity>
        )}
      </View>

      <View style={styles.filterRow}>
        <FlatList
          horizontal
          data={FILTERS}
          showsHorizontalScrollIndicator={false}
          keyExtractor={(i) => i.key}
          contentContainerStyle={{ paddingHorizontal: 16, gap: 8 }}
          renderItem={({ item }) => (
            <TouchableOpacity
              testID={`filter-${item.key}`}
              onPress={() => setFilter(item.key)}
              style={[styles.chip, filter === item.key && styles.chipActive]}
              activeOpacity={0.7}
            >
              <Text style={[styles.chipText, filter === item.key && styles.chipTextActive]}>
                {t(item.labelKey)}
              </Text>
            </TouchableOpacity>
          )}
        />
      </View>

      {loading ? (
        <View style={[styles.flex, styles.center]}>
          <ActivityIndicator color={colors.primary} size="large" />
        </View>
      ) : (
        <>
          {/* 🚀 Carte "Premiers pas" — disparaît dès que commercial + technicien
             sont créés (la 3e étape "créer un chantier" est cosmétique). */}
          {user?.role === "admin" &&
            !isArtisanAccount &&
            !onboardingHidden &&
            !(
              teamMembers.some((m) => m.role === "commercial") &&
              teamMembers.some((m) => m.role === "technician")
            ) && (
              <View
                style={{
                  paddingHorizontal: 16,
                  paddingTop: 16,
                  maxWidth: isTablet ? 900 : "100%",
                  width: "100%",
                  alignSelf: "center",
                }}
              >
                <OnboardingCard
                  teamMembers={teamMembers}
                  hasChantier={items.length > 0}
                  onGoTeam={() => router.push("/admin/team")}
                  onNewChantier={() => setNewModal(true)}
                  onDismiss={dismissOnboarding}
                  t={t}
                />
              </View>
            )}
        <FlatList
          data={items}
          keyExtractor={(i) => i.id}
          renderItem={renderItem}
          contentContainerStyle={{
            padding: 16,
            paddingBottom: 120,
            maxWidth: isTablet ? 900 : "100%",
            width: "100%",
            alignSelf: "center",
          }}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={onRefresh}
              tintColor={colors.primary}
            />
          }
          ListHeaderComponent={null}
          ListEmptyComponent={
            <View style={styles.empty}>
              <Ionicons name="folder-open-outline" size={48} color={colors.borderStrong} />
              <Text style={styles.emptyText}>{t("dashboard.empty")}</Text>
              <Text style={styles.emptySub}>
                {isArtisanAccount
                  ? t("onboarding.soloHint")
                  : user?.role === "commercial"
                    ? t("onboarding.commercialHint")
                    : user?.role === "technician"
                      ? t("onboarding.techHint")
                      : t("dashboard.createFirst") + " ↓"}
              </Text>
            </View>
          }
        />
        </>
      )}

      <TouchableOpacity
        testID="new-chantier-button"
        onPress={() => setNewModal(true)}
        style={[
          styles.fab,
          (!canCreate ||
            // 🚀 Masque le FAB tant que l'onboarding (Admin Entreprise) n'est
            // pas finalisé : on force l'utilisateur à passer par la carte
            // « Premiers pas » pour bien comprendre les étapes.
            (user?.role === "admin" &&
              !isArtisanAccount &&
              !onboardingHidden &&
              !(
                teamMembers.some((m) => m.role === "commercial") &&
                teamMembers.some((m) => m.role === "technician")
              ))) && { display: "none" },
        ]}
        activeOpacity={0.85}
      >
        <Ionicons name="add" size={26} color="#000" />
        <Text style={styles.fabText}>{t("dashboardExtended.newProjectFab")}</Text>
      </TouchableOpacity>

      {pendingCount > 0 && (
        <TouchableOpacity
          testID="offline-queue-banner"
          onPress={() => syncQueue().then(() => fetchData())}
          activeOpacity={0.8}
          style={[styles.offlineBanner, !canCreate && { bottom: 24 }]}
        >
          <Ionicons name="cloud-upload" size={18} color="#000" />
          <Text style={styles.offlineText}>
            {pendingCount > 1
              ? t("dashboardExtended.pendingPlural", { count: pendingCount })
              : t("dashboardExtended.pendingSingular", { count: pendingCount })}
          </Text>
        </TouchableOpacity>
      )}

      <Modal visible={newModal} transparent animationType="fade" onRequestClose={() => setNewModal(false)}>
        <KeyboardAvoidingView
          behavior={Platform.OS === "ios" ? "padding" : "height"}
          style={styles.modalOverlay}
        >
          <View style={[styles.modalCard, { maxHeight: "92%" }]}>
            <Text style={styles.modalTitle}>{t("dashboardExtended.modal.title")}</Text>
            <Text style={styles.modalSub}>{t("dashboardExtended.modal.subtitle")}</Text>
            <ScrollView keyboardShouldPersistTaps="handled" style={{ marginTop: 6 }}>
              <View style={styles.row2}>
                <View style={styles.col2}>
                  <Text style={styles.label}>{t("dashboardExtended.modal.lastNameLabel")}</Text>
                  <TextInput
                    testID="new-lastname-input"
                    value={newLastName}
                    onChangeText={setNewLastName}
                    placeholder={t("dashboardExtended.modal.lastNamePlaceholder")}
                    placeholderTextColor={colors.placeholder}
                    style={[
                      styles.input,
                      // 🆕 V3 — validation visuelle stricte (cahier 10/06/2026)
                      !newLastName.trim() && { borderColor: "#ef4444", borderWidth: 1.5 },
                    ]}
                  />
                  {!newLastName.trim() && (
                    <Text style={{ color: "#ef4444", fontSize: 11, marginTop: 2 }}>
                      {t("dashboardExtended.modal.lastNameError")}
                    </Text>
                  )}
                </View>
                <View style={styles.col2}>
                  <Text style={styles.label}>{t("dashboardExtended.modal.firstNameLabel")}</Text>
                  <TextInput
                    testID="new-firstname-input"
                    value={newFirstName}
                    onChangeText={setNewFirstName}
                    placeholder={t("dashboardExtended.modal.firstNamePlaceholder")}
                    placeholderTextColor={colors.placeholder}
                    style={styles.input}
                  />
                </View>
              </View>

              <Text style={styles.label}>{t("dashboardExtended.modal.addressLabel")}</Text>
              <AddressAutocomplete
                testID="new-address-input"
                value={newAddr}
                onChangeText={setNewAddr}
                onSelect={(data) => {
                  // Auto-remplissage : si Photon nous donne CP + ville, on remplit
                  // les autres champs pour gagner du temps à l'utilisateur.
                  if (data.postalCode) setNewPostal(data.postalCode.slice(0, 5));
                  if (data.city) setNewCity(data.city);
                }}
                placeholder={t("dashboardExtended.modal.addressPlaceholder")}
                placeholderTextColor={colors.placeholder}
                style={[
                  styles.input,
                  !newAddr.trim() && { borderColor: "#ef4444", borderWidth: 1.5 },
                ]}
              />
              {!newAddr.trim() && (
                <Text style={{ color: "#ef4444", fontSize: 11, marginTop: 2 }}>
                  {t("dashboardExtended.modal.addressError")}
                </Text>
              )}

              <View style={styles.row2}>
                <View style={styles.col3}>
                  <Text style={styles.label}>{t("dashboardExtended.modal.postalLabel")}</Text>
                  <TextInput
                    testID="new-postal-input"
                    value={newPostal}
                    onChangeText={(v) => setNewPostal(v.replace(/[^0-9]/g, "").slice(0, 5))}
                    keyboardType="number-pad"
                    placeholder={t("dashboardExtended.modal.postalPlaceholder")}
                    placeholderTextColor={colors.placeholder}
                    style={styles.input}
                  />
                </View>
                <View style={styles.col7}>
                  <Text style={styles.label}>{t("dashboardExtended.modal.cityLabel")}</Text>
                  <TextInput
                    testID="new-city-input"
                    value={newCity}
                    onChangeText={setNewCity}
                    placeholder={t("dashboardExtended.modal.cityPlaceholder")}
                    placeholderTextColor={colors.placeholder}
                    style={styles.input}
                  />
                </View>
              </View>

              {/* 📞 (juin 2026) Coordonnées client — obligatoires à la création,
                  écrasées par scan CDC IA le cas échéant. */}
              <View style={styles.row2}>
                <View style={styles.col2}>
                  <Text style={styles.label}>Téléphone client *</Text>
                  <TextInput
                    testID="new-phone-input"
                    value={newPhone}
                    onChangeText={setNewPhone}
                    keyboardType="phone-pad"
                    placeholder="+32 496 65 00 32"
                    placeholderTextColor={colors.placeholder}
                    style={[
                      styles.input,
                      !newPhone.trim() && { borderColor: "#ef4444", borderWidth: 1.5 },
                    ]}
                  />
                  {!newPhone.trim() && (
                    <Text style={{ color: "#ef4444", fontSize: 11, marginTop: 2 }}>
                      Téléphone requis
                    </Text>
                  )}
                </View>
                <View style={styles.col2}>
                  <Text style={styles.label}>Email client *</Text>
                  <TextInput
                    testID="new-email-input"
                    value={newEmail}
                    onChangeText={setNewEmail}
                    keyboardType="email-address"
                    autoCapitalize="none"
                    placeholder="jean.dupont@example.com"
                    placeholderTextColor={colors.placeholder}
                    style={[
                      styles.input,
                      !newEmail.trim() && { borderColor: "#ef4444", borderWidth: 1.5 },
                    ]}
                  />
                  {!newEmail.trim() && (
                    <Text style={{ color: "#ef4444", fontSize: 11, marginTop: 2 }}>
                      Email requis
                    </Text>
                  )}
                </View>
              </View>
              <View style={{ flexDirection: "row", alignItems: "center", gap: 6, marginTop: 4, marginBottom: 4 }}>
                <Ionicons name="sparkles-outline" size={12} color={colors.textSecondary} />
                <Text style={{ color: colors.textSecondary, fontSize: 11, flex: 1 }}>
                  Si vous scannez un cahier des charges plus tard, les coordonnées seront mises à jour automatiquement.
                </Text>
              </View>

              <Text style={styles.label}>{t("dashboardExtended.modal.apptLabel")}</Text>
              <TouchableOpacity
                testID="new-appointment-picker"
                onPress={() => setShowDatePicker(true)}
                style={[styles.input, { justifyContent: "center", minHeight: 56 }]}
                activeOpacity={0.75}
              >
                <View style={{ flexDirection: "row", alignItems: "center", gap: 10 }}>
                  <Ionicons
                    name="calendar"
                    size={20}
                    color={newAppt ? colors.primary : colors.placeholder}
                  />
                  <Text
                    style={{
                      color: newAppt ? colors.textPrimary : colors.placeholder,
                      fontSize: 16,
                      fontWeight: newAppt ? "700" : "400",
                      flex: 1,
                    }}
                    numberOfLines={1}
                  >
                    {newAppt
                      ? new Date(newAppt).toLocaleString("fr-FR", {
                          weekday: "long",
                          day: "2-digit",
                          month: "short",
                          year: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        })
                      : t("dashboardExtended.modal.apptPlaceholder")}
                  </Text>
                  <Ionicons
                    name="chevron-forward"
                    size={18}
                    color={colors.textSecondary}
                  />
                </View>
              </TouchableOpacity>
              <AppointmentPicker
                visible={showDatePicker}
                value={newAppt || null}
                onClose={() => setShowDatePicker(false)}
                onConfirm={(iso) => setNewAppt(iso)}
                title={t("dashboardExtended.modal.apptLabel")}
              />

              <Text style={styles.label}>{t("dashboardExtended.modal.notesLabel")}</Text>
              <TextInput
                testID="new-notes-input"
                value={newNotes}
                onChangeText={setNewNotes}
                placeholder={t("dashboardExtended.modal.notesPlaceholder")}
                placeholderTextColor={colors.placeholder}
                multiline
                numberOfLines={3}
                style={[styles.input, { minHeight: 80, textAlignVertical: "top", paddingTop: 12 }]}
              />
              <View style={styles.dictationHint}>
                <Ionicons name="mic-outline" size={14} color={colors.textSecondary} />
                <Text style={styles.dictationHintText}>
                  {t("dashboardExtended.modal.dictationHint")}
                </Text>
              </View>
              {mustAssignToCommercial && (
                <View style={{ marginTop: 16 }}>
                  <Text style={styles.label}>
                    {t("dashboardExtended.modal.assignLabel")}
                  </Text>
                  <TouchableOpacity
                    onPress={() => setShowAssigneePicker(true)}
                    style={[
                      styles.input,
                      {
                        flexDirection: "row",
                        alignItems: "center",
                        justifyContent: "space-between",
                      },
                    ]}
                    activeOpacity={0.75}
                  >
                    <Text
                      style={{
                        color: newAssignedTo
                          ? colors.textPrimary
                          : colors.placeholder,
                        flex: 1,
                      }}
                      numberOfLines={1}
                    >
                      {newAssignedTo
                        ? teamMembers.find((m) => m.id === newAssignedTo)?.name ||
                          t("dashboardExtended.modal.assignSelected")
                        : t("dashboardExtended.modal.assignPlaceholder")}
                    </Text>
                    <Ionicons
                      name="chevron-down"
                      size={18}
                      color={colors.textSecondary}
                    />
                  </TouchableOpacity>
                  <Text
                    style={{
                      color: colors.textSecondary,
                      fontSize: 11,
                      marginTop: 6,
                    }}
                  >
                    {t("dashboardExtended.modal.assignHelper")}
                  </Text>
                </View>
              )}
            </ScrollView>
            <View style={styles.modalActions}>
              <TouchableOpacity
                onPress={() => setNewModal(false)}
                style={[styles.modalBtn, styles.modalBtnSecondary]}
                activeOpacity={0.7}
              >
                <Text style={styles.modalBtnSecondaryText}>{t("dashboardExtended.modal.cancel")}</Text>
              </TouchableOpacity>
              <TouchableOpacity
                testID="new-chantier-submit"
                onPress={createChantier}
                disabled={creating}
                style={[styles.modalBtn, styles.modalBtnPrimary]}
                activeOpacity={0.85}
              >
                {creating ? (
                  <ActivityIndicator color="#000" />
                ) : (
                  <Text style={styles.modalBtnPrimaryText}>{t("dashboardExtended.modal.create")}</Text>
                )}
              </TouchableOpacity>
            </View>
          </View>
        </KeyboardAvoidingView>
      </Modal>

      {/* ────── Picker Commercial (assignation à la création) ────── */}
      <Modal
        visible={showAssigneePicker}
        transparent
        animationType="fade"
        onRequestClose={() => setShowAssigneePicker(false)}
      >
        <View
          style={{
            flex: 1,
            backgroundColor: "rgba(0,0,0,0.6)",
            justifyContent: "center",
            alignItems: "center",
            padding: 20,
          }}
        >
          <View
            style={{
              backgroundColor: colors.card,
              borderRadius: 14,
              padding: 18,
              width: "100%",
              maxWidth: 420,
              maxHeight: "70%",
            }}
          >
            <Text
              style={{
                color: colors.textPrimary,
                fontSize: 17,
                fontWeight: "800",
                marginBottom: 14,
              }}
            >
              {t("dashboardExtended.assignPicker.title")}
            </Text>
            <ScrollView style={{ maxHeight: 360 }}>
              {(() => {
                const commercials = teamMembers.filter(
                  (m) => (m.role || "").toLowerCase() === "commercial",
                );
                if (__DEV__) {
                  // eslint-disable-next-line no-console
                  console.log("[Picker] teamMembers:", teamMembers.length, "commercials:", commercials.length, teamMembers.map(m => ({n: m.name, r: m.role})));
                }
                if (commercials.length === 0) {
                  return (
                    <View style={{ padding: 18, alignItems: "center" }}>
                      <Ionicons
                        name="people-outline"
                        size={36}
                        color={colors.textSecondary}
                      />
                      <Text
                        style={{
                          color: colors.textSecondary,
                          textAlign: "center",
                          marginTop: 10,
                        }}
                      >
                        {t("dashboardExtended.assignPicker.empty")}
                      </Text>
                    </View>
                  );
                }
                return commercials.map((m) => {
                  const selected = newAssignedTo === m.id;
                  return (
                    <TouchableOpacity
                      key={m.id}
                      onPress={() => {
                        setNewAssignedTo(m.id);
                        setShowAssigneePicker(false);
                      }}
                      style={{
                        padding: 14,
                        borderRadius: 10,
                        borderWidth: 1,
                        borderColor: selected
                          ? colors.primary
                          : colors.border,
                        backgroundColor: selected
                          ? colors.primary + "1A"
                          : "transparent",
                        marginBottom: 8,
                        flexDirection: "row",
                        alignItems: "center",
                        gap: 12,
                      }}
                      activeOpacity={0.7}
                    >
                      <Ionicons
                        name={
                          selected
                            ? "radio-button-on"
                            : "radio-button-off"
                        }
                        size={20}
                        color={
                          selected ? colors.primary : colors.textSecondary
                        }
                      />
                      <View style={{ flex: 1 }}>
                        <Text
                          style={{
                            color: colors.textPrimary,
                            fontWeight: "700",
                            fontSize: 14,
                          }}
                        >
                          {m.name}
                        </Text>
                        <Text
                          style={{
                            color: colors.textSecondary,
                            fontSize: 12,
                            marginTop: 2,
                          }}
                        >
                          {m.email}
                        </Text>
                      </View>
                    </TouchableOpacity>
                  );
                });
              })()}
            </ScrollView>
            <TouchableOpacity
              onPress={() => setShowAssigneePicker(false)}
              style={{
                marginTop: 10,
                padding: 12,
                borderRadius: 8,
                backgroundColor: colors.border,
                alignItems: "center",
              }}
            >
              <Text style={{ color: colors.textPrimary, fontWeight: "700" }}>
                Fermer
              </Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

      {/* ────── FAB Aide (flottant en bas, couleur flashy bleue) ────── */}
      <TouchableOpacity
        testID="help-fab"
        onPress={() => setHelpOpen(true)}
        activeOpacity={0.85}
        style={styles.helpFab}
        hitSlop={8}
      >
        <Ionicons name="help-circle" size={26} color="#FFFFFF" />
        <Text style={styles.helpFabText}>{t("dashboardExtended.help")}</Text>
      </TouchableOpacity>

      {/* Centre d'aide / FAQ */}
      <ChatHelp
        visible={helpOpen}
        onClose={() => setHelpOpen(false)}
        onContactSupport={() => router.push("/company-profile")}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  flex: { flex: 1 },
  center: { alignItems: "center", justifyContent: "center" },
  // FAB Aide — bouton flottant flashy (bleu cyan) en bas à droite
  // Positionné au-dessus du bouton "+ Nouveau chantier" pour ne pas
  // cacher le texte des cartes (offset 90px).
  helpFab: {
    position: "absolute",
    right: 16,
    bottom: 96,
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    backgroundColor: "#3B82F6",
    borderRadius: 30,
    paddingHorizontal: 16,
    paddingVertical: 11,
    elevation: 8,
    shadowColor: "#3B82F6",
    shadowOpacity: 0.5,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 4 },
    borderWidth: 2,
    borderColor: "#60A5FA",
    zIndex: 50,
  },
  helpFabText: {
    color: "#FFFFFF",
    fontWeight: "900",
    letterSpacing: 1.1,
    fontSize: 12,
  },
  topBar: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 20,
    paddingTop: 8,
    paddingBottom: 14,
  },
  welcome: { color: colors.textSecondary, fontSize: 13, letterSpacing: 0.5 },
  userName: { color: colors.textPrimary, fontSize: 22, fontWeight: "900", marginTop: 2 },
  companyTag: {
    color: colors.primary,
    fontSize: 11,
    fontWeight: "700",
    letterSpacing: 1,
    textTransform: "uppercase",
    marginTop: 2,
  },
  logoutBtn: {
    marginLeft: "auto",
    width: 48,
    height: 48,
    borderRadius: 8,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    alignItems: "center",
    justifyContent: "center",
  },
  roleChipsRow: {
    flexDirection: "row",
    alignItems: "center",
    flexWrap: "wrap",
    marginTop: 6,
    gap: 6,
  },
  roleChip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 999,
    backgroundColor: "rgba(255, 107, 26, 0.10)",
    borderWidth: 1,
    borderColor: "rgba(255, 107, 26, 0.35)",
  },
  roleChipText: {
    color: colors.primary,
    fontSize: 10,
    fontWeight: "800",
    letterSpacing: 0.4,
  },
  actionsBarWrap: {
    flexGrow: 0,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSubtle,
  },
  actionsBar: {
    flexDirection: "row",
    alignItems: "stretch",
    gap: 6,
    paddingHorizontal: 16,
    paddingBottom: 10,
  },
  actionBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 4,
    paddingHorizontal: 6,
    paddingVertical: 8,
    borderRadius: 8,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    minHeight: 40,
  },
  actionBtnText: {
    color: colors.textPrimary,
    fontSize: 11,
    fontWeight: "700",
    letterSpacing: 0.3,
    flexShrink: 1,
  },
  searchWrap: {
    marginHorizontal: 16,
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    backgroundColor: colors.surface,
    borderColor: colors.borderSubtle,
    borderWidth: 1,
    borderRadius: 10,
    paddingHorizontal: 14,
    minHeight: 56,
  },
  searchInput: { flex: 1, color: colors.textPrimary, fontSize: 16, paddingVertical: 8 },
  filterRow: { marginTop: 14, marginBottom: 4 },
  chip: {
    paddingHorizontal: 16,
    minHeight: 40,
    borderRadius: 100,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    alignItems: "center",
    justifyContent: "center",
  },
  chipActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  chipText: {
    color: colors.textSecondary,
    fontWeight: "700",
    fontSize: 12,
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  chipTextActive: { color: "#000" },
  card: {
    backgroundColor: colors.surface,
    borderColor: colors.borderSubtle,
    borderWidth: 1,
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
  },
  cardHeader: { flexDirection: "row", alignItems: "center", marginBottom: 10 },
  cardTitle: { color: colors.textPrimary, fontSize: 17, fontWeight: "800", marginBottom: 4 },
  cardAddr: { color: colors.textSecondary, fontSize: 13 },
  badge: {
    flexDirection: "row",
    alignItems: "center",
    alignSelf: "flex-start",
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 4,
    gap: 6,
  },
  badgeDot: { width: 6, height: 6, borderRadius: 3 },
  badgeText: {
    fontSize: 10,
    fontWeight: "800",
    textTransform: "uppercase",
    letterSpacing: 0.8,
  },
  badgeRow: { flexDirection: "row", flexWrap: "wrap", gap: 6, marginTop: 4 },
  exportReadyBadge: {
    backgroundColor: "#0e3315",
    borderWidth: 1,
    borderColor: "#32D74B",
    flexDirection: "row",
    alignItems: "center",
  },
  empty: { alignItems: "center", padding: 60, gap: 8 },
  emptyText: { color: colors.textPrimary, fontWeight: "800", fontSize: 16 },
  emptySub: { color: colors.textSecondary, fontSize: 13, textAlign: "center", paddingHorizontal: 20 },
  fab: {
    position: "absolute",
    bottom: 24,
    left: 16,
    right: 16,
    minHeight: 64,
    backgroundColor: colors.primary,
    borderRadius: 8,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    shadowColor: colors.primary,
    shadowOpacity: 0.4,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 },
    elevation: 8,
  },
  fabText: { color: "#000", fontWeight: "900", fontSize: 16, letterSpacing: 1.2 },
  offlineBanner: {
    position: "absolute",
    bottom: 100,
    left: 16,
    right: 16,
    backgroundColor: colors.warning,
    borderRadius: 8,
    paddingHorizontal: 14,
    minHeight: 48,
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  offlineText: { color: "#000", fontWeight: "800", fontSize: 13, flex: 1 },
  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.8)",
    justifyContent: "center",
    padding: 20,
  },
  modalCard: {
    backgroundColor: colors.surface,
    borderColor: colors.borderSubtle,
    borderWidth: 1,
    borderRadius: 12,
    padding: 22,
  },
  modalTitle: {
    color: colors.textPrimary,
    fontWeight: "900",
    fontSize: 18,
    letterSpacing: 1,
    marginBottom: 4,
  },
  modalSub: { color: colors.textSecondary, fontSize: 12, marginBottom: 8 },
  row2: { flexDirection: "row", gap: 10 },
  col2: { flex: 1 },
  col3: { flex: 3 },
  col7: { flex: 7 },
  dictationHint: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    marginTop: 8,
    paddingHorizontal: 4,
  },
  dictationHintText: {
    color: colors.textSecondary,
    fontSize: 12,
    fontStyle: "italic",
    flex: 1,
    lineHeight: 16,
  },
  label: {
    color: colors.textSecondary,
    fontSize: 11,
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: 1.2,
    marginTop: 10,
    marginBottom: 6,
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
  },
  modalActions: { flexDirection: "row", marginTop: 20, gap: 10 },
  modalBtn: { flex: 1, minHeight: 56, alignItems: "center", justifyContent: "center", borderRadius: 8 },
  modalBtnSecondary: { borderWidth: 2, borderColor: colors.borderStrong },
  modalBtnSecondaryText: { color: colors.textPrimary, fontWeight: "700", textTransform: "uppercase" },
  modalBtnPrimary: { backgroundColor: colors.primary },
  modalBtnPrimaryText: { color: "#000", fontWeight: "900", textTransform: "uppercase", letterSpacing: 0.8 },
});
