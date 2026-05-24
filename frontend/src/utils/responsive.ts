import { useWindowDimensions } from "react-native";

/**
 * Détection responsive basée sur la largeur de l'écran.
 *
 * Breakpoints :
 *  - mobile  : < 768 px
 *  - tablet  : >= 768 px (iPad Mini portrait minimum)
 *  - desktop : >= 1024 px (rare en RN, utile pour le mode web)
 *
 * Renvoie aussi `contentMaxWidth` pour limiter la largeur du contenu
 * principal sur les grands écrans (évite que les boutons s'étirent
 * sur toute la largeur d'un iPad Pro en paysage).
 */
export function useResponsive() {
  const { width, height } = useWindowDimensions();
  const isTablet = width >= 768;
  const isLandscape = width > height;
  const isDesktop = width >= 1024;

  // Largeur max du contenu principal pour rester lisible
  const contentMaxWidth = isTablet ? 960 : width;

  return {
    width,
    height,
    isTablet,
    isLandscape,
    isDesktop,
    contentMaxWidth,
  };
}
