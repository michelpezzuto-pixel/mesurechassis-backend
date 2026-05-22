import React, { useEffect, useState, useCallback } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity, Alert, ActivityIndicator, Modal, TextInput, KeyboardAvoidingView, Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, useRouter, useFocusEffect } from 'expo-router';
import { Ionicons, MaterialCommunityIcons, Feather } from '@expo/vector-icons';
import { Projects, Stairs, ApiStair } from '@/src/api';
import { useAuth } from '@/src/auth';
import { C, SP, R, FONT, STATUS_LABELS, STATUS_COLOR } from '@/src/theme';

/**
 * PROJECT DETAIL v2 — Chantier = client + liste d'escaliers.
 * Plus de wizard direct : on clique "AJOUTER UN ESCALIER" → modal nom → écran éditeur.
 */
export default function ProjectDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const { user } = useAuth();
  const [project, setProject] = useState<any>(null);
  const [stairs, setStairs] = useState<ApiStair[]>([]);
  const [loading, setLoading] = useState(true);
  const [addOpen, setAddOpen] = useState(false);
  const [newStairName, setNewStairName] = useState('');
  const [newStairShape, setNewStairShape] = useState<'droit' | 'tournant'>('tournant');
  const [creating, setCreating] = useState(false);

  const load = useCallback(async () => {
    if (!id) return;
    try {
      const [p, s] = await Promise.all([
        Projects.get(id),
        Stairs.list(id),
      ]);
      setProject(p);
      setStairs(s);
    } catch (e: any) {
      Alert.alert('Erreur', e?.response?.data?.detail || 'Introuvable');
      router.back();
    } finally { setLoading(false); }
  }, [id, router]);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  const canEdit = !project?.locked && (user?.role === 'admin' || user?.solo_mode || project?.technicien_id === user?.id);
  const canDelete = user?.role === 'admin' && !project?.locked;

  const transmit = async () => {
    Alert.alert('Transmettre au technicien', 'Le chantier sera verrouillé.', [
      { text: 'Annuler', style: 'cancel' },
      {
        text: 'Confirmer', style: 'destructive', onPress: async () => {
          try { await Projects.transmit(id!); load(); } catch (e: any) { Alert.alert('Erreur', e?.response?.data?.detail || 'Erreur'); }
        },
      },
    ]);
  };

  const remove = async () => {
    Alert.alert('Supprimer le chantier ?', 'Action irréversible.', [
      { text: 'Annuler', style: 'cancel' },
      {
        text: 'Supprimer', style: 'destructive', onPress: async () => {
          try { await Projects.remove(id!); router.replace('/dashboard'); } catch (e: any) { Alert.alert('Erreur', e?.response?.data?.detail || 'Erreur'); }
        },
      },
    ]);
  };

  const openAddStair = () => { setNewStairName(''); setNewStairShape('tournant'); setAddOpen(true); };

  const createStair = async () => {
    const name = newStairName.trim() || `Escalier ${stairs.length + 1}`;
    setCreating(true);
    try {
      const s = await Stairs.create(id!, { name, shape: newStairShape });
      setStairs([...stairs, s]);
      setAddOpen(false);
      // Navigation directe vers l'éditeur
      router.push(`/projects/${id}/stairs/${s.id}` as any);
    } catch (e: any) {
      Alert.alert('Erreur', e?.response?.data?.detail || 'Création impossible');
    } finally { setCreating(false); }
  };

  const removeStair = (s: ApiStair) => {
    Alert.alert(`Supprimer "${s.name}" ?`, 'Tous ses niveaux et tronçons seront perdus.', [
      { text: 'Annuler', style: 'cancel' },
      {
        text: 'Supprimer', style: 'destructive', onPress: async () => {
          try { await Stairs.remove(id!, s.id); setStairs(stairs.filter(x => x.id !== s.id)); } catch (e: any) { Alert.alert('Erreur', e?.response?.data?.detail || 'Erreur'); }
        },
      },
    ]);
  };

  if (loading || !project) {
    return (
      <SafeAreaView style={[styles.safe, { justifyContent: 'center', alignItems: 'center' }]}>
        <ActivityIndicator color={C.ACCENT} size="large" />
      </SafeAreaView>
    );
  }

  const clientFullName = `${project.client_nom} ${project.client_prenom || ''}`.trim();

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
        {/* Hero client */}
        <View style={styles.heroClient}>
          <Text style={styles.heroLabel}>CLIENT</Text>
          <Text style={styles.heroName} numberOfLines={2}>{clientFullName.toUpperCase()}</Text>
          {!!project.address && (
            <View style={styles.heroAddr}>
              <Ionicons name="location-sharp" size={14} color={C.GRAY3} />
              <Text style={styles.heroAddrTxt} numberOfLines={2}>
                {project.address}{project.city ? `, ${project.city}` : ''}
              </Text>
            </View>
          )}
          <View style={[styles.badge, { backgroundColor: STATUS_COLOR[project.status] + '22', borderColor: STATUS_COLOR[project.status] }]}>
            <Text style={[styles.badgeTxt, { color: STATUS_COLOR[project.status] }]}>{STATUS_LABELS[project.status]}</Text>
            {project.locked && <Ionicons name="lock-closed" size={11} color={STATUS_COLOR[project.status]} style={{ marginLeft: 6 }} />}
          </View>
        </View>

        {!!project.phone && (
          <View style={styles.card}>
            <Text style={styles.cardHead}>COORDONNÉES</Text>
            <View style={styles.row}>
              <Ionicons name="call" size={16} color={C.ACCENT} />
              <Text style={styles.rowValue}>{project.phone}</Text>
            </View>
            {!!project.notes && (
              <View style={styles.row}>
                <Ionicons name="document-text" size={16} color={C.ACCENT} />
                <Text style={styles.rowValue}>{project.notes}</Text>
              </View>
            )}
          </View>
        )}

        {/* Escaliers du chantier */}
        <View style={styles.sectionHead}>
          <Text style={styles.section}>ESCALIERS DU CHANTIER</Text>
          <Text style={styles.sectionCount}>{stairs.length}</Text>
        </View>

        {stairs.length === 0 ? (
          <View style={styles.empty}>
            <MaterialCommunityIcons name="stairs-up" size={56} color={C.GRAY3} />
            <Text style={styles.emptyTitle}>Aucun escalier</Text>
            <Text style={styles.emptyHint}>Ajoutez votre premier escalier ci-dessous, donnez-lui un nom (ex. Cave-to-RDC), puis configurez ses niveaux et tronçons.</Text>
          </View>
        ) : (
          stairs.map(s => (
            <TouchableOpacity
              key={s.id}
              style={styles.stairCard}
              onPress={() => router.push(`/projects/${id}/stairs/${s.id}` as any)}
              testID={`stair-${s.id}`}
            >
              <View style={styles.stairIcon}>
                <MaterialCommunityIcons name="stairs" size={28} color={C.ACCENT} />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.stairName} numberOfLines={1}>{s.name}</Text>
                <Text style={styles.stairMeta}>
                  {s.niveaux.length} niveau{s.niveaux.length > 1 ? 'x' : ''} ·{' '}
                  {s.niveaux.reduce((sum, n) => sum + (n.troncons?.length || 0), 0)} tronçons
                </Text>
              </View>
              {canEdit && (
                <TouchableOpacity onPress={() => removeStair(s)} hitSlop={10} testID={`del-stair-${s.id}`}>
                  <Feather name="trash-2" size={18} color={C.DANGER} />
                </TouchableOpacity>
              )}
              <Ionicons name="chevron-forward" size={20} color={C.GRAY3} />
            </TouchableOpacity>
          ))
        )}

        {canEdit && (
          <TouchableOpacity style={styles.addBtn} onPress={openAddStair} testID="btn-add-stair">
            <Ionicons name="add-circle" size={22} color={C.DARK} />
            <Text style={styles.addBtnTxt}>AJOUTER UN ESCALIER</Text>
          </TouchableOpacity>
        )}

        {stairs.length > 0 && canEdit && (
          <TouchableOpacity style={styles.exportBtn} onPress={() => router.push(`/projects/${id}/export` as any)} testID="btn-export">
            <Ionicons name="share-outline" size={18} color={C.WHITE} />
            <Text style={styles.exportBtnTxt}>EXPORTER LES LIVRABLES</Text>
          </TouchableOpacity>
        )}

        {canEdit && !project.locked && (
          <TouchableOpacity style={styles.photosBtn} onPress={() => router.push(`/projects/${id}/photos` as any)}>
            <Ionicons name="camera" size={18} color={C.WHITE} />
            <Text style={styles.exportBtnTxt}>PHOTOS DE CHANTIER</Text>
          </TouchableOpacity>
        )}

        {user?.role === 'admin' && !project.locked && project.status !== 'valide' && stairs.length > 0 && (
          <TouchableOpacity style={styles.transmitBtn} onPress={transmit}>
            <Ionicons name="paper-plane" size={18} color={C.WHITE} />
            <Text style={styles.exportBtnTxt}>TRANSMETTRE AU TECHNICIEN</Text>
          </TouchableOpacity>
        )}
      </ScrollView>

      {/* Modal "Nom de l'escalier" */}
      <Modal visible={addOpen} transparent animationType="fade" onRequestClose={() => setAddOpen(false)}>
        <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.modalBg}>
          <View style={styles.modalCard}>
            <View style={styles.modalHead}>
              <MaterialCommunityIcons name="stairs-up" size={22} color={C.ACCENT} />
              <Text style={styles.modalTitle}>NOM DE L'ESCALIER</Text>
              <TouchableOpacity onPress={() => setAddOpen(false)}><Ionicons name="close" size={22} color={C.WHITE} /></TouchableOpacity>
            </View>
            <Text style={styles.modalHint}>
              Donne un nom clair pour identifier cet escalier (ex. Cave-to-RDC, Escalier principal, Mezzanine…)
            </Text>
            <TextInput
              value={newStairName}
              onChangeText={setNewStairName}
              placeholder="Cave-to-RDC"
              placeholderTextColor={C.GRAY3}
              style={styles.modalInput}
              autoFocus
              maxLength={60}
              onSubmitEditing={createStair}
              returnKeyType="done"
              testID="input-new-stair-name"
            />

            {/* Shape selector — DROIT (simplifié) vs TOURNANT (multi-niveaux) */}
            <Text style={styles.modalSubLabel}>FORME DE L'ESCALIER</Text>
            <View style={styles.shapeRow}>
              <TouchableOpacity
                style={[styles.shapeBtn, newStairShape === 'droit' && styles.shapeBtnActive]}
                onPress={() => setNewStairShape('droit')}
                testID="shape-droit"
              >
                <MaterialCommunityIcons
                  name="arrow-top-right"
                  size={24}
                  color={newStairShape === 'droit' ? C.DARK : C.GRAY3}
                />
                <Text style={[styles.shapeTitle, newStairShape === 'droit' && { color: C.DARK }]}>DROIT</Text>
                <Text style={[styles.shapeHint, newStairShape === 'droit' && { color: C.DARK, opacity: 0.7 }]}>
                  1 volée linéaire
                </Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.shapeBtn, newStairShape === 'tournant' && styles.shapeBtnActive]}
                onPress={() => setNewStairShape('tournant')}
                testID="shape-tournant"
              >
                <MaterialCommunityIcons
                  name="rotate-3d-variant"
                  size={24}
                  color={newStairShape === 'tournant' ? C.DARK : C.GRAY3}
                />
                <Text style={[styles.shapeTitle, newStairShape === 'tournant' && { color: C.DARK }]}>TOURNANT</Text>
                <Text style={[styles.shapeHint, newStairShape === 'tournant' && { color: C.DARK, opacity: 0.7 }]}>
                  Niveaux & tronçons
                </Text>
              </TouchableOpacity>
            </View>
            <View style={{ flexDirection: 'row', gap: SP.sm, marginTop: SP.md }}>
              <TouchableOpacity style={[styles.modalBtn, styles.modalBtnGhost]} onPress={() => setAddOpen(false)}>
                <Text style={[styles.modalBtnTxt, { color: C.WHITE }]}>ANNULER</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.modalBtn, styles.modalBtnPrimary, creating && { opacity: 0.6 }]}
                onPress={createStair}
                disabled={creating}
                testID="btn-create-stair"
              >
                {creating ? <ActivityIndicator color={C.DARK} /> : <Text style={styles.modalBtnTxt}>CRÉER</Text>}
              </TouchableOpacity>
            </View>
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: C.DARK },
  topbar: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', padding: SP.lg, borderBottomWidth: 1, borderBottomColor: C.BORDER, gap: SP.md },
  topbarTitle: { ...FONT.label, color: C.GRAY3, flex: 1, textAlign: 'center', fontSize: 12 },
  // Hero
  heroClient: { backgroundColor: C.CARD, borderRadius: R.lg, padding: SP.lg, borderLeftWidth: 4, borderLeftColor: C.ACCENT, marginBottom: SP.md },
  heroLabel: { ...FONT.label, color: C.ACCENT, fontSize: 11, marginBottom: 4 },
  heroName: { ...FONT.h1, fontSize: 24, letterSpacing: 0.5, lineHeight: 30 },
  heroAddr: { flexDirection: 'row', alignItems: 'center', gap: 4, marginTop: SP.sm },
  heroAddrTxt: { ...FONT.small, flex: 1 },
  badge: { alignSelf: 'flex-start', flexDirection: 'row', alignItems: 'center', paddingHorizontal: SP.md, paddingVertical: 6, borderRadius: R.pill, borderWidth: 1, marginTop: SP.md },
  badgeTxt: { ...FONT.label, fontSize: 11 },

  card: { backgroundColor: C.CARD, borderRadius: R.lg, padding: SP.lg, borderWidth: 1, borderColor: C.BORDER, marginBottom: SP.md },
  cardHead: { ...FONT.label, color: C.ACCENT, marginBottom: SP.md },
  row: { flexDirection: 'row', alignItems: 'center', gap: SP.sm, marginBottom: SP.sm },
  rowValue: { ...FONT.body, flex: 1 },

  sectionHead: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: SP.md, marginTop: SP.md },
  section: { ...FONT.label, color: C.ACCENT },
  sectionCount: { ...FONT.label, color: C.GRAY3 },

  empty: { alignItems: 'center', padding: SP.xl, backgroundColor: C.CARD, borderRadius: R.lg, borderWidth: 1, borderColor: C.BORDER, borderStyle: 'dashed' as any, marginBottom: SP.md },
  emptyTitle: { ...FONT.h3, marginTop: SP.md },
  emptyHint: { ...FONT.small, textAlign: 'center', marginTop: SP.sm, lineHeight: 19, paddingHorizontal: SP.md },

  stairCard: { flexDirection: 'row', alignItems: 'center', gap: SP.md, backgroundColor: C.CARD, borderRadius: R.lg, padding: SP.md, borderWidth: 1, borderColor: C.BORDER, marginBottom: SP.sm },
  stairIcon: { width: 48, height: 48, borderRadius: R.md, backgroundColor: C.ACCENT_BG, borderWidth: 1, borderColor: C.ACCENT, alignItems: 'center', justifyContent: 'center' },
  stairName: { ...FONT.h3, fontSize: 15 },
  stairMeta: { ...FONT.small, fontSize: 11, marginTop: 2 },

  addBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: SP.sm, backgroundColor: C.ACCENT, paddingVertical: 16, borderRadius: R.md, marginTop: SP.md },
  addBtnTxt: { ...FONT.button, color: C.DARK, fontSize: 13, letterSpacing: 1 },

  exportBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: SP.sm, backgroundColor: C.CARD, borderWidth: 1, borderColor: C.BORDER, paddingVertical: 14, borderRadius: R.md, marginTop: SP.md },
  exportBtnTxt: { ...FONT.button, color: C.WHITE, fontSize: 12 },
  photosBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: SP.sm, backgroundColor: C.CARD, borderWidth: 1, borderColor: C.BORDER, paddingVertical: 14, borderRadius: R.md, marginTop: SP.sm },
  transmitBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: SP.sm, backgroundColor: C.WARN, paddingVertical: 14, borderRadius: R.md, marginTop: SP.md },

  // Modal
  modalBg: { flex: 1, backgroundColor: 'rgba(0,0,0,0.7)', alignItems: 'center', justifyContent: 'center', padding: SP.lg },
  modalCard: { backgroundColor: C.CARD, borderRadius: R.lg, padding: SP.lg, width: '100%', maxWidth: 420, borderWidth: 1, borderColor: C.ACCENT },
  modalHead: { flexDirection: 'row', alignItems: 'center', gap: SP.sm, marginBottom: SP.md },
  modalTitle: { ...FONT.h3, fontSize: 14, flex: 1 },
  modalHint: { ...FONT.small, lineHeight: 18, marginBottom: SP.md },
  modalInput: { backgroundColor: C.BG_DEEPER, borderWidth: 1, borderColor: C.BORDER, borderRadius: R.md, padding: SP.md, color: C.WHITE, fontSize: 16 },
  modalBtn: { flex: 1, paddingVertical: 14, borderRadius: R.md, alignItems: 'center' },
  modalBtnGhost: { backgroundColor: 'transparent', borderWidth: 1, borderColor: C.BORDER },
  modalBtnPrimary: { backgroundColor: C.ACCENT },
  modalBtnTxt: { ...FONT.button, color: C.DARK, fontSize: 13 },

  // Shape selector inside modal
  modalSubLabel: { ...FONT.label, color: C.ACCENT, fontSize: 11, marginTop: SP.md },
  shapeRow: { flexDirection: 'row', gap: SP.sm, marginTop: SP.sm },
  shapeBtn: {
    flex: 1,
    paddingVertical: 14,
    paddingHorizontal: 8,
    backgroundColor: C.BG_DEEPER,
    borderRadius: R.md,
    borderWidth: 1,
    borderColor: C.BORDER,
    alignItems: 'center',
    gap: 4,
  },
  shapeBtnActive: { backgroundColor: C.ACCENT, borderColor: C.ACCENT },
  shapeTitle: { ...FONT.button, color: C.WHITE, fontSize: 12, marginTop: 4 },
  shapeHint: { ...FONT.small, fontSize: 10, color: C.GRAY3, textAlign: 'center' },
});
