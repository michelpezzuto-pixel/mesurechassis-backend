import React, { useEffect, useState, useCallback } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet, FlatList,
  RefreshControl, ActivityIndicator, Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons, MaterialCommunityIcons, Feather } from '@expo/vector-icons';
import { useRouter, useFocusEffect } from 'expo-router';
import { useAuth } from '@/src/auth';
import { Projects, Project } from '@/src/api';
import { C, SP, R, FONT, STATUS_LABELS, STATUS_COLOR } from '@/src/theme';

const FILTERS: { key: string; label: string }[] = [
  { key: 'tous', label: 'TOUS' },
  { key: 'brouillon', label: 'BROUILLON' },
  { key: 'a_mesurer', label: 'À MESURER' },
  { key: 'a_verifier', label: 'À VÉRIFIER' },
  { key: 'valide', label: 'VALIDÉ' },
];

export default function Dashboard() {
  const { user, signOut } = useAuth();
  const router = useRouter();
  const [filter, setFilter] = useState('tous');
  const [search, setSearch] = useState('');
  const [items, setItems] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Paywall guard — locked users get redirected
  useEffect(() => {
    if (user?.is_locked) {
      router.replace('/subscription-required');
    }
  }, [user?.is_locked, router]);

  const load = useCallback(async () => {
    try {
      const data = await Projects.list(filter);
      setItems(data);
    } catch (e: any) {
      Alert.alert('Erreur', e?.response?.data?.detail || 'Chargement impossible');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [filter]);

  useFocusEffect(useCallback(() => { setLoading(true); load(); }, [load]));
  useEffect(() => { load(); }, [load]);

  const filtered = items.filter(p => {
    if (!search) return true;
    const s = search.toLowerCase();
    return (
      p.client_nom?.toLowerCase().includes(s) ||
      p.client_prenom?.toLowerCase().includes(s) ||
      p.address?.toLowerCase().includes(s) ||
      p.city?.toLowerCase().includes(s)
    );
  });

  const handleLogout = async () => {
    await signOut();
    router.replace('/login');
  };

  const canCreate = user?.role === 'admin';

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      {/* Header */}
      <View style={styles.header}>
        <View style={{ flex: 1 }}>
          <Text style={styles.hello}>Bonjour</Text>
          <Text style={styles.name} numberOfLines={1}>{user?.full_name?.split(' ')[0] || '—'}</Text>
          <Text style={styles.company} numberOfLines={1}>
            {(user?.company_name || '').toUpperCase()}
            {user?.solo_mode ? '  ·  ARTISAN' : ''}
          </Text>
        </View>
        <View style={styles.iconRow}>
          <TouchableOpacity style={styles.iconBtn} onPress={() => router.push('/stats')} testID="header-stats">
            <Ionicons name="stats-chart" size={20} color={C.ACCENT} />
          </TouchableOpacity>
          {user?.role === 'admin' && (
            <TouchableOpacity style={styles.iconBtn} onPress={() => router.push('/team')} testID="header-team">
              <Ionicons name="people" size={20} color={C.ACCENT} />
            </TouchableOpacity>
          )}
          <TouchableOpacity style={styles.iconBtn} onPress={() => router.push('/settings')} testID="header-settings">
            <Ionicons name="settings-sharp" size={20} color={C.ACCENT} />
          </TouchableOpacity>
          <TouchableOpacity style={styles.iconBtn} onPress={handleLogout} testID="header-logout">
            <Feather name="log-out" size={20} color={C.ACCENT} />
          </TouchableOpacity>
        </View>
      </View>

      {/* Trial / Beta banner — dynamic */}
      {user?.subscription_active ? (
        <View style={styles.beta}>
          <MaterialCommunityIcons name="check-decagram" size={26} color={C.ACCENT} />
          <View style={{ flex: 1, marginLeft: SP.md }}>
            <Text style={styles.betaTitle}>ABONNEMENT ACTIF</Text>
            <Text style={styles.betaTxt}>Accès complet à toutes les fonctionnalités.</Text>
          </View>
        </View>
      ) : user?.is_trial_active ? (
        <View style={styles.beta}>
          <MaterialCommunityIcons name="rocket-launch" size={26} color={C.ACCENT} />
          <View style={{ flex: 1, marginLeft: SP.md }}>
            <Text style={styles.betaTitle}>
              BETA GRATUITE · {user.trial_days_remaining} JOUR{user.trial_days_remaining > 1 ? 'S' : ''} RESTANT{user.trial_days_remaining > 1 ? 'S' : ''}
            </Text>
            <Text style={styles.betaTxt}>
              Vous avez accès à toutes les fonctionnalités pendant la phase de test (3 mois).
            </Text>
          </View>
        </View>
      ) : null}

      {/* Search */}
      <View style={styles.searchBox}>
        <Ionicons name="search" size={18} color={C.GRAY3} />
        <TextInput
          style={styles.searchInput}
          placeholder="Rechercher un client ou une adresse..."
          placeholderTextColor={C.GRAY3}
          value={search}
          onChangeText={setSearch}
          testID="dashboard-search-input"
        />
      </View>

      {/* Filters */}
      <FlatList
        horizontal
        showsHorizontalScrollIndicator={false}
        data={FILTERS}
        keyExtractor={f => f.key}
        contentContainerStyle={{ paddingHorizontal: SP.lg, gap: SP.sm }}
        style={{ flexGrow: 0, marginBottom: SP.md }}
        renderItem={({ item }) => {
          const active = filter === item.key;
          return (
            <TouchableOpacity
              style={[styles.pill, active && styles.pillActive]}
              onPress={() => setFilter(item.key)}
              testID={`filter-pill-${item.key}`}
            >
              <Text style={[styles.pillTxt, active && styles.pillTxtActive]}>{item.label}</Text>
            </TouchableOpacity>
          );
        }}
      />

      {/* List */}
      {loading ? (
        <View style={styles.empty}>
          <ActivityIndicator color={C.ACCENT} size="large" />
        </View>
      ) : filtered.length === 0 ? (
        <View style={styles.empty}>
          <Feather name="folder" size={56} color={C.GRAY3} />
          <Text style={styles.emptyTitle}>Aucun chantier</Text>
          <Text style={styles.emptyTxt}>
            {canCreate ? 'Créez votre premier chantier ↓' : 'Aucun chantier ne vous est encore assigné.'}
          </Text>
        </View>
      ) : (
        <FlatList
          data={filtered}
          keyExtractor={p => p.id}
          contentContainerStyle={{ paddingHorizontal: SP.lg, paddingBottom: 110 }}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load(); }} tintColor={C.ACCENT} />}
          ItemSeparatorComponent={() => <View style={{ height: SP.md }} />}
          renderItem={({ item }) => (
            <TouchableOpacity
              style={styles.card}
              onPress={() => router.push(`/projects/${item.id}`)}
              testID={`project-card-${item.id}`}
            >
              <View style={{ flex: 1 }}>
                <Text style={styles.cardName}>
                  {item.client_nom} {item.client_prenom || ''}
                </Text>
                <Text style={styles.cardAddr} numberOfLines={1}>
                  {item.address}{item.city ? `, ${item.city}` : ''}
                </Text>
                <View style={[styles.badge, { backgroundColor: STATUS_COLOR[item.status] + '22', borderColor: STATUS_COLOR[item.status] }]}>
                  <Text style={[styles.badgeTxt, { color: STATUS_COLOR[item.status] }]}>
                    {STATUS_LABELS[item.status] || item.status}
                  </Text>
                </View>
              </View>
              <Ionicons name="chevron-forward" size={20} color={C.GRAY3} />
            </TouchableOpacity>
          )}
        />
      )}

      {/* FAB */}
      {canCreate && (
        <TouchableOpacity
          style={styles.fab}
          onPress={() => router.push('/projects/new')}
          testID="new-project-fab"
        >
          <Ionicons name="add" size={22} color={C.DARK} />
          <Text style={styles.fabTxt}>NOUVEAU CHANTIER</Text>
        </TouchableOpacity>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: C.DARK },
  header: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: SP.lg, paddingTop: SP.md, paddingBottom: SP.md, gap: SP.md },
  hello: { ...FONT.small, color: C.GRAY3 },
  name: { ...FONT.h1, fontSize: 26 },
  company: { ...FONT.label, color: C.ACCENT, marginTop: 2 },
  iconRow: { flexDirection: 'row', gap: 6 },
  iconBtn: {
    width: 38, height: 38, borderRadius: R.md,
    borderWidth: 1, borderColor: C.BORDER,
    alignItems: 'center', justifyContent: 'center',
    backgroundColor: C.CARD,
  },
  beta: {
    marginHorizontal: SP.lg, marginBottom: SP.md, padding: SP.md,
    backgroundColor: C.ACCENT_BG,
    borderRadius: R.lg, borderWidth: 1, borderColor: C.ACCENT,
    flexDirection: 'row', alignItems: 'center',
  },
  betaTitle: { ...FONT.label, color: C.ACCENT, fontWeight: '800' },
  betaTxt: { ...FONT.small, color: C.GRAY1, marginTop: 2 },
  searchBox: {
    flexDirection: 'row', alignItems: 'center', gap: SP.sm,
    marginHorizontal: SP.lg, paddingHorizontal: SP.md, paddingVertical: 12,
    backgroundColor: C.CARD, borderRadius: R.md,
    borderWidth: 1, borderColor: C.BORDER, marginBottom: SP.md,
  },
  searchInput: { ...FONT.body, flex: 1 },
  pill: {
    paddingHorizontal: SP.lg, paddingVertical: 10,
    borderRadius: R.pill, borderWidth: 1, borderColor: C.BORDER,
    backgroundColor: 'transparent',
  },
  pillActive: { backgroundColor: C.ACCENT, borderColor: C.ACCENT },
  pillTxt: { ...FONT.button, color: C.GRAY3, fontSize: 12 },
  pillTxtActive: { color: C.DARK },
  empty: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: SP.xl },
  emptyTitle: { ...FONT.h3, color: C.WHITE, marginTop: SP.md },
  emptyTxt: { ...FONT.small, marginTop: SP.sm, textAlign: 'center' },
  card: {
    flexDirection: 'row', alignItems: 'center',
    backgroundColor: C.CARD, borderRadius: R.lg, padding: SP.lg,
    borderWidth: 1, borderColor: C.BORDER,
  },
  cardName: { ...FONT.h3, color: C.WHITE },
  cardAddr: { ...FONT.small, marginTop: 2 },
  badge: {
    alignSelf: 'flex-start', marginTop: SP.sm,
    paddingHorizontal: SP.md, paddingVertical: 4,
    borderRadius: R.pill, borderWidth: 1,
  },
  badgeTxt: { ...FONT.label, fontSize: 11 },
  fab: {
    position: 'absolute', bottom: 24, left: SP.lg, right: SP.lg,
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: SP.sm,
    backgroundColor: C.ACCENT, paddingVertical: 18, borderRadius: R.lg,
    shadowColor: C.ACCENT, shadowOpacity: 0.4, shadowRadius: 12, shadowOffset: { width: 0, height: 4 },
    elevation: 6,
  },
  fabTxt: { ...FONT.button, color: C.DARK, fontSize: 14 },
});
