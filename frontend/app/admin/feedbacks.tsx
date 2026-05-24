/**
 * Redirige l'ancienne route /admin/feedbacks vers la nouvelle page
 * unifiée /feedback. Conservé pour compatibilité (deep-links, cache).
 */
import { Redirect } from "expo-router";

export default function AdminFeedbacksRedirect() {
  return <Redirect href="/feedback" />;
}
