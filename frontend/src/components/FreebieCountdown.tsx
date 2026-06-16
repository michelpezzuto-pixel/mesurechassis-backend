/**
 * FreebieCountdown.tsx
 *
 * Bannière mondiale promotionnelle "Accès TOTAL GRATUIT jusqu'au 30 septembre 2026"
 * affichée en haut du dashboard. Passe automatiquement en mode urgence
 * (rouge pulsé) à partir du 16 septembre 2026 (14 derniers jours).
 *
 * Fin de la promo : 30 septembre 2026 à 23:59:59 (heure de Bruxelles).
 * Au-delà, la bannière disparaît automatiquement.
 *
 * 🍎 iOS : la bannière est masquée car la promotion est gérée
 * côté site web pour éviter toute interprétation "promotion d'abonnement"
 * dans l'app (App Store 3.1.1).
 */
import React, { useEffect, useState } from "react";
import {
  Animated,
  Easing,
  Platform,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";

// 30 septembre 2026 à 23h59:59 (Brussels, UTC+2)
const DEADLINE = new Date("2026-09-30T23:59:59+02:00").getTime();
const URGENT_THRESHOLD_MS = 14 * 24 * 60 * 60 * 1000;

function formatTimeLeft(diffMs: number): { label: string; urgent: boolean } {
  if (diffMs <= 0) return { label: "", urgent: false };
  const urgent = diffMs <= URGENT_THRESHOLD_MS;
  const d = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  const h = Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
  const m = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
  if (urgent) return { label: `${d}j ${h}h ${m}min`, urgent: true };
  return { label: `${d} jours`, urgent: false };
}

export default function FreebieCountdown() {
  const router = useRouter();
  const [diff, setDiff] = useState<number>(DEADLINE - Date.now());
  const pulse = React.useRef(new Animated.Value(0)).current;

  // Tick toutes les 30 secondes
  useEffect(() => {
    const id = setInterval(() => setDiff(DEADLINE - Date.now()), 30_000);
    return () => clearInterval(id);
  }, []);

  // Animation pulse pendant la phase urgente
  useEffect(() => {
    const urgent = diff <= URGENT_THRESHOLD_MS && diff > 0;
    if (!urgent) {
      pulse.setValue(0);
      return;
    }
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, {
          toValue: 1,
          duration: 1200,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: false,
        }),
        Animated.timing(pulse, {
          toValue: 0,
          duration: 1200,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: false,
        }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [diff, pulse]);

  // 🍎 iOS — masqué (cf. App Store 3.1.1)
  if (Platform.OS === "ios") return null;

  // Offre terminée → ne plus rien afficher
  if (diff <= 0) return null;

  const { label, urgent } = formatTimeLeft(diff);

  const bgColor = pulse.interpolate({
    inputRange: [0, 1],
    outputRange: urgent ? ["#FF3B30", "#FF6B35"] : ["#FF6B35", "#FF6B35"],
  });

  return (
    <Animated.View style={[styles.banner, { backgroundColor: bgColor }]}>
      <Ionicons name="gift" size={18} color="#fff" style={{ marginRight: 6 }} />
      <Text style={styles.text}>
        <Text style={styles.bold}>Accès TOTAL GRATUIT</Text> · Plus que{" "}
        <Text style={styles.pill}>{label}</Text>
      </Text>
      <TouchableOpacity
        onPress={() => router.push("/dashboard")}
        activeOpacity={0.7}
        style={styles.cta}
      >
        <Text style={styles.ctaText}>Profiter →</Text>
      </TouchableOpacity>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  banner: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 14,
    paddingVertical: 10,
    flexWrap: "wrap",
    gap: 6,
  },
  text: {
    color: "#fff",
    fontSize: 13,
    fontWeight: "500",
    flex: 1,
    lineHeight: 18,
  },
  bold: { fontWeight: "800" },
  pill: {
    backgroundColor: "rgba(0,0,0,0.18)",
    color: "#FFF7E6",
    fontWeight: "800",
    paddingHorizontal: 6,
    paddingVertical: 1,
    borderRadius: 6,
    overflow: "hidden",
  },
  cta: {
    backgroundColor: "rgba(255,255,255,0.18)",
    paddingHorizontal: 12,
    paddingVertical: 5,
    borderRadius: 999,
    marginLeft: 8,
  },
  ctaText: {
    color: "#fff",
    fontSize: 12,
    fontWeight: "700",
  },
});
