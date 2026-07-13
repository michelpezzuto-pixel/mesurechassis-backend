/**
 * 🖼️ Utilitaire cross-platform pour "enregistrer une image" affichée
 * dans l'app (Countdown, LinkedIn, etc.).
 *
 * L'appui long natif sur `<Image>` de React Native **ne déclenche pas**
 * le menu "Enregistrer l'image" du navigateur / iOS Photos par défaut.
 * On expose donc une action explicite `saveImageToDevice()` :
 *
 *   - Sur **web**  : crée un `<a href download>` invisible et clique dessus →
 *     l'utilisateur récupère l'image dans son dossier Téléchargements.
 *   - Sur **iOS/Android** : télécharge d'abord l'image via `expo-file-system`
 *     puis ouvre la feuille de partage (`expo-sharing`) → l'utilisateur peut
 *     "Enregistrer dans Photos", "Envoyer par mail", etc. Pas besoin de
 *     permission MediaLibrary (l'utilisateur choisit la destination).
 *
 * Utilisation :
 *
 *   import { saveImageToDevice } from "@/src/utils/saveImage";
 *
 *   await saveImageToDevice(
 *     "https://api.example.com/campaign/countdown/visual/15",
 *     "JetonCafe_J-15.png",
 *   );
 */
import { Alert, Platform } from "react-native";
import * as FileSystem from "expo-file-system/legacy";
import * as Sharing from "expo-sharing";

/**
 * Télécharge et sauvegarde une image sur le device (mobile) ou déclenche
 * un téléchargement navigateur (web). Retourne `true` si l'opération a
 * abouti, `false` sinon (l'utilisateur peut avoir annulé le share sheet).
 */
export async function saveImageToDevice(
  url: string,
  filename: string,
): Promise<boolean> {
  if (!url || !filename) {
    Alert.alert("Erreur", "URL ou nom de fichier manquant.");
    return false;
  }

  // ── WEB ────────────────────────────────────────────────────────────
  if (Platform.OS === "web") {
    try {
      if (typeof document === "undefined") return false;
      // Astuce : pour forcer le téléchargement (pas juste ouvrir dans un
      // onglet), on fetch l'image, la transforme en blob, puis crée un
      // objectURL. Nécessite que le serveur ait un CORS permissif — c'est
      // le cas ici (backend FastAPI + CORS wildcard).
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const objUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = objUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      // Cleanup asynchrone
      setTimeout(() => URL.revokeObjectURL(objUrl), 1000);
      return true;
    } catch (e: any) {
      // Fallback : ouvrir dans un nouvel onglet (l'utilisateur pourra faire
      // clic droit → Enregistrer).
      try {
        window.open(url, "_blank");
        return true;
      } catch {
        Alert.alert(
          "Téléchargement échoué",
          `Impossible de télécharger l'image : ${e?.message ?? e}`,
        );
        return false;
      }
    }
  }

  // ── MOBILE (iOS / Android) ────────────────────────────────────────
  try {
    // 1) Télécharger dans le cache local
    const cacheDir =
      (FileSystem as any).cacheDirectory ||
      (FileSystem as any).documentDirectory ||
      "";
    const localPath = `${cacheDir}${filename}`;
    const dl = await FileSystem.downloadAsync(url, localPath);
    if (dl.status !== 200) {
      throw new Error(`Téléchargement échoué (HTTP ${dl.status})`);
    }

    // 2) Vérifier que le sharing est dispo (iOS/Android en général oui)
    const canShare = await Sharing.isAvailableAsync();
    if (!canShare) {
      Alert.alert(
        "Partage indisponible",
        "Impossible d'ouvrir la feuille de partage sur cet appareil. " +
          "L'image a été téléchargée dans le cache de l'app.",
      );
      return false;
    }

    // 3) Ouvrir la feuille de partage — l'utilisateur choisit
    //    "Enregistrer dans Photos" (iOS) ou l'équivalent Android.
    await Sharing.shareAsync(dl.uri, {
      mimeType: "image/png",
      dialogTitle: "Enregistrer l'image",
      UTI: "public.png", // iOS uniquement, aide Photos à comprendre
    });
    return true;
  } catch (e: any) {
    Alert.alert(
      "Enregistrement impossible",
      String(e?.message ?? e ?? "Erreur inconnue"),
    );
    return false;
  }
}
