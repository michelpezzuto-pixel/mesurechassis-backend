import React, { useEffect, useState, useCallback } from 'react';
import { View, Text, StyleSheet, ScrollView, ActivityIndicator, TouchableOpacity, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { useRouter, useFocusEffect } from 'expo-router';
import { Stats } from '@/src/api';
import { useAuth } from '@/src/auth';
import { C, SP, R, FONT, STATUS_LABELS, STATUS_COLOR } from '@/src/theme';

export default function StatsScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try { setData(await Stats.get()); }
    catch (e: any) { Alert.alert('Erreur', e?.response?.data?.detail || 'Chargement impossible'); }
    finally { setLoading(false); }
  }, []);

  useFocusEffect(useCallback(() => { setLoading(true); load(); }, [load]));

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <View style={styles.topbar}>
        <TouchableOpacity onPress={() => router.back()} testID="back-btn">
          <Ionicons name="arrow-back" size={24} color={C.WHITE} />
        </TouchableOpacity>
        <Text style={styles.title}>STATISTIQUES</Text>
        <View style={{ width: 24 }} />
      </View>

      {loading || !data ? (
        <View style={styles.center}><ActivityIndicator color={C.ACCENT} size="large" /></View>
      ) : (
        <ScrollView contentContainerStyle={{ padding: SP.lg, paddingBottom: 48 }}>
          <Text style={styles.subtitle}>Vue d'ensemble de votre activité</Text>

          {/* Top KPIs */}
          <View style={styles.kpiGrid}>
            <BigKpi icon="folder" label="Chantiers" value={data.total_projects} testID="kpi-projects" />
            <BigKpi icon="stairs-up" iconLib="mci" label="Mesures" value={data.total_measurements} testID="kpi-measurements" />
            <BigKpi icon="checkmark-circle" label="Validés" value={data.validated_measurements} testID="kpi-validated" />
            <BigKpi
              icon="trending-up"
              label="Marches moy."
              value={data.average_steps ?? '—'}
              testID="kpi-avg-steps"
            />
          </View>

          {/* By status breakdown */}
          <View style={styles.card}>
            <Text style={styles.cardHead}>RÉPARTITION PAR STATUT</Text>
            {Object.entries(data.by_status as Record<string, number>).map(([s, n]) => (
              <View key={s} style={styles.statusRow}>
                <View style={[styles.statusDot, { backgroundColor: STATUS_COLOR[s] }]} />
                <Text style={styles.statusLabel}>{STATUS_LABELS[s] || s}</Text>
                <Text style={styles.statusCount}>{n}</Text>
              </View>
            ))}
          </View>

          {data.team_size !== null && (
            <View style={styles.card}>
              <Text style={styles.cardHead}>ÉQUIPE</Text>
              <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                <Ionicons name="people" size={28} color={C.ACCENT} />
                <Text style={{ ...FONT.h2, marginLeft: SP.md }}>{data.team_size} membres</Text>
              </View>
            </View>
          )}

          {user?.solo_mode && (
            <View style={styles.soloBanner}>
              <MaterialCommunityIcons name="account-star" size={24} color={C.ACCENT} />
              <Text style={styles.soloTxt}>Mode artisan unique activé — pleins pouvoirs.</Text>
            </View>
          )}
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

function BigKpi({ icon, iconLib, label, value, testID }: any) {
  const Lib = iconLib === 'mci' ? MaterialCommunityIcons : Ionicons;
  return (
    <View style={styles.bigKpi} testID={testID}>
      <Lib name={icon} size={26} color={C.ACCENT} />
      <Text style={styles.bigKpiValue}>{value}</Text>
      <Text style={styles.bigKpiLabel}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: C.DARK },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  topbar: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', padding: SP.lg, borderBottomWidth: 1, borderBottomColor: C.BORDER },
  title: { ...FONT.h2, fontSize: 18 },
  subtitle: { ...FONT.small, marginBottom: SP.lg },
  kpiGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: SP.md, marginBottom: SP.md },
  bigKpi: { flexBasis: '47%', flexGrow: 1, backgroundColor: C.CARD, borderRadius: R.lg, padding: SP.lg, alignItems: 'center', borderWidth: 1, borderColor: C.BORDER },
  bigKpiValue: { ...FONT.h1, fontSize: 32, marginTop: SP.sm, color: C.ACCENT },
  bigKpiLabel: { ...FONT.label, marginTop: 4, fontSize: 11 },
  card: { backgroundColor: C.CARD, borderRadius: R.lg, padding: SP.lg, borderWidth: 1, borderColor: C.BORDER, marginTop: SP.md },
  cardHead: { ...FONT.label, color: C.ACCENT, marginBottom: SP.md },
  statusRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 10, borderTopWidth: 1, borderTopColor: C.BORDER },
  statusDot: { width: 10, height: 10, borderRadius: 5 },
  statusLabel: { ...FONT.body, marginLeft: SP.md, flex: 1 },
  statusCount: { ...FONT.h3, color: C.ACCENT },
  soloBanner: { flexDirection: 'row', alignItems: 'center', gap: SP.md, padding: SP.md, backgroundColor: C.ACCENT_BG, borderRadius: R.md, borderLeftWidth: 3, borderLeftColor: C.ACCENT, marginTop: SP.lg },
  soloTxt: { ...FONT.small, color: C.GRAY1, flex: 1 },
});
