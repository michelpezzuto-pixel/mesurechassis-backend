/**
 * RESULT.tsx — Centre de pilotage interactif de l'escalier.
 * Affiché APRÈS la validation des mesures du wizard.
 *
 * Fonctionnalités :
 *  - Toggle [Profil] [Plan] pour basculer entre vues 2D
 *  - Sélecteur de forme (Droit / Quart bas / Quart haut / Double quart)
 *  - Sliders / inputs : Largeur volée, Jour escalier
 *  - KPIs temps réel : N marches, h, g, pente
 *  - Alerte Blondel hors-norme
 *  - Sticky bottom : MODIFIER LES MESURES | VALIDER LA CONCEPTION
 *
 * Le moteur math n'est pas dupliqué : on appelle /measurement/preview à chaque ajustement.
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity, ScrollView, TextInput,
  ActivityIndicator, Alert, KeyboardAvoidingView, Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { Projects, Measurements } from '@/src/api';
import StairSketch from '@/src/StairSketch';
import PlanSketch, { ShapeKey } from '@/src/PlanSketch';
import { C, SP, R, FONT } from '@/src/theme';

type View2D = 'profile' | 'plan';

const SHAPE_OPTIONS: { key: ShapeKey; label: string; icon: any }[] = [
  { key: 'droit', label: 'DROIT', icon: 'arrow-up-bold' },
  { key: 'quart_bas', label: 'QUART BAS', icon: 'rotate-3d-variant' },
  { key: 'quart_haut', label: 'QUART HAUT', icon: 'rotate-3d' },
  { key: 'double_quart', label: 'DOUBLE QUART', icon: 'rotate-orbit' },
];

export default function ResultScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const [project, setProject] = useState<any>(null);
  const [meas, setMeas] = useState<any>(null);   // raw measurement input doc
  const [result, setResult] = useState<any>(null); // computed result
  const [view, setView] = useState<View2D>('profile');
  const [shape, setShape] = useState<ShapeKey>('droit');
  const [largeurVolee, setLargeurVolee] = useState('900');
  const [jourEscalier, setJourEscalier] = useState('100');
  const [loading, setLoading] = useState(true);
  const [previewing, setPreviewing] = useState(false);
  const [validating, setValidating] = useState(false);
  const debounceRef = useRef<any>(null);

  // Load project + existing measurement on mount
  useEffect(() => {
    if (!id) return;
    Projects.get(id).then(p => {
      setProject(p);
      const m = p.measurement;
      if (m) {
        setMeas(m);
        setResult(m.result);
        setShape((m.result?.shape_key as ShapeKey) || (m.forme_choisie as ShapeKey) || 'droit');
        setLargeurVolee(String(m.largeur_volee ?? m.result?.largeur_volee ?? 900));
        setJourEscalier(String(m.jour_escalier ?? m.result?.jour_escalier ?? 100));
      }
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [id]);

  // Live preview when shape/width/jour change
  const triggerPreview = useCallback(() => {
    if (!meas || !id) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      setPreviewing(true);
      try {
        const payload = {
          ...meas,
          forme_choisie: shape,
          largeur_volee: Math.max(700, parseInt(largeurVolee, 10) || 900),
          jour_escalier: Math.max(50, parseInt(jourEscalier, 10) || 100),
        };
        const r = await Measurements.preview(id, payload);
        setResult(r);
        // sauvegarde silencieuse de la nouvelle config
        await Measurements.save(id, payload).catch(() => {});
        setMeas(payload);
      } catch (e) {
        // silent fail — keep last result
      } finally { setPreviewing(false); }
    }, 350);
  }, [meas, id, shape, largeurVolee, jourEscalier]);

  useEffect(() => {
    if (!loading && meas) triggerPreview();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shape, largeurVolee, jourEscalier]);

  const validate = async () => {
    if (!id) return;
    setValidating(true);
    try {
      await Measurements.validate(id);
      router.replace(`/projects/${id}/export` as any);
    } catch (e: any) {
      Alert.alert('Erreur', e?.response?.data?.detail || 'Validation échouée');
    } finally { setValidating(false); }
  };

  // Blondel ergonomic check (target 600-640)
  const ergoOk = useMemo(() => {
    if (!result) return true;
    const b = result.blondel_value;
    return b >= 600 && b <= 640;
  }, [result]);

  if (loading) {
    return (
      <SafeAreaView style={[styles.safe, { justifyContent: 'center', alignItems: 'center' }]}>
        <ActivityIndicator color={C.ACCENT} size="large" />
      </SafeAreaView>
    );
  }

  if (!result || !meas) {
    return (
      <SafeAreaView style={styles.safe} edges={['top']}>
        <View style={styles.topbar}>
          <TouchableOpacity onPress={() => router.back()}><Ionicons name="arrow-back" size={24} color={C.WHITE} /></TouchableOpacity>
          <Text style={styles.title}>CONCEPTION</Text>
          <View style={{ width: 24 }} />
        </View>
        <View style={styles.empty}>
          <MaterialCommunityIcons name="ruler" size={56} color={C.GRAY3} />
          <Text style={styles.emptyTitle}>Pas encore de mesures</Text>
          <Text style={styles.emptyHint}>Lancez d'abord le wizard de prise de cotes.</Text>
          <TouchableOpacity style={styles.startBtn} onPress={() => router.replace(`/projects/${id}/measure` as any)}>
            <Text style={styles.startTxt}>PRENDRE LES COTES</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1 }}>
        <View style={styles.topbar}>
          <TouchableOpacity onPress={() => router.back()} testID="back-btn" hitSlop={10}>
            <Ionicons name="arrow-back" size={24} color={C.WHITE} />
          </TouchableOpacity>
          <View style={{ flex: 1, alignItems: 'center' }}>
            <Text style={styles.topbarLabel}>CONCEPTION</Text>
            <Text style={styles.topbarClient} numberOfLines={1}>
              {(project?.client_nom || 'CLIENT').toUpperCase()}
            </Text>
          </View>
          {previewing ? <ActivityIndicator color={C.ACCENT} /> : <View style={{ width: 24 }} />}
        </View>

        <ScrollView contentContainerStyle={{ padding: SP.lg, paddingBottom: 140 }} keyboardShouldPersistTaps="handled">
          {/* Element title */}
          {!!meas.element_title && (
            <View style={styles.elemBadge}>
              <MaterialCommunityIcons name="stairs" size={14} color={C.ACCENT} />
              <Text style={styles.elemTxt}>{meas.element_title}</Text>
            </View>
          )}

          {/* Toggle Profil / Plan */}
          <View style={styles.toggleWrap}>
            <TouchableOpacity
              style={[styles.toggleBtn, view === 'profile' && styles.toggleBtnActive]}
              onPress={() => setView('profile')}
              testID="toggle-profile"
            >
              <MaterialCommunityIcons name="stairs" size={16} color={view === 'profile' ? C.DARK : C.WHITE} />
              <Text style={[styles.toggleTxt, view === 'profile' && styles.toggleTxtActive]}>VUE DE PROFIL</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.toggleBtn, view === 'plan' && styles.toggleBtnActive]}
              onPress={() => setView('plan')}
              testID="toggle-plan"
            >
              <MaterialCommunityIcons name="map" size={16} color={view === 'plan' ? C.DARK : C.WHITE} />
              <Text style={[styles.toggleTxt, view === 'plan' && styles.toggleTxtActive]}>VUE EN PLAN</Text>
            </TouchableOpacity>
          </View>

          {/* SVG */}
          <View style={styles.svgWrap}>
            {view === 'profile' ? (
              <StairSketch
                n={result.n_steps}
                h={result.h}
                g={result.g}
                trueHeight={result.true_height}
                reculement={result.reculement_needed}
                limonLength={result.limon_length}
                tremieL={meas.tremie_longueur}
                tremieW={meas.tremie_largeur}
              />
            ) : (
              <PlanSketch
                shapeKey={shape}
                n={result.n_steps}
                reculement={result.reculement_needed}
                largeurVolee={result.largeur_volee || parseInt(largeurVolee, 10) || 900}
                jourEscalier={result.jour_escalier || parseInt(jourEscalier, 10) || 100}
              />
            )}
          </View>

          {/* Ergonomic alert */}
          {!ergoOk && (
            <View style={styles.alert}>
              <Ionicons name="warning" size={20} color={C.WARN} />
              <View style={{ flex: 1, marginLeft: SP.sm }}>
                <Text style={styles.alertTitle}>Erreur d'ergonomie</Text>
                <Text style={styles.alertTxt}>
                  Loi de Blondel : 2h+g = {Math.round(result.blondel_value)} mm
                  (cible 600–640). Ajustez la forme ou le reculement pour optimiser.
                </Text>
              </View>
            </View>
          )}

          {/* KPI cards */}
          <View style={styles.kpiRow}>
            <Kpi label="MARCHES" value={result.n_steps} />
            <Kpi label="HAUTEUR h" value={`${Math.round(result.h)}`} unit="mm" />
            <Kpi label="GIRON g" value={`${Math.round(result.g)}`} unit="mm" />
            <Kpi label="PENTE" value={`${Math.round(result.slope_angle)}`} unit="°" />
          </View>

          {/* Trajectoire */}
          <Text style={styles.section}>TRAJECTOIRE</Text>
          <View style={styles.shapeGrid}>
            {SHAPE_OPTIONS.map((opt) => (
              <TouchableOpacity
                key={opt.key}
                style={[styles.shapeBtn, shape === opt.key && styles.shapeBtnActive]}
                onPress={() => setShape(opt.key)}
                testID={`shape-${opt.key}`}
              >
                <MaterialCommunityIcons name={opt.icon} size={22} color={shape === opt.key ? C.DARK : C.ACCENT} />
                <Text style={[styles.shapeTxt, shape === opt.key && styles.shapeTxtActive]}>{opt.label}</Text>
              </TouchableOpacity>
            ))}
          </View>

          {/* Largeur volée + Jour */}
          <View style={styles.row}>
            <View style={{ flex: 1 }}>
              <Text style={styles.label}>LARGEUR DE VOLÉE</Text>
              <TextInput
                value={largeurVolee}
                onChangeText={setLargeurVolee}
                keyboardType="numeric"
                style={styles.input}
                testID="input-largeur-volee"
              />
              <Text style={styles.hintSm}>en mm — défaut 900</Text>
            </View>
            {shape !== 'droit' && (
              <View style={{ flex: 1, marginLeft: SP.md }}>
                <Text style={styles.label}>JOUR D'ESCALIER</Text>
                <TextInput
                  value={jourEscalier}
                  onChangeText={setJourEscalier}
                  keyboardType="numeric"
                  style={styles.input}
                  testID="input-jour"
                />
                <Text style={styles.hintSm}>espace entre 2 volées</Text>
              </View>
            )}
          </View>

          {/* Détails */}
          <View style={styles.detailCard}>
            <DetailRow label="Forme calculée" value={result.shape} />
            <DetailRow label="Reculement requis" value={`${Math.round(result.reculement_needed)} mm`} />
            <DetailRow label="Longueur du LIMON" value={`${Math.round(result.limon_length)} mm`} accent />
            {result.echappee != null && (
              <DetailRow
                label="Échappée"
                value={`${Math.round(result.echappee)} mm`}
                danger={!!result.echappee_critique}
              />
            )}
            <DetailRow label="Blondel (2h+g)" value={`${Math.round(result.blondel_value)} mm`} danger={!result.valid_blondel} />
          </View>
        </ScrollView>

        {/* Sticky bottom actions */}
        <View style={styles.bottomBar}>
          <TouchableOpacity style={[styles.btn, styles.btnGhost]} onPress={() => router.replace(`/projects/${id}/measure` as any)} testID="btn-modify">
            <Ionicons name="create-outline" size={18} color={C.WHITE} />
            <Text style={[styles.btnTxt, { color: C.WHITE }]}>MODIFIER LES MESURES</Text>
          </TouchableOpacity>
          <TouchableOpacity style={[styles.btn, styles.btnPrimary, validating && { opacity: 0.6 }]} onPress={validate} disabled={validating} testID="btn-validate">
            {validating ? <ActivityIndicator color={C.DARK} /> : (
              <>
                <Ionicons name="checkmark-circle" size={18} color={C.DARK} />
                <Text style={styles.btnTxt}>VALIDER LA CONCEPTION</Text>
              </>
            )}
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function Kpi({ label, value, unit }: { label: string; value: any; unit?: string }) {
  return (
    <View style={styles.kpi}>
      <Text style={styles.kpiLabel}>{label}</Text>
      <View style={{ flexDirection: 'row', alignItems: 'baseline', gap: 3 }}>
        <Text style={styles.kpiVal}>{value}</Text>
        {!!unit && <Text style={styles.kpiUnit}>{unit}</Text>}
      </View>
    </View>
  );
}

