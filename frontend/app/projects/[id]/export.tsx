import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ActivityIndicator, Alert, ScrollView, Platform } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { useLocalSearchParams, useRouter } from 'expo-router';
import * as FileSystem from 'expo-file-system/legacy';
import * as Sharing from 'expo-sharing';
import { Projects, Exports, getToken } from '@/src/api';
import { C, SP, R, FONT } from '@/src/theme';

export default function ExportScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const [project, setProject] = useState<any>(null);
  const [pdfPath, setPdfPath] = useState<string | null>(null);
  const [dxfPath, setDxfPath] = useState<string | null>(null);
  const [busy, setBusy] = useState<'pdf' | 'dxf' | 'share' | null>(null);

  useEffect(() => { if (id) Projects.get(id).then(setProject); }, [id]);

  const download = async (kind: 'pdf' | 'dxf') => {
    if (!id || !project) return;
    setBusy(kind);
    try {
      const url = kind === 'pdf' ? Exports.pdfUrl(id) : Exports.dxfUrl(id);
      const token = await getToken();
      const safeName = (project.client_nom || 'chantier').toLowerCase().replace(/[^a-z0-9_-]/g, '_');
      const target = `${FileSystem.cacheDirectory}${safeName}.${kind}`;
      const res = await FileSystem.downloadAsync(url, target, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.status !== 200) throw new Error(`HTTP ${res.status}`);
      if (kind === 'pdf') setPdfPath(res.uri); else setDxfPath(res.uri);
      Alert.alert('Téléchargé', `${kind.toUpperCase()} prêt à être partagé.`);
    } catch (e: any) {
      Alert.alert('Erreur', String(e?.message || e));
    } finally { setBusy(null); }
  };

  const share = async () => {
    if (!pdfPath && !dxfPath) {
      Alert.alert('Aucun fichier', 'Générez d\'abord le PDF ou le DXF.');
      return;
    }
    setBusy('share');
    try {
      const available = await Sharing.isAvailableAsync();
      if (!available) {
        Alert.alert('Partage indisponible', 'Le partage natif n\'est pas pris en charge sur cette plateforme.');
        return;
      }
      const file = pdfPath || dxfPath!;
      await Sharing.shareAsync(file, {
        mimeType: file.endsWith('.pdf') ? 'application/pdf' : 'application/dxf',
        dialogTitle: 'Partager le rapport MesureEscalier',
      });
    } catch (e: any) {
      Alert.alert('Erreur partage', String(e?.message || e));
    } finally { setBusy(null); }
  };

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <View style={styles.topbar}>
        <TouchableOpacity onPress={() => router.back()} testID="back-btn"><Ionicons name="arrow-back" size={24} color={C.WHITE} /></TouchableOpacity>
        <Text style={styles.title}>EXPORTS</Text>
        <View style={{ width: 24 }} />
      </View>

      <ScrollView contentContainerStyle={{ padding: SP.lg, paddingBottom: 48 }}>
        <Text style={styles.head}>Génération des livrables</Text>
        <Text style={styles.subtitle}>Téléchargez le rapport PDF et le fichier 2D vectoriel DXF pour AutoCAD.</Text>

        <View style={styles.card}>
          <View style={styles.cardHead}>
            <MaterialCommunityIcons name="file-pdf-box" size={28} color={C.ACCENT} />
            <View style={{ flex: 1, marginLeft: SP.md }}>
              <Text style={styles.cardTitle}>Rapport PDF</Text>
              <Text style={styles.cardSub}>Client, mesures, schéma 2D et notes terrain.</Text>
            </View>
          </View>
          <TouchableOpacity style={styles.btn} onPress={() => download('pdf')} disabled={busy !== null} testID="btn-export-pdf">
            {busy === 'pdf' ? <ActivityIndicator color={C.DARK} /> : (
              <>
                <MaterialCommunityIcons name="download" size={18} color={C.DARK} />
                <Text style={styles.btnTxt}>{pdfPath ? 'RÉGÉNÉRER PDF' : 'GÉNÉRER PDF'}</Text>
              </>
            )}
          </TouchableOpacity>
          {pdfPath && <Text style={styles.ready}>✓ PDF prêt</Text>}
        </View>

        <View style={styles.card}>
          <View style={styles.cardHead}>
            <MaterialCommunityIcons name="file-cad-box" size={28} color={C.ACCENT} />
            <View style={{ flex: 1, marginLeft: SP.md }}>
              <Text style={styles.cardTitle}>Fichier DXF (AutoCAD)</Text>
              <Text style={styles.cardSub}>Profil 2D vectoriel : marches, hypoténuse, trémie.</Text>
            </View>
          </View>
          <TouchableOpacity style={styles.btn} onPress={() => download('dxf')} disabled={busy !== null} testID="btn-export-dxf">
            {busy === 'dxf' ? <ActivityIndicator color={C.DARK} /> : (
              <>
                <MaterialCommunityIcons name="download" size={18} color={C.DARK} />
                <Text style={styles.btnTxt}>{dxfPath ? 'RÉGÉNÉRER DXF' : 'GÉNÉRER DXF'}</Text>
              </>
            )}
          </TouchableOpacity>
          {dxfPath && <Text style={styles.ready}>✓ DXF prêt</Text>}
        </View>

        <TouchableOpacity style={[styles.btn, styles.btnShare]} onPress={share} disabled={busy !== null} testID="btn-share">
          {busy === 'share' ? <ActivityIndicator color={C.WHITE} /> : (
            <>
              <Ionicons name="share-social" size={20} color={C.WHITE} />
              <Text style={[styles.btnTxt, { color: C.WHITE }]}>PARTAGER (PDF + DXF)</Text>
            </>
          )}
        </TouchableOpacity>

        {Platform.OS === 'web' && (
          <Text style={styles.note}>
            ℹ️ Le partage natif n'est pas disponible sur web. Téléchargez les fichiers directement.
          </Text>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: C.DARK },
  topbar: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', padding: SP.lg, borderBottomWidth: 1, borderBottomColor: C.BORDER },
  title: { ...FONT.h2, fontSize: 18 },
  head: { ...FONT.h2, fontSize: 22 },
  subtitle: { ...FONT.small, marginTop: SP.sm, marginBottom: SP.lg },
  card: { backgroundColor: C.CARD, borderRadius: R.lg, padding: SP.lg, borderWidth: 1, borderColor: C.BORDER, marginBottom: SP.md },
  cardHead: { flexDirection: 'row', alignItems: 'center', marginBottom: SP.md },
  cardTitle: { ...FONT.h3 },
  cardSub: { ...FONT.small, marginTop: 2 },
  btn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: SP.sm, backgroundColor: C.ACCENT, borderRadius: R.md, paddingVertical: 14 },
  btnShare: { backgroundColor: C.INFO, marginTop: SP.lg },
  btnTxt: { ...FONT.button, color: C.DARK, fontSize: 13 },
  ready: { ...FONT.small, color: C.ACCENT, marginTop: SP.sm, textAlign: 'center' },
  note: { ...FONT.small, marginTop: SP.lg, textAlign: 'center', color: C.GRAY3 },
});
