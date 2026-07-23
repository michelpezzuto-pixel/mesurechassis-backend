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

/** 🇫🇷🇧🇪 v1.1.4 — Modes de validation professionnels acceptés. */
type IdMode = "vat" | "siren" | "siret" | "bce";

const ID_MODE_LABELS: Record<IdMode, string> = {
  vat: "TVA UE",
  siren: "SIREN (FR)",
  siret: "SIRET (FR)",
  bce: "BCE (BE)",
};

const ID_MODE_PLACEHOLDERS: Record<IdMode, string> = {
  vat: "ex. BE0123456789",
  siren: "9 chiffres — ex. 383474814",
  siret: "14 chiffres — ex. 44306184100047",
  bce: "10 chiffres — ex. 0403170701",
};

export default function CompleteVatScreen({
  defaultCompanyName,
  onCompleted,
  onLogout,
}: Props) {
  const [idMode, setIdMode] = useState<IdMode>("vat");
  const [showFallback, setShowFallback] = useState(false);
  const [vatNumber, setVatNumber] = useState<string>("");
  const [companyName, setCompanyName] = useState<string>(defaultCompanyName || "");
  const [vatStatus, setVatStatus] = useState<VatStatus>(null);
  const [checking, setChecking] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Validation en direct (VIES pour TVA, contrôle local pour SIREN/SIRET/BCE).
  const runValidation = useCallback(async (raw: string, mode: IdMode) => {
    const cleaned = mode === "vat" ? raw.trim() : raw.replace(/\D/g, "");
    const minLen = mode === "vat" ? 4 : mode === "siren" ? 9 : mode === "siret" ? 14 : 10;
    if (!cleaned || cleaned.length < minLen) {
      setVatStatus(null);
      return;
    }
    setChecking(true);
    try {
      if (mode === "vat") {
        const { data } = await api.post<{
          valid: boolean;
          normalized?: string;
          message?: string;
        }>("/auth/validate-vat", { vat_number: cleaned });
        setVatStatus(data);
        if (data.valid && data.normalized && data.normalized !== cleaned) {
          setVatNumber(data.normalized);
        }
      } else {
        const { data } = await api.post<{
          valid: boolean;
          normalized?: string;
          message?: string;
        }>("/auth/validate-business-id", {
          id_type: mode,
          id_value: cleaned,
        });
        setVatStatus(data);
        if (data.valid && data.normalized && data.normalized !== cleaned) {
          setVatNumber(data.normalized);
        }
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
      runValidation(vatNumber, idMode);
    }, 500);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [vatNumber, idMode, runValidation]);

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
      const body: Record<string, string> = {
        company_name: companyName.trim(),
      };
      if (idMode === "vat") {
        body.vat_number = vatNumber.trim();
      } else {
        body.business_id_type = idMode;
        body.business_id_value = vatNumber.trim();
      }
      await api.post("/company/complete-signup", body);
      await onCompleted();
    } catch (e) {
      const err = e as { response?: { data?: { detail?: string } } };
      setSubmitError(
        err?.response?.data?.detail ||
          "Impossible d'enregistrer vos informations. Vérifiez la saisie et réessayez.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  /** Change de mode et reset la validation. */
  const switchMode = (m: IdMode) => {
    setIdMode(m);
    setVatNumber("");
    setVatStatus(null);
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
              <Text style={styles.bold}>identifiant professionnel</Text> et le{" "}
              <Text style={styles.bold}>nom de votre société</Text>. Ces
              informations sont obligatoires pour émettre vos factures
              conformes UE et respecter les règles Apple.
            </Text>
          </View>

          {/* 🇫🇷🇧🇪 v1.1.4 — Toggle "Je n'ai pas de numéro de TVA" */}
          {!showFallback ? (
            <TouchableOpacity
              testID="complete-vat-toggle-fallback"
              onPress={() => setShowFallback(true)}
              activeOpacity={0.7}
              style={styles.fallbackToggle}
            >
              <Ionicons
                name="help-circle-outline"
                size={16}
                color={colors.textSecondary}
              />
              <Text style={styles.fallbackToggleText}>
                Je n&apos;ai pas de TVA (auto-entrepreneur, franchise…)
              </Text>
            </TouchableOpacity>
          ) : (
            <View style={styles.segmentWrap}>
              <Text style={[styles.label, { alignSelf: "flex-start" }]}>
                Type d&apos;identifiant
              </Text>
              <View style={styles.segmentRow}>
                {(["vat", "siren", "siret", "bce"] as IdMode[]).map((m) => (
                  <TouchableOpacity
                    key={m}
                    testID={`id-mode-${m}`}
                    onPress={() => switchMode(m)}
                    activeOpacity={0.85}
                    style={[
                      styles.segment,
                      idMode === m && styles.segmentActive,
                    ]}
                  >
                    <Text
                      style={[
                        styles.segmentText,
                        idMode === m && styles.segmentTextActive,
                      ]}
                    >
                      {ID_MODE_LABELS[m]}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>
            </View>
          )}

          {/* Identifiant TVA / SIREN / SIRET / BCE */}
          <Text style={[styles.label, { marginTop: 14 }]}>
            {idMode === "vat"
              ? "Numéro de TVA européen"
              : `Numéro ${ID_MODE_LABELS[idMode]}`}{" "}
            <Text style={{ color: colors.alert }}>*</Text>
          </Text>
          <View style={styles.inputRow}>
            <TextInput
              testID="complete-vat-input"
              value={vatNumber}
              onChangeText={(v) =>
                setVatNumber(
                  idMode === "vat"
                    ? v.toUpperCase().replace(/\s/g, "")
                    : v.replace(/\D/g, ""),
                )
              }
              placeholder={ID_MODE_PLACEHOLDERS[idMode]}
              placeholderTextColor={colors.placeholder}
              autoCapitalize={idMode === "vat" ? "characters" : "none"}
              autoCorrect={false}
              keyboardType={idMode === "vat" ? "default" : "number-pad"}
              maxLength={idMode === "vat" ? 20 : 14}
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
              {idMode === "vat"
                ? "✓ TVA validée par la base européenne VIES"
                : `✓ ${ID_MODE_LABELS[idMode]} valide (contrôle de clé OK)`}
            </Text>
          )}
          {vatStatus && !vatStatus.valid && vatNumber.trim().length >= 4 && (
            <Text style={[styles.hint, { color: colors.anomaly }]}>
              ✗ {vatStatus.message || "Identifiant invalide"}
            </Text>
          )}
          {!vatStatus && vatNumber.trim().length < 4 && (
            <Text style={styles.hint}>
              {idMode === "vat"
                ? "Pays supportés : BE, FR, DE, NL, LU, IT, ES, PT, AT, PL, et tous les autres États membres de l'UE."
                : idMode === "siren"
                  ? "Le SIREN identifie votre entreprise auprès de l'INSEE (9 chiffres)."
                  : idMode === "siret"
                    ? "Le SIRET identifie votre établissement (14 chiffres, inclut le SIREN)."
                    : "Le BCE est votre numéro d'entreprise belge (10 chiffres)."}
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
            {idMode === "vat"
              ? "Validation automatique via la base européenne "
              : "Contrôle de clé local — aucune donnée n'est partagée avec des tiers. "}
            {idMode === "vat" && (
              <Text style={styles.helperBold}>VIES</Text>
            )}
            {idMode === "vat" && ". Aucune donnée n'est partagée avec des tiers."}
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
  fallbackToggle: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    marginTop: 4,
    marginBottom: 4,
    paddingVertical: 8,
    paddingHorizontal: 12,
  },
  fallbackToggleText: {
    color: colors.textSecondary,
    fontSize: 12.5,
    textDecorationLine: "underline",
  },
  segmentWrap: {
    width: "100%",
    marginBottom: 4,
  },
  segmentRow: {
    flexDirection: "row",
    backgroundColor: colors.surface,
    borderRadius: 10,
    padding: 4,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
    gap: 4,
  },
  segment: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 7,
    alignItems: "center",
    justifyContent: "center",
  },
  segmentActive: {
    backgroundColor: colors.primary,
  },
  segmentText: {
    color: colors.textSecondary,
    fontSize: 11.5,
    fontWeight: "700",
    letterSpacing: 0.2,
  },
  segmentTextActive: {
    color: "#fff",
  },
});
