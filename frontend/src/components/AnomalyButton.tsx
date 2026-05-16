import React, { useState } from "react";
import {
  Modal,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
  Alert,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import * as Haptics from "expo-haptics";
import { api } from "@/src/services/api";
import { colors } from "@/src/theme";

type Props = {
  pageContext: string;
  dataSnapshot?: Record<string, unknown>;
};

export default function AnomalyButton({ pageContext, dataSnapshot }: Props) {
  const [open, setOpen] = useState(false);
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const openModal = async () => {
    if (Platform.OS !== "web") {
      await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy);
    }
    setOpen(true);
  };

  const submit = async () => {
    if (!comment.trim()) {
      Alert.alert("Commentaire requis", "Décrivez l'anomalie ou l'idée.");
      return;
    }
    setSubmitting(true);
    try {
      await api.post("/feedbacks", {
        page_context: pageContext,
        user_comment: comment.trim(),
        encoded_data_snapshot: dataSnapshot ?? {},
      });
      setComment("");
      setOpen(false);
      Alert.alert("Merci !", "Votre signalement a été envoyé à l'admin.");
    } catch (e) {
      Alert.alert("Erreur", "Envoi impossible. Réessayez.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <TouchableOpacity
        testID="report-anomaly-button"
        onPress={openModal}
        activeOpacity={0.7}
        style={styles.fab}
      >
        <Ionicons name="warning" size={24} color="#fff" />
        <Text style={styles.fabText}>SIGNALER UNE ANOMALIE / IDÉE</Text>
      </TouchableOpacity>

      <Modal visible={open} transparent animationType="fade" onRequestClose={() => setOpen(false)}>
        <KeyboardAvoidingView
          behavior={Platform.OS === "ios" ? "padding" : "height"}
          style={styles.overlay}
        >
          <View style={styles.card}>
            <View style={styles.header}>
              <Ionicons name="warning" size={22} color={colors.anomaly} />
              <Text style={styles.title}>Signaler une anomalie</Text>
            </View>
            <Text style={styles.subtitle}>Page : {pageContext}</Text>
            <TextInput
              testID="anomaly-comment-input"
              placeholder="Décrivez l'anomalie ou votre idée d'amélioration..."
              placeholderTextColor={colors.placeholder}
              multiline
              numberOfLines={5}
              value={comment}
              onChangeText={setComment}
              style={styles.input}
            />
            <View style={styles.row}>
              <TouchableOpacity
                testID="anomaly-cancel-button"
                onPress={() => setOpen(false)}
                style={[styles.btn, styles.btnSecondary]}
                activeOpacity={0.7}
              >
                <Text style={styles.btnSecondaryText}>Annuler</Text>
              </TouchableOpacity>
              <TouchableOpacity
                testID="anomaly-submit-button"
                onPress={submit}
                disabled={submitting}
                style={[styles.btn, styles.btnPrimary]}
                activeOpacity={0.7}
              >
                {submitting ? (
                  <ActivityIndicator color="#000" />
                ) : (
                  <Text style={styles.btnPrimaryText}>Envoyer</Text>
                )}
              </TouchableOpacity>
            </View>
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  fab: {
    position: "absolute",
    bottom: 24,
    left: 16,
    right: 16,
    minHeight: 64,
    backgroundColor: colors.anomaly,
    borderRadius: 8,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 16,
    shadowColor: colors.anomaly,
    shadowOpacity: 0.5,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 0 },
    elevation: 8,
    zIndex: 50,
  },
  fabText: {
    color: "#fff",
    fontWeight: "800",
    fontSize: 15,
    letterSpacing: 0.8,
    marginLeft: 8,
  },
  overlay: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.75)",
    justifyContent: "center",
    padding: 20,
  },
  card: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: 22,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
  },
  header: { flexDirection: "row", alignItems: "center", marginBottom: 8 },
  title: {
    color: colors.textPrimary,
    fontWeight: "900",
    fontSize: 20,
    textTransform: "uppercase",
    marginLeft: 8,
    letterSpacing: 0.5,
  },
  subtitle: { color: colors.textSecondary, marginBottom: 14, fontSize: 13 },
  input: {
    backgroundColor: colors.inputBg,
    borderColor: colors.borderSubtle,
    borderWidth: 2,
    color: colors.textPrimary,
    borderRadius: 8,
    padding: 14,
    minHeight: 120,
    textAlignVertical: "top",
    fontSize: 16,
    marginBottom: 16,
  },
  row: { flexDirection: "row", gap: 12 },
  btn: {
    flex: 1,
    minHeight: 56,
    borderRadius: 8,
    alignItems: "center",
    justifyContent: "center",
  },
  btnSecondary: { borderWidth: 2, borderColor: colors.borderStrong },
  btnSecondaryText: {
    color: colors.textPrimary,
    fontWeight: "700",
    textTransform: "uppercase",
  },
  btnPrimary: { backgroundColor: colors.primary },
  btnPrimaryText: {
    color: "#000",
    fontWeight: "900",
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
});
