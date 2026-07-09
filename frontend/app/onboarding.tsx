/**
 * 🚀 Onboarding — 5 slides au premier lancement (Priorité 3, juillet 2026)
 *
 * Affiché UNE SEULE FOIS (flag AsyncStorage `mc_onboarding_seen`) avant
 * l'écran de connexion. Vraies captures d'écran de l'app dans un cadre
 * téléphone stylisé + boutons « Passer » / « Suivant » / « Commencer ».
 */
import AsyncStorage from "@react-native-async-storage/async-storage";
import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import React, { useRef, useState } from "react";
import {
  Dimensions,
  FlatList,
  Image,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { colors } from "@/src/theme";

export const ONBOARDING_SEEN_KEY = "mc_onboarding_seen";

const { width: SCREEN_W, height: SCREEN_H } = Dimensions.get("window");
// Cadre téléphone : hauteur fixe (~45% écran) — les hauteurs en % ou flex
// ne fonctionnent pas dans les items d'une FlatList horizontale sur web.
const FRAME_H = Math.min(SCREEN_H * 0.45, 460);
const FRAME_W = FRAME_H * (390 / 844);

type Slide = {
  key: string;
  icon: keyof typeof Ionicons.glyphMap;
  title: string;
  description: string;
  image: any;
};

const SLIDES: Slide[] = [
  {
    key: "inscription",
    icon: "person-add",
    title: "Créez votre compte pro",
    description:
      "Artisan solo ou entreprise avec équipe : inscrivez-vous en 1 minute avec votre numéro de TVA. 100% réservé aux professionnels de la menuiserie.",
    image: require("../assets/images/onboarding/slide1_inscription.jpg"),
  },
  {
    key: "chantier",
    icon: "business",
    title: "Créez vos chantiers",
    description:
      "Un chantier = un client. Suivez chaque projet du relevé de mesures jusqu'à la fabrication, avec votre équipe ou en solo.",
    image: require("../assets/images/onboarding/slide2_chantier.jpg"),
  },
  {
    key: "cdc",
    icon: "document-text",
    title: "Importez le cahier des charges",
    description:
      "PDF, Excel ou simple photo : l'IA détecte automatiquement tous les châssis, dimensions et spécifications techniques. Rien n'est perdu.",
    image: require("../assets/images/onboarding/slide3_cdc.jpg"),
  },
  {
    key: "ouverture",
    icon: "resize",
    title: "Mesurez vos ouvertures",
    description:
      "Wizard guidé étape par étape : configuration du mur, prises de cotes, alertes automatiques. Fini les erreurs de mesure sur chantier.",
    image: require("../assets/images/onboarding/slide4_ouverture.jpg"),
  },
  {
    key: "parrainage",
    icon: "gift",
    title: "Parrainez, gagnez",
    description:
      "Partagez votre code parrain à d'autres menuisiers et gagnez 2 mois offerts sur votre prochain renouvellement. Jusqu'à 10 filleuls !",
    image: require("../assets/images/onboarding/slide5_parrainage.jpg"),
  },
];

export default function OnboardingScreen() {
  const router = useRouter();
  const listRef = useRef<FlatList<Slide>>(null);
  const [index, setIndex] = useState(0);
  const isLast = index === SLIDES.length - 1;

  const finish = async () => {
    await AsyncStorage.setItem(ONBOARDING_SEEN_KEY, "1");
    router.replace("/");
  };

  const next = () => {
    if (isLast) {
      finish();
      return;
    }
    listRef.current?.scrollToIndex({ index: index + 1, animated: true });
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top", "bottom"]}>
      {/* Header : logo + Passer */}
      <View style={styles.header}>
        <Text style={styles.brand}>MESURECHÂSSIS</Text>
        <TouchableOpacity
          onPress={finish}
          hitSlop={12}
          testID="onboarding-skip"
          activeOpacity={0.7}
        >
          <Text style={styles.skipText}>Passer</Text>
        </TouchableOpacity>
      </View>

      <FlatList
        ref={listRef}
        data={SLIDES}
        keyExtractor={(s) => s.key}
        horizontal
        pagingEnabled
        style={{ flex: 1 }}
        showsHorizontalScrollIndicator={false}
        onMomentumScrollEnd={(e) => {
          const i = Math.round(e.nativeEvent.contentOffset.x / SCREEN_W);
          setIndex(Math.max(0, Math.min(SLIDES.length - 1, i)));
        }}
        getItemLayout={(_, i) => ({
          length: SCREEN_W,
          offset: SCREEN_W * i,
          index: i,
        })}
        renderItem={({ item, index: i }) => (
          <View style={styles.slide}>
            {/* Capture d'écran dans un cadre téléphone */}
            <View style={styles.phoneFrame}>
              <Image
                source={item.image}
                style={styles.phoneImage}
                resizeMode="cover"
              />
            </View>
            <View style={styles.textBlock}>
              <View style={styles.iconBadge}>
                <Ionicons name={item.icon} size={22} color="#000" />
              </View>
              <Text style={styles.stepLabel}>
                ÉTAPE {i + 1} / {SLIDES.length}
              </Text>
              <Text style={styles.title}>{item.title}</Text>
              <Text style={styles.description}>{item.description}</Text>
            </View>
          </View>
        )}
      />

      {/* Footer : dots + Suivant */}
      <View style={styles.footer}>
        <View style={styles.dots}>
          {SLIDES.map((s, i) => (
            <View
              key={s.key}
              style={[styles.dot, i === index && styles.dotActive]}
            />
          ))}
        </View>
        <TouchableOpacity
          style={styles.nextBtn}
          onPress={next}
          activeOpacity={0.85}
          testID="onboarding-next"
        >
          <Text style={styles.nextBtnText}>
            {isLast ? "Commencer" : "Suivant"}
          </Text>
          <Ionicons
            name={isLast ? "checkmark" : "arrow-forward"}
            size={18}
            color="#000"
          />
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: "#0C0C0E" },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 20,
    paddingVertical: 12,
  },
  brand: {
    fontSize: 13,
    fontWeight: "900",
    letterSpacing: 1.5,
    color: colors.primary,
  },
  skipText: {
    fontSize: 14,
    fontWeight: "600",
    color: colors.placeholder,
    padding: 4,
  },
  slide: {
    width: SCREEN_W,
    alignItems: "center",
    paddingHorizontal: 28,
  },
  phoneFrame: {
    width: FRAME_W,
    height: FRAME_H,
    borderRadius: 24,
    borderWidth: 3,
    borderColor: "#2A2A2E",
    overflow: "hidden",
    backgroundColor: "#000",
    marginTop: 8,
  },
  phoneImage: { width: "100%", height: "100%" },
  textBlock: {
    alignItems: "center",
    paddingTop: 18,
    paddingBottom: 4,
    minHeight: 190,
  },
  iconBadge: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 10,
  },
  stepLabel: {
    fontSize: 11,
    fontWeight: "700",
    letterSpacing: 1.2,
    color: colors.placeholder,
    marginBottom: 6,
  },
  title: {
    fontSize: 22,
    fontWeight: "800",
    color: "#FFF",
    textAlign: "center",
    marginBottom: 8,
  },
  description: {
    fontSize: 14,
    lineHeight: 21,
    color: "#A6A6AD",
    textAlign: "center",
  },
  footer: {
    paddingHorizontal: 20,
    paddingTop: 10,
    paddingBottom: 8,
    gap: 16,
  },
  dots: {
    flexDirection: "row",
    justifyContent: "center",
    gap: 8,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: "#2E2E33",
  },
  dotActive: {
    backgroundColor: colors.primary,
    width: 22,
  },
  nextBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    backgroundColor: colors.primary,
    borderRadius: 14,
    paddingVertical: 15,
  },
  nextBtnText: { fontSize: 16, fontWeight: "800", color: "#000" },
});
