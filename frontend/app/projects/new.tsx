import React, { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet, ScrollView,
  KeyboardAvoidingView, Platform, Alert, ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { Projects } from '@/src/api';
import { C, SP, R, FONT } from '@/src/theme';

export default function NewProject() {
  const router = useRouter();
  const [nom, setNom] = useState('');
  const [prenom, setPrenom] = useState('');
  const [address, setAddress] = useState('');
  const [postalCode, setPostalCode] = useState('');
  const [city, setCity] = useState('');
  const [phone, setPhone] = useState('');
  const [notes, setNotes] = useState('');
  const [saving, setSaving] = useState(false);

  const submit = async () => {
    if (!nom || !address) {
      Alert.alert('Champs requis', 'Le nom client et l\'adresse sont obligatoires.');
      return;
    }
    setSaving(true);
    try {
      const p = await Projects.create({
        client_nom: nom.trim(), client_prenom: prenom.trim(),
        address: address.trim(), postal_code: postalCode.trim(), city: city.trim(),
        phone: phone.trim(), notes: notes.trim(),
      });
      router.replace(`/projects/${p.id}`);
    } catch (e: any) {
      Alert.alert('Erreur', e?.response?.data?.detail || 'Création impossible');
    } finally {
      setSaving(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe} edges={['top', 'bottom']}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={{ flex: 1 }}>
        <View style={styles.topbar}>
          <TouchableOpacity onPress={() => router.back()} testID="back-btn">
            <Ionicons name="arrow-back" size={24} color={C.WHITE} />
          </TouchableOpacity>
          <Text style={styles.title}>NOUVEAU CHANTIER</Text>
          <View style={{ width: 24 }} />
        </View>

        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          <Text style={styles.subtitle}>Identification du client</Text>

          <View style={styles.row}>
            <View style={{ flex: 1 }}>
              <Text style={styles.label}>NOM *</Text>
              <TextInput
                style={styles.input}
                placeholder="Dupont"
                placeholderTextColor={C.GRAY3}
                value={nom}
                onChangeText={setNom}
                testID="modal-input-nom"
              />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.label}>PRÉNOM</Text>
              <TextInput
                style={styles.input}
                placeholder="Marie"
                placeholderTextColor={C.GRAY3}
                value={prenom}
                onChangeText={setPrenom}
                testID="modal-input-prenom"
              />
            </View>
          </View>

          <Text style={styles.label}>ADRESSE & NUMÉRO *</Text>
          <TextInput
            style={styles.input}
            placeholder="15 Rue de la République"
            placeholderTextColor={C.GRAY3}
            value={address}
            onChangeText={setAddress}
            testID="modal-input-address"
          />

          <View style={styles.row}>
            <View style={{ flex: 1 }}>
              <Text style={styles.label}>CODE POSTAL</Text>
              <TextInput
                style={styles.input}
                placeholder="75011"
                placeholderTextColor={C.GRAY3}
                value={postalCode}
                onChangeText={setPostalCode}
                keyboardType="numeric"
                testID="modal-input-cp"
              />
            </View>
            <View style={{ flex: 2 }}>
              <Text style={styles.label}>VILLE</Text>
              <TextInput
                style={styles.input}
                placeholder="Paris"
                placeholderTextColor={C.GRAY3}
                value={city}
                onChangeText={setCity}
                testID="modal-input-city"
              />
            </View>
          </View>

          <Text style={styles.label}>TÉLÉPHONE</Text>
          <TextInput
            style={styles.input}
            placeholder="06 12 34 56 78"
            placeholderTextColor={C.GRAY3}
            value={phone}
            onChangeText={setPhone}
            keyboardType="phone-pad"
            testID="modal-input-phone"
          />

          <Text style={styles.label}>NOTES & INSTRUCTIONS</Text>
          <TextInput
            style={[styles.input, { height: 100, textAlignVertical: 'top', paddingTop: 12 }]}
            placeholder="Clé sous le paillasson, accès portail latéral..."
            placeholderTextColor={C.GRAY3}
            value={notes}
            onChangeText={setNotes}
            multiline
            testID="modal-input-notes"
          />

          <View style={styles.btnRow}>
            <TouchableOpacity style={styles.cancel} onPress={() => router.back()} testID="modal-cancel">
              <Text style={styles.cancelTxt}>ANNULER</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.create} onPress={submit} disabled={saving} testID="modal-submit-project">
              {saving ? <ActivityIndicator color={C.DARK} /> : <Text style={styles.createTxt}>CRÉER</Text>}
            </TouchableOpacity>
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
  scroll: { padding: SP.lg, paddingBottom: 48 },
  subtitle: { ...FONT.small, marginBottom: SP.lg },
  row: { flexDirection: 'row', gap: SP.md },
  label: { ...FONT.label, marginTop: SP.lg, marginBottom: SP.sm },
  input: {
    backgroundColor: C.BG_DEEPER, borderWidth: 1, borderColor: C.BORDER,
    borderRadius: R.md, paddingHorizontal: SP.md, paddingVertical: 14,
    color: C.WHITE, fontSize: 16,
  },
  btnRow: { flexDirection: 'row', gap: SP.md, marginTop: SP.xl },
  cancel: { flex: 1, borderWidth: 1, borderColor: C.BORDER, borderRadius: R.md, paddingVertical: 16, alignItems: 'center', backgroundColor: C.CARD },
  cancelTxt: { ...FONT.button, color: C.WHITE, fontSize: 14 },
  create: { flex: 1, backgroundColor: C.ACCENT, borderRadius: R.md, paddingVertical: 16, alignItems: 'center' },
  createTxt: { ...FONT.button, color: C.DARK, fontSize: 14 },
});
