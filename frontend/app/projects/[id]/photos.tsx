import React, { useCallback, useState } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity, ScrollView, ActivityIndicator,
  Image, Alert, Modal, TextInput, KeyboardAvoidingView, Platform, Pressable,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useFocusEffect, useLocalSearchParams, useRouter } from 'expo-router';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { Photos, type ProjectPhoto } from '@/src/api';
import { C, SP, R, FONT } from '@/src/theme';
import { pickFromCamera, pickFromGallery } from '@/src/utils/imagePicker';

const MAX_PHOTOS = 10;

export default function ProjectPhotosScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const [photos, setPhotos] = useState<ProjectPhoto[]>([]);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [preview, setPreview] = useState<ProjectPhoto | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingCaption, setEditingCaption] = useState('');

  const load = useCallback(async () => {
    if (!id) return;
    try {
      const data = await Photos.list(id);
      setPhotos(data);
    } catch (e: any) {
      Alert.alert('Erreur', e?.response?.data?.detail || 'Impossible de charger les photos');
    } finally { setLoading(false); }
  }, [id]);

  useFocusEffect(useCallback(() => { setLoading(true); load(); }, [load]));

  const remaining = MAX_PHOTOS - photos.length;

  const onAdd = async (source: 'camera' | 'gallery') => {
    if (remaining <= 0) {
      Alert.alert('Limite atteinte', `${MAX_PHOTOS} photos maximum par chantier.`);
      return;
    }
    setAdding(true);
    try {
      const img = source === 'camera' ? await pickFromCamera() : await pickFromGallery();
      if (!img || !img.base64) return;
      const created = await Photos.add(id!, img.base64, '');
      setPhotos((p) => [...p, created]);
    } catch (e: any) {
      Alert.alert('Erreur', e?.response?.data?.detail || "Impossible d'ajouter la photo");
    } finally { setAdding(false); }
  };

  const onDelete = (photo: ProjectPhoto) => {
    Alert.alert('Supprimer cette photo ?', 'Cette action est irréversible.', [
      { text: 'Annuler', style: 'cancel' },
      {
        text: 'Supprimer', style: 'destructive', onPress: async () => {
          try {
            await Photos.remove(id!, photo.id);
            setPhotos((p) => p.filter((x) => x.id !== photo.id));
            setPreview(null);
          } catch (e: any) {
            Alert.alert('Erreur', e?.response?.data?.detail || 'Erreur');
          }
        },
      },
    ]);
  };

  const startEditCaption = (photo: ProjectPhoto) => {
    setEditingId(photo.id);
    setEditingCaption(photo.caption || '');
  };

  const saveCaption = async () => {
    if (!editingId) return;
    const target = editingId;
    const value = editingCaption.trim();
    try {
      await Photos.updateCaption(id!, target, value);
      setPhotos((p) => p.map((x) => (x.id === target ? { ...x, caption: value } : x)));
      if (preview?.id === target) setPreview({ ...preview, caption: value });
    } catch (e: any) {
      Alert.alert('Erreur', e?.response?.data?.detail || 'Erreur');
    } finally {
      setEditingId(null);
      setEditingCaption('');
    }
  };

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <View style={styles.topbar}>
        <TouchableOpacity onPress={() => router.back()} testID="back-btn"><Ionicons name="arrow-back" size={24} color={C.WHITE} /></TouchableOpacity>
        <Text style={styles.title}>PHOTOS DE CHANTIER</Text>
        <Text style={styles.counter}>{photos.length}/{MAX_PHOTOS}</Text>
      </View>

      {loading ? (
        <View style={styles.center}><ActivityIndicator color={C.ACCENT} size="large" /></View>
      ) : (
        <ScrollView contentContainerStyle={{ padding: SP.md, paddingBottom: 140 }}>
          {photos.length === 0 ? (
            <View style={styles.empty}>
              <MaterialCommunityIcons name="image-multiple-outline" size={64} color={C.GRAY3} />
              <Text style={styles.emptyTitle}>Aucune photo</Text>
              <Text style={styles.emptyHint}>Photographiez la trémie, les murs, les contraintes du chantier. Elles seront annexées au rapport PDF.</Text>
            </View>
          ) : (
            <View style={styles.grid}>
              {photos.map((ph) => {
                const isEditing = editingId === ph.id;
                return (
                  <View key={ph.id} style={styles.tile}>
                    <Pressable onPress={() => setPreview(ph)} testID={`photo-tile-${ph.id}`}>
                      <Image
                        source={{ uri: ph.base64.startsWith('data:') ? ph.base64 : `data:image/jpeg;base64,${ph.base64}` }}
                        style={styles.tileImg}
                        resizeMode="cover"
                      />
                    </Pressable>
                    {isEditing ? (
                      <View style={styles.captionEdit}>
                        <TextInput
                          value={editingCaption}
                          onChangeText={setEditingCaption}
                          placeholder="Légende…"
                          placeholderTextColor={C.GRAY3}
                          style={styles.captionInput}
                          autoFocus
                          onSubmitEditing={saveCaption}
                          maxLength={120}
                        />
                        <TouchableOpacity onPress={saveCaption} testID={`caption-save-${ph.id}`}>
                          <Ionicons name="checkmark-circle" size={24} color={C.ACCENT} />
                        </TouchableOpacity>
                      </View>
                    ) : (
                      <TouchableOpacity onPress={() => startEditCaption(ph)} style={styles.captionRow} testID={`caption-edit-${ph.id}`}>
                        <Text style={styles.caption} numberOfLines={2}>
                          {ph.caption?.trim() || 'Ajouter une légende…'}
                        </Text>
                        <Ionicons name="pencil" size={14} color={C.GRAY3} />
                      </TouchableOpacity>
                    )}
                    <TouchableOpacity style={styles.tileDel} onPress={() => onDelete(ph)} testID={`photo-delete-${ph.id}`}>
                      <Ionicons name="trash" size={16} color={C.WHITE} />
                    </TouchableOpacity>
                  </View>
                );
              })}
            </View>
          )}
        </ScrollView>
      )}

      {/* Action bar (Camera + Gallery) */}
      <View style={styles.actionBar}>
        <TouchableOpacity
          style={[styles.actionBtn, styles.actionPrimary, (adding || remaining <= 0) && { opacity: 0.5 }]}
          onPress={() => onAdd('camera')}
          disabled={adding || remaining <= 0}
          testID="photo-add-camera"
        >
          {adding ? <ActivityIndicator color={C.DARK} /> : (
            <>
              <Ionicons name="camera" size={20} color={C.DARK} />
              <Text style={styles.actionTxt}>APPAREIL</Text>
            </>
          )}
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.actionBtn, styles.actionSecondary, (adding || remaining <= 0) && { opacity: 0.5 }]}
          onPress={() => onAdd('gallery')}
          disabled={adding || remaining <= 0}
          testID="photo-add-gallery"
        >
          <Ionicons name="images" size={20} color={C.WHITE} />
          <Text style={[styles.actionTxt, { color: C.WHITE }]}>GALERIE</Text>
        </TouchableOpacity>
      </View>

      {/* Full-screen preview modal */}
      <Modal visible={!!preview} transparent animationType="fade" onRequestClose={() => setPreview(null)}>
        <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={styles.modalBg}>
          {preview && (
            <>
              <View style={styles.modalTop}>
                <TouchableOpacity onPress={() => setPreview(null)} testID="preview-close">
                  <Ionicons name="close" size={28} color={C.WHITE} />
                </TouchableOpacity>
                <TouchableOpacity onPress={() => onDelete(preview)} testID="preview-delete">
                  <Ionicons name="trash" size={24} color={C.DANGER} />
                </TouchableOpacity>
              </View>
              <Image
                source={{ uri: preview.base64.startsWith('data:') ? preview.base64 : `data:image/jpeg;base64,${preview.base64}` }}
                style={styles.modalImg}
                resizeMode="contain"
              />
              <View style={styles.modalCaption}>
                <Text style={styles.modalCaptionTxt}>{preview.caption?.trim() || '—'}</Text>
              </View>
            </>
          )}
        </KeyboardAvoidingView>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: C.DARK },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  topbar: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', padding: SP.lg, borderBottomWidth: 1, borderBottomColor: C.BORDER },
  title: { ...FONT.h3, fontSize: 16 },
  counter: { ...FONT.label, color: C.ACCENT, minWidth: 40, textAlign: 'right' },
  empty: { alignItems: 'center', justifyContent: 'center', padding: SP.xl, marginTop: SP.xl * 2 },
  emptyTitle: { ...FONT.h3, marginTop: SP.md },
  emptyHint: { ...FONT.small, textAlign: 'center', marginTop: SP.sm, lineHeight: 20, paddingHorizontal: SP.lg },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: SP.sm },
  tile: { width: '48.5%', backgroundColor: C.CARD, borderRadius: R.md, borderWidth: 1, borderColor: C.BORDER, overflow: 'hidden', position: 'relative' },
  tileImg: { width: '100%', height: 140, backgroundColor: C.BG_DEEPER },
  tileDel: { position: 'absolute', top: 6, right: 6, backgroundColor: 'rgba(0,0,0,0.55)', borderRadius: 16, width: 32, height: 32, alignItems: 'center', justifyContent: 'center' },
  captionRow: { flexDirection: 'row', alignItems: 'center', padding: SP.sm, gap: 6 },
  caption: { ...FONT.small, flex: 1, fontSize: 12 },
  captionEdit: { flexDirection: 'row', alignItems: 'center', padding: SP.sm, gap: SP.sm },
  captionInput: { flex: 1, color: C.WHITE, fontSize: 12, padding: 0 },
  actionBar: { position: 'absolute', bottom: 0, left: 0, right: 0, padding: SP.lg, flexDirection: 'row', gap: SP.sm, backgroundColor: C.DARK, borderTopWidth: 1, borderTopColor: C.BORDER },
  actionBtn: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: SP.sm, paddingVertical: 14, borderRadius: R.md, borderWidth: 1 },
  actionPrimary: { backgroundColor: C.ACCENT, borderColor: C.ACCENT },
  actionSecondary: { backgroundColor: C.CARD, borderColor: C.BORDER },
  actionTxt: { ...FONT.button, color: C.DARK, fontSize: 13 },
  modalBg: { flex: 1, backgroundColor: 'rgba(0,0,0,0.95)' },
  modalTop: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', padding: SP.lg, paddingTop: SP.lg + 24 },
  modalImg: { flex: 1, width: '100%' },
  modalCaption: { padding: SP.lg, paddingBottom: SP.xl },
  modalCaptionTxt: { ...FONT.body, color: C.WHITE, textAlign: 'center', fontStyle: 'italic' },
});
