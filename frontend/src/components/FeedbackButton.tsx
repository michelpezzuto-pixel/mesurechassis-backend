import React, { useState } from "react";
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Modal,
  Platform,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { usePathname } from "expo-router";
import { api } from "@/src/services/api";
import { colors } from "@/src/theme";

/**
 * Bouton « Suggérer une amélioration / Signaler un bug » accessible
 * depuis l'écran profil société. Ouvre un modal avec textarea ; à la
 * soumission, POST /feedbacks → backend envoie un email interne au support.
 */
export default function FeedbackButton() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const submit = async () => {
    const trimmed = comment.trim();
    if (trimmed.length < 5) {
      Alert.alert(
        "Message trop court",
        "Merci de rédiger au moins quelques mots pour expliquer votre retour."
      );
      return;
    }
    setSubmitting(true);
    try {
      await api.post("/feedbacks", {
        user_comment: trimmed,
        page_context: pathname || "/company-profile",
      });
      setOpen(false);
      setComment("");
      Alert.alert(
        "✅ Merci pour votre retour",
        "Votre message a été transmis à notre équipe. Nous reviendrons vers vous rapidement si nécessaire."
      );
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      Alert.alert(
        "Erreur",
        typeof detail === "string" ? detail : "Envoi impossible."
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <TouchableOpacity
        testID="open-feedback-modal-button"
        onPress={() => setOpen(true)}
        activeOpacity={0.85}
        style={styles.feedbackBtn}
      >
        <Ionicons name="chatbubble-ellipses-outline" size={20} color={colors.primary} />
        <Text style={styles.feedbackBtnText}>
          Suggérer une amélioration / Signaler un bug
        </Text>
      </TouchableOpacity>

      <Modal
        visible={open}
        transparent
        animationType="slide"
        onRequestClose={() => setOpen(false)}
      >
        <KeyboardAvoidingView
          behavior={Platform.OS === "ios" ? "padding" : undefined}
          style={styles.modalBackdrop}
        >
          <View style={styles.modalCard}>
            <View style={styles.modalHeader}>
              <Ionicons
                name="chatbubbles"
                size={22}
                color={colors.primary}
              />
              <Text style={styles.modalTitle}>VOTRE RETOUR</Text>
            </View>
            <Text style={styles.modalSub}>
              Décrivez votre suggestion ou le bug rencontré. Notre équipe
              reçoit directement votre message par email.
            </Text>

            <TextInput
              testID="feedback-textarea"
              value={comment}
              onChangeText={setComment}
              placeholder="Ex. Lorsque je clique sur EXPORTER…"
              placeholderTextColor={colors.placeholder}
              multiline
              numberOfLines={6}
              style={styles.textarea}
            />

            <View style={styles.modalActions}>
              <TouchableOpacity
                onPress={() => {
                  setOpen(false);
                  setComment("");
                }}
                disabled={submitting}
                activeOpacity={0.85}
                style={[styles.btn, styles.btnGhost, { flex: 1 }]}
              >
                <Text style={styles.btnGhostText}>ANNULER</Text>
              </TouchableOpacity>
              <TouchableOpacity
                testID="feedback-submit-button"
                onPress={submit}
                disabled={submitting || comment.trim().length < 5}
                activeOpacity={0.85}
                style={[
                  styles.btn,
                  styles.btnSubmit,
                  { flex: 1.3 },
                  (submitting || comment.trim().length < 5) && {
                    opacity: 0.55,
                  },
                ]}
              >
                {submitting ? (
                  <ActivityIndicator color="#000" />
                ) : (
                  <>
                    <Ionicons name="send" size={16} color="#000" />
                    <Text style={styles.btnSubmitText}>ENVOYER</Text>
                  </>
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
  feedbackBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    backgroundColor: colors.surface,
    borderColor: colors.borderStrong,
    borderWidth: 1,
    borderRadius: 12,
    padding: 14,
    marginTop: 14,
  },
  feedbackBtnText: {
    color: colors.textPrimary,
    fontWeight: "800",
    fontSize: 13,
    flex: 1,
  },
  modalBackdrop: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.7)",
    justifyContent: "flex-end",
  },
  modalCard: {
    backgroundColor: colors.bg,
    padding: 20,
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
    borderTopWidth: 1,
    borderColor: colors.borderStrong,
  },
  modalHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginBottom: 4,
  },
  modalTitle: {
    color: colors.textPrimary,
    fontWeight: "900",
    fontSize: 14,
    letterSpacing: 1,
  },
  modalSub: {
    color: colors.textSecondary,
    fontSize: 12,
    marginBottom: 14,
  },
  textarea: {
    backgroundColor: colors.surface,
    color: colors.textPrimary,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.borderStrong,
    padding: 12,
    fontSize: 14,
    minHeight: 130,
    textAlignVertical: "top",
  },
  modalActions: {
    flexDirection: "row",
    gap: 10,
    marginTop: 16,
  },
  btn: {
    minHeight: 50,
    borderRadius: 12,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    paddingHorizontal: 14,
  },
  btnGhost: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderStrong,
  },
  btnGhostText: {
    color: colors.textPrimary,
    fontWeight: "800",
    fontSize: 13,
    letterSpacing: 0.8,
  },
  btnSubmit: { backgroundColor: colors.primary },
  btnSubmitText: { color: "#000", fontWeight: "900", letterSpacing: 1 },
});
