import axios from "axios";
import Constants from "expo-constants";
import { storage } from "@/src/utils/storage";

const BASE_URL = process.env.EXPO_PUBLIC_BACKEND_URL;
const TOKEN_KEY = "mc_access_token";

// 📱 v1.1.3 — Version installée sur l'appareil, envoyée à toutes les requêtes
// via l'entête X-App-Version. Le backend l'utilise pour tracker qui reste
// sur d'anciennes versions et afficher la bannière/écran de mise à jour.
const APP_VERSION: string =
  (Constants.expoConfig?.version as string | undefined) || "0.0.0";

/**
 * Clé API statique partagée — couche de sécurité supplémentaire au-dessus
 * du JWT Bearer (défense en profondeur). Validée côté proxy PHP avant
 * d'atteindre le FastAPI. La vraie valeur est dans `.env` :
 *   EXPO_PUBLIC_API_KEY=...
 * Si la variable n'est pas définie (dev local), on n'envoie pas l'en-tête.
 */
const API_KEY: string | undefined = process.env.EXPO_PUBLIC_API_KEY;
const HAS_API_KEY = !!API_KEY && API_KEY !== "__REPLACE_ME_WITH_REAL_X_API_KEY__";

export const api = axios.create({
  baseURL: `${BASE_URL}/api`,
  timeout: 30000,
});

api.interceptors.request.use(async (config) => {
  if (!config.headers) {
    // axios v1 type: AxiosHeaders. Cast pour rester compatible avec les
    // setters via assignation directe.
    config.headers = {} as any;
  }
  const token = await storage.secureGet<string>(TOKEN_KEY, "");
  if (token) {
    (config.headers as any).Authorization = `Bearer ${token}`;
  }
  // 🔐 X-API-Key — défense en profondeur, validée par le proxy PHP avant
  // de toucher le FastAPI. Toujours envoyée si la clé est définie en env.
  if (HAS_API_KEY) {
    (config.headers as any)["X-API-Key"] = API_KEY;
  }
  // 📱 v1.1.3 — Version installée du client mobile (pour tracking + banner update)
  (config.headers as any)["X-App-Version"] = APP_VERSION;
  return config;
});

// Subscription-lock event bus — subscribed by AuthContext for paywall display
type SubscriptionState = {
  expired: boolean;
  status?: string;
  expires_at?: string;
};
const subscriptionListeners = new Set<(s: SubscriptionState) => void>();
export function onSubscriptionState(cb: (s: SubscriptionState) => void) {
  subscriptionListeners.add(cb);
  return () => subscriptionListeners.delete(cb);
}

// 🔒 PAYWALL_VALIDATION_REQUIRED (403) — event bus dédié.
// Cas où l'abonnement de la société est OK, mais le compte individuel de
// l'utilisateur n'est pas (encore) validé par son gérant (Phase 2 —
// double-validation Freemium/Team). Différent de subscription_expired (402).
type ValidationState = {
  required: boolean;
  message?: string;
  reason?: string;
};
const validationListeners = new Set<(s: ValidationState) => void>();
export function onValidationRequired(cb: (s: ValidationState) => void) {
  validationListeners.add(cb);
  return () => validationListeners.delete(cb);
}

// Session-expired event bus — souscrit par AuthContext pour forcer la
// déconnexion propre quand le JWT est expiré/invalide (401).
const authExpiredListeners = new Set<() => void>();
export function onAuthExpired(cb: () => void) {
  authExpiredListeners.add(cb);
  return () => authExpiredListeners.delete(cb);
}

