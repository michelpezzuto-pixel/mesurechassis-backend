/**
 * ☕ CafeJetonModal — Pop-up « Vous avez gagné un café ! » (Priorité 4)
 *
 * Étapes :
 *   1. "won"     : félicitations + gros bouton VERT « VALIDATION POMPISTE »
 *                  (réservé au pompiste de la station) + « Plus tard ».
 *   2. "pin"     : le pompiste tape le code PIN à 4 chiffres de sa station
 *                  sur le téléphone de l'artisan.
 *   3. "success" : café validé, bonne dégustation !
 *
 * ⚠️ Ne bloque jamais l'artisan : « Plus tard » ferme la pop-up, le jeton
 * reste consommable pendant 30 jours via l'écran « Mes cafés ».
 */
import { Ionicons } from "@expo/vector-icons";
import React, { useState } from "react";
import {
  ActivityIndicator,
  Modal,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";

import RatingPromptModal from "@/src/components/RatingPromptModal";
import { api } from "@/src/services/api";
import {
  markPromptDismissed,
  markPromptShown,
  shouldShowRatingPrompt,
  triggerNativeReview,
} from "@/src/services/ratingPrompt";

const GREEN = "#10B981";

export type CafeJeton = {
  id: string;
  status: string;
  earned_at?: string;
  expires_at?: string;
};

type Props = {
  visible: boolean;
  jeton: CafeJeton | null;
  stationName?: string;
  /** Fermeture (Plus tard ou après succès). `consumed` = jeton validé. */
  onClose: (consumed: boolean) => void;
};

export default function CafeJetonModal({
  visible,
  jeton,
  stationName,
  onClose,
}: Props) {
  const [step, setStep] = useState<"won" | "pin" | "success">("won");
  const [pin, setPin] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [ratingVisible, setRatingVisible] = useState(false);

  const reset = () => {
    setStep("won");
    setPin("");
    setError("");
    setSubmitting(false);
  };

  const close = (consumed: boolean) => {
    reset();
    onClose(consumed);
  };

  const submitPin = async () => {
    if (!jeton || pin.length !== 4) return;
    setSubmitting(true);
    setError("");
    try {
      await api.post(`/cafe/jetons/${jeton.id}/consume`, { pin });
      setStep("success");
      // ⭐ Déclencheur Rating Prompt (feature flag OFF par défaut — voir
      //    src/services/ratingPrompt.ts). Le check `shouldShowRatingPrompt`
      //    gère l'activation + les throttles (max 1× / 90 jours, iOS only).
      shouldShowRatingPrompt()
        .then(async (should) => {
          if (should) {
            await markPromptShown();
            setRatingVisible(true);
          }
        })
        .catch(() => {});
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      setError(
        typeof detail === "string" ? detail : "Validation impossible. Réessayez.",
      );
      setPin("");
    } finally {
      setSubmitting(false);
    }
  };

  const handleRate = async () => {
    setRatingVisible(false);
    await triggerNativeReview();
  };

  const handleDismissRating = async () => {
    setRatingVisible(false);
    await markPromptDismissed();
  };

  if (!jeton) return null;

  return (
    <>
      <Modal visible={visible} transparent animationType="fade">
      <View style={styles.backdrop}>
        <View style={styles.card}>
          {step === "won" && (
            <>
              <Text style={styles.bigEmoji}>☕</Text>
              <Text style={styles.title}>Vous avez gagné un café !</Text>
              <Text style={styles.subtitle}>
                Passez à la station {stationName || "partenaire"} et présentez
                cet écran au pompiste pour déguster votre café offert.
              </Text>
              <TouchableOpacity
                style={styles.greenBtn}
                onPress={() => setStep("pin")}
                activeOpacity={0.85}
                testID="cafe-validate-btn"
              >
                <Ionicons name="checkmark-circle" size={22} color="#FFF" />
                <Text style={styles.greenBtnText}>VALIDATION POMPISTE</Text>
              </TouchableOpacity>
              <Text style={styles.pompisteHint}>
                🔒 Bouton réservé au pompiste de la station
              </Text>
              <TouchableOpacity
                onPress={() => close(false)}
                hitSlop={10}
                testID="cafe-later-btn"
              >
                <Text style={styles.laterText}>Plus tard — je continue mon travail</Text>
              </TouchableOpacity>
            </>
          )}

          {step === "pin" && (
            <>
              <View style={styles.pinIconWrap}>
                <Ionicons name="keypad" size={30} color={GREEN} />
              </View>
              <Text style={styles.title}>Code PIN station</Text>
              <Text style={styles.subtitle}>
                Pompiste : saisissez le code à 4 chiffres de votre station pour
                valider ce café.
              </Text>
              <TextInput
                value={pin}
                onChangeText={(v) => {
                  setPin(v.replace(/[^0-9]/g, "").slice(0, 4));
                  setError("");
                }}
                keyboardType="number-pad"
                maxLength={4}
                autoFocus
                secureTextEntry
                style={styles.pinInput}
                placeholder="• • • •"
                placeholderTextColor="#555"
                testID="cafe-pin-input"
              />
              {!!error && <Text style={styles.errorText}>{error}</Text>}
              <TouchableOpacity
                style={[
                  styles.greenBtn,
                  (pin.length !== 4 || submitting) && { opacity: 0.4 },
                ]}
                disabled={pin.length !== 4 || submitting}
                onPress={submitPin}
                activeOpacity={0.85}
                testID="cafe-pin-submit"
              >
                {submitting ? (
                  <ActivityIndicator color="#FFF" />
                ) : (
                  <>
                    <Ionicons name="cafe" size={20} color="#FFF" />
                    <Text style={styles.greenBtnText}>VALIDER LE CAFÉ</Text>
                  </>
                )}
              </TouchableOpacity>
              <TouchableOpacity onPress={() => setStep("won")} hitSlop={10}>
                <Text style={styles.laterText}>← Retour</Text>
              </TouchableOpacity>
            </>
          )}

          {step === "success" && (
            <>
              <Text style={styles.bigEmoji}>🎉</Text>
              <Text style={styles.title}>Café validé !</Text>
              <Text style={styles.subtitle}>
                Bonne dégustation ! Créez une nouvelle ouverture pour gagner
                votre prochain café.
              </Text>
              <TouchableOpacity
                style={styles.greenBtn}
                onPress={() => close(true)}
                activeOpacity={0.85}
                testID="cafe-success-close"
              >
                <Text style={styles.greenBtnText}>MERCI !</Text>
              </TouchableOpacity>
            </>
          )}
        </View>
      </View>
    </Modal>
    <RatingPromptModal
      visible={ratingVisible}
      onRate={handleRate}
      onDismiss={handleDismissRating}
    />
    </>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.75)",
    alignItems: "center",
    justifyContent: "center",
    padding: 24,
  },
  card: {
    width: "100%",
    maxWidth: 380,
    backgroundColor: "#1A1A1E",
    borderRadius: 20,
    padding: 26,
    alignItems: "center",
    borderWidth: 1,
    borderColor: GREEN + "44",
  },
  bigEmoji: { fontSize: 54, marginBottom: 8 },
  pinIconWrap: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: GREEN + "18",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 8,
  },
  title: {
    fontSize: 20,
    fontWeight: "800",
    color: "#FFF",
    textAlign: "center",
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 14,
    lineHeight: 20,
    color: "#A6A6AD",
    textAlign: "center",
    marginBottom: 18,
  },
  greenBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    backgroundColor: GREEN,
    borderRadius: 14,
    paddingVertical: 15,
    paddingHorizontal: 22,
    alignSelf: "stretch",
    minHeight: 48,
  },
  greenBtnText: { fontSize: 15, fontWeight: "800", color: "#FFF" },
  pompisteHint: {
    fontSize: 11,
    color: "#6E6E76",
    marginTop: 8,
    marginBottom: 14,
  },
  laterText: {
    fontSize: 13,
    color: "#8A8A92",
    fontWeight: "600",
    padding: 6,
  },
  pinInput: {
    backgroundColor: "#0C0C0E",
    borderRadius: 12,
    borderWidth: 1,
    borderColor: GREEN + "55",
    color: "#FFF",
    fontSize: 28,
    fontWeight: "800",
    textAlign: "center",
    letterSpacing: 12,
    paddingVertical: 12,
    alignSelf: "stretch",
    marginBottom: 12,
  },
  errorText: {
    fontSize: 12,
    color: "#EF4444",
    textAlign: "center",
    marginBottom: 10,
  },
});
