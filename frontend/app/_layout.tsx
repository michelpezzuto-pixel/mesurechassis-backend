import { useEffect } from "react";
import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { AuthProvider } from "@/src/context/AuthContext";
import { startQueueAutoSync } from "@/src/services/offlineQueue";

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
              contentStyle: { backgroundColor: "#0C0C0E" },
            }}
          >
            <Stack.Screen name="index" options={{ headerShown: false }} />
            <Stack.Screen name="dashboard" options={{ headerShown: false }} />
            <Stack.Screen name="chantier/[id]/index" options={{ title: "CHANTIER" }} />
            <Stack.Screen name="chantier/[id]/new-mesure" options={{ title: "NOUVELLE OUVERTURE" }} />
            <Stack.Screen name="chantier/[id]/closure" options={{ title: "CLÔTURE" }} />
            <Stack.Screen name="admin/feedbacks" options={{ title: "FEEDBACKS" }} />
            <Stack.Screen name="admin/stats" options={{ title: "STATISTIQUES" }} />
          </Stack>
        </AuthProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
