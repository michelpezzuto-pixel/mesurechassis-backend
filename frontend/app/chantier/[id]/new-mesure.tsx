import React, { useEffect, useMemo, useState } from "react";
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
import * as ImagePicker from "expo-image-picker";
import { useLocalSearchParams, useRouter } from "expo-router";
import {
  RawBaySchemaRect,
  RawBaySchemaTrapeze,
  WallSection,
} from "@/src/components/WindowSchema";
import { api } from "@/src/services/api";
import { enqueueMesure, isOnline } from "@/src/services/offlineQueue";
import { colors } from "@/src/theme";

type BlockType = "standard" | "coulissant" | "porte" | "trapeze";
type WallType = "ite" | "iti" | "brique_parement" | "crepi_simple";
type DiagState = "auto" | "validated" | "manual";

const BLOCKS: { key: BlockType; letter: string; label: string; icon: keyof typeof Ionicons.glyphMap }[] = [
  { key: "standard", letter: "A", label: "CHÂSSIS STANDARD", icon: "square-outline" },
  { key: "coulissant", letter: "B", label: "CHÂSSIS COULISSANT", icon: "swap-horizontal-outline" },
  { key: "porte", letter: "C", label: "PORTE D'ENTRÉE", icon: "exit-outline" },
  { key: "trapeze", letter: "D", label: "CHÂSSIS TRAPÈZE", icon: "triangle-outline" },
];

type Step = 0 | 1 | 2;

type Step2 = {
  bay_width: string;
  bay_height: string;
  diag_1: string;
  diag_1_state: DiagState;
  diag_2: string;
  diag_2_state: DiagState;
  floor_reserve: string;
};

const initStep2 = (): Step2 => ({
  bay_width: "",
  bay_height: "",
  diag_1: "",
  diag_1_state: "manual",
  diag_2: "",
  diag_2_state: "manual",
  floor_reserve: "",
});

type Step3 = {
  bloc_thickness: string;
  wall_type: WallType | null;
  insulation_thickness: string;
  finish_outer: string;
  finish_inner: string;
};

const initStep3 = (): Step3 => ({
  bloc_thickness: "",
  wall_type: null,
  insulation_thickness: "",
  finish_outer: "",
  finish_inner: "",
});

const parseNum = (s: string) => {
  const n = parseFloat(s.replace(",", "."));
  return Number.isFinite(n) ? n : null;
};

