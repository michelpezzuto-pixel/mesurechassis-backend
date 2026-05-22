/**
 * STAIR EDITOR v2 — Niveaux + Tronçons + Croquis pédagogiques + KPI temps réel.
 * URL : /projects/[id]/stairs/[sid]
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity, ActivityIndicator,
  TextInput, Switch, Alert, KeyboardAvoidingView, Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, useRouter, useFocusEffect } from 'expo-router';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import Svg, { Line, Polygon, Rect, Text as SvgText, G, Circle } from 'react-native-svg';
import { Stairs, ApiStair, ApiNiveau, ApiTroncon, StairCompute, TronconType } from '@/src/api';
import { C, SP, R, FONT } from '@/src/theme';

const TYPE_LABEL: Record<TronconType, string> = {
  droit: 'Droit',
  palier: 'Palier',
  quart_bas: 'Quart-tournant BAS',
  quart_haut: 'Quart-tournant HAUT',
};

const TYPE_ICON: Record<TronconType, any> = {
  droit: 'arrow-up-bold',
  palier: 'pause',
  quart_bas: 'rotate-3d-variant',
  quart_haut: 'rotate-3d',
};

export default function StairEditor() {
  const { id, sid } = useLocalSearchParams<{ id: string; sid: string }>();
  const router = useRouter();
  const [stair, setStair] = useState<ApiStair | null>(null);
  const [compute, setCompute] = useState<StairCompute | null>(null);
  const [loading, setLoading] = useState(true);
  const [computing, setComputing] = useState(false);

  const refresh = useCallback(async () => {
    if (!id || !sid) return;
    try {
      const s = await Stairs.get(id, sid);
      setStair(s);
      setComputing(true);
      const c = await Stairs.compute(id, sid).catch(() => null);
      if (c) setCompute(c);
    } catch (e: any) {
      Alert.alert('Erreur', e?.response?.data?.detail || 'Chargement impossible');
      router.back();
    } finally { setLoading(false); setComputing(false); }
  }, [id, sid, router]);

  const recompute = useCallback(async () => {
    if (!id || !sid) return;
    setComputing(true);
    try {
      const c = await Stairs.compute(id, sid);
      setCompute(c);
    } catch { /* ignore */ }
    finally { setComputing(false); }
  }, [id, sid]);

  useFocusEffect(useCallback(() => { refresh(); }, [refresh]));

  // ── Niveau actions ──
  const addNiveau = async () => {
    if (!stair) return;
    const label = `Niveau ${stair.niveaux.length + 1}`;
    try {
      const n = await Stairs.addNiveau(id!, sid!, { label, hauteur_mm: 2700, sol_fini: true });
      setStair({ ...stair, niveaux: [...stair.niveaux, n] });
      recompute();
    } catch (e: any) {
      Alert.alert('Erreur', e?.response?.data?.detail || 'Erreur');
    }
  };

  const updateNiveauLocal = (nid: string, patch: Partial<ApiNiveau>) => {
    if (!stair) return;
    setStair({
      ...stair,
      niveaux: stair.niveaux.map(n => n.id === nid ? { ...n, ...patch } : n),
    });
  };

  const commitNiveau = async (nid: string, patch: Partial<ApiNiveau>) => {
    try {
      await Stairs.updateNiveau(id!, sid!, nid, patch);
      recompute();
    } catch { /* ignore */ }
  };

  const removeNiveau = (n: ApiNiveau) => {
    Alert.alert(`Supprimer "${n.label}" ?`, '', [
      { text: 'Annuler', style: 'cancel' },
      { text: 'Supprimer', style: 'destructive', onPress: async () => {
        await Stairs.removeNiveau(id!, sid!, n.id);
        setStair({ ...stair!, niveaux: stair!.niveaux.filter(x => x.id !== n.id) });
        recompute();
      }},
    ]);
  };

  // ── Tronçon actions ──
  const addTroncon = async (niveau: ApiNiveau, type: TronconType) => {
    const defaultLen = type === 'palier' ? 1000 : 2500;
    try {
      const t = await Stairs.addTroncon(id!, sid!, niveau.id, { type, longueur_mm: defaultLen, largeur_mm: 900 });
      updateNiveauLocal(niveau.id, { troncons: [...niveau.troncons, t] });
      recompute();
    } catch (e: any) { Alert.alert('Erreur', e?.response?.data?.detail || 'Erreur'); }
  };

  const updateTronconLocal = (nid: string, tid: string, patch: Partial<ApiTroncon>) => {
    if (!stair) return;
    setStair({
      ...stair,
      niveaux: stair.niveaux.map(n =>
        n.id === nid ? { ...n, troncons: n.troncons.map(t => t.id === tid ? { ...t, ...patch } : t) } : n,
      ),
    });
  };

  const commitTroncon = async (nid: string, tid: string, patch: Partial<ApiTroncon>) => {
    try {
      await Stairs.updateTroncon(id!, sid!, nid, tid, patch);
      recompute();
    } catch { /* ignore */ }
  };

  const removeTroncon = (nid: string, t: ApiTroncon) => {
    Alert.alert('Supprimer ce tronçon ?', '', [
      { text: 'Annuler', style: 'cancel' },
      { text: 'Supprimer', style: 'destructive', onPress: async () => {
        await Stairs.removeTroncon(id!, sid!, nid, t.id);
        updateNiveauLocal(nid, { troncons: stair!.niveaux.find(n => n.id === nid)!.troncons.filter(x => x.id !== t.id) });
        recompute();
      }},
    ]);
  };

  const goExport = () => router.push(`/projects/${id}/export` as any);

  if (loading || !stair) {
    return (
      <SafeAreaView style={[styles.safe, { justifyContent: 'center', alignItems: 'center' }]}>
        <ActivityIndicator color={C.ACCENT} size="large" />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1 }}>
        <View style={styles.topbar}>
          <TouchableOpacity onPress={() => router.back()} hitSlop={10}>
            <Ionicons name="arrow-back" size={24} color={C.WHITE} />
          </TouchableOpacity>
          <View style={{ flex: 1, alignItems: 'center' }}>
            <Text style={styles.topbarLabel}>ESCALIER</Text>
            <Text style={styles.topbarTitle} numberOfLines={1}>{stair.name.toUpperCase()}</Text>
          </View>
          {computing ? <ActivityIndicator color={C.ACCENT} /> : <View style={{ width: 24 }} />}
        </View>

        <ScrollView contentContainerStyle={{ padding: SP.lg, paddingBottom: 130 }} keyboardShouldPersistTaps="handled">
          {/* KPI global */}
          {compute && (
            <View style={styles.kpiBlock}>
              <KPI label="MARCHES" value={compute.total_steps} />
              <KPI label="HAUTEUR" value={`${Math.round(compute.total_height)}`} unit="mm" />
              <KPI label="RECULEMENT" value={`${Math.round(compute.total_reculement)}`} unit="mm" />
              <KPI label="LIMON" value={`${Math.round(compute.limon_length)}`} unit="mm" />
            </View>
          )}

          {/* Warnings */}
          {!!compute?.warnings.length && (
            <View style={styles.warnBox}>
              <Ionicons name="warning" size={18} color={C.WARN} />
              <View style={{ flex: 1, marginLeft: SP.sm }}>
                {compute.warnings.map((w, i) => <Text key={i} style={styles.warnTxt}>{w}</Text>)}
              </View>
            </View>
          )}

          {/* Niveaux */}
          {stair.niveaux.length === 0 ? (
            <View style={styles.empty}>
              <MaterialCommunityIcons name="layers-outline" size={48} color={C.GRAY3} />
              <Text style={styles.emptyTitle}>Aucun niveau</Text>
              <Text style={styles.emptyHint}>Ajoutez un niveau (RDC, R+1, ...) puis ses tronçons.</Text>
            </View>
          ) : (
            stair.niveaux.map((n, idx) => {
              const calc = compute?.niveaux_calc.find(x => x.niveau_id === n.id);
              return (
                <NiveauCard
                  key={n.id}
                  niveau={n}
                  index={idx}
                  calc={calc}
                  onPatchLocal={(patch) => updateNiveauLocal(n.id, patch)}
                  onCommit={(patch) => commitNiveau(n.id, patch)}
                  onRemove={() => removeNiveau(n)}
                  onAddTroncon={(type) => addTroncon(n, type)}
                  onPatchTronconLocal={(tid, patch) => updateTronconLocal(n.id, tid, patch)}
                  onCommitTroncon={(tid, patch) => commitTroncon(n.id, tid, patch)}
                  onRemoveTroncon={(t) => removeTroncon(n.id, t)}
                />
              );
            })
          )}

          <TouchableOpacity style={styles.addNivBtn} onPress={addNiveau} testID="btn-add-niveau">
            <Ionicons name="add-circle-outline" size={20} color={C.ACCENT} />
            <Text style={styles.addNivBtnTxt}>AJOUTER UN NIVEAU</Text>
          </TouchableOpacity>
        </ScrollView>

        {/* Sticky bottom */}
        <View style={styles.bottomBar}>
          <TouchableOpacity style={[styles.btn, styles.btnGhost]} onPress={() => router.back()}>
            <Ionicons name="arrow-back" size={18} color={C.WHITE} />
            <Text style={[styles.btnTxt, { color: C.WHITE }]}>RETOUR</Text>
          </TouchableOpacity>
          <TouchableOpacity style={[styles.btn, styles.btnPrimary]} onPress={goExport} testID="btn-export">
            <Ionicons name="share-outline" size={18} color={C.DARK} />
            <Text style={styles.btnTxt}>EXPORTER</Text>
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

