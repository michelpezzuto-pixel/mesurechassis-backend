import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  Image,
  Linking,
  Modal,
  Platform,
  RefreshControl,
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
import { api, buildAuthHeaders, PDF_URL, JSON_URL, XLSX_URL, CSV_URL } from "@/src/services/api";
import { ShapeIcon, blockTypeToShape } from "@/src/components/ShapeIcon";
import { useAuth } from "@/src/context/AuthContext";
import { colors, statusMeta, blockMeta } from "@/src/theme";

type SitePhoto = { uri: string; caption: string };

type Chantier = {
  id: string;
  client_name: string;
  address: string;
  status: string;
  assigned_to?: string | null;
  created_by?: string | null;
  created_at: string;
  site_photos?: SitePhoto[];
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
  const router = useRouter();
  const { user, hasRole, artisanMode, company } = useAuth();
  // 🔒 HARDCODED ROLE GATES (NE PAS passer par `hasRole` qui peut être
  // bypassé par `artisan_mode=true` dans la DB).
  // Ces booléens reflètent STRICTEMENT le rôle réel de l'utilisateur connecté.
  const roleIsAdmin = user?.role === "admin";
  const roleIsCommercial = user?.role === "commercial";
  const roleIsTechnician = user?.role === "technician";
  const canManage = roleIsAdmin || roleIsCommercial;
  // `canMeasure` est défini plus bas après `isSoloArtisan` car en Mode
  // Artisan Solo (1 seul user) ou Mode Artisan activé, l'admin doit pouvoir
  // mesurer comme un technicien.
  const canExportTech = roleIsTechnician || roleIsAdmin;
  // 🚧 BETA GRATUITE : pas de plan Free tant que beta_mode est actif.
  const isFreePlan = !company?.beta_mode && (company?.plan ?? "trial") === "free";
  const showUpgradeLock = () => {
    Alert.alert(
      "🔒 Exports verrouillés",
      "Les exports (PDF, Excel, CSV, JSON) sont réservés aux abonnés Pro. " +
        "Passez en Pro pour débloquer toutes les exportations techniques.",
      [
        { text: "Plus tard", style: "cancel" },
        {
          text: "Voir l'abonnement",
          onPress: () => router.push("/company-profile"),
        },
      ]
    );
  };
  const [chantier, setChantier] = useState<Chantier | null>(null);
  const [mesures, setMesures] = useState<Mesure[]>([]);
  const [users, setUsers] = useState<UserOpt[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [assignOpen, setAssignOpen] = useState(false);
  const [exporting, setExporting] = useState<string | null>(null);
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
  //  - Admin : TOUJOURS — il gère et configure, doit pouvoir mesurer pour
  //    démo, formation, ajustement. Le RBAC reste strict sur la VALIDATION
  //    de la fabrication (seul technicien en mode équipe).
  const canMeasure = roleIsCommercial || roleIsTechnician || roleIsAdmin;
  // 🔒 Qui peut valider le passage en fabrication ?
  // - Mode Solo (teamSize=1) : admin ou technicien
  // - Mode Équipe : SEUL le technicien (jamais commercial, jamais admin)
  // - Tant que `users` n'est pas chargé : pas de bouton (sécurité)
  const canValidateForFab =
    usersLoaded &&
    isAwaitingValidation &&
    (isSoloArtisan
      ? roleIsAdmin || roleIsTechnician
      : roleIsTechnician);
  // Message d'attente : tout le monde sauf le technicien en mode équipe.
  const isWaitingForTech =
    usersLoaded && isAwaitingValidation && !isSoloArtisan && !roleIsTechnician;
  // Verrou fabrication : commercial = read-only strict
  // Tech peut déverrouiller via override exceptionnel
  // Admin (sauf solo) = également read-only
  // 🔒 Chantier TERMINÉ (cloture/livre) = verrou ABSOLU pour tous les rôles
  //    (sauf consultation PDF/CSV/XLSX/JSON qui restent ouverts).
  const canEditMesures = (() => {
    if (isArchived) return false; // Terminé/Clôturé = verrou total
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
      "🔒 Chantier verrouillé",
      "Les mesures ne sont plus modifiables. Veuillez vous référer au PDF d'export.",
      [{ text: "J'ai compris", style: "default" }]
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
      "🛑 Action non autorisée",
      "Ce chantier est verrouillé en fabrication. Seul le technicien peut modifier ces données ou exporter les formats d'atelier.",
      [{ text: "J'ai compris", style: "default" }]
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
    return u?.name || "Opérateur inconnu";
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
      Alert.alert("Erreur", "Impossible de charger le chantier.");
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
      Alert.alert("Erreur", "Affectation impossible.");
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
        "🔒 Suppression bloquée",
        "Les chantiers terminés/livrés ne peuvent être supprimés que par l'administrateur principal (Responsable).",
        [{ text: "J'ai compris", style: "default" }]
      );
      return;
    }
    const msg = `« ${chantier.client_name} » et toutes ses mesures seront supprimés définitivement. Cette action est irréversible.`;
    const doDelete = async () => {
      try {
        await api.delete(`/chantiers/${id}`);
        router.replace("/dashboard");
      } catch (e: any) {
        const reason =
          e?.response?.status === 403
            ? "Vous n'avez pas les droits pour supprimer ce chantier."
            : "Suppression impossible.";
        Alert.alert("Erreur", reason);
      }
    };
    if (Platform.OS === "web") {
      const ok =
        typeof window !== "undefined" &&
        window.confirm(`Supprimer le chantier ?\n\n${msg}`);
      if (ok) doDelete();
      return;
    }
    Alert.alert(
      "Supprimer le chantier ?",
      msg,
      [
        { text: "Annuler", style: "cancel" },
        { text: "Supprimer", style: "destructive", onPress: doDelete },
      ]
    );
  };

  // -------- Site photos anti-litige ---------------------------------------
  const addSitePhoto = async (source: "camera" | "library") => {
    if (!chantier) return;
    const current = chantier.site_photos ?? [];
    if (current.length >= 6) {
      Alert.alert("Limite atteinte", "Maximum 6 photos site (anti-litige).");
      return;
    }
    try {
      const fn = source === "camera"
        ? ImagePicker.requestCameraPermissionsAsync
        : ImagePicker.requestMediaLibraryPermissionsAsync;
      const perm = await fn();
      if (!perm.granted) {
        Alert.alert("Permission refusée", "Activez l'accès dans les réglages.");
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
      Alert.alert("Erreur", "Ajout photo impossible.");
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
    Alert.alert("Supprimer la photo ?", "Cette action est définitive.", [
      { text: "Annuler", style: "cancel" },
      {
        text: "Supprimer",
        style: "destructive",
        onPress: async () => {
          const next = (chantier.site_photos ?? []).filter((_, i) => i !== idx);
          try {
            const r = await api.patch<Chantier>(`/chantiers/${chantier.id}`, { site_photos: next });
            setChantier(r.data);
          } catch {
            Alert.alert("Erreur", "Suppression impossible.");
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
        ? content.slice(0, MAX_BODY) +
          "\n\n[...]\n— Contenu tronqué. Connectez-vous à MesureChâssis sur le web pour récupérer le fichier complet."
        : content;
    const subject = `MesureChâssis — Export ${kind.toUpperCase()} — ${clientName}`;
    const adminEmail = user?.email || ""; // pré-remplit avec l'email du master admin connecté

    Alert.alert(
      `Export ${kind.toUpperCase()} prêt`,
      `Envoyer le fichier ${kind.toUpperCase()} par email à votre bureau ou à un collaborateur ?\n\nAstuce : pour télécharger le fichier brut, utilisez MesureChâssis depuis Safari/Chrome.`,
      [
        { text: "Annuler", style: "cancel" },
        {
          text: "Envoyer par email",
          onPress: async () => {
            const mailtoUrl = `mailto:${adminEmail}?subject=${encodeURIComponent(
              subject
            )}&body=${encodeURIComponent(truncated)}`;
            try {
              const supported = await Linking.canOpenURL(mailtoUrl);
              if (!supported) {
                Alert.alert(
                  "Aucune app Mail détectée",
                  "Veuillez configurer un client mail sur cet appareil (Mail, Gmail, Outlook…) pour utiliser cette option."
                );
                return;
              }
              await Linking.openURL(mailtoUrl);
            } catch (e: any) {
              Alert.alert("Erreur", e?.message || "Impossible d'ouvrir le client mail.");
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

  const downloadExport = async (kind: "pdf" | "xlsx" | "csv" | "json") => {
    if (!chantier) return;
    if (isFreePlan) {
      showUpgradeLock();
      return;
    }
    const urlMap: Record<string, (cid: string) => string> = {
      pdf: PDF_URL, xlsx: XLSX_URL, csv: CSV_URL, json: JSON_URL,
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
        a.download = `MesureChassis_${safe}.${kind}`;
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
              Alert.alert("Téléchargement OK", `Fichier enregistré : ${finalUri}`);
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
              "Export indisponible sur Expo Go",
              `Le téléchargement direct du fichier ${kind.toUpperCase()} n'est pas supporté sur cet appareil. Veuillez utiliser la version web de MesureChâssis (depuis Safari/Chrome) pour télécharger ce format.`,
              [{ text: "OK" }]
            );
          }
        }
      }
    } catch (e: any) {
      if (e?.message === "FREE_PLAN_LOCK") {
        showUpgradeLock();
      } else {
        Alert.alert("Erreur export", e?.message || "Téléchargement impossible.");
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
        "✅ Chantier validé",
        "Le chantier est désormais en fabrication. Les exports techniques (CSV / Excel) sont disponibles."
      );
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      Alert.alert(
        "Erreur",
        typeof detail === "string"
          ? detail
          : "Validation impossible. Vérifiez vos droits."
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
      "Modification exceptionnelle",
      "Voulez-vous temporairement déverrouiller ce chantier ?\n\nCette action accorde un accès édition/suppression temporaire au technicien pour coordination atelier urgente.",
      [
        { text: "Annuler", style: "cancel" },
        {
          text: "Déverrouiller",
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

  return (
    <SafeAreaView style={styles.flex} edges={["bottom"]}>
      <FlatList
        data={mesures}
        keyExtractor={(i) => i.id}
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
                  <Text style={[styles.badgeText, { color: meta.color }]}>{meta.label}</Text>
                </View>
              )}

              <TouchableOpacity
                testID="assign-button"
                onPress={() => canManage && setAssignOpen(true)}
                disabled={!canManage}
                style={[styles.assignRow, !canManage && { opacity: 0.6 }]}
                activeOpacity={0.7}
              >
                <Ionicons name="person-circle-outline" size={18} color={colors.primary} />
                <Text style={styles.assignLabel}>Affecté à :</Text>
                <Text style={styles.assignValue}>
                  {assignedUser ? assignedUser.name : "Personne — affecter"}
                </Text>
                <Ionicons name="chevron-down" size={16} color={colors.textSecondary} style={{ marginLeft: "auto" }} />
              </TouchableOpacity>
            </View>

            <View style={styles.statsRow}>
              <View style={styles.statCard}>
                <Text style={styles.statValue}>{mesures.length}</Text>
                <Text style={styles.statLabel}>Ouvertures</Text>
              </View>
              <View style={styles.statCard}>
                <Text style={styles.statValue}>
                  {mesures.reduce((acc, m) => acc + (m.alerts?.length ?? 0), 0)}
                </Text>
                <Text style={styles.statLabel}>Alertes</Text>
              </View>
            </View>

            <Text style={styles.sectionTitle}>OUVERTURES</Text>
          </View>
        }
        renderItem={({ item, index }) => {
          const block = blockMeta[item.block_type] ?? { label: item.block_type, icon: "square-outline" };
          return (
            <View testID={`mesure-card-${item.id}`} style={styles.mesureCard}>
              <View style={styles.mesureRow}>
                {item.photo_url ? (
                  <Image source={{ uri: item.photo_url }} style={styles.mesureThumb} />
                ) : (
                  <View style={styles.mesureThumbPlaceholder}>
                    <ShapeIcon
                      shape={blockTypeToShape(item.block_type)}
                      size={40}
                      color={colors.textPrimary}
                      strokeWidth={1.8}
                    />
                  </View>
                )}
                <View style={{ flex: 1 }}>
                  <Text style={styles.mesureLabel}>
                    #{index + 1} · {item.label}
                  </Text>
                  <Text style={styles.mesureType}>{block.label}</Text>
                  {item.slope_angle_deg != null && (
                    <Text style={styles.slope}>Pente : {item.slope_angle_deg}°</Text>
                  )}
                </View>
              </View>
              {item.alerts && item.alerts.length > 0 && (
                <View style={styles.alertWrap}>
                  {item.alerts.map((a, i) => (
                    <Text key={i} style={styles.alertText}>
                      {a}
                    </Text>
                  ))}
                </View>
              )}
              {(canEditMesures || showCommercialFabIntercept || showArchivedLockIntercept) && (
                <View style={styles.mesureActions}>
                  <TouchableOpacity
                    testID={`edit-mesure-${item.id}`}
                    onPress={() => {
                      if (showArchivedLockIntercept) {
                        interceptArchivedLock();
                        return;
                      }
                      if (showCommercialFabIntercept) {
                        interceptCommercialFab();
                        return;
                      }
                      router.push(`/chantier/${id}/new-mesure?mesure_id=${item.id}`);
                    }}
                    activeOpacity={0.7}
                    style={styles.mesureEditBtn}
                  >
                    <Ionicons name="create-outline" size={14} color={colors.primary} />
                    <Text style={styles.mesureEditText}>MODIFIER</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    testID={`delete-mesure-${item.id}`}
                    onPress={() => {
                      if (showArchivedLockIntercept) {
                        interceptArchivedLock();
                        return;
                      }
                      if (showCommercialFabIntercept) {
                        interceptCommercialFab();
                        return;
                      }
                      Alert.alert(
                        "Supprimer cette mesure ?",
                        `« ${item.label} » sera définitivement supprimée.`,
                        [
                          { text: "Annuler", style: "cancel" },
                          {
                            text: "Supprimer",
                            style: "destructive",
                            onPress: async () => {
                              try {
                                await api.delete(`/mesures/${item.id}`);
                                fetchAll();
                              } catch {
                                Alert.alert("Erreur", "Suppression impossible.");
                              }
                            },
                          },
                        ]
                      );
                    }}
                    activeOpacity={0.7}
                    style={styles.mesureDelBtn}
                  >
                    <Ionicons name="trash-outline" size={14} color={colors.anomaly} />
                    <Text style={styles.mesureDelText}>SUPPRIMER</Text>
                  </TouchableOpacity>
                </View>
              )}
              {isArchived && (
                <View style={styles.archiveRow}>
                  <Ionicons name="lock-closed" size={12} color={colors.textSecondary} />
                  <Text style={styles.archiveText}>LECTURE SEULE — Chantier archivé</Text>
                </View>
              )}
            </View>
          );
        }}
        contentContainerStyle={{ padding: 16, paddingBottom: 200 }}
        ListEmptyComponent={
          <View style={styles.empty}>
            <Ionicons name="grid-outline" size={48} color={colors.borderStrong} />
            <Text style={styles.emptyText}>Aucune ouverture mesurée</Text>
            {canEditMesures ? (
              <>
                <Text style={styles.emptyHint}>
                  Commencez par ajouter votre première ouverture (Carré /
                  Rectangle, Porte, Trapèze, Triangle, Œil-de-bœuf, Coulissant
                  levant, Porte de garage…)
                </Text>
                <TouchableOpacity
                  testID="empty-add-ouverture-button"
                  onPress={() => router.push(`/chantier/${id}/new-mesure`)}
                  activeOpacity={0.85}
                  style={styles.emptyCta}
                >
                  <Ionicons name="add-circle" size={22} color="#000" />
                  <Text style={styles.emptyCtaText}>
                    AJOUTER UN CHÂSSIS / UNE OUVERTURE
                  </Text>
                </TouchableOpacity>
              </>
            ) : showArchivedLockIntercept ? (
              <Text style={styles.emptyHint}>
                🔒 Chantier verrouillé. Les mesures ne sont plus modifiables.
                Référez-vous au PDF d'export.
              </Text>
            ) : showCommercialFabIntercept ? (
              <Text style={styles.emptyHint}>
                Ce chantier est verrouillé en fabrication. Seul le technicien
                peut ajouter ou modifier les mesures.
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
                <Text style={styles.exportTitle}>PHOTOS SITE (ANTI-LITIGE)</Text>
              </View>
              <Text style={styles.exportSub}>
                Jusqu'à 6 photos avec légende — preuves de l'état existant.
                ({(chantier.site_photos?.length ?? 0)}/6)
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
                      placeholder="Note / Légende de la photo"
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
                      <Text style={photoStyles.delBtnText}>Supprimer</Text>
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
                    <Text style={photoStyles.addBtnText}>Caméra</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    testID="add-site-photo-library"
                    onPress={() => addSitePhoto("library")}
                    activeOpacity={0.7}
                    style={photoStyles.addBtn}
                  >
                    <Ionicons name="images" size={18} color={colors.primary} />
                    <Text style={photoStyles.addBtnText}>Galerie</Text>
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
                        ? "✅ VALIDER ET PUBLIER POUR FABRICATION"
                        : "✅ CLÔTURER ET LANCER LA FABRICATION"}
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
                    EN ATTENTE DE VALIDATION PAR LE TECHNICIEN
                  </Text>
                  <Text style={validateStyles.waitBody}>
                    Seul un technicien peut valider ce chantier pour la
                    fabrication. L'administrateur ne peut pas bypasser cette
                    étape de sécurité.
                  </Text>
                </View>
              </View>
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
                  ⚠️ AUTORISER UNE MODIFICATION EXCEPTIONNELLE
                </Text>
              </TouchableOpacity>
            )}
            {isInFabrication && techOverride && (
              <View style={validateStyles.overrideActive}>
                <Ionicons name="lock-open" size={18} color={colors.anomaly} />
                <Text style={validateStyles.overrideActiveText}>
                  Édition déverrouillée temporairement (override technicien).
                </Text>
                <TouchableOpacity
                  onPress={() => setTechOverride(false)}
                  activeOpacity={0.7}
                  style={validateStyles.lockBackBtn}
                >
                  <Text style={validateStyles.lockBackText}>VERROUILLER</Text>
                </TouchableOpacity>
              </View>
            )}
            {isInFabrication && user?.role !== "technician" && (
              <View style={validateStyles.fabLockCard}>
                <Ionicons name="cog" size={20} color={colors.primary} />
                <View style={{ flex: 1 }}>
                  <Text style={validateStyles.fabLockTitle}>
                    EN FABRICATION — LECTURE SEULE
                  </Text>
                  <Text style={validateStyles.fabLockBody}>
                    {user?.role === "commercial"
                      ? "Les mesures sont figées pour garantir la cohérence avec l'atelier. Contactez le technicien en cas d'urgence."
                      : "Seul le technicien peut modifier exceptionnellement les mesures à ce stade."}
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
                    🔒 CHANTIER VERROUILLÉ
                  </Text>
                  <Text style={validateStyles.archivedLockBody}>
                    Les mesures ne sont plus modifiables. Référez-vous au PDF
                    d'export. Les téléchargements (PDF, CSV, Excel, JSON)
                    restent disponibles ci-dessous.
                  </Text>
                </View>
              </View>
            )}

            {/* === Exports === */}
            {mesures.length > 0 && (
              <View style={styles.exportCard}>
                <View style={styles.exportHeader}>
                  <Ionicons name="download" size={18} color={colors.primary} />
                  <Text style={styles.exportTitle}>EXPORTS</Text>
                  {isFreePlan && (
                    <View style={styles.freeLockBadge}>
                      <Ionicons name="lock-closed" size={11} color={colors.anomaly} />
                      <Text style={styles.freeLockBadgeText}>VERROU FREE</Text>
                    </View>
                  )}
                </View>
                <Text style={styles.exportSub}>
                  {isFreePlan
                    ? "Exports réservés au plan Pro — passez en Pro pour débloquer."
                    : "Document client, fichier fabrication ou intégration logiciel."}
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
                  label="RÉCAPITULATIF PDF"
                  sub="Fiche technique"
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
                      label="EXCEL .xlsx"
                      sub="Tableau atelier"
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
                            "🛑 Export CSV réservé",
                            "L'export CSV est réservé aux Techniciens et Administrateurs. Demandez l'export technique à votre équipe atelier.",
                            [{ text: "OK", style: "default" }]
                          );
                          return;
                        }
                      }
                      downloadExport("csv");
                    }}
                    icon="list"
                    label="CSV"
                    sub="Tabulaire brut"
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
                      label="JSON"
                      sub="Intégration CNC"
                      color="#A855F7"
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
        {chantier.status !== "cloture" && canManage && (
          <TouchableOpacity
            testID="close-project-button"
            onPress={() => router.push(`/chantier/${id}/closure`)}
            style={[styles.btn, styles.btnSecondary]}
            activeOpacity={0.7}
          >
            <Ionicons name="flag-outline" size={20} color={colors.textPrimary} />
            <Text style={styles.btnSecondaryText}>CLÔTURER</Text>
          </TouchableOpacity>
        )}
        {canEditMesures && (
          <TouchableOpacity
            testID="add-mesure-button"
            onPress={() => router.push(`/chantier/${id}/new-mesure`)}
            style={[styles.btn, styles.btnPrimary]}
            activeOpacity={0.85}
          >
            <Ionicons name="add-circle" size={22} color="#000" />
            <Text style={styles.btnPrimaryText}>AJOUTER UNE OUVERTURE</Text>
          </TouchableOpacity>
        )}
        {canEditMesures && chantier?.wall_config?.masonry_type && (
          <TouchableOpacity
            testID="edit-wall-config-button"
            onPress={() => router.push(`/chantier/${id}/new-mesure?edit_wall_config=1`)}
            style={[styles.btn, styles.btnSecondary]}
            activeOpacity={0.85}
          >
            <Ionicons name="construct-outline" size={20} color={colors.primary} />
            <Text style={[styles.btnSecondaryText, { color: colors.primary }]}>
              MODIFIER LA STRUCTURE DU MUR
            </Text>
          </TouchableOpacity>
        )}
      </View>

      <Modal visible={assignOpen} transparent animationType="fade" onRequestClose={() => setAssignOpen(false)}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>AFFECTER LE CHANTIER</Text>
            <Text style={styles.modalSub}>Sélectionnez un membre de l'équipe</Text>
            <FlatList
              data={users}
              keyExtractor={(u) => u.id}
              style={{ maxHeight: 320 }}
              ListHeaderComponent={
                <TouchableOpacity
                  testID="assign-none"
                  onPress={() => assignTo(null)}
                  style={[styles.assignItem, !chantier.assigned_to && styles.assignItemActive]}
                  activeOpacity={0.7}
                >
                  <Ionicons name="close-circle-outline" size={20} color={colors.textSecondary} />
                  <Text style={styles.assignItemText}>Aucune affectation</Text>
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
                      name={
                        item.role === "admin"
                          ? "shield-checkmark"
                          : item.role === "commercial"
                          ? "briefcase"
                          : "construct"
                      }
                      size={20}
                      color={active ? colors.primary : colors.textSecondary}
                    />
                    <View style={{ flex: 1 }}>
                      <Text style={styles.assignItemText}>{item.name}</Text>
                      <Text style={styles.assignItemRole}>{item.role}</Text>
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
              <Text style={styles.btnSecondaryText}>FERMER</Text>
            </TouchableOpacity>
          </View>
        </View>
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
    padding: 12,
    marginBottom: 10,
  },
  mesureRow: { flexDirection: "row", alignItems: "center", gap: 12 },
  mesureThumb: { width: 64, height: 64, borderRadius: 8, backgroundColor: colors.bg },
  mesureThumbPlaceholder: {
    width: 64,
    height: 64,
    borderRadius: 8,
    backgroundColor: colors.bg,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    alignItems: "center",
    justifyContent: "center",
  },
  mesureLabel: { color: colors.textPrimary, fontWeight: "800", fontSize: 15 },
  mesureType: { color: colors.textSecondary, marginTop: 2, fontSize: 13 },
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
  btnSecondary: { borderWidth: 2, borderColor: colors.borderStrong },
  btnSecondaryText: { color: colors.textPrimary, fontWeight: "800", letterSpacing: 1 },
});


const validateStyles = StyleSheet.create({
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