export default function NewMesureWizard() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();

  const [step, setStep] = useState<Step>(0);
  const [blockType, setBlockType] = useState<BlockType | null>(null);
  const [label, setLabel] = useState("");
  const [photo, setPhoto] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const [s2, setS2] = useState<Step2>(initStep2());
  const [s2Err, setS2Err] = useState<Record<string, boolean>>({});

  const [s3, setS3] = useState<Step3>(initStep3());
  const [s3Err, setS3Err] = useState<Record<string, boolean>>({});

  const [reportOpen, setReportOpen] = useState(false);
  const [reportText, setReportText] = useState("");
  const [reportSending, setReportSending] = useState(false);

  // ---------- Auto-Pythagoras prefill ----------------------------------
  useEffect(() => {
    const w = parseNum(s2.bay_width);
    const h = parseNum(s2.bay_height);
    if (w && h && w > 0 && h > 0) {
      const d = Math.round(Math.sqrt(w * w + h * h));
      setS2((prev) => {
        let next = prev;
        if (prev.diag_1_state === "manual" && prev.diag_1.trim().length === 0) {
          next = { ...next, diag_1: String(d), diag_1_state: "auto" };
        }
        if (prev.diag_2_state === "manual" && prev.diag_2.trim().length === 0) {
          next = { ...next, diag_2: String(d), diag_2_state: "auto" };
        }
        return next;
      });
    }
  }, [s2.bay_width, s2.bay_height]);

  const setS2Field = (k: keyof Step2, v: any) => setS2((p) => ({ ...p, [k]: v }));
  const setS3Field = (k: keyof Step3, v: any) => setS3((p) => ({ ...p, [k]: v }));

  // ---------- Validation -----------------------------------------------
  const validateStep2 = (): boolean => {
    if (!blockType) return false;
    const err: Record<string, boolean> = {};
    if (!parseNum(s2.bay_width)) err.bay_width = true;
    if (!parseNum(s2.bay_height)) err.bay_height = true;
    if (!parseNum(s2.diag_1)) err.diag_1 = true;
    if (!parseNum(s2.diag_2)) err.diag_2 = true;
    if (s2.diag_1_state === "auto") err.diag_1 = true; // not yet validated/modified
    if (s2.diag_2_state === "auto") err.diag_2 = true;
    if (blockType === "porte" && !parseNum(s2.floor_reserve)) err.floor_reserve = true;
    if (!label.trim()) {
      Alert.alert("Libellé manquant", "Indiquez un libellé (ex. Salon).");
      return false;
    }
    setS2Err(err);
    return Object.keys(err).length === 0;
  };

  const validateStep3 = (): boolean => {
    const err: Record<string, boolean> = {};
    if (!parseNum(s3.bloc_thickness)) err.bloc_thickness = true;
    if (!s3.wall_type) err.wall_type = true;
    setS3Err(err);
    return Object.keys(err).length === 0;
  };

  // ---------- Photo helpers --------------------------------------------
  const pickPhoto = async (source: "camera" | "library") => {
    const fn =
      source === "camera"
        ? ImagePicker.requestCameraPermissionsAsync
        : ImagePicker.requestMediaLibraryPermissionsAsync;
    const perm = await fn();
    if (!perm.granted) {
      Alert.alert("Permission refusée", "Activez l'accès dans les réglages.");
      return;
    }
    const launcher =
      source === "camera" ? ImagePicker.launchCameraAsync : ImagePicker.launchImageLibraryAsync;
    const res = await launcher({ mediaTypes: ImagePicker.MediaTypeOptions.Images, quality: 0.5, base64: true });
    if (!res.canceled && res.assets[0]) {
      const a = res.assets[0];
      setPhoto(a.base64 ? `data:image/jpeg;base64,${a.base64}` : a.uri);
    }
  };

  // ---------- Submit ----------------------------------------------------
  const submit = async () => {
    if (!blockType || !validateStep3()) return;
    setSaving(true);
    const payload: Record<string, unknown> = {
      chantier_id: id,
      block_type: blockType,
      label: label.trim(),
      photo_url: photo,
      bay_width: parseNum(s2.bay_width),
      bay_height: parseNum(s2.bay_height),
      bay_diagonal_1: parseNum(s2.diag_1),
      bay_diagonal_2: parseNum(s2.diag_2),
      diag_1_verified: s2.diag_1_state !== "auto",
      diag_2_verified: s2.diag_2_state !== "auto",
      bloc_thickness: parseNum(s3.bloc_thickness),
      wall_type: s3.wall_type,
      options: {},
    };
    if (blockType === "porte") payload.floor_reserve = parseNum(s2.floor_reserve);
    if (s3.insulation_thickness) payload.insulation_thickness = parseNum(s3.insulation_thickness);
    if (s3.finish_outer) payload.finish_outer = parseNum(s3.finish_outer);
    if (s3.finish_inner) payload.finish_inner = parseNum(s3.finish_inner);

    try {
      const online = await isOnline();
      if (!online) {
        await enqueueMesure(payload);
        Alert.alert("Hors ligne", "Mesure ajoutée à la file de synchro.", [
          { text: "OK", onPress: () => router.back() },
        ]);
        return;
      }
      await api.post("/mesures", payload);
      router.back();
    } catch {
      await enqueueMesure(payload);
      Alert.alert("Réseau indisponible", "Mesure mise en file d'attente.", [
        { text: "OK", onPress: () => router.back() },
      ]);
    } finally {
      setSaving(false);
    }
  };

  // ---------- Quick report (top-corner) ---------------------------------
  const sendReport = async () => {
    if (!reportText.trim()) return;
    setReportSending(true);
    try {
      await api.post("/feedbacks", {
        page_context: `wizard:step${step + 1}:${blockType ?? "none"}`,
        user_comment: reportText.trim(),
        encoded_data_snapshot: { chantier_id: id, blockType, label, s2, s3 },
      });
      setReportOpen(false);
      setReportText("");
      Alert.alert("Merci !", "Votre signalement a été envoyé.");
    } catch {
      Alert.alert("Erreur", "Envoi impossible.");
    } finally {
      setReportSending(false);
    }
  };

  const isRectangular = blockType !== "trapeze";

  return (
    <SafeAreaView style={styles.flex} edges={["bottom"]}>
      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={styles.flex}>
        {/* Top bar with steps + tiny "Signaler un problème" */}
        <View style={styles.topBar}>
          <View style={styles.stepRow}>
            {[0, 1, 2].map((i) => (
              <View
                key={i}
                testID={`step-pill-${i + 1}`}
                style={[styles.stepPill, i <= step && styles.stepPillActive]}
              >
                <Text style={[styles.stepPillText, i <= step && { color: "#000" }]}>{i + 1}</Text>
              </View>
            ))}
          </View>
          <TouchableOpacity
            testID="open-report-modal"
            onPress={() => setReportOpen(true)}
            style={styles.reportBtn}
            activeOpacity={0.7}
          >
            <Ionicons name="alert-circle-outline" size={14} color={colors.anomaly} />
            <Text style={styles.reportBtnText}>Signaler un problème</Text>
          </TouchableOpacity>
        </View>

        <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 200 }} keyboardShouldPersistTaps="handled">
          {step === 0 && (
            <Step1
              onPick={(k) => {
                setBlockType(k);
                setStep(1);
              }}
            />
          )}
          {step === 1 && blockType && (
            <Step2View
              blockType={blockType}
              isRectangular={isRectangular}
              label={label}
              setLabel={setLabel}
              s2={s2}
              setS2Field={setS2Field}
              err={s2Err}
              photo={photo}
              setPhoto={setPhoto}
              pickPhoto={pickPhoto}
            />
          )}
          {step === 2 && (
            <Step3View s3={s3} setField={setS3Field} err={s3Err} />
          )}
        </ScrollView>

        <View style={styles.footer}>
          {step > 0 && (
            <TouchableOpacity
              testID="wizard-back"
              onPress={() => setStep((step - 1) as Step)}
              style={[styles.btn, styles.btnSecondary]}
              activeOpacity={0.7}
            >
              <Ionicons name="arrow-back" size={20} color={colors.textPrimary} />
              <Text style={styles.btnSecondaryText}>RETOUR</Text>
            </TouchableOpacity>
          )}
          {step === 1 && (
            <TouchableOpacity
              testID="wizard-next"
              onPress={() => validateStep2() && setStep(2)}
              style={[styles.btn, styles.btnPrimary]}
              activeOpacity={0.85}
            >
              <Text style={styles.btnPrimaryText}>SUIVANT</Text>
              <Ionicons name="arrow-forward" size={20} color="#000" />
            </TouchableOpacity>
          )}
          {step === 2 && (
            <TouchableOpacity
              testID="wizard-submit"
              onPress={submit}
              disabled={saving}
              style={[styles.btn, styles.btnPrimary]}
              activeOpacity={0.85}
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
        </View>
      </KeyboardAvoidingView>

      {/* Report modal */}
      <Modal visible={reportOpen} transparent animationType="fade" onRequestClose={() => setReportOpen(false)}>
        <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : "height"} style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
              <Ionicons name="alert-circle" size={20} color={colors.anomaly} />
              <Text style={styles.modalTitle}>Signaler un problème</Text>
            </View>
            <Text style={styles.modalSub}>Décrivez ce qui ne va pas — envoyé à l'admin avec le contexte.</Text>
            <TextInput
              testID="report-text-input"
              value={reportText}
              onChangeText={setReportText}
              multiline
              numberOfLines={4}
              placeholder="Ex: la diagonale auto-calculée est fausse..."
              placeholderTextColor={colors.placeholder}
              style={styles.reportInput}
            />
            <View style={{ flexDirection: "row", gap: 8, marginTop: 12 }}>
              <TouchableOpacity
                onPress={() => setReportOpen(false)}
                style={[styles.btn, styles.btnSecondary, { flex: 1, minHeight: 48 }]}
                activeOpacity={0.7}
              >
                <Text style={styles.btnSecondaryText}>ANNULER</Text>
              </TouchableOpacity>
              <TouchableOpacity
                testID="report-submit"
                onPress={sendReport}
                disabled={reportSending}
                style={[styles.btn, styles.btnPrimary, { flex: 1, minHeight: 48 }]}
                activeOpacity={0.85}
              >
                {reportSending ? <ActivityIndicator color="#000" /> : <Text style={styles.btnPrimaryText}>ENVOYER</Text>}
              </TouchableOpacity>
            </View>
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </SafeAreaView>
  );
}

