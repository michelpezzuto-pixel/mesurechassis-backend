import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Alert, ScrollView } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons, MaterialCommunityIcons, Feather } from '@expo/vector-icons';
import { useAuth } from '@/src/auth';
import { C, SP, R, FONT } from '@/src/theme';

export default function SubscriptionRequired() {
  const router = useRouter();
  const { user, signOut } = useAuth();

  const logout = async () => {
    await signOut();
    router.replace('/login');
  };

  const onSubscribe = () => {
    Alert.alert(
      'Configurer mon abonnement',
      "La page de paiement sécurisée sera bientôt disponible.\n\nPour activer dès maintenant votre licence, contactez :\ninfo@mesureescalier.com",
      [{ text: 'Compris' }],
    );
  };

  return (
    <SafeAreaView style={styles.safe} edges={['top', 'bottom']}>
      <ScrollView contentContainerStyle={styles.scroll}>
        {/* Big lock icon */}
        <View style={styles.iconWrap}>
          <View style={styles.iconBox}>
            <MaterialCommunityIcons name="lock-clock" size={56} color={C.WARN} />
          </View>
        </View>

        <Text style={styles.title}>PÉRIODE D'ESSAI TERMINÉE</Text>
        <Text style={styles.subtitle}>
          Votre essai gratuit de 90 jours est arrivé à son terme.
        </Text>
        <Text style={styles.subtitle}>
          Activez votre abonnement pour reprendre vos chantiers, vos mesures et vos exports
          en toute liberté.
        </Text>

        {/* Info card */}
        <View style={styles.infoCard}>
          <View style={styles.infoRow}>
            <Ionicons name="person-circle" size={20} color={C.ACCENT} />
            <Text style={styles.infoLabel}>Compte</Text>
            <Text style={styles.infoValue}>{user?.email || '—'}</Text>
          </View>
          <View style={styles.infoRow}>
            <Ionicons name="business" size={20} color={C.ACCENT} />
            <Text style={styles.infoLabel}>Société</Text>
            <Text style={styles.infoValue}>{user?.company_name || '—'}</Text>
          </View>
          <View style={styles.infoRow}>
            <Ionicons name="calendar" size={20} color={C.ACCENT} />
            <Text style={styles.infoLabel}>Statut</Text>
            <Text style={[styles.infoValue, { color: C.DANGER }]}>Essai expiré</Text>
          </View>
        </View>

        {/* Benefits */}
        <View style={styles.benefits}>
          <Text style={styles.benefitsTitle}>VOTRE ABONNEMENT INCLUT</Text>
          <Benefit icon="infinite" text="Chantiers et mesures illimités" />
          <Benefit icon="cloud-upload" text="Sauvegarde sécurisée multi-appareil" />
          <Benefit icon="document-text" text="Exports PDF et DXF illimités" />
          <Benefit icon="mic" text="Dictée vocale terrain (Whisper)" />
          <Benefit icon="people" text="Gestion d'équipe (Techniciens)" />
        </View>

        {/* CTA */}
        <TouchableOpacity style={styles.ctaPrimary} onPress={onSubscribe} testID="paywall-subscribe">
          <MaterialCommunityIcons name="credit-card-outline" size={20} color={C.DARK} />
          <Text style={styles.ctaPrimaryTxt}>CONFIGURER MON ABONNEMENT</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.ctaSecondary} onPress={logout} testID="paywall-logout">
          <Feather name="log-out" size={18} color={C.WHITE} />
          <Text style={styles.ctaSecondaryTxt}>SE DÉCONNECTER</Text>
        </TouchableOpacity>

        <Text style={styles.footer}>
          Une question ? Contactez-nous : info@mesureescalier.com
        </Text>
      </ScrollView>
    </SafeAreaView>
  );
}

function Benefit({ icon, text }: { icon: any; text: string }) {
  return (
    <View style={styles.benefitRow}>
      <Ionicons name={icon} size={18} color={C.ACCENT} />
      <Text style={styles.benefitTxt}>{text}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: C.DARK },
  scroll: { padding: SP.xl, paddingBottom: 64 },
  iconWrap: { alignItems: 'center', marginTop: SP.xl, marginBottom: SP.xl },
  iconBox: {
    width: 120, height: 120, borderRadius: 60,
    backgroundColor: 'rgba(245, 158, 11, 0.12)',
    borderWidth: 2, borderColor: C.WARN,
    alignItems: 'center', justifyContent: 'center',
  },
  title: { ...FONT.h1, fontSize: 24, color: C.WHITE, textAlign: 'center', letterSpacing: 1 },
  subtitle: { ...FONT.body, color: C.GRAY2, textAlign: 'center', marginTop: SP.md, lineHeight: 22 },
  infoCard: {
    backgroundColor: C.CARD, borderRadius: R.lg, padding: SP.lg,
    borderWidth: 1, borderColor: C.BORDER, marginTop: SP.xl,
  },
  infoRow: { flexDirection: 'row', alignItems: 'center', gap: SP.md, marginBottom: SP.sm },
  infoLabel: { ...FONT.small, color: C.GRAY3, width: 70 },
  infoValue: { ...FONT.body, flex: 1, fontWeight: '600' },
  benefits: {
    backgroundColor: C.ACCENT_BG, borderRadius: R.lg, padding: SP.lg,
    borderLeftWidth: 3, borderLeftColor: C.ACCENT, marginTop: SP.lg,
  },
  benefitsTitle: { ...FONT.label, color: C.ACCENT, marginBottom: SP.md },
  benefitRow: { flexDirection: 'row', alignItems: 'center', gap: SP.md, paddingVertical: 6 },
  benefitTxt: { ...FONT.body, color: C.WHITE, flex: 1 },
  ctaPrimary: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: SP.sm,
    backgroundColor: C.ACCENT, borderRadius: R.lg, paddingVertical: 18, marginTop: SP.xl,
  },
  ctaPrimaryTxt: { ...FONT.button, color: C.DARK, fontSize: 15 },
  ctaSecondary: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: SP.sm,
    backgroundColor: 'transparent', borderRadius: R.lg, paddingVertical: 16,
    borderWidth: 1, borderColor: C.BORDER, marginTop: SP.md,
  },
  ctaSecondaryTxt: { ...FONT.button, color: C.WHITE, fontSize: 13 },
  footer: { ...FONT.small, textAlign: 'center', marginTop: SP.xl, color: C.GRAY3 },
});
