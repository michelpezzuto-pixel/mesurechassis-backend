import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  Image,
  KeyboardAvoidingView,
  Linking,
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
import { useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import * as ImagePicker from "expo-image-picker";
import { api, buildAuthHeaders, PDF_URL, JSON_URL, XLSX_URL, CSV_URL, ERP_CSV_URL, ERP_XML_URL } from "@/src/services/api";
import { useResponsive } from "@/src/utils/responsive";
import { ShapeIcon, blockTypeToShape } from "@/src/components/ShapeIcon";
import AppointmentPicker from "@/src/components/AppointmentPicker";
import { useAuth } from "@/src/context/AuthContext";
import { colors, statusMeta, getStatusLabel, getStatusLabelI18n, blockMeta, shapeMeta } from "@/src/theme";
import { useTranslation } from "react-i18next";

type SitePhoto = { uri: string; caption: string };

type Chantier = {
  id: string;
  client_name: string;
  first_name?: string | null;
  last_name?: string | null;
  address: string;
  postal_code?: string | null;
  city?: string | null;
  appointment_at?: string | null;
  status: string;
  assigned_to?: string | null;
  created_by?: string | null;
  created_at: string;
  site_photos?: SitePhoto[];
  wall_config?: { masonry_type?: string };
};

type Mesure = {
  id: string;
  block_type: string;
  label: string;
  photo_url?: string;
  alerts?: string[];
  slope_angle_deg?: number | null;
};

type UserOpt = { id: string; name: string; email: string; role: string };

export default function ChantierDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { t, i18n } = useTranslation();
  const router = useRouter();
  const { user, hasRole, artisanMode, company } = useAuth();
  // 🆕 V3 — Responsive (cahier 10/06/2026 Phase 5). DOIT être appelé
  //    EN TÊTE du composant car les hooks doivent toujours être appelés
  //    dans le même ordre, indépendamment des early-returns.
  const { width: screenWidth, isTablet } = useResponsive();
  const numColumns = screenWidth >= 1100 ? 3 : screenWidth >= 768 ? 2 : 1;
  // 🔒 HARDCODED ROLE GATES (NE PAS passer par `hasRole` qui peut être
  // bypassé par `artisan_mode=true` dans la DB).
  // Ces booléens reflètent STRICTEMENT le rôle réel de l'utilisateur connecté.
  const roleIsAdmin = user?.role === "admin";
  const roleIsCommercial = user?.role === "commercial";
  const roleIsTechnician = user?.role === "technician";
  // 🔒 Seul l'admin (le patron) peut affecter un chantier à un commercial /
  //    technicien. Le Commercial NE peut pas réassigner. (Règle métier
  //    explicite : "Il n'y a que le patron qui peut affecter les chantiers
  //    aux commerciaux. C'est tout.")
  //    Exception : en mode Artisan/Solo, l'admin = tous les rôles, donc OK.
  const canManage = roleIsAdmin;
  // `canMeasure` est défini plus bas après `isSoloArtisan` car en Mode
  // Artisan Solo (1 seul user) ou Mode Artisan activé, l'admin doit pouvoir
  // mesurer comme un technicien.
  const canExportTech = roleIsTechnician || roleIsAdmin;
  // 🚧 BETA GRATUITE : pas de plan Free tant que beta_mode est actif.
  const isFreePlan = !company?.beta_mode && (company?.plan ?? "trial") === "free";
  const showUpgradeLock = () => {
    // 🍎 iOS App Store 3.1.1 — pas de CTA "Voir l'abonnement" (écran de paiement).
    const buttons: any[] =
      Platform.OS === "ios"
        ? [{ text: t("common.ok"), style: "cancel" }]
        : [
            { text: t("chantierDetail.upgradeLock.later"), style: "cancel" },
            {
              text: t("chantierDetail.upgradeLock.viewSubscription"),
              onPress: () => router.push("/company-profile"),
            },
          ];
    Alert.alert(
      t("chantierDetail.upgradeLock.title"),
      t("chantierDetail.upgradeLock.msgBase") +
        (Platform.OS === "ios"
          ? t("chantierDetail.upgradeLock.msgIosSuffix")
          : ""),
      buttons,
    );
  };
  const [chantier, setChantier] = useState<Chantier | null>(null);
  const [mesures, setMesures] = useState<Mesure[]>([]);
  const [users, setUsers] = useState<UserOpt[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [assignOpen, setAssignOpen] = useState(false);
  // 🆕 V3 — Modale "Demande de modification au technicien" (remplace
  //    Alert.prompt qui n'est pas universel — KO sur Android & web).
  const [modRequestOpen, setModRequestOpen] = useState(false);
  const [modRequestReason, setModRequestReason] = useState("");
  const [modRequestSubmitting, setModRequestSubmitting] = useState(false);
  const [exporting, setExporting] = useState<string | null>(null);
  // ✏️ Édition des infos du chantier (Admin/Commercial avant fabrication)
  const [editOpen, setEditOpen] = useState(false);
  const [editFirstName, setEditFirstName] = useState("");
  const [editLastName, setEditLastName] = useState("");
  const [editAddress, setEditAddress] = useState("");
  const [editPostal, setEditPostal] = useState("");
  const [editCity, setEditCity] = useState("");
  const [editAppointment, setEditAppointment] = useState<Date | null>(null);
  const [editApptPickerOpen, setEditApptPickerOpen] = useState(false);
  const [savingEdit, setSavingEdit] = useState(false);
  // Override technicien en mode fabrication (déverrouille temporairement)
  const [techOverride, setTechOverride] = useState(false);
  const [validating, setValidating] = useState(false);
  const isArchived = chantier?.status === "cloture" || chantier?.status === "termine";
  const isInFabrication = chantier?.status === "en_fabrication";
  const isAwaitingValidation =
    chantier?.status === "a_verifier" ||
    chantier?.status === "technique_a_valider";
  // Team size — solo artisan si exactement 1 utilisateur (le master admin)
  // ⚠️ On considère "non chargé" tant que `users` est vide afin d'éviter de
  // basculer transitoirement en mode "solo" pendant le fetch initial (ce qui
  // ferait apparaître le bouton vert à l'admin avant la liste des membres).
  const usersLoaded = users.length > 0;
  const teamSize = users.length;
  const isSoloArtisan = usersLoaded && teamSize === 1;
  // 📐 Qui peut PRENDRE / MODIFIER des mesures ?
  //  - Commercial & Technicien : toujours (sur chantiers non-fab)
  //  - Admin : UNIQUEMENT en compte Artisan (compte solo par design)
  //    ou en Mode Artisan activé. En compte Entreprise — même si
  //    l'Admin est seul (équipe pas encore invitée) — il NE PEUT
  //    PAS prendre de mesures. Son rôle : créer le chantier et le
  //    transmettre au Commercial / Technicien.
  const isArtisanAccount =
    (company?.account_type || "").toLowerCase() === "artisan";
  const adminCanMeasure = roleIsAdmin && (isArtisanAccount || artisanMode);
  const canMeasure = roleIsCommercial || roleIsTechnician || adminCanMeasure;
  // 🔒 Qui peut valider le passage en fabrication ?
  // - Mode Solo (teamSize=1) : admin ou technicien
  // - Mode Équipe : SEUL le technicien (jamais commercial, jamais admin)
  // - Mode Artisan/Solo : le bouton vert est MASQUÉ. L'artisan utilise
  //   uniquement le bouton CLÔTURER en bas (qui passe par closure.tsx et
  //   redirige automatiquement vers le dashboard). On évite ainsi le doublon
  //   trompeur "bouton vert" + "bouton CLÔTURER".
  // - Tant que `users` n'est pas chargé : pas de bouton (sécurité)
  const canValidateForFab =
    usersLoaded &&
    isAwaitingValidation &&
    !isSoloArtisan &&
    !isArtisanAccount &&
    !artisanMode &&
    roleIsTechnician;
  // Message d'attente : tout le monde sauf le technicien en mode équipe.
  const isWaitingForTech =
    usersLoaded && isAwaitingValidation && !isSoloArtisan && !roleIsTechnician;
  // 🔒 Verrou spécifique COMMERCIAL au statut "À vérifier par le technicien"
  //    Une fois validé, le Commercial n'a plus que la possibilité de
  //    revenir en arrière (downgrade à "a_mesurer") pour corriger.
  //    Il ne peut PLUS modifier/ajouter/supprimer une ouverture ni la
  //    structure du mur. Le Technicien prend la main.
  const isCommercialInVerify =
    !isSoloArtisan && roleIsCommercial && isAwaitingValidation;

  // Verrou fabrication : commercial = read-only strict
  // Tech peut déverrouiller via override exceptionnel
  // Admin (sauf solo) = également read-only
  // 🔒 Chantier TERMINÉ (cloture/livre) = verrou ABSOLU pour tous les rôles
  //    (sauf consultation PDF/CSV/XLSX/JSON qui restent ouverts).
  const canEditMesures = (() => {
    if (isArchived) return false; // Terminé/Clôturé = verrou total
    if (isCommercialInVerify) return false; // Commercial verrouillé après validation
    if (isInFabrication) {
      if (isSoloArtisan && roleIsAdmin) return true;
      return roleIsTechnician && techOverride;
    }
    if (!canMeasure) return false;
    return true;
  })();

  // 🔒 Interception pour chantier TERMINÉ — popup pédagogique
  //    Le verrou s'applique à TOUS les rôles (commercial, tech, admin).
  //    Les exports (PDF, CSV, XLSX, JSON) restent 100% disponibles.
  const showArchivedLockIntercept = isArchived;
  const interceptArchivedLock = () => {
    Alert.alert(
      t("chantierDetail.archivedLock.alertTitle"),
      t("chantierDetail.archivedLock.alertMsg"),
      [{ text: t("chantierDetail.archivedLock.got"), style: "default" }]
    );
  };

  // Verrouillage Fabrication / Terminé pour Commercial : on AFFICHE les
  // boutons (Modifier, exports avancés) mais on intercepte le clic avec
  // un Alert pédagogique. Le mode Solo Artisan bypass tout.
  const showCommercialFabIntercept =
    !isSoloArtisan &&
    roleIsCommercial &&
    isInFabrication;

  // ---- DIAGNOSTIC LOGGING ----------------------------------------------
  // Permet de diagnostiquer rapidement les états en console développeur.
  useEffect(() => {
    if (!chantier || !user) return;
    // eslint-disable-next-line no-console
    console.log("[CHANTIER GATE]", {
      role: user.role,
      teamSize,
      isSoloArtisan,
      status: chantier.status,
      isInFabrication,
      isArchived,
      artisanMode,
      canEditMesures,
      showCommercialFabIntercept,
      canDeleteChantier: undefined, // set below
    });
  }, [
    chantier?.status,
    user?.role,
    teamSize,
    isInFabrication,
    isArchived,
    artisanMode,
    canEditMesures,
    showCommercialFabIntercept,
  ]);

  /**
   * Affiche l'Alert pédagogique pour les actions verrouillées en
   * fabrication / terminé du côté Commercial.
   */
  const interceptCommercialFab = () => {
    Alert.alert(
      t("chantierDetail.commercialFabBlock.title"),
      t("chantierDetail.commercialFabBlock.msg"),
      [{ text: t("chantierDetail.archivedLock.got"), style: "default" }]
    );
  };

  // 🗑️ Trash can (suppression chantier) :
  //   - Status `en_fabrication` OU `cloture/termine` :
  //       → MASQUÉ pour TOUS en mode équipe (Commercial + Technicien + Admin).
  //       → En mode Solo : seul le master Admin peut supprimer.
  //   - Autres statuts (nouveau / a_verifier / technique_a_valider) :
  //       → Admin ou Commercial peuvent supprimer (canManage).
  const canDeleteChantier = (() => {
    if (isInFabrication || isArchived) {
      return isSoloArtisan && roleIsAdmin;
    }
    return canManage;
  })();
  const creatorName = (() => {
    if (!chantier) return "";
    const u = users.find((x) => x.id === chantier.created_by);
    return u?.name || t("common.unknownUser", { defaultValue: "Opérateur inconnu" });
  })();

  const fetchAll = useCallback(async () => {
    try {
      const [c, m, u] = await Promise.all([
        api.get<Chantier>(`/chantiers/${id}`),
        api.get<Mesure[]>(`/chantiers/${id}/mesures`),
        api.get<UserOpt[]>("/users"),
      ]);
      setChantier(c.data);
      setMesures(m.data);
      setUsers(u.data);
    } catch {
      Alert.alert(t("chantierDetail.errors.title"), t("chantierDetail.errors.loadFail"));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [id]);

  useFocusEffect(
    useCallback(() => {
      fetchAll();
    }, [fetchAll])
  );

  const assignTo = async (userId: string | null) => {
    try {
      const res = await api.patch<Chantier>(`/chantiers/${id}`, { assigned_to: userId });
      setChantier(res.data);
      setAssignOpen(false);
    } catch {
      Alert.alert(t("chantierDetail.errors.title"), t("chantierDetail.errors.assignFail"));
    }
  };

  // 📤 Bouton ADMIN "Envoyer à un commercial" (statut devis_a_faire) :
  // affecte le chantier au commercial choisi ET passe le statut à "a_mesurer"
  // en une seule action. Si plusieurs commerciaux dans l'équipe → modale
  // picker (sendToCommercialOpen). Si un seul → confirmation rapide.
  const [sendToCommercialOpen, setSendToCommercialOpen] = useState(false);
  const sendToCommercial = async (commercialUserId: string) => {
    try {
      const res = await api.patch<Chantier>(`/chantiers/${id}`, {
        assigned_to: commercialUserId,
        status: "a_mesurer",
      });
      setChantier(res.data);
      setSendToCommercialOpen(false);
      Alert.alert(
        t("chantierDetail.sendToCommercial.successTitle"),
        t("chantierDetail.sendToCommercial.successMsg"),
        [{ text: t("common.ok"), onPress: () => router.replace("/dashboard") }],
      );
    } catch {
      Alert.alert(t("chantierDetail.errors.title"), t("chantierDetail.errors.sendFail"));
    }
  };
  const handleSendToCommercialClick = () => {
    const commercials = users.filter((u) => u.role === "commercial");
    if (commercials.length === 0) {
      Alert.alert(
        t("chantierDetail.sendToCommercial.noneTitle"),
        t("chantierDetail.sendToCommercial.noneMsg"),
      );
      return;
    }
    if (commercials.length === 1) {
      const c = commercials[0];
      Alert.alert(
        t("chantierDetail.sendToCommercial.confirmTitle"),
        t("chantierDetail.sendToCommercial.confirmMsg", { name: c.name }),
        [
          { text: t("common.cancel"), style: "cancel" },
          {
            text: t("chantierDetail.sendToCommercial.send"),
            style: "default",
            onPress: () => sendToCommercial(c.id),
          },
        ],
      );
      return;
    }
    // Plusieurs commerciaux : ouvrir le picker
    setSendToCommercialOpen(true);
  };

  // ✏️ Édition des infos chantier (adresse, code postal, ville, RDV, client)
  // — pré-remplit les inputs depuis l'état actuel et ouvre la modale.
  const openEdit = () => {
    if (!chantier) return;
    setEditFirstName(chantier.first_name || "");
    setEditLastName(chantier.last_name || "");
    setEditAddress(chantier.address || "");
    setEditPostal(chantier.postal_code || "");
    setEditCity(chantier.city || "");
    setEditAppointment(
      chantier.appointment_at ? new Date(chantier.appointment_at) : null,
    );
    setEditOpen(true);
  };
  const saveEdit = async () => {
    if (!chantier) return;
    if (savingEdit) return;
    setSavingEdit(true);
    try {
      const payload: any = {
        first_name: editFirstName.trim() || null,
        last_name: editLastName.trim() || null,
        address: editAddress.trim(),
        postal_code: editPostal.trim() || null,
        city: editCity.trim() || null,
        appointment_at: editAppointment
          ? editAppointment.toISOString()
          : null,
      };
      // Reconstruction de client_name à partir du prénom + nom si modifiés
      const parts = [editLastName, editFirstName].filter(Boolean).map((p) => p.trim());
      if (parts.length) payload.client_name = parts.join(" ");
      const res = await api.patch<Chantier>(`/chantiers/${id}`, payload);
      setChantier(res.data);
      setEditOpen(false);
    } catch (e: any) {
      const reason =
        e?.response?.status === 403
          ? t("chantierDetail.errors.editForbidden")
          : t("chantierDetail.errors.editFail");
      Alert.alert(t("chantierDetail.errors.title"), reason);
    } finally {
      setSavingEdit(false);
    }
  };

  const handleDelete = () => {
    if (!chantier) return;
    // Sécurité côté UI : si chantier archivé (Terminé/Livré), seul l'admin
    // peut supprimer. Solo Artisan / artisan_mode bypassent tout.
    if (
      isArchived &&
      !isSoloArtisan &&
      !artisanMode &&
      user?.role !== "admin"
    ) {
      Alert.alert(
        t("chantierDetail.deleteBlocked.title"),
        t("chantierDetail.deleteBlocked.msg"),
        [{ text: t("chantierDetail.archivedLock.got"), style: "default" }]
      );
      return;
    }
    const msg = t("chantierDetail.deleteConfirm.msg", { name: chantier.client_name });
    const doDelete = async () => {
      try {
        await api.delete(`/chantiers/${id}`);
        router.replace("/dashboard");
      } catch (e: any) {
        const reason =
          e?.response?.status === 403
            ? t("chantierDetail.errors.deleteForbidden")
            : t("chantierDetail.errors.deleteFail");
        Alert.alert(t("chantierDetail.errors.title"), reason);
      }
    };
    if (Platform.OS === "web") {
      const ok =
        typeof window !== "undefined" &&
        window.confirm(`${t("chantierDetail.deleteConfirm.title")}\n\n${msg}`);
      if (ok) doDelete();
      return;
    }
    Alert.alert(
      t("chantierDetail.deleteConfirm.title"),
      msg,
      [
        { text: t("common.cancel"), style: "cancel" },
        { text: t("chantierDetail.deleteConfirm.delete"), style: "destructive", onPress: doDelete },
      ]
    );
  };

  // -------- Site photos anti-litige ---------------------------------------
  const addSitePhoto = async (source: "camera" | "library") => {
    if (!chantier) return;
    const current = chantier.site_photos ?? [];
    if (current.length >= 6) {
      Alert.alert(t("chantierDetail.photoLimit.title"), t("chantierDetail.photoLimit.msg"));
      return;
    }
    try {
      const fn = source === "camera"
        ? ImagePicker.requestCameraPermissionsAsync
        : ImagePicker.requestMediaLibraryPermissionsAsync;
      const perm = await fn();
      if (!perm.granted) {
        Alert.alert(t("chantierDetail.permission.denied"), t("chantierDetail.permission.deniedMsg"));
        return;
      }
      const launcher = source === "camera"
        ? ImagePicker.launchCameraAsync
        : ImagePicker.launchImageLibraryAsync;
      const res = await launcher({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        quality: 0.5,
        base64: true,
      });
      if (res.canceled || !res.assets[0]) return;
      const a = res.assets[0];
      const uri = a.base64 ? `data:image/jpeg;base64,${a.base64}` : a.uri;
      const next = [...current, { uri, caption: "" }];
      const r = await api.patch<Chantier>(`/chantiers/${chantier.id}`, { site_photos: next });
      setChantier(r.data);
    } catch {
      Alert.alert(t("chantierDetail.errors.title"), t("chantierDetail.errors.photoAddFail"));
    }
  };

  const updateSitePhotoCaption = async (idx: number, caption: string) => {
    if (!chantier) return;
    const next = (chantier.site_photos ?? []).map((p, i) => i === idx ? { ...p, caption } : p);
    setChantier({ ...chantier, site_photos: next });
  };

  const persistSitePhotoCaption = async () => {
    if (!chantier) return;
    try {
      await api.patch(`/chantiers/${chantier.id}`, { site_photos: chantier.site_photos ?? [] });
    } catch { /* swallow */ }
  };

  const removeSitePhoto = (idx: number) => {
    if (!chantier) return;
    Alert.alert(t("chantierDetail.deletePhoto.title"), t("chantierDetail.deletePhoto.msg"), [
      { text: t("common.cancel"), style: "cancel" },
      {
        text: t("chantierDetail.sitePhotos.delete"),
        style: "destructive",
        onPress: async () => {
          const next = (chantier.site_photos ?? []).filter((_, i) => i !== idx);
          try {
            const r = await api.patch<Chantier>(`/chantiers/${chantier.id}`, { site_photos: next });
            setChantier(r.data);
          } catch {
            Alert.alert(t("chantierDetail.errors.title"), t("chantierDetail.errors.deleteFail"));
          }
        },
      },
    ]);
  };

  // -------- Exports --------------------------------------------------------

  /**
   * Fallback iOS / Mobile Safari : ouvre le client Mail natif via `mailto:`
   * avec le contenu CSV/JSON en pièce-jointe textuelle (body).
   *
   * Pourquoi ?
   *  - Sur Expo Go iOS, `Sharing.shareAsync` sur du `text/csv` ouvre parfois
   *    QuickLook plein écran sans bouton retour (limitation iOS).
   *  - Sur Mobile Safari (preview web), l'attribut `<a download>` n'est pas
   *    respecté → Safari rend le CSV en table HTML plein écran.
   *  - Ce fallback garantit que l'utilisateur ne reste JAMAIS bloqué.
   *
   * NB : `mailto:` a une limite de body (~2KB iOS, ~5KB Android). On tronque
   * proprement si nécessaire en indiquant à l'utilisateur que le fichier
   * complet est disponible côté Web.
   */
  const offerEmailFallback = (
    kind: "csv" | "json",
    content: string,
    clientName: string
  ) => {
    const MAX_BODY = 1500; // marge de sécurité sous la limite mailto: iOS
    const truncated =
      content.length > MAX_BODY
        ? content.slice(0, MAX_BODY) + t("chantierDetail.emailFallback.truncated")
        : content;
    const subject = `${t("chantierDetail.emailFallback.subjectPrefix")} ${kind.toUpperCase()} — ${clientName}`;
    const adminEmail = user?.email || ""; // pré-remplit avec l'email du master admin connecté

    Alert.alert(
      t("chantierDetail.emailFallback.title", { kind: kind.toUpperCase() }),
      t("chantierDetail.emailFallback.msg", { kind: kind.toUpperCase() }),
      [
        { text: t("common.cancel"), style: "cancel" },
        {
          text: t("chantierDetail.emailFallback.send"),
          onPress: async () => {
            const mailtoUrl = `mailto:${adminEmail}?subject=${encodeURIComponent(
              subject
            )}&body=${encodeURIComponent(truncated)}`;
            try {
              const supported = await Linking.canOpenURL(mailtoUrl);
              if (!supported) {
                Alert.alert(
                  t("chantierDetail.emailFallback.noMailTitle"),
                  t("chantierDetail.emailFallback.noMailMsg")
                );
                return;
              }
              await Linking.openURL(mailtoUrl);
            } catch (e: any) {
              Alert.alert(t("chantierDetail.errors.title"), e?.message || t("chantierDetail.errors.mailFail"));
            }
          },
        },
      ]
    );
  };

  /** Détecte iOS Safari (Mobile Safari sur la preview Web). */
  const isIOSMobileSafari = (): boolean => {
    if (Platform.OS !== "web") return false;
    if (typeof navigator === "undefined") return false;
    const ua = navigator.userAgent || "";
    return /iPad|iPhone|iPod/.test(ua) && !/CriOS|FxiOS|EdgiOS/.test(ua);
  };

  const downloadExport = async (
    kind: "pdf" | "xlsx" | "csv" | "json" | "erp-csv" | "erp-xml",
  ) => {
    if (!chantier) return;
    if (isFreePlan) {
      showUpgradeLock();
      return;
    }
    const urlMap: Record<string, (cid: string) => string> = {
      pdf: PDF_URL,
      xlsx: XLSX_URL,
      csv: CSV_URL,
      json: JSON_URL,
      // 🆕 V3 — Exports ERP universels (CSV BOM UTF-8 + XML structuré)
      "erp-csv": ERP_CSV_URL,
      "erp-xml": ERP_XML_URL,
    };
    const url = urlMap[kind](chantier.id);
    setExporting(kind);
    try {
      const headers = await buildAuthHeaders();
      if (Platform.OS === "web") {
        // Authenticated blob download via fetch
        const r = await fetch(url, { headers });
        if (r.status === 402) {
          throw new Error("FREE_PLAN_LOCK");
        }
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const safe = (chantier.client_name || chantier.id).replace(/[^a-z0-9_-]+/gi, "_");

        // 🍏 iOS Mobile Safari ignore l'attribut `<a download>` et navigue
        // directement vers le blob, ce qui affiche le CSV en plein écran sous
        // forme de table HTML (bug remonté par l'utilisateur). On bascule donc
        // sur le fallback `mailto:` immédiatement pour CSV/JSON sur cette
        // plateforme uniquement.
        if (isIOSMobileSafari() && (kind === "csv" || kind === "json")) {
          const text = await r.text();
          offerEmailFallback(kind, text, safe);
          return;
        }

        const blob = await r.blob();
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        // 🆕 V3 — Mapping extension pour les exports ERP (csv/xml)
        const fileExt =
          kind === "erp-csv" ? "csv" :
          kind === "erp-xml" ? "xml" :
          kind;
        const filePrefix =
          kind === "erp-csv" || kind === "erp-xml" ? "ERP" : "MesureChassis";
        a.download = `${filePrefix}_${safe}.${fileExt}`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        setTimeout(() => URL.revokeObjectURL(a.href), 0);
      } else {
        // Native: open in system viewer / share
        // 🐛 FIX iOS Expo Go SDK 54 — `expo-file-system/legacy` peut planter
        // au runtime avec "TurboModuleProxy: Cannot read property 'get' of
        // undefined" sur certaines configurations Expo Go (modules natifs
        // non liés). On entoure TOUTE l'opération dans un mega try/catch qui
        // bascule vers le fallback `mailto:` (CSV/JSON) ou une Alert
        // explicite (PDF/XLSX) si le natif crashe.
        const safe = (chantier.client_name || chantier.id).replace(/[^a-z0-9_-]+/gi, "_");
        let textContent: string | null = null;

        // 1) D'abord on récupère le contenu (HTTP) pour pouvoir fallback
        //    AVANT même de toucher au natif iOS.
        const r = await fetch(url, { headers });
        if (r.status === 402) throw new Error("FREE_PLAN_LOCK");
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        if (kind === "csv" || kind === "json") {
          textContent = await r.text();
        }

        // 🍏 Sur iOS Expo Go, le partage natif de CSV/JSON via Sharing
        // peut soit échouer silencieusement, soit ouvrir une feuille de
        // partage où aucune app ne sait gérer le format. Pour CSV/JSON
        // on bascule DIRECTEMENT sur le fallback `mailto:` (plus fiable).
        if (
          Platform.OS === "ios" &&
          (kind === "csv" || kind === "json") &&
          textContent != null
        ) {
          offerEmailFallback(kind, textContent, safe);
          return;
        }

        // 2) Tentative native (download + share). Si ÇA PLANTE → fallback.
        try {
          const FileSystem = await import("expo-file-system/legacy");
          const Sharing = await import("expo-sharing");
          const cacheDir = FileSystem.cacheDirectory;
          if (!cacheDir) throw new Error("FS_UNAVAILABLE");
          const fileUri = `${cacheDir}MesureChassis_${safe}.${kind}`;

          const mime =
            kind === "pdf"
              ? "application/pdf"
              : kind === "xlsx"
                ? "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                : kind === "csv"
                  ? "text/csv"
                  : "application/json";
          const uti =
            kind === "pdf"
              ? "com.adobe.pdf"
              : kind === "csv"
                ? "public.comma-separated-values-text"
                : kind === "json"
                  ? "public.json"
                  : "org.openxmlformats.spreadsheetml.sheet";

          let finalUri: string;
          if (textContent != null) {
            await FileSystem.writeAsStringAsync(fileUri, textContent, {
              encoding: FileSystem.EncodingType.UTF8,
            });
            finalUri = fileUri;
          } else {
            const dl = await FileSystem.downloadAsync(url, fileUri, {
              headers: headers as any,
            });
            if (dl.status === 402) throw new Error("FREE_PLAN_LOCK");
            if (dl.status && dl.status >= 400) throw new Error(`HTTP ${dl.status}`);
            finalUri = dl.uri;
          }

          const info = await FileSystem.getInfoAsync(finalUri);
          if (!info.exists) throw new Error("FILE_NOT_FOUND");

          const isAvailable = await Sharing.isAvailableAsync();
          if (!isAvailable) {
            if (textContent != null) {
              offerEmailFallback(kind as "csv" | "json", textContent, safe);
            } else {
              Alert.alert(t("chantierDetail.exports.downloadOK"), t("chantierDetail.exports.fileSaved", { uri: finalUri }));
            }
            return;
          }
          await Sharing.shareAsync(finalUri, {
            dialogTitle: `Export ${kind.toUpperCase()}`,
            mimeType: mime,
            UTI: uti,
          });
        } catch (nativeErr: any) {
          // Crash natif (TurboModuleProxy ou autre) → fallback gracieux
          console.warn("[export native] fallback:", nativeErr?.message || nativeErr);
          if ((kind === "csv" || kind === "json") && textContent != null) {
            offerEmailFallback(kind, textContent, safe);
          } else {
            // PDF / XLSX : on ne peut pas embarquer un binaire dans un mailto.
            // On propose à l'utilisateur d'utiliser la version web.
            Alert.alert(
              t("chantierDetail.exports.expoGoUnavailableTitle"),
              t("chantierDetail.exports.expoGoUnavailableMsg", { kind: kind.toUpperCase() }),
              [{ text: t("common.ok") }]
            );
          }
        }
      }
    } catch (e: any) {
      if (e?.message === "FREE_PLAN_LOCK") {
        showUpgradeLock();
      } else {
        Alert.alert(t("chantierDetail.exports.errorTitle"), e?.message || t("chantierDetail.errors.exportFail"));
      }
    } finally {
      setExporting(null);
    }
  };

  const assignedUser = chantier?.assigned_to
    ? users.find((u) => u.id === chantier.assigned_to)
    : null;

  /**
   * Valide le chantier et le fait passer en fabrication.
   * - Solo Artisan : l'admin peut le faire directement.
   * - Mode équipe : seul le technicien peut valider (l'admin ne bypass PAS).
   */
  const validateForFabrication = async () => {
    if (!chantier) return;
    setValidating(true);
    try {
      const r = await api.patch<Chantier>(`/chantiers/${chantier.id}`, {
        status: "en_fabrication",
      });
      setChantier(r.data);
      Alert.alert(
        t("chantierDetail.validation.validatedTitle"),
        t("chantierDetail.validation.validatedMsg"),
        [
          {
            text: t("common.ok"),
            onPress: () => router.replace("/dashboard"),
          },
        ],
      );
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      Alert.alert(
        t("chantierDetail.errors.title"),
        typeof detail === "string"
          ? detail
          : t("chantierDetail.errors.validateFail")
      );
    } finally {
      setValidating(false);
    }
  };

  /**
   * Active le mode override technicien : déverrouille temporairement
   * l'édition des mesures sur un chantier déjà en fabrication.
   */
  const requestTechOverride = () => {
    Alert.alert(
      t("chantierDetail.techOverride.alertTitle"),
      t("chantierDetail.techOverride.alertMsg"),
      [
        { text: t("common.cancel"), style: "cancel" },
        {
          text: t("chantierDetail.techOverride.unlock"),
          style: "destructive",
          onPress: () => setTechOverride(true),
        },
      ]
    );
  };

  const meta = chantier ? statusMeta[chantier.status] : null;

  if (loading || !chantier) {
    return (
      <View style={[styles.flex, styles.center]}>
        <ActivityIndicator color={colors.primary} size="large" />
      </View>
    );
  }

  // 🆕 V3 — `numColumns` est calculé en haut du composant (cf. useResponsive).

  return (
    <SafeAreaView style={styles.flex} edges={["bottom"]}>
      <FlatList
        // `key` force le remount quand on change de breakpoint (RN
        // n'autorise pas de changer numColumns à chaud sans key).
        key={`mesures-grid-${numColumns}`}
        data={mesures}
        keyExtractor={(i) => i.id}
        numColumns={numColumns}
        columnWrapperStyle={
          numColumns > 1 ? { gap: 8, paddingHorizontal: 8 } : undefined
        }
        contentContainerStyle={[
          { padding: 16, paddingBottom: 200 },
          isTablet ? { maxWidth: 1200, alignSelf: "center", width: "100%" } : null,
        ]}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => {
              setRefreshing(true);
              fetchAll();
            }}
            tintColor={colors.primary}
          />
        }
        ListHeaderComponent={
          <View>
            <View style={styles.header}>
              <View style={styles.headerTopRow}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.clientName}>{chantier.client_name}</Text>
                  <View style={styles.addressRow}>
                    <Ionicons name="location" size={14} color={colors.textSecondary} />
                    <Text style={styles.address}>{chantier.address}</Text>
                  </View>
                </View>
                {/* ✏️ Édition des infos chantier (Admin/Commercial sauf
                    archivé/fabrication). Le Commercial verrouillé en
                    technique_a_valider doit d'abord revenir à "À mesurer"
                    pour éditer (passe par isCommercialInVerify). */}
                {canManage && !isArchived && !isInFabrication && !isCommercialInVerify && (
                  <TouchableOpacity
                    testID="edit-chantier-button"
                    onPress={openEdit}
                    style={styles.deleteIconBtn}
                    activeOpacity={0.7}
                    hitSlop={{ top: 8, left: 8, right: 8, bottom: 8 }}
                  >
                    <Ionicons name="create-outline" size={20} color={colors.primary} />
                  </TouchableOpacity>
                )}
                {canDeleteChantier && (
                  <TouchableOpacity
                    testID="delete-chantier-button"
                    onPress={handleDelete}
                    style={styles.deleteIconBtn}
                    activeOpacity={0.7}
                    hitSlop={{ top: 8, left: 8, right: 8, bottom: 8 }}
                  >
                    <Ionicons name="trash-outline" size={20} color={colors.anomaly} />
                  </TouchableOpacity>
                )}
              </View>
              {meta && (
                <View style={[styles.badge, { backgroundColor: meta.bg }]}>
                  <View style={[styles.badgeDot, { backgroundColor: meta.color }]} />
                  <Text style={[styles.badgeText, { color: meta.color }]}>
                    {getStatusLabelI18n(chantier.status, company?.account_type, t)}
                  </Text>
                </View>
              )}

              {/* 🚫 En mode Artisan (solo) il n'y a personne à qui affecter
                  le chantier (l'artisan joue tous les rôles). On masque
                  entièrement la zone d'affectation pour éviter la confusion. */}
              {!isSoloArtisan && !isArtisanAccount && !artisanMode && (
                canManage && !assignedUser ? (
                  // 🚨 Pas encore d'affectation : CTA bien visible pour l'admin
                  <TouchableOpacity
                    testID="assign-button"
                    onPress={() => setAssignOpen(true)}
                    style={styles.assignCta}
                    activeOpacity={0.85}
                  >
                    <Ionicons name="person-add" size={18} color={colors.primary} />
                    <Text style={styles.assignCtaText}>
                      {t("chantierDetail.assign.cta")}
                    </Text>
                    <Ionicons
                      name="chevron-forward"
                      size={18}
                      color={colors.primary}
                    />
                  </TouchableOpacity>
                ) : (
                <TouchableOpacity
                  testID="assign-button"
                  onPress={() => canManage && setAssignOpen(true)}
                  disabled={!canManage}
                  style={[styles.assignRow, !canManage && { opacity: 0.6 }]}
                  activeOpacity={0.7}
                >
                  <Ionicons
                    name="person-circle"
                    size={20}
                    color={colors.primary}
                  />
                  <View style={{ flex: 1 }}>
                    <Text style={styles.assignLabel}>{t("chantierDetail.assign.to")}</Text>
                    <Text style={styles.assignValue}>
                      {assignedUser ? assignedUser.name : t("chantierDetail.assign.none")}
                    </Text>
                  </View>
                  {canManage && (
                    <View style={styles.assignChangePill}>
                      <Ionicons
                        name="swap-horizontal"
                        size={14}
                        color={colors.primary}
                      />
                      <Text style={styles.assignChangeText}>{t("chantierDetail.assign.reassign")}</Text>
                    </View>
                  )}
                </TouchableOpacity>
                )
              )}
            </View>

            <View style={styles.statsRow}>
              <View style={styles.statCard}>
                <Text style={styles.statValue}>{mesures.length}</Text>
                <Text style={styles.statLabel}>{t("chantierDetail.kpi.openings")}</Text>
              </View>
              <View style={styles.statCard}>
                <Text style={styles.statValue}>
                  {mesures.reduce((acc, m) => acc + (m.alerts?.length ?? 0), 0)}
                </Text>
                <Text style={styles.statLabel}>{t("chantierDetail.kpi.alerts")}</Text>
              </View>
            </View>

            <Text style={styles.sectionTitle}>{t("chantierDetail.kpi.openingsSection")}</Text>
          </View>
        }
        renderItem={({ item, index }) => {
          const block = blockMeta[item.block_type] ?? { label: item.block_type, icon: "square-outline" };
          // Récupère la forme précise (porte_garage vs porte_entree, etc.)
          // depuis options.shape pour afficher le bon label + icône.
          const trueShape = blockTypeToShape(item.block_type, item.options);
          const trueLabel = shapeMeta[trueShape]?.label ?? block.label;
          // 🆕 V3 — Miniature dans la liste compacte (cahier juin 2026) :
          //   Priorité 1 : photo prise au moment de la mesure (item.photo_url)
          //   Priorité 2 : 1ère photo "site anti-litige" du chantier (fallback)
          //   Priorité 3 : schéma SVG par forme (fallback final)
          const sitePhotoUri =
            (chantier?.site_photos ?? []).find((p) => p?.uri)?.uri ?? null;
          const thumbUri = item.photo_url || sitePhotoUri;
          // 👁️ La carte est cliquable PARTOUT (Admin en consultation, Commercial
          // en édition, Tech en vérification). Le mode dépend du rôle / statut.
          //   - canEditMesures = true  → on ouvre en édition
          //   - sinon              → on ouvre en lecture seule (mode ?view=1)
          const handleCardPress = () => {
            if (showArchivedLockIntercept) {
              interceptArchivedLock();
              return;
            }
            if (showCommercialFabIntercept) {
              interceptCommercialFab();
              return;
            }
            if (canEditMesures) {
              // Édition : on ouvre le wizard avec mesure_id pour pré-remplir
              router.push(
                `/chantier/${id}/new-mesure?mesure_id=${item.id}`,
              );
            } else {
              // Lecture seule : page de consultation dédiée
              router.push(`/chantier/${id}/mesure/${item.id}`);
            }
          };
          return (
            <TouchableOpacity
              testID={`mesure-card-${item.id}`}
              style={[
                styles.mesureCard,
                // 🆕 V3 — En mode grille (tablette), chaque carte prend
                // une part égale de la rangée pour un alignement propre.
                numColumns > 1 && { flex: 1 / numColumns },
              ]}
              onPress={handleCardPress}
              activeOpacity={0.75}
            >
              <View style={styles.mesureRow}>
                {thumbUri ? (
                  <Image source={{ uri: thumbUri }} style={styles.mesureThumb} />
                ) : (
                  <View style={styles.mesureThumbPlaceholder}>
                    <ShapeIcon
                      shape={trueShape}
                      size={28}
                      color={colors.textPrimary}
                      strokeWidth={1.8}
                    />
                  </View>
                )}
                <View style={{ flex: 1, minWidth: 0 }}>
                  <View style={{ flexDirection: "row", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
                    <Text style={styles.mesureLabel} numberOfLines={1}>
                      #{index + 1} · {item.label}
                    </Text>
                    {/* 🆕 Import CDC — Badge "À valider" si mesure importée par IA non encore confirmée sur place */}
                    {item.options?.imported_from_spec && !item.options?.validated_on_site && (
                      <View style={styles.importBadgeToValidate}>
                        <Ionicons name="sparkles" size={10} color="#FF9F0A" />
                        <Text style={styles.importBadgeToValidateText}>À VALIDER</Text>
                      </View>
                    )}
                    {/* 🆕 Import CDC — Cercle vert "V" si mesure validée sur place */}
                    {item.options?.validated_on_site && (
                      <View style={styles.validatedCircle}>
                        <Ionicons name="checkmark" size={11} color="#FFFFFF" />
                      </View>
                    )}
                  </View>
                  <Text style={styles.mesureType} numberOfLines={1}>
                    {trueLabel}
                    {item.slope_angle_deg != null ? `  ·  ${item.slope_angle_deg}°` : ""}
                  </Text>
                </View>
                {/* 🆕 V3 — Action de suppression sous forme d'icône discrète
                    intégrée à la carte (plus de bouton textuel lourd).
                    Le tap sur la carte déclenche l'édition. */}
                {(canEditMesures || showCommercialFabIntercept || showArchivedLockIntercept) && (
                  <TouchableOpacity
                    testID={`delete-mesure-${item.id}`}
                    onPress={(e) => {
                      e.stopPropagation?.();
                      if (showArchivedLockIntercept) {
                        interceptArchivedLock();
                        return;
                      }
                      if (showCommercialFabIntercept) {
                        interceptCommercialFab();
                        return;
                      }
                      Alert.alert(
                        t("chantierDetail.deleteMesure.title"),
                        t("chantierDetail.deleteMesure.msg", { label: item.label }),
                        [
                          { text: t("common.cancel"), style: "cancel" },
                          {
                            text: t("chantierDetail.deleteConfirm.delete"),
                            style: "destructive",
                            onPress: async () => {
                              try {
                                await api.delete(`/mesures/${item.id}`);
                                fetchAll();
                              } catch {
                                Alert.alert(t("chantierDetail.errors.title"), t("chantierDetail.errors.deleteFail"));
                              }
                            },
                          },
                          ]
                        );
                    }}
                    hitSlop={{ top: 10, left: 10, right: 10, bottom: 10 }}
                    style={styles.mesureTrashIcon}
                    activeOpacity={0.6}
                  >
                    <Ionicons name="trash-outline" size={18} color={colors.anomaly} />
                  </TouchableOpacity>
                )}
              </View>
              {item.alerts && item.alerts.length > 0 && (
                <View style={styles.alertWrap}>
                  {item.alerts.map((a, i) => (
                    <Text key={i} style={styles.alertText} numberOfLines={2}>
                      {a}
                    </Text>
                  ))}
                </View>
              )}
              {isArchived && (
                <View style={styles.archiveRow}>
                  <Ionicons name="lock-closed" size={12} color={colors.textSecondary} />
                  <Text style={styles.archiveText}>{t("chantierDetail.archivedLock.cardReadonly")}</Text>
                </View>
              )}
            </TouchableOpacity>
          );
        }}
        ListEmptyComponent={
          <View style={styles.empty}>
            <Ionicons name="grid-outline" size={48} color={colors.borderStrong} />
            <Text style={styles.emptyText}>{t("chantierDetail.empty.title")}</Text>
            {canEditMesures ? (
              <>
                <Text style={styles.emptyHint}>
                  {t("chantierDetail.empty.hint")}
                </Text>
                {/* 🆕 Build 11 — Import cahier des charges via IA (PDF/Excel/Photo) */}
                <TouchableOpacity
                  testID="import-spec-cta"
                  onPress={() => router.push(`/chantier/${id}/import-spec`)}
                  activeOpacity={0.85}
                  style={styles.importCta}
                >
                  <Ionicons name="sparkles" size={18} color="#000" />
                  <Text style={styles.importCtaText}>
                    {t("chantierDetail.importCdc.cta")}
                  </Text>
                </TouchableOpacity>
                <Text style={styles.importCtaSub}>
                  {t("chantierDetail.importCdc.sub")}
                </Text>
              </>
            ) : showArchivedLockIntercept ? (
              <Text style={styles.emptyHint}>
                {t("chantierDetail.empty.hintArchived")}
              </Text>
            ) : showCommercialFabIntercept ? (
              <Text style={styles.emptyHint}>
                {t("chantierDetail.empty.hintFab")}
              </Text>
            ) : null}
          </View>
        }
        ListFooterComponent={
          <View>
            {/* === Site photos anti-litige === */}
            <View style={styles.exportCard}>
              <View style={styles.exportHeader}>
                <Ionicons name="camera" size={18} color={colors.warning} />
                <Text style={styles.exportTitle}>{t("chantierDetail.sitePhotos.title")}</Text>
              </View>
              <Text style={styles.exportSub}>
                {t("chantierDetail.sitePhotos.sub", { count: chantier.site_photos?.length ?? 0 })}
              </Text>
              {(chantier.site_photos ?? []).map((p, idx) => (
                <View key={idx} style={photoStyles.row}>
                  <Image source={{ uri: p.uri }} style={photoStyles.thumb} />
                  <View style={photoStyles.captionWrap}>
                    <TextInput
                      testID={`site-photo-caption-${idx}`}
                      value={p.caption}
                      onChangeText={(v) => updateSitePhotoCaption(idx, v)}
                      onBlur={persistSitePhotoCaption}
                      placeholder={t("chantierDetail.sitePhotos.captionPlaceholder")}
                      placeholderTextColor={colors.placeholder}
                      style={photoStyles.captionInput}
                    />
                    <TouchableOpacity
                      testID={`site-photo-delete-${idx}`}
                      onPress={() => removeSitePhoto(idx)}
                      activeOpacity={0.7}
                      style={photoStyles.delBtn}
                    >
                      <Ionicons name="trash-outline" size={14} color={colors.anomaly} />
                      <Text style={photoStyles.delBtnText}>{t("chantierDetail.sitePhotos.delete")}</Text>
                    </TouchableOpacity>
                  </View>
                </View>
              ))}
              {(chantier.site_photos?.length ?? 0) < 6 && (
                <View style={photoStyles.addRow}>
                  <TouchableOpacity
                    testID="add-site-photo-camera"
                    onPress={() => addSitePhoto("camera")}
                    activeOpacity={0.7}
                    style={photoStyles.addBtn}
                  >
                    <Ionicons name="camera" size={18} color={colors.primary} />
                    <Text style={photoStyles.addBtnText}>{t("chantierDetail.sitePhotos.camera")}</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    testID="add-site-photo-library"
                    onPress={() => addSitePhoto("library")}
                    activeOpacity={0.7}
                    style={photoStyles.addBtn}
                  >
                    <Ionicons name="images" size={18} color={colors.primary} />
                    <Text style={photoStyles.addBtnText}>{t("chantierDetail.sitePhotos.gallery")}</Text>
                  </TouchableOpacity>
                </View>
              )}
            </View>

            {/* ============ VALIDATION & FABRICATION GATE ============ */}
            {isAwaitingValidation && canValidateForFab && (
              <TouchableOpacity
                testID="validate-for-fabrication-button"
                onPress={validateForFabrication}
                disabled={validating}
                activeOpacity={0.85}
                style={validateStyles.btnGo}
              >
                {validating ? (
                  <ActivityIndicator color="#000" />
                ) : (
                  <>
                    <Ionicons name="checkmark-done-circle" size={22} color="#000" />
                    <Text style={validateStyles.btnGoText}>
                      {isSoloArtisan
                        ? t("chantierDetail.validation.validatePublish")
                        : t("chantierDetail.validation.validateClose")}
                    </Text>
                  </>
                )}
              </TouchableOpacity>
            )}
            {isWaitingForTech && (
              <View style={validateStyles.waitCard}>
                <Ionicons name="hourglass-outline" size={20} color={colors.warning} />
                <View style={{ flex: 1 }}>
                  <Text style={validateStyles.waitTitle}>
                    {t("chantierDetail.validation.waitingTitle")}
                  </Text>
                  <Text style={validateStyles.waitBody}>
                    {t("chantierDetail.validation.waitingBody")}
                  </Text>
                </View>
              </View>
            )}
            {/* ↩️ Bouton "Renvoyer au commercial" pour le Technicien.
                 Permet de signaler une erreur ou un manque sur les mesures.
                 Repasse le chantier en "À mesurer" pour que le Commercial
                 puisse corriger. */}
            {isAwaitingValidation && roleIsTechnician && !isSoloArtisan && (
              <TouchableOpacity
                testID="tech-send-back-to-commercial"
                onPress={() => {
                  Alert.alert(
                    t("chantierDetail.validation.sendBackTitle"),
                    t("chantierDetail.validation.sendBackMsg"),
                    [
                      { text: t("common.cancel"), style: "cancel" },
                      {
                        text: t("chantierDetail.validation.sendBackConfirm"),
                        style: "default",
                        onPress: async () => {
                          let patchOk = false;
                          try {
                            await api.patch(`/chantiers/${id}`, {
                              status: "a_mesurer",
                            });
                            patchOk = true;
                          } catch {
                            /* on vérifiera après refetch */
                          }
                          try {
                            const res = await api.get<Chantier>(
                              `/chantiers/${id}`,
                            );
                            setChantier(res.data);
                            if (res.data.status === "a_mesurer") return;
                          } catch {
                            /* refetch ko */
                          }
                          if (!patchOk) {
                            Alert.alert(
                              t("chantierDetail.errors.title"),
                              t("chantierDetail.errors.sendBackFail"),
                            );
                          }
                        },
                      },
                    ],
                  );
                }}
                activeOpacity={0.85}
                style={validateStyles.btnOverride}
              >
                <Ionicons name="arrow-undo" size={20} color={colors.warning} />
                <Text style={validateStyles.btnOverrideText}>
                  {t("chantierDetail.validation.sendBackBtn")}
                </Text>
              </TouchableOpacity>
            )}
            {/* ↩️ DEMANDE DE MODIFICATION pour le Commercial.
                 Une fois en "à vérifier", le Commercial NE PEUT PLUS revenir
                 directement en "à mesurer". Il doit demander l'autorisation
                 au Technicien (workflow d'approbation). */}
            {isCommercialInVerify && (() => {
              const modReq = (chantier as any)?.mod_request;
              const isPending = modReq?.status === "pending";
              const isRefused = modReq?.status === "refused";
              if (isPending) {
                return (
                  <View style={validateStyles.waitCard}>
                    <Ionicons
                      name="hourglass-outline"
                      size={20}
                      color={colors.warning}
                    />
                    <View style={{ flex: 1 }}>
                      <Text style={validateStyles.waitTitle}>
                        {t("chantierDetail.modRequest.pendingTitle")}
                      </Text>
                      <Text style={validateStyles.waitBody}>
                        {t("chantierDetail.modRequest.pendingBody")}
                      </Text>
                    </View>
                  </View>
                );
              }
              return (
                <TouchableOpacity
                  testID="commercial-request-modification-button"
                  onPress={() => {
                    // 🆕 V3 — On ouvre une modale propre (compatible iOS/
                    // Android/web) au lieu de Alert.prompt (iOS-only).
                    setModRequestReason("");
                    setModRequestOpen(true);
                  }}
                  activeOpacity={0.85}
                  style={validateStyles.btnOverride}
                >
                  <Ionicons name="paper-plane-outline" size={20} color={colors.warning} />
                  <Text style={validateStyles.btnOverrideText}>
                    {isRefused
                      ? t("chantierDetail.modRequest.btnRenew")
                      : t("chantierDetail.modRequest.btnNew")}
                  </Text>
                </TouchableOpacity>
              );
            })()}
            {/* 🔔 BANNIÈRE TECHNICIEN — Demande de modification en attente */}
            {roleIsTechnician &&
              (chantier as any)?.mod_request?.status === "pending" && (
              <View
                style={[
                  validateStyles.waitCard,
                  { borderColor: colors.primary, borderWidth: 1 },
                ]}
              >
                <Ionicons
                  name="alert-circle"
                  size={22}
                  color={colors.primary}
                />
                <View style={{ flex: 1 }}>
                  <Text style={validateStyles.waitTitle}>
                    {t("chantierDetail.modRequest.techTitle")}
                  </Text>
                  <Text style={validateStyles.waitBody}>
                    {(chantier as any).mod_request.requested_by_name
                      ? t("chantierDetail.modRequest.techBodyName", { name: (chantier as any).mod_request.requested_by_name })
                      : t("chantierDetail.modRequest.techBodyDefault")}
                    {(chantier as any).mod_request.reason
                      ? t("chantierDetail.modRequest.techBodyReason", { reason: (chantier as any).mod_request.reason })
                      : ""}
                  </Text>
                  <View style={{ flexDirection: "row", gap: 8, marginTop: 10 }}>
                    <TouchableOpacity
                      testID="tech-approve-mod-request"
                      onPress={async () => {
                        Alert.alert(
                          t("chantierDetail.modRequest.approveTitle"),
                          t("chantierDetail.modRequest.approveMsg"),
                          [
                            { text: t("common.cancel"), style: "cancel" },
                            {
                              text: t("chantierDetail.modRequest.approveConfirm"),
                              style: "default",
                              onPress: async () => {
                                try {
                                  await api.post(
                                    `/chantiers/${id}/mod-request/respond`,
                                    { approve: true },
                                  );
                                  const res = await api.get<Chantier>(
                                    `/chantiers/${id}`,
                                  );
                                  setChantier(res.data);
                                } catch {
                                  Alert.alert(
                                    t("chantierDetail.errors.title"),
                                    t("chantierDetail.errors.respondFail"),
                                  );
                                }
                              },
                            },
                          ],
                        );
                      }}
                      style={[
                        validateStyles.btnOverride,
                        {
                          flex: 1,
                          borderColor: colors.success,
                          backgroundColor: colors.success + "1A",
                        },
                      ]}
                      activeOpacity={0.85}
                    >
                      <Ionicons
                        name="checkmark-circle"
                        size={18}
                        color={colors.success}
                      />
                      <Text
                        style={[
                          validateStyles.btnOverrideText,
                          { color: colors.success },
                        ]}
                      >
                        {t("chantierDetail.modRequest.approveBtn")}
                      </Text>
                    </TouchableOpacity>
                    <TouchableOpacity
                      testID="tech-refuse-mod-request"
                      onPress={async () => {
                        Alert.alert(
                          t("chantierDetail.modRequest.refuseTitle"),
                          t("chantierDetail.modRequest.refuseMsg"),
                          [
                            { text: t("common.cancel"), style: "cancel" },
                            {
                              text: t("chantierDetail.modRequest.refuseConfirm"),
                              style: "destructive",
                              onPress: async () => {
                                try {
                                  await api.post(
                                    `/chantiers/${id}/mod-request/respond`,
                                    { approve: false },
                                  );
                                  const res = await api.get<Chantier>(
                                    `/chantiers/${id}`,
                                  );
                                  setChantier(res.data);
                                } catch {
                                  Alert.alert(
                                    t("chantierDetail.errors.title"),
                                    t("chantierDetail.errors.respondFail"),
                                  );
                                }
                              },
                            },
                          ],
                        );
                      }}
                      style={[
                        validateStyles.btnOverride,
                        {
                          flex: 1,
                          borderColor: colors.warning,
                          backgroundColor: colors.warning + "1A",
                        },
                      ]}
                      activeOpacity={0.85}
                    >
                      <Ionicons
                        name="close-circle"
                        size={18}
                        color={colors.warning}
                      />
                      <Text
                        style={[
                          validateStyles.btnOverrideText,
                          { color: colors.warning },
                        ]}
                      >
                        {t("chantierDetail.modRequest.refuseBtn")}
                      </Text>
                    </TouchableOpacity>
                  </View>
                </View>
              </View>
            )}
            {/* ↩️ Bouton de RETOUR ARRIÈRE (legacy) — Désactivé pour Commercial.
                 Garde la logique uniquement pour les workflows existants. */}
            {false && isCommercialInVerify && (
              <TouchableOpacity
                testID="commercial-back-to-measure-button"
                onPress={() => {
                  Alert.alert(
                    t("chantierDetail.backToMeasure.title"),
                    t("chantierDetail.backToMeasure.msg"),
                    [
                      { text: t("common.cancel"), style: "cancel" },
                      {
                        text: t("chantierDetail.backToMeasure.confirm"),
                        style: "default",
                        onPress: async () => {
                          // ✅ Résilience : on tente le PATCH. Même si axios
                          // lève (timeout, réseau capricieux), on refetch
                          // l'état du chantier — si le statut a bougé côté
                          // serveur on considère que c'est un succès, et on
                          // ne montre une erreur qu'en cas de vraie panne.
                          let patchOk = false;
                          try {
                            await api.patch(`/chantiers/${id}`, {
                              status: "a_mesurer",
                            });
                            patchOk = true;
                          } catch {
                            /* on vérifiera l'état après refetch */
                          }
                          try {
                            const res = await api.get<Chantier>(
                              `/chantiers/${id}`,
                            );
                            setChantier(res.data);
                            if (res.data.status === "a_mesurer") {
                              return; // succès — pas d'alerte
                            }
                          } catch {
                            /* refetch impossible, on tombe sur l'erreur */
                          }
                          if (!patchOk) {
                            Alert.alert(
                              t("chantierDetail.errors.title"),
                              t("chantierDetail.errors.backToMeasureFail"),
                            );
                          }
                        },
                      },
                    ],
                  );
                }}
                activeOpacity={0.85}
                style={validateStyles.btnOverride}
              >
                <Ionicons name="arrow-undo" size={20} color={colors.warning} />
                <Text style={validateStyles.btnOverrideText}>
                  {t("chantierDetail.backToMeasure.btn")}
                </Text>
              </TouchableOpacity>
            )}
            {isInFabrication && user?.role === "technician" && !techOverride && (
              <TouchableOpacity
                testID="tech-override-button"
                onPress={requestTechOverride}
                activeOpacity={0.85}
                style={validateStyles.btnOverride}
              >
                <Ionicons name="warning" size={20} color={colors.warning} />
                <Text style={validateStyles.btnOverrideText}>
                  {t("chantierDetail.techOverride.btn")}
                </Text>
              </TouchableOpacity>
            )}
            {isInFabrication && techOverride && (
              <View style={validateStyles.overrideActive}>
                <Ionicons name="lock-open" size={18} color={colors.anomaly} />
                <Text style={validateStyles.overrideActiveText}>
                  {t("chantierDetail.techOverride.active")}
                </Text>
                <TouchableOpacity
                  onPress={() => setTechOverride(false)}
                  activeOpacity={0.7}
                  style={validateStyles.lockBackBtn}
                >
                  <Text style={validateStyles.lockBackText}>{t("chantierDetail.techOverride.lock")}</Text>
                </TouchableOpacity>
              </View>
            )}
            {/* 🚫 En mode Artisan/Solo, l'admin EST le technicien — pas de
                 message "seul le technicien peut" car il fait tout lui-même.
                 En mode Entreprise, le verrou reste affiché pour Commercial/Admin. */}
            {isInFabrication &&
              user?.role !== "technician" &&
              !isSoloArtisan &&
              !isArtisanAccount &&
              !artisanMode && (
              <View style={validateStyles.fabLockCard}>
                <Ionicons name="cog" size={20} color={colors.primary} />
                <View style={{ flex: 1 }}>
                  <Text style={validateStyles.fabLockTitle}>
                    {t("chantierDetail.fabLock.title")}
                  </Text>
                  <Text style={validateStyles.fabLockBody}>
                    {user?.role === "commercial"
                      ? t("chantierDetail.fabLock.msgCommercial")
                      : t("chantierDetail.fabLock.msgOther")}
                  </Text>
                </View>
              </View>
            )}

            {/* 🔒 Bannière verrou TOTAL si chantier "Terminé / Clôturé".
                 Les exports PDF/CSV/XLSX/JSON restent 100% dispo en dessous. */}
            {isArchived && (
              <View
                testID="chantier-archived-lock-banner"
                style={validateStyles.archivedLockCard}
              >
                <Ionicons name="lock-closed" size={20} color={colors.success} />
                <View style={{ flex: 1 }}>
                  <Text style={validateStyles.archivedLockTitle}>
                    {t("chantierDetail.archivedLock.bannerTitle")}
                  </Text>
                  <Text style={validateStyles.archivedLockBody}>
                    {t("chantierDetail.archivedLock.bannerBody")}
                  </Text>
                </View>
              </View>
            )}

            {/* === Exports === */}
            {mesures.length > 0 && (
              <View style={styles.exportCard}>
                <View style={styles.exportHeader}>
                  <Ionicons name="download" size={18} color={colors.primary} />
                  <Text style={styles.exportTitle}>{t("chantierDetail.exports.title")}</Text>
                  {isFreePlan && (
                    <View style={styles.freeLockBadge}>
                      <Ionicons name="lock-closed" size={11} color={colors.anomaly} />
                      <Text style={styles.freeLockBadgeText}>{t("chantierDetail.exports.freeLockBadge")}</Text>
                    </View>
                  )}
                </View>
                <Text style={styles.exportSub}>
                  {isFreePlan
                    ? t("chantierDetail.exports.subFree")
                    : t("chantierDetail.exports.sub")}
                </Text>
                <View style={styles.exportGrid}>
                <ExportTile
                  testID="export-pdf-button"
                  busy={exporting === "pdf"}
                  onPress={() =>
                    isFreePlan
                      ? showUpgradeLock()
                      : router.push(`/chantier/${id}/pdf-preview`)
                  }
                  icon="document-text"
                  label={t("chantierDetail.exports.pdfLabel")}
                  sub={t("chantierDetail.exports.pdfSub")}
                  color="#EF4444"
                  locked={isFreePlan}
                />
                  {(canExportTech || showCommercialFabIntercept) && (
                    <ExportTile
                      testID="export-xlsx-button"
                      busy={exporting === "xlsx"}
                      onPress={() => {
                        if (showCommercialFabIntercept) return interceptCommercialFab();
                        if (isFreePlan) return showUpgradeLock();
                        router.push(`/chantier/${id}/xlsx-preview`);
                      }}
                      icon="grid"
                      label={t("chantierDetail.exports.xlsxLabel")}
                      sub={t("chantierDetail.exports.xlsxSub")}
                      color="#22C55E"
                      locked={isFreePlan || showCommercialFabIntercept}
                    />
                  )}
                  {/* CSV tile : TOUJOURS visible. Le clic est intercepté
                      avec un Alert pédagogique pour les rôles non autorisés.
                      Sur web/simulateur, fallback via anchor blob download. */}
                  <ExportTile
                    testID="export-csv-button"
                    busy={exporting === "csv"}
                    onPress={() => {
                      if (showCommercialFabIntercept) return interceptCommercialFab();
                      if (!canExportTech) {
                        // Commercial hors fab : alert pédagogique RBAC standard
                        if (user?.role === "commercial") {
                          Alert.alert(
                            t("chantierDetail.exports.csvReservedTitle"),
                            t("chantierDetail.exports.csvReservedMsg"),
                            [{ text: t("common.ok"), style: "default" }]
                          );
                          return;
                        }
                      }
                      downloadExport("csv");
                    }}
                    icon="list"
                    label={t("chantierDetail.exports.csvLabel")}
                    sub={t("chantierDetail.exports.csvSub")}
                    color="#3B82F6"
                    locked={
                      isFreePlan ||
                      showCommercialFabIntercept ||
                      (!canExportTech && user?.role === "commercial")
                    }
                  />
                  {(canExportTech || showCommercialFabIntercept) && (
                    <ExportTile
                      testID="export-json-button"
                      busy={exporting === "json"}
                      onPress={() => {
                        if (showCommercialFabIntercept) return interceptCommercialFab();
                        if (isFreePlan) return showUpgradeLock();
                        router.push(`/chantier/${id}/json-preview`);
                      }}
                      icon="code-slash"
                      label={t("chantierDetail.exports.jsonLabel")}
                      sub={t("chantierDetail.exports.jsonSub")}
                      color="#A855F7"
                      locked={isFreePlan || showCommercialFabIntercept}
                    />
                  )}
                  {/* 🆕 V3 — Export ERP universel (CSV + XML)
                   * Format générique compatible Elcia, Ramasoft & autres
                   * ERPs menuiserie (import manuel). */}
                  {(canExportTech || showCommercialFabIntercept) && (
                    <ExportTile
                      testID="export-erp-csv-button"
                      busy={exporting === "erp-csv"}
                      onPress={() => {
                        if (showCommercialFabIntercept) return interceptCommercialFab();
                        if (isFreePlan) return showUpgradeLock();
                        downloadExport("erp-csv");
                      }}
                      icon="business"
                      label={t("chantierDetail.exports.erpCsvLabel")}
                      sub={t("chantierDetail.exports.erpCsvSub")}
                      color="#F59E0B"
                      locked={isFreePlan || showCommercialFabIntercept}
                    />
                  )}
                  {(canExportTech || showCommercialFabIntercept) && (
                    <ExportTile
                      testID="export-erp-xml-button"
                      busy={exporting === "erp-xml"}
                      onPress={() => {
                        if (showCommercialFabIntercept) return interceptCommercialFab();
                        if (isFreePlan) return showUpgradeLock();
                        downloadExport("erp-xml");
                      }}
                      icon="document-attach"
                      label={t("chantierDetail.exports.erpXmlLabel")}
                      sub={t("chantierDetail.exports.erpXmlSub")}
                      color="#0EA5E9"
                      locked={isFreePlan || showCommercialFabIntercept}
                    />
                  )}
                </View>
              </View>
            )}
          </View>
        }
      />

      <View style={styles.footer}>
        {chantier.status !== "cloture" && (() => {
          // ... (RBAC logic identical to before)
          const status = chantier.status;
          let canCloseStep = false;
          if (isSoloArtisan || isArtisanAccount || artisanMode) {
            canCloseStep = roleIsAdmin || roleIsCommercial || roleIsTechnician;
          } else if (status === "devis_a_faire") {
            canCloseStep = roleIsAdmin;
          } else if (status === "a_mesurer") {
            canCloseStep = roleIsCommercial;
          } else if (
            status === "technique_a_valider" ||
            status === "a_verifier" ||
            status === "en_fabrication" ||
            status === "en_commande"
          ) {
            canCloseStep = roleIsTechnician;
          }
          const isAdminEntreprise =
            roleIsAdmin &&
            !isSoloArtisan &&
            !isArtisanAccount &&
            !artisanMode;
          // 📤 Cas spécial : "ENVOYER À UN COMMERCIAL" reste full-width
          //    car c'est le CTA principal pour faire avancer le chantier
          //    depuis l'état initial.
          if (canCloseStep && isAdminEntreprise && status === "devis_a_faire") {
            return (
              <TouchableOpacity
                testID="send-to-commercial-button"
                onPress={handleSendToCommercialClick}
                style={[styles.btn, styles.btnPrimary]}
                activeOpacity={0.85}
              >
                <Ionicons name="paper-plane" size={20} color="#000" />
                <Text style={styles.btnPrimaryText}>
                  {t("chantierDetail.sendToCommercial.footerBtn")}
                </Text>
              </TouchableOpacity>
            );
          }
          // 🆕 V3 — Grille uniforme à 3 boutons IDENTIQUES (cahier 10/06/2026).
          //    Chaque action principale prend la même largeur sur une seule
          //    ligne pour libérer la liste d'ouvertures au-dessus.
          const showClose = canCloseStep;
          const showAdd = canEditMesures;
          // 🆕 (juin 2026) Wall config OPTIONNELLE : le bouton est TOUJOURS
          // visible (même sans wall_config). Le libellé s'adapte :
          //   • wall_config déjà rempli → "Modifier les murs"
          //   • wall_config vide       → "Dimensions des murs (optionnel)"
          const hasWallConfig = !!chantier?.wall_config?.masonry_type;
          const showEditWall = canEditMesures;
          const wallBtnLabel = hasWallConfig
            ? t("chantierDetail.footer.wall")
            : "Dimensions des murs";
          if (!showClose && !showAdd && !showEditWall) return null;
          return (
            <View style={styles.actionGrid}>
              {showClose && (
                <TouchableOpacity
                  testID="close-project-button"
                  onPress={() => router.push(`/chantier/${id}/closure`)}
                  style={[styles.gridBtn, styles.gridBtnSecondary]}
                  activeOpacity={0.7}
                >
                  <Ionicons
                    name="flag-outline"
                    size={20}
                    color={colors.textPrimary}
                  />
                  <Text
                    style={styles.gridBtnTextSecondary}
                    numberOfLines={1}
                    adjustsFontSizeToFit
                    minimumFontScale={0.8}
                  >
                    {t("chantierDetail.footer.close")}
                  </Text>
                </TouchableOpacity>
              )}
              {showAdd && (
                <TouchableOpacity
                  testID="add-mesure-button"
                  onPress={() => router.push(`/chantier/${id}/new-mesure`)}
                  style={[styles.gridBtn, styles.gridBtnPrimary]}
                  activeOpacity={0.85}
                >
                  <Ionicons name="add" size={22} color="#000" />
                  <Text
                    style={styles.gridBtnTextPrimary}
                    numberOfLines={1}
                    adjustsFontSizeToFit
                    minimumFontScale={0.8}
                  >
                    {t("chantierDetail.footer.add")}
                  </Text>
                </TouchableOpacity>
              )}
              {showEditWall && (
                <TouchableOpacity
                  testID="edit-wall-config-button"
                  onPress={() => router.push(`/chantier/${id}/new-mesure?edit_wall_config=1`)}
                  style={[styles.gridBtn, styles.gridBtnSecondary]}
                  activeOpacity={0.85}
                >
                  <Ionicons
                    name={hasWallConfig ? "construct-outline" : "cube-outline"}
                    size={20}
                    color={colors.primary}
                  />
                  <Text
                    style={[styles.gridBtnTextSecondary, { color: colors.primary }]}
                    numberOfLines={1}
                    adjustsFontSizeToFit
                    minimumFontScale={0.8}
                  >
                    {wallBtnLabel}
                  </Text>
                  {!hasWallConfig && (
                    <View
                      style={{
                        position: "absolute",
                        top: 4,
                        right: 6,
                        backgroundColor: colors.textSecondary,
                        borderRadius: 8,
                        paddingHorizontal: 5,
                        paddingVertical: 1,
                      }}
                    >
                      <Text style={{ color: "#fff", fontSize: 8, fontWeight: "700", letterSpacing: 0.5 }}>
                        OPT
                      </Text>
                    </View>
                  )}
                </TouchableOpacity>
              )}
            </View>
          );
        })()}
      </View>

      <Modal visible={assignOpen} transparent animationType="fade" onRequestClose={() => setAssignOpen(false)}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>{t("chantierDetail.assign.modalTitle")}</Text>
            <Text style={styles.modalSub}>
              {t("chantierDetail.assign.modalSub")}
            </Text>
            <FlatList
              data={users.filter((u) => u.role === "commercial")}
              keyExtractor={(u) => u.id}
              style={{ maxHeight: 320 }}
              ListEmptyComponent={
                <View style={{ padding: 16, alignItems: "center" }}>
                  <Text style={[styles.modalSub, { marginBottom: 0 }]}>
                    {t("chantierDetail.assign.noCommercial")}
                  </Text>
                </View>
              }
              ListHeaderComponent={
                <TouchableOpacity
                  testID="assign-none"
                  onPress={() => assignTo(null)}
                  style={[styles.assignItem, !chantier.assigned_to && styles.assignItemActive]}
                  activeOpacity={0.7}
                >
                  <Ionicons name="close-circle-outline" size={20} color={colors.textSecondary} />
                  <Text style={styles.assignItemText}>{t("chantierDetail.assign.noAssignment")}</Text>
                </TouchableOpacity>
              }
              renderItem={({ item }) => {
                const active = chantier.assigned_to === item.id;
                return (
                  <TouchableOpacity
                    testID={`assign-user-${item.id}`}
                    onPress={() => assignTo(item.id)}
                    style={[styles.assignItem, active && styles.assignItemActive]}
                    activeOpacity={0.7}
                  >
                    <Ionicons
                      name="briefcase"
                      size={20}
                      color={active ? colors.primary : colors.textSecondary}
                    />
                    <View style={{ flex: 1 }}>
                      <Text style={styles.assignItemText}>{item.name}</Text>
                      <Text style={styles.assignItemRole}>{t("chantierDetail.assign.roleCommercial")}</Text>
                    </View>
                    {active && <Ionicons name="checkmark-circle" size={20} color={colors.primary} />}
                  </TouchableOpacity>
                );
              }}
            />
            <TouchableOpacity
              testID="assign-cancel"
              onPress={() => setAssignOpen(false)}
              style={[styles.btn, styles.btnSecondary, { marginTop: 12 }]}
              activeOpacity={0.7}
            >
              <Text style={styles.btnSecondaryText}>{t("chantierDetail.assign.close")}</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

      {/* 🆕 V3 — Modale "Demande de modification au technicien".
          Remplace Alert.prompt (iOS-only) par un composant universel. */}
      <Modal
        visible={modRequestOpen}
        transparent
        animationType="fade"
        onRequestClose={() => !modRequestSubmitting && setModRequestOpen(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>{t("chantierDetail.modRequest.modalTitle")}</Text>
            <Text style={styles.modalSub}>
              {t("chantierDetail.modRequest.modalSub")}
            </Text>
            <TextInput
              testID="mod-request-reason-input"
              value={modRequestReason}
              onChangeText={setModRequestReason}
              placeholder={t("chantierDetail.modRequest.reasonPlaceholder")}
              placeholderTextColor={colors.placeholder}
              multiline
              numberOfLines={4}
              maxLength={500}
              editable={!modRequestSubmitting}
              style={{
                backgroundColor: colors.inputBg,
                color: colors.textPrimary,
                borderRadius: 8,
                borderWidth: 1,
                borderColor: colors.borderStrong,
                minHeight: 96,
                padding: 12,
                fontSize: 14,
                textAlignVertical: "top",
                marginBottom: 12,
              }}
            />
            <View style={{ flexDirection: "row", gap: 8 }}>
              <TouchableOpacity
                testID="mod-request-cancel"
                onPress={() => {
                  if (modRequestSubmitting) return;
                  setModRequestOpen(false);
                  setModRequestReason("");
                }}
                disabled={modRequestSubmitting}
                style={[styles.btn, styles.btnSecondary, { flex: 1 }]}
                activeOpacity={0.7}
              >
                <Text style={styles.btnSecondaryText}>{t("chantierDetail.edit.cancel")}</Text>
              </TouchableOpacity>
              <TouchableOpacity
                testID="mod-request-confirm"
                onPress={async () => {
                  if (modRequestSubmitting) return;
                  setModRequestSubmitting(true);
                  try {
                    await api.post(`/chantiers/${id}/mod-request`, {
                      reason: modRequestReason.trim() || "",
                    });
                    const res = await api.get<Chantier>(`/chantiers/${id}`);
                    setChantier(res.data);
                    setModRequestOpen(false);
                    setModRequestReason("");
                    Alert.alert(
                      t("chantierDetail.modRequest.sentTitle"),
                      t("chantierDetail.modRequest.sentMsg"),
                    );
                  } catch (e: any) {
                    Alert.alert(
                      t("chantierDetail.errors.title"),
                      e?.response?.data?.detail ||
                        t("chantierDetail.errors.modRequestFail"),
                    );
                  } finally {
                    setModRequestSubmitting(false);
                  }
                }}
                disabled={modRequestSubmitting}
                style={[
                  styles.btn,
                  styles.btnPrimary,
                  { flex: 1 },
                  modRequestSubmitting && { opacity: 0.5 },
                ]}
                activeOpacity={0.85}
              >
                <Ionicons name="paper-plane" size={16} color="#000" />
                <Text style={styles.btnPrimaryText}>
                  {modRequestSubmitting
                    ? t("chantierDetail.modRequest.sendingBtn")
                    : t("chantierDetail.modRequest.confirmBtn")}
                </Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      {/* 📤 Modale picker : choix du commercial (plusieurs commerciaux dispos) */}
      <Modal
        visible={sendToCommercialOpen}
        transparent
        animationType="fade"
        onRequestClose={() => setSendToCommercialOpen(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>{t("chantierDetail.sendToCommercial.modalTitle")}</Text>
            <Text style={styles.modalSub}>
              {t("chantierDetail.sendToCommercial.modalSub")}
            </Text>
            <FlatList
              data={users.filter((u) => u.role === "commercial")}
              keyExtractor={(u) => u.id}
              style={{ maxHeight: 320 }}
              renderItem={({ item }) => (
                <TouchableOpacity
                  testID={`send-commercial-${item.id}`}
                  onPress={() => sendToCommercial(item.id)}
                  style={styles.assignItem}
                  activeOpacity={0.7}
                >
                  <Ionicons
                    name="briefcase"
                    size={20}
                    color={colors.primary}
                  />
                  <View style={{ flex: 1 }}>
                    <Text style={styles.assignItemText}>{item.name}</Text>
                    <Text style={styles.assignItemRole}>{item.email}</Text>
                  </View>
                  <Ionicons
                    name="paper-plane-outline"
                    size={18}
                    color={colors.primary}
                  />
                </TouchableOpacity>
              )}
            />
            <TouchableOpacity
              testID="send-commercial-cancel"
              onPress={() => setSendToCommercialOpen(false)}
              style={[styles.btn, styles.btnSecondary, { marginTop: 12 }]}
              activeOpacity={0.7}
            >
              <Text style={styles.btnSecondaryText}>{t("chantierDetail.edit.cancel")}</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

      {/* ✏️ Modale d'édition des infos chantier (client + adresse + RDV) */}
      <Modal
        visible={editOpen}
        transparent
        animationType="fade"
        presentationStyle="overFullScreen"
        statusBarTranslucent
        onRequestClose={() => setEditOpen(false)}
      >
        <KeyboardAvoidingView
          behavior={Platform.OS === "ios" ? "padding" : "height"}
          style={{ flex: 1 }}
        >
          <View style={styles.modalOverlay}>
            <View style={[styles.modalCard, { maxHeight: "92%" }]}>
              <Text style={styles.modalTitle}>{t("chantierDetail.edit.modalTitle")}</Text>
              <Text style={styles.modalSub}>
                {t("chantierDetail.edit.modalSub")}
              </Text>
              <ScrollView
                keyboardShouldPersistTaps="handled"
                contentContainerStyle={{ paddingBottom: 8 }}
              >
                <Text style={editStyles.label}>{t("chantierDetail.edit.firstName")}</Text>
                <TextInput
                  testID="edit-firstname-input"
                  value={editFirstName}
                  onChangeText={setEditFirstName}
                  placeholder={t("chantierDetail.edit.firstNamePlaceholder")}
                  placeholderTextColor={colors.placeholder}
                  style={editStyles.input}
                />
                <Text style={editStyles.label}>{t("chantierDetail.edit.lastName")}</Text>
                <TextInput
                  testID="edit-lastname-input"
                  value={editLastName}
                  onChangeText={setEditLastName}
                  placeholder={t("chantierDetail.edit.lastNamePlaceholder")}
                  placeholderTextColor={colors.placeholder}
                  style={editStyles.input}
                />
                <Text style={editStyles.label}>{t("chantierDetail.edit.address")}</Text>
                <TextInput
                  testID="edit-address-input"
                  value={editAddress}
                  onChangeText={setEditAddress}
                  placeholder={t("chantierDetail.edit.addressPlaceholder")}
                  placeholderTextColor={colors.placeholder}
                  style={editStyles.input}
                />
                <View style={{ flexDirection: "row", gap: 10 }}>
                  <View style={{ flex: 1 }}>
                    <Text style={editStyles.label}>{t("chantierDetail.edit.postal")}</Text>
                    <TextInput
                      testID="edit-postal-input"
                      value={editPostal}
                      onChangeText={setEditPostal}
                      placeholder={t("chantierDetail.edit.postalPlaceholder")}
                      placeholderTextColor={colors.placeholder}
                      keyboardType="number-pad"
                      style={editStyles.input}
                    />
                  </View>
                  <View style={{ flex: 2 }}>
                    <Text style={editStyles.label}>{t("chantierDetail.edit.city")}</Text>
                    <TextInput
                      testID="edit-city-input"
                      value={editCity}
                      onChangeText={setEditCity}
                      placeholder={t("chantierDetail.edit.cityPlaceholder")}
                      placeholderTextColor={colors.placeholder}
                      style={editStyles.input}
                    />
                  </View>
                </View>
                <Text style={editStyles.label}>{t("chantierDetail.edit.appointment")}</Text>
                <TouchableOpacity
                  testID="edit-appointment-button"
                  onPress={() => setEditApptPickerOpen(true)}
                  style={[editStyles.input, editStyles.dateBtn]}
                  activeOpacity={0.7}
                >
                  <Ionicons
                    name="calendar-outline"
                    size={18}
                    color={colors.textSecondary}
                  />
                  <Text
                    style={[
                      editStyles.dateBtnText,
                      !editAppointment && { color: colors.placeholder },
                    ]}
                  >
                    {editAppointment
                      ? editAppointment.toLocaleString(
                          i18n.language === "en"
                            ? "en-US"
                            : i18n.language === "nl"
                              ? "nl-BE"
                              : "fr-FR",
                          {
                            weekday: "short",
                            day: "2-digit",
                            month: "short",
                            year: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                          },
                        )
                      : t("chantierDetail.edit.appointmentEmpty")}
                  </Text>
                  {editAppointment && (
                    <TouchableOpacity
                      onPress={() => setEditAppointment(null)}
                      hitSlop={10}
                    >
                      <Ionicons
                        name="close-circle"
                        size={18}
                        color={colors.textSecondary}
                      />
                    </TouchableOpacity>
                  )}
                </TouchableOpacity>
              </ScrollView>
              <AppointmentPicker
                visible={editApptPickerOpen}
                value={editAppointment ? editAppointment.toISOString() : null}
                onClose={() => setEditApptPickerOpen(false)}
                onConfirm={(iso) => setEditAppointment(new Date(iso))}
                title={t("chantierDetail.edit.appointment")}
              />
              <View
                style={{
                  flexDirection: "row",
                  gap: 10,
                  marginTop: 12,
                }}
              >
                <TouchableOpacity
                  testID="edit-cancel"
                  onPress={() => setEditOpen(false)}
                  style={[styles.btn, styles.btnSecondary, { flex: 1 }]}
                  activeOpacity={0.7}
                >
                  <Text style={styles.btnSecondaryText}>{t("chantierDetail.edit.cancel")}</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  testID="edit-save"
                  onPress={saveEdit}
                  disabled={savingEdit}
                  style={[
                    styles.btn,
                    styles.btnPrimary,
                    { flex: 1, opacity: savingEdit ? 0.6 : 1 },
                  ]}
                  activeOpacity={0.85}
                >
                  <Ionicons name="save" size={18} color="#000" />
                  <Text style={styles.btnPrimaryText}>
                    {savingEdit ? t("chantierDetail.edit.saving") : t("chantierDetail.edit.save")}
                  </Text>
                </TouchableOpacity>
              </View>
            </View>
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </SafeAreaView>
  );
}

// ---- Export tile composant ------------------------------------------------
function ExportTile({
  testID,
  busy,
  onPress,
  icon,
  label,
  sub,
  color,
  locked,
}: {
  testID?: string;
  busy: boolean;
  onPress: () => void;
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  sub: string;
  color: string;
  locked?: boolean;
}) {
  return (
    <TouchableOpacity
      testID={testID}
      onPress={onPress}
      disabled={busy}
      activeOpacity={0.85}
      style={[exportStyles.tile, busy && { opacity: 0.5 }, locked && { opacity: 0.85 }]}
    >
      <View style={[exportStyles.iconBox, { backgroundColor: color + "22" }]}>
        {busy ? (
          <ActivityIndicator color={color} />
        ) : (
          <Ionicons name={icon} size={20} color={color} />
        )}
        {locked && (
          <View style={exportStyles.lockOverlay}>
            <Ionicons name="lock-closed" size={12} color="#fff" />
          </View>
        )}
      </View>
      <Text style={exportStyles.label}>{label}</Text>
      <Text style={exportStyles.sub}>{sub}</Text>
    </TouchableOpacity>
  );
}

const exportStyles = StyleSheet.create({
  tile: {
    width: "47%",
    backgroundColor: "#0C0C0E",
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#202024",
    padding: 12,
    alignItems: "center",
  },
  iconBox: {
    width: 38,
    height: 38,
    borderRadius: 19,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 6,
  },
  lockOverlay: {
    position: "absolute",
    bottom: -2,
    right: -2,
    width: 16,
    height: 16,
    borderRadius: 8,
    backgroundColor: colors.anomaly,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1.5,
    borderColor: "#0C0C0E",
  },
  label: { color: "#fff", fontWeight: "900", fontSize: 12, letterSpacing: 0.5 },
  sub: { color: "#888", fontSize: 10, marginTop: 2, textAlign: "center" },
});

const photoStyles = StyleSheet.create({
  row: {
    flexDirection: "row",
    gap: 10,
    marginBottom: 10,
    padding: 8,
    backgroundColor: "#0C0C0E",
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#202024",
  },
  thumb: { width: 64, height: 64, borderRadius: 8, backgroundColor: "#000" },
  captionWrap: { flex: 1, justifyContent: "space-between" },
  captionInput: {
    backgroundColor: "#000",
    color: "#fff",
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#2a2a2e",
    paddingHorizontal: 10,
    paddingVertical: 8,
    fontSize: 12,
    minHeight: 36,
  },
  delBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    alignSelf: "flex-end",
    paddingTop: 4,
  },
  delBtnText: { color: "#EF4444", fontSize: 10, fontWeight: "800", letterSpacing: 0.4 },
  addRow: { flexDirection: "row", gap: 10, marginTop: 4 },
  addBtn: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    paddingVertical: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#202024",
    backgroundColor: "#0C0C0E",
  },
  addBtnText: { color: "#fff", fontSize: 12, fontWeight: "800", letterSpacing: 0.4 },
});

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: colors.bg },
  center: { alignItems: "center", justifyContent: "center" },
  header: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: 18,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    marginBottom: 12,
  },
  headerTopRow: { flexDirection: "row", alignItems: "flex-start", gap: 8 },
  deleteIconBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: "#2a1010",
    borderWidth: 1,
    borderColor: colors.anomaly,
    alignItems: "center",
    justifyContent: "center",
  },
  clientName: { color: colors.textPrimary, fontSize: 22, fontWeight: "900" },
  addressRow: { flexDirection: "row", alignItems: "center", gap: 6, marginTop: 4 },
  address: { color: colors.textSecondary, fontSize: 13, flex: 1 },
  badge: {
    flexDirection: "row",
    alignItems: "center",
    alignSelf: "flex-start",
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 4,
    gap: 6,
    marginTop: 12,
  },
  badgeDot: { width: 6, height: 6, borderRadius: 3 },
  badgeText: { fontSize: 11, fontWeight: "800", textTransform: "uppercase", letterSpacing: 0.8 },
  statsRow: { flexDirection: "row", gap: 12, marginBottom: 18 },
  statCard: {
    flex: 1,
    backgroundColor: colors.surface,
    padding: 16,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
  },
  statValue: { color: colors.primary, fontSize: 28, fontWeight: "900" },
  statLabel: {
    color: colors.textSecondary,
    fontSize: 11,
    textTransform: "uppercase",
    letterSpacing: 0.8,
    fontWeight: "700",
  },
  sectionTitle: {
    color: colors.textSecondary,
    fontSize: 12,
    fontWeight: "800",
    letterSpacing: 1.5,
    marginBottom: 10,
  },
  mesureCard: {
    backgroundColor: colors.surface,
    borderColor: colors.borderSubtle,
    borderWidth: 1,
    borderRadius: 10,
    paddingVertical: 8,
    paddingHorizontal: 10,
    marginBottom: 6,
  },
  mesureRow: { flexDirection: "row", alignItems: "center", gap: 10 },
  mesureThumb: { width: 44, height: 44, borderRadius: 6, backgroundColor: colors.bg },
  mesureThumbPlaceholder: {
    width: 44,
    height: 44,
    borderRadius: 6,
    backgroundColor: colors.bg,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    alignItems: "center",
    justifyContent: "center",
  },
  mesureLabel: { color: colors.textPrimary, fontWeight: "800", fontSize: 14 },
  mesureType: { color: colors.textSecondary, marginTop: 1, fontSize: 12 },
  // 🆕 Import CDC — Badge orange "À VALIDER" sur mesure importée par IA pas encore confirmée
  importBadgeToValidate: {
    flexDirection: "row",
    alignItems: "center",
    gap: 3,
    backgroundColor: "#FF9F0A22",
    borderColor: "#FF9F0A",
    borderWidth: 1,
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
  },
  importBadgeToValidateText: {
    color: "#FF9F0A",
    fontSize: 9,
    fontWeight: "900",
    letterSpacing: 0.5,
  },
  // 🆕 Import CDC — Cercle vert avec V blanc — mesure CDC validée sur place
  validatedCircle: {
    width: 18,
    height: 18,
    borderRadius: 9,
    backgroundColor: "#32D74B",
    alignItems: "center",
    justifyContent: "center",
  },
  // 🆕 V3 — Icône corbeille discrète intégrée au bloc (remplace les
  //    boutons textuels MODIFIER/SUPPRIMER pour gagner en compacité).
  mesureTrashIcon: {
    width: 36,
    height: 36,
    borderRadius: 8,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "rgba(255,30,30,0.08)",
    borderWidth: 1,
    borderColor: "rgba(255,30,30,0.25)",
  },
  mesureActions: {
    flexDirection: "row",
    gap: 8,
    marginTop: 10,
    paddingTop: 10,
    borderTopWidth: 1,
    borderTopColor: colors.borderSubtle,
  },
  mesureEditBtn: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    paddingVertical: 8,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.primary,
    backgroundColor: "#1a0e05",
  },
  mesureEditText: { color: colors.primary, fontSize: 11, fontWeight: "900", letterSpacing: 0.6 },
  mesureDelBtn: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    paddingVertical: 8,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.anomaly,
    backgroundColor: "#2a1010",
  },
  mesureDelText: { color: colors.anomaly, fontSize: 11, fontWeight: "900", letterSpacing: 0.6 },
  slope: { color: colors.primary, fontSize: 12, marginTop: 4, fontWeight: "700" },
  alertWrap: {
    marginTop: 10,
    paddingTop: 10,
    borderTopWidth: 1,
    borderTopColor: colors.borderSubtle,
    gap: 4,
  },
  alertText: { color: colors.alert, fontSize: 12, fontWeight: "700" },
  empty: { alignItems: "center", padding: 50, gap: 8 },
  emptyText: { color: colors.textSecondary, fontWeight: "700" },
  emptyHint: {
    color: colors.textSecondary,
    fontSize: 12,
    textAlign: "center",
    lineHeight: 17,
    marginTop: 4,
    paddingHorizontal: 12,
  },
  importCta: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    backgroundColor: colors.primary,
    paddingHorizontal: 20,
    paddingVertical: 14,
    borderRadius: 12,
    marginTop: 20,
    minWidth: 240,
  },
  importCtaText: { fontSize: 14, fontWeight: "700", color: "#000" },
  importCtaSub: {
    fontSize: 11,
    color: colors.textSecondary,
    textAlign: "center",
    marginTop: 8,
    paddingHorizontal: 24,
    lineHeight: 16,
  },
  emptyCta: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    backgroundColor: colors.primary,
    paddingHorizontal: 18,
    paddingVertical: 14,
    borderRadius: 10,
    marginTop: 16,
  },
  emptyCtaText: {
    color: "#000",
    fontWeight: "900",
    letterSpacing: 0.8,
    fontSize: 13,
  },

  exportCard: {
    marginTop: 14,
    backgroundColor: colors.surface,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    padding: 14,
  },
  exportHeader: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 4 },
  exportTitle: { color: colors.textPrimary, fontWeight: "900", fontSize: 13, letterSpacing: 1 },
  exportSub: { color: colors.textSecondary, fontSize: 11, marginBottom: 10 },
  freeLockBadge: {
    marginLeft: "auto",
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    backgroundColor: "#3a1010",
    borderColor: colors.anomaly,
    borderWidth: 1,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
  },
  freeLockBadgeText: {
    color: colors.anomaly,
    fontSize: 10,
    fontWeight: "900",
    letterSpacing: 0.6,
  },
  exportGrid: { flexDirection: "row", flexWrap: "wrap", gap: 10 },
  footer: {
    position: "absolute",
    bottom: 0,
    left: 0,
    right: 0,
    padding: 16,
    paddingBottom: 24,
    backgroundColor: colors.bg,
    borderTopWidth: 1,
    borderTopColor: colors.borderSubtle,
    gap: 10,
  },
  btn: {
    minHeight: 64,
    borderRadius: 8,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
  },
  btnPrimary: { backgroundColor: colors.primary },
  btnPrimaryText: { color: "#000", fontWeight: "900", fontSize: 15, letterSpacing: 1 },
  // 🆕 V3 — Bouton "AJOUTER" compact (cahier des charges 09/06/2026 : libérer
  //    de l'espace en bas d'écran pour gagner en densité d'affichage).
  btnPrimaryCompact: {
    backgroundColor: colors.primary,
    paddingHorizontal: 14,
    paddingVertical: 10,
    alignSelf: "flex-end",
    minWidth: 140,
    minHeight: 44,
  },
  btnPrimaryTextCompact: { color: "#000", fontWeight: "900", fontSize: 13, letterSpacing: 0.8 },
  btnSecondary: { borderWidth: 2, borderColor: colors.borderStrong },
  btnSecondaryText: { color: colors.textPrimary, fontWeight: "800", letterSpacing: 1 },
  // 🆕 V3 — Barre d'actions UNIFORME (cahier 10/06/2026) :
  //    3 boutons identiques (même taille) sur une seule ligne pour
  //    libérer l'espace au profit de la liste d'ouvertures.
  actionGrid: {
    flexDirection: "row",
    gap: 8,
    alignItems: "stretch",
    // 🆕 Android — empêche le wrap en 2 lignes des boutons sur petits écrans
    flexWrap: "nowrap",
  },
  gridBtn: {
    flex: 1,
    flexShrink: 1,
    // Permet aux boutons de se contracter sans wrap sur Android petit écran
    minWidth: 0,
    minHeight: 56,
    borderRadius: 8,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 6,
    gap: 6,
  },
  gridBtnPrimary: { backgroundColor: colors.primary },
  gridBtnTextPrimary: {
    color: "#000",
    fontWeight: "900",
    fontSize: 12,
    letterSpacing: 0.6,
  },
  gridBtnSecondary: {
    borderWidth: 2,
    borderColor: colors.borderStrong,
    backgroundColor: colors.surface,
  },
  gridBtnTextSecondary: {
    color: colors.textPrimary,
    fontWeight: "800",
    fontSize: 12,
    letterSpacing: 0.6,
  },
  // Modales (overlay sombre + carte centrée) — utilisés par AFFECTER,
  // ENVOYER À UN COMMERCIAL et MODIFIER LE CHANTIER.
  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.78)",
    justifyContent: "center",
    paddingHorizontal: 16,
  },
  modalCard: {
    backgroundColor: colors.surface,
    borderRadius: 14,
    padding: 18,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
  },
  modalTitle: {
    color: colors.textPrimary,
    fontSize: 16,
    fontWeight: "900",
    letterSpacing: 1.2,
    textAlign: "center",
    marginBottom: 4,
  },
  modalSub: {
    color: colors.textSecondary,
    fontSize: 13,
    textAlign: "center",
    marginBottom: 12,
    lineHeight: 18,
  },
  assignItem: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    paddingVertical: 12,
    paddingHorizontal: 14,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    marginBottom: 8,
    backgroundColor: "#141417",
  },
  // Ligne d'affichage de l'affectation (chantier déjà affecté)
  assignRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    backgroundColor: "#141417",
    marginTop: 8,
  },
  assignLabel: {
    color: colors.textSecondary,
    fontSize: 10,
    fontWeight: "700",
    letterSpacing: 0.8,
    textTransform: "uppercase",
  },
  assignValue: {
    color: colors.textPrimary,
    fontSize: 14,
    fontWeight: "700",
    marginTop: 2,
  },
  // Pill "RÉAFFECTER" à droite de la ligne (visible si admin)
  assignChangePill: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 5,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: colors.primary,
    backgroundColor: "rgba(245, 158, 11, 0.12)",
  },
  assignChangeText: {
    color: colors.primary,
    fontSize: 10,
    fontWeight: "900",
    letterSpacing: 0.6,
  },
});const validateStyles = StyleSheet.create({
  btnGo: {
    marginTop: 14,
    minHeight: 58,
    borderRadius: 12,
    backgroundColor: "#22C55E",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
    paddingHorizontal: 14,
  },
  btnGoText: {
    color: "#000",
    fontWeight: "900",
    fontSize: 13,
    letterSpacing: 0.8,
    textAlign: "center",
    flexShrink: 1,
  },
  waitCard: {
    marginTop: 14,
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 10,
    backgroundColor: "#2a1c08",
    borderColor: colors.warning,
    borderWidth: 1,
    borderRadius: 12,
    padding: 14,
  },
  waitTitle: {
    color: colors.warning,
    fontWeight: "900",
    fontSize: 12,
    letterSpacing: 0.6,
  },
  waitBody: {
    color: colors.textPrimary,
    fontSize: 12,
    lineHeight: 17,
    marginTop: 4,
  },
  btnOverride: {
    marginTop: 14,
    minHeight: 54,
    borderRadius: 12,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
    paddingHorizontal: 14,
    backgroundColor: "#2a1c08",
    borderColor: colors.warning,
    borderWidth: 2,
  },
  btnOverrideText: {
    color: colors.warning,
    fontWeight: "900",
    fontSize: 12,
    letterSpacing: 0.7,
    textAlign: "center",
    flexShrink: 1,
  },
  overrideActive: {
    marginTop: 14,
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    backgroundColor: "#3a1010",
    borderColor: colors.anomaly,
    borderWidth: 1,
    borderRadius: 12,
    padding: 12,
  },
  overrideActiveText: {
    color: colors.textPrimary,
    fontSize: 12,
    fontWeight: "700",
    flex: 1,
  },
  lockBackBtn: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: colors.borderStrong,
    backgroundColor: colors.surface,
  },
  lockBackText: {
    color: colors.textPrimary,
    fontSize: 10,
    fontWeight: "900",
    letterSpacing: 0.6,
  },
  fabLockCard: {
    marginTop: 14,
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 10,
    backgroundColor: colors.surface,
    borderColor: colors.borderStrong,
    borderWidth: 1,
    borderRadius: 12,
    padding: 14,
  },
  fabLockTitle: {
    color: colors.primary,
    fontWeight: "900",
    fontSize: 12,
    letterSpacing: 0.6,
  },
  fabLockBody: {
    color: colors.textPrimary,
    fontSize: 12,
    lineHeight: 17,
    marginTop: 4,
  },
  archivedLockCard: {
    marginTop: 14,
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 10,
    backgroundColor: "#0b2418",
    borderColor: colors.success,
    borderWidth: 1,
    borderRadius: 12,
    padding: 14,
  },
  archivedLockTitle: {
    color: colors.success,
    fontWeight: "900",
    fontSize: 13,
    letterSpacing: 0.6,
  },
  archivedLockBody: {
    color: colors.textPrimary,
    fontSize: 12,
    lineHeight: 17,
    marginTop: 4,
  },
});

// Styles spécifiques à la modale d'édition du chantier (✏️)
const editStyles = StyleSheet.create({
  label: {
    color: colors.textSecondary,
    fontSize: 11,
    fontWeight: "800",
    letterSpacing: 0.6,
    textTransform: "uppercase",
    marginTop: 10,
    marginBottom: 4,
  },
  input: {
    backgroundColor: "#1a1a1d",
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    paddingHorizontal: 12,
    paddingVertical: Platform.OS === "ios" ? 12 : 10,
    color: colors.textPrimary,
    fontSize: 15,
    minHeight: 44,
  },
  dateBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  dateBtnText: {
    color: colors.textPrimary,
    fontSize: 14,
    flex: 1,
  },
});

