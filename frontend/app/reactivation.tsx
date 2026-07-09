/**
 * 🔓 Page de confirmation de réactivation de compte
 *
 * L'utilisateur arrive ici après avoir cliqué sur le lien magique
 * reçu par email. Le token est passé en query string.
 *
 * Étapes :
 * 1. Vérifie le token (GET /auth/reactivation/verify/:token)
 * 2. Affiche l'email du compte à réactiver + formulaire "nouveau mot de passe"
 * 3. À la soumission → POST /auth/reactivation/confirm
 * 4. Succès → connexion auto (JWT) → redirection vers /dashboard
 */
import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
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
import { useLocalSearchParams, useRouter } from "expo-router";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { api } from "@/src/services/api";
import { colors } from "@/src/theme";
import { useAuth } from "@/src/context/AuthContext";

type VerifyResp = {
  ok: boolean;
  email: string;
  name: string;
  expires_at: string;
};

type ConfirmResp = {
  ok: boolean;
  access_token: string;
  token_type: string;
  user: { id: string; email: string; name: string; role: string };
  message: string;
};

export default function ReactivationScreen() {
  const params = useLocalSearchParams<{ token?: string }>();
  const router = useRouter();
  const { refreshUser } = useAuth();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [verified, setVerified] = useState<VerifyResp | null>(null);

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    const t = params.token;
    if (!t || typeof t !== "string") {
      setError("Aucun token de réactivation fourni.");
      setLoading(false);
      return;
    }
    (async () => {
      try {
        const { data } = await api.get<VerifyResp>(
          `/auth/reactivation/verify/${encodeURIComponent(t)}`,
        );
        setVerified(data);
      } catch (e: any) {
        const detail = e?.response?.data?.detail;
        setError(
          typeof detail === "string"
            ? detail
            : "Ce lien de réactivation est invalide ou a expiré.",
        );
      } finally {
        setLoading(false);
      }
    })();
  }, [params.token]);

  const handleConfirm = async () => {
    if (password.length < 8) {
      Alert.alert(
        "Mot de passe trop court",
        "Le mot de passe doit contenir au moins 8 caractères.",
      );
      return;
    }
    if (password !== confirmPassword) {
      Alert.alert(
        "Mots de passe différents",
        "Les deux mots de passe ne correspondent pas.",
      );
      return;
    }
    setSubmitting(true);
    try {
      const { data } = await api.post<ConfirmResp>(
        "/auth/reactivation/confirm",
        { token: params.token, new_password: password },
      );
      // Connexion automatique
      await AsyncStorage.setItem("access_token", data.access_token);
      await refreshUser?.();
      setDone(true);
      setTimeout(() => router.replace("/dashboard"), 1500);
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      Alert.alert(
        "Erreur",
        typeof detail === "string"
          ? detail
          : "Impossible de réactiver votre compte. Contactez info@mesurechassis.com.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <View style={[styles.container, styles.center]}>
        <ActivityIndicator color={colors.primary} size="large" />
        <Text style={styles.subtle}>Vérification du lien...</Text>
      </View>
    );
  }

  if (error) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.center}>
          <Ionicons name="alert-circle" size={64} color="#EF4444" />
          <Text style={styles.title}>Lien invalide</Text>
          <Text style={styles.error}>{error}</Text>
          <TouchableOpacity
            style={styles.btnPrimary}
            onPress={() => router.replace("/")}
          >
            <Text style={styles.btnPrimaryText}>Retour à l&apos;accueil</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  if (done) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.center}>
          <Ionicons name="checkmark-circle" size={72} color="#22C55E" />
          <Text style={styles.title}>Compte réactivé !</Text>
          <Text style={styles.subtle}>
            Bienvenue à nouveau. Vous allez être redirigé...
          </Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container} edges={["top", "bottom"]}>
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        style={{ flex: 1 }}
      >
        <ScrollView contentContainerStyle={styles.scroll}>
          <View style={styles.header}>
            <Ionicons
              name="lock-open"
              size={56}
              color={colors.primary}
              style={{ marginBottom: 12 }}
            />
            <Text style={styles.title}>Réactivation de compte</Text>
            <Text style={styles.subtle}>
              Bienvenue à nouveau{verified?.name ? `, ${verified.name}` : ""}.
              Définissez un nouveau mot de passe pour restaurer votre compte.
            </Text>
          </View>

          <View style={styles.emailBadge}>
            <Ionicons name="mail" size={18} color={colors.primary} />
            <Text style={styles.emailText}>{verified?.email}</Text>
          </View>

          <View style={styles.form}>
            <Text style={styles.label}>Nouveau mot de passe</Text>
            <View style={styles.inputWrap}>
              <TextInput
                testID="reactivation-password"
                style={styles.input}
                secureTextEntry={!showPassword}
                placeholder="Au moins 8 caractères"
                placeholderTextColor="#9CA3AF"
                autoCapitalize="none"
                autoCorrect={false}
                value={password}
                onChangeText={setPassword}
              />
              <TouchableOpacity
                onPress={() => setShowPassword((v) => !v)}
                style={styles.eye}
              >
                <Ionicons
                  name={showPassword ? "eye-off" : "eye"}
                  size={20}
                  color="#6B7280"
                />
              </TouchableOpacity>
            </View>

            <Text style={styles.label}>Confirmer le mot de passe</Text>
            <View style={styles.inputWrap}>
              <TextInput
                testID="reactivation-confirm-password"
                style={styles.input}
                secureTextEntry={!showPassword}
                placeholder="Ressaisissez le mot de passe"
                placeholderTextColor="#9CA3AF"
                autoCapitalize="none"
                autoCorrect={false}
                value={confirmPassword}
                onChangeText={setConfirmPassword}
              />
            </View>

            <TouchableOpacity
              testID="reactivation-submit"
              style={[
                styles.btnPrimary,
                submitting && { opacity: 0.6 },
              ]}
              onPress={handleConfirm}
              disabled={submitting}
            >
              {submitting ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={styles.btnPrimaryText}>
                  🔓 Réactiver mon compte
                </Text>
              )}
            </TouchableOpacity>

            <View style={styles.info}>
              <Ionicons name="information-circle" size={16} color="#6B7280" />
              <Text style={styles.infoText}>
                Cette réactivation est unique — vous ne pourrez plus réactiver
                ce compte à l&apos;avenir.
              </Text>
            </View>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#F9FAFB",
  },
  scroll: {
    padding: 24,
    paddingTop: 40,
  },
  center: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: 24,
  },
  header: {
    alignItems: "center",
    marginBottom: 24,
  },
  title: {
    fontSize: 24,
    fontWeight: "800",
    color: "#111827",
    marginBottom: 8,
    textAlign: "center",
  },
  subtle: {
    fontSize: 14,
    color: "#6B7280",
    textAlign: "center",
    lineHeight: 20,
    maxWidth: 340,
    marginTop: 8,
  },
  emailBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    backgroundColor: "#FFF7ED",
    borderColor: "#FED7AA",
    borderWidth: 1,
    padding: 12,
    borderRadius: 10,
    marginBottom: 24,
    alignSelf: "center",
  },
  emailText: {
    fontSize: 14,
    color: "#9A3412",
    fontWeight: "600",
  },
  form: {
    gap: 4,
  },
  label: {
    fontSize: 13,
    fontWeight: "600",
    color: "#374151",
    marginTop: 12,
    marginBottom: 6,
  },
  inputWrap: {
    position: "relative",
  },
  input: {
    borderWidth: 1,
    borderColor: "#D1D5DB",
    backgroundColor: "#fff",
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 15,
    color: "#111827",
    paddingRight: 44,
  },
  eye: {
    position: "absolute",
    right: 12,
    top: 12,
    padding: 4,
  },
  btnPrimary: {
    backgroundColor: colors.primary,
    borderRadius: 12,
    paddingVertical: 15,
    alignItems: "center",
    marginTop: 20,
  },
  btnPrimaryText: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "700",
  },
  error: {
    fontSize: 14,
    color: "#B91C1C",
    textAlign: "center",
    marginTop: 12,
    marginBottom: 24,
    maxWidth: 320,
    lineHeight: 20,
  },
  info: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 8,
    backgroundColor: "#F3F4F6",
    padding: 12,
    borderRadius: 8,
    marginTop: 16,
  },
  infoText: {
    fontSize: 12,
    color: "#6B7280",
    flex: 1,
    lineHeight: 16,
  },
});
