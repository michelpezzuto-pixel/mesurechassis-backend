import React, { useEffect, useState, useCallback } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity, Alert, ActivityIndicator, Modal, TextInput, KeyboardAvoidingView, Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, useRouter, useFocusEffect } from 'expo-router';
import { Ionicons, MaterialCommunityIcons, Feather } from '@expo/vector-icons';
import Svg, { Line, Polyline, Path, Polygon, Rect, Circle, Text as SvgText, G } from 'react-native-svg';
import { Projects, Stairs, ApiStair, StairShape } from '@/src/api';
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
  const [newStairShape, setNewStairShape] = useState<'droit' | 'quart_tournant' | 'demi_tournant' | 'helicoidal' | null>(null);
  const [niveauFini, setNiveauFini] = useState(true);
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

  // ⚠️ Règle d'édition :
  //   - ADMIN : toujours autorisé (même sur projet verrouillé) → peut intervenir partout.
  //   - SOLO MODE : autorisé tant que le projet n'est pas verrouillé.
  //   - TECHNICIEN ASSIGNÉ : autorisé tant que le projet n'est pas verrouillé.
  //   - AUTRES : interdits.
  const isAdmin = user?.role === 'admin';
  const canEdit = isAdmin || (!project?.locked && (user?.solo_mode || project?.technicien_id === user?.id));
  const canDelete = isAdmin;  // Admin peut toujours supprimer; les autres jamais.
  const canUnlock = isAdmin && !!project?.locked;

  const unlockProject = () => {
    Alert.alert(
      'Déverrouiller le chantier ?',
      'Le chantier repassera en statut Brouillon et redeviendra modifiable.',
      [
        { text: 'Annuler', style: 'cancel' },
        {
          text: 'Déverrouiller', onPress: async () => {
            try { await Projects.unlock(id!); load(); }
            catch (e: any) { Alert.alert('Erreur', e?.response?.data?.detail || 'Erreur'); }
          },
        },
      ],
    );
  };

  const transmit = async () => {
    Alert.alert('Transmettre au technicien', 'Le chantier sera verrouillé.', [
      { text: 'Annuler', style: 'cancel' },
      {
        text: 'Confirmer', style: 'destructive', onPress: async () => {
          try { await Projects.transmit(id!); load(); } catch (e: any) { Alert.alert('Erreur', e?.response?.data?.detail || 'Erreur'); }        },
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

  const openAddStair = () => {
    setNewStairName('');
    setNewStairShape(null);
    setNiveauFini(true);
    setAddOpen(true);
  };

  const createStair = async () => {
    if (!newStairShape) {
      Alert.alert('Sélection requise', 'Choisissez d\'abord une forme d\'escalier.');
      return;
    }
    if (newStairShape === 'helicoidal') {
      Alert.alert('Bientôt disponible', "L'escalier hélicoïdal sera disponible dans une prochaine mise à jour.");
      return;
    }
    const name = newStairName.trim() || `Escalier ${stairs.length + 1}`;
    setCreating(true);
    try {
      const s = await Stairs.create(id!, { name, shape: newStairShape as StairShape });
      // Pour DROIT, mettre à jour le niveau RDC auto-créé si NIVEAU FINI décoché
      if (newStairShape === 'droit' && !niveauFini && s.niveaux[0]) {
        await Stairs.updateNiveau(id!, s.id, s.niveaux[0].id, { sol_fini: false });
        s.niveaux[0].sol_fini = false;
      }
      setStairs([...stairs, s]);
      setAddOpen(false);
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
          <View style={styles.empty} testID="empty-no-stair">
            <MaterialCommunityIcons name="stairs-up" size={56} color={C.ACCENT} />
            <Text style={styles.emptyTitle}>Aucun escalier</Text>
            <Text style={styles.emptyHint}>
              Ajoutez votre premier escalier : choisissez la forme (Droit, 1/4 T, 2/4 T, Hélicoïdal),
              donnez-lui un nom (ex. Cave-to-RDC), puis configurez ses niveaux.
            </Text>
            {canEdit && (
              <TouchableOpacity
                style={styles.emptyCta}
                onPress={openAddStair}
                testID="btn-add-first-stair"
                activeOpacity={0.8}
              >
                <Ionicons name="add-circle" size={22} color={C.DARK} />
                <Text style={styles.emptyCtaTxt}>AJOUTER MON PREMIER ESCALIER</Text>
              </TouchableOpacity>
            )}
            {!canEdit && (
              <View style={styles.emptyLocked}>
                <Ionicons name="lock-closed" size={14} color={C.WARN} />
                <Text style={styles.emptyLockedTxt}>
                  Chantier verrouillé — déverrouillage admin nécessaire pour ajouter un escalier.
                </Text>
              </View>
            )}
            {canUnlock && (
              <TouchableOpacity
                style={styles.emptyUnlockCta}
                onPress={unlockProject}
                testID="btn-unlock-project"
                activeOpacity={0.8}
              >
                <Ionicons name="lock-open" size={18} color={C.DARK} />
                <Text style={styles.emptyCtaTxt}>DÉVERROUILLER CE CHANTIER</Text>
              </TouchableOpacity>
            )}
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
          <TouchableOpacity
            style={styles.exportBtn}
            onPress={() => router.push(`/projects/${id}/stairs/${stairs[0].id}/export` as any)}
            testID="btn-export"
          >
            <Ionicons name="share-outline" size={18} color={C.WHITE} />
            <Text style={styles.exportBtnTxt}>
              {stairs.length === 1
                ? 'EXPORTER LES LIVRABLES'
                : `EXPORTER (${stairs[0].name.toUpperCase()})`}
            </Text>
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

      {/* FAB "+" floating add stair (visible when canEdit, always reachable) */}
      {canEdit && !addOpen && (
        <TouchableOpacity
          style={styles.fab}
          onPress={openAddStair}
          testID="fab-add-stair"
          activeOpacity={0.85}
        >
          <Ionicons name="add" size={32} color={C.DARK} />
        </TouchableOpacity>
      )}

      {/* Modal "Aucun escalier" — choix forme + nom (UI image_42 style fiches techniques) */}
      <Modal visible={addOpen} transparent animationType="fade" onRequestClose={() => setAddOpen(false)}>
        <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.modalBg}>
          <View style={styles.modalCardBig}>
            <View style={styles.modalHead}>
              <View>
                <Text style={styles.modalKicker}>{project?.client_nom?.toUpperCase()} {project?.client_prenom || ''}</Text>
                <Text style={styles.modalTitleBig}>AUCUN ESCALIER</Text>
              </View>
              <TouchableOpacity onPress={() => setAddOpen(false)} hitSlop={10}>
                <Ionicons name="close" size={22} color={C.WHITE} />
              </TouchableOpacity>
            </View>

            <Text style={styles.modalHint}>
              Sélectionnez la forme · attribuez un nom · puis configurez.
            </Text>

            <ScrollView style={{ flexGrow: 0, maxHeight: 460 }} contentContainerStyle={{ paddingBottom: SP.sm }}>
              {/* Grille 2×2 de fiches techniques */}
              <View style={styles.cardsGrid}>
                <ShapeCardDroit
                  active={newStairShape === 'droit'}
                  onPress={() => setNewStairShape('droit')}
                  niveauFini={niveauFini}
                  onToggleNiveauFini={() => setNiveauFini(!niveauFini)}
                />
                <ShapeCardQuart
                  active={newStairShape === 'quart_tournant'}
                  onPress={() => setNewStairShape('quart_tournant')}
                />
                <ShapeCardDemi
                  active={newStairShape === 'demi_tournant'}
                  onPress={() => setNewStairShape('demi_tournant')}
                />
                <ShapeCardHelico
                  onPress={() => Alert.alert('Bientôt disponible', "L'escalier hélicoïdal sera disponible dans une prochaine mise à jour.")}
                />
              </View>

              {/* Nom de l'escalier */}
              <Text style={styles.modalSubLabel}>NOM DE L'ESCALIER</Text>
              <TextInput
                value={newStairName}
                onChangeText={setNewStairName}
                placeholder="Cave-to-RDC, Terrasse, Intérieur..."
                placeholderTextColor={C.GRAY3}
                style={styles.modalInput}
                maxLength={60}
                returnKeyType="done"
                testID="input-new-stair-name"
              />
            </ScrollView>

            {/* Bottom : ANNULER + CONFIGURER */}
            <View style={{ flexDirection: 'row', gap: SP.sm, marginTop: SP.md }}>
              <TouchableOpacity style={[styles.modalBtn, styles.modalBtnGhost]} onPress={() => setAddOpen(false)}>
                <Text style={[styles.modalBtnTxt, { color: C.WHITE }]}>ANNULER</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[
                  styles.modalBtn, styles.modalBtnPrimary,
                  (!newStairShape || newStairShape === 'helicoidal' || creating) && { opacity: 0.4 },
                ]}
                onPress={createStair}
                disabled={!newStairShape || newStairShape === 'helicoidal' || creating}
                testID="btn-create-stair"
              >
                {creating
                  ? <ActivityIndicator color={C.DARK} />
                  : <Text style={styles.modalBtnTxt}>CONFIGURER →</Text>}
              </TouchableOpacity>
            </View>
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </SafeAreaView>
  );
}

// ╔═══════════════════════════════════════════════════════╗
//   SHAPE CARDS — 4 fiches techniques visuelles (image_42)
//   Chaque carte : SVG profil + plan, flèches métier rouges,
//   libellés dimensions, état active = bord vert + halo.
// ╚═══════════════════════════════════════════════════════╝

const RED = '#E11D48';
const GREEN = C.ACCENT;
const GRAY = '#9098A8';
const ARROW = (id: string) => null; // arrowhead defined per-svg

function CardFrame({
  title, active, onPress, children, testID,
}: { title: string; active: boolean; onPress: () => void; children: React.ReactNode; testID?: string }) {
  return (
    <TouchableOpacity
      activeOpacity={0.8}
      onPress={onPress}
      style={[styles.shapeCard, active && styles.shapeCardActive]}
      testID={testID}
    >
      <View style={styles.shapeCardSvg}>{children}</View>
      <Text style={[styles.shapeCardTitle, active && { color: C.ACCENT }]}>{title}</Text>
    </TouchableOpacity>
  );
}

function ShapeCardDroit({
  active, onPress, niveauFini, onToggleNiveauFini,
}: { active: boolean; onPress: () => void; niveauFini: boolean; onToggleNiveauFini: () => void }) {
  return (
    <CardFrame title="DROIT" active={active} onPress={onPress} testID="shape-droit">
      <Svg width="100%" height="100" viewBox="0 0 140 100">
        {/* Profil : escalier qui monte */}
        <Polyline points="20,80 20,72 32,72 32,64 44,64 44,56 56,56 56,48 68,48 68,40" stroke={C.WHITE} strokeWidth="1.5" fill="none"/>
        {/* Sol bas/haut */}
        <Line x1="12" y1="80" x2="78" y2="80" stroke={GRAY} strokeWidth="0.8"/>
        <Line x1="62" y1="40" x2="92" y2="40" stroke={GRAY} strokeWidth="0.8"/>
        {/* Dalle (vert) */}
        <Rect x="62" y="32" width="30" height="8" fill="rgba(140,198,63,0.25)" stroke={GREEN} strokeWidth="0.8"/>
        {/* Flèche HAUTEUR TOTALE (rouge gauche) */}
        <Line x1="10" y1="80" x2="10" y2="40" stroke={RED} strokeWidth="1"/>
        <Polygon points="10,40 7,46 13,46" fill={RED}/>
        <Polygon points="10,80 7,74 13,74" fill={RED}/>
        <SvgText x="2" y="62" fontSize="5" fill={RED} fontWeight="bold">HT</SvgText>
        {/* Flèche ÉPAISSEUR DALLE (vert) */}
        <Line x1="96" y1="32" x2="96" y2="40" stroke={GREEN} strokeWidth="1"/>
        <SvgText x="98" y="38" fontSize="5" fill={GREEN} fontWeight="bold">ED</SvgText>
        {/* Plan */}
        <Rect x="100" y="60" width="32" height="22" fill="none" stroke={C.WHITE} strokeWidth="1"/>
        {/* Marches plan */}
        <Line x1="100" y1="66" x2="132" y2="66" stroke={GRAY} strokeWidth="0.4"/>
        <Line x1="100" y1="72" x2="132" y2="72" stroke={GRAY} strokeWidth="0.4"/>
        <Line x1="100" y1="78" x2="132" y2="78" stroke={GRAY} strokeWidth="0.4"/>
        <SvgText x="116" y="56" fontSize="4" fill={RED} fontWeight="bold" textAnchor="middle">L</SvgText>
        <SvgText x="136" y="73" fontSize="4" fill={RED} fontWeight="bold">l</SvgText>
      </Svg>
      {/* NIVEAU FINI checkbox (DROIT-only, sous le dessin) */}
      <TouchableOpacity
        onPress={(e) => { e.stopPropagation?.(); onToggleNiveauFini(); }}
        style={styles.nivFiniRow}
        testID="droit-niveau-fini"
      >
        <View style={[styles.nivFiniBox, niveauFini && styles.nivFiniBoxOn]}>
          {niveauFini && <Ionicons name="checkmark" size={11} color={C.DARK} />}
        </View>
        <Text style={styles.nivFiniLabel}>NIVEAU FINI</Text>
      </TouchableOpacity>
    </CardFrame>
  );
}

function ShapeCardQuart({ active, onPress }: { active: boolean; onPress: () => void }) {
  return (
    <CardFrame title="1/4 TOURNANT" active={active} onPress={onPress} testID="shape-quart-tournant">
      <Svg width="100%" height="100" viewBox="0 0 140 100">
        {/* L-shape plan */}
        <Polygon points="20,75 60,75 60,40 95,40 95,55 75,55 75,90 20,90" fill="none" stroke={C.WHITE} strokeWidth="1.5"/>
        {/* Marches lignes parallèles section A horizontale */}
        <Line x1="80" y1="40" x2="80" y2="55" stroke={GRAY} strokeWidth="0.5"/>
        <Line x1="85" y1="40" x2="85" y2="55" stroke={GRAY} strokeWidth="0.5"/>
        <Line x1="90" y1="40" x2="90" y2="55" stroke={GRAY} strokeWidth="0.5"/>
        {/* Marches section B verticale */}
        <Line x1="60" y1="60" x2="75" y2="60" stroke={GRAY} strokeWidth="0.5"/>
        <Line x1="60" y1="68" x2="75" y2="68" stroke={GRAY} strokeWidth="0.5"/>
        <Line x1="60" y1="76" x2="75" y2="76" stroke={GRAY} strokeWidth="0.5"/>
        {/* Dansantes au coin */}
        <Line x1="60" y1="55" x2="75" y2="40" stroke={GRAY} strokeWidth="0.5"/>
        {/* Flèches LONGUEUR A (haut) */}
        <Line x1="60" y1="32" x2="95" y2="32" stroke={RED} strokeWidth="1"/>
        <Polygon points="60,32 64,30 64,34" fill={RED}/>
        <Polygon points="95,32 91,30 91,34" fill={RED}/>
        <SvgText x="77" y="29" fontSize="4" fill={RED} fontWeight="bold" textAnchor="middle">LONG. A</SvgText>
        {/* Flèche LONGUEUR B (gauche) */}
        <Line x1="12" y1="75" x2="12" y2="90" stroke={RED} strokeWidth="1"/>
        <Polygon points="12,75 10,79 14,79" fill={RED}/>
        <Polygon points="12,90 10,86 14,86" fill={RED}/>
        <SvgText x="2" y="86" fontSize="4" fill={RED} fontWeight="bold">L.B</SvgText>
        {/* Largeur */}
        <SvgText x="40" y="97" fontSize="4" fill={RED} fontWeight="bold">l</SvgText>
      </Svg>
    </CardFrame>
  );
}

function ShapeCardDemi({ active, onPress }: { active: boolean; onPress: () => void }) {
  return (
    <CardFrame title="2/4 TOURNANT" active={active} onPress={onPress} testID="shape-demi-tournant">
      <Svg width="100%" height="100" viewBox="0 0 140 100">
        {/* U-shape plan */}
        <Polygon points="20,25 50,25 50,65 90,65 90,25 120,25 120,85 20,85" fill="none" stroke={C.WHITE} strokeWidth="1.5"/>
        {/* Marches section A (gauche bas) */}
        <Line x1="20" y1="72" x2="50" y2="72" stroke={GRAY} strokeWidth="0.5"/>
        <Line x1="20" y1="78" x2="50" y2="78" stroke={GRAY} strokeWidth="0.5"/>
        {/* Section B (haut, palier) */}
        <Line x1="55" y1="40" x2="85" y2="40" stroke={GRAY} strokeWidth="0.5"/>
        <Line x1="55" y1="50" x2="85" y2="50" stroke={GRAY} strokeWidth="0.5"/>
        {/* Section C (droite bas) */}
        <Line x1="90" y1="72" x2="120" y2="72" stroke={GRAY} strokeWidth="0.5"/>
        <Line x1="90" y1="78" x2="120" y2="78" stroke={GRAY} strokeWidth="0.5"/>
        {/* Flèches : LONG A en bas, LARGEUR à droite */}
        <Line x1="20" y1="92" x2="50" y2="92" stroke={RED} strokeWidth="1"/>
        <Polygon points="20,92 24,90 24,94" fill={RED}/>
        <Polygon points="50,92 46,90 46,94" fill={RED}/>
        <SvgText x="35" y="98" fontSize="4" fill={RED} fontWeight="bold" textAnchor="middle">L.A</SvgText>
        <Line x1="90" y1="92" x2="120" y2="92" stroke={RED} strokeWidth="1"/>
        <Polygon points="90,92 94,90 94,94" fill={RED}/>
        <Polygon points="120,92 116,90 116,94" fill={RED}/>
        <SvgText x="105" y="98" fontSize="4" fill={RED} fontWeight="bold" textAnchor="middle">L.B</SvgText>
        <SvgText x="125" y="78" fontSize="4" fill={RED} fontWeight="bold">l</SvgText>
      </Svg>
    </CardFrame>
  );
}

function ShapeCardHelico({ onPress }: { onPress: () => void }) {
  return (
    <TouchableOpacity activeOpacity={0.7} onPress={onPress} style={[styles.shapeCard, styles.shapeCardDisabled]} testID="shape-helicoidal">
      <View style={styles.shapeCardSvg}>
        <Svg width="100%" height="100" viewBox="0 0 140 100">
          {/* Cercle plan (gauche) */}
          <Circle cx="40" cy="55" r="28" fill="none" stroke={GRAY} strokeWidth="1"/>
          <Circle cx="40" cy="55" r="8" fill="none" stroke={GRAY} strokeWidth="1"/>
          {/* Marches radiales */}
          {[0,30,60,90,120,150,180,210,240,270,300,330].map(a => {
            const rad = (a * Math.PI) / 180;
            const x1 = 40 + 8 * Math.cos(rad);
            const y1 = 55 + 8 * Math.sin(rad);
            const x2 = 40 + 28 * Math.cos(rad);
            const y2 = 55 + 28 * Math.sin(rad);
            return <Line key={a} x1={x1} y1={y1} x2={x2} y2={y2} stroke={GRAY} strokeWidth="0.4"/>;
          })}
          {/* Spiral profile (droite) */}
          <Path d="M85 80 L85 70 Q95 70 95 60 Q105 60 105 50 Q115 50 115 40 Q125 40 125 30" stroke={GRAY} strokeWidth="1" fill="none"/>
          <SvgText x="40" y="14" fontSize="4" fill={GRAY} fontWeight="bold" textAnchor="middle">RAYON r</SvgText>
        </Svg>
      </View>
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
        <Text style={[styles.shapeCardTitle, { color: C.GRAY3 }]}>HÉLICOÏDAL</Text>
        <View style={styles.bientotBadge}><Text style={styles.bientotTxt}>BIENTÔT</Text></View>
      </View>
    </TouchableOpacity>
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

  empty: { alignItems: 'center', padding: SP.xl, backgroundColor: C.CARD, borderRadius: R.lg, borderWidth: 1, borderColor: C.ACCENT, borderStyle: 'dashed' as any, marginBottom: SP.md },
  emptyTitle: { ...FONT.h3, marginTop: SP.md },
  emptyHint: { ...FONT.small, textAlign: 'center', marginTop: SP.sm, lineHeight: 19, paddingHorizontal: SP.md, color: C.GRAY3 },
  emptyCta: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: SP.sm,
    marginTop: SP.lg, paddingVertical: 14, paddingHorizontal: SP.lg,
    backgroundColor: C.ACCENT, borderRadius: R.md, alignSelf: 'stretch',
  },
  emptyCtaTxt: { ...FONT.button, fontSize: 13, color: C.DARK, letterSpacing: 0.5 },
  emptyUnlockCta: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: SP.sm,
    marginTop: SP.sm, paddingVertical: 12, paddingHorizontal: SP.lg,
    backgroundColor: C.WARN, borderRadius: R.md, alignSelf: 'stretch',
  },
  emptyLocked: {
    flexDirection: 'row', alignItems: 'center', gap: 6,
    marginTop: SP.md, paddingHorizontal: SP.md, paddingVertical: SP.sm,
    backgroundColor: 'rgba(245,158,11,0.10)', borderRadius: R.md,
    borderWidth: 1, borderColor: C.WARN,
  },
  emptyLockedTxt: { ...FONT.small, fontSize: 11, color: C.WARN, flex: 1 },
  fab: {
    position: 'absolute', right: SP.lg, bottom: SP.lg + 8,
    width: 56, height: 56, borderRadius: 28,
    backgroundColor: C.ACCENT, alignItems: 'center', justifyContent: 'center',
    elevation: 8, shadowColor: '#000', shadowOpacity: 0.4, shadowRadius: 8, shadowOffset: { width: 0, height: 4 },
    borderWidth: 2, borderColor: C.DARK,
  },

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

  // Modal "Aucun escalier" (image_42)
  modalCardBig: {
    width: '100%', maxWidth: 520,
    backgroundColor: C.CARD, borderRadius: R.lg, padding: SP.lg,
    borderWidth: 1, borderColor: C.BORDER,
  },
  modalKicker: { ...FONT.label, fontSize: 9, color: C.GRAY3 },
  modalTitleBig: { ...FONT.h2, fontSize: 18, color: C.WHITE, marginTop: 2 },
  cardsGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: SP.sm, marginTop: SP.sm, marginBottom: SP.md },

  shapeCard: {
    flexBasis: '48%', flexGrow: 1,
    backgroundColor: C.BG_DEEPER,
    borderRadius: R.md,
    borderWidth: 1.5, borderColor: C.BORDER,
    padding: 10,
    minHeight: 150,
  },
  shapeCardActive: {
    borderColor: C.ACCENT,
    backgroundColor: 'rgba(140,198,63,0.06)',
  },
  shapeCardDisabled: {
    opacity: 0.55, flexBasis: '48%', flexGrow: 1,
    backgroundColor: C.BG_DEEPER, borderRadius: R.md,
    borderWidth: 1.5, borderColor: C.BORDER, padding: 10, minHeight: 150,
  },
  shapeCardSvg: { backgroundColor: 'rgba(255,255,255,0.02)', borderRadius: 6, marginBottom: 6, paddingVertical: 4 },
  shapeCardTitle: { ...FONT.button, fontSize: 12, color: C.WHITE, textAlign: 'center' },

  nivFiniRow: {
    flexDirection: 'row', alignItems: 'center', gap: 6,
    marginTop: 6, paddingTop: 6,
    borderTopWidth: 1, borderTopColor: C.BORDER,
    justifyContent: 'center',
  },
  nivFiniBox: {
    width: 16, height: 16, borderRadius: 4,
    borderWidth: 1.5, borderColor: C.GRAY3,
    alignItems: 'center', justifyContent: 'center',
  },
  nivFiniBoxOn: { backgroundColor: C.ACCENT, borderColor: C.ACCENT },
  nivFiniLabel: { ...FONT.label, fontSize: 9, color: C.WHITE },

  // Shape selector inside modal (4 formes, grid 2×2)
  modalSubLabel: { ...FONT.label, color: C.ACCENT, fontSize: 11, marginTop: SP.md },
  shapeRow: { flexDirection: 'row', gap: SP.sm, marginTop: SP.sm },
  shapeGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: SP.sm, marginTop: SP.sm },
  shapeBtn: {
    flexBasis: '48%',
    flexGrow: 1,
    paddingVertical: 12,
    paddingHorizontal: 8,
    backgroundColor: C.BG_DEEPER,
    borderRadius: R.md,
    borderWidth: 1,
    borderColor: C.BORDER,
    alignItems: 'center',
    gap: 4,
    minHeight: 88,
    justifyContent: 'center',
  },
  shapeBtnActive: { backgroundColor: C.ACCENT, borderColor: C.ACCENT },
  shapeBtnDisabled: { opacity: 0.5 },
  shapeTitle: { ...FONT.button, color: C.WHITE, fontSize: 11, marginTop: 2, textAlign: 'center' },
  shapeHint: { ...FONT.small, fontSize: 9, color: C.GRAY3, textAlign: 'center' },
  bientotBadge: {
    marginTop: 4, paddingHorizontal: 6, paddingVertical: 2, borderRadius: R.pill,
    borderWidth: 1, borderColor: C.WARN, backgroundColor: 'transparent',
  },
  bientotTxt: { ...FONT.label, color: C.WARN, fontSize: 8 },
});
