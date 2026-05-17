import React from "react";
import {
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import { colors } from "@/src/theme";

const LAST_UPDATED = "Mai 2026";

export default function CGV() {
  const router = useRouter();
  return (
    <SafeAreaView style={styles.flex} edges={["top", "bottom"]}>
      <View style={styles.topBar}>
        <TouchableOpacity onPress={() => router.back()} hitSlop={10}>
          <Ionicons name="arrow-back" size={22} color={colors.textPrimary} />
        </TouchableOpacity>
        <Text style={styles.topTitle}>CONDITIONS GÉNÉRALES DE VENTE</Text>
        <View style={{ width: 22 }} />
      </View>
      <ScrollView contentContainerStyle={{ padding: 20, paddingBottom: 60 }}>
        <Text style={styles.updated}>Dernière mise à jour : {LAST_UPDATED}</Text>

        <Section title="1. Objet">
          Les présentes Conditions Générales de Vente (CGV) régissent les
          relations contractuelles entre MesureChâssis (« l'Éditeur ») et tout
          utilisateur (« le Client ») souscrivant à l'offre Pro. Elles
          définissent les droits et obligations des parties.
        </Section>

        <Section title="2. Description du service">
          MesureChâssis est une application SaaS dédiée aux entreprises de
          menuiserie permettant la prise de mesures terrain, la génération de
          fichiers techniques (PDF, Excel, CSV, JSON) et la gestion d'équipe.
          Le service est accessible via application mobile et web après
          authentification.
        </Section>

        <Section title="3. Période d'essai">
          Un essai gratuit de 90 jours est proposé à toute nouvelle société
          inscrite. À l'issue de cette période, l'accès est automatiquement
          verrouillé si aucun abonnement Pro n'a été souscrit. Les données
          restent conservées pendant 12 mois en cas de non-renouvellement.
        </Section>

        <Section title="4. Tarifs et facturation">
          L'abonnement Pro est mensuel ou annuel selon la formule choisie.
          Les tarifs en vigueur sont indiqués sur le site web de l'Éditeur et
          confirmés lors de la souscription. La facturation est récurrente
          jusqu'à résiliation. Les paiements sont sécurisés via prestataire
          tiers certifié PCI-DSS.
        </Section>

        <Section title="5. Engagement et résiliation">
          Sans engagement de durée minimale, sauf souscription d'une formule
          annuelle. La résiliation s'effectue depuis l'écran « Profil société
          » via le bouton « Se désabonner ». L'accès Pro reste actif jusqu'à
          la fin de la période payée, puis l'écran de verrouillage
          plein-écran s'active.
        </Section>

        <Section title="6. Plan Freemium (anti-fraude)">
          Les comptes gratuits sont limités à 3 chantiers sur la durée de vie
          du compte. La suppression d'un chantier ne réinitialise PAS ce
          compteur. Les exports techniques (PDF, Excel, CSV, JSON) ne sont
          accessibles qu'aux abonnés Pro.
        </Section>

        <Section title="7. Obligations du Client">
          Le Client s'engage à fournir des informations exactes lors de
          l'inscription, à conserver la confidentialité de ses identifiants,
          et à utiliser le service conformément à sa destination
          professionnelle.
        </Section>

        <Section title="8. Données et propriété intellectuelle">
          Le Client demeure propriétaire des données saisies (clients,
          mesures, photos). L'Éditeur conserve la propriété intellectuelle de
          l'application, du code source et de la marque MesureChâssis.
        </Section>

        <Section title="9. Responsabilité">
          L'Éditeur s'engage à maintenir le service en bon état de
          fonctionnement (SLA 99,5%). Sa responsabilité ne saurait être
          engagée pour les pertes indirectes, défaut de mesures terrain ou
          litiges client liés à l'usage des données générées.
        </Section>

        <Section title="10. Loi applicable">
          Les présentes CGV sont soumises au droit français. Tout litige
          relève de la compétence exclusive du Tribunal de commerce du siège
          social de l'Éditeur.
        </Section>

        <Text style={styles.contact}>
          Pour toute question : contact@mesurechassis.fr
        </Text>
      </ScrollView>
    </SafeAreaView>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      <Text style={styles.sectionBody}>{children}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: colors.bg },
  topBar: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSubtle,
  },
  topTitle: {
    color: colors.textPrimary,
    fontWeight: "900",
    letterSpacing: 1,
    fontSize: 12,
  },
  updated: {
    color: colors.textSecondary,
    fontSize: 11,
    fontStyle: "italic",
    marginBottom: 18,
  },
  section: { marginBottom: 22 },
  sectionTitle: {
    color: colors.primary,
    fontSize: 13,
    fontWeight: "900",
    letterSpacing: 0.6,
    marginBottom: 8,
  },
  sectionBody: {
    color: colors.textPrimary,
    fontSize: 13,
    lineHeight: 20,
  },
  contact: {
    color: colors.textSecondary,
    fontSize: 12,
    textAlign: "center",
    marginTop: 12,
    paddingTop: 18,
    borderTopWidth: 1,
    borderTopColor: colors.borderSubtle,
  },
});
