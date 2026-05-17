import React, { useState } from "react";
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
  trap_height_left: string;
  trap_height_right: string;
};

const initStep2 = (): Step2 => ({
  bay_width: "",
  bay_height: "",
  diag_1: "",
  diag_1_state: "manual",
  diag_2: "",
  diag_2_state: "manual",
  floor_reserve: "",
  trap_height_left: "",
  trap_height_right: "",
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

  // ---------- Pythagoras manual trigger (onBlur or explicit button) ------
  // We deliberately DO NOT auto-compute on every keystroke — only when the
  // user has finished typing both width AND height (blur, or tap the button).
  const computeDiagonals = (force = false) => {
    if (blockType === "trapeze") return;
    const w = parseNum(s2.bay_width);
    const h = parseNum(s2.bay_height);
    if (!w || !h || w <= 0 || h <= 0) return;
    const d = Math.round(Math.sqrt(w * w + h * h));
    setS2((prev) => {
      let next = prev;
      // Force = explicit button click → always (re)fill in auto state.
      // onBlur = soft → only fill if still empty / not validated.
      if (force || (prev.diag_1_state !== "validated" && prev.diag_1.trim().length === 0)) {
        next = { ...next, diag_1: String(d), diag_1_state: "auto" };
      }
      if (force || (prev.diag_2_state !== "validated" && prev.diag_2.trim().length === 0)) {
        next = { ...next, diag_2: String(d), diag_2_state: "auto" };
      }
      return next;
    });
  };

  const canComputeDiag = blockType !== "trapeze"
    && !!parseNum(s2.bay_width) && !!parseNum(s2.bay_height);

  const setS2Field = (k: keyof Step2, v: any) => setS2((p) => ({ ...p, [k]: v }));
  const setS3Field = (k: keyof Step3, v: any) => setS3((p) => ({ ...p, [k]: v }));

  // ---------- Validation -----------------------------------------------
  const validateStep2 = (): boolean => {
    if (!blockType) return false;
    const err: Record<string, boolean> = {};
    if (!label.trim()) {
      Alert.alert("Libellé manquant", "Indiquez un libellé (ex. Salon).");
      return false;
    }
    if (blockType === "trapeze") {
      if (!parseNum(s2.bay_width)) err.bay_width = true;
      if (!parseNum(s2.trap_height_left)) err.trap_height_left = true;
      if (!parseNum(s2.trap_height_right)) err.trap_height_right = true;
    } else {
      if (!parseNum(s2.bay_width)) err.bay_width = true;
      if (!parseNum(s2.bay_height)) err.bay_height = true;
      if (!parseNum(s2.diag_1)) err.diag_1 = true;
      if (!parseNum(s2.diag_2)) err.diag_2 = true;
      if (s2.diag_1_state === "auto") err.diag_1 = true;
      if (s2.diag_2_state === "auto") err.diag_2 = true;
      if ((blockType === "porte" || blockType === "coulissant") && !parseNum(s2.floor_reserve)) {
        err.floor_reserve = true;
      }
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
      options: {},
    };
    if (blockType === "trapeze") {
      payload.height_left = parseNum(s2.trap_height_left);
      payload.height_right = parseNum(s2.trap_height_right);
    } else {
      payload.bay_height = parseNum(s2.bay_height);
      payload.bay_diagonal_1 = parseNum(s2.diag_1);
      payload.bay_diagonal_2 = parseNum(s2.diag_2);
      payload.diag_1_verified = s2.diag_1_state !== "auto";
      payload.diag_2_verified = s2.diag_2_state !== "auto";
    }
    payload.bloc_thickness = parseNum(s3.bloc_thickness);
    payload.wall_type = s3.wall_type;
    if (blockType === "porte" || blockType === "coulissant") {
      payload.floor_reserve = parseNum(s2.floor_reserve);
    }
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
              onBlurDimension={() => computeDiagonals(false)}
              onComputeDiagonals={() => computeDiagonals(true)}
              canComputeDiag={canComputeDiag}
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
  onBlurDimension,
  onComputeDiagonals,
  canComputeDiag,
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
  onBlurDimension: () => void;
  onComputeDiagonals: () => void;
  canComputeDiag: boolean;
}) {
  const Sketch = isRectangular ? RawBaySchemaRect : RawBaySchemaTrapeze;

  if (!isRectangular) {
    // === Trapezoidal workflow: ONLY 3 fields, no diagonals ===
    return (
      <View>
        <Text style={styles.h1}>PRISE À LA MESURE</Text>
        <Text style={styles.h2}>Cotes de la baie brute · Trapèze</Text>

        <Text style={[styles.label, { marginTop: 14 }]}>Libellé de l'ouverture</Text>
        <TextInput
          testID="mesure-label-input"
          value={label}
          onChangeText={setLabel}
          placeholder="ex. Lucarne, Pignon..."
          placeholderTextColor={colors.placeholder}
          style={styles.input}
        />

        <View style={styles.sketchBox}>
          <Sketch
            values={{
              bay_width: s2.bay_width,
              bay_height: s2.trap_height_left,
              bay_diagonal: s2.trap_height_right,
            }}
          />
        </View>

        <CotField
          testID="input-bay-width"
          label="LARGEUR (mm)"
          value={s2.bay_width}
          onChange={(v) => setS2Field("bay_width", v.replace(",", "."))}
          error={!!err.bay_width}
        />
        <CotField
          testID="input-trap-height-left"
          label="HAUTEUR GAUCHE (mm)"
          value={s2.trap_height_left}
          onChange={(v) => setS2Field("trap_height_left", v.replace(",", "."))}
          error={!!err.trap_height_left}
        />
        <CotField
          testID="input-trap-height-right"
          label="HAUTEUR DROITE (mm)"
          value={s2.trap_height_right}
          onChange={(v) => setS2Field("trap_height_right", v.replace(",", "."))}
          error={!!err.trap_height_right}
        />

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
        onBlur={onBlurDimension}
        error={!!err.bay_width}
      />
      <CotField
        testID="input-bay-height"
        label="HAUTEUR (mm)"
        value={s2.bay_height}
        onChange={(v) => setS2Field("bay_height", v.replace(",", "."))}
        onBlur={onBlurDimension}
        error={!!err.bay_height}
      />

      {/* Bouton de calcul manuel — alternative claire à l'onBlur */}
      <TouchableOpacity
        testID="compute-diagonal-button"
        onPress={onComputeDiagonals}
        disabled={!canComputeDiag}
        activeOpacity={0.8}
        style={[
          styles.computeBtn,
          !canComputeDiag && { opacity: 0.4 },
        ]}
      >
        <Ionicons name="calculator-outline" size={18} color={colors.primary} />
        <Text style={styles.computeBtnText}>CALCULER LA DIAGONALE</Text>
      </TouchableOpacity>

      {/* Diagonales — auto-calculées Pythagore */}
      <DiagonalField
        testID="input-diag-1"
        label="DIAGONALE 1 (mm)"
        value={s2.diag_1}
        state={s2.diag_1_state}
        onChange={(v) => {
          setS2Field("diag_1", v.replace(",", "."));
          setS2Field("diag_1_state", "manual");
        }}
        onValidate={() => validateDiag(1)}
        onModify={() => modifyDiag(1)}
        error={!!err.diag_1}
      />
      <DiagonalField
        testID="input-diag-2"
        label="DIAGONALE 2 (mm)"
        value={s2.diag_2}
        state={s2.diag_2_state}
        onChange={(v) => {
          setS2Field("diag_2", v.replace(",", "."));
          setS2Field("diag_2_state", "manual");
        }}
        onValidate={() => validateDiag(2)}
        onModify={() => modifyDiag(2)}
        error={!!err.diag_2}
      />

      {(blockType === "porte" || blockType === "coulissant") && (
        <CotField
          testID="input-floor-reserve"
          label="RÉSERVE SOL FINI (mm) *"
          value={s2.floor_reserve}
          onChange={(v) => setS2Field("floor_reserve", v.replace(",", "."))}
          error={!!err.floor_reserve}
        />
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

// ======================== Step 3 ========================================
function Step3View({
  s3,
  setField,
  err,
}: {
  s3: Step3;
  setField: (k: keyof Step3, v: any) => void;
  err: Record<string, boolean>;
}) {
  const WALLS: { key: WallType; label: string; sub: string; variant: "ite" | "iti" | "crepi" }[] = [
    { key: "ite", label: "ITE", sub: "Isolation Thermique Extérieure", variant: "ite" },
    { key: "iti", label: "ITI", sub: "Isolation Thermique Intérieure", variant: "iti" },
    { key: "brique_parement", label: "BRIQUE", sub: "Brique de parement", variant: "crepi" },
    { key: "crepi_simple", label: "CRÉPI", sub: "Crépi simple", variant: "crepi" },
  ];
  return (
    <View>
      <Text style={styles.h1}>CONCEPTION MAÇONNERIE</Text>
      <Text style={styles.h2}>Informations indicatives (épaisseurs &amp; isolation)</Text>

      <CotField
        testID="input-bloc-thickness"
        label="ÉPAISSEUR BLOC BÉTON (mm) *"
        value={s3.bloc_thickness}
        onChange={(v) => setField("bloc_thickness", v.replace(",", "."))}
        error={!!err.bloc_thickness}
      />

      <Text style={[styles.label, { marginTop: 18 }]}>Type de paroi *</Text>
      <View style={styles.wallGrid}>
        {WALLS.map((w) => {
          const active = s3.wall_type === w.key;
          return (
            <TouchableOpacity
              key={w.key}
              testID={`wall-type-${w.key}`}
              onPress={() => setField("wall_type", w.key)}
              activeOpacity={0.8}
              style={[
                styles.wallCard,
                active && styles.wallCardActive,
                err.wall_type && !active && styles.wallCardError,
              ]}
            >
              <WallSection variant={w.variant} size={64} />
              <Text style={[styles.wallLabel, active && { color: colors.primary }]}>{w.label}</Text>
              <Text style={styles.wallSub}>{w.sub}</Text>
            </TouchableOpacity>
          );
        })}
      </View>

      {(s3.wall_type === "ite" || s3.wall_type === "iti") && (
        <>
          <CotField
            testID="input-insulation-thickness"
            label="ÉPAISSEUR ISOLANT (mm)"
            value={s3.insulation_thickness}
            onChange={(v) => setField("insulation_thickness", v.replace(",", "."))}
          />
          <CotField
            testID="input-finish-outer"
            label="FINITION EXTÉRIEURE (mm)"
            value={s3.finish_outer}
            onChange={(v) => setField("finish_outer", v.replace(",", "."))}
          />
          <CotField
            testID="input-finish-inner"
            label="FINITION INTÉRIEURE (mm)"
            value={s3.finish_inner}
            onChange={(v) => setField("finish_inner", v.replace(",", "."))}
          />
        </>
      )}
    </View>
  );
}

// ======================== Sub-components ================================
function CotField({
  testID,
  label,
  value,
  onChange,
  onBlur,
  error,
}: {
  testID?: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
  onBlur?: () => void;
  error?: boolean;
}) {
  return (
    <View style={{ marginTop: 14 }}>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        testID={testID}
        value={value}
        onChangeText={onChange}
        onBlur={onBlur}
        keyboardType="decimal-pad"
        placeholder="0"
        placeholderTextColor={colors.placeholder}
        style={[styles.input, error && styles.inputError]}
      />
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
  testID?: string;
  label: string;
  value: string;
  state: DiagState;
  onChange: (v: string) => void;
  onValidate: () => void;
  onModify: () => void;
  error?: boolean;
}) {
  const isAuto = state === "auto";
  const isValidated = state === "validated";
  return (
    <View style={{ marginTop: 14 }}>
      <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
        <Text style={styles.label}>{label}</Text>
        {isAuto && (
          <View style={styles.autoBadge}>
            <Ionicons name="calculator-outline" size={11} color="#000" />
            <Text style={styles.autoBadgeText}>AUTO PYTHAGORE</Text>
          </View>
        )}
        {isValidated && (
          <View style={styles.validBadge}>
            <Ionicons name="checkmark" size={12} color="#000" />
            <Text style={styles.autoBadgeText}>VALIDÉ</Text>
          </View>
        )}
      </View>
      <View style={{ flexDirection: "row", gap: 8 }}>
        <TextInput
          testID={testID}
          value={value}
          onChangeText={onChange}
          keyboardType="decimal-pad"
          placeholder="0"
          placeholderTextColor={colors.placeholder}
          editable={!isAuto}
          style={[
            styles.input,
            { flex: 1 },
            error && styles.inputError,
            isAuto && { borderColor: colors.primary, color: colors.primary },
            isValidated && { borderColor: colors.success, color: colors.success },
          ]}
        />
        {isAuto && (
          <>
            <TouchableOpacity
              testID={`${testID}-validate`}
              onPress={onValidate}
              activeOpacity={0.8}
              style={[styles.diagBtn, { backgroundColor: colors.success }]}
            >
              <Ionicons name="checkmark" size={18} color="#000" />
            </TouchableOpacity>
            <TouchableOpacity
              testID={`${testID}-modify`}
              onPress={onModify}
              activeOpacity={0.8}
              style={[styles.diagBtn, { backgroundColor: colors.warning }]}
            >
              <Ionicons name="create-outline" size={18} color="#000" />
            </TouchableOpacity>
          </>
        )}
      </View>
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
    paddingTop: 12,
    paddingBottom: 10,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSubtle,
  },
  stepRow: { flexDirection: "row", gap: 8 },
  stepPill: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: colors.surfaceElevated,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
    borderColor: colors.borderSubtle,
  },
  stepPillActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  stepPillText: { color: colors.textSecondary, fontWeight: "800", fontSize: 12 },
  reportBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
    backgroundColor: "#2a1010",
    borderWidth: 1,
    borderColor: colors.anomaly,
  },
  reportBtnText: { color: colors.anomaly, fontSize: 11, fontWeight: "700" },

  h1: { color: colors.textPrimary, fontSize: 18, fontWeight: "800", letterSpacing: 0.5 },
  h2: { color: colors.textSecondary, fontSize: 12, marginTop: 2 },
  label: { color: colors.textSecondary, fontSize: 11, fontWeight: "700", letterSpacing: 0.6, marginBottom: 6 },
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
  inputError: { borderColor: colors.anomaly, backgroundColor: "#1a0808" },

  gridRow: { flexDirection: "row", flexWrap: "wrap", marginTop: 16, gap: 12 },
  blockCard: {
    width: "47%",
    backgroundColor: colors.surface,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    padding: 14,
    minHeight: 130,
    alignItems: "center",
    justifyContent: "center",
    position: "relative",
  },
  blockLetterBadge: {
    position: "absolute",
    top: 8,
    left: 8,
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
  },
  blockLetter: { color: "#000", fontWeight: "900", fontSize: 12 },
  blockIconBox: { marginTop: 8, marginBottom: 10 },
  blockTitle: { color: colors.textPrimary, fontSize: 12, fontWeight: "800", textAlign: "center", letterSpacing: 0.4 },

  sketchBox: {
    marginTop: 16,
    alignItems: "center",
    backgroundColor: colors.surface,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    paddingVertical: 12,
  },

  autoBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    backgroundColor: colors.primary,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
  },
  validBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    backgroundColor: colors.success,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
  },
  autoBadgeText: { color: "#000", fontSize: 10, fontWeight: "900", letterSpacing: 0.5 },
  diagBtn: {
    width: 48,
    height: 48,
    borderRadius: 10,
    alignItems: "center",
    justifyContent: "center",
  },
  computeBtn: {
    marginTop: 12,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    paddingVertical: 12,
    paddingHorizontal: 14,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.primary,
    backgroundColor: "#1a0e05",
  },
  computeBtnText: { color: colors.primary, fontWeight: "900", fontSize: 13, letterSpacing: 0.8 },

  photo: { width: "100%", height: 180, borderRadius: 12, marginTop: 8 },
  removePhoto: {
    position: "absolute",
    top: 16,
    right: 8,
    backgroundColor: "rgba(0,0,0,0.7)",
    padding: 6,
    borderRadius: 14,
  },
  photoRow: { flexDirection: "row", gap: 8, marginTop: 8 },
  photoBtn: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    paddingVertical: 14,
    borderRadius: 10,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
  },
  photoBtnText: { color: colors.primary, fontWeight: "700", fontSize: 13 },

  wallGrid: { flexDirection: "row", flexWrap: "wrap", gap: 10, marginTop: 6 },
  wallCard: {
    width: "47%",
    backgroundColor: colors.surface,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    padding: 12,
    alignItems: "center",
  },
  wallCardActive: { borderColor: colors.primary, backgroundColor: "#1a0e05" },
  wallCardError: { borderColor: colors.anomaly },
  wallLabel: { color: colors.textPrimary, fontWeight: "900", fontSize: 14, marginTop: 6, letterSpacing: 0.8 },
  wallSub: { color: colors.textSecondary, fontSize: 10, marginTop: 2, textAlign: "center" },

  footer: {
    flexDirection: "row",
    gap: 10,
    padding: 16,
    borderTopWidth: 1,
    borderTopColor: colors.borderSubtle,
    backgroundColor: colors.bg,
  },
  btn: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    minHeight: 52,
    borderRadius: 12,
    paddingHorizontal: 16,
  },
  btnPrimary: { backgroundColor: colors.primary },
  btnPrimaryText: { color: "#000", fontWeight: "900", fontSize: 14, letterSpacing: 0.8 },
  btnSecondary: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.borderSubtle },
  btnSecondaryText: { color: colors.textPrimary, fontWeight: "800", fontSize: 13, letterSpacing: 0.5 },

  modalOverlay: { flex: 1, backgroundColor: "rgba(0,0,0,0.7)", justifyContent: "center", padding: 20 },
  modalCard: {
    backgroundColor: colors.surface,
    borderRadius: 16,
    padding: 18,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
  },
  modalTitle: { color: colors.textPrimary, fontWeight: "800", fontSize: 16 },
  modalSub: { color: colors.textSecondary, fontSize: 12, marginTop: 4, marginBottom: 12 },
  reportInput: {
    backgroundColor: colors.inputBg,
    color: colors.textPrimary,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.borderStrong,
    padding: 12,
    minHeight: 100,
    textAlignVertical: "top",
    fontSize: 14,
  },
});