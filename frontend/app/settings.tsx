import React, { useState, useEffect } from 'react';
import {
  View, Text, StyleSheet, TextInput, TouchableOpacity, ScrollView,
  KeyboardAvoidingView, Platform, Alert, ActivityIndicator, Switch,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { useAuth } from '@/src/auth';
import { Auth } from '@/src/api';
import { C, SP, R, FONT } from '@/src/theme';

export default function SettingsScreen() {
  const router = useRouter();
  const { user, refresh } = useAuth();
  const [fullName, setFullName] = useState(user?.full_name || '');
  const [companyName, setCompanyName] = useState(user?.company_name || '');
  const [soloMode, setSoloMode] = useState(!!user?.solo_mode);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setFullName(user?.full_name || '');
    setCompanyName(user?.company_name || '');
    setSoloMode(!!user?.solo_mode);
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
            <Text style={styles.aboutLine}>MesureEscalier · v1.1</Text>
            <Text style={styles.aboutLine}>info@mesureescalier.com</Text>
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
  aboutLine: { ...FONT.small, marginBottom: 4 },
});
