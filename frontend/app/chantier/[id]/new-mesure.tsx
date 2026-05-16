import React, { useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Image,
  KeyboardAvoidingView,
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
import AnomalyButton from "@/src/components/AnomalyButton";
import { api } from "@/src/services/api";
import { enqueueMesure, isOnline } from "@/src/services/offlineQueue";
import { colors } from "@/src/theme";

type BlockType = "standard" | "coulissant" | "porte" | "trapeze";
type WallType = "ite" | "iti" | "crepi_simple";

const BLOCKS: { key: BlockType; letter: string; label: string; icon: keyof typeof Ionicons.glyphMap }[] = [
  { key: "standard", letter: "A", label: "CHÂSSIS STANDARD", icon: "square-outline" },
  { key: "coulissant", letter: "B", label: "CHÂSSIS COULISSANT", icon: "swap-horizontal-outline" },
  { key: "porte", letter: "C", label: "PORTE D'ENTRÉE", icon: "exit-outline" },
  { key: "trapeze", letter: "D", label: "CHÂSSIS TRAPÈZE", icon: "triangle-outline" },
];

type Step = 0 | 1 | 2;

type Step2Form = {
  bay_height: string;
  bay_width: string;
  bay_diagonal: string;
  floor_reserve: string;
};

type Step3Form = {
  bloc_thickness: string;
  wall_type: WallType | null;
  insulation_thickness: string;
  finish_outer: string;
  finish_inner: string;
};

export default function NewMesure() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const [step, setStep] = useState<Step>(0);
  const [blockType, setBlockType] = useState<BlockType | null>(null);
  const [label, setLabel] = useState("");
  const [photo, setPhoto] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const [s2, setS2] = useState<Step2Form>({
    bay_height: "",
    bay_width: "",
    bay_diagonal: "",
    floor_reserve: "",
  });
  const [s2Errors, setS2Errors] = useState<Partial<Record<keyof Step2Form, boolean>>>({});

  const [s3, setS3] = useState<Step3Form>({
    bloc_thickness: "",
    wall_type: null,
    insulation_thickness: "",
    finish_outer: "",
    finish_inner: "",
  });
  const [s3Errors, setS3Errors] = useState<Partial<Record<keyof Step3Form, boolean>>>({});

  // ---------------------------------------------------------------- Step 1
  const onPickBlock = (key: BlockType) => {
    setBlockType(key);
    setStep(1);
  };

  // ---------------------------------------------------------------- Step 2
  const validateStep2 = (): boolean => {
    const errors: Partial<Record<keyof Step2Form, boolean>> = {};
    (Object.keys(s2) as (keyof Step2Form)[]).forEach((k) => {
      if (!s2[k] || s2[k].trim().length === 0 || Number.isNaN(parseFloat(s2[k]))) {
        errors[k] = true;
      }
    });
    if (!label.trim()) {
      Alert.alert("Libellé manquant", "Indiquez un libellé (ex. Salon, Chambre 1...).");
      return false;
    }
    setS2Errors(errors);
    return Object.keys(errors).length === 0;
  };

  const goToStep3 = () => {
    if (validateStep2()) setStep(2);
  };

  // ---------------------------------------------------------------- Step 3
  const validateStep3 = (): boolean => {
    const errors: Partial<Record<keyof Step3Form, boolean>> = {};
    if (!s3.bloc_thickness || Number.isNaN(parseFloat(s3.bloc_thickness))) {
      errors.bloc_thickness = true;
    }
    if (!s3.wall_type) errors.wall_type = true;
    setS3Errors(errors);
    return Object.keys(errors).length === 0;
  };

  // ---------------------------------------------------------------- Photo
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
      source === "camera"
        ? ImagePicker.launchCameraAsync
        : ImagePicker.launchImageLibraryAsync;
    const res = await launcher({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 0.5,
      base64: true,
    });
    if (!res.canceled && res.assets[0]) {
      const a = res.assets[0];
      setPhoto(a.base64 ? `data:image/jpeg;base64,${a.base64}` : a.uri);
    }
  };

  // ---------------------------------------------------------------- Submit
  const submit = async () => {
    if (!blockType) return;
    if (!validateStep3()) return;
    setSaving(true);
    const payload: Record<string, unknown> = {
      chantier_id: id,
      block_type: blockType,
      label: label.trim(),
      photo_url: photo,
      bay_height: parseFloat(s2.bay_height),
      bay_width: parseFloat(s2.bay_width),
      bay_diagonal: parseFloat(s2.bay_diagonal),
      floor_reserve: parseFloat(s2.floor_reserve),
      bloc_thickness: parseFloat(s3.bloc_thickness),
      wall_type: s3.wall_type,
      options: {},
    };
    if (s3.insulation_thickness) payload.insulation_thickness = parseFloat(s3.insulation_thickness);
    if (s3.finish_outer) payload.finish_outer = parseFloat(s3.finish_outer);
    if (s3.finish_inner) payload.finish_inner = parseFloat(s3.finish_inner);

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

  // ============================ RENDER ====================================

  return (
    <SafeAreaView style={styles.flex} edges={["bottom"]}>
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        style={styles.flex}
      >
        <View style={styles.stepBar}>
          {[0, 1, 2].map((i) => (
            <View
              key={i}
              testID={`step-pill-${i + 1}`}
              style={[
                styles.stepPill,
                i <= step && styles.stepPillActive,
                i === step && styles.stepPillCurrent,
              ]}
            >
              <Text style={[styles.stepPillText, i <= step && { color: "#000" }]}>
                {i + 1}
              </Text>
            </View>
          ))}
        </View>

        <ScrollView
          contentContainerStyle={{ padding: 16, paddingBottom: 200 }}
          keyboardShouldPersistTaps="handled"
        >
          {step === 0 && <Step1Picker onPick={onPickBlock} />}

          {step === 1 && blockType && (
            <Step2Bay
              blockType={blockType}
              label={label}
              setLabel={setLabel}
              values={s2}
              setValues={setS2}
              errors={s2Errors}
              photo={photo}
              setPhoto={setPhoto}
              pickPhoto={pickPhoto}
            />
          )}

          {step === 2 && (
            <Step3Wall values={s3} setValues={setS3} errors={s3Errors} />
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
              testID="wizard-next-step2"
              onPress={goToStep3}
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

      {step >= 1 && (
        <AnomalyButton
          pageContext={`mesure_wizard:step${step + 1}:${blockType}`}
          dataSnapshot={{ chantier_id: id, block_type: blockType, label, step2: s2, step3: s3 }}
        />
      )}
    </SafeAreaView>
  );
}

// ====================== STEP 1 — Block type picker ========================
function Step1Picker({ onPick }: { onPick: (k: BlockType) => void }) {
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

// ====================== STEP 2 — Raw bay measurements =====================
function Step2Bay({
  blockType,
  label,
  setLabel,
  values,
  setValues,
  errors,
  photo,
  setPhoto,
  pickPhoto,
}: {
  blockType: BlockType;
  label: string;
  setLabel: (v: string) => void;
  values: Step2Form;
  setValues: (v: Step2Form) => void;
  errors: Partial<Record<keyof Step2Form, boolean>>;
  photo: string | null;
  setPhoto: (v: string | null) => void;
  pickPhoto: (s: "camera" | "library") => void;
}) {
  const set = (k: keyof Step2Form, v: string) =>
    setValues({ ...values, [k]: v.replace(",", ".") });
  const Sketch = blockType === "trapeze" ? RawBaySchemaTrapeze : RawBaySchemaRect;
  return (
    <View>
      <Text style={styles.h1}>PRISE À LA MESURE</Text>
      <Text style={styles.h2}>Cotes de la baie brute</Text>

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
        <Sketch />
      </View>

      <BayField
        testID="input-bay-height"
        label="HAUTEUR (mm)"
        value={values.bay_height}
        onChange={(v) => set("bay_height", v)}
        error={errors.bay_height}
      />
      <BayField
        testID="input-bay-width"
        label="LARGEUR (mm)"
        value={values.bay_width}
        onChange={(v) => set("bay_width", v)}
        error={errors.bay_width}
      />
      <BayField
        testID="input-bay-diagonal"
        label="DIAGONALE (mm)"
        value={values.bay_diagonal}
        onChange={(v) => set("bay_diagonal", v)}
        error={errors.bay_diagonal}
      />

      <View style={styles.criticalBlock}>
        <View style={styles.criticalHeader}>
          <Ionicons name="warning" size={18} color={colors.anomaly} />
          <Text style={styles.criticalTitle}>RÉSERVE SOL FINI (mm)</Text>
        </View>
        <Text style={styles.criticalHelp}>
          Mesurez la distance entre le sol brut et le sol fini prévu. Cette cote est OBLIGATOIRE.
        </Text>
        <TextInput
          testID="input-floor-reserve"
          value={values.floor_reserve}
          onChangeText={(v) => set("floor_reserve", v.replace(",", "."))}
          placeholder="0"
          placeholderTextColor={colors.placeholder}
          keyboardType="decimal-pad"
          style={[styles.input, styles.inputCritical, errors.floor_reserve && styles.inputErrorCritical]}
        />
        {errors.floor_reserve && (
          <View style={styles.errorRow}>
            <Ionicons name="alert-circle" size={14} color={colors.anomaly} />
            <Text style={styles.errorText}>OBLIGATOIRE — MANQUANT</Text>
          </View>
        )}
      </View>

      <View style={styles.validationCallout}>
        <Text style={styles.calloutBold}>VALIDATION STRICTE :</Text>
        <Text style={styles.calloutBody}>
          Hauteur, Largeur, Diagonale et Réserve Sol Fini sont toutes OBLIGATOIRES avant validation.
        </Text>
      </View>

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

function BayField({
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
  error?: boolean;
}) {
  return (
    <View style={{ marginTop: 14 }}>
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
      {error && (
        <View style={styles.errorRow}>
          <Ionicons name="alert-circle" size={14} color={colors.anomaly} />
          <Text style={styles.errorText}>OBLIGATOIRE — MANQUANT</Text>
        </View>
      )}
    </View>
  );
}

// ====================== STEP 3 — Wall & isolation =========================
const WALL_OPTIONS: { key: WallType; letter: string; title: string; sub1: string; sub2: string; variant: "ite" | "iti" | "crepi" }[] = [
  {
    key: "ite",
    letter: "A",
    title: "FAÇADE ISOLANTE EXTÉRIEURE (ITE)",
    sub1: "Épaisseur Isolant (mm)",
    sub2: "Épaisseur Crépi (mm)",
    variant: "ite",
  },
  {
    key: "iti",
    letter: "B",
    title: "ISOLATION INTÉRIEURE (ITI)",
    sub1: "Épaisseur Isolant (mm)",
    sub2: "Épaisseur Plâtre/Finition (mm)",
    variant: "iti",
  },
  {
    key: "crepi_simple",
    letter: "C",
    title: "CRÉPI SIMPLE",
    sub1: "Épaisseur Crépi Ext. (mm)",
    sub2: "Épaisseur Crépi Int. (mm)",
    variant: "crepi",
  },
];

function Step3Wall({
  values,
  setValues,
  errors,
}: {
  values: Step3Form;
  setValues: (v: Step3Form) => void;
  errors: Partial<Record<keyof Step3Form, boolean>>;
}) {
  const set = (k: keyof Step3Form, v: any) => setValues({ ...values, [k]: v });
  return (
    <View>
      <Text style={styles.h1}>CONCEPTION MAÇONNERIE & ISOLATION</Text>
      <Text style={[styles.h2, { color: colors.textSecondary }]}>(INDICATIF)</Text>

      <View style={styles.mainWallCard}>
        <Text style={styles.mainWallTitle}>MUR DE BASE</Text>
        <Text style={styles.label}>Épaisseur Bloc Béton (mm)</Text>
        <TextInput
          testID="input-bloc-thickness"
          value={values.bloc_thickness}
          onChangeText={(v) => set("bloc_thickness", v.replace(",", "."))}
          placeholder="Ex: 200"
          placeholderTextColor={colors.placeholder}
          keyboardType="decimal-pad"
          style={[styles.input, errors.bloc_thickness && styles.inputError]}
        />
        {errors.bloc_thickness && (
          <View style={styles.errorRow}>
            <Ionicons name="alert-circle" size={14} color={colors.anomaly} />
            <Text style={styles.errorText}>OBLIGATOIRE — MANQUANT</Text>
          </View>
        )}
      </View>

      <Text style={[styles.label, { marginTop: 22 }]}>Type de paroi (sélectionner)</Text>
      {errors.wall_type && (
        <View style={styles.errorRow}>
          <Ionicons name="alert-circle" size={14} color={colors.anomaly} />
          <Text style={styles.errorText}>OBLIGATOIRE — MANQUANT</Text>
        </View>
      )}

      {WALL_OPTIONS.map((opt) => {
        const active = values.wall_type === opt.key;
        return (
          <TouchableOpacity
            key={opt.key}
            testID={`wall-type-${opt.key}`}
            onPress={() => set("wall_type", opt.key)}
            activeOpacity={0.75}
            style={[styles.wallCard, active && styles.wallCardActive]}
          >
            <View style={styles.wallCardHeader}>
              <View style={[styles.blockLetterBadge, active && { backgroundColor: colors.primary }]}>
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
                <SubField
                  testID={`wall-${opt.key}-sub1`}
                  label={opt.sub1}
                  value={values.insulation_thickness}
                  onChange={(v) => set("insulation_thickness", v.replace(",", "."))}
                />
                <SubField
                  testID={`wall-${opt.key}-sub2`}
                  label={opt.sub2}
                  value={opt.key === "crepi_simple" ? values.finish_inner : values.finish_outer}
                  onChange={(v) => {
                    if (opt.key === "crepi_simple") set("finish_inner", v.replace(",", "."));
                    else set("finish_outer", v.replace(",", "."));
                  }}
                />
                {opt.key === "crepi_simple" && (
                  <SubField
                    testID="wall-crepi-ext"
                    label="Épaisseur Crépi Ext. (mm)"
                    value={values.finish_outer}
                    onChange={(v) => set("finish_outer", v.replace(",", "."))}
                  />
                )}
              </View>
            )}
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

function SubField({
  testID,
  label,
  value,
  onChange,
}: {
  testID: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <View style={{ marginTop: 10 }}>
      <Text style={styles.subFieldLabel}>{label} <Text style={styles.indicatifInline}>(INDICATIF)</Text></Text>
      <TextInput
        testID={testID}
        value={value}
        onChangeText={onChange}
        placeholder="0"
        placeholderTextColor={colors.placeholder}
        keyboardType="decimal-pad"
        style={styles.input}
      />
    </View>
  );
}

// ============================ Styles =====================================
const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: colors.bg },
  stepBar: {
    flexDirection: "row",
    gap: 8,
    justifyContent: "center",
    paddingTop: 12,
    paddingBottom: 8,
    backgroundColor: colors.bg,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSubtle,
  },
  stepPill: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    alignItems: "center",
    justifyContent: "center",
  },
  stepPillActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  stepPillCurrent: {
    transform: [{ scale: 1.1 }],
  },
  stepPillText: { color: colors.textSecondary, fontWeight: "900", fontSize: 14 },
  h1: { color: colors.textPrimary, fontSize: 20, fontWeight: "900", letterSpacing: 1 },
  h2: { color: colors.textPrimary, fontSize: 14, marginTop: 2, fontWeight: "700", letterSpacing: 0.8 },
  // Step 1
  gridRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 12,
    marginTop: 20,
  },
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
  blockTitle: {
    color: colors.textPrimary,
    fontWeight: "900",
    fontSize: 13,
    letterSpacing: 0.6,
    textAlign: "center",
  },
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
    minHeight: 56,
    paddingHorizontal: 14,
    fontSize: 16,
    fontWeight: "600",
  },
  inputError: { borderColor: colors.anomaly },
  inputCritical: {
    borderColor: colors.anomaly,
    backgroundColor: "#1c0606",
  },
  inputErrorCritical: {
    borderColor: colors.anomaly,
    backgroundColor: "#260a0a",
  },
  errorRow: { flexDirection: "row", alignItems: "center", gap: 4, marginTop: 6 },
  errorText: {
    color: colors.anomaly,
    fontWeight: "900",
    fontSize: 11,
    letterSpacing: 1,
  },
  sketchBox: {
    backgroundColor: colors.bg,
    borderColor: colors.borderSubtle,
    borderWidth: 1,
    borderRadius: 12,
    marginTop: 16,
    padding: 12,
    alignItems: "center",
  },
  criticalBlock: {
    marginTop: 22,
    padding: 14,
    borderRadius: 10,
    borderWidth: 2,
    borderColor: colors.anomaly,
    backgroundColor: "#1a0707",
  },
  criticalHeader: { flexDirection: "row", alignItems: "center", gap: 6, marginBottom: 4 },
  criticalTitle: {
    color: colors.anomaly,
    fontWeight: "900",
    fontSize: 13,
    letterSpacing: 1,
  },
  criticalHelp: { color: colors.textSecondary, fontSize: 12, marginBottom: 10 },
  validationCallout: {
    marginTop: 18,
    padding: 12,
    borderRadius: 8,
    backgroundColor: colors.surface,
    borderColor: colors.borderSubtle,
    borderWidth: 1,
  },
  calloutBold: { color: colors.anomaly, fontWeight: "900", letterSpacing: 0.8, fontSize: 13 },
  calloutBody: { color: colors.textSecondary, fontSize: 12, marginTop: 4 },
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
  mainWallTitle: {
    color: colors.primary,
    fontWeight: "900",
    fontSize: 14,
    letterSpacing: 1.2,
    marginBottom: 12,
  },
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
  indicatif: {
    color: colors.textSecondary,
    fontSize: 10,
    fontWeight: "700",
    letterSpacing: 0.8,
    marginTop: 2,
  },
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
  btn: {
    flex: 1,
    minHeight: 60,
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
