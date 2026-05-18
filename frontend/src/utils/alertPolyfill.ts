/**
 * Polyfill pour `react-native.Alert.alert` sur la plateforme **web**.
 *
 * Contexte : `react-native-web` implémente `Alert.alert` comme un **NO-OP**
 * (https://github.com/necolas/react-native-web/blob/master/.../Alert/index.js).
 * Conséquence : sur la preview web Emergent, **aucune** alerte ne s'affiche,
 * alors qu'elles fonctionnent parfaitement sur iOS / Android natifs.
 *
 * Ce polyfill remplace `Alert.alert` sur web par :
 *   - `window.alert(...)` pour les alertes informationnelles (0-1 bouton)
 *   - `window.confirm(...)` pour les alertes avec choix (2+ boutons) :
 *       OK déclenche le `onPress` du premier bouton non-`cancel`,
 *       Annuler déclenche le `onPress` du bouton `cancel` (s'il existe).
 *
 * Importé une seule fois dans `app/_layout.tsx` (au boot de l'app).
 */
import { Alert, Platform } from "react-native";

type AlertButton = {
  text?: string;
  style?: "default" | "cancel" | "destructive";
  onPress?: () => void;
};

if (Platform.OS === "web" && typeof window !== "undefined") {
  // @ts-expect-error - override static method
  Alert.alert = (
    title: string,
    message?: string,
    buttons?: AlertButton[]
  ): void => {
    const composed = message ? `${title}\n\n${message}` : title;
    const list = buttons && buttons.length > 0 ? buttons : [{ text: "OK" }];

    // 1 seul bouton (informationnel) → window.alert
    if (list.length === 1) {
      try {
        window.alert(composed);
      } catch {
        /* noop */
      }
      try {
        list[0]?.onPress?.();
      } catch {
        /* noop */
      }
      return;
    }

    // ≥ 2 boutons → window.confirm
    const action = list.find((b) => b.style !== "cancel") ?? list[0];
    const cancel = list.find((b) => b.style === "cancel");
    let ok = false;
    try {
      ok = window.confirm(composed);
    } catch {
      ok = false;
    }
    try {
      if (ok) {
        action?.onPress?.();
      } else if (cancel) {
        cancel?.onPress?.();
      }
    } catch {
      /* noop */
    }
  };
}

export {};
