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

export default function PrivacyPolicy() {
  const router = useRouter();
  return (
    <SafeAreaView style={styles.flex} edges={["top", "bottom"]}>
      <View style={styles.topBar}>
        <TouchableOpacity onPress={() => router.back()} hitSlop={10}>
          <Ionicons name="arrow-back" size={22} color={colors.textPrimary} />
        </TouchableOpacity>
        <Text style={styles.topTitle}>POLITIQUE DE CONFIDENTIALITÉ</Text>
        <View style={{ width: 22 }} />
      </View>
      <ScrollView contentContainerStyle={{ padding: 20, paddingBottom: 60 }}>
        <Text style={styles.updated}>Dernière mise à jour : {LAST_UPDATED}</Text>

        <Section title="1. Responsable du traitement">
          MesureChâssis (« l&apos;Éditeur ») est responsable du traitement des
          données personnelles collectées via l&apos;application. Le délégué à la
          protection des données est joignable à dpo@mesurechassis.fr.
        </Section>

        <Section title="2. Données collectées">
          Nous collectons les données strictement nécessaires au
          fonctionnement du service :{"\n"}
          • Identité (nom, email, mot de passe haché){"\n"}
          • Société (nom commercial, ID){"\n"}
          • Données métier (clients, chantiers, mesures, photos anti-litige){"\n"}
          • Données techniques (logs de connexion, push tokens){"\n"}
          • Données de facturation (statut abonnement, dates)
        </Section>

        <Section title="3. Finalités">
          • Fourniture du service (gestion des chantiers et mesures){"\n"}
          • Authentification et sécurité (double opt-in, RBAC){"\n"}
          • Facturation et gestion d&apos;abonnement{"\n"}
          • Notifications push (assignation, alertes){"\n"}
          • Amélioration produit (feedbacks utilisateurs)
        </Section>

        <Section title="4. Base légale">
          Le traitement est fondé sur l&apos;exécution du contrat (CGV) et,
          pour certaines données (push tokens), sur le consentement
          explicite recueilli au moment de l&apos;autorisation du système
          d&apos;exploitation.
        </Section>

        <Section title="5. Durée de conservation">
          • Données de compte : pendant toute la durée de l&apos;abonnement
          + 12 mois après résiliation{"\n"}
          • Photos chantier : 3 ans (durée de garantie décennale){"\n"}
          • Logs techniques : 12 mois{"\n"}
          • Données de facturation : 10 ans (obligation légale)
        </Section>

        <Section title="6. Destinataires">
          Les données sont accessibles aux utilisateurs autorisés de votre
          société selon la matrice RBAC (Admin, Commercial, Technicien).
          Aucune donnée n&apos;est vendue ni transmise à des tiers, sauf
          obligations légales ou prestataires techniques sous contrat
          (hébergeur certifié ISO 27001, prestataire de paiement PCI-DSS).
        </Section>

        <Section title="7. Hébergement et transferts">
          Les données sont hébergées en Union européenne (France). Aucun
          transfert hors UE n&apos;est effectué sans garanties appropriées
          (clauses contractuelles types).
        </Section>

        <Section title="8. Sécurité">
          • Chiffrement TLS 1.3 en transit{"\n"}
          • Mots de passe hachés (bcrypt){"\n"}
          • Authentification multi-rôle (RBAC strict){"\n"}
          • Double opt-in email à l&apos;inscription{"\n"}
          • Sauvegardes quotidiennes chiffrées
        </Section>

        <Section title="9. Vos droits (RGPD)">
          Conformément au Règlement Général sur la Protection des Données,
          vous disposez des droits suivants :{"\n"}
          • Accès, rectification, effacement de vos données{"\n"}
          • Portabilité (export JSON/CSV via l&apos;application){"\n"}
          • Opposition au traitement{"\n"}
          • Limitation du traitement{"\n"}
          • Introduction d&apos;une réclamation auprès de la CNIL{"\n\n"}
          Pour exercer vos droits : dpo@mesurechassis.fr
        </Section>

        <Section title="10. Cookies">
          L&apos;application web utilise uniquement des cookies techniques
          (session JWT) strictement nécessaires au fonctionnement. Aucun
          cookie de traçage publicitaire n&apos;est déposé.
        </Section>

        <Text style={styles.contact}>
          Pour toute question relative à vos données : dpo@mesurechassis.fr
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
