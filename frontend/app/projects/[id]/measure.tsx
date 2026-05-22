import React, { useState, useEffect } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet, ScrollView,
  KeyboardAvoidingView, Platform, Alert, ActivityIndicator, Switch,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons, MaterialCommunityIcons, Feather } from '@expo/vector-icons';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Audio } from 'expo-av';
import { Measurements, Projects, Voice } from '@/src/api';
import { C, SP, R, FONT } from '@/src/theme';
import StairSketch from '@/src/StairSketch';

type Material = 'acier' | 'bois' | 'beton';
const MATERIALS: { key: Material; label: string; icon: any; iconLib: 'mci' | 'ion' }[] = [
  { key: 'acier', label: 'Acier', icon: 'tools', iconLib: 'mci' },
  { key: 'bois', label: 'Bois', icon: 'pine-tree', iconLib: 'mci' },
  { key: 'beton', label: 'Béton', icon: 'wall', iconLib: 'mci' },
];

export default function MeasureWizard() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [project, setProject] = useState<any>(null);

  // Step 1
  const [elementTitle, setElementTitle] = useState('Escalier Principal');
  const [material, setMaterial] = useState<Material | null>(null);
  // Tooltip "Recul au sol"
  const [showReculHelp, setShowReculHelp] = useState(false);
  // Step 2
  const [hauteur, setHauteur] = useState('');
  const [solsZero, setSolsZero] = useState(true);
  const [resBas, setResBas] = useState('');
  const [resHaut, setResHaut] = useState('');
  const [epDalle, setEpDalle] = useState('');
  const [tremieL, setTremieL] = useState('');
  const [tremieW, setTremieW] = useState('');
  const [recul, setRecul] = useState('');
  const [hauteurPlafondTremie, setHauteurPlafondTremie] = useState('');
  const [remarques, setRemarques] = useState('');

  // Step 3
  const [result, setResult] = useState<any>(null);
  const [saving, setSaving] = useState(false);
  const [recording, setRecording] = useState<Audio.Recording | null>(null);
  const [transcribing, setTranscribing] = useState(false);

  useEffect(() => {
    if (!id) return;
    Projects.get(id).then(p => {
      setProject(p);
      if (p.measurement) {
        const m = p.measurement;
        setElementTitle(m.element_title || 'Escalier Principal');
        setMaterial(m.material);
        setHauteur(String(m.hauteur_brute));
        setSolsZero(m.sols_finis_zero);
        setResBas(String(m.reserve_bas || ''));
        setResHaut(String(m.reserve_haut || ''));
        setEpDalle(String(m.epaisseur_dalle));
        setTremieL(String(m.tremie_longueur));
        setTremieW(String(m.tremie_largeur));
        setRecul(String(m.reculement_max));
        setHauteurPlafondTremie(m.hauteur_sous_plafond_tremie ? String(m.hauteur_sous_plafond_tremie) : '');
        setRemarques(m.remarques || '');
        setResult(m.result);
      }
    });
  }, [id]);

  const next = async () => {
    if (step === 1) {
      if (!material) { Alert.alert('Choix requis', 'Sélectionnez un matériau.'); return; }
      setStep(2);
    } else if (step === 2) {
      if (!hauteur || !epDalle || !tremieL || !tremieW || !recul || !remarques.trim()) {
        Alert.alert('Champs requis', 'Renseignez toutes les dimensions et les remarques.');
        return;
      }
      try {
        const payload = buildPayload();
        const res = await Measurements.preview(id!, payload);
        setResult(res);
        setStep(3);
      } catch (e: any) {
        Alert.alert('Erreur', e?.response?.data?.detail || 'Calcul impossible');
      }
    }
  };

  const buildPayload = () => ({
    element_title: elementTitle.trim() || 'Escalier',
    material: material!,
    hauteur_brute: Number(hauteur),
    sols_finis_zero: solsZero,
    reserve_bas: Number(resBas || 0),
    reserve_haut: Number(resHaut || 0),
    epaisseur_dalle: Number(epDalle),
    tremie_longueur: Number(tremieL),
    tremie_largeur: Number(tremieW),
    reculement_max: Number(recul),
    remarques: remarques.trim(),
    hauteur_sous_plafond_tremie: hauteurPlafondTremie ? Number(hauteurPlafondTremie) : null,
  });

  const saveAndValidate = async () => {
    setSaving(true);
    try {
      await Measurements.save(id!, buildPayload());
      Alert.alert('Mesures enregistrées', 'Vous pouvez désormais valider la conception et exporter.', [
        { text: 'OK', onPress: () => router.replace(`/projects/${id}`) },
      ]);
    } catch (e: any) {
      Alert.alert('Erreur', e?.response?.data?.detail || 'Sauvegarde impossible');
    } finally { setSaving(false); }
  };

  const startRec = async () => {
    try {
      const perm = await Audio.requestPermissionsAsync();
      if (!perm.granted) {
        Alert.alert('Permission refusée', 'Activez l\'accès microphone dans les réglages.');
        return;
      }
      await Audio.setAudioModeAsync({ allowsRecordingIOS: true, playsInSilentModeIOS: true });
      const { recording: rec } = await Audio.Recording.createAsync(Audio.RecordingOptionsPresets.HIGH_QUALITY);
      setRecording(rec);
    } catch (e: any) {
      Alert.alert('Erreur micro', String(e?.message || e));
    }
  };

  const stopRec = async () => {
    if (!recording) return;
    setTranscribing(true);
    try {
      await recording.stopAndUnloadAsync();
      const uri = recording.getURI();
      setRecording(null);
      if (!uri) throw new Error('Pas d\'enregistrement');
      const { text } = await Voice.transcribe(uri);
      setRemarques(prev => (prev ? prev + ' ' : '') + text);
    } catch (e: any) {
      Alert.alert('Erreur transcription', String(e?.message || e));
    } finally { setTranscribing(false); }
  };

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={{ flex: 1 }}>
        <View style={styles.topbar}>
          <TouchableOpacity onPress={() => router.back()} testID="back-btn"><Ionicons name="arrow-back" size={24} color={C.WHITE} /></TouchableOpacity>
          <Text style={styles.title}>NOUVELLE MESURE</Text>
          <View style={{ width: 24 }} />
        </View>

        {/* Stepper */}
        <View style={styles.stepperRow}>
          <View style={styles.dots}>
            {[1, 2, 3].map(n => (
              <View key={n} style={[styles.dot, step >= n && styles.dotActive]} testID={`stepper-step-${n}`}>
                <Text style={[styles.dotTxt, step >= n && { color: C.DARK }]}>{n}</Text>
              </View>
            ))}
          </View>
          <TouchableOpacity style={styles.problemBtn} onPress={() => Alert.alert('Signaler', 'Le commercial sera notifié du blocage.')}>
            <Ionicons name="warning" size={14} color={C.DANGER} />
            <Text style={styles.problemTxt}>Signaler un problème</Text>
          </TouchableOpacity>
        </View>

        <ScrollView contentContainerStyle={{ padding: SP.lg, paddingBottom: 100 }}>
          {step === 1 && (
            <>
              <Text style={styles.section}>TITRE DE L'ÉLÉMENT</Text>
              <Text style={styles.hint}>Permet d'identifier cette mesure quand un chantier en compte plusieurs.</Text>
              <TextInput
                style={styles.input}
                placeholder="ex. Escalier Principal, Escalier Cave..."
                placeholderTextColor={C.GRAY3}
                value={elementTitle}
                onChangeText={setElementTitle}
                maxLength={60}
                testID="input-element-title"
              />

              <Text style={styles.section}>MATÉRIAU</Text>
              <Text style={styles.hint}>Choisissez le matériau principal de l'escalier.</Text>
              <View style={styles.matGrid}>
                {MATERIALS.map(m => (
                  <TouchableOpacity
                    key={m.key}
                    style={[styles.matCard, material === m.key && styles.matCardActive]}
                    onPress={() => setMaterial(m.key)}
                    testID={`material-card-${m.key}`}
                  >
                    <MaterialCommunityIcons name={m.icon as any} size={36} color={material === m.key ? C.DARK : C.ACCENT} />
                    <Text style={[styles.matLabel, material === m.key && { color: C.DARK }]}>{m.label}</Text>
                  </TouchableOpacity>
                ))}
              </View>
            </>
          )}

          {step === 2 && (
            <>
              <Text style={styles.section}>DIMENSIONS DU VOLUME</Text>
              <Field label="Hauteur brute à franchir (mm) *" value={hauteur} onChangeText={setHauteur} keyboardType="numeric" testID="input-hauteur" />

              <View style={styles.toggleRow}>
                <View style={{ flex: 1 }}>
                  <Text style={[styles.label, { marginTop: 0 }]}>SOLS FINIS À ZÉRO ?</Text>
                  <Text style={styles.small}>Aucune réserve d'épaisseur pour les revêtements.</Text>
                </View>
                <Switch
                  value={solsZero}
                  onValueChange={setSolsZero}
                  trackColor={{ false: C.BORDER, true: C.ACCENT }}
                  thumbColor={solsZero ? C.WHITE : C.GRAY3}
                  testID="toggle-sols-finis"
                />
              </View>

              {!solsZero && (
                <View style={styles.row}>
                  <View style={{ flex: 1 }}><Field label="Réserve bas (mm)" value={resBas} onChangeText={setResBas} keyboardType="numeric" testID="input-res-bas" /></View>
                  <View style={{ flex: 1 }}><Field label="Réserve haut (mm)" value={resHaut} onChangeText={setResHaut} keyboardType="numeric" testID="input-res-haut" /></View>
                </View>
              )}

              <Field label="Épaisseur de la dalle (mm) *" value={epDalle} onChangeText={setEpDalle} keyboardType="numeric" testID="input-ep-dalle" />

              <Text style={styles.section}>TRÉMIE</Text>
              <View style={styles.row}>
                <View style={{ flex: 1 }}><Field label="Longueur (mm) *" value={tremieL} onChangeText={setTremieL} keyboardType="numeric" testID="input-tremie-l" /></View>
                <View style={{ flex: 1 }}><Field label="Largeur (mm) *" value={tremieW} onChangeText={setTremieW} keyboardType="numeric" testID="input-tremie-w" /></View>
              </View>

              <View style={styles.labelRow}>
                <Text style={styles.label}>RECULEMENT MAXIMAL AU SOL (MM) *</Text>
                <TouchableOpacity onPress={() => setShowReculHelp(true)} testID="btn-help-recul" hitSlop={10}>
                  <Ionicons name="help-circle" size={22} color={C.ACCENT} />
                </TouchableOpacity>
              </View>
              <TextInput
                style={styles.input}
                placeholder="ex. 3500"
                placeholderTextColor={C.GRAY3}
                value={recul}
                onChangeText={setRecul}
                keyboardType="numeric"
                testID="input-reculement"
              />

              {/* Help Modal — Recul au sol */}
              {showReculHelp && (
                <View style={styles.helpOverlay}>
                  <View style={styles.helpCard}>
                    <View style={styles.helpHead}>
                      <MaterialCommunityIcons name="ruler-square-compass" size={24} color={C.ACCENT} />
                      <Text style={styles.helpTitle}>Reculement au sol</Text>
                      <TouchableOpacity onPress={() => setShowReculHelp(false)} testID="btn-close-help">
                        <Ionicons name="close" size={22} color={C.WHITE} />
                      </TouchableOpacity>
                    </View>
                    <Text style={styles.helpTxt}>
                      Le <Text style={{ color: C.ACCENT, fontWeight: '700' }}>reculement</Text> est la
                      distance horizontale disponible au sol pour poser l'escalier, mesurée du pied
                      de la première marche jusqu'au mur opposé (ou tout autre obstacle).
                    </Text>
                    <View style={styles.helpDiagram}>
                      <View style={styles.helpDiagramStair} />
                      <View style={styles.helpDiagramFloor} />
                      <View style={styles.helpDiagramArrow}>
                        <Ionicons name="arrow-back" size={16} color={C.ACCENT} />
                        <Text style={styles.helpDiagramTxt}>RECULEMENT</Text>
                        <Ionicons name="arrow-forward" size={16} color={C.ACCENT} />
                      </View>
                    </View>
                    <Text style={[styles.helpTxt, { color: C.WARN }]}>
                      ⚠️ Plus le reculement est court, plus l'escalier sera raide (et inversement).
                      Pour un escalier confortable : ≥ 3500 mm sur 2700 mm de hauteur.
                    </Text>
                    <TouchableOpacity style={styles.helpOk} onPress={() => setShowReculHelp(false)}>
                      <Text style={styles.helpOkTxt}>J'AI COMPRIS</Text>
                    </TouchableOpacity>
                  </View>
                </View>
              )}

              <Field
                label="Hauteur sous plafond au niveau de la trémie (mm)"
                value={hauteurPlafondTremie}
                onChangeText={setHauteurPlafondTremie}
                keyboardType="numeric"
                testID="input-hauteur-plafond-tremie"
              />

              <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: SP.lg }}>
                <Text style={styles.label}>REMARQUES / OBSTACLES *</Text>
                <TouchableOpacity
                  onPress={recording ? stopRec : startRec}
                  disabled={transcribing}
                  style={[styles.dictateBtn, recording && { backgroundColor: C.DANGER_BG, borderColor: C.DANGER }]}
                  testID="btn-dicter"
                >
                  {transcribing ? <ActivityIndicator color={C.ACCENT} size="small" /> : (
                    <>
                      <Feather name={recording ? 'stop-circle' : 'mic'} size={14} color={recording ? C.DANGER : C.ACCENT} />
                      <Text style={[styles.dictateTxt, { color: recording ? C.DANGER : C.ACCENT }]}>
                        {recording ? 'STOP' : 'DICTER'}
                      </Text>
                    </>
                  )}
                </TouchableOpacity>
              </View>
              <TextInput
                style={[styles.input, { height: 100, textAlignVertical: 'top', paddingTop: 12 }]}
                placeholder="Tuyauterie au plafond, sortie à droite, mur porteur..."
                placeholderTextColor={C.GRAY3}
                value={remarques}
                onChangeText={setRemarques}
                multiline
                testID="input-remarques"
              />
            </>
          )}

          {step === 3 && result && (
            <>
              <Text style={styles.section}>RÉSULTATS</Text>
              <View style={[styles.resultCard]}>
                <View style={{ alignItems: 'center', marginBottom: SP.md }}>
                  <StairSketch
                    trueHeight={result.true_height}
                    reculement={result.reculement_needed}
                    n={result.n_steps}
                    h={result.h}
                    g={result.g}
                    tremieL={Number(tremieL)}
                    tremieW={Number(tremieW)}
                    limonLength={result.limon_length}
                  />
                </View>
                <Text style={[styles.shape, { color: result.shape.includes('Droit') ? C.ACCENT : C.WARN }]}>
                  {result.shape}
                </Text>

                {/* Échappée critique alert */}
                {result.echappee_critique && (
                  <View style={styles.alertCritical} testID="alert-echappee-critique">
                    <Ionicons name="warning" size={20} color={C.DANGER} />
                    <Text style={styles.alertCriticalTxt}>
                      ⚠️ Échappée critique ({Math.round(result.echappee)} mm &lt; 2000 mm) : Risque de choc à la tête
                    </Text>
                  </View>
                )}

                <View style={styles.kpiRow}>
                  <Kpi label="Marches" value={`${result.n_steps}`} />
                  <Kpi label="h" value={`${Math.round(result.h)}`} />
                  <Kpi label={result.is_tournant ? 'g (foulée)' : 'g'} value={`${Math.round(result.g)}`} />
                </View>
                <View style={styles.kpiRow}>
                  <Kpi label="Pente" value={`${result.slope_angle}°`} />
                  <Kpi label="2h+g" value={`${Math.round(result.blondel_value)}`} ok={result.valid_blondel} />
                  {result.echappee !== null && result.echappee !== undefined ? (
                    <Kpi label="Échappée" value={`${Math.round(result.echappee)}`} ok={!result.echappee_critique} />
                  ) : (
                    <Kpi label="Pente" value=" " />
                  )}
                </View>

                {/* Limon — featured atelier dimension */}
                <View style={styles.limonCard} testID="kpi-limon">
                  <MaterialCommunityIcons name="ruler" size={24} color={C.ACCENT} />
                  <View style={{ flex: 1, marginLeft: SP.md }}>
                    <Text style={styles.limonLabel}>LONGUEUR DU LIMON</Text>
                    <Text style={styles.limonHint}>Dimension exacte pour l'atelier (découpe poutre)</Text>
                  </View>
                  <Text style={styles.limonValue}>{Math.round(result.limon_length)} mm</Text>
                </View>

                {result.ligne_foulee_note && (
                  <View style={styles.fouleeNote}>
                    <MaterialCommunityIcons name="rotate-3d-variant" size={18} color={C.ACCENT} />
                    <Text style={styles.fouleeNoteTxt}>{result.ligne_foulee_note}</Text>
                  </View>
                )}

                {result.notes && result.notes.length > 0 && (
                  <View style={{ marginTop: SP.md }}>
                    {result.notes.map((n: string, i: number) => (
                      <Text key={i} style={{ ...FONT.small, color: C.WARN, marginBottom: 2 }}>• {n}</Text>
                    ))}
                  </View>
                )}
              </View>
            </>
          )}
        </ScrollView>

        {/* Footer */}
        <View style={styles.footer}>
          {step > 1 && (
            <TouchableOpacity style={styles.btnBack} onPress={() => setStep(step - 1)} testID="btn-back">
              <Ionicons name="arrow-back" size={18} color={C.WHITE} />
              <Text style={styles.btnBackTxt}>RETOUR</Text>
            </TouchableOpacity>
          )}
          {step < 3 ? (
            <TouchableOpacity style={styles.btnNext} onPress={next} testID="btn-next">
              <Text style={styles.btnNextTxt}>SUIVANT</Text>
              <Ionicons name="arrow-forward" size={18} color={C.DARK} />
            </TouchableOpacity>
          ) : (
            <TouchableOpacity style={styles.btnNext} onPress={saveAndValidate} disabled={saving} testID="btn-validate-conception">
              {saving ? <ActivityIndicator color={C.DARK} /> : (
                <>
                  <Ionicons name="checkmark" size={20} color={C.DARK} />
                  <Text style={styles.btnNextTxt}>VALIDER CETTE CONCEPTION</Text>
                </>
              )}
            </TouchableOpacity>
          )}
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function Field({ label, ...rest }: any) {
  return (
    <View>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        style={styles.input}
        placeholderTextColor={C.GRAY3}
        {...rest}
      />
    </View>
  );
}