function DetailRow({ label, value, accent, danger }: { label: string; value: string; accent?: boolean; danger?: boolean }) {
  return (
    <View style={styles.detailRow}>
      <Text style={styles.detailLabel}>{label}</Text>
      <Text style={[styles.detailVal, accent && { color: C.ACCENT, fontWeight: '800' as any }, danger && { color: C.DANGER }]}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: C.DARK },
  topbar: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', padding: SP.lg, borderBottomWidth: 1, borderBottomColor: C.BORDER, gap: SP.md },
  topbarLabel: { ...FONT.label, color: C.GRAY3, fontSize: 10 },
  topbarClient: { ...FONT.h3, fontSize: 14, letterSpacing: 0.5 },
  title: { ...FONT.h2, fontSize: 18, flex: 1, textAlign: 'center' },

  empty: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: SP.xl },
  emptyTitle: { ...FONT.h3, marginTop: SP.md },
  emptyHint: { ...FONT.small, textAlign: 'center', marginTop: SP.sm, marginBottom: SP.xl },
  startBtn: { backgroundColor: C.ACCENT, paddingHorizontal: SP.lg, paddingVertical: 14, borderRadius: R.md },
  startTxt: { ...FONT.button, color: C.DARK, fontSize: 13 },

  elemBadge: { alignSelf: 'flex-start', flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: C.ACCENT_BG, paddingHorizontal: SP.md, paddingVertical: 4, borderRadius: R.pill, borderWidth: 1, borderColor: C.ACCENT, marginBottom: SP.md },
  elemTxt: { ...FONT.label, color: C.ACCENT, fontSize: 11 },

  toggleWrap: { flexDirection: 'row', backgroundColor: C.CARD, borderRadius: R.md, padding: 4, marginBottom: SP.md, borderWidth: 1, borderColor: C.BORDER },
  toggleBtn: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, paddingVertical: 10, borderRadius: R.sm },
  toggleBtnActive: { backgroundColor: C.ACCENT },
  toggleTxt: { ...FONT.button, color: C.WHITE, fontSize: 11 },
  toggleTxtActive: { color: C.DARK },

  svgWrap: { backgroundColor: C.CARD, borderRadius: R.lg, padding: SP.md, borderWidth: 1, borderColor: C.BORDER, alignItems: 'center', marginBottom: SP.md },

  alert: { flexDirection: 'row', backgroundColor: 'rgba(245, 158, 11, 0.12)', borderColor: C.WARN, borderWidth: 1, borderLeftWidth: 4, borderRadius: R.md, padding: SP.md, marginBottom: SP.md },
  alertTitle: { ...FONT.label, color: C.WARN, fontSize: 11, marginBottom: 2 },
  alertTxt: { ...FONT.small, color: C.WHITE, fontSize: 12, lineHeight: 17 },

  kpiRow: { flexDirection: 'row', gap: SP.sm, marginBottom: SP.lg },
  kpi: { flex: 1, backgroundColor: C.CARD, borderRadius: R.md, padding: SP.sm, alignItems: 'center', borderWidth: 1, borderColor: C.ACCENT, borderLeftWidth: 3 },
  kpiLabel: { ...FONT.label, fontSize: 9, color: C.GRAY3 },
  kpiVal: { ...FONT.h2, color: C.ACCENT, fontSize: 20 },
  kpiUnit: { ...FONT.small, color: C.GRAY3, fontSize: 10 },

  section: { ...FONT.label, color: C.ACCENT, marginBottom: SP.md, marginTop: SP.sm },

  shapeGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: SP.sm, marginBottom: SP.lg },
  shapeBtn: { flex: 1, minWidth: '47%' as any, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, paddingVertical: 12, paddingHorizontal: SP.md, borderRadius: R.md, borderWidth: 1, borderColor: C.BORDER, backgroundColor: C.CARD },
  shapeBtnActive: { backgroundColor: C.ACCENT, borderColor: C.ACCENT },
  shapeTxt: { ...FONT.button, color: C.WHITE, fontSize: 11 },
  shapeTxtActive: { color: C.DARK },

  row: { flexDirection: 'row', marginBottom: SP.md },
  label: { ...FONT.label, marginBottom: SP.sm, fontSize: 11 },
  input: { backgroundColor: C.BG_DEEPER, borderWidth: 1, borderColor: C.BORDER, borderRadius: R.md, padding: SP.md, color: C.WHITE, fontSize: 16 },
  hintSm: { ...FONT.small, fontSize: 10, marginTop: 4 },

  detailCard: { backgroundColor: C.CARD, borderRadius: R.lg, padding: SP.md, borderWidth: 1, borderColor: C.BORDER, marginTop: SP.md },
  detailRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: SP.sm, borderBottomWidth: 1, borderBottomColor: C.BORDER + '55' },
  detailLabel: { ...FONT.small, color: C.GRAY2, fontSize: 12 },
  detailVal: { ...FONT.body, fontSize: 13, fontWeight: '600' as any },

  bottomBar: { position: 'absolute', bottom: 0, left: 0, right: 0, padding: SP.md, gap: SP.sm, backgroundColor: C.DARK, borderTopWidth: 1, borderTopColor: C.BORDER, flexDirection: 'row' },
  btn: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: SP.sm, paddingVertical: 14, borderRadius: R.md, borderWidth: 1 },
  btnGhost: { backgroundColor: C.CARD, borderColor: C.BORDER },
  btnPrimary: { backgroundColor: C.ACCENT, borderColor: C.ACCENT },
  btnTxt: { ...FONT.button, color: C.DARK, fontSize: 12 },
});
