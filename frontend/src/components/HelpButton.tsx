/**
 * 🆘 HelpButton — Bouton d'aide contextuel.
 *
 * Ouvre l'app Mail native de l'iPhone avec un message pré-rempli
 * contenant les infos techniques utiles (email, version, plateforme).
 *
 * Objectif : ne JAMAIS laisser un menuisier bloqué sans issue.
 * Utilisé sur les écrans où un blocage peut arriver :
 *   - Écran de connexion / inscription
 *   - Écran "Vérifiez votre email"
 *   - N'importe quel écran d'erreur
 *
 * Michel reçoit un email parfaitement structuré → me le forward → je fixe.
 */
import { Ionicons } from "@expo/vector-icons";
import Constants from "expo-constants";
import React from "react";
import {
  Alert,
  Linking,
  Platform,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";

const SUPPORT_EMAIL = "info@mesurechassis.com";
const SUPPORT_PHONE = "+32496650032"; // 0496 65 00 32

type Props = {
  /** Contexte du problème (ex: "Connexion", "Vérification email"). */
  context?: string;
  /** Email de l'utilisateur si connu (pour pré-remplir). */
  userEmail?: string;
  /** Style : "compact" (une ligne) ou "full" (bloc complet). */
  variant?: "compact" | "full";
};

export default function HelpButton({
  context = "Général",
  userEmail = "",
  variant = "full",
}: Props) {
  const appVersion =
    (Constants.expoConfig?.version || "1.0.x") +
    " (build " +
    (Constants.expoConfig?.ios?.buildNumber || "?") +
    ")";

  const buildMailtoUrl = () => {
    const subject = `[MesureChâssis] Aide - ${context}`;
    const body =
      "Bonjour Michel,\n\n" +
      "Je rencontre un problème avec l'application MesureChâssis :\n\n" +
      "[Décrivez ici votre problème le plus précisément possible]\n\n" +
      "─────────────────\n" +
      "Infos techniques (utiles pour vous aider) :\n" +
      `• Email de connexion : ${userEmail || "[votre email ici]"}\n` +
      `• Version app : ${appVersion}\n` +
      `• Appareil : ${Platform.OS === "ios" ? "iPhone / iPad" : "Android"}\n` +
      `• Écran où le problème arrive : ${context}\n` +
      "─────────────────\n\n" +
      "Merci pour votre patience !\n";
    return (
      `mailto:${SUPPORT_EMAIL}` +
      `?subject=${encodeURIComponent(subject)}` +
      `&body=${encodeURIComponent(body)}`
    );
  };

  const openMail = async () => {
    const url = buildMailtoUrl();
    try {
      const supported = await Linking.canOpenURL(url);
      if (supported) {
        await Linking.openURL(url);
      } else {
        Alert.alert(
          "App Mail introuvable",
          `Envoyez directement un email à ${SUPPORT_EMAIL}\n\nOu appelez le ${SUPPORT_PHONE}`,
          [{ text: "OK" }],
        );
      }
    } catch {
      Alert.alert(
        "Impossible d'ouvrir Mail",
        `Contactez-nous à ${SUPPORT_EMAIL} ou au ${SUPPORT_PHONE}`,
      );
    }
  };

  const callPhone = async () => {
    const url = `tel:${SUPPORT_PHONE}`;
    try {
      await Linking.openURL(url);
    } catch {
      Alert.alert("Impossible d'appeler", `Composez le ${SUPPORT_PHONE}`);
    }
  };

  // Variante compacte : juste un lien texte discret
  if (variant === "compact") {
    return (
      <TouchableOpacity
        onPress={openMail}
        style={styles.compactBtn}
        activeOpacity={0.7}
        accessibilityLabel="Contacter l'aide"
      >
        <Ionicons name="help-circle-outline" size={16} color="#9E9EA5" />
        <Text style={styles.compactText}>Besoin d'aide ?</Text>
      </TouchableOpacity>
    );
  }

  // Variante complète : bloc avec mail + téléphone
  return (
    <View style={styles.wrap}>
      <Text style={styles.wrapTitle}>Un souci ? On est là 👋</Text>
      <View style={styles.row}>
        <TouchableOpacity
          onPress={openMail}
          style={[styles.actionBtn, styles.mailBtn]}
          activeOpacity={0.85}
        >
          <Ionicons name="mail-outline" size={16} color="#0A0A0C" />
          <Text style={styles.actionBtnText}>Envoyer un email</Text>
        </TouchableOpacity>
        <TouchableOpacity
          onPress={callPhone}
          style={[styles.actionBtn, styles.phoneBtn]}
          activeOpacity={0.85}
        >
          <Ionicons name="call-outline" size={16} color="#F5F5F5" />
          <Text style={[styles.actionBtnText, { color: "#F5F5F5" }]}>
            0496 65 00 32
          </Text>
        </TouchableOpacity>
      </View>
      <Text style={styles.hint}>
        Réponse en moins de 24h par Michel, fondateur — en Belge, sans robot.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    marginTop: 20,
    paddingVertical: 16,
    paddingHorizontal: 14,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: "rgba(255,255,255,0.08)",
    alignItems: "center",
  },
  wrapTitle: {
    color: "#F5F5F5",
    fontSize: 13.5,
    fontWeight: "700",
    marginBottom: 12,
    letterSpacing: 0.2,
  },
  row: {
    flexDirection: "row",
    gap: 10,
    marginBottom: 10,
  },
  actionBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    paddingVertical: 10,
    paddingHorizontal: 14,
    borderRadius: 999,
    minWidth: 140,
  },
  mailBtn: {
    backgroundColor: "#FF5A00",
  },
  phoneBtn: {
    backgroundColor: "transparent",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.15)",
  },
  actionBtnText: {
    color: "#0A0A0C",
    fontSize: 12.5,
    fontWeight: "800",
    letterSpacing: 0.3,
  },
  hint: {
    color: "#7A7A80",
    fontSize: 11,
    textAlign: "center",
    marginTop: 6,
    fontStyle: "italic",
  },
  compactBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    padding: 8,
    alignSelf: "center",
  },
  compactText: {
    color: "#9E9EA5",
    fontSize: 12.5,
    fontWeight: "500",
  },
});
