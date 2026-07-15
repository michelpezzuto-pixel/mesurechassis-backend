/**
 * 🔒 CompleteVatScreen — verrou plein écran post-Google Sign-In.
 *
 * S'affiche automatiquement (rendu par AuthContext) quand
 * `user.vat_completion_required === true`. C'est le cas des comptes
 * créés via Google Sign-In (qui ne fournit ni TVA ni nom société).
 *
 * Compliance :
 *   - Apple 3.1.3(c) : app B2B réservée aux professionnels UE.
 *   - Stripe / facturation UE : TVA obligatoire (reverse charge).
 *
 * Flow :
 *   1. L'utilisateur saisit sa TVA (auto-validation VIES via
 *      /auth/validate-vat, 500ms debounce).
 *   2. Badge vert + pré-remplissage du nom société dès validation.
 *   3. L'utilisateur peut ajuster le nom société, puis « VALIDER ».
 *   4. POST /company/complete-signup → refresh user + company.
 *
 * Il n'y a AUCUN bouton retour ni bypass. Seule alternative : se
 * déconnecter (bouton discret en bas).
 */
import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
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
import { api } from "@/src/services/api";
import { colors } from "@/src/theme";

type Props = {
  defaultCompanyName?: string;
  onCompleted: () => Promise<void> | void;
  onLogout?: () => void;
};

type VatStatus = {
  valid: boolean;
  normalized?: string;
  message?: string;
} | null;

