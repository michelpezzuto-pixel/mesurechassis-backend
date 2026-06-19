/**
 * Écran « Centre d'aide » — wrapper simple sur ChatHelp.
 *
 * Permet d'accéder à la FAQ depuis le menu Profil sans devoir repasser par
 * le dashboard. Le modal s'ouvre automatiquement et la navigation revient
 * en arrière lorsque l'utilisateur le ferme.
 */
import React, { useState } from "react";
import { useRouter } from "expo-router";
import { ChatHelp } from "@/src/components/ChatHelp";

export default function HelpScreen() {
  const router = useRouter();
  const [visible, setVisible] = useState(true);

  const close = () => {
    setVisible(false);
    // Petit délai pour laisser l'animation de fermeture jouer
    setTimeout(() => {
      try {
        router.back();
      } catch {
        router.replace("/dashboard");
      }
    }, 200);
  };

  return (
    <ChatHelp
      visible={visible}
      onClose={close}
      onContactSupport={() => {
        setVisible(false);
        router.push("/feedback");
      }}
    />
  );
}
