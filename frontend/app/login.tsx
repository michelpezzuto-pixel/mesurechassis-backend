import React, { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet, ScrollView,
  KeyboardAvoidingView, Platform, Alert, ActivityIndicator,
} from 'react-native';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { useAuth } from '@/src/auth';
import { C, SP, R, FONT } from '@/src/theme';

type Mode = 'login' | 'register';

export default function LoginScreen() {
  const router = useRouter();
  const { signIn, signUp } = useAuth();
  const [mode, setMode] = useState<Mode>('login');
  const [fullName, setFullName] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    if (!email || !password) {
      Alert.alert('Champs requis', 'Email et mot de passe sont obligatoires.');
      return;
    }
    if (mode === 'register' && !fullName) {
      Alert.alert('Champ requis', 'Indiquez votre nom complet.');
      return;
    }
    setLoading(true);
    try {
      if (mode === 'login') await signIn(email.trim(), password);
      else await signUp({ full_name: fullName.trim(), email: email.trim(), password, company_name: companyName.trim() || undefined });
      router.replace('/dashboard');
    } catch (e: any) {
      const msg = e?.response?.data?.detail || 'Échec de la connexion';
      Alert.alert('Erreur', String(msg));
    } finally {
      setLoading(false);
    }
  };

  const demo = async (role: 'admin' | 'commercial' | 'technicien') => {
    const map = {
      admin: 'admin@demo.fr',
      commercial: 'marc@mesureescalier.com',
      technicien: 'sophie@mesureescaliee.com',
    };
    setEmail(map[role]);
    setPassword('Demo1234!');
    setMode('login');
    setLoading(true);
    try {
      await signIn(map[role], 'Demo1234!');
      router.replace('/dashboard');
    } catch (e: any) {
      Alert.alert('Erreur', e?.response?.data?.detail || 'Échec démo');
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe} edges={['top', 'bottom']}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          {/* Logo */}
          <View style={styles.logoWrap}>
            <View style={styles.logoBox}>
              <MaterialCommunityIcons name="stairs-up" size={40} color={C.ACCENT} />
            </View>
            <Text style={styles.brand}>MESUREESCALIER</Text>
            <Text style={styles.tag}>Mesures terrain · Escaliers pro</Text>
          </View>

          {/* Tabs */}
          <View style={styles.tabs}>
            <TouchableOpacity
              style={[styles.tab, mode === 'login' && styles.tabActive]}
              onPress={() => setMode('login')}
              testID="login-tab-connexion"
            >
              <Text style={[styles.tabTxt, mode === 'login' && styles.tabTxtActive]}>CONNEXION</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.tab, mode === 'register' && styles.tabActive]}
              onPress={() => setMode('register')}
              testID="login-tab-inscription"
            >
              <Text style={[styles.tabTxt, mode === 'register' && styles.tabTxtActive]}>INSCRIPTION</Text>
            </TouchableOpacity>
          </View>

          {/* Form */}
          {mode === 'register' && (
            <>
              <Text style={styles.label}>NOM COMPLET (MASTER ADMIN)</Text>
              <TextInput
                style={styles.input}
                placeholder="ex. Marc Dubois"
                placeholderTextColor={C.GRAY3}
                value={fullName}
                onChangeText={setFullName}
                testID="signup-input-name"
              />
              <Text style={styles.label}>NOM DE LA SOCIÉTÉ (OPTIONNEL)</Text>
              <TextInput
                style={styles.input}
                placeholder="ex. Escaliers Dubois SARL"
                placeholderTextColor={C.GRAY3}
                value={companyName}
                onChangeText={setCompanyName}
                testID="signup-input-company"
              />
              <View style={styles.notice}>
                <Ionicons name="information-circle" size={16} color={C.ACCENT} />
                <Text style={styles.noticeTxt}>
                  L'inscription crée un compte <Text style={{ fontWeight: '800' }}>Master Admin</Text> pour
                  une nouvelle société. Les Commerciaux et Techniciens sont invités depuis l'écran Équipe.
                </Text>
              </View>
            </>
          )}

          <Text style={styles.label}>EMAIL</Text>
          <TextInput
            style={styles.input}
            placeholder="prenom.nom@entreprise.fr"
            placeholderTextColor={C.GRAY3}
            value={email}
            onChangeText={setEmail}
            autoCapitalize="none"
            keyboardType="email-address"
            testID="login-input-email"
          />

          <Text style={styles.label}>MOT DE PASSE</Text>
          <TextInput
            style={styles.input}
            placeholder="••••••••"
            placeholderTextColor={C.GRAY3}
            value={password}
            onChangeText={setPassword}
            secureTextEntry
            testID="login-input-password"
          />

          <TouchableOpacity style={styles.cta} onPress={submit} disabled={loading} testID="login-submit-button">
            {loading ? (
              <ActivityIndicator color={C.DARK} />
            ) : (
              <Text style={styles.ctaTxt}>{mode === 'login' ? 'SE CONNECTER' : 'CRÉER LE COMPTE'}</Text>
            )}
          </TouchableOpacity>

          {/* Demo accounts */}
          <Text style={styles.demoHead}>COMPTES DE DÉMO</Text>
          <View style={styles.demoRow}>
            <TouchableOpacity style={styles.demoBtn} onPress={() => demo('admin')} testID="demo-admin">
              <Ionicons name="shield-checkmark" size={16} color={C.ACCENT} />
              <Text style={styles.demoTxt}>ADMIN</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.demoBtn} onPress={() => demo('commercial')} testID="demo-commercial">
              <Ionicons name="briefcase" size={16} color={C.ACCENT} />
              <Text style={styles.demoTxt}>COMMERCIAL</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.demoBtn} onPress={() => demo('technicien')} testID="demo-technicien">
              <MaterialCommunityIcons name="wrench" size={16} color={C.ACCENT} />
              <Text style={styles.demoTxt}>TECHNICIEN</Text>
            </TouchableOpacity>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: C.DARK },
  scroll: { padding: SP.xl, paddingBottom: 48 },
  logoWrap: { alignItems: 'center', marginVertical: SP.xl },
  logoBox: {
    width: 88, height: 88, borderRadius: 20,
    borderWidth: 2, borderColor: C.ACCENT,
    alignItems: 'center', justifyContent: 'center',
    backgroundColor: 'rgba(140,198,63,0.08)',
  },
  brand: { ...FONT.h1, marginTop: SP.md, fontSize: 26, color: C.WHITE },
  tag: { ...FONT.small, marginTop: 4 },
  tabs: {
    flexDirection: 'row',
    backgroundColor: C.CARD,
    borderRadius: R.lg,
    padding: 4,
    marginBottom: SP.xl,
    borderWidth: 1, borderColor: C.BORDER,
  },
  tab: { flex: 1, paddingVertical: 14, borderRadius: R.md, alignItems: 'center' },
  tabActive: { backgroundColor: C.ACCENT },
  tabTxt: { ...FONT.button, color: C.GRAY3, fontSize: 13 },
  tabTxtActive: { color: C.DARK },
  label: { ...FONT.label, marginBottom: SP.sm, marginTop: SP.md },
  input: {
    backgroundColor: C.DARK,
    borderWidth: 1, borderColor: C.BORDER,
    borderRadius: R.md,
    paddingHorizontal: SP.md, paddingVertical: 14,
    color: C.WHITE, fontSize: 16,
  },
  notice: {
    flexDirection: 'row', gap: SP.sm, padding: SP.md,
    backgroundColor: C.ACCENT_BG, borderLeftWidth: 3, borderLeftColor: C.ACCENT,
    borderRadius: R.sm, marginTop: SP.md,
  },
  noticeTxt: { ...FONT.small, color: C.GRAY1, flex: 1, lineHeight: 18 },
  cta: {
    backgroundColor: C.ACCENT, borderRadius: R.lg,
    paddingVertical: 18, alignItems: 'center', marginTop: SP.xl,
  },
  ctaTxt: { ...FONT.button, color: C.DARK, fontSize: 16 },
  demoHead: { ...FONT.label, textAlign: 'center', marginTop: SP.xl },
  demoRow: { flexDirection: 'row', gap: SP.sm, marginTop: SP.md },
  demoBtn: {
    flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6,
    backgroundColor: C.CARD, borderRadius: R.md, paddingVertical: 14,
    borderWidth: 1, borderColor: C.BORDER,
  },
  demoTxt: { ...FONT.button, color: C.WHITE, fontSize: 12 },
});
