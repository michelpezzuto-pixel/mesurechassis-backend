import React, { useEffect, useState } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity, ActivityIndicator, Alert, ScrollView, Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons, MaterialCommunityIcons, Feather } from '@expo/vector-icons';
import { useLocalSearchParams, useRouter } from 'expo-router';
import * as FileSystem from 'expo-file-system/legacy';
import * as Sharing from 'expo-sharing';
import { Projects, Exports, getToken } from '@/src/api';
import { ScreenHeader } from '@shared-ui';
import { C, SP, R, FONT } from '@/src/theme';

/**
 * LIVRABLES — Écran de génération & partage des fichiers PDF / DXF.
 * Design "premium" : 2 grandes cartes avec icônes + statut + gros bouton de partage en bas.
 * Couleur du bouton "Partager" : violet/indigo profond (#5B5BE8 sur dégradé) pour
 * distinguer la zone "premium / export pro" du Vert Pomme métier.
 */
export default function LivrablesScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const [project, setProject] = useState<any>(null);
  const [pdfPath, setPdfPath] = useState<string | null>(null);
  const [dxfPath, setDxfPath] = useState<string | null>(null);
  const [busy, setBusy] = useState<'pdf' | 'dxf' | 'all' | 'share' | null>(null);

  useEffect(() => { if (id) Projects.get(id).then(setProject); }, [id]);

  const clientFullName = [project?.client_nom, project?.client_prenom].filter(Boolean).join(' ').trim() || 'Client';

  const download = async (kind: 'pdf' | 'dxf'): Promise<string | null> => {
    if (!id || !project) return null;
    try {
      const url = kind === 'pdf' ? Exports.pdfUrl(id) : Exports.dxfUrl(id);
      const token = await getToken();
      const safeName = (project.client_nom || 'chantier').toLowerCase().replace(/[^a-z0-9_-]/g, '_');
      const target = `${FileSystem.cacheDirectory}${safeName}.${kind}`;
      const res = await FileSystem.downloadAsync(url, target, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.status !== 200) throw new Error(`HTTP ${res.status}`);
      return res.uri;
    } catch (e: any) {
      Alert.alert('Erreur', String(e?.message || e));
      return null;
    }
  };

  const generate = async (kind: 'pdf' | 'dxf') => {
    setBusy(kind);
    const uri = await download(kind);
    if (uri) {
      if (kind === 'pdf') setPdfPath(uri); else setDxfPath(uri);
    }
    setBusy(null);
  };

  const generateBoth = async () => {
    setBusy('all');
    const [a, b] = await Promise.all([download('pdf'), download('dxf')]);
    if (a) setPdfPath(a);
    if (b) setDxfPath(b);
    setBusy(null);
  };

  const shareAll = async () => {
    // Auto-génère ce qui manque avant de partager
    let pdf = pdfPath;
    let dxf = dxfPath;
    if (!pdf || !dxf) {
      setBusy('all');
      const [a, b] = await Promise.all([
        pdf ? Promise.resolve(pdf) : download('pdf'),
        dxf ? Promise.resolve(dxf) : download('dxf'),
      ]);
      if (a) { setPdfPath(a); pdf = a; }
      if (b) { setDxfPath(b); dxf = b; }
    }
    if (!pdf && !dxf) { setBusy(null); return; }

    setBusy('share');
    try {
      const available = await Sharing.isAvailableAsync();
      if (!available) {
        Alert.alert('Partage indisponible', "Le partage natif n'est pas pris en charge sur cette plateforme.");
        return;
      }
      // expo-sharing ne partage qu'un fichier à la fois — on partage le PDF en priorité
      const file = pdf || dxf!;
      await Sharing.shareAsync(file, {
        mimeType: file.endsWith('.pdf') ? 'application/pdf' : 'application/dxf',
        dialogTitle: `Rapport ${clientFullName}`,
      });
    } catch (e: any) {
      Alert.alert('Erreur partage', String(e?.message || e));
    } finally { setBusy(null); }
  };

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <ScreenHeader title="LIVRABLES" />

      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        {/* Header chantier : NOM CLIENT en évidence */}
        <View style={styles.clientBlock}>
          <Text style={styles.clientLabel}>CLIENT</Text>
          <Text style={styles.clientName} numberOfLines={2}>{clientFullName.toUpperCase()}</Text>
          {!!project?.address && (
            <Text style={styles.clientAddress} numberOfLines={1}>
              <Ionicons name="location-outline" size={12} color={C.GRAY3} /> {project.address}{project.city ? `, ${project.city}` : ''}
            </Text>
          )}
        </View>

        <Text style={styles.section}>FICHIERS DISPONIBLES</Text>

        {/* Card PDF */}
        <FileCard
          icon="file-pdf-box"
          tint="#EF4444"
          title="Rapport PDF"
          subtitle="Mesures, schéma 2D, photos du chantier et notes terrain."
          ready={!!pdfPath}
          loading={busy === 'pdf'}
          disabled={busy !== null && busy !== 'pdf'}
          onPress={() => generate('pdf')}
          testID="btn-generate-pdf"
        />

        {/* Card DXF */}
        <FileCard
          icon="file-cad-box"
          tint="#3B82F6"
          title="Fichier DXF (AutoCAD)"
          subtitle="Profil 2D vectoriel pour découpe atelier : marches, limon, trémie."
          ready={!!dxfPath}
          loading={busy === 'dxf'}
          disabled={busy !== null && busy !== 'dxf'}
          onPress={() => generate('dxf')}
          testID="btn-generate-dxf"
        />

        <TouchableOpacity
          style={[styles.generateAll, busy && { opacity: 0.5 }]}
          onPress={generateBoth}
          disabled={busy !== null}
          testID="btn-generate-all"
        >
          {busy === 'all' ? <ActivityIndicator color={C.ACCENT} /> : (
            <>
              <Feather name="zap" size={16} color={C.ACCENT} />
              <Text style={styles.generateAllTxt}>GÉNÉRER LES DEUX FICHIERS</Text>
            </>
          )}
        </TouchableOpacity>

        {Platform.OS === 'web' && (
          <Text style={styles.webNote}>
            ℹ️ Sur le web, les fichiers sont téléchargés directement (pas de partage natif).
          </Text>
        )}
      </ScrollView>

      {/* CTA "PARTAGER" — bouton premium violet, sticky bottom */}
      <View style={styles.bottomBar}>
        <TouchableOpacity
          style={[styles.shareBtn, (!pdfPath && !dxfPath) && styles.shareBtnIdle, busy === 'share' && { opacity: 0.7 }]}
          onPress={shareAll}
          disabled={busy === 'share'}
          testID="btn-share-all"
        >
          {busy === 'share' || busy === 'all' ? <ActivityIndicator color={C.WHITE} /> : (
            <>
              <Ionicons name="share-social" size={22} color={C.WHITE} />
              <Text style={styles.shareTxt}>PARTAGER (PDF + DXF)</Text>
            </>
          )}
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