export default function CompleteVatScreen({
  defaultCompanyName,
  onCompleted,
  onLogout,
}: Props) {
  const [vatNumber, setVatNumber] = useState<string>("");
  const [companyName, setCompanyName] = useState<string>(defaultCompanyName || "");
  const [vatStatus, setVatStatus] = useState<VatStatus>(null);
  const [checking, setChecking] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Validation en direct VIES avec debounce 500ms.
  const runValidation = useCallback(async (raw: string) => {
    const cleaned = raw.trim();
    if (!cleaned || cleaned.length < 4) {
      setVatStatus(null);
      return;
    }
    setChecking(true);
    try {
      const { data } = await api.post<{
        valid: boolean;
        normalized?: string;
        message?: string;
      }>("/auth/validate-vat", { vat_number: cleaned });
      setVatStatus(data);
      if (data.valid && data.normalized && data.normalized !== cleaned) {
        setVatNumber(data.normalized);
      }
    } catch {
      setVatStatus({ valid: false, message: "Erreur réseau — réessayez." });
    } finally {
      setChecking(false);
    }
  }, []);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!vatNumber.trim()) {
      setVatStatus(null);
      return;
    }
    debounceRef.current = setTimeout(() => {
      runValidation(vatNumber);
    }, 500);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [vatNumber, runValidation]);

  const canSubmit =
    !!vatStatus?.valid &&
    !!vatNumber.trim() &&
    companyName.trim().length >= 2 &&
    !submitting &&
    !checking;

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      await api.post("/company/complete-signup", {
        vat_number: vatNumber.trim(),
        company_name: companyName.trim(),
      });
      await onCompleted();
    } catch (e) {
      const err = e as { response?: { data?: { detail?: string } } };
      setSubmitError(
        err?.response?.data?.detail ||
          "Impossible d'enregistrer la TVA. Vérifiez la saisie et réessayez.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <SafeAreaView style={styles.flex} edges={["top", "bottom"]}>
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        style={styles.flex}
      >
        <ScrollView
          contentContainerStyle={styles.scroll}
          keyboardShouldPersistTaps="handled"
        >
          <View style={styles.iconWrap}>
            <Ionicons
              name="shield-checkmark-outline"
              size={64}
              color={colors.primary}
            />
          </View>

          <Text style={styles.title}>Une dernière étape</Text>
          <Text style={styles.subtitle}>
            MesureChâssis est un service réservé aux professionnels
            de la menuiserie
          </Text>

          <View style={styles.messageBox}>
            <Text style={styles.messageText}>
              Pour activer votre compte, indiquez votre{" "}
              <Text style={styles.bold}>numéro de TVA européen</Text> et le{" "}
              <Text style={styles.bold}>nom de votre société</Text>. Ces
              informations sont obligatoires pour émettre vos factures
              conformes UE et respecter les règles Apple.
            </Text>
          </View>

          {/* TVA */}
          <Text style={styles.label}>
            Numéro de TVA européen{" "}
            <Text style={{ color: colors.alert }}>*</Text>
          </Text>
          <View style={styles.inputRow}>
            <TextInput
              testID="complete-vat-input"
              value={vatNumber}
              onChangeText={(v) => setVatNumber(v.toUpperCase().replace(/\s/g, ""))}
              placeholder="ex. BE0123456789"
              placeholderTextColor={colors.placeholder}
              autoCapitalize="characters"
              autoCorrect={false}
              maxLength={20}
              editable={!submitting}
              style={[
                styles.input,
                { flex: 1 },
                vatStatus?.valid && styles.inputValid,
                vatStatus && !vatStatus.valid && styles.inputInvalid,
              ]}
            />
            <View style={styles.statusIcon}>
              {checking ? (
                <ActivityIndicator size="small" color={colors.primary} />
              ) : vatStatus?.valid ? (
                <Ionicons
                  name="checkmark-circle"
                  size={24}
                  color={colors.success}
                />
              ) : (
                <Ionicons
                  name="shield-checkmark-outline"
                  size={22}
                  color={colors.placeholder}
                />
              )}
            </View>
          </View>
          {vatStatus?.valid && (
            <Text style={[styles.hint, { color: colors.success }]}>
              ✓ TVA validée par la base européenne VIES
            </Text>
          )}
          {vatStatus && !vatStatus.valid && vatNumber.trim().length >= 4 && (
            <Text style={[styles.hint, { color: colors.anomaly }]}>
              ✗ {vatStatus.message || "Numéro de TVA invalide"}
            </Text>
          )}
          {!vatStatus && vatNumber.trim().length < 4 && (
            <Text style={styles.hint}>
              Pays supportés : BE, FR, DE, NL, LU, IT, ES, PT, AT, PL, et tous
              les autres États membres de l&apos;UE.
            </Text>
          )}

          {/* Nom société */}
          <Text style={[styles.label, { marginTop: 18 }]}>
            Nom de votre société{" "}
            <Text style={{ color: colors.alert }}>*</Text>
          </Text>
          <TextInput
            testID="complete-companyname-input"
            value={companyName}
            onChangeText={setCompanyName}
            placeholder="ex. Menuiserie Dupont SPRL"
            placeholderTextColor={colors.placeholder}
            autoCapitalize="words"
            autoCorrect={false}
            maxLength={120}
            editable={!submitting}
            style={styles.input}
          />
          <Text style={styles.hint}>
            Ce nom apparaîtra sur vos devis et factures.
          </Text>

          {!!submitError && (
            <View style={styles.errorBox}>
              <Ionicons name="alert-circle" size={16} color={colors.anomaly} />
              <Text style={styles.errorText}>{submitError}</Text>
            </View>
          )}

          <TouchableOpacity
            testID="complete-vat-submit"
            style={[styles.primaryBtn, !canSubmit && styles.btnDisabled]}
            onPress={handleSubmit}
            disabled={!canSubmit}
            activeOpacity={0.85}
          >
            {submitting ? (
              <ActivityIndicator size="small" color="#fff" />
            ) : (
              <>
                <Ionicons
                  name="arrow-forward-circle"
                  size={18}
                  color="#fff"
                />
                <Text style={styles.primaryBtnText}>
                  VALIDER ET COMMENCER
                </Text>
              </>
            )}
          </TouchableOpacity>

          {!!onLogout && (
            <TouchableOpacity
              testID="complete-vat-logout"
              style={styles.logoutBtn}
              onPress={onLogout}
              disabled={submitting}
              activeOpacity={0.85}
            >
              <Ionicons
                name="log-out-outline"
                size={16}
                color={colors.textSecondary}
              />
              <Text style={styles.logoutText}>Se déconnecter</Text>
            </TouchableOpacity>
          )}

          <Text style={styles.helper}>
            Validation automatique via la base européenne{" "}
            <Text style={styles.helperBold}>VIES</Text>. Aucune donnée n&apos;est
            partagée avec des tiers.
          </Text>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: colors.bg },
  scroll: {
    flexGrow: 1,
    padding: 24,
    alignItems: "center",
    justifyContent: "flex-start",
  },
  iconWrap: {
    width: 110,
    height: 110,
    borderRadius: 55,
    backgroundColor: "rgba(255,90,0,0.10)",
    alignItems: "center",
    justifyContent: "center",
    marginTop: Platform.OS === "web" ? 24 : 8,
    marginBottom: 16,
  },
  title: {
    color: colors.textPrimary,
    fontSize: 24,
    fontWeight: "800",
    textAlign: "center",
  },
  subtitle: {
    color: colors.textSecondary,
    fontSize: 14,
    textAlign: "center",
    marginTop: 6,
    marginBottom: 18,
  },
  messageBox: {
    backgroundColor: colors.surface,
    borderRadius: 14,
    padding: 16,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    width: "100%",
    marginBottom: 20,
  },
  messageText: {
    color: colors.textPrimary,
    fontSize: 13.5,
    lineHeight: 20,
  },
  bold: { fontWeight: "800" },
  label: {
    color: colors.textPrimary,
    fontSize: 13,
    fontWeight: "700",
    marginBottom: 8,
    alignSelf: "flex-start",
  },
  inputRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    width: "100%",
  },
  input: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    color: colors.textPrimary,
    paddingHorizontal: 14,
    paddingVertical: Platform.OS === "ios" ? 14 : 12,
    fontSize: 15,
    width: "100%",
  },
  inputValid: {
    borderColor: colors.success,
    backgroundColor: "#0b2a14",
  },
  inputInvalid: {
    borderColor: colors.anomaly,
  },
  statusIcon: {
    width: 32,
    height: 32,
    alignItems: "center",
    justifyContent: "center",
  },
  hint: {
    color: colors.textSecondary,
    fontSize: 12,
    marginTop: 6,
    alignSelf: "flex-start",
    lineHeight: 17,
  },
  errorBox: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    backgroundColor: "rgba(255,59,48,0.10)",
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.anomaly,
    paddingVertical: 10,
    paddingHorizontal: 12,
    marginTop: 16,
    width: "100%",
  },
  errorText: {
    color: colors.anomaly,
    fontSize: 12.5,
    flex: 1,
    lineHeight: 18,
  },
  primaryBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    backgroundColor: colors.primary,
    borderRadius: 26,
    paddingVertical: 15,
    marginTop: 24,
    width: "100%",
  },
  btnDisabled: {
    opacity: 0.4,
  },
  primaryBtnText: {
    color: "#fff",
    fontWeight: "800",
    fontSize: 13,
    letterSpacing: 0.5,
  },
  logoutBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    marginTop: 18,
    padding: 8,
  },
  logoutText: { color: colors.textSecondary, fontSize: 13 },
  helper: {
    color: colors.textSecondary,
    fontSize: 11.5,
    marginTop: 20,
    textAlign: "center",
    lineHeight: 16,
  },
  helperBold: { fontWeight: "700", color: colors.textPrimary },
});
