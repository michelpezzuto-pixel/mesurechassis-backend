/**
 * 📋 Import Cahier des Charges (Build 11+ — juin 2026)
 *
 * Écran de import + preview pour un chantier donné. Workflow :
 *   1. L'utilisateur choisit un fichier (PDF / Excel / Photo)
 *   2. Upload → backend → Gemini 2.5 Flash analyse → liste de châssis
 *   3. Preview éditable (label, dims, type, quantité, notes)
 *   4. Validation → création des mesures pré-remplies
 *
 * Stratégie UX :
 *   - Choix du type de source via 3 gros boutons tactiles (44pt+ touch).
 *   - Loader pleine page pendant l'analyse IA (peut prendre 5-30s).
 *   - Tableau d'items éditables avec swipe-to-delete.
 *   - CTA "Valider l'import" toujours visible (bottom safe area).
 *
 * Paywall :
 *   - En BETA_MODE backend, accessible à tous (rien à faire côté UI).
 *   - Si 402 paywall → on affiche un encart explicatif (sans prix sur iOS).
 */
import { Ionicons } from "@expo/vector-icons";
import * as DocumentPicker from "expo-document-picker";
import * as ImagePicker from "expo-image-picker";
import { useLocalSearchParams, useRouter } from "expo-router";
import React, { useCallback, useMemo, useState } from "react";
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
import { SafeAreaView, useSafeAreaInsets } from "react-native-safe-area-context";

import { api } from "@/src/services/api";
import { colors } from "@/src/theme";
import { useT } from "@/src/utils/useT";

// Alias compatibles avec le thème central
const C = {
  ...colors,
  cardBg: colors.surface,
  textMuted: colors.placeholder,
  border: colors.borderSubtle,
};

// ─────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────
type BlockType = "standard" | "coulissant" | "porte" | "trapeze";

type SpecItem = {
  label: string;
  block_type: BlockType;
  width_mm: number;
  height_mm: number;
  quantity: number;
  notes: string;
  // 🆕 P2 — Specs techniques exhaustives (extraites du CDC, jamais perdues)
  reference?: string;
  location?: string;
  material?: string;
  color_ral?: string;
  glazing?: string;
  uw?: string;
  ug?: string;
  rw?: string;
  opening_type?: string;
  opening_direction?: string;
  security?: string;
  hardware?: string;
  accessories?: string;
  extra?: string;
};

type ProjectSpecs = {
  client?: string;
  address?: string;
  general_norms?: string;
  deadlines?: string;
  warranty?: string;
  payment?: string;
  other?: string;
};

type SpecDraft = {
  id: string;
  chantier_id: string;
  filename: string;
  source: "pdf" | "excel" | "image";
  summary: string;
  items: SpecItem[];
  project_specs?: ProjectSpecs | null;
  status: "processing" | "pending" | "imported" | "rejected" | "failed";
  created_at: string;
  error_message?: string | null;
};

const BLOCK_OPTIONS: { value: BlockType; label: string; icon: string }[] = [
  { value: "standard", label: "Fenêtre", icon: "square-outline" },
  { value: "coulissant", label: "Coulissant", icon: "swap-horizontal-outline" },
  { value: "porte", label: "Porte", icon: "log-out-outline" },
  { value: "trapeze", label: "Trapèze", icon: "triangle-outline" },
];

