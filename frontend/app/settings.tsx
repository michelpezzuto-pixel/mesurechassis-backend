import React, { useState, useEffect } from 'react';
import {
  View, Text, StyleSheet, TextInput, TouchableOpacity, ScrollView,
  KeyboardAvoidingView, Platform, Alert, ActivityIndicator, Switch, Image,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { useAuth } from '@/src/auth';
import { Auth } from '@/src/api';
import { C, SP, R, FONT } from '@/src/theme';
import { pickLogo } from '@/src/utils/imagePicker';

export default function SettingsScreen() {
  const router = useRouter();
  const { user, refresh } = useAuth();
  const [fullName, setFullName] = useState(user?.full_name || '');
  const [companyName, setCompanyName] = useState(user?.company_name || '');
  const [soloMode, setSoloMode] = useState(!!user?.solo_mode);
  const [saving, setSaving] = useState(false);
  const [logoB64, setLogoB64] = useState<string | null | undefined>(user?.company_logo_base64 || null);
  const [savingLogo, setSavingLogo] = useState(false);

  useEffect(() => {
    setFullName(user?.full_name || '');
    setCompanyName(user?.company_name || '');
    setSoloMode(!!user?.solo_mode);
    setLogoB64(user?.company_logo_base64 || null);
  }, [user]);

  const save = async () => {
    setSaving(true);
    try {
      const payload: any = { full_name: fullName.trim(), company_name: companyName.trim() };
      if (user?.role === 'admin') payload.solo_mode = soloMode;
      await Auth.updateProfile(payload);
      await refresh();
      Alert.alert('Enregistré', 'Vos paramètres ont été mis à jour.');
    } catch (e: any) {
      Alert.alert('Erreur', e?.response?.data?.detail || 'Sauvegarde impossible');
    } finally { setSaving(false); }
  };

  const toggleSolo = async (val: boolean) => {
    setSoloMode(val);
    setSaving(true);
    try {
      await Auth.updateProfile({ solo_mode: val });
      await refresh();
    } catch (e: any) {
      Alert.alert('Erreur', e?.response?.data?.detail || 'Erreur');
      setSoloMode(!val);
    } finally { setSaving(false); }
  };

  const onPickLogo = async () => {
    if (savingLogo) return;
    try {
      const img = await pickLogo();
      if (!img || !img.base64) return;
      setSavingLogo(true);
      const dataUri = `data:image/png;base64,${img.base64}`;
      await Auth.updateProfile({ company_logo_base64: dataUri });
      await refresh();
      setLogoB64(dataUri);
    } catch (e: any) {
      Alert.alert('Erreur', e?.response?.data?.detail || "Impossible d'enregistrer le logo");
    } finally { setSavingLogo(false); }
  };

  const onRemoveLogo = async () => {
    Alert.alert('Supprimer le logo ?', "Vos PDF ne contiendront plus de logo personnalisé.", [
      { text: 'Annuler', style: 'cancel' },
      {
        text: 'Supprimer', style: 'destructive', onPress: async () => {
          setSavingLogo(true);
          try {
            await Auth.updateProfile({ company_logo_base64: '' });
            await refresh();
            setLogoB64(null);
          } catch (e: any) {
            Alert.alert('Erreur', e?.response?.data?.detail || 'Erreur');
          } finally { setSavingLogo(false); }
        },
      },
    ]);
  };

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={{ flex: 1 }}>
        <View style={styles.topbar}>
          <TouchableOpacity onPress={() => router.back()} testID="back-btn">
            <Ionicons name="arrow-back" size={24} color={C.WHITE} />
          </TouchableOpacity>
          <Text style={styles.title}>PARAMÈTRES</Text>
          <View style={{ width: 24 }} />
        </View>

        <ScrollView contentContainerStyle={{ padding: SP.lg, paddingBottom: 48 }} keyboardShouldPersistTaps="handled">
          {/* Profile */}
          <Text style={styles.section}>PROFIL</Text>

          <View style={styles.userBlock}>
            <View style={[styles.avatar, { backgroundColor: user?.role === 'admin' ? C.ACCENT : C.WARN }]}>
              <Text style={{ color: C.DARK, fontWeight: '800', fontSize: 22 }}>{(user?.full_name || '?').charAt(0)}</Text>
            </View>
            <View style={{ marginLeft: SP.md, flex: 1 }}>
              <Text style={styles.userName}>{user?.full_name}</Text>
              <Text style={styles.userEmail}>{user?.email}</Text>
              <Text style={[styles.userRole, { color: user?.role === 'admin' ? C.ACCENT : C.WARN }]}>
                {user?.role?.toUpperCase()}{user?.solo_mode ? '  ·  ARTISAN' : ''}
              </Text>
            </View>
          </View>

          <Text style={styles.label}>NOM COMPLET</Text>
          <TextInput
            style={styles.input}
            value={fullName}
            onChangeText={setFullName}
            placeholderTextColor={C.GRAY3}
            testID="settings-input-name"
          />

          <Text style={styles.label}>NOM DE LA SOCIÉTÉ</Text>
          <TextInput
            style={styles.input}
            value={companyName}
            onChangeText={setCompanyName}
            placeholderTextColor={C.GRAY3}
            testID="settings-input-company"
          />

          <TouchableOpacity style={styles.saveBtn} onPress={save} disabled={saving} testID="settings-save">
            {saving ? <ActivityIndicator color={C.DARK} /> : <Text style={styles.saveTxt}>ENREGISTRER LE PROFIL</Text>}
          </TouchableOpacity>

          {/* Logo entreprise (Admin only) */}
          {user?.role === 'admin' && (
            <>
              <Text style={styles.section}>LOGO ENTREPRISE</Text>
              <View style={styles.logoCard}>
                <View style={styles.logoPreviewWrap}>
                  {logoB64 ? (
                    <Image source={{ uri: logoB64.startsWith('data:') ? logoB64 : `data:image/png;base64,${logoB64}` }} style={styles.logoPreview} resizeMode="contain" />
                  ) : (
                    <View style={[styles.logoPreview, styles.logoPlaceholder]}>
                      <MaterialCommunityIcons name="image-plus" size={36} color={C.GRAY3} />
                    </View>
                  )}
                </View>
                <Text style={styles.logoHint}>Apparaîtra en en-tête de tous vos rapports PDF (max 22×16 mm).</Text>
                <View style={styles.logoActions}>
                  <TouchableOpacity
                    style={[styles.logoBtn, styles.logoBtnPrimary, savingLogo && { opacity: 0.5 }]}
                    onPress={onPickLogo}
                    disabled={savingLogo}
                    testID="settings-logo-pick"
                  >
                    {savingLogo ? <ActivityIndicator color={C.DARK} /> : (
                      <>
                        <MaterialCommunityIcons name={logoB64 ? 'image-edit' : 'image-plus'} size={18} color={C.DARK} />
                        <Text style={styles.logoBtnTxt}>{logoB64 ? 'CHANGER' : 'CHOISIR UN LOGO'}</Text>
                      </>
                    )}
                  </TouchableOpacity>
                  {logoB64 && !savingLogo && (
                    <TouchableOpacity
                      style={[styles.logoBtn, styles.logoBtnDanger]}
                      onPress={onRemoveLogo}
                      testID="settings-logo-remove"
                    >
                      <Ionicons name="trash-outline" size={18} color={C.DANGER} />
                      <Text style={[styles.logoBtnTxt, { color: C.DANGER }]}>SUPPRIMER</Text>
                    </TouchableOpacity>
                  )}
                </View>
              </View>
            </>
          )}

          {/* Solo mode (admin only) */}
          {user?.role === 'admin' && (
            <>
              <Text style={styles.section}>MODE DE TRAVAIL</Text>
              <View style={[styles.soloCard, soloMode && styles.soloCardActive]}>
                <View style={styles.soloRow}>
                  <MaterialCommunityIcons name="account-star" size={28} color={soloMode ? C.ACCENT : C.GRAY3} />
                  <View style={{ flex: 1, marginLeft: SP.md }}>
                    <Text style={styles.soloTitle}>Activer le mode artisan unique</Text>
                    <Text style={styles.soloDesc}>
                      Fusion des droits Admin + Technicien. Créez et mesurez vos chantiers sans étape d'assignation.
                    </Text>
                  </View>
                  <Switch
                    value={soloMode}
                    onValueChange={toggleSolo}
                    trackColor={{ false: C.BORDER, true: C.ACCENT }}
                    thumbColor={soloMode ? C.WHITE : C.GRAY3}
                    testID="toggle-solo-mode"
                  />
                </View>
                {soloMode && (
                  <View style={styles.soloActive}>
                    <Ionicons name="checkmark-circle" size={16} color={C.ACCENT} />
                    <Text style={styles.soloActiveTxt}>Mode artisan actif — pleins pouvoirs sur tous les chantiers.</Text>
                  </View>
                )}
              </View>
            </>
          )}

          <Text style={styles.section}>À PROPOS</Text>
          <View style={styles.aboutCard}>
            <View style={styles.aboutRow}>
              <View style={styles.aboutBadge}>
                <MaterialCommunityIcons name="stairs" size={20} color={C.ACCENT} />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.aboutTitle}>MesureEscalier</Text>
                <Text style={styles.aboutLine}>Version <Text style={{ color: C.ACCENT, fontWeight: '700' }}>1.2.0</Text> · Phase 1 polish</Text>
              </View>
            </View>
            <View style={styles.aboutDivider} />
            <Text style={styles.aboutLine}>
              <Ionicons name="mail-outline" size={12} color={C.GRAY3} /> info@mesureescalier.com
            </Text>
            <Text style={styles.aboutLine}>
              <Ionicons name="cloud-done-outline" size={12} color={C.ACCENT} /> Mises à jour automatiques (OTA)
            </Text>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: C.DARK },
  topbar: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', padding: SP.lg, borderBottomWidth: 1, borderBottomColor: C.BORDER },
  title: { ...FONT.h2, fontSize: 18 },
  section: { ...FONT.label, color: C.ACCENT, marginTop: SP.xl, marginBottom: SP.md },
  userBlock: { flexDirection: 'row', alignItems: 'center', backgroundColor: C.CARD, borderRadius: R.lg, padding: SP.lg, borderWidth: 1, borderColor: C.BORDER },
  avatar: { width: 56, height: 56, borderRadius: 28, alignItems: 'center', justifyContent: 'center' },
  userName: { ...FONT.h3 },
  userEmail: { ...FONT.small, marginTop: 2 },
  userRole: { ...FONT.label, fontSize: 10, marginTop: 4 },
  label: { ...FONT.label, marginTop: SP.lg, marginBottom: SP.sm },
  input: { backgroundColor: C.BG_DEEPER, borderWidth: 1, borderColor: C.BORDER, borderRadius: R.md, paddingHorizontal: SP.md, paddingVertical: 14, color: C.WHITE, fontSize: 16 },
  saveBtn: { backgroundColor: C.ACCENT, borderRadius: R.md, paddingVertical: 16, alignItems: 'center', marginTop: SP.xl },
  saveTxt: { ...FONT.button, color: C.DARK, fontSize: 14 },
  soloCard: { backgroundColor: C.CARD, borderRadius: R.lg, padding: SP.lg, borderWidth: 1, borderColor: C.BORDER },
  soloCardActive: { borderColor: C.ACCENT, backgroundColor: C.ACCENT_BG },
  soloRow: { flexDirection: 'row', alignItems: 'center' },
  soloTitle: { ...FONT.h3, fontSize: 15 },
  soloDesc: { ...FONT.small, marginTop: 4, lineHeight: 16 },
  soloActive: { flexDirection: 'row', alignItems: 'center', marginTop: SP.md, paddingTop: SP.md, borderTopWidth: 1, borderTopColor: 'rgba(140,198,63,0.2)' },
  soloActiveTxt: { ...FONT.small, color: C.GRAY1, marginLeft: SP.sm, flex: 1 },
  aboutCard: { backgroundColor: C.CARD, borderRadius: R.lg, padding: SP.lg, borderWidth: 1, borderColor: C.BORDER },
  aboutRow: { flexDirection: 'row', alignItems: 'center', gap: SP.md },
  aboutBadge: { width: 42, height: 42, borderRadius: R.md, backgroundColor: C.ACCENT_BG, alignItems: 'center', justifyContent: 'center', borderWidth: 1, borderColor: C.ACCENT },
  aboutTitle: { ...FONT.h3, fontSize: 14 },
  aboutLine: { ...FONT.small, marginBottom: 4 },
  aboutDivider: { height: 1, backgroundColor: C.BORDER, marginVertical: SP.md },
  logoCard: { backgroundColor: C.CARD, borderRadius: R.lg, padding: SP.lg, borderWidth: 1, borderColor: C.BORDER, alignItems: 'center' },
  logoPreviewWrap: { width: 140, height: 140, alignItems: 'center', justifyContent: 'center' },
  logoPreview: { width: 140, height: 140, borderRadius: R.md, backgroundColor: C.WHITE },
  logoPlaceholder: { alignItems: 'center', justifyContent: 'center', backgroundColor: C.BG_DEEPER, borderWidth: 1, borderColor: C.BORDER, borderStyle: 'dashed' as any },
  logoHint: { ...FONT.small, color: C.GRAY2, textAlign: 'center', marginTop: SP.md, paddingHorizontal: SP.md },
  logoActions: { flexDirection: 'row', gap: SP.sm, marginTop: SP.lg, alignSelf: 'stretch' },
  logoBtn: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: SP.sm, paddingVertical: 12, borderRadius: R.md, borderWidth: 1 },
  logoBtnPrimary: { backgroundColor: C.ACCENT, borderColor: C.ACCENT },
  logoBtnDanger: { backgroundColor: 'transparent', borderColor: C.DANGER },
  logoBtnTxt: { ...FONT.button, color: C.DARK, fontSize: 12 },
});