// ======================== Step 1 ========================================
function Step1({ onPick }: { onPick: (k: BlockType) => void }) {
  return (
    <View>
      <Text style={styles.h1}>SÉLECTION TYPE CHÂSSIS</Text>
      <View style={styles.gridRow}>
        {BLOCKS.map((b) => (
          <TouchableOpacity
            key={b.key}
            testID={`block-type-${b.key}`}
            onPress={() => onPick(b.key)}
            style={styles.blockCard}
            activeOpacity={0.75}
          >
            <View style={styles.blockLetterBadge}>
              <Text style={styles.blockLetter}>{b.letter}</Text>
            </View>
            <View style={styles.blockIconBox}>
              <Ionicons name={b.icon} size={36} color={colors.textPrimary} />
            </View>
            <Text style={styles.blockTitle}>{b.label}</Text>
          </TouchableOpacity>
        ))}
      </View>
    </View>
  );
}

// ======================== Step 2 ========================================
function Step2View({
  blockType,
  isRectangular,
  label,
  setLabel,
  s2,
  setS2Field,
  err,
  photo,
  setPhoto,
  pickPhoto,
}: {
  blockType: BlockType;
  isRectangular: boolean;
  label: string;
  setLabel: (v: string) => void;
  s2: Step2;
  setS2Field: (k: keyof Step2, v: any) => void;
  err: Record<string, boolean>;
  photo: string | null;
  setPhoto: (v: string | null) => void;
  pickPhoto: (s: "camera" | "library") => void;
}) {
  const Sketch = isRectangular ? RawBaySchemaRect : RawBaySchemaTrapeze;

  const validateDiag = (which: 1 | 2) =>
    setS2Field(which === 1 ? "diag_1_state" : "diag_2_state", "validated");
  const modifyDiag = (which: 1 | 2) => {
    setS2Field(which === 1 ? "diag_1" : "diag_2", "");
    setS2Field(which === 1 ? "diag_1_state" : "diag_2_state", "manual");
  };

  return (
    <View>
      <Text style={styles.h1}>PRISE À LA MESURE</Text>
      <Text style={styles.h2}>Cotes de la baie brute · {isRectangular ? "Rectangulaire" : "Trapèze"}</Text>

      <Text style={[styles.label, { marginTop: 14 }]}>Libellé de l'ouverture</Text>
      <TextInput
        testID="mesure-label-input"
        value={label}
        onChangeText={setLabel}
        placeholder="ex. Salon, Chambre 1..."
        placeholderTextColor={colors.placeholder}
        style={styles.input}
      />

      <View style={styles.sketchBox}>
        <Sketch values={{ bay_width: s2.bay_width, bay_height: s2.bay_height, bay_diagonal: s2.diag_1 }} />
      </View>

      <CotField
        testID="input-bay-width"
        label="LARGEUR (mm)"
        value={s2.bay_width}
        onChange={(v) => setS2Field("bay_width", v.replace(",", "."))}
        error={!!err.bay_width}
      />
      <CotField
        testID="input-bay-height"
        label="HAUTEUR (mm)"
        value={s2.bay_height}
        onChange={(v) => setS2Field("bay_height", v.replace(",", "."))}
        error={!!err.bay_height}
      />

      <DiagonalField
        testID="diag-1"
        label="DIAGONALE 1 (mm)"
        value={s2.diag_1}
        state={s2.diag_1_state}
        onChange={(v) => {
          setS2Field("diag_1", v.replace(",", "."));
          if (s2.diag_1_state === "auto") setS2Field("diag_1_state", "manual");
        }}
        onValidate={() => validateDiag(1)}
        onModify={() => modifyDiag(1)}
        error={!!err.diag_1}
      />
      <DiagonalField
        testID="diag-2"
        label="DIAGONALE 2 (mm)"
        value={s2.diag_2}
        state={s2.diag_2_state}
        onChange={(v) => {
          setS2Field("diag_2", v.replace(",", "."));
          if (s2.diag_2_state === "auto") setS2Field("diag_2_state", "manual");
        }}
        onValidate={() => validateDiag(2)}
        onModify={() => modifyDiag(2)}
        error={!!err.diag_2}
      />

      {blockType === "porte" && (
        <View style={styles.criticalBlock}>
          <View style={styles.criticalHeader}>
            <Ionicons name="warning" size={18} color={colors.anomaly} />
            <Text style={styles.criticalTitle}>RÉSERVE SOL FINI (mm)</Text>
          </View>
          <Text style={styles.criticalHelp}>Obligatoire pour les portes d'entrée.</Text>
          <TextInput
            testID="input-floor-reserve"
            value={s2.floor_reserve}
            onChangeText={(v) => setS2Field("floor_reserve", v.replace(",", "."))}
            placeholder="0"
            placeholderTextColor={colors.placeholder}
            keyboardType="decimal-pad"
            style={[styles.input, styles.inputCritical, err.floor_reserve && styles.inputErrorCritical]}
          />
          {err.floor_reserve && <ErrFlag />}
        </View>
      )}

      <Text style={[styles.label, { marginTop: 24 }]}>Photo (optionnel)</Text>
      {photo ? (
        <View>
          <Image source={{ uri: photo }} style={styles.photo} />
          <TouchableOpacity testID="remove-photo-button" onPress={() => setPhoto(null)} style={styles.removePhoto}>
            <Ionicons name="trash" size={16} color="#fff" />
          </TouchableOpacity>
        </View>
      ) : (
        <View style={styles.photoRow}>
          <TouchableOpacity testID="photo-camera-button" onPress={() => pickPhoto("camera")} style={styles.photoBtn} activeOpacity={0.7}>
            <Ionicons name="camera" size={22} color={colors.primary} />
            <Text style={styles.photoBtnText}>Caméra</Text>
          </TouchableOpacity>
          <TouchableOpacity testID="photo-library-button" onPress={() => pickPhoto("library")} style={styles.photoBtn} activeOpacity={0.7}>
            <Ionicons name="images" size={22} color={colors.primary} />
            <Text style={styles.photoBtnText}>Galerie</Text>
          </TouchableOpacity>
        </View>
      )}
    </View>
  );
}

