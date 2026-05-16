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
  CoulissantSchema,
  MeasurementValues,
  PorteSchema,
  StandardSchema,
  TrapezeSchema,
} from "@/src/components/WindowSchema";
import AnomalyButton from "@/src/components/AnomalyButton";
import { api } from "@/src/services/api";
import { enqueueMesure, isOnline } from "@/src/services/offlineQueue";
import { colors, blockMeta } from "@/src/theme";

type BlockType = "standard" | "coulissant" | "porte" | "trapeze";

const BLOCKS: { key: BlockType; label: string; icon: keyof typeof Ionicons.glyphMap; desc: string }[] = [
  { key: "standard", label: "Standard", icon: "square-outline", desc: "Fenêtre rectangulaire classique" },
  { key: "coulissant", label: "Coulissant", icon: "swap-horizontal-outline", desc: "Baie coulissante 3L × 5H" },
  { key: "porte", label: "Porte", icon: "exit-outline", desc: "Porte d'entrée ou intérieure" },
  { key: "trapeze", label: "Trapèze", icon: "triangle-outline", desc: "Forme avec angle (pente)" },
];

export default function NewMesure() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const [blockType, setBlockType] = useState<BlockType | null>(null);
  const [label, setLabel] = useState("");
  const [values, setValues] = useState<MeasurementValues>({});
  const [photo, setPhoto] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const setVal = (k: string, v: string) => {
    setValues((s) => ({ ...s, [k]: v.replace(",", ".") }));
  };

  const pickPhoto = async (source: "camera" | "library") => {
    const fn =
      source === "camera"
        ? ImagePicker.requestCameraPermissionsAsync
        : ImagePicker.requestMediaLibraryPermissionsAsync;
    const perm = await fn();
    if (!perm.granted) {
      Alert.alert(
        "Permission refusée",
        "Activez l'accès dans les réglages de l'appareil.",
        [{ text: "OK" }]
      );
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
      if (a.base64) {
        setPhoto(`data:image/jpeg;base64,${a.base64}`);
      } else {
        setPhoto(a.uri);
      }
    }
  };

  const submit = async () => {
    if (!blockType) return;
    if (!label.trim()) {
      Alert.alert("Champ requis", "Indiquez le libellé (ex. Salon, Chambre).");
      return;
    }
    setSaving(true);
    const payload: Record<string, unknown> = {
      chantier_id: id,
      block_type: blockType,
      label: label.trim(),
      photo_url: photo,
      options: {},
    };
    Object.keys(values).forEach((k) => {
      const v = values[k];
      if (v && v.trim()) payload[k] = parseFloat(v);
    });
    try {
      const online = await isOnline();
      if (!online) {
        await enqueueMesure(payload);
        Alert.alert(
          "Hors ligne",
          "La mesure a été ajoutée à la file et sera synchronisée dès le retour du réseau.",
          [{ text: "OK", onPress: () => router.back() }]
        );
        return;
      }
      const res = await api.post("/mesures", payload);
      const alerts: string[] = res.data.alerts || [];
      if (alerts.length > 0) {
        Alert.alert("Alertes détectées", alerts.join("\n"), [
          { text: "Retour au chantier", onPress: () => router.back() },
        ]);
      } else {
        router.back();
      }
    } catch (e) {
      // network error: queue it offline as fallback
      await enqueueMesure(payload);
      Alert.alert(
        "Réseau indisponible",
        "Mesure mise en file d'attente — sera envoyée au retour du réseau.",
        [{ text: "OK", onPress: () => router.back() }]
      );
    } finally {
      setSaving(false);
    }
  };

  if (!blockType) {
    return (
      <SafeAreaView style={styles.flex} edges={["bottom"]}>
        <ScrollView contentContainerStyle={{ padding: 20 }}>
          <Text style={styles.heading}>TYPE DE BLOC</Text>
          <Text style={styles.subheading}>Choisissez la forme à mesurer</Text>
          <View style={{ marginTop: 20, gap: 12 }}>
            {BLOCKS.map((b) => (
              <TouchableOpacity
                key={b.key}
                testID={`block-type-${b.key}`}
                onPress={() => setBlockType(b.key)}
                style={styles.blockCard}
                activeOpacity={0.7}
              >
                <View style={styles.blockIcon}>
                  <Ionicons name={b.icon} size={32} color={colors.primary} />
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={styles.blockLabel}>{b.label}</Text>
                  <Text style={styles.blockDesc}>{b.desc}</Text>
                </View>
                <Ionicons name="chevron-forward" size={22} color={colors.textSecondary} />
              </TouchableOpacity>
            ))}
          </View>
        </ScrollView>
      </SafeAreaView>
    );
  }

  const meta = blockMeta[blockType];

  const renderSchema = () => {
    const props = { values, onChange: setVal };
    switch (blockType) {
      case "standard":
        return <StandardSchema {...props} />;
      case "coulissant":
        return <CoulissantSchema {...props} />;
      case "porte":
        return <PorteSchema {...props} />;
      case "trapeze":
        return <TrapezeSchema {...props} />;
    }
  };

  return (
    <SafeAreaView style={styles.flex} edges={["bottom"]}>
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        style={styles.flex}
      >
        <ScrollView
          contentContainerStyle={{ padding: 16, paddingBottom: 200 }}
          keyboardShouldPersistTaps="handled"
        >
          <View style={styles.typeRow}>
            <View style={styles.typeBadge}>
              <Text style={styles.typeBadgeText}>{meta.label.toUpperCase()}</Text>
            </View>
            <TouchableOpacity
              testID="change-block-type"
              onPress={() => {
                setBlockType(null);
                setValues({});
              }}
              activeOpacity={0.7}
            >
              <Text style={styles.changeLink}>Changer</Text>
            </TouchableOpacity>
          </View>

          <Text style={styles.label}>Libellé</Text>
          <TextInput
            testID="mesure-label-input"
            value={label}
            onChangeText={setLabel}
            placeholder="ex. Salon, Chambre 1..."
            placeholderTextColor={colors.placeholder}
            style={styles.input}
          />

          <Text style={[styles.label, { marginTop: 18 }]}>Schéma & mesures (mm)</Text>
          {renderSchema()}

          <Text style={[styles.label, { marginTop: 24 }]}>Photo</Text>
          {photo ? (
            <View>
              <Image source={{ uri: photo }} style={styles.photo} />
              <TouchableOpacity
                testID="remove-photo-button"
                onPress={() => setPhoto(null)}
                style={styles.removePhoto}
              >
                <Ionicons name="trash" size={16} color="#fff" />
              </TouchableOpacity>
            </View>
          ) : (
            <View style={styles.photoRow}>
              <TouchableOpacity
                testID="photo-camera-button"
                onPress={() => pickPhoto("camera")}
                style={styles.photoBtn}
                activeOpacity={0.7}
              >
                <Ionicons name="camera" size={22} color={colors.primary} />
                <Text style={styles.photoBtnText}>Caméra</Text>
              </TouchableOpacity>
              <TouchableOpacity
                testID="photo-library-button"
                onPress={() => pickPhoto("library")}
                style={styles.photoBtn}
                activeOpacity={0.7}
              >
                <Ionicons name="images" size={22} color={colors.primary} />
                <Text style={styles.photoBtnText}>Galerie</Text>
              </TouchableOpacity>
            </View>
          )}

          <TouchableOpacity
            testID="save-mesure-button"
            onPress={submit}
            disabled={saving}
            style={styles.saveBtn}
            activeOpacity={0.85}
          >
            {saving ? (
              <ActivityIndicator color="#000" />
            ) : (
              <>
                <Ionicons name="checkmark-circle" size={22} color="#000" />
                <Text style={styles.saveBtnText}>ENREGISTRER L'OUVERTURE</Text>
              </>
            )}
          </TouchableOpacity>
        </ScrollView>
      </KeyboardAvoidingView>

      <AnomalyButton
        pageContext={`mesure_form:${blockType}`}
        dataSnapshot={{ chantier_id: id, block_type: blockType, label, values }}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: colors.bg },
  heading: {
    color: colors.textPrimary,
    fontSize: 24,
    fontWeight: "900",
    letterSpacing: 1,
    marginTop: 6,
  },
  subheading: { color: colors.textSecondary, marginTop: 4 },
  blockCard: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.surface,
    borderColor: colors.borderSubtle,
    borderWidth: 1,
    borderRadius: 12,
    padding: 16,
    gap: 12,
    minHeight: 80,
  },
  blockIcon: {
    width: 56,
    height: 56,
    borderRadius: 8,
    backgroundColor: colors.bg,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    alignItems: "center",
    justifyContent: "center",
  },
  blockLabel: { color: colors.textPrimary, fontSize: 18, fontWeight: "900" },
  blockDesc: { color: colors.textSecondary, fontSize: 12, marginTop: 2 },
  typeRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 16,
  },
  typeBadge: {
    backgroundColor: colors.primary,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 4,
  },
  typeBadgeText: { color: "#000", fontWeight: "900", letterSpacing: 1, fontSize: 13 },
  changeLink: {
    marginLeft: "auto",
    color: colors.primary,
    fontWeight: "700",
    textDecorationLine: "underline",
  },
  label: {
    color: colors.textSecondary,
    fontSize: 11,
    fontWeight: "700",
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
  photo: {
    width: "100%",
    height: 200,
    borderRadius: 10,
    backgroundColor: colors.surface,
  },
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
  saveBtn: {
    marginTop: 24,
    minHeight: 64,
    backgroundColor: colors.primary,
    borderRadius: 8,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
  },
  saveBtnText: { color: "#000", fontWeight: "900", letterSpacing: 1, fontSize: 15 },
});
