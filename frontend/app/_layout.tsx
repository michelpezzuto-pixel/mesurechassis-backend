import { useEffect } from "react";
import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { AuthProvider } from "@/src/context/AuthContext";
import { startQueueAutoSync } from "@/src/services/offlineQueue";
// ⚠️ Side-effect import: patches `Alert.alert` on web (no-op in RNW) so the
// pedagogical popups (RBAC, fabrication lock…) are visible on the web preview.
import "@/src/utils/alertPolyfill";

export default function RootLayout() {
  useEffect(() => {
    const unsub = startQueueAutoSync();
    return () => unsub();
  }, []);

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <AuthProvider>
          <StatusBar style="light" />
          <Stack
            screenOptions={{
              headerStyle: { backgroundColor: "#0C0C0E" },
              headerTintColor: "#fff",
              headerTitleStyle: { fontWeight: "900", letterSpacing: 0.5 },
              headerBackTitle: "",
              headerBackTitleVisible: false,
              contentStyle: { backgroundColor: "#0C0C0E" },
            }}
          >
            <Stack.Screen name="index" options={{ headerShown: false }} />
            <Stack.Screen name="dashboard" options={{ headerShown: false }} />
            <Stack.Screen name="chantier/[id]/index" options={{ title: "CHANTIER" }} />
            <Stack.Screen name="chantier/[id]/new-mesure" options={{ title: "NOUVELLE OUVERTURE" }} />
            <Stack.Screen name="chantier/[id]/closure" options={{ title: "CLÔTURE" }} />
            <Stack.Screen name="chantier/[id]/pdf-preview" options={{ headerShown: false }} />
            <Stack.Screen name="chantier/[id]/xlsx-preview" options={{ headerShown: false }} />
            <Stack.Screen name="chantier/[id]/json-preview" options={{ headerShown: false }} />
            <Stack.Screen name="admin/feedbacks" options={{ headerShown: false }} />
            <Stack.Screen name="admin/stats" options={{ headerShown: false }} />
            <Stack.Screen name="admin/team" options={{ headerShown: false }} />
            <Stack.Screen name="feedback" options={{ headerShown: false }} />
            <Stack.Screen name="company-profile" options={{ headerShown: false }} />
          </Stack>
        </AuthProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
