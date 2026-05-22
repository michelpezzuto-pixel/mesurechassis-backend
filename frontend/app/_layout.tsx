import React, { useEffect } from 'react';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { AuthProvider } from '@/src/auth';
import { C } from '@/src/theme';
import { checkForOtaUpdate } from '@/src/utils/updates';

export default function RootLayout() {
  // EAS Update — vérifie en arrière-plan au démarrage (no-op en dev / Expo Go)
  useEffect(() => { checkForOtaUpdate(true); }, []);

  return (
    <GestureHandlerRootView style={{ flex: 1, backgroundColor: C.DARK }}>
      <SafeAreaProvider>
        <AuthProvider>
          <StatusBar style="light" />
          <Stack
            screenOptions={{
              headerShown: false,
              contentStyle: { backgroundColor: C.DARK },
              animation: 'fade',
            }}
          />
        </AuthProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
