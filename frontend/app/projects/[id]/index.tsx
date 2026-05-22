import React, { useEffect, useState, useCallback } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Alert, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, useRouter, useFocusEffect } from 'expo-router';
import { Ionicons, MaterialCommunityIcons, Feather } from '@expo/vector-icons';
import { Projects } from '@/src/api';
import { useAuth } from '@/src/auth';
import { C, SP, R, FONT, STATUS_LABELS, STATUS_COLOR } from '@/src/theme';
import StairSketch from '@/src/StairSketch';

export default function ProjectDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const { user } = useAuth();
  const [project, setProject] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!id) return;
    try {
      const p = await Projects.get(id);
      setProject(p);
    } catch (e: any) {
      Alert.alert('Erreur', e?.response?.data?.detail || 'Introuvable');
      router.back();
    } finally { setLoading(false); }
  }, [id, router]);

  useFocusEffect(useCallback(() => { setLoading(true); load(); }, [load]));

  const transmit = async () => {
    Alert.alert(
      'Transmettre au technicien',
      'Le chantier sera verrouillé. Vous ne pourrez plus modifier les informations.',
      [
        { text: 'Annuler', style: 'cancel' },
        {
          text: 'Confirmer', style: 'destructive', onPress: async () => {
            try { await Projects.transmit(id!); load(); } catch (e: any) { Alert.alert('Erreur', e?.response?.data?.detail || 'Erreur'); }
          },
        },
      ]
    );
  };

  const remove = async () => {
    Alert.alert('Supprimer ?', 'Action irréversible.', [
      { text: 'Annuler', style: 'cancel' },
      {
        text: 'Supprimer', style: 'destructive', onPress: async () => {
          try { await Projects.remove(id!); router.replace('/dashboard'); }
          catch (e: any) { Alert.alert('Erreur', e?.response?.data?.detail || 'Erreur'); }
        },
      },
    ]);
  };

  if (loading || !project) {
    return <SafeAreaView style={styles.safe}><View style={styles.center}><ActivityIndicator color={C.ACCENT} size="large" /></View></SafeAreaView>;
  }

  const m = project.measurement;
  const isSolo = !!user?.solo_mode;
  const canTransmit = !project.locked && user?.role === 'admin' && !isSolo;
  const canEditClient = user?.role === 'admin' && !project.locked;
  const canMeasure = (user?.role === 'technicien' && project.locked) || (user?.role === 'admin' && isSolo);
  const canDelete = user?.role === 'admin';
  const canValidate = (user?.role === 'technicien' || (user?.role === 'admin' && isSolo)) && m && !m.validated;
  const canExport = m;

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <View style={styles.topbar}>
        <TouchableOpacity onPress={() => router.back()} testID="back-btn" hitSlop={10}>
          <Ionicons name="arrow-back" size={24} color={C.WHITE} />
        </TouchableOpacity>
        <Text style={styles.topbarTitle}>CHANTIER</Text>
        {canDelete ? (
          <TouchableOpacity onPress={remove} testID="delete-project" hitSlop={10}>
            <Feather name="trash-2" size={22} color={C.DANGER} />
          </TouchableOpacity>
        ) : <View style={{ width: 22 }} />}
      </View>

      <ScrollView contentContainerStyle={{ padding: SP.lg, paddingBottom: 100 }}>
        {/* Header chantier : NOM CLIENT en évidence */}
        <View style={styles.heroClient}>
          <Text style={styles.heroLabel}>CLIENT</Text>
          <Text style={styles.heroName} numberOfLines={2}>
            {(`${project.client_nom} ${project.client_prenom || ''}`).trim().toUpperCase()}
          </Text>
          {!!project.address && (
            <View style={styles.heroAddr}>
              <Ionicons name="location-sharp" size={14} color={C.GRAY3} />
              <Text style={styles.heroAddrTxt} numberOfLines={1}>
                {project.address}{project.city ? `, ${project.city}` : ''}
              </Text>
            </View>
          )}
          <View style={[styles.badge, styles.heroBadge, { backgroundColor: STATUS_COLOR[project.status] + '22', borderColor: STATUS_COLOR[project.status] }]}>
            <Text style={[styles.badgeTxt, { color: STATUS_COLOR[project.status] }]}>
              {STATUS_LABELS[project.status]}
            </Text>
            {project.locked && <Ionicons name="lock-closed" size={11} color={STATUS_COLOR[project.status]} style={{ marginLeft: 6 }} />}
          </View>
        </View>

        <View style={styles.card}>
          <Text style={styles.cardHead}>COORDONNÉES</Text>
          <Row icon="call" label="Téléphone" value={project.phone || '—'} />
          <Row icon="document-text" label="Notes" value={project.notes || '—'} />
          {project.postal_code && <Row icon="map" label="Code postal" value={project.postal_code} />}
        </View>

        {m ? (
          <View style={styles.card}>
            <View style={styles.measHead}>
              <Text style={styles.cardHead}>MESURES & CALCULS</Text>
              {!!m.element_title && (
                <View style={styles.elemTitleBadge}>
                  <MaterialCommunityIcons name="stairs" size={12} color={C.ACCENT} />
                  <Text style={styles.elemTitleTxt} numberOfLines={1}>{m.element_title}</Text>
                </View>
              )}
            </View>
            <View style={{ alignItems: 'center', marginBottom: SP.md }}>
              <StairSketch
                trueHeight={m.result.true_height}
                reculement={m.result.reculement_needed}
                n={m.result.n_steps}
                h={m.result.h}
                g={m.result.g}
                tremieL={m.tremie_longueur}
                tremieW={m.tremie_largeur}
                limonLength={m.result.limon_length}
              />
            </View>
            <Text style={[styles.shape, { color: m.result.shape.includes('Droit') ? C.ACCENT : C.WARN }]}>
              {m.result.shape}
            </Text>
            {m.result.echappee_critique && (
              <View style={styles.alertCritical} testID="alert-echappee-critique">
                <Ionicons name="warning" size={20} color={C.DANGER} />
                <Text style={styles.alertCriticalTxt}>
                  ⚠️ Échappée critique ({Math.round(m.result.echappee)} mm &lt; 2000 mm) : Risque de choc à la tête
                </Text>
              </View>
            )}
            <View style={styles.kpiRow}>
              <Kpi label="Marches" value={`${m.result.n_steps}`} />
              <Kpi label="h" value={`${Math.round(m.result.h)} mm`} />
              <Kpi label={m.result.is_tournant ? 'g (foulée)' : 'g'} value={`${Math.round(m.result.g)} mm`} />
            </View>
            <View style={styles.kpiRow}>
              <Kpi label="Pente" value={`${m.result.slope_angle}°`} />
              <Kpi label="2h+g" value={`${Math.round(m.result.blondel_value)}`} ok={m.result.valid_blondel} />
              {m.result.echappee !== null && m.result.echappee !== undefined ? (
                <Kpi label="Échappée" value={`${Math.round(m.result.echappee)}`} ok={!m.result.echappee_critique} />
              ) : (
                <Kpi label="—" value="—" />
              )}
            </View>

            {/* Limon — atelier dimension */}
            <View style={styles.limonCard} testID="kpi-limon">
              <MaterialCommunityIcons name="ruler" size={24} color={C.ACCENT} />
              <View style={{ flex: 1, marginLeft: SP.md }}>
                <Text style={styles.limonLabel}>LONGUEUR DU LIMON</Text>
                <Text style={styles.limonHint}>Dimension exacte pour l'atelier (découpe poutre)</Text>
              </View>
              <Text style={styles.limonValue}>{Math.round(m.result.limon_length || m.result.hypotenuse)} mm</Text>
            </View>

            {m.result.ligne_foulee_note && (
              <View style={styles.fouleeNote}>
                <MaterialCommunityIcons name="rotate-3d-variant" size={18} color={C.ACCENT} />
                <Text style={styles.fouleeNoteTxt}>{m.result.ligne_foulee_note}</Text>
              </View>
            )}
            {m.result.notes && m.result.notes.length > 0 && (
              <View style={{ marginTop: SP.md }}>
                {m.result.notes.map((n: string, i: number) => (
                  <Text key={i} style={styles.noteTxt}>• {n}</Text>
                ))}
              </View>
            )}
            {m.validated && (
              <View style={styles.validatedBadge}>
                <Ionicons name="checkmark-circle" size={18} color={C.ACCENT} />
                <Text style={[styles.badgeTxt, { color: C.ACCENT, marginLeft: 6 }]}>CONCEPTION VALIDÉE</Text>
              </View>
            )}
          </View>
        ) : (
          <View style={styles.card}>
            <Text style={styles.cardHead}>MESURES TERRAIN</Text>
            <Text style={styles.empty}>Aucune mesure prise. {canMeasure ? 'Démarrez la prise de mesures.' : 'En attente de transmission au technicien.'}</Text>
          </View>
        )}

        {canEditClient && (
          <TouchableOpacity style={styles.btn} onPress={transmit} testID="btn-transmit">
            <MaterialCommunityIcons name="send" size={20} color={C.DARK} />
            <Text style={styles.btnTxt}>TRANSMETTRE AU TECHNICIEN</Text>
          </TouchableOpacity>
        )}

        {canMeasure && (
          <TouchableOpacity style={[styles.btn, m ? styles.btnSecondary : null]} onPress={() => router.push(`/projects/${id}/measure`)} testID="btn-measure">
            <MaterialCommunityIcons name="ruler-square" size={20} color={m ? C.WHITE : C.DARK} />
            <Text style={[styles.btnTxt, m && { color: C.WHITE }]}>{m ? 'MODIFIER MESURES' : 'PRENDRE LES MESURES'}</Text>
          </TouchableOpacity>
        )}

        {canValidate && (
          <TouchableOpacity style={[styles.btn, { backgroundColor: C.INFO }]} onPress={async () => {
            try { await (await import('@/src/api')).Measurements.validate(id!); load(); }
            catch (e: any) { Alert.alert('Erreur', e?.response?.data?.detail || 'Erreur'); }
          }} testID="btn-validate">
            <Ionicons name="checkmark-circle" size={20} color={C.WHITE} />
            <Text style={[styles.btnTxt, { color: C.WHITE }]}>VALIDER LA CONCEPTION</Text>
          </TouchableOpacity>
        )}

        {canExport && (
          <TouchableOpacity style={[styles.btn, styles.btnSecondary]} onPress={() => router.push(`/projects/${id}/export`)} testID="btn-goto-export">
            <Ionicons name="share-outline" size={20} color={C.WHITE} />
            <Text style={[styles.btnTxt, { color: C.WHITE }]}>EXPORTER PDF / DXF</Text>
          </TouchableOpacity>
        )}

        <TouchableOpacity
          style={[styles.btn, styles.btnSecondary]}
          onPress={() => router.push(`/projects/${id}/photos`)}
          testID="btn-goto-photos"
        >
          <Ionicons name="camera" size={20} color={C.WHITE} />
          <Text style={[styles.btnTxt, { color: C.WHITE }]}>PHOTOS DE CHANTIER</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

