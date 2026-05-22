import React, { useEffect, useState, useCallback } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet, ScrollView, Alert,
  ActivityIndicator, KeyboardAvoidingView, Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons, MaterialCommunityIcons, Feather } from '@expo/vector-icons';
import { Team, User } from '@/src/api';
import { useAuth } from '@/src/auth';
import { C, SP, R, FONT } from '@/src/theme';

export default function TeamScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const [list, setList] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<'technicien'>('technicien');
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try { setList(await Team.list()); }
    catch (e: any) { Alert.alert('Erreur', e?.response?.data?.detail || 'Chargement impossible'); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const invite = async () => {
    if (!fullName || !email || password.length < 6) {
      Alert.alert('Champs', 'Nom, email et mot de passe (≥6 caractères) requis.');
      return;
    }
    setSaving(true);
    try {
      await Team.invite({ full_name: fullName.trim(), email: email.trim(), password, role });
      setShowForm(false); setFullName(''); setEmail(''); setPassword('');
      load();
    } catch (e: any) {
      Alert.alert('Erreur', e?.response?.data?.detail || 'Création impossible');
    } finally { setSaving(false); }
  };

  const remove = async (u: User) => {
    Alert.alert('Supprimer ?', `Supprimer ${u.full_name} (${u.email}) ?`, [
      { text: 'Annuler', style: 'cancel' },
      {
        text: 'Supprimer', style: 'destructive', onPress: async () => {
          try { await Team.remove(u.id); load(); }
          catch (e: any) { Alert.alert('Erreur', e?.response?.data?.detail || 'Erreur'); }
        },
      },
    ]);
  };

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={{ flex: 1 }}>
        <View style={styles.topbar}>
          <TouchableOpacity onPress={() => router.back()} testID="back-btn"><Ionicons name="arrow-back" size={24} color={C.WHITE} /></TouchableOpacity>
          <Text style={styles.title}>ÉQUIPE</Text>
          <TouchableOpacity onPress={() => setShowForm(s => !s)} testID="btn-toggle-form">
            <Ionicons name={showForm ? 'close' : 'add'} size={26} color={C.ACCENT} />
          </TouchableOpacity>
        </View>

        <ScrollView contentContainerStyle={{ padding: SP.lg, paddingBottom: 48 }}>
          {showForm && (
            <View style={styles.formCard}>
              <Text style={styles.formHead}>INVITER UN MEMBRE</Text>

              <Text style={styles.label}>RÔLE</Text>
              <View style={styles.roleRow}>
                {(['technicien'] as const).map(r => (
                  <TouchableOpacity
                    key={r}
                    style={[styles.roleBtn, role === r && styles.roleBtnActive]}
                    onPress={() => setRole(r)}
                    testID={`role-${r}`}
                  >
                    <MaterialCommunityIcons
                      name={'wrench'}
                      size={16}
                      color={role === r ? C.DARK : C.ACCENT}
                    />
                    <Text style={[styles.roleTxt, role === r && { color: C.DARK }]}>{r.toUpperCase()}</Text>
                  </TouchableOpacity>
                ))}
              </View>

              <Text style={styles.label}>NOM COMPLET</Text>
              <TextInput style={styles.input} value={fullName} onChangeText={setFullName} placeholder="Marc Commercial" placeholderTextColor={C.GRAY3} testID="invite-name" />

              <Text style={styles.label}>EMAIL</Text>
              <TextInput style={styles.input} value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address" placeholder="marc@entreprise.fr" placeholderTextColor={C.GRAY3} testID="invite-email" />

              <Text style={styles.label}>MOT DE PASSE TEMPORAIRE</Text>
              <TextInput style={styles.input} value={password} onChangeText={setPassword} secureTextEntry placeholder="≥ 6 caractères" placeholderTextColor={C.GRAY3} testID="invite-password" />

              <TouchableOpacity style={styles.cta} onPress={invite} disabled={saving} testID="invite-submit">
                {saving ? <ActivityIndicator color={C.DARK} /> : <Text style={styles.ctaTxt}>CRÉER LE COMPTE</Text>}
              </TouchableOpacity>
            </View>
          )}

          {loading ? (
            <View style={{ paddingVertical: 60, alignItems: 'center' }}><ActivityIndicator color={C.ACCENT} /></View>
          ) : (
            list.map(u => (
              <View key={u.id} style={styles.userCard}>
                <View style={[styles.avatar, { backgroundColor: u.role === 'admin' ? C.ACCENT : C.WARN }]}>
                  <Text style={{ color: C.DARK, fontWeight: '800', fontSize: 16 }}>{u.full_name.charAt(0)}</Text>
                </View>
                <View style={{ flex: 1, marginLeft: SP.md }}>
                  <Text style={styles.userName}>{u.full_name}</Text>
                  <Text style={styles.userEmail}>{u.email}</Text>
                  <Text style={[styles.userRole, { color: u.role === 'admin' ? C.ACCENT : C.WARN }]}>
                    {u.role.toUpperCase()}{u.solo_mode ? '  ·  ARTISAN' : ''}
                  </Text>
                </View>
                {u.id !== user?.id && u.role !== 'admin' && (
                  <TouchableOpacity onPress={() => remove(u)} testID={`delete-user-${u.id}`}>
                    <Feather name="trash-2" size={20} color={C.DANGER} />
                  </TouchableOpacity>
                )}
              </View>
            ))
          )}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: C.DARK },
  topbar: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', padding: SP.lg, borderBottomWidth: 1, borderBottomColor: C.BORDER },
  title: { ...FONT.h2, fontSize: 18 },
  formCard: { backgroundColor: C.CARD, borderRadius: R.lg, padding: SP.lg, borderWidth: 1, borderColor: C.BORDER, marginBottom: SP.lg },
  formHead: { ...FONT.label, color: C.ACCENT },
  label: { ...FONT.label, marginTop: SP.lg, marginBottom: SP.sm },
  input: { backgroundColor: C.BG_DEEPER, borderWidth: 1, borderColor: C.BORDER, borderRadius: R.md, paddingHorizontal: SP.md, paddingVertical: 14, color: C.WHITE, fontSize: 16 },
  roleRow: { flexDirection: 'row', gap: SP.md },
  roleBtn: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, backgroundColor: C.BG_DEEPER, borderRadius: R.md, paddingVertical: 12, borderWidth: 1, borderColor: C.BORDER },
  roleBtnActive: { backgroundColor: C.ACCENT, borderColor: C.ACCENT },
  roleTxt: { ...FONT.button, color: C.WHITE, fontSize: 12 },
  cta: { backgroundColor: C.ACCENT, borderRadius: R.md, paddingVertical: 16, alignItems: 'center', marginTop: SP.lg },
  ctaTxt: { ...FONT.button, color: C.DARK, fontSize: 14 },
  userCard: { flexDirection: 'row', alignItems: 'center', backgroundColor: C.CARD, borderRadius: R.lg, padding: SP.md, borderWidth: 1, borderColor: C.BORDER, marginBottom: SP.sm },
  avatar: { width: 44, height: 44, borderRadius: 22, alignItems: 'center', justifyContent: 'center' },
  userName: { ...FONT.body, fontWeight: '700' },
  userEmail: { ...FONT.small },
  userRole: { ...FONT.label, fontSize: 10, marginTop: 2 },
});