// ───────────────────────── NiveauCard ─────────────────────────

function NiveauCard({
  niveau, index, calc, onPatchLocal, onCommit, onRemove,
  onAddTroncon, onPatchTronconLocal, onCommitTroncon, onRemoveTroncon,
}: {
  niveau: ApiNiveau;
  index: number;
  calc: any;
  onPatchLocal: (patch: Partial<ApiNiveau>) => void;
  onCommit: (patch: Partial<ApiNiveau>) => void;
  onRemove: () => void;
  onAddTroncon: (type: TronconType) => void;
  onPatchTronconLocal: (tid: string, patch: Partial<ApiTroncon>) => void;
  onCommitTroncon: (tid: string, patch: Partial<ApiTroncon>) => void;
  onRemoveTroncon: (t: ApiTroncon) => void;
}) {
  const [expanded, setExpanded] = useState(true);
  const [tronconPickerOpen, setTronconPickerOpen] = useState(false);
  return (
    <View style={styles.niveauCard}>
      <TouchableOpacity onPress={() => setExpanded(!expanded)} style={styles.niveauHead} activeOpacity={0.8}>
        <View style={styles.niveauBadge}>
          <Text style={styles.niveauNum}>{index + 1}</Text>
        </View>
        <View style={{ flex: 1 }}>
          <TextInput
            value={niveau.label}
            onChangeText={(v) => onPatchLocal({ label: v })}
            onEndEditing={(e) => onCommit({ label: e.nativeEvent.text })}
            style={styles.niveauLabel}
            maxLength={30}
            testID={`niv-label-${niveau.id}`}
          />
          {calc && (
            <Text style={styles.niveauMeta}>
              {calc.n_steps_niveau} marche{calc.n_steps_niveau > 1 ? 's' : ''} ·
              h {Math.round(calc.h)} mm · g {Math.round(calc.g)} mm
              {!calc.valid_blondel ? '  ⚠' : ''}
            </Text>
          )}
        </View>
        <TouchableOpacity onPress={onRemove} hitSlop={10} style={{ marginRight: 8 }}>
          <Ionicons name="trash-outline" size={18} color={C.DANGER} />
        </TouchableOpacity>
        <Ionicons name={expanded ? 'chevron-up' : 'chevron-down'} size={20} color={C.GRAY3} />
      </TouchableOpacity>

      {expanded && (
        <View style={styles.niveauBody}>
          {/* Hauteur + sol fini */}
          <View style={styles.fieldsRow}>
            <View style={{ flex: 1 }}>
              <Text style={styles.fieldLabel}>HAUTEUR TOTALE (mm)</Text>
              <TextInput
                value={String(niveau.hauteur_mm)}
                onChangeText={(v) => onPatchLocal({ hauteur_mm: parseFloat(v) || 0 })}
                onEndEditing={(e) => onCommit({ hauteur_mm: parseFloat(e.nativeEvent.text) || 0 })}
                keyboardType="numeric"
                style={styles.input}
                testID={`niv-h-${niveau.id}`}
              />
            </View>
            <View style={{ flex: 1, marginLeft: SP.md }}>
              <Text style={styles.fieldLabel}>SOL FINI</Text>
              <View style={styles.toggleRow}>
                <Switch
                  value={niveau.sol_fini}
                  onValueChange={(v) => { onPatchLocal({ sol_fini: v }); onCommit({ sol_fini: v }); }}
                  trackColor={{ false: C.BORDER, true: C.ACCENT }}
                  thumbColor={C.WHITE}
                  testID={`niv-solfini-${niveau.id}`}
                />
                <Text style={styles.toggleTxt}>{niveau.sol_fini ? 'Oui' : 'Non'}</Text>
              </View>
            </View>
          </View>

          {!niveau.sol_fini && (
            <View>
              <Text style={styles.fieldLabel}>RÉSERVE DE SOL (mm)</Text>
              <TextInput
                value={String(niveau.reserve_mm)}
                onChangeText={(v) => onPatchLocal({ reserve_mm: parseFloat(v) || 0 })}
                onEndEditing={(e) => onCommit({ reserve_mm: parseFloat(e.nativeEvent.text) || 0 })}
                keyboardType="numeric"
                style={styles.input}
                placeholder="ex. 50"
                placeholderTextColor={C.GRAY3}
              />
              <Text style={styles.hint}>Cette valeur sera soustraite de la hauteur pour le calcul du limon.</Text>
            </View>
          )}

          {/* Croquis pédagogique du niveau */}
          {niveau.troncons.length > 0 && calc && <NiveauSketch niveau={niveau} calc={calc} />}

          {/* Tronçons */}
          <Text style={[styles.fieldLabel, { marginTop: SP.lg }]}>TRONÇONS ({niveau.troncons.length})</Text>
          {niveau.troncons.map((t: ApiTroncon, ti: number) => {
            const tcalc = calc?.troncons_calc.find((c: any) => c.troncon_id === t.id);
            return (
              <View key={t.id} style={styles.tronconCard}>
                <View style={styles.tronconHead}>
                  <View style={styles.tronconBadge}>
                    <MaterialCommunityIcons name={TYPE_ICON[t.type]} size={16} color={C.ACCENT} />
                  </View>
                  <Text style={styles.tronconTitle}>{ti + 1}. {TYPE_LABEL[t.type]}</Text>
                  {tcalc && <Text style={styles.tronconCount}>{tcalc.n_marches} marche{tcalc.n_marches > 1 ? 's' : ''}</Text>}
                  <TouchableOpacity onPress={() => onRemoveTroncon(t)} hitSlop={10}>
                    <Ionicons name="close" size={18} color={C.DANGER} />
                  </TouchableOpacity>
                </View>
                <View style={styles.fieldsRow}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.fieldLabelSm}>LONGUEUR (mm)</Text>
                    <TextInput
                      value={String(t.longueur_mm)}
                      onChangeText={(v) => onPatchTronconLocal(t.id, { longueur_mm: parseFloat(v) || 0 })}
                      onEndEditing={(e) => onCommitTroncon(t.id, { longueur_mm: parseFloat(e.nativeEvent.text) || 0 })}
                      keyboardType="numeric"
                      style={styles.inputSm}
                    />
                  </View>
                  <View style={{ flex: 1, marginLeft: SP.sm }}>
                    <Text style={styles.fieldLabelSm}>LARGEUR (mm)</Text>
                    <TextInput
                      value={String(t.largeur_mm)}
                      onChangeText={(v) => onPatchTronconLocal(t.id, { largeur_mm: parseFloat(v) || 0 })}
                      onEndEditing={(e) => onCommitTroncon(t.id, { largeur_mm: parseFloat(e.nativeEvent.text) || 0 })}
                      keyboardType="numeric"
                      style={styles.inputSm}
                    />
                  </View>
                </View>
              </View>
            );
          })}

          {/* Add tronçon picker */}
          {tronconPickerOpen ? (
            <View style={styles.pickerRow}>
              {(['droit', 'quart_bas', 'quart_haut', 'palier'] as TronconType[]).map(type => (
                <TouchableOpacity
                  key={type}
                  style={styles.pickerBtn}
                  onPress={() => { onAddTroncon(type); setTronconPickerOpen(false); }}
                  testID={`add-troncon-${type}`}
                >
                  <MaterialCommunityIcons name={TYPE_ICON[type]} size={18} color={C.ACCENT} />
                  <Text style={styles.pickerTxt}>{TYPE_LABEL[type]}</Text>
                </TouchableOpacity>
              ))}
              <TouchableOpacity style={[styles.pickerBtn, { borderColor: C.BORDER }]} onPress={() => setTronconPickerOpen(false)}>
                <Ionicons name="close" size={18} color={C.GRAY3} />
              </TouchableOpacity>
            </View>
          ) : (
            <TouchableOpacity style={styles.addTronconBtn} onPress={() => setTronconPickerOpen(true)} testID={`add-troncon-niv-${niveau.id}`}>
              <Ionicons name="add" size={18} color={C.DARK} />
              <Text style={styles.addTronconTxt}>AJOUTER UN TRONÇON</Text>
            </TouchableOpacity>
          )}
        </View>
      )}
    </View>
  );
}

