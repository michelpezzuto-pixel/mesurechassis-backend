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
};

type SpecDraft = {
  id: string;
  chantier_id: string;
  filename: string;
  source: "pdf" | "excel" | "image";
  summary: string;
  items: SpecItem[];
  status: string;
  created_at: string;
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
  const [draft, setDraft] = useState<SpecDraft | null>(null);
  const [items, setItems] = useState<SpecItem[]>([]);
  const [confirming, setConfirming] = useState(false);

  // ───────────────────────────────────────────────────────────────────
  // Upload helpers
  // ───────────────────────────────────────────────────────────────────
  const uploadFile = useCallback(
    async (file: { uri: string; name: string; mimeType?: string }) => {
      if (!id) return;
      setUploading(true);
      try {
        const formData = new FormData();
        // React Native FormData accepte un objet { uri, name, type }
        formData.append("file", {
          uri: file.uri,
          name: file.name,
          type: file.mimeType || "application/octet-stream",
        } as any);
        const res = await api.post<SpecDraft>(
          `/chantiers/${id}/import-spec`,
          formData,
          {
            headers: { "Content-Type": "multipart/form-data" },
            timeout: 120_000, // 2 min : l'IA peut prendre du temps sur gros PDF
          }
        );
        setDraft(res.data);
        setItems(res.data.items || []);
        if ((res.data.items || []).length === 0) {
          Alert.alert(
            t("importSpec.noItemsTitle"),
            res.data.summary ||
              t("importSpec.noItemsMessage"),
          );
        }
      } catch (e: any) {
        const detail = e?.response?.data?.detail;
        const status = e?.response?.status;
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
      }
    },
    [id, t],
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

              <Text style={styles.sectionLabel}>
                {t("importSpec.sourceLabel")}
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
                {t("importSpec.loadingTitle")}
              </Text>
              <Text style={styles.loaderSub}>
                {t("importSpec.loadingSub")}
              </Text>
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