api.interceptors.response.use(
  // ⚠️ Ne JAMAIS effacer le verrou paywall sur un simple succès : les
  // endpoints non soumis à l'abonnement (auth/me, company/profile, push
  // token…) réussissent même pour un compte expiré, ce qui démontait le
  // PaywallScreen et laissait apparaître une alerte "Chargement impossible"
  // (rejet Apple 2.1a, Build 114). Le verrou n'est levé que par
  // fetchCompany() (AuthContext) ou signOut().
  (r) => r,
  (err) => {
    if (err?.response?.status === 402) {
      const d = err.response.data?.detail ?? {};
      if (d?.code === "subscription_expired") {
        subscriptionListeners.forEach((cb) =>
          cb({
            expired: true,
            status: d.subscription_status,
            expires_at: d.subscription_expires_at,
          })
        );
      }
    }
    // 🔒 403 PAYWALL_VALIDATION_REQUIRED — le compte utilisateur nécessite
    // une approbation par le gérant/admin de son organisation avant de
    // pouvoir continuer à utiliser l'app (Phase 2).
    if (err?.response?.status === 403) {
      const d = err.response.data?.detail ?? {};
      if (d?.code === "PAYWALL_VALIDATION_REQUIRED") {
        validationListeners.forEach((cb) =>
          cb({
            required: true,
            message: d.message,
            reason: d.reason,
          })
        );
      }
    }
    // 🔐 401 = JWT expiré/invalide → déconnexion automatique (sauf sur les
    // routes d'auth elles-mêmes : un mauvais mot de passe ne doit pas
    // déclencher de signOut global).
    if (err?.response?.status === 401) {
      const url = String(err.config?.url || "");
      const isAuthRoute =
        url.includes("/auth/login") ||
        url.includes("/auth/register") ||
        url.includes("/auth/verify") ||
        url.includes("/invitations");
      if (!isAuthRoute) {
        authExpiredListeners.forEach((cb) => cb());
      }
    }
    return Promise.reject(err);
  }
);

export async function saveToken(token: string) {
  await storage.secureSet(TOKEN_KEY, token);
}

export async function getToken(): Promise<string | null> {
  const t = await storage.secureGet<string>(TOKEN_KEY, "");
  return t && t.length > 0 ? t : null;
}

export async function clearToken() {
  await storage.secureRemove(TOKEN_KEY);
}

/**
 * 🔐 Construit les en-têtes d'authentification pour les appels `fetch()` /
 * `FileSystem.downloadAsync()` qui ne passent PAS par l'instance axios
 * (typiquement : téléchargement de fichiers binaires PDF / XLSX / etc.).
 *
 * Inclut :
 *  - `Authorization: Bearer <jwt>` si un token est stocké
 *  - `X-API-Key: <key>` si la clé est définie en variable d'env
 *
 * À toujours préférer à `{ Authorization: ... }` brut pour rester aligné
 * sur le proxy PHP de production.
 */
export async function buildAuthHeaders(): Promise<Record<string, string>> {
  const headers: Record<string, string> = {};
  const token = await getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (HAS_API_KEY) headers["X-API-Key"] = API_KEY as string;
  return headers;
}

/** Renvoie la clé API si elle est configurée (utile pour les diagnostics). */
export function getApiKey(): string | null {
  return HAS_API_KEY ? (API_KEY as string) : null;
}

export const PDF_URL = (chantierId: string, lang?: string) => {
  const base = `${BASE_URL}/api/chantiers/${chantierId}/export.pdf`;
  return lang ? `${base}?lang=${encodeURIComponent(lang)}` : base;
};
export const JSON_URL = (chantierId: string) =>
  `${BASE_URL}/api/chantiers/${chantierId}/export.json`;
export const XLSX_URL = (chantierId: string, lang?: string) => {
  const base = `${BASE_URL}/api/chantiers/${chantierId}/export.xlsx`;
  return lang ? `${base}?lang=${encodeURIComponent(lang)}` : base;
};
export const CSV_URL = (chantierId: string, lang?: string) => {
  const base = `${BASE_URL}/api/chantiers/${chantierId}/export.csv`;
  return lang ? `${base}?lang=${encodeURIComponent(lang)}` : base;
};
// 🆕 V3 — Exports ERP universels (CSV + XML) pour import dans Elcia, Ramasoft, etc.
export const ERP_CSV_URL = (chantierId: string) =>
  `${BASE_URL}/api/chantiers/${chantierId}/export-erp.csv`;
export const ERP_XML_URL = (chantierId: string) =>
  `${BASE_URL}/api/chantiers/${chantierId}/export-erp.xml`;