// ───────────────────────── NiveauSketch (croquis pédagogique) ─────────────────────────

function NiveauSketch({ niveau, calc }: { niveau: ApiNiveau; calc: any }) {
  const W = 320, H = 130;
  const hauteur = niveau.hauteur_mm || 0;
  const totalLen = niveau.troncons.reduce((s, t) => s + t.longueur_mm, 0) || 1;
  const M = 36;
  const usableW = W - M * 2;
  const usableH = H - 30;
  // Map points: each marche tronçon adds vertical h_steps * n_marches climbing
  const points: { x: number; y: number }[] = [{ x: M, y: H - 10 }];
  let cum = 0;
  let curH = H - 10;
  niveau.troncons.forEach(t => {
    const cTr = calc.troncons_calc.find((c: any) => c.troncon_id === t.id);
    const wPx = (t.longueur_mm / totalLen) * usableW;
    if (t.type === 'palier') {
      curH = curH; // pas de montée
    } else if (cTr) {
      const rise = (cTr.n_marches / calc.n_steps_niveau) * usableH;
      curH = curH - rise;
    }
    cum += wPx;
    points.push({ x: M + cum, y: curH });
  });
  const poly = points.map(p => `${p.x},${p.y}`).join(' ');

  return (
    <View style={{ alignItems: 'center', marginTop: SP.md, marginBottom: SP.sm }}>
      <Svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}>
        <Rect x={0} y={0} width={W} height={H} fill={C.BG_DEEPER} rx={10} />
        {/* Sol */}
        <Line x1={M - 10} y1={H - 10} x2={W - M + 10} y2={H - 10} stroke={C.GRAY3} strokeWidth={1} />
        {/* Plafond (cible) */}
        <Line x1={M - 10} y1={20} x2={W - M + 10} y2={20} stroke={C.GRAY3} strokeWidth={0.5} strokeDasharray="3,3" />
        {/* Polyligne escalier */}
        <Polygon points={poly} fill="none" stroke={C.ACCENT} strokeWidth={1.5} />
        {/* Flèche hauteur (gauche) */}
        <Line x1={M - 18} y1={20} x2={M - 18} y2={H - 10} stroke={C.ACCENT} strokeWidth={1} />
        <Polygon points={`${M - 22},${24} ${M - 14},${24} ${M - 18},${18}`} fill={C.ACCENT} />
        <Polygon points={`${M - 22},${H - 14} ${M - 14},${H - 14} ${M - 18},${H - 8}`} fill={C.ACCENT} />
        <SvgText x={M - 26} y={H / 2 + 4} fontSize={9} fill={C.WHITE} textAnchor="end">{Math.round(hauteur)}</SvgText>
        {/* Flèche reculement (bas) */}
        <Line x1={M} y1={H + 4} x2={W - M} y2={H + 4} stroke={C.ACCENT} strokeWidth={0.8} />
        {/* Labels par tronçon */}
        {niveau.troncons.map((t, i) => {
          const prev = i === 0 ? M : M + niveau.troncons.slice(0, i).reduce((s, x) => s + (x.longueur_mm / totalLen) * usableW, 0);
          const wPx = (t.longueur_mm / totalLen) * usableW;
          return (
            <SvgText key={t.id} x={prev + wPx / 2} y={H - 16} fontSize={8} fill={C.GRAY3} textAnchor="middle">
              {Math.round(t.longueur_mm)}
            </SvgText>
          );
        })}
      </Svg>
      <Text style={styles.sketchLegend}>Vue de profil — flèches : hauteur ({Math.round(hauteur)} mm) et longueurs par tronçon (mm)</Text>
    </View>
  );
}