function CotField({
  testID,
  label,
  value,
  onChange,
  error,
}: {
  testID: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
  error: boolean;
}) {
  return (
    <View style={{ marginTop: 12 }}>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        testID={testID}
        value={value}
        onChangeText={onChange}
        placeholder="Ex: 1200"
        placeholderTextColor={colors.placeholder}
        keyboardType="decimal-pad"
        style={[styles.input, error && styles.inputError]}
      />
      {error && <ErrFlag />}
    </View>
  );
}

function DiagonalField({
  testID,
  label,
  value,
  state,
  onChange,
  onValidate,
  onModify,
  error,
}: {
  testID: string;
  label: string;
  value: string;
  state: DiagState;
  onChange: (v: string) => void;
  onValidate: () => void;
  onModify: () => void;
  error: boolean;
}) {
  const badge = useMemo(() => {
    if (state === "auto") return { text: "AUTO (Pythagore)", bg: "#3a2400", color: colors.warning };
    if (state === "validated") return { text: "VALIDÉ", bg: "#0e3315", color: colors.success };
    return { text: "MANUEL", bg: "#27272A", color: colors.textPrimary };
  }, [state]);
  return (
    <View style={{ marginTop: 12 }}>
      <View style={styles.diagHeader}>
        <Text style={styles.label}>{label}</Text>
        <View style={[styles.diagBadge, { backgroundColor: badge.bg }]}>
          <Text style={[styles.diagBadgeText, { color: badge.color }]}>{badge.text}</Text>
        </View>
      </View>
      <TextInput
        testID={`${testID}-input`}
        value={value}
        onChangeText={onChange}
        editable={state !== "validated"}
        placeholder="Ex: 1800"
        placeholderTextColor={colors.placeholder}
        keyboardType="decimal-pad"
        style={[
          styles.input,
          error && styles.inputError,
          state === "auto" && { borderColor: colors.warning, backgroundColor: "#1a1206" },
          state === "validated" && { borderColor: colors.success },
        ]}
      />
      <View style={styles.diagActions}>
        <TouchableOpacity
          testID={`${testID}-validate`}
          onPress={onValidate}
          disabled={!value || state === "validated"}
          style={[styles.diagBtn, styles.diagBtnValid, (!value || state === "validated") && { opacity: 0.5 }]}
          activeOpacity={0.85}
        >
          <Ionicons name="checkmark" size={16} color="#000" />
          <Text style={styles.diagBtnValidText}>Valider</Text>
        </TouchableOpacity>
        <TouchableOpacity
          testID={`${testID}-modify`}
          onPress={onModify}
          style={[styles.diagBtn, styles.diagBtnModify]}
          activeOpacity={0.85}
        >
          <Ionicons name="create" size={16} color={colors.textPrimary} />
          <Text style={styles.diagBtnModifyText}>Modifier</Text>
        </TouchableOpacity>
      </View>
      {error && <ErrFlag />}
    </View>
  );
}