function Row({ icon, label, value }: any) {
  return (
    <View style={styles.row}>
      <Ionicons name={icon} size={16} color={C.ACCENT} style={{ marginTop: 2 }} />
      <View style={{ flex: 1, marginLeft: SP.md }}>
        <Text style={styles.rowLabel}>{label}</Text>
        <Text style={styles.rowValue}>{value}</Text>
      </View>
    </View>
  );
}

function Kpi({ label, value, ok }: { label: string; value: string; ok?: boolean }) {
  return (
    <View style={styles.kpi}>
      <Text style={styles.kpiLabel}>{label}</Text>
      <Text style={[styles.kpiValue, ok === false && { color: C.DANGER }]}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: C.DARK },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  topbar: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', padding: SP.lg, gap: SP.md, borderBottomWidth: 1, borderBottomColor: C.BORDER },
  title: { ...FONT.h3, flex: 1, textAlign: 'center' },
  topbarTitle: { ...FONT.label, color: C.GRAY3, flex: 1, textAlign: 'center', fontSize: 12 },
  // Hero client
  heroClient: {
    backgroundColor: C.CARD,
    borderRadius: R.lg,
    padding: SP.lg,
    borderLeftWidth: 4,
    borderLeftColor: C.ACCENT,
    marginBottom: SP.md,
  },
  heroLabel: { ...FONT.label, color: C.ACCENT, fontSize: 11, marginBottom: 4 },
  heroName: { ...FONT.h1, fontSize: 24, letterSpacing: 0.5, lineHeight: 30 },
  heroAddr: { flexDirection: 'row', alignItems: 'center', gap: 4, marginTop: SP.sm },
  heroAddrTxt: { ...FONT.small, flex: 1 },
  heroBadge: { marginTop: SP.md, marginBottom: 0 },
  badge: { alignSelf: 'flex-start', flexDirection: 'row', alignItems: 'center', paddingHorizontal: SP.md, paddingVertical: 6, borderRadius: R.pill, borderWidth: 1, marginBottom: SP.md },
  badgeTxt: { ...FONT.label, fontSize: 11 },
  card: { backgroundColor: C.CARD, borderRadius: R.lg, padding: SP.lg, borderWidth: 1, borderColor: C.BORDER, marginBottom: SP.md },
  cardHead: { ...FONT.label, color: C.ACCENT, marginBottom: SP.md },
  measHead: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: SP.sm, marginBottom: 4 },
  elemTitleBadge: { flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: C.ACCENT_BG, paddingHorizontal: SP.sm, paddingVertical: 4, borderRadius: R.pill, marginBottom: SP.md, borderWidth: 1, borderColor: C.ACCENT },
  elemTitleTxt: { ...FONT.label, color: C.ACCENT, fontSize: 10, maxWidth: 180 },
  row: { flexDirection: 'row', marginBottom: SP.sm },
  rowLabel: { ...FONT.small },
  rowValue: { ...FONT.body, marginTop: 2 },
  shape: { ...FONT.h3, textAlign: 'center', marginBottom: SP.md },
  kpiRow: { flexDirection: 'row', gap: SP.sm, marginBottom: SP.sm },
  kpi: { flex: 1, backgroundColor: C.BG_DEEPER, padding: SP.md, borderRadius: R.md, alignItems: 'center', borderWidth: 1, borderColor: C.BORDER },
  kpiLabel: { ...FONT.small, fontSize: 11 },
  kpiValue: { ...FONT.h3, marginTop: 4, color: C.ACCENT },
  noteTxt: { ...FONT.small, color: C.WARN, marginBottom: 2 },
  alertCritical: { flexDirection: 'row', alignItems: 'center', gap: SP.sm, padding: SP.md, backgroundColor: C.DANGER_BG, borderRadius: R.md, borderLeftWidth: 3, borderLeftColor: C.DANGER, marginBottom: SP.md },
  alertCriticalTxt: { ...FONT.body, color: C.DANGER, flex: 1, fontWeight: '700', fontSize: 13 },
  limonCard: { flexDirection: 'row', alignItems: 'center', padding: SP.md, backgroundColor: C.ACCENT_BG, borderRadius: R.md, borderLeftWidth: 3, borderLeftColor: C.ACCENT, marginTop: SP.md },
  limonLabel: { ...FONT.label, color: C.ACCENT, fontSize: 11 },
  limonHint: { ...FONT.small, fontSize: 11, marginTop: 2 },
  limonValue: { ...FONT.h2, fontSize: 22, color: C.ACCENT },
  fouleeNote: { flexDirection: 'row', alignItems: 'flex-start', gap: SP.sm, padding: SP.md, backgroundColor: C.BG_DEEPER, borderRadius: R.md, marginTop: SP.md, borderWidth: 1, borderColor: C.BORDER },
  fouleeNoteTxt: { ...FONT.small, color: C.GRAY1, flex: 1, lineHeight: 18 },
  validatedBadge: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', backgroundColor: C.ACCENT_BG, borderRadius: R.md, padding: SP.md, marginTop: SP.md },
  empty: { ...FONT.small },
  btn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: SP.sm, backgroundColor: C.ACCENT, borderRadius: R.md, paddingVertical: 16, marginTop: SP.md },
  btnSecondary: { backgroundColor: C.CARD, borderWidth: 1, borderColor: C.BORDER },
  btnTxt: { ...FONT.button, color: C.DARK, fontSize: 13 },
});