// ─────────────────────────────────────────────────────────────────────
// Écran
// ─────────────────────────────────────────────────────────────────────
export default function ImportSpecScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { t } = useT();

  const [uploading, setUploading] = useState(false);
  // 🆕 Progression du chunked upload : { current: N, total: M } ou null
  const [uploadProgress, setUploadProgress] = useState<{ current: number; total: number } | null>(null);
  const [draft, setDraft] = useState<SpecDraft | null>(null);
  const [items, setItems] = useState<SpecItem[]>([]);
  const [confirming, setConfirming] = useState(false);
  const [checkingExisting, setCheckingExisting] = useState(true);
  const [pendingDrafts, setPendingDrafts] = useState<SpecDraft[]>([]);

  // ───────────────────────────────────────────────────────────────────
  // Au montage : récupère TOUS les drafts pending existants. Si l'upload
  // précédent a Cloudflare-timeout côté client mais que le backend a
  // réussi, on peut récupérer les résultats stockés en base.
  // ───────────────────────────────────────────────────────────────────
  const refreshDrafts = useCallback(async () => {
    if (!id) return;
    try {
      const r = await api.get<SpecDraft[]>(`/chantiers/${id}/spec-drafts`);
      const found = (r.data || []).filter(
        (d) => d.status === "pending" || d.status === "processing",
      );
      setPendingDrafts(found);
      console.log(
        "[import-spec] Drafts trouvés :",
        found.length,
        found.map((d) => `${d.id.slice(0, 8)}…(${d.status},${d.items.length})`),
      );
    } catch (e: any) {
      console.warn("[import-spec] refresh drafts failed:", e?.message);
    }
  }, [id]);

  React.useEffect(() => {
    if (!id) {
      setCheckingExisting(false);
      return;
    }
    (async () => {
      await refreshDrafts();
      setCheckingExisting(false);
    })();
  }, [id, refreshDrafts]);

  // Bouton "Ouvrir cet import" — bascule un draft en mode preview
  const openExistingDraft = useCallback(
    async (d: SpecDraft) => {
      let finalDraft = d;
      if (d.status === "processing") {
        setUploading(true);
        try {
          finalDraft = await pollDraftUntilReady(d.id);
        } catch (e: any) {
          Alert.alert(t("common.error"), e?.message || "Polling échoué");
          setUploading(false);
          return;
        }
        setUploading(false);
      }
      setDraft(finalDraft);
      setItems(finalDraft.items || []);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [t],
  );

  // ───────────────────────────────────────────────────────────────────
  // Upload helpers
  // ───────────────────────────────────────────────────────────────────
  // ───────────────────────────────────────────────────────────────────
  // Polling : appelle /spec-drafts/{id} jusqu'à status final (pending|failed)
  //   - Tente toutes les 3 secondes
  //   - Max 60 essais soit 3 minutes (timeout final)
  //   - Évite tout timeout Cloudflare car chaque requête est < 5 sec
  // ───────────────────────────────────────────────────────────────────
  const pollDraftUntilReady = useCallback(
    async (draftId: string): Promise<SpecDraft> => {
      const MAX_TRIES = 60;
      const INTERVAL_MS = 3000;
      for (let i = 0; i < MAX_TRIES; i++) {
        await new Promise((resolve) => setTimeout(resolve, INTERVAL_MS));
        try {
          const r = await api.get<SpecDraft>(`/spec-drafts/${draftId}`);
          const d = r.data;
          if (d.status !== "processing") {
            console.log(
              `[import-spec] poll done in ${i + 1} tries (${(i + 1) * INTERVAL_MS / 1000}s) — status=${d.status}`,
            );
            return d;
          }
        } catch (e: any) {
          // Si 404 etc, on remonte immédiatement
          if (e?.response?.status === 404) {
            throw new Error("Brouillon introuvable côté serveur");
          }
          // Erreur réseau temporaire → on retente
          console.warn("[import-spec] poll error, retry…", e?.message);
        }
      }
      throw new Error(
        "L'analyse prend plus de 3 minutes. Réessayez avec un document plus petit ou contactez le support.",
      );
    },
    [],
  );

  const uploadFile = useCallback(
    async (file: { uri: string; name: string; mimeType?: string }) => {
      if (!id) return;
      setUploading(true);
      try {
        // ────────────────────────────────────────────────────────────
        // 🔧 Stratégie d'upload (juil. 2026 fix — "Fichier vide" iOS) :
        //   • Sur WEB : lecture Blob via fetch(uri) → Blob → FormData
        //   • Sur NATIF (iOS/Android) : envoi direct { uri, name, type }
        //     dans FormData. React Native native module lit le fichier
        //     lui-même sans passer par fetch() qui retourne parfois un
        //     Blob de 0 bytes sur iOS avec des URI file:// et content://.
        //   • Chunked (>1.5 Mo) : garde Blob + slice (natif : fallback
        //     via fetch avec retry si taille 0).
        // ────────────────────────────────────────────────────────────
        console.log(
          "[import-spec] upload",
          { platform: Platform.OS, name: file.name, mime: file.mimeType, uri: file.uri.slice(0, 40) },
        );

        const isWeb = Platform.OS === "web";
        let fileBlob: Blob | null = null;
        let totalSize = 0;

        // Sur natif, on essaie de lire le blob juste pour connaître la
        // taille (chunked ou pas), mais si le blob est 0 bytes on utilise
        // la méthode RN native directement.
        try {
          const resp = await fetch(file.uri);
          if (resp.ok) {
            fileBlob = await resp.blob();
            if (!fileBlob.type && file.mimeType) {
              fileBlob = new Blob([await fileBlob.arrayBuffer()], { type: file.mimeType });
            }
            totalSize = fileBlob.size;
          }
        } catch (readErr: any) {
          console.warn("[import-spec] fetch(uri) échoué :", readErr?.message);
        }

        console.log(
          "[import-spec] blob read →",
          totalSize,
          "bytes,",
          fileBlob?.type || "n/a",
        );

        // 🆕 Fix "Fichier vide" iOS : si taille inconnue ou 0 sur natif,
        // on passe forcément par l'upload direct URI React Native
        // (limité aux fichiers < 1.5 Mo, la grande majorité des cahiers
        // des charges PDF).
        const CHUNK_THRESHOLD = 1.5 * 1024 * 1024;
        const CHUNK_SIZE = 1024 * 1024;
        const useRnDirectUpload = !isWeb && (totalSize === 0 || !fileBlob);

        let draftData: SpecDraft;

        if (useRnDirectUpload) {
          // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
          // 📱 UPLOAD NATIF RN — { uri, name, type } directement
          // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
          console.log("[import-spec] Native RN direct upload (fix Blob vide iOS)");
          const formData = new FormData();
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          formData.append("file", {
            uri: file.uri,
            name: file.name || "document.pdf",
            type: file.mimeType || "application/pdf",
          } as any);
          const res = await api.post<SpecDraft>(
            `/chantiers/${id}/import-spec`,
            formData,
            {
              timeout: 120_000,
              headers: { "Content-Type": "multipart/form-data" },
            },
          );
          draftData = res.data;
        } else if (totalSize > CHUNK_THRESHOLD && fileBlob) {
          // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
          // 📦 CHUNKED UPLOAD — Découpage en chunks de 1 Mo
          // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
          const totalChunks = Math.ceil(totalSize / CHUNK_SIZE);
          console.log(`[import-spec] CHUNKED mode: ${totalChunks} chunks de ${CHUNK_SIZE / 1024} Ko`);

          const initRes = await api.post<{ upload_id: string; chunk_size: number }>(
            `/chantiers/${id}/import-spec/chunked/init`,
            {
              filename: file.name,
              mime_type: file.mimeType || fileBlob.type || "application/octet-stream",
              total_size: totalSize,
              total_chunks: totalChunks,
            },
            { timeout: 15_000 },
          );
          const uploadId = initRes.data.upload_id;

          for (let i = 0; i < totalChunks; i++) {
            const start = i * CHUNK_SIZE;
            const end = Math.min(start + CHUNK_SIZE, totalSize);
            const chunk = fileBlob.slice(start, end);
            setUploadProgress({ current: i + 1, total: totalChunks });

            const fd = new FormData();
            fd.append("chunk_index", String(i));
            fd.append("file", chunk, `chunk_${i}`);

            let lastErr: any = null;
            for (let attempt = 0; attempt < 2; attempt++) {
              try {
                await api.post(
                  `/chantiers/${id}/import-spec/chunked/${uploadId}/chunk`,
                  fd,
                  { timeout: 30_000 },
                );
                lastErr = null;
                break;
              } catch (e: any) {
                lastErr = e;
                await new Promise((r) => setTimeout(r, 1500));
              }
            }
            if (lastErr) throw lastErr;
          }

          setUploadProgress(null);
          const completeRes = await api.post<SpecDraft>(
            `/chantiers/${id}/import-spec/chunked/${uploadId}/complete`,
            {},
            { timeout: 30_000 },
          );
          draftData = completeRes.data;
        } else if (fileBlob) {
          // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
          // 🚀 UPLOAD CLASSIQUE WEB — 1 seule requête (Blob)
          // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
          const formData = new FormData();
          formData.append("file", fileBlob, file.name);
          const res = await api.post<SpecDraft>(
            `/chantiers/${id}/import-spec`,
            formData,
            { timeout: 120_000 },
          );
          draftData = res.data;
        } else {
          throw new Error(
            "Impossible de lire le fichier. Réessayez ou choisissez un autre document.",
          );
        }

        // Poll jusqu'à statut final (commun aux 2 modes)
        if (draftData.status === "processing") {
          draftData = await pollDraftUntilReady(draftData.id);
        }

        if (draftData.status === "failed") {
          throw new Error(
            draftData.error_message ||
              "L'analyse IA n'a pas abouti. Réessayez ou utilisez un autre fichier.",
          );
        }

        const created = (draftData as any).mesures_created ?? draftData.items.length;
        Alert.alert(
          "✅ Import réussi",
          `${created} châssis ont été ajoutés à votre chantier avec leurs mesures théoriques. Vous pouvez maintenant les ouvrir et valider sur place.`,
          [
            {
              text: "Voir mon chantier",
              onPress: () => router.replace(`/chantier/${id}`),
            },
          ],
        );
      } catch (e: any) {
        const detail = e?.response?.data?.detail;
        const status = e?.response?.status;
        // 🆘 PLAN B : si réseau / 502, on tente de récupérer le dernier draft pending
        const isNetworkOrTimeout =
          !status ||
          status === 502 ||
          status === 503 ||
          status === 504 ||
          status === 524 ||
          /network|timeout/i.test(e?.message || "");

        if (isNetworkOrTimeout && id) {
          console.warn(
            "[import-spec] Réseau échoué → tentative de récupération du draft...",
          );
          try {
            const recovery = await api.get<SpecDraft[]>(
              `/chantiers/${id}/spec-drafts`,
            );
            const latest = (recovery.data || []).find(
              (d) => d.status === "pending" || d.status === "processing",
            );
            if (latest) {
              const finalDraft =
                latest.status === "processing"
                  ? await pollDraftUntilReady(latest.id)
                  : latest;
              if (finalDraft.status === "pending") {
                setDraft(finalDraft);
                setItems(finalDraft.items || []);
                return;
              }
            }
          } catch (recoveryErr: any) {
            console.warn(
              "[import-spec] Recovery a échoué :",
              recoveryErr?.message,
            );
          }
        }

        let message = t("importSpec.uploadError");
        if (status === 402 && detail?.message) {
          message = detail.message;
        } else if (typeof detail === "string") {
          message = detail;
        } else if (detail?.message) {
          message = detail.message;
        } else if (e?.message) {
          message = e.message;
        }
        Alert.alert(t("common.error"), message);
      } finally {
        setUploading(false);
        setUploadProgress(null);
      }
    },
    [id, t, pollDraftUntilReady, router],
  );

  const pickPdfOrExcel = useCallback(async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: [
          "application/pdf",
          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
          "application/vnd.ms-excel",
        ],
        copyToCacheDirectory: true,
        multiple: false,
      });
      if (result.canceled || !result.assets?.[0]) return;
      const asset = result.assets[0];
      await uploadFile({
        uri: asset.uri,
        name: asset.name || "document",
        mimeType: asset.mimeType || undefined,
      });
    } catch (e: any) {
      Alert.alert(t("common.error"), e?.message || "Erreur sélection fichier");
    }
  }, [uploadFile, t]);

  const pickImage = useCallback(
    async (source: "camera" | "gallery") => {
      try {
        const perm =
          source === "camera"
            ? await ImagePicker.requestCameraPermissionsAsync()
            : await ImagePicker.requestMediaLibraryPermissionsAsync();
        if (!perm.granted) {
          Alert.alert(
            t("importSpec.permTitle"),
            t("importSpec.permMessage"),
          );
          return;
        }
        const launcher =
          source === "camera"
            ? ImagePicker.launchCameraAsync
            : ImagePicker.launchImageLibraryAsync;
        const result = await launcher({
          mediaTypes: ImagePicker.MediaTypeOptions.Images,
          quality: 0.85,
          allowsEditing: false,
        });
        if (result.canceled || !result.assets?.[0]) return;
        const asset = result.assets[0];
        await uploadFile({
          uri: asset.uri,
          name: asset.fileName || `photo_${Date.now()}.jpg`,
          mimeType: asset.mimeType || "image/jpeg",
        });
      } catch (e: any) {
        Alert.alert(t("common.error"), e?.message || "Erreur photo");
      }
    },
    [uploadFile, t],
  );

  // ───────────────────────────────────────────────────────────────────
  // Édition des items
  // ───────────────────────────────────────────────────────────────────
  const updateItem = useCallback(
    (idx: number, patch: Partial<SpecItem>) => {
      setItems((prev) =>
        prev.map((it, i) => (i === idx ? { ...it, ...patch } : it)),
      );
    },
    [],
  );

  const removeItem = useCallback((idx: number) => {
    setItems((prev) => prev.filter((_, i) => i !== idx));
  }, []);

  const addEmptyItem = useCallback(() => {
    setItems((prev) => [
      ...prev,
      {
        label: "",
        block_type: "standard",
        width_mm: 0,
        height_mm: 0,
        quantity: 1,
        notes: "",
      },
    ]);
  }, []);

  const totalOpenings = useMemo(
    () => items.reduce((sum, it) => sum + Math.max(1, it.quantity || 1), 0),
    [items],
  );

  // ───────────────────────────────────────────────────────────────────
  // Validation
  // ───────────────────────────────────────────────────────────────────
  const confirmImport = useCallback(async () => {
    if (!draft || items.length === 0) return;
    // Valide : tous les items doivent avoir un label
    const invalid = items.find((it) => !it.label.trim());
    if (invalid) {
      Alert.alert(
        t("common.error"),
        t("importSpec.invalidLabelMessage"),
      );
      return;
    }
    Alert.alert(
      t("importSpec.confirmTitle"),
      t("importSpec.confirmMessage", { count: totalOpenings }),
      [
        { text: t("common.cancel"), style: "cancel" },
        {
          text: t("importSpec.confirmCta"),
          style: "default",
          onPress: async () => {
            setConfirming(true);
            try {
              const res = await api.post(
                `/spec-drafts/${draft.id}/confirm`,
                { items },
              );
              const created = res.data?.mesures_created || 0;
              Alert.alert(
                t("importSpec.successTitle"),
                t("importSpec.successMessage", { count: created }),
                [
                  {
                    text: t("common.ok"),
                    onPress: () => router.replace(`/chantier/${id}`),
                  },
                ],
              );
            } catch (e: any) {
              const detail = e?.response?.data?.detail;
              const message =
                typeof detail === "string"
                  ? detail
                  : detail?.message || e?.message || t("importSpec.confirmError");
              Alert.alert(t("common.error"), message);
            } finally {
              setConfirming(false);
            }
          },
        },
      ],
    );
  }, [draft, items, id, router, totalOpenings, t]);

  const cancelDraft = useCallback(async () => {
    if (!draft) {
      router.back();
      return;
    }
    Alert.alert(
      t("importSpec.cancelTitle"),
      t("importSpec.cancelMessage"),
      [
        { text: t("common.cancel"), style: "cancel" },
        {
          text: t("importSpec.cancelConfirm"),
          style: "destructive",
          onPress: async () => {
            try {
              await api.post(`/spec-drafts/${draft.id}/reject`);
            } catch {
              /* silent */
            }
            setDraft(null);
            setItems([]);
            router.back();
          },
        },
      ],
    );
  }, [draft, router, t]);

  // ───────────────────────────────────────────────────────────────────
  // RENDU
  // ───────────────────────────────────────────────────────────────────
  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        keyboardVerticalOffset={Platform.OS === "ios" ? 0 : 0}
      >
        {/* HEADER */}
        <View style={styles.header}>
          <TouchableOpacity
            onPress={() => (draft ? cancelDraft() : router.back())}
            style={styles.backBtn}
            hitSlop={10}
          >
            <Ionicons name="arrow-back" size={24} color={C.textPrimary} />
          </TouchableOpacity>
          <Text style={styles.headerTitle} numberOfLines={1}>
            {t("importSpec.title")}
          </Text>
          <View style={{ width: 32 }} />
        </View>

        <ScrollView
          contentContainerStyle={{
            paddingBottom: 120 + insets.bottom,
            paddingHorizontal: 16,
          }}
          showsVerticalScrollIndicator={false}
        >
          {/* PHASE 1 : Choix de la source (avant upload) */}
          {!draft && !uploading && (
            <>
              <View style={styles.heroCard}>
                <Ionicons
                  name="document-text-outline"
                  size={42}
                  color={C.primary}
                />
                <Text style={styles.heroTitle}>{t("importSpec.heroTitle")}</Text>
                <Text style={styles.heroSub}>{t("importSpec.heroSub")}</Text>
              </View>

              {/* 🆕 Encart "Imports déjà analysés" — très visible */}
              {pendingDrafts.length > 0 && (
                <View style={styles.pendingCard}>
                  <View style={styles.pendingHeader}>
                    <Ionicons name="checkmark-circle" size={20} color="#10B981" />
                    <Text style={styles.pendingTitle}>
                      {pendingDrafts.length === 1
                        ? `1 import déjà analysé par l'IA`
                        : `${pendingDrafts.length} imports déjà analysés par l'IA`}
                    </Text>
                  </View>
                  <Text style={styles.pendingSub}>
                    Cliquez pour voir les châssis détectés et les valider.
                  </Text>
                  {pendingDrafts.slice(0, 3).map((d) => {
                    const totalCount = (d.items || []).reduce(
                      (sum, it) => sum + Math.max(1, it.quantity || 1),
                      0,
                    );
                    return (
                      <TouchableOpacity
                        key={d.id}
                        style={styles.pendingItem}
                        onPress={() => openExistingDraft(d)}
                        activeOpacity={0.8}
                      >
                        <View style={{ flex: 1 }}>
                          <Text style={styles.pendingItemName} numberOfLines={1}>
                            📎 {d.filename}
                          </Text>
                          <Text style={styles.pendingItemMeta}>
                            {d.items.length} type(s) — {totalCount} châssis détectés
                          </Text>
                        </View>
                        <Ionicons
                          name="arrow-forward-circle"
                          size={26}
                          color={C.primary}
                        />
                      </TouchableOpacity>
                    );
                  })}
                </View>
              )}

              <Text style={styles.sectionLabel}>
                {pendingDrafts.length > 0
                  ? "Ou importez un NOUVEAU document"
                  : t("importSpec.sourceLabel")}
              </Text>

              <SourceButton
                icon="document-attach"
                color="#EF4444"
                title={t("importSpec.sourcePdf")}
                subtitle={t("importSpec.sourcePdfSub")}
                onPress={pickPdfOrExcel}
              />
              <SourceButton
                icon="grid"
                color="#10B981"
                title={t("importSpec.sourceExcel")}
                subtitle={t("importSpec.sourceExcelSub")}
                onPress={pickPdfOrExcel}
              />
              <SourceButton
                icon="camera"
                color="#3B82F6"
                title={t("importSpec.sourceCamera")}
                subtitle={t("importSpec.sourceCameraSub")}
                onPress={() => pickImage("camera")}
              />
              <SourceButton
                icon="images"
                color="#8B5CF6"
                title={t("importSpec.sourceGallery")}
                subtitle={t("importSpec.sourceGallerySub")}
                onPress={() => pickImage("gallery")}
              />

              <View style={styles.infoBox}>
                <Ionicons
                  name="information-circle"
                  size={18}
                  color={C.primary}
                />
                <Text style={styles.infoText}>
                  {t("importSpec.infoTip")}
                </Text>
              </View>
            </>
          )}

          {/* PHASE 2 : Loader IA */}
          {uploading && (
            <View style={styles.loaderBox}>
              <ActivityIndicator size="large" color={C.primary} />
              <Text style={styles.loaderTitle}>
                {uploadProgress
                  ? `📦 Envoi sécurisé du document...`
                  : t("importSpec.loadingTitle")}
              </Text>
              <Text style={styles.loaderSub}>
                {uploadProgress
                  ? `Chunk ${uploadProgress.current} / ${uploadProgress.total} envoyé`
                  : t("importSpec.loadingSub")}
              </Text>
              {uploadProgress && (
                <View style={styles.progressBarTrack}>
                  <View
                    style={[
                      styles.progressBarFill,
                      {
                        width: `${(uploadProgress.current / uploadProgress.total) * 100}%`,
                      },
                    ]}
                  />
                </View>
              )}
            </View>
          )}

          {/* PHASE 3 : Preview + édition */}
          {draft && !uploading && (
            <>
              <View style={styles.summaryCard}>
                <View
                  style={{
                    flexDirection: "row",
                    alignItems: "center",
                    gap: 8,
                  }}
                >
                  <Ionicons name="sparkles" size={18} color={C.primary} />
                  <Text style={styles.summaryLabel}>
                    {t("importSpec.aiDetected", {
                      count: items.length,
                      total: totalOpenings,
                    })}
                  </Text>
                </View>
                {!!draft.summary && (
                  <Text style={styles.summaryText}>{draft.summary}</Text>
                )}
                <Text style={styles.summaryFile}>📎 {draft.filename}</Text>
              </View>

              {/* 🆕 P2 — Exigences globales du projet (rien n'est perdu) */}
              {(() => {
                const ps = draft.project_specs || {};
                const rows: { label: string; value?: string }[] = [
                  { label: "Client", value: ps.client },
                  { label: "Adresse chantier", value: ps.address },
                  { label: "Normes / labels", value: ps.general_norms },
                  { label: "Délais / dates", value: ps.deadlines },
                  { label: "Garantie", value: ps.warranty },
                  { label: "Paiement", value: ps.payment },
                  { label: "Autres exigences", value: ps.other },
                ].filter((r) => !!(r.value && r.value.trim()));
                if (rows.length === 0) return null;
                return (
                  <View style={styles.projectCard}>
                    <View style={styles.projectHeader}>
                      <Ionicons name="document-text" size={16} color={C.primary} />
                      <Text style={styles.projectTitle}>
                        Exigences du cahier des charges
                      </Text>
                    </View>
                    {rows.map((r) => (
                      <View key={r.label} style={styles.projectRow}>
                        <Text style={styles.projectRowLabel}>{r.label}</Text>
                        <Text style={styles.projectRowValue}>{r.value}</Text>
                      </View>
                    ))}
                  </View>
                );
              })()}

              {items.map((item, idx) => (
                <ItemEditor
                  key={`${idx}-${item.label}`}
                  item={item}
                  onChange={(patch) => updateItem(idx, patch)}
                  onDelete={() => removeItem(idx)}
                />
              ))}

              <TouchableOpacity
                style={styles.addItemBtn}
                onPress={addEmptyItem}
                activeOpacity={0.8}
              >
                <Ionicons name="add-circle" size={22} color={C.primary} />
                <Text style={styles.addItemText}>
                  {t("importSpec.addItem")}
                </Text>
              </TouchableOpacity>
            </>
          )}
        </ScrollView>

        {/* FOOTER : Bouton "Valider l'import" */}
        {draft && !uploading && items.length > 0 && (
          <View
            style={[
              styles.footer,
              { paddingBottom: Math.max(12, insets.bottom) },
            ]}
          >
            <TouchableOpacity
              style={[styles.btn, styles.btnPrimary]}
              onPress={confirmImport}
              disabled={confirming}
              activeOpacity={0.85}
            >
              {confirming ? (
                <ActivityIndicator color="#000" />
              ) : (
                <>
                  <Ionicons name="checkmark-circle" size={20} color="#000" />
                  <Text style={styles.btnPrimaryText}>
                    {t("importSpec.confirmCta")} ({totalOpenings})
                  </Text>
                </>
              )}
            </TouchableOpacity>
          </View>
        )}
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────────────────────────────
function SourceButton({
  icon,
  color,
  title,
  subtitle,
  onPress,
}: {
  icon: keyof typeof Ionicons.glyphMap;
  color: string;
  title: string;
  subtitle: string;
  onPress: () => void;
}) {
  return (
    <TouchableOpacity
      style={styles.sourceBtn}
      onPress={onPress}
      activeOpacity={0.8}
    >
      <View style={[styles.sourceIcon, { backgroundColor: color + "22" }]}>
        <Ionicons name={icon} size={24} color={color} />
      </View>
      <View style={{ flex: 1 }}>
        <Text style={styles.sourceTitle}>{title}</Text>
        <Text style={styles.sourceSub}>{subtitle}</Text>
      </View>
      <Ionicons name="chevron-forward" size={20} color={C.textMuted} />
    </TouchableOpacity>
  );
}

