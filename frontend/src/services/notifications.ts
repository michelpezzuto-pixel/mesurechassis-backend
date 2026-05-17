import { Platform } from "react-native";
import { api } from "@/src/services/api";

/**
 * expo-notifications n'étant pas supporté sur Web, on évite tout import
 * (et tout side-effect) du module quand on tourne dans un navigateur.
 * Cela supprime le warning de console
 * "[expo-notifications] Listening to push token changes is not yet fully
 *  supported on web. Adding a listener will have no effect."
 */
async function setupHandlerNative(): Promise<void> {
  // Import dynamique : Metro/Webpack n'évaluera ce module que sur natif.
  const Notifications = await import("expo-notifications");
  Notifications.setNotificationHandler({
    handleNotification: async () => ({
      shouldShowBanner: true,
      shouldShowList: true,
      shouldPlaySound: true,
      shouldSetBadge: true,
    }),
  });
}

if (Platform.OS !== "web") {
  // Fire-and-forget : on n'attend pas l'init du handler côté natif.
  setupHandlerNative().catch(() => {
    /* noop */
  });
}

export async function registerPushTokenWithBackend(): Promise<string | null> {
  if (Platform.OS === "web") return null;
  try {
    const Device = await import("expo-device");
    if (!Device.isDevice) return null;
    const Notifications = await import("expo-notifications");
    const Constants = (await import("expo-constants")).default;

    const { status: existing } = await Notifications.getPermissionsAsync();
    let final = existing;
    if (existing !== "granted") {
      const { status } = await Notifications.requestPermissionsAsync();
      final = status;
    }
    if (final !== "granted") return null;

    if (Platform.OS === "android") {
      await Notifications.setNotificationChannelAsync("default", {
        name: "MesureChâssis",
        importance: Notifications.AndroidImportance.HIGH,
        vibrationPattern: [0, 250, 250, 250],
        lightColor: "#FF5A00",
      });
    }
    const projectId =
      Constants.expoConfig?.extra?.eas?.projectId ??
      Constants.easConfig?.projectId;
    const tokenRes = await Notifications.getExpoPushTokenAsync(
      projectId ? { projectId } : undefined
    );
    const token = tokenRes.data;
    await api.post("/auth/push-token", { push_token: token });
    return token;
  } catch {
    // Expo Go SDK 53+ no longer supports remote push: silently ignore
    return null;
  }
}