function KPI({ label, value, unit }: { label: string; value: any; unit?: string }) {
  return (
    <View style={styles.kpi}>
      <Text style={styles.kpiLabel}>{label}</Text>
      <View style={{ flexDirection: 'row', alignItems: 'baseline', gap: 2 }}>
        <Text style={styles.kpiVal}>{value}</Text>
        {!!unit && <Text style={styles.kpiUnit}>{unit}</Text>}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: C.DARK },
  topbar: { flexDirection: 'row', alignItems: 'center', padding: SP.lg, borderBottomWidth: 1, borderBottomColor: C.BORDER, gap: SP.md },
  topbarLabel: { ...FONT.label, color: C.GRAY3, fontSize: 9 },
  topbarTitle: { ...FONT.h3, fontSize: 14, letterSpacing: 0.5 },

  // KPI
  kpiBlock: { flexDirection: 'row', gap: SP.sm, marginBottom: SP.md },
  kpi: { flex: 1, backgroundColor: C.CARD, borderRadius: R.md, padding: SP.sm, alignItems: 'center', borderWidth: 1, borderColor: C.ACCENT, borderLeftWidth: 3 },
  kpiLabel: { ...FONT.label, fontSize: 9, color: C.GRAY3 },
  kpiVal: { ...FONT.h2, color: C.ACCENT, fontSize: 18 },
  kpiUnit: { ...FONT.small, color: C.GRAY3, fontSize: 9 },

  warnBox: { flexDirection: 'row', backgroundColor: 'rgba(245,158,11,0.12)', borderColor: C.WARN, borderWidth: 1, borderLeftWidth: 4, borderRadius: R.md, padding: SP.md, marginBottom: SP.md },
  warnTxt: { ...FONT.small, color: C.WHITE, fontSize: 11, lineHeight: 16, marginBottom: 4 },

  empty: { alignItems: 'center', padding: SP.xl, backgroundColor: C.CARD, borderRadius: R.lg, borderWidth: 1, borderStyle: 'dashed' as any, borderColor: C.BORDER, marginBottom: SP.md },
  emptyTitle: { ...FONT.h3, marginTop: SP.sm, fontSize: 14 },
  emptyHint: { ...FONT.small, textAlign: 'center', marginTop: 4 },

  // Niveau card
  niveauCard: { backgroundColor: C.CARD, borderRadius: R.lg, borderWidth: 1, borderColor: C.BORDER, marginBottom: SP.md, overflow: 'hidden' },
  niveauHead: { flexDirection: 'row', alignItems: 'center', padding: SP.md, gap: SP.sm },
  niveauBadge: { width: 32, height: 32, borderRadius: 16, backgroundColor: C.ACCENT_BG, borderWidth: 1, borderColor: C.ACCENT, alignItems: 'center', justifyContent: 'center' },
  niveauNum: { ...FONT.button, color: C.ACCENT, fontSize: 13 },
  niveauLabel: { ...FONT.h3, fontSize: 14, padding: 0 },
  niveauMeta: { ...FONT.small, fontSize: 11, marginTop: 2 },
  niveauBody: { padding: SP.md, paddingTop: 0, borderTopWidth: 1, borderTopColor: C.BORDER },

  fieldsRow: { flexDirection: 'row', marginTop: SP.md },
  fieldLabel: { ...FONT.label, fontSize: 10, marginBottom: 4 },
  fieldLabelSm: { ...FONT.label, fontSize: 9, marginBottom: 2 },
  input: { backgroundColor: C.BG_DEEPER, borderWidth: 1, borderColor: C.BORDER, borderRadius: R.md, padding: 10, color: C.WHITE, fontSize: 14 },
  inputSm: { backgroundColor: C.BG_DEEPER, borderWidth: 1, borderColor: C.BORDER, borderRadius: R.sm, padding: 8, color: C.WHITE, fontSize: 13 },
  toggleRow: { flexDirection: 'row', alignItems: 'center', gap: SP.sm, paddingVertical: 4 },
  toggleTxt: { ...FONT.body, fontSize: 13 },
  hint: { ...FONT.small, marginTop: 4, fontSize: 10 },

  sketchLegend: { ...FONT.small, fontSize: 10, marginTop: 4, textAlign: 'center' },

  tronconCard: { backgroundColor: C.BG_DEEPER, borderRadius: R.md, padding: SP.sm, marginTop: SP.sm, borderWidth: 1, borderColor: C.BORDER },
  tronconHead: { flexDirection: 'row', alignItems: 'center', gap: SP.sm, marginBottom: SP.sm },
  tronconBadge: { width: 26, height: 26, borderRadius: 13, backgroundColor: C.ACCENT_BG, alignItems: 'center', justifyContent: 'center', borderWidth: 1, borderColor: C.ACCENT },
  tronconTitle: { ...FONT.body, fontSize: 12, flex: 1, fontWeight: '600' as any },
  tronconCount: { ...FONT.label, color: C.ACCENT, fontSize: 10 },

  pickerRow: { flexDirection: 'row', flexWrap: 'wrap', gap: SP.sm, marginTop: SP.md },
  pickerBtn: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: SP.sm, paddingVertical: 8, borderRadius: R.md, borderWidth: 1, borderColor: C.ACCENT, backgroundColor: C.ACCENT_BG },
  pickerTxt: { ...FONT.label, color: C.ACCENT, fontSize: 10 },

  addTronconBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: SP.sm, paddingVertical: 10, marginTop: SP.md, borderRadius: R.md, backgroundColor: C.ACCENT },
  addTronconTxt: { ...FONT.button, color: C.DARK, fontSize: 11 },

  addNivBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: SP.sm, paddingVertical: 14, borderRadius: R.md, borderWidth: 1, borderColor: C.ACCENT, borderStyle: 'dashed' as any, marginTop: SP.sm, backgroundColor: 'transparent' },
  addNivBtnTxt: { ...FONT.button, color: C.ACCENT, fontSize: 12 },

  bottomBar: { position: 'absolute', bottom: 0, left: 0, right: 0, padding: SP.md, gap: SP.sm, backgroundColor: C.DARK, borderTopWidth: 1, borderTopColor: C.BORDER, flexDirection: 'row' },
  btn: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: SP.sm, paddingVertical: 14, borderRadius: R.md, borderWidth: 1 },
  btnGhost: { backgroundColor: C.CARD, borderColor: C.BORDER },
  btnPrimary: { backgroundColor: C.ACCENT, borderColor: C.ACCENT },
  btnTxt: { ...FONT.button, color: C.DARK, fontSize: 12 },
});
