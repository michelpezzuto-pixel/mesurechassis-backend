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
import { Stairs, ApiStair, ApiNiveau, ApiTroncon, StairCompute, TronconType, floorIndexToLabel, FLOOR_INDEX_RANGE } from '@/src/api';
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
  const [viewMode, setViewMode] = useState<'profile' | 'plan'>('profile');

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
  /**
   * Add a niveau using next-available floor_index :
   *   - Si aucun niveau → 0 (RDC)
   *   - Sinon → max(floor_index) + 1
   *   - Bloqué à +7 (UI) ; le backend rejettera hors plage [-3..+7]
   */
  const nextFloorIndex = useMemo(() => {
    if (!stair || stair.niveaux.length === 0) return 0;
    const maxIdx = Math.max(...stair.niveaux.map(n => n.floor_index));
    return Math.min(maxIdx + 1, 7);
  }, [stair]);

  const addNiveau = async (opts?: { ghost?: boolean; floor_index?: number }) => {
    if (!stair) return;
    const fi = opts?.floor_index ?? nextFloorIndex;
    try {
      const n = await Stairs.addNiveau(id!, sid!, {
        floor_index: fi,
        is_ghost: !!opts?.ghost,
        hauteur_mm: 2700,
        sol_fini: true,
      });
      setStair({ ...stair, niveaux: [...stair.niveaux, n].sort((a, b) => a.floor_index - b.floor_index) });
      recompute();
    } catch (e: any) {
      Alert.alert('Niveau invalide', e?.response?.data?.detail || 'Erreur');
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

  const goExport = () => router.push(`/projects/${id}/stairs/${sid}/export` as any);

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

          {/* ╔═══════════════════════════════════════════════════════╗
              UI BRANCH selon `stair.shape` :
              - DROIT    → formulaire ultra-épuré (3 inputs)
              - TOURNANT → multi-niveaux / tronçons / vue plan
            ╚═══════════════════════════════════════════════════════╝ */}
          {stair.shape === 'droit' ? (
            <DroitForm
              stair={stair}
              compute={compute}
              onCommitNiveau={commitNiveau}
              onCommitTroncon={commitTroncon}
              onPatchNiveauLocal={updateNiveauLocal}
              onPatchTronconLocal={updateTronconLocal}
            />
          ) : (
          <>

          {/* View mode toggle (Profile / Plan) */}
          {stair.niveaux.length > 0 && (
            <View style={styles.viewToggle} testID="view-mode-toggle">
              <TouchableOpacity
                style={[styles.viewToggleBtn, viewMode === 'profile' && styles.viewToggleBtnActive]}
                onPress={() => setViewMode('profile')}
                testID="btn-view-profile"
              >
                <MaterialCommunityIcons
                  name="stairs"
                  size={16}
                  color={viewMode === 'profile' ? C.DARK : C.GRAY3}
                />
                <Text style={[styles.viewToggleTxt, viewMode === 'profile' && styles.viewToggleTxtActive]}>
                  PROFIL
                </Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.viewToggleBtn, viewMode === 'plan' && styles.viewToggleBtnActive]}
                onPress={() => setViewMode('plan')}
                testID="btn-view-plan"
              >
                <MaterialCommunityIcons
                  name="floor-plan"
                  size={16}
                  color={viewMode === 'plan' ? C.DARK : C.GRAY3}
                />
                <Text style={[styles.viewToggleTxt, viewMode === 'plan' && styles.viewToggleTxtActive]}>
                  PLAN
                </Text>
              </TouchableOpacity>
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
                  viewMode={viewMode}
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

          <View style={styles.addNivRow}>
            <TouchableOpacity style={styles.addNivBtn} onPress={() => addNiveau()} testID="btn-add-niveau">
              <Ionicons name="add-circle-outline" size={20} color={C.ACCENT} />
              <Text style={styles.addNivBtnTxt}>AJOUTER UN NIVEAU</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.addNivBtn, styles.addGhostBtn]}
              onPress={() => addNiveau({ ghost: true })}
              testID="btn-add-niveau-ghost"
            >
              <Ionicons name="eye-off-outline" size={18} color={C.GRAY3} />
              <Text style={[styles.addNivBtnTxt, { color: C.GRAY3, fontSize: 10 }]}>NIVEAU FANTÔME</Text>
            </TouchableOpacity>
          </View>

          {/* DÉTAILS DE LA SAISIE — récap des inputs (data binding) */}
          {compute && stair.niveaux.length > 0 && (
            <View style={styles.recapCard} testID="detailed-data">
              <Text style={styles.recapTitle}>DÉTAILS DE LA SAISIE</Text>
              <View style={styles.recapRow}>
                <Text style={styles.recapKey}>Forme</Text>
                <Text style={styles.recapVal}>{stair.shape === 'droit' ? 'Droit' : 'Tournant'}</Text>
              </View>
              <View style={styles.recapRow}>
                <Text style={styles.recapKey}>Nombre de niveaux</Text>
                <Text style={styles.recapVal}>{compute.n_niveaux}</Text>
              </View>
              <View style={styles.recapRow}>
                <Text style={styles.recapKey}>Hauteur totale</Text>
                <Text style={styles.recapVal}>{Math.round(compute.total_height)} mm</Text>
              </View>
              <View style={styles.recapRow}>
                <Text style={styles.recapKey}>Reculement total</Text>
                <Text style={styles.recapVal}>{Math.round(compute.total_reculement)} mm</Text>
              </View>
              <View style={styles.recapRow}>
                <Text style={styles.recapKey}>Nombre de marches</Text>
                <Text style={styles.recapVal}>{compute.total_steps}</Text>
              </View>
              <View style={styles.recapRow}>
                <Text style={styles.recapKey}>Longueur du limon</Text>
                <Text style={styles.recapVal}>{Math.round(compute.limon_length)} mm</Text>
              </View>

              {/* Per-niveau breakdown */}
              <View style={styles.recapDivider} />
              {stair.niveaux.map(n => {
                const nc = compute.niveaux_calc.find(x => x.niveau_id === n.id);
                if (!nc) return null;
                const niveauLabel = n.is_ghost
                  ? `${n.label || floorIndexToLabel(n.floor_index)} (fantôme)`
                  : (n.label || floorIndexToLabel(n.floor_index));
                return (
                  <View key={n.id} style={styles.recapNivBlock}>
                    <Text style={styles.recapNivTitle}>{niveauLabel}</Text>
                    <Text style={styles.recapNivLine}>
                      H {Math.round(n.hauteur_mm)} · sol_fini {n.sol_fini ? 'oui' : 'non'}
                      {!n.sol_fini && ` · réserve ${Math.round(n.reserve_mm)}`}
                    </Text>
                    {!n.is_ghost && (
                      <Text style={styles.recapNivLine}>
                        {nc.n_steps_niveau} marches · h {Math.round(nc.h)} · g {Math.round(nc.g)} · Blondel {Math.round(nc.blondel_value)}
                      </Text>
                    )}
                    {n.troncons.length > 0 && (
                      <Text style={styles.recapNivLine}>
                        Tronçons : {n.troncons.map(t =>
                          `${t.type.replace('_', '-')} ${Math.round(t.longueur_mm)}×${Math.round(t.largeur_mm)}`,
                        ).join(' · ')}
                      </Text>
                    )}
                  </View>
                );
              })}
            </View>
          )}
          </>
          )}
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

