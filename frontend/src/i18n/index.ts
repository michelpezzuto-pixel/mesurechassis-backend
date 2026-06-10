/**
 * Initialisation i18n (i18next + react-i18next).
 *
 * - Détecte la langue système via `expo-localization`.
 * - Persiste le choix utilisateur dans AsyncStorage (clé `mc.lang`).
 * - Fallback : Français (FR) — langue principale du produit.
 *
 * 🆕 V3 (juin 2026) — MVP Démo i18n :
 *   • 3 langues : FR, NL, EN
 *   • Écrans traduits : auth + dashboard top bar + sélecteur dans profil
 *   • Les autres écrans restent en français le temps de valider la mécanique.
 */
import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import * as Localization from "expo-localization";
import AsyncStorage from "@react-native-async-storage/async-storage";

import fr from "./locales/fr.json";
import nl from "./locales/nl.json";
import en from "./locales/en.json";

export const SUPPORTED_LANGUAGES = ["fr", "nl", "en"] as const;
export type SupportedLanguage = (typeof SUPPORTED_LANGUAGES)[number];

const STORAGE_KEY = "mc.lang";

/** Détecte la langue à utiliser au démarrage.
 *  Priorité : AsyncStorage > Langue système > FR
 */
async function detectInitialLanguage(): Promise<SupportedLanguage> {
  try {
    const stored = await AsyncStorage.getItem(STORAGE_KEY);
    if (stored && SUPPORTED_LANGUAGES.includes(stored as SupportedLanguage)) {
      return stored as SupportedLanguage;
    }
  } catch {
    // AsyncStorage indisponible (SSR / web initial render) — on continue
  }
  try {
    const locales = Localization.getLocales();
    const sysCode = (locales[0]?.languageCode || "fr").toLowerCase();
    if (SUPPORTED_LANGUAGES.includes(sysCode as SupportedLanguage)) {
      return sysCode as SupportedLanguage;
    }
  } catch {
    // Localization indisponible
  }
  return "fr";
}

// Initialisation synchrone avec FR — puis mise à jour async via init().
void i18n.use(initReactI18next).init({
  resources: {
    fr: { translation: fr },
    nl: { translation: nl },
    en: { translation: en },
  },
  lng: "fr",
  fallbackLng: "fr",
  interpolation: { escapeValue: false },
  react: { useSuspense: false },
  compatibilityJSON: "v4",
});

// Au boot : détecte la langue et applique de manière asynchrone.
void detectInitialLanguage().then((lng) => {
  if (i18n.language !== lng) {
    void i18n.changeLanguage(lng);
  }
});

export async function setLanguage(lng: SupportedLanguage): Promise<void> {
  await i18n.changeLanguage(lng);
  try {
    await AsyncStorage.setItem(STORAGE_KEY, lng);
  } catch {
    // Ignore les erreurs de persistance
  }
}

export default i18n;