function ErrFlag() {
  return (
    <View style={styles.errorRow}>
      <Ionicons name="alert-circle" size={14} color={colors.anomaly} />
      <Text style={styles.errorText}>COTE OBLIGATOIRE MANQUANTE</Text>
    </View>
  );
}

// ======================== Step 3 ========================================
const WALLS: {
  key: WallType;
  letter: string;
  title: string;
  variant: "ite" | "iti" | "crepi";
  subs: { label: string; key: "insulation_thickness" | "finish_outer" | "finish_inner" }[];
}[] = [
  {
    key: "ite",
    letter: "A",
    title: "FAÇADE ISOLANTE EXTÉRIEURE (ITE)",
    variant: "ite",
    subs: [
      { label: "Épaisseur Isolant (mm)", key: "insulation_thickness" },
      { label: "Épaisseur Crépi (mm)", key: "finish_outer" },
    ],
  },
  {
    key: "iti",
    letter: "B",
    title: "ISOLATION INTÉRIEURE (ITI)",
    variant: "iti",
    subs: [
      { label: "Épaisseur Isolant (mm)", key: "insulation_thickness" },
      { label: "Épaisseur Plâtre/Finition (mm)", key: "finish_inner" },
    ],
  },
  {
    key: "brique_parement",
    letter: "C",
    title: "BRIQUE DE PAREMENT",
    variant: "ite",
    subs: [
      { label: "Épaisseur Coulisse/Isolant (mm)", key: "insulation_thickness" },
      { label: "Épaisseur Brique (mm)", key: "finish_outer" },
    ],
  },
  {
    key: "crepi_simple",
    letter: "D",
    title: "CRÉPI SIMPLE",
    variant: "crepi",
    subs: [{ label: "Épaisseur Crépi/Finition (mm)", key: "finish_outer" }],
  },
];