// ───────────────────────── DROIT FORM (ultra-épuré) ─────────────────────────
//
// Quand `stair.shape === 'droit'` on n'expose QUE :
//   • Hauteur  (mm) → niveau.hauteur_mm
//   • Largeur  (mm) → troncon.largeur_mm
//   • Longueur (mm) → troncon.longueur_mm
// + Badge Blondel (vert/orange) avec marches calculées.
// Aucune gestion de niveau, aucun picker tronçon, aucune section "détails".

function DroitForm({
  stair, compute, onCommitNiveau, onCommitTroncon, onPatchNiveauLocal, onPatchTronconLocal,
}: {
  stair: ApiStair;
  compute: StairCompute | null;
  onCommitNiveau: (nid: string, patch: Partial<ApiNiveau>) => void;
  onCommitTroncon: (nid: string, tid: string, patch: Partial<ApiTroncon>) => void;
  onPatchNiveauLocal: (nid: string, patch: Partial<ApiNiveau>) => void;
  onPatchTronconLocal: (nid: string, tid: string, patch: Partial<ApiTroncon>) => void;
}) {
  const niveau = stair.niveaux[0];
  const troncon = niveau?.troncons[0];
  const niveauCalc = compute?.niveaux_calc.find(n => n.niveau_id === niveau?.id);

  if (!niveau || !troncon) {
    return (
      <View style={{ alignItems: 'center', padding: SP.xl }}>
        <ActivityIndicator color={C.ACCENT} />
        <Text style={[FONT.small, { marginTop: SP.md }]}>Préparation de l'escalier droit...</Text>
      </View>
    );
  }

  // HT / ED / HSP — logique de saisie liée
  // - entry_mode='hauteur' → HT saisi, HSP verrouillé (HSP = HT - ED)
  // - entry_mode='hsp'     → HSP saisi, HT verrouillé (HT = HSP + ED)
  const entryMode = niveau.entry_mode || 'hauteur';
  const HT = Math.round(niveau.hauteur_mm || 0);
  const ED = Math.round(niveau.epaisseur_dalle_mm || 0);
  const HSP = entryMode === 'hauteur' ? HT - ED : Math.round(niveau.hauteur_sous_plafond_mm || 0);
  const HTeff = entryMode === 'hsp' ? HSP + ED : HT;

  // Switch entry mode (clic sur le champ verrouillé)
  const switchEntryMode = () => {
    const newMode = entryMode === 'hauteur' ? 'hsp' : 'hauteur';
    onCommitNiveau(niveau.id, {
      entry_mode: newMode,
      hauteur_sous_plafond_mm: HSP,
    });
  };

  const updateHT = (v: number) => {
    onPatchNiveauLocal(niveau.id, { hauteur_mm: v, hauteur_sous_plafond_mm: v - ED, entry_mode: 'hauteur' });
  };
  const commitHT = (v: number) => {
    onCommitNiveau(niveau.id, { hauteur_mm: v, hauteur_sous_plafond_mm: v - ED, entry_mode: 'hauteur' });
  };
  const updateED = (v: number) => {
    if (entryMode === 'hauteur') {
      onPatchNiveauLocal(niveau.id, { epaisseur_dalle_mm: v, hauteur_sous_plafond_mm: HT - v });
    } else {
      onPatchNiveauLocal(niveau.id, { epaisseur_dalle_mm: v, hauteur_mm: HSP + v });
    }
  };
  const commitED = (v: number) => {
    if (entryMode === 'hauteur') {
      onCommitNiveau(niveau.id, { epaisseur_dalle_mm: v, hauteur_sous_plafond_mm: HT - v });
    } else {
      onCommitNiveau(niveau.id, { epaisseur_dalle_mm: v, hauteur_mm: HSP + v });
    }
  };
  const updateHSP = (v: number) => {
    onPatchNiveauLocal(niveau.id, { hauteur_sous_plafond_mm: v, hauteur_mm: v + ED, entry_mode: 'hsp' });
  };
  const commitHSP = (v: number) => {
    onCommitNiveau(niveau.id, { hauteur_sous_plafond_mm: v, hauteur_mm: v + ED, entry_mode: 'hsp' });
  };

  const blondelOk = !!niveauCalc?.valid_blondel;
  const blondelVal = niveauCalc ? Math.round(niveauCalc.blondel_value) : 0;
  const marches = niveauCalc?.n_steps_niveau ?? 0;
  const h = niveauCalc?.h ?? 0;
  const g = niveauCalc?.g ?? 0;

  return (
    <View>
      <Text style={droitStyles.section}>HAUTEURS — SAISIE LIÉE</Text>
      <Text style={droitStyles.hint}>
        Saisissez 2 valeurs au choix ; la 3ᵉ se calcule auto. Le champ verrouillé est en gris.
      </Text>

      {/* Hauteur Totale */}
      <DroitField
        label="HAUTEUR TOTALE (HT)"
        hint="Du sol fini bas au sol fini haut"
        value={HTeff}
        locked={entryMode === 'hsp'}
        onTapLocked={switchEntryMode}
        onChange={updateHT}
        onCommit={commitHT}
        testID="droit-input-ht"
      />

      {/* Épaisseur Dalle */}
      <DroitField
        label="ÉPAISSEUR DALLE (ED)"
        hint="Plancher + revêtement de la dalle haute"
        value={ED}
        locked={false}
        onChange={updateED}
        onCommit={commitED}
        testID="droit-input-ed"
      />

      {/* Hauteur Sous Plafond */}
      <DroitField
        label="HAUTEUR SOUS PLAFOND (HSP)"
        hint="HT − ED · = espace utile sous dalle"
        value={HSP}
        locked={entryMode === 'hauteur'}
        onTapLocked={switchEntryMode}
        onChange={updateHSP}
        onCommit={commitHSP}
        testID="droit-input-hsp"
      />

      <Text style={[droitStyles.section, { marginTop: SP.lg }]}>EMPRISE AU SOL</Text>

      <DroitField
        label="LARGEUR D'ESCALIER"
        hint="Largeur utile de passage"
        value={Math.round(troncon.largeur_mm)}
        locked={false}
        onChange={(v) => onPatchTronconLocal(niveau.id, troncon.id, { largeur_mm: v })}
        onCommit={(v) => onCommitTroncon(niveau.id, troncon.id, { largeur_mm: v })}
        testID="droit-input-largeur"
      />

      <DroitField
        label="LONGUEUR (RECULEMENT)"
        hint="Emprise au sol entre départ et arrivée"
        value={Math.round(troncon.longueur_mm)}
        locked={false}
        onChange={(v) => onPatchTronconLocal(niveau.id, troncon.id, { longueur_mm: v })}
        onCommit={(v) => onCommitTroncon(niveau.id, troncon.id, { longueur_mm: v })}
        testID="droit-input-longueur"
      />

      {/* Validation Blondel — minimaliste */}
      {niveauCalc && (
        <View
          style={[droitStyles.blondelBox, blondelOk ? droitStyles.blondelOk : droitStyles.blondelWarn]}
          testID="droit-blondel"
        >
          <Ionicons
            name={blondelOk ? 'checkmark-circle' : 'warning'}
            size={20}
            color={blondelOk ? C.ACCENT : C.WARN}
          />
          <View style={{ flex: 1, marginLeft: SP.sm }}>
            <Text style={[droitStyles.blondelTitle, { color: blondelOk ? C.ACCENT : C.WARN }]}>
              {marches} marches · h {Math.round(h)} mm · g {Math.round(g)} mm
            </Text>
            <Text style={droitStyles.blondelHint}>
              Blondel 2h+g = {blondelVal} mm — {blondelOk ? 'OK (560-670)' : 'Hors plage 560-670'}
            </Text>
          </View>
        </View>
      )}
    </View>
  );
}

