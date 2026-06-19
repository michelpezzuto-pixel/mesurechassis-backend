/**
 * Hook de traduction adapté au mode Artisan.
 *
 * Drop-in replacement de `useTranslation()` de react-i18next :
 *   • Wrappe `t()` pour post-traiter le texte selon `artisanMode`.
 *   • Retourne aussi la valeur brute `artisanMode` pour les composants qui
 *     veulent conditionner du JSX (cards, icons, etc.).
 *
 * Usage :
 *   const { t, artisanMode } = useT();
 *   <Text>{t("screens.dashboard.commercialHint")}</Text>
 *   → automatiquement transformé en mode artisan.
 */
import { useCallback } from "react";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/src/context/AuthContext";
import { adaptArtisan } from "./artisanText";

export function useT() {
  const { t: rawT, i18n } = useTranslation();
  const { artisanMode } = useAuth();

  const t = useCallback(
    (key: string, options?: Record<string, unknown>): string => {
      const value = rawT(key, options ?? {}) as unknown as string;
      return adaptArtisan(String(value), artisanMode);
    },
    [rawT, artisanMode],
  );

  return { t, artisanMode, i18n };
}
