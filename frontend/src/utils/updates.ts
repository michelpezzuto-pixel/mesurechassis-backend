/**
 * OTA Updates via expo-updates. Au démarrage de l'app on vérifie silencieusement
 * si une nouvelle version JS a été publiée. Si oui on télécharge et on prompt l'utilisateur
 * pour relancer immédiatement (ou différer au prochain démarrage).
 *
 * Ne fonctionne QU'EN BUILD EAS (pas dans Expo Go).
 * Configure d'abord ton projet EAS : `eas init` puis `eas update:configure`.
 */
import * as Updates from 'expo-updates';
import { Alert } from 'react-native';

export async function checkForOtaUpdate(promptUser = true): Promise<void> {
  if (__DEV__) return; // skip in dev / Expo Go
  if (!Updates.isEnabled) return;
  try {
    const update = await Updates.checkForUpdateAsync();
    if (!update.isAvailable) return;
    await Updates.fetchUpdateAsync();
    if (promptUser) {
      Alert.alert(
        'Mise à jour disponible',
        "Une mise à jour corrective vient d'être téléchargée. Relancer l'app maintenant ?",
        [
          { text: 'Plus tard', style: 'cancel' },
          { text: 'Relancer', onPress: () => Updates.reloadAsync() },
        ],
      );
    } else {
      // Auto-reload at next launch
      await Updates.reloadAsync();
    }
  } catch (err) {
    // Silent fail — pas critique
    if (__DEV__) console.warn('[OTA] check failed:', err);
  }
}