/** Champ numérique réutilisable avec état verrouillé (auto-calculé). */
function DroitField({
  label, hint, value, locked, onTapLocked, onChange, onCommit, testID,
}: {
  label: string;
  hint?: string;
  value: number;
  locked?: boolean;
  onTapLocked?: () => void;
  onChange: (v: number) => void;
  onCommit: (v: number) => void;
  testID?: string;
}) {
  return (
    <View style={droitStyles.field}>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
        <Text style={droitStyles.label}>{label}</Text>
        {locked && (
          <View style={droitStyles.lockBadge}>
            <Ionicons name="lock-closed" size={9} color={C.GRAY3} />
            <Text style={droitStyles.lockBadgeTxt}>AUTO</Text>
          </View>
        )}
      </View>
      {!!hint && <Text style={droitStyles.hint}>{hint}</Text>}
      <TouchableOpacity
        activeOpacity={locked ? 0.7 : 1}
        onPress={() => locked && onTapLocked && onTapLocked()}
        style={[droitStyles.inputRow, locked && droitStyles.inputRowLocked]}
      >
        <TextInput
          value={String(value)}
          onChangeText={(v) => !locked && onChange(Number(v) || 0)}
          onEndEditing={(e) => !locked && onCommit(Number(e.nativeEvent.text) || 0)}
          editable={!locked}
          selectTextOnFocus={!locked}
          keyboardType="numeric"
          style={[droitStyles.input, locked && droitStyles.inputLocked]}
          placeholderTextColor={C.GRAY3}
          testID={testID}
        />
        <Text style={droitStyles.unit}>mm</Text>
      </TouchableOpacity>
      {locked && (
        <Text style={droitStyles.lockHint}>Tap pour saisir cette valeur (l'autre deviendra auto)</Text>
      )}
    </View>
  );
}

const droitStyles = StyleSheet.create({
  section: { ...FONT.label, color: C.ACCENT, fontSize: 11, marginBottom: SP.sm, marginTop: SP.sm },
  field: { marginBottom: SP.lg },
  label: { ...FONT.label, fontSize: 11, marginBottom: 2 },
  hint: { ...FONT.small, fontSize: 11, marginBottom: SP.sm, color: C.GRAY3 },
  inputRow: {
    flexDirection: 'row', alignItems: 'center',
    backgroundColor: C.CARD, borderRadius: R.md,
    paddingHorizontal: SP.md, borderWidth: 1, borderColor: C.BORDER,
  },
  inputRowLocked: { backgroundColor: 'rgba(255,255,255,0.03)', borderColor: C.BORDER, opacity: 0.65 },
  input: { flex: 1, ...FONT.h3, fontSize: 18, color: C.WHITE, paddingVertical: 14 },
  inputLocked: { color: C.GRAY3, fontStyle: 'italic' as any },
  unit: { ...FONT.label, color: C.GRAY3, fontSize: 11 },
  lockBadge: {
    flexDirection: 'row', alignItems: 'center', gap: 2,
    paddingHorizontal: 5, paddingVertical: 1, borderRadius: R.pill,
    borderWidth: 1, borderColor: C.GRAY3, backgroundColor: 'transparent',
  },
  lockBadgeTxt: { ...FONT.label, fontSize: 8, color: C.GRAY3 },
  lockHint: { ...FONT.small, fontSize: 10, fontStyle: 'italic' as any, marginTop: 4, color: C.GRAY3 },
  blondelBox: {
    flexDirection: 'row', alignItems: 'center',
    padding: SP.md, borderRadius: R.md, borderWidth: 1, borderLeftWidth: 4,
    marginTop: SP.sm,
  },
  blondelOk: { backgroundColor: 'rgba(140,198,63,0.10)', borderColor: C.ACCENT },
  blondelWarn: { backgroundColor: 'rgba(245,158,11,0.10)', borderColor: C.WARN },
  blondelTitle: { ...FONT.h3, fontSize: 13 },
  blondelHint: { ...FONT.small, fontSize: 11, marginTop: 2 },
});

// ───────────────────────── NiveauCard ─────────────────────────

function NiveauCard({
  niveau, index, calc, viewMode, onPatchLocal, onCommit, onRemove,
  onAddTroncon, onPatchTronconLocal, onCommitTroncon, onRemoveTroncon,
}: {
  niveau: ApiNiveau;
  index: number;
  calc: any;
  viewMode: 'profile' | 'plan';
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
        <View style={[styles.niveauBadge, niveau.is_ghost && { backgroundColor: 'transparent', borderColor: C.GRAY3 }]}>
          <Text style={[styles.niveauNum, niveau.is_ghost && { color: C.GRAY3 }]}>{niveau.floor_index >= 0 ? `+${niveau.floor_index}` : niveau.floor_index}</Text>
        </View>
        <View style={{ flex: 1 }}>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
            <Text style={styles.niveauLabel}>{floorIndexToLabel(niveau.floor_index)}</Text>
            {niveau.is_ghost && (
              <View style={styles.ghostBadge}>
                <Ionicons name="eye-off-outline" size={11} color={C.GRAY3} />
                <Text style={styles.ghostBadgeTxt}>FANTÔME</Text>
              </View>
            )}
          </View>
          {!niveau.is_ghost && calc && (
            <Text style={styles.niveauMeta}>
              {calc.n_steps_niveau} marche{calc.n_steps_niveau > 1 ? 's' : ''} ·
              h {Math.round(calc.h)} mm · g {Math.round(calc.g)} mm
              {!calc.valid_blondel ? '  ⚠' : ''}
            </Text>
          )}
          {niveau.is_ghost && (
            <Text style={styles.niveauMeta}>Pas d'escalier à ce niveau · H {Math.round(niveau.hauteur_mm)} mm</Text>
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

          {/* Croquis pédagogique du niveau (Profil ou Plan selon viewMode) */}
          {!niveau.is_ghost && niveau.troncons.length > 0 && calc && (
            viewMode === 'profile'
              ? <NiveauSketch niveau={niveau} calc={calc} />
              : <NiveauPlanSketch niveau={niveau} calc={calc} />
          )}

          {niveau.is_ghost ? (
            <View style={styles.ghostNotice}>
              <Ionicons name="information-circle-outline" size={18} color={C.GRAY3} />
              <Text style={styles.ghostNoticeTxt}>
                Niveau « Pas d'escalier ici ». La hauteur compte dans le total mais aucun tronçon n'est rendu.
                Utile pour maintenir la continuité des niveaux.
              </Text>
            </View>
          ) : (
            <>
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
            </>
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

// ───────────────────────── NiveauPlanSketch (vue de dessus, multi-tronçons) ─────────────────────────

function NiveauPlanSketch({ niveau, calc }: { niveau: ApiNiveau; calc: any }) {
  const W = 320, H = 220;
  const PAD = 24;

  // Walk tronçons, tracking position & direction. dir 0=right, 1=up, 2=left, 3=down.
  // quart_bas turns right (clockwise from top-down) and quart_haut turns left.
  // We compute the path in mm-space first, then scale to fit bounding box.
  type Cell = {
    troncon: ApiTroncon;
    n_marches: number;
    x: number; y: number;     // origin of segment (axis along direction)
    dir: number;              // direction along which the segment extends (length)
    perp: number;             // direction of width (perpendicular)
    longueur: number;
    largeur: number;
  };

  const cells: Cell[] = [];
  let x = 0, y = 0, dir = 0; // start: facing right
  const turn = (d: number, k: number) => (d + k + 4) % 4;
  const dx = [1, 0, -1, 0];
  const dy = [0, -1, 0, 1];

  niveau.troncons.forEach(t => {
    const tCalc = calc?.troncons_calc?.find((c: any) => c.troncon_id === t.id);
    const L = t.longueur_mm || 0;
    const W_t = t.largeur_mm || 900;
    const perp = turn(dir, 1); // perpendicular = 90° CCW

    if (t.type === 'quart_bas') {
      // Quarter-turn going RIGHT (clockwise from above)
      cells.push({ troncon: t, n_marches: tCalc?.n_marches ?? 0, x, y, dir, perp, longueur: L, largeur: W_t });
      // Advance to end of segment
      x += dx[dir] * L;
      y += dy[dir] * L;
      dir = turn(dir, -1); // turn right (CW)
    } else if (t.type === 'quart_haut') {
      cells.push({ troncon: t, n_marches: tCalc?.n_marches ?? 0, x, y, dir, perp, longueur: L, largeur: W_t });
      x += dx[dir] * L;
      y += dy[dir] * L;
      dir = turn(dir, 1); // turn left (CCW)
    } else {
      cells.push({ troncon: t, n_marches: tCalc?.n_marches ?? 0, x, y, dir, perp, longueur: L, largeur: W_t });
      x += dx[dir] * L;
      y += dy[dir] * L;
    }
  });

  // Compute bounding box (consider both length-extent and perpendicular width)
  let minX = 0, maxX = 0, minY = 0, maxY = 0;
  cells.forEach(c => {
    const ex = c.x + dx[c.dir] * c.longueur;
    const ey = c.y + dy[c.dir] * c.longueur;
    // Perpendicular extent (centered)
    const px1 = c.x + dx[c.perp] * (c.largeur / 2);
    const py1 = c.y + dy[c.perp] * (c.largeur / 2);
    const px2 = c.x - dx[c.perp] * (c.largeur / 2);
    const py2 = c.y - dy[c.perp] * (c.largeur / 2);
    [c.x, ex, px1, px2].forEach(xx => { minX = Math.min(minX, xx); maxX = Math.max(maxX, xx); });
    [c.y, ey, py1, py2].forEach(yy => { minY = Math.min(minY, yy); maxY = Math.max(maxY, yy); });
  });
  const bboxW = Math.max(maxX - minX, 1);
  const bboxH = Math.max(maxY - minY, 1);
  const scale = Math.min((W - PAD * 2) / bboxW, (H - PAD * 2) / bboxH);
  // Center
  const ox = PAD + (W - PAD * 2 - bboxW * scale) / 2 - minX * scale;
  const oy = PAD + (H - PAD * 2 - bboxH * scale) / 2 - minY * scale;
  const tx = (xx: number) => ox + xx * scale;
  const ty = (yy: number) => oy + yy * scale;

  return (
    <View style={{ alignItems: 'center', marginTop: SP.md, marginBottom: SP.sm }}>
      <Svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}>
        <Rect x={0} y={0} width={W} height={H} fill={C.BG_DEEPER} rx={10} />
        {cells.map((c, i) => {
          const isPalier = c.troncon.type === 'palier';
          const isQuart = c.troncon.type === 'quart_bas' || c.troncon.type === 'quart_haut';
          // Compute 4 corners of the segment rectangle
          const px = dx[c.perp] * (c.largeur / 2);
          const py = dy[c.perp] * (c.largeur / 2);
          const ex = c.x + dx[c.dir] * c.longueur;
          const ey = c.y + dy[c.dir] * c.longueur;
          const pts = [
            `${tx(c.x + px)},${ty(c.y + py)}`,
            `${tx(ex + px)},${ty(ey + py)}`,
            `${tx(ex - px)},${ty(ey - py)}`,
            `${tx(c.x - px)},${ty(c.y - py)}`,
          ].join(' ');
          const fillColor = isPalier ? 'rgba(91,168,199,0.15)' : isQuart ? 'rgba(245,158,11,0.12)' : 'rgba(140,198,63,0.10)';
          const strokeColor = isPalier ? '#5BA8C7' : isQuart ? C.WARN : C.ACCENT;

          // Step lines (nez de marche) — only for marche tronçons
          const stepLines = [];
          if (!isPalier && c.n_marches > 1) {
            const step = c.longueur / c.n_marches;
            for (let k = 1; k < c.n_marches; k++) {
              const sx = c.x + dx[c.dir] * step * k;
              const sy = c.y + dy[c.dir] * step * k;
              stepLines.push(
                <Line
                  key={`step-${i}-${k}`}
                  x1={tx(sx + px)} y1={ty(sy + py)}
                  x2={tx(sx - px)} y2={ty(sy - py)}
                  stroke={strokeColor} strokeWidth={0.8} opacity={0.7}
                />,
              );
            }
          }

          // Label center
          const cxr = (c.x + ex) / 2;
          const cyr = (c.y + ey) / 2;
          const label = isPalier ? 'PALIER' :
            c.troncon.type === 'quart_bas' ? '↻ BAS' :
            c.troncon.type === 'quart_haut' ? '↺ HAUT' :
            `${c.n_marches} m`;

          return (
            <G key={c.troncon.id}>
              <Polygon points={pts} fill={fillColor} stroke={strokeColor} strokeWidth={1.5} />
              {stepLines}
              <SvgText
                x={tx(cxr)} y={ty(cyr) + 3}
                fontSize={9} fill={strokeColor} textAnchor="middle" fontWeight="bold"
              >
                {label}
              </SvgText>
            </G>
          );
        })}

        {/* Start arrow (montée) */}
        {cells.length > 0 && (
          <G>
            <Circle cx={tx(0)} cy={ty(0)} r={5} fill={C.ACCENT} />
            <SvgText
              x={tx(0)} y={ty(0) - 8}
              fontSize={8} fill={C.ACCENT} textAnchor="middle" fontWeight="bold"
            >
              ↑ DÉPART
            </SvgText>
          </G>
        )}

        {/* Compass (top-right) */}
        <G x={W - 30} y={20}>
          <Circle cx={0} cy={0} r={11} fill="transparent" stroke={C.GRAY3} strokeWidth={0.8} />
          <Line x1={0} y1={-8} x2={0} y2={8} stroke={C.GRAY3} strokeWidth={0.6} />
          <Line x1={-8} y1={0} x2={8} y2={0} stroke={C.GRAY3} strokeWidth={0.6} />
          <SvgText x={0} y={-13} fontSize={7} fill={C.GRAY3} textAnchor="middle">N</SvgText>
        </G>
      </Svg>
      <Text style={styles.sketchLegend}>
        Vue en plan — vert: marches · bleu: palier · orange: quart-tournant
      </Text>
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

  // View mode toggle (Profile / Plan)
  viewToggle: { flexDirection: 'row', backgroundColor: C.CARD, borderRadius: R.pill, padding: 3, marginBottom: SP.md, borderWidth: 1, borderColor: C.BORDER },
  viewToggleBtn: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, paddingVertical: 8, borderRadius: R.pill },
  viewToggleBtnActive: { backgroundColor: C.ACCENT },
  viewToggleTxt: { ...FONT.label, color: C.GRAY3, fontSize: 11 },
  viewToggleTxtActive: { color: C.DARK },

  // Add niveau row (regular + ghost)
  addNivRow: { flexDirection: 'row', gap: SP.sm, marginTop: SP.md },
  addGhostBtn: { backgroundColor: 'transparent', borderColor: C.BORDER, borderStyle: 'dashed' as any },
  ghostBadge: {
    flexDirection: 'row', alignItems: 'center', gap: 4,
    paddingHorizontal: 6, paddingVertical: 2, borderRadius: R.pill,
    borderWidth: 1, borderColor: C.GRAY3, backgroundColor: 'transparent',
  },
  ghostBadgeTxt: { ...FONT.label, fontSize: 9, color: C.GRAY3 },
  ghostNotice: {
    flexDirection: 'row', alignItems: 'flex-start', gap: SP.sm, padding: SP.md,
    backgroundColor: C.BG_DEEPER, borderRadius: R.md, marginTop: SP.md,
    borderLeftWidth: 3, borderLeftColor: C.GRAY3,
  },
  ghostNoticeTxt: { ...FONT.small, flex: 1, lineHeight: 18, fontSize: 11 },

  // DÉTAILS DE LA SAISIE (recap)
  recapCard: {
    backgroundColor: C.CARD, borderRadius: R.lg, padding: SP.lg,
    borderWidth: 1, borderColor: C.ACCENT, borderLeftWidth: 3,
    marginTop: SP.lg,
  },
  recapTitle: { ...FONT.label, color: C.ACCENT, marginBottom: SP.md, fontSize: 11 },
  recapRow: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingVertical: 6,
  },
  recapKey: { ...FONT.small, fontSize: 12, color: C.GRAY3, flex: 1 },
  recapVal: { ...FONT.body, fontSize: 13, color: C.WHITE, fontWeight: '600' },
  recapDivider: { height: 1, backgroundColor: C.BORDER, marginVertical: SP.sm },
  recapNivBlock: {
    paddingVertical: SP.sm, borderBottomWidth: 1, borderBottomColor: C.BORDER,
  },
  recapNivTitle: { ...FONT.h3, fontSize: 13, color: C.ACCENT, marginBottom: 4 },
  recapNivLine: { ...FONT.small, fontSize: 11, lineHeight: 16, marginTop: 2 },

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