function Kpi({ label, value, ok }: any) {
  return (
    <View style={{ flex: 1, backgroundColor: C.BG_DEEPER, padding: SP.md, borderRadius: R.md, alignItems: 'center', borderWidth: 1, borderColor: C.BORDER }}>
      <Text style={{ ...FONT.small, fontSize: 11 }}>{label}</Text>
      <Text style={{ ...FONT.h3, marginTop: 4, color: ok === false ? C.DANGER : C.ACCENT }}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: C.DARK },
  topbar: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', padding: SP.lg, borderBottomWidth: 1, borderBottomColor: C.BORDER },
  title: { ...FONT.h2, fontSize: 18 },
  stepperRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: SP.lg, paddingVertical: SP.md },
  dots: { flexDirection: 'row', gap: SP.sm },
  dot: { width: 32, height: 32, borderRadius: 16, backgroundColor: C.CARD, borderWidth: 1, borderColor: C.BORDER, alignItems: 'center', justifyContent: 'center' },
  dotActive: { backgroundColor: C.ACCENT, borderColor: C.ACCENT },
  dotTxt: { color: C.GRAY3, fontWeight: '800' },
  problemBtn: { flexDirection: 'row', alignItems: 'center', gap: 6, borderColor: C.DANGER, borderWidth: 1, borderRadius: R.md, paddingHorizontal: SP.md, paddingVertical: 8 },
  problemTxt: { color: C.DANGER, fontSize: 12, fontWeight: '700' },
  section: { ...FONT.label, color: C.ACCENT, marginTop: SP.lg, marginBottom: SP.sm },
  hint: { ...FONT.small, marginBottom: SP.lg },
  matGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: SP.md },
  matCard: { flex: 1, minWidth: 100, aspectRatio: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: C.CARD, borderRadius: R.lg, borderWidth: 1, borderColor: C.BORDER, padding: SP.md },
  matCardActive: { backgroundColor: C.ACCENT, borderColor: C.ACCENT },
  matLabel: { ...FONT.button, color: C.WHITE, fontSize: 14, marginTop: SP.sm },
  label: { ...FONT.label, marginTop: SP.lg, marginBottom: SP.sm },
  labelRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: SP.lg, marginBottom: SP.sm },
  small: { ...FONT.small, marginTop: 2, fontSize: 11 },
  // Help modal (Recul au sol)
  helpOverlay: { position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.85)', alignItems: 'center', justifyContent: 'center', padding: SP.lg, zIndex: 99 },
  helpCard: { backgroundColor: C.CARD, borderRadius: R.lg, padding: SP.lg, width: '100%', maxWidth: 420, borderWidth: 1, borderColor: C.ACCENT },
  helpHead: { flexDirection: 'row', alignItems: 'center', gap: SP.sm, marginBottom: SP.md },
  helpTitle: { ...FONT.h3, flex: 1 },
  helpTxt: { ...FONT.body, color: C.GRAY1, lineHeight: 21, marginBottom: SP.md },
  helpDiagram: { height: 80, backgroundColor: C.BG_DEEPER, borderRadius: R.md, padding: SP.sm, marginBottom: SP.md, position: 'relative', justifyContent: 'flex-end' },
  helpDiagramStair: { position: 'absolute', left: 12, top: 12, width: 0, height: 0, borderStyle: 'solid', borderLeftWidth: 0, borderRightWidth: 60, borderBottomWidth: 50, borderTopWidth: 0, borderRightColor: 'transparent', borderBottomColor: C.ACCENT, borderTopColor: 'transparent', borderLeftColor: 'transparent' },
  helpDiagramFloor: { height: 2, backgroundColor: C.GRAY3, marginBottom: 8 },
  helpDiagramArrow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 4 },
  helpDiagramTxt: { ...FONT.label, color: C.ACCENT, fontSize: 10 },
  helpOk: { backgroundColor: C.ACCENT, borderRadius: R.md, paddingVertical: 12, alignItems: 'center' },
  helpOkTxt: { ...FONT.button, color: C.DARK, fontSize: 13 },
  input: { backgroundColor: C.BG_DEEPER, borderWidth: 1, borderColor: C.BORDER, borderRadius: R.md, paddingHorizontal: SP.md, paddingVertical: 14, color: C.WHITE, fontSize: 16 },
  toggleRow: { flexDirection: 'row', alignItems: 'center', backgroundColor: C.CARD, padding: SP.md, borderRadius: R.md, borderWidth: 1, borderColor: C.BORDER, marginTop: SP.lg },
  row: { flexDirection: 'row', gap: SP.md },
  dictateBtn: { flexDirection: 'row', alignItems: 'center', gap: 6, borderWidth: 1, borderColor: C.ACCENT, borderRadius: R.md, paddingHorizontal: SP.md, paddingVertical: 6 },
  dictateTxt: { fontSize: 12, fontWeight: '800', color: C.ACCENT },
  resultCard: { backgroundColor: C.CARD, borderRadius: R.lg, padding: SP.lg, borderWidth: 1, borderColor: C.BORDER },
  shape: { ...FONT.h3, textAlign: 'center', marginBottom: SP.md },
  kpiRow: { flexDirection: 'row', gap: SP.sm, marginBottom: SP.sm },
  alertCritical: { flexDirection: 'row', alignItems: 'center', gap: SP.sm, padding: SP.md, backgroundColor: C.DANGER_BG, borderRadius: R.md, borderLeftWidth: 3, borderLeftColor: C.DANGER, marginBottom: SP.md },
  alertCriticalTxt: { ...FONT.body, color: C.DANGER, flex: 1, fontWeight: '700', fontSize: 13 },
  limonCard: { flexDirection: 'row', alignItems: 'center', padding: SP.md, backgroundColor: C.ACCENT_BG, borderRadius: R.md, borderLeftWidth: 3, borderLeftColor: C.ACCENT, marginTop: SP.md },
  limonLabel: { ...FONT.label, color: C.ACCENT, fontSize: 11 },
  limonHint: { ...FONT.small, fontSize: 11, marginTop: 2 },
  limonValue: { ...FONT.h2, fontSize: 22, color: C.ACCENT },
  fouleeNote: { flexDirection: 'row', alignItems: 'flex-start', gap: SP.sm, padding: SP.md, backgroundColor: C.BG_DEEPER, borderRadius: R.md, marginTop: SP.md, borderWidth: 1, borderColor: C.BORDER },
  fouleeNoteTxt: { ...FONT.small, color: C.GRAY1, flex: 1, lineHeight: 18 },
  footer: { flexDirection: 'row', padding: SP.lg, gap: SP.md, borderTopWidth: 1, borderTopColor: C.BORDER, backgroundColor: C.DARK },
  btnBack: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: SP.sm, backgroundColor: C.CARD, borderRadius: R.md, paddingVertical: 16, borderWidth: 1, borderColor: C.BORDER },
  btnBackTxt: { ...FONT.button, color: C.WHITE, fontSize: 14 },
  btnNext: { flex: 2, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: SP.sm, backgroundColor: C.ACCENT, borderRadius: R.md, paddingVertical: 16 },
  btnNextTxt: { ...FONT.button, color: C.DARK, fontSize: 14 },
});
