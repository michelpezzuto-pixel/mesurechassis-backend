import React, { useCallback, useEffect, useState } from "react";
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
import { api } from "@/src/services/api";
import { useAuth } from "@/src/context/AuthContext";
import { colors } from "@/src/theme";

type Invitation = {
  email: string;
  name: string;
  role: "commercial" | "technician";
  company_name?: string;
  expires_at: string;
};

/**
 * Page d'acceptation d'invitation (deep-link).
 *
 * URL : `/invite?token=xxx`
 * - GET `/admin/invitations/{token}` pour récupérer email/nom/rôle
 * - POST `/admin/invitations/{token}/accept` avec mot de passe + nom
 *   définit le mot de passe ET valide l'email simultanément.
 */
export default function InviteScreen() {
  const { token } = useLocalSearchParams<{ token?: string }>();
  const router = useRouter();
  const { acceptInvitation } = useAuth();
  const [invite, setInvite] = useState<Invitation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const fetchInvite = useCallback(async () => {
    if (!token) {
      setError("Lien d'invitation manquant.");
      setLoading(false);
      return;
    }
    try {
      const res = await api.get<Invitation>(
        `/admin/invitations/${encodeURIComponent(String(token))}`
      );
      setInvite(res.data);
      setName(res.data.name);
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      setError(
        typeof detail === "string"
          ? detail
          : "Invitation introuvable, expirée ou déjà utilisée."
      );
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchInvite();
  }, [fetchInvite]);

  const submit = async () => {
    if (!password || password.length < 6) {
      Alert.alert(
        "Mot de passe trop court",
        "Choisissez un mot de passe d'au moins 6 caractères."
      );
      return;
    }
    setSubmitting(true);
    try {
      await acceptInvitation(String(token), password, name.trim() || undefined);
      router.replace("/dashboard");
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      Alert.alert(
        "Erreur",
        typeof detail === "string"
          ? detail
          : "Impossible d'accepter cette invitation."
      );
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.flex} edges={["top", "bottom"]}>
        <View style={styles.center}>
          <ActivityIndicator color={colors.primary} size="large" />
          <Text style={styles.subTitle}>Chargement de l'invitation…</Text>
        </View>
      </SafeAreaView>
    );
  }

  if (error || !invite) {
    return (
      <SafeAreaView style={styles.flex} edges={["top", "bottom"]}>
        <View style={styles.center}>
          <View style={[styles.iconWrap, { borderColor: colors.anomaly }]}>
            <Ionicons name="close-circle" size={56} color={colors.anomaly} />
          </View>
          <Text style={styles.title}>INVITATION INVALIDE</Text>
          <Text style={styles.body}>{error || "Lien malformé"}</Text>
          <TouchableOpacity
            onPress={() => router.replace("/")}
            activeOpacity={0.85}
            style={styles.btnPrimary}
          >
            <Text style={styles.btnPrimaryText}>RETOUR</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  const roleLabel =
    invite.role === "commercial" ? "Commercial" : "Technicien";

  return (
    <SafeAreaView style={styles.flex} edges={["top", "bottom"]}>
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        style={styles.flex}
      >
        <ScrollView contentContainerStyle={{ padding: 24, paddingBottom: 80 }}>
          <View style={[styles.iconWrap, { borderColor: colors.primary }]}>
            <Ionicons name="people" size={48} color={colors.primary} />
          </View>
          <Text style={styles.title}>INVITATION REÇUE</Text>
          <View style={styles.summary}>
            <View style={styles.kv}>
              <Text style={styles.kvLabel}>Email</Text>
              <Text style={styles.kvValue}>{invite.email}</Text>
            </View>
            <View style={styles.kv}>
              <Text style={styles.kvLabel}>Rôle</Text>
              <Text style={styles.kvValue}>{roleLabel}</Text>
            </View>
            {invite.company_name && (
              <View style={styles.kv}>
                <Text style={styles.kvLabel}>Société</Text>
                <Text style={styles.kvValue}>{invite.company_name}</Text>
              </View>
            )}
          </View>
          <Text style={styles.help}>
            Pour activer votre compte, définissez votre mot de passe ci-dessous.
            Votre email sera automatiquement vérifié.
          </Text>

          <Text style={styles.label}>Nom complet</Text>
          <TextInput
            testID="invite-name-input"
            value={name}
            onChangeText={setName}
            placeholder={invite.name}
            placeholderTextColor={colors.placeholder}
            style={styles.input}
          />

          <Text style={styles.label}>Mot de passe (min. 6 caractères)</Text>
          <TextInput
            testID="invite-password-input"
            value={password}
            onChangeText={setPassword}
            placeholder="••••••••"
            placeholderTextColor={colors.placeholder}
            secureTextEntry
            style={styles.input}
          />

          <TouchableOpacity
            testID="invite-submit-button"
            onPress={submit}
            disabled={submitting}
            activeOpacity={0.85}
            style={[styles.btnPrimary, { marginTop: 14 }]}
          >
            {submitting ? (
              <ActivityIndicator color="#000" />
            ) : (
              <Text style={styles.btnPrimaryText}>
                ACTIVER MON COMPTE
              </Text>
            )}
          </TouchableOpacity>
        </ScrollView>
      </KeyboardAvoidingView>
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
    width: 90,
    height: 90,
    borderRadius: 45,
    borderWidth: 3,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 12,
    alignSelf: "center",
  },
  title: {
    color: colors.textPrimary,
    fontWeight: "900",
    fontSize: 18,
    letterSpacing: 1.4,
    textAlign: "center",
    marginBottom: 6,
  },
  subTitle: { color: colors.textSecondary, marginTop: 12, fontSize: 13 },
  summary: {
    backgroundColor: colors.surface,
    borderRadius: 10,
    padding: 14,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    marginTop: 12,
    marginBottom: 18,
  },
  kv: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 6,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSubtle,
  },
  kvLabel: { color: colors.textSecondary, fontSize: 12 },
  kvValue: { color: colors.textPrimary, fontSize: 13, fontWeight: "700" },
  help: {
    color: colors.textSecondary,
    fontSize: 12,
    lineHeight: 17,
    marginBottom: 14,
  },
  body: {
    color: colors.textSecondary,
    fontSize: 13,
    textAlign: "center",
    lineHeight: 19,
  },
  label: {
    color: colors.textSecondary,
    fontSize: 11,
    fontWeight: "700",
    letterSpacing: 0.6,
    marginBottom: 6,
  },
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
    marginBottom: 12,
  },
  btnPrimary: {
    backgroundColor: colors.primary,
    minHeight: 52,
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 18,
  },
  btnPrimaryText: { color: "#000", fontWeight: "900", letterSpacing: 1 },
});