function Step3View({
  s3,
  setField,
  err,
}: {
  s3: Step3;
  setField: (k: keyof Step3, v: any) => void;
  err: Record<string, boolean>;
}) {
  return (
    <View>
      <Text style={styles.h1}>CONCEPTION MAÇONNERIE & ISOLATION</Text>
      <Text style={[styles.h2, { color: colors.textSecondary }]}>(INDICATIF)</Text>

      <View style={styles.mainWallCard}>
        <Text style={styles.mainWallTitle}>MUR DE BASE</Text>
        <Text style={styles.label}>Épaisseur Bloc Béton (mm)</Text>
        <TextInput
          testID="input-bloc-thickness"
          value={s3.bloc_thickness}
          onChangeText={(v) => setField("bloc_thickness", v.replace(",", "."))}
          placeholder="Ex: 200"
          placeholderTextColor={colors.placeholder}
          keyboardType="decimal-pad"
          style={[styles.input, err.bloc_thickness && styles.inputError]}
        />
        {err.bloc_thickness && <ErrFlag />}
      </View>

      <Text style={[styles.label, { marginTop: 22 }]}>Type de paroi (sélectionner)</Text>
      {err.wall_type && <ErrFlag />}

      {WALLS.map((opt) => {
        const active = s3.wall_type === opt.key;
        return (
          <TouchableOpacity
            key={opt.key}
            testID={`wall-type-${opt.key}`}
            onPress={() => setField("wall_type", opt.key)}
            activeOpacity={0.75}
            style={[styles.wallCard, active && styles.wallCardActive]}
          >
            <View style={styles.wallCardHeader}>
              <View style={[styles.blockLetterBadge, active && { backgroundColor: colors.primary }, { position: "relative", top: 0, left: 0 }]}>
                <Text style={[styles.blockLetter, active && { color: "#000" }]}>{opt.letter}</Text>
              </View>
              <View style={{ flex: 1, marginLeft: 10 }}>
                <Text style={styles.wallTitle}>{opt.title}</Text>
                <Text style={styles.indicatif}>(INDICATIF)</Text>
              </View>
              <WallSection variant={opt.variant} size={60} />
            </View>
            {active && (
              <View style={styles.wallFields}>
                {opt.subs.map((sub) => (
                  <View key={sub.key} style={{ marginTop: 10 }}>
                    <Text style={styles.subFieldLabel}>
                      {sub.label} <Text style={styles.indicatifInline}>(INDICATIF)</Text>
                    </Text>
                    <TextInput
                      testID={`${opt.key}-${sub.key}`}
                      value={(s3 as any)[sub.key] ?? ""}
                      onChangeText={(v) => setField(sub.key as any, v.replace(",", "."))}
                      placeholder="0"
                      placeholderTextColor={colors.placeholder}
                      keyboardType="decimal-pad"
                      style={styles.input}
                    />
                  </View>
                ))}
              </View>
            )}
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

// ======================== Styles ========================================
const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: colors.bg },
  topBar: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 16,
    paddingTop: 10,
    paddingBottom: 8,
    backgroundColor: colors.bg,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSubtle,
  },
  stepRow: { flexDirection: "row", gap: 6 },
  stepPill: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    alignItems: "center",
    justifyContent: "center",
  },
  stepPillActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  stepPillText: { color: colors.textSecondary, fontWeight: "900", fontSize: 13 },
  reportBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: colors.anomaly,
    backgroundColor: "#1a0707",
  },
  reportBtnText: { color: colors.anomaly, fontSize: 11, fontWeight: "700" },
  h1: { color: colors.textPrimary, fontSize: 20, fontWeight: "900", letterSpacing: 1 },
  h2: { color: colors.textPrimary, fontSize: 14, marginTop: 2, fontWeight: "700", letterSpacing: 0.8 },
  // Step 1
  gridRow: { flexDirection: "row", flexWrap: "wrap", gap: 12, marginTop: 20 },
  blockCard: {
    width: "47%",
    backgroundColor: colors.surface,
    borderColor: colors.borderSubtle,
    borderWidth: 1,
    borderRadius: 12,
    padding: 16,
    alignItems: "center",
    minHeight: 150,
  },
  blockLetterBadge: {
    position: "absolute",
    top: 10,
    left: 10,
    width: 28,
    height: 28,
    borderRadius: 6,
    backgroundColor: colors.bg,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    alignItems: "center",
    justifyContent: "center",
  },
  blockLetter: { color: colors.primary, fontWeight: "900", fontSize: 14 },
  blockIconBox: {
    width: 72,
    height: 72,
    borderRadius: 10,
    backgroundColor: colors.bg,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 12,
    marginBottom: 14,
  },
  blockTitle: { color: colors.textPrimary, fontWeight: "900", fontSize: 13, letterSpacing: 0.6, textAlign: "center" },
  // Inputs
  label: {
    color: colors.textSecondary,
    fontSize: 11,
    fontWeight: "800",
    textTransform: "uppercase",
    letterSpacing: 1.2,
    marginBottom: 6,
  },
  input: {
    backgroundColor: colors.inputBg,
    borderColor: colors.borderSubtle,
    borderWidth: 2,
    borderRadius: 8,
    color: colors.textPrimary,
    minHeight: 52,
    paddingHorizontal: 14,
    fontSize: 16,
    fontWeight: "600",
  },
  inputError: { borderColor: colors.anomaly, borderWidth: 3 },
  inputCritical: { borderColor: colors.anomaly, backgroundColor: "#1c0606" },
  inputErrorCritical: { borderColor: colors.anomaly, borderWidth: 3, backgroundColor: "#260a0a" },
  errorRow: { flexDirection: "row", alignItems: "center", gap: 4, marginTop: 6 },
  errorText: { color: colors.anomaly, fontWeight: "900", fontSize: 11, letterSpacing: 1 },
  sketchBox: {
    backgroundColor: colors.bg,
    borderColor: colors.borderSubtle,
    borderWidth: 1,
    borderRadius: 12,
    marginTop: 16,
    padding: 12,
    alignItems: "center",
  },
  // Diag
  diagHeader: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  diagBadge: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 4, marginBottom: 6 },
  diagBadgeText: { fontSize: 10, fontWeight: "900", letterSpacing: 0.8 },
  diagActions: { flexDirection: "row", gap: 8, marginTop: 8 },
  diagBtn: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    minHeight: 46,
    borderRadius: 8,
  },
  diagBtnValid: { backgroundColor: colors.success },
  diagBtnValidText: { color: "#000", fontWeight: "900", letterSpacing: 0.6, fontSize: 13 },
  diagBtnModify: { backgroundColor: colors.surfaceElevated, borderWidth: 1, borderColor: colors.borderStrong },
  diagBtnModifyText: { color: colors.textPrimary, fontWeight: "800", letterSpacing: 0.6, fontSize: 13 },
  // Critical block
  criticalBlock: {
    marginTop: 22,
    padding: 14,
    borderRadius: 10,
    borderWidth: 2,
    borderColor: colors.anomaly,
    backgroundColor: "#1a0707",
  },
  criticalHeader: { flexDirection: "row", alignItems: "center", gap: 6, marginBottom: 4 },
  criticalTitle: { color: colors.anomaly, fontWeight: "900", fontSize: 13, letterSpacing: 1 },
  criticalHelp: { color: colors.textSecondary, fontSize: 12, marginBottom: 10 },
  // Photo
  photo: { width: "100%", height: 200, borderRadius: 10, backgroundColor: colors.surface },
  removePhoto: {
    position: "absolute",
    top: 10,
    right: 10,
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: "rgba(0,0,0,0.7)",
    alignItems: "center",
    justifyContent: "center",
  },
  photoRow: { flexDirection: "row", gap: 10 },
  photoBtn: {
    flex: 1,
    minHeight: 64,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    borderStyle: "dashed",
    borderRadius: 10,
    alignItems: "center",
    justifyContent: "center",
    flexDirection: "row",
    gap: 8,
  },
  photoBtnText: { color: colors.textPrimary, fontWeight: "700" },
  // Step 3
  mainWallCard: {
    marginTop: 16,
    backgroundColor: colors.surface,
    borderColor: colors.borderSubtle,
    borderWidth: 1,
    borderRadius: 12,
    padding: 14,
  },
  mainWallTitle: { color: colors.primary, fontWeight: "900", fontSize: 14, letterSpacing: 1.2, marginBottom: 12 },
  wallCard: {
    marginTop: 10,
    backgroundColor: colors.surface,
    borderColor: colors.borderSubtle,
    borderWidth: 1,
    borderRadius: 12,
    padding: 14,
  },
  wallCardActive: { borderColor: colors.primary, backgroundColor: "#1a0e00" },
  wallCardHeader: { flexDirection: "row", alignItems: "center" },
  wallTitle: { color: colors.textPrimary, fontWeight: "900", fontSize: 13, letterSpacing: 0.4 },
  indicatif: { color: colors.textSecondary, fontSize: 10, fontWeight: "700", letterSpacing: 0.8, marginTop: 2 },
  indicatifInline: { color: colors.textSecondary, fontSize: 10, fontWeight: "700" },
  wallFields: { marginTop: 12, borderTopWidth: 1, borderTopColor: colors.borderSubtle, paddingTop: 12 },
  subFieldLabel: {
    color: colors.textSecondary,
    fontSize: 11,
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: 0.8,
    marginBottom: 4,
  },
  // Footer
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
    flexDirection: "row",
    gap: 10,
  },
  btn: { flex: 1, minHeight: 60, borderRadius: 8, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8 },
  btnPrimary: { backgroundColor: colors.primary },
  btnPrimaryText: { color: "#000", fontWeight: "900", fontSize: 15, letterSpacing: 1 },
  btnSecondary: { borderWidth: 2, borderColor: colors.borderStrong },
  btnSecondaryText: { color: colors.textPrimary, fontWeight: "800", letterSpacing: 1 },
  // Modal
  modalOverlay: { flex: 1, backgroundColor: "rgba(0,0,0,0.8)", justifyContent: "center", padding: 20 },
  modalCard: {
    backgroundColor: colors.surface,
    borderColor: colors.borderSubtle,
    borderWidth: 1,
    borderRadius: 12,
    padding: 20,
  },
  modalTitle: { color: colors.textPrimary, fontWeight: "900", fontSize: 17, letterSpacing: 0.6 },
  modalSub: { color: colors.textSecondary, fontSize: 12, marginTop: 4, marginBottom: 12 },
  reportInput: {
    backgroundColor: colors.inputBg,
    borderColor: colors.borderSubtle,
    borderWidth: 2,
    borderRadius: 8,
    color: colors.textPrimary,
    padding: 12,
    fontSize: 15,
    minHeight: 110,
    textAlignVertical: "top",
  },
});