function ItemEditor({
  item,
  onChange,
  onDelete,
}: {
  item: SpecItem;
  onChange: (patch: Partial<SpecItem>) => void;
  onDelete: () => void;
}) {
  const { t } = useT();
  return (
    <View style={styles.itemCard}>
      <View style={styles.itemRow}>
        <TextInput
          value={item.label}
          onChangeText={(v) => onChange({ label: v })}
          placeholder={t("importSpec.itemLabel")}
          placeholderTextColor={C.textMuted}
          style={styles.itemLabelInput}
          maxLength={80}
        />
        <TouchableOpacity onPress={onDelete} hitSlop={10}>
          <Ionicons name="trash-outline" size={20} color="#EF4444" />
        </TouchableOpacity>
      </View>

      {/* Type de châssis - choix par chips */}
      <View style={styles.chipsRow}>
        {BLOCK_OPTIONS.map((opt) => {
          const active = item.block_type === opt.value;
          return (
            <TouchableOpacity
              key={opt.value}
              style={[styles.chip, active && styles.chipActive]}
              onPress={() => onChange({ block_type: opt.value })}
              activeOpacity={0.7}
            >
              <Ionicons
                name={opt.icon as any}
                size={14}
                color={active ? "#000" : C.textPrimary}
              />
              <Text
                style={[styles.chipText, active && styles.chipTextActive]}
              >
                {opt.label}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>

      {/* Dimensions */}
      <View style={styles.dimsRow}>
        <DimField
          label={t("importSpec.width")}
          value={item.width_mm}
          onChange={(v) => onChange({ width_mm: v })}
        />
        <Text style={styles.dimsX}>×</Text>
        <DimField
          label={t("importSpec.height")}
          value={item.height_mm}
          onChange={(v) => onChange({ height_mm: v })}
        />
        <Text style={styles.dimsMm}>mm</Text>
      </View>

      {/* Quantité */}
      <View style={styles.qtyRow}>
        <Text style={styles.qtyLabel}>{t("importSpec.quantity")} :</Text>
        <TouchableOpacity
          onPress={() => onChange({ quantity: Math.max(1, item.quantity - 1) })}
          style={styles.qtyBtn}
          hitSlop={6}
        >
          <Ionicons name="remove" size={18} color={C.textPrimary} />
        </TouchableOpacity>
        <Text style={styles.qtyValue}>{item.quantity}</Text>
        <TouchableOpacity
          onPress={() => onChange({ quantity: Math.min(50, item.quantity + 1) })}
          style={styles.qtyBtn}
          hitSlop={6}
        >
          <Ionicons name="add" size={18} color={C.textPrimary} />
        </TouchableOpacity>
      </View>

      {/* Notes optionnelles */}
      <TextInput
        value={item.notes}
        onChangeText={(v) => onChange({ notes: v })}
        placeholder={t("importSpec.notesPlaceholder")}
        placeholderTextColor={C.textMuted}
        style={styles.notesInput}
        multiline
        maxLength={300}
      />

      {/* 🆕 P2 — Specs techniques détaillées extraites du CDC (lecture seule) */}
      {(() => {
        const specs: { label: string; value?: string }[] = [
          { label: "Repère", value: item.reference },
          { label: "Emplacement", value: item.location },
          { label: "Matériau", value: item.material },
          { label: "Couleur/RAL", value: item.color_ral },
          { label: "Vitrage", value: item.glazing },
          { label: "Uw", value: item.uw },
          { label: "Ug", value: item.ug },
          { label: "Rw", value: item.rw },
          { label: "Ouverture", value: item.opening_type },
          { label: "Sens", value: item.opening_direction },
          { label: "Sécurité", value: item.security },
          { label: "Quincaillerie", value: item.hardware },
          { label: "Accessoires", value: item.accessories },
          { label: "Autre", value: item.extra },
        ].filter((s) => !!(s.value && s.value.trim()));
        if (specs.length === 0) return null;
        return (
          <View style={styles.specDetails}>
            <Text style={styles.specDetailsTitle}>
              📋 Spécifications détectées ({specs.length})
            </Text>
            <View style={styles.specChipsWrap}>
              {specs.map((s) => (
                <View key={s.label} style={styles.specChip}>
                  <Text style={styles.specChipLabel}>{s.label}</Text>
                  <Text style={styles.specChipValue}>{s.value}</Text>
                </View>
              ))}
            </View>
          </View>
        );
      })()}
    </View>
  );
}

function DimField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
}) {
  const [tmp, setTmp] = useState(String(value || ""));
  React.useEffect(() => {
    setTmp(value ? String(value) : "");
  }, [value]);
  return (
    <View style={{ flex: 1 }}>
      <Text style={styles.dimLabel}>{label}</Text>
      <TextInput
        value={tmp}
        onChangeText={(v) => {
          const clean = v.replace(/[^0-9]/g, "");
          setTmp(clean);
          onChange(parseInt(clean || "0", 10));
        }}
        keyboardType="number-pad"
        placeholder="0"
        placeholderTextColor={C.textMuted}
        style={styles.dimInput}
        maxLength={5}
      />
    </View>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Styles
// ─────────────────────────────────────────────────────────────────────
const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: C.bg },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: C.border,
  },
  backBtn: { width: 32, height: 32, justifyContent: "center" },
  headerTitle: {
    fontSize: 17,
    fontWeight: "700",
    color: C.textPrimary,
    flex: 1,
    textAlign: "center",
  },

  heroCard: {
    marginTop: 16,
    backgroundColor: C.cardBg || "#1A1A1A",
    borderRadius: 16,
    padding: 20,
    alignItems: "center",
    borderWidth: 1,
    borderColor: C.border,
  },
  pendingCard: {
    marginTop: 16,
    backgroundColor: "#10B98115",
    borderRadius: 14,
    padding: 14,
    borderWidth: 1,
    borderColor: "#10B98144",
  },
  pendingHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginBottom: 4,
  },
  pendingTitle: {
    fontSize: 14,
    fontWeight: "700",
    color: "#10B981",
    flex: 1,
  },
  pendingSub: {
    fontSize: 12,
    color: C.textSecondary,
    marginBottom: 10,
    lineHeight: 17,
  },
  pendingItem: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    backgroundColor: C.bg,
    borderRadius: 10,
    padding: 12,
    marginTop: 6,
  },
  pendingItemName: {
    fontSize: 14,
    fontWeight: "600",
    color: C.textPrimary,
  },
  pendingItemMeta: {
    fontSize: 11,
    color: C.textMuted,
    marginTop: 2,
  },
  heroTitle: {
    fontSize: 18,
    fontWeight: "700",
    color: C.textPrimary,
    marginTop: 10,
    textAlign: "center",
  },
  heroSub: {
    fontSize: 14,
    color: C.textSecondary,
    marginTop: 6,
    textAlign: "center",
    lineHeight: 20,
  },
  sectionLabel: {
    fontSize: 13,
    color: C.textMuted,
    marginTop: 20,
    marginBottom: 10,
    textTransform: "uppercase",
    fontWeight: "600",
    letterSpacing: 0.5,
  },

  sourceBtn: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: C.cardBg || "#1A1A1A",
    borderRadius: 12,
    padding: 14,
    marginBottom: 10,
    gap: 12,
    borderWidth: 1,
    borderColor: C.border,
  },
  sourceIcon: {
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: "center",
    justifyContent: "center",
  },
  sourceTitle: {
    fontSize: 15,
    fontWeight: "600",
    color: C.textPrimary,
  },
  sourceSub: { fontSize: 12, color: C.textMuted, marginTop: 2 },

  infoBox: {
    flexDirection: "row",
    alignItems: "flex-start",
    backgroundColor: (C.primary || "#FACC15") + "15",
    borderRadius: 10,
    padding: 12,
    marginTop: 20,
    gap: 8,
    borderWidth: 1,
    borderColor: (C.primary || "#FACC15") + "33",
  },
  infoText: {
    flex: 1,
    fontSize: 12,
    color: C.textSecondary,
    lineHeight: 18,
  },

  loaderBox: {
    marginTop: 60,
    alignItems: "center",
    paddingHorizontal: 24,
  },
  loaderTitle: {
    fontSize: 17,
    fontWeight: "600",
    color: C.textPrimary,
    marginTop: 20,
    textAlign: "center",
  },
  loaderSub: {
    fontSize: 13,
    color: C.textMuted,
    marginTop: 8,
    textAlign: "center",
    lineHeight: 19,
  },
  // 🆕 Barre de progression chunked upload
  progressBarTrack: {
    width: "85%",
    height: 8,
    backgroundColor: C.bg,
    borderRadius: 4,
    marginTop: 16,
    overflow: "hidden",
    borderWidth: 1,
    borderColor: C.border,
  },
  progressBarFill: {
    height: "100%",
    backgroundColor: C.primary,
    borderRadius: 4,
  },

  summaryCard: {
    backgroundColor: (C.primary || "#FACC15") + "12",
    borderRadius: 12,
    padding: 14,
    marginTop: 16,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: (C.primary || "#FACC15") + "33",
  },
  summaryLabel: {
    fontSize: 14,
    fontWeight: "700",
    color: C.primary,
  },
  summaryText: {
    fontSize: 13,
    color: C.textSecondary,
    marginTop: 6,
    lineHeight: 18,
  },
  summaryFile: { fontSize: 11, color: C.textMuted, marginTop: 6 },

  // 🆕 P2 — Carte "Exigences du cahier des charges" (specs globales projet)
  projectCard: {
    backgroundColor: C.cardBg || "#1A1A1A",
    borderRadius: 12,
    padding: 14,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: C.border,
  },
  projectHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginBottom: 10,
  },
  projectTitle: {
    fontSize: 14,
    fontWeight: "700",
    color: C.textPrimary,
    flex: 1,
  },
  projectRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 10,
    paddingVertical: 5,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: C.border,
  },
  projectRowLabel: {
    fontSize: 12,
    color: C.textMuted,
    fontWeight: "600",
    width: 110,
  },
  projectRowValue: {
    flex: 1,
    fontSize: 12,
    color: C.textSecondary,
    lineHeight: 17,
  },

  // 🆕 P2 — Specs techniques par châssis (chips lecture seule)
  specDetails: {
    marginTop: 10,
    paddingTop: 10,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: C.border,
  },
  specDetailsTitle: {
    fontSize: 12,
    fontWeight: "700",
    color: C.textSecondary,
    marginBottom: 8,
  },
  specChipsWrap: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 6,
  },
  specChip: {
    backgroundColor: C.bg,
    borderRadius: 8,
    paddingHorizontal: 8,
    paddingVertical: 5,
    borderWidth: 1,
    borderColor: C.border,
    maxWidth: "100%",
  },
  specChipLabel: {
    fontSize: 9,
    color: C.textMuted,
    fontWeight: "600",
    textTransform: "uppercase",
    letterSpacing: 0.3,
  },
  specChipValue: {
    fontSize: 12,
    color: C.textPrimary,
    fontWeight: "500",
    marginTop: 1,
  },

  itemCard: {
    backgroundColor: C.cardBg || "#1A1A1A",
    borderRadius: 12,
    padding: 12,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: C.border,
  },
  itemRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginBottom: 10,
  },
  itemLabelInput: {
    flex: 1,
    fontSize: 15,
    fontWeight: "600",
    color: C.textPrimary,
    paddingVertical: 6,
    paddingHorizontal: 8,
    backgroundColor: C.bg,
    borderRadius: 8,
  },

  chipsRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 6,
    marginBottom: 10,
  },
  chip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 14,
    backgroundColor: C.bg,
    borderWidth: 1,
    borderColor: C.border,
  },
  chipActive: {
    backgroundColor: C.primary,
    borderColor: C.primary,
  },
  chipText: { fontSize: 12, color: C.textPrimary, fontWeight: "500" },
  chipTextActive: { color: "#000", fontWeight: "700" },

  dimsRow: {
    flexDirection: "row",
    alignItems: "flex-end",
    gap: 6,
    marginBottom: 10,
  },
  dimsX: {
    fontSize: 20,
    color: C.textMuted,
    paddingBottom: 6,
  },
  dimsMm: {
    fontSize: 12,
    color: C.textMuted,
    paddingBottom: 10,
    paddingLeft: 4,
  },
  dimLabel: { fontSize: 11, color: C.textMuted, marginBottom: 4 },
  dimInput: {
    backgroundColor: C.bg,
    borderRadius: 8,
    paddingVertical: 8,
    paddingHorizontal: 10,
    fontSize: 15,
    color: C.textPrimary,
    textAlign: "center",
  },

  qtyRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    marginBottom: 10,
  },
  qtyLabel: { fontSize: 13, color: C.textSecondary, flex: 1 },
  qtyBtn: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: C.bg,
    alignItems: "center",
    justifyContent: "center",
  },
  qtyValue: {
    fontSize: 16,
    fontWeight: "700",
    color: C.textPrimary,
    minWidth: 24,
    textAlign: "center",
  },

  notesInput: {
    backgroundColor: C.bg,
    borderRadius: 8,
    paddingVertical: 8,
    paddingHorizontal: 10,
    fontSize: 13,
    color: C.textSecondary,
    minHeight: 40,
    textAlignVertical: "top",
  },

  addItemBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    padding: 14,
    borderRadius: 10,
    borderStyle: "dashed",
    borderWidth: 1,
    borderColor: C.primary,
    marginTop: 6,
    marginBottom: 20,
  },
  addItemText: {
    fontSize: 14,
    fontWeight: "600",
    color: C.primary,
  },

  footer: {
    position: "absolute",
    left: 0,
    right: 0,
    bottom: 0,
    paddingHorizontal: 16,
    paddingTop: 12,
    backgroundColor: C.bg,
    borderTopWidth: 1,
    borderTopColor: C.border,
  },
  btn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    paddingVertical: 14,
    borderRadius: 12,
  },
  btnPrimary: { backgroundColor: C.primary },
  btnPrimaryText: { fontSize: 15, fontWeight: "700", color: "#000" },
});
