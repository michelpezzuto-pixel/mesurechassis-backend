/**
 * ⭐ Modale "Un café, une note ?" — Pré-prompt de rating custom.
 *
 * Affichée après validation d'un café Jeton (état d'esprit positif = pic
 * de conversion). Copywriting fourni par Michel (fondateur menuisier).
 *
 * Étape 1 (cette modale) → si "Laisser 5 étoiles" → Étape 2 (StoreKit natif).
 * Voir : src/services/ratingPrompt.ts
 */
import { Ionicons } from "@expo/vector-icons";
import React from "react";
import {
  Modal,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";

type Props = {
  visible: boolean;
  onRate: () => void;
  onDismiss: () => void;
};

export default function RatingPromptModal({
  visible,
  onRate,
  onDismiss,
}: Props) {
  return (
    <Modal visible={visible} transparent animationType="fade">
      <View style={styles.backdrop}>
        <View style={styles.card}>
          <View style={styles.starsRow}>
            {[0, 1, 2, 3, 4].map((i) => (
              <Ionicons key={i} name="star" size={30} color="#FFB020" />
            ))}
          </View>

          <Text style={styles.title}>Un café, une note ?</Text>

          <Text style={styles.body}>
            Content de votre café ? Si MesureChâssis vous aide au quotidien sur
            vos chantiers, un petit avis 5 étoiles nous aide énormément à
            continuer le développement.
          </Text>
          <Text style={styles.signature}>Merci, confrère ! ☕</Text>

          <TouchableOpacity
            style={styles.primaryBtn}
            onPress={onRate}
            activeOpacity={0.85}
            testID="rating-prompt-rate"
          >
            <Ionicons name="star" size={16} color="#0A0A0C" />
            <Text style={styles.primaryBtnText}>LAISSER 5 ÉTOILES</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.secondaryBtn}
            onPress={onDismiss}
            activeOpacity={0.7}
            testID="rating-prompt-dismiss"
          >
            <Text style={styles.secondaryBtnText}>Pas maintenant</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.75)",
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 24,
  },
  card: {
    backgroundColor: "#FFFFFF",
    borderRadius: 20,
    paddingVertical: 26,
    paddingHorizontal: 22,
    width: "100%",
    maxWidth: 380,
    alignItems: "center",
    shadowColor: "#000",
    shadowOpacity: 0.4,
    shadowRadius: 24,
    shadowOffset: { width: 0, height: 12 },
    elevation: 10,
  },
  starsRow: {
    flexDirection: "row",
    gap: 4,
    marginBottom: 14,
  },
  title: {
    fontSize: 21,
    fontWeight: "800",
    color: "#0A0A0C",
    marginBottom: 10,
    letterSpacing: -0.4,
    textAlign: "center",
  },
  body: {
    fontSize: 14.5,
    color: "#3F3F46",
    lineHeight: 20,
    textAlign: "center",
    marginBottom: 6,
  },
  signature: {
    fontSize: 13.5,
    color: "#FF5A00",
    fontWeight: "700",
    marginBottom: 20,
    textAlign: "center",
  },
  primaryBtn: {
    backgroundColor: "#FF5A00",
    borderRadius: 999,
    paddingVertical: 14,
    paddingHorizontal: 22,
    width: "100%",
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    gap: 8,
  },
  primaryBtnText: {
    color: "#0A0A0C",
    fontSize: 14,
    fontWeight: "900",
    letterSpacing: 0.4,
  },
  secondaryBtn: {
    marginTop: 10,
    paddingVertical: 12,
    width: "100%",
    alignItems: "center",
  },
  secondaryBtnText: {
    color: "#6B7280",
    fontSize: 13.5,
    fontWeight: "600",
  },
});