interface FileCardProps {
  icon: any;
  tint: string;
  title: string;
  subtitle: string;
  ready: boolean;
  loading: boolean;
  disabled: boolean;
  onPress: () => void;
  testID?: string;
}

function FileCard({ icon, tint, title, subtitle, ready, loading, disabled, onPress, testID }: FileCardProps) {
  return (
    <TouchableOpacity
      style={[styles.card, ready && styles.cardReady]}
      onPress={onPress}
      disabled={disabled || loading}
      activeOpacity={0.85}
      testID={testID}
    >
      <View style={[styles.cardIcon, { backgroundColor: tint + '20', borderColor: tint }]}>
        <MaterialCommunityIcons name={icon} size={28} color={tint} />
      </View>
      <View style={{ flex: 1, marginLeft: SP.lg }}>
        <Text style={styles.cardTitle}>{title}</Text>
        <Text style={styles.cardSubtitle}>{subtitle}</Text>
        {ready && (
          <View style={styles.cardStatus}>
            <Ionicons name="checkmark-circle" size={14} color={C.ACCENT} />
            <Text style={styles.cardStatusTxt}>FICHIER PRÊT</Text>
          </View>
        )}
      </View>
      <View style={styles.cardAction}>
        {loading ? <ActivityIndicator color={C.ACCENT} /> : (
          <Ionicons name={ready ? 'refresh' : 'download'} size={22} color={C.ACCENT} />
        )}
      </View>
    </TouchableOpacity>
  );
}

const PURPLE = '#5B5BE8';
const PURPLE_DARK = '#3D3DC7';

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: C.DARK },
  scroll: { padding: SP.lg, paddingBottom: 140 },

  // Client header block
  clientBlock: {
    backgroundColor: C.CARD,
    borderRadius: R.lg,
    padding: SP.lg,
    borderLeftWidth: 4,
    borderLeftColor: C.ACCENT,
    marginBottom: SP.lg,
  },
  clientLabel: { ...FONT.label, color: C.ACCENT, fontSize: 11, marginBottom: 4 },
  clientName: { ...FONT.h1, fontSize: 22, letterSpacing: 0.5 },
  clientAddress: { ...FONT.small, marginTop: 4 },

  section: { ...FONT.label, color: C.GRAY3, marginBottom: SP.md },

  // File cards
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: C.CARD,
    borderRadius: R.lg,
    padding: SP.lg,
    borderWidth: 1,
    borderColor: C.BORDER,
    marginBottom: SP.md,
  },
  cardReady: { borderColor: C.ACCENT, backgroundColor: 'rgba(140, 198, 63, 0.06)' },
  cardIcon: {
    width: 56, height: 56, borderRadius: R.md,
    alignItems: 'center', justifyContent: 'center',
    borderWidth: 1,
  },
  cardTitle: { ...FONT.h3, fontSize: 16 },
  cardSubtitle: { ...FONT.small, marginTop: 4, lineHeight: 18 },
  cardStatus: { flexDirection: 'row', alignItems: 'center', gap: 4, marginTop: SP.sm },
  cardStatusTxt: { ...FONT.label, color: C.ACCENT, fontSize: 10 },
  cardAction: { width: 32, alignItems: 'flex-end' },

  // Génère les deux
  generateAll: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: SP.sm,
    paddingVertical: 14, marginTop: SP.sm,
    backgroundColor: 'transparent',
    borderRadius: R.md, borderWidth: 1, borderColor: C.ACCENT, borderStyle: 'dashed' as any,
  },
  generateAllTxt: { ...FONT.button, color: C.ACCENT, fontSize: 12 },

  webNote: { ...FONT.small, marginTop: SP.lg, textAlign: 'center' },

  // Sticky share bar
  bottomBar: {
    position: 'absolute', bottom: 0, left: 0, right: 0,
    padding: SP.lg,
    backgroundColor: C.DARK,
    borderTopWidth: 1, borderTopColor: C.BORDER,
  },
  shareBtn: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: SP.md,
    backgroundColor: PURPLE,
    borderRadius: R.lg, paddingVertical: 18,
    borderWidth: 1, borderColor: PURPLE_DARK,
    shadowColor: PURPLE, shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.4, shadowRadius: 8, elevation: 6,
  },
  shareBtnIdle: { backgroundColor: PURPLE_DARK, opacity: 0.9 },
  shareTxt: { ...FONT.button, color: C.WHITE, fontSize: 15, letterSpacing: 1.5 },
});
