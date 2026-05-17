import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useAuth } from "@/src/context/AuthContext";
import { colors } from "@/src/theme";

/**
 * Deep-link page for email verification.
 *
 * Triggered via `/verify?token=xxx` after the user clicks the email link.
 * Calls `POST /auth/verify` and auto-logs the user in on success.
 */
export default function VerifyEmailScreen() {
  const { token } = useLocalSearchParams<{ token?: string }>();
  const router = useRouter();
  const { verifyEmail } = useAuth();
  const [status, setStatus] = useState<"loading" | "ok" | "error">("loading");
  const [errMsg, setErrMsg] = useState<string>("");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setErrMsg("Lien de vérification manquant.");
      return;
    }
    (async () => {
      try {
        await verifyEmail(String(token));
        setStatus("ok");
        // Petit délai pour que l'utilisateur voie le check vert
        setTimeout(() => router.replace("/dashboard"), 1500);
      } catch (e: any) {
        const detail = e?.response?.data?.detail;
        const msg =
          typeof detail === "string"
            ? detail
            : "Lien invalide, expiré ou déjà utilisé.";
        setErrMsg(msg);
        setStatus("error");
      }
    })();
  }, [token, verifyEmail, router]);

  return (
    <SafeAreaView style={styles.flex} edges={["top", "bottom"]}>
      <View style={styles.center}>
        {status === "loading" && (
          <>
            <ActivityIndicator color={colors.primary} size="large" />
            <Text style={styles.title}>Vérification en cours…</Text>
            <Text style={styles.body}>
              Activation de votre compte MesureChâssis.
            </Text>
          </>
        )}
        {status === "ok" && (
          <>
            <View style={[styles.iconWrap, { borderColor: "#34d399" }]}>
              <Ionicons name="checkmark-circle" size={64} color="#34d399" />
            </View>
            <Text style={styles.title}>EMAIL VÉRIFIÉ !</Text>
            <Text style={styles.body}>
              Votre compte est désormais actif. Redirection vers le dashboard…
            </Text>
          </>
        )}
        {status === "error" && (
          <>
            <View style={[styles.iconWrap, { borderColor: colors.anomaly }]}>
              <Ionicons name="close-circle" size={64} color={colors.anomaly} />
            </View>
            <Text style={styles.title}>LIEN INVALIDE</Text>
            <Text style={styles.body}>{errMsg}</Text>
            <TouchableOpacity
              onPress={() => router.replace("/")}
              activeOpacity={0.85}
              style={styles.btn}
            >
              <Text style={styles.btnText}>RETOUR À LA CONNEXION</Text>
            </TouchableOpacity>
          </>
        )}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: colors.bg },
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: 32,
    gap: 14,
  },
  iconWrap: {
    width: 110,
    height: 110,
    borderRadius: 55,
    borderWidth: 3,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 8,
  },
  title: {
    color: colors.textPrimary,
    fontWeight: "900",
    fontSize: 18,
    letterSpacing: 1.4,
  },
  body: {
    color: colors.textSecondary,
    fontSize: 14,
    textAlign: "center",
    lineHeight: 20,
  },
  btn: {
    backgroundColor: colors.primary,
    paddingHorizontal: 24,
    paddingVertical: 14,
    borderRadius: 10,
    marginTop: 12,
  },
  btnText: { color: "#000", fontWeight: "900", letterSpacing: 1 },
});
