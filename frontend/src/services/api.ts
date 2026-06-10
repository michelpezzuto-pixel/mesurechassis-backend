import axios from "axios";
import { storage } from "@/src/utils/storage";

const BASE_URL = process.env.EXPO_PUBLIC_BACKEND_URL;
const TOKEN_KEY = "mc_access_token";

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

api.interceptors.response.use(
  (r) => {
    // Any successful call proves subscription is healthy → clear paywall
    subscriptionListeners.forEach((cb) => cb({ expired: false }));
    return r;
  },
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

export const PDF_URL = (chantierId: string) =>
  `${BASE_URL}/api/chantiers/${chantierId}/export.pdf`;
export const JSON_URL = (chantierId: string) =>
  `${BASE_URL}/api/chantiers/${chantierId}/export.json`;
export const XLSX_URL = (chantierId: string) =>
  `${BASE_URL}/api/chantiers/${chantierId}/export.xlsx`;
export const CSV_URL = (chantierId: string) =>
  `${BASE_URL}/api/chantiers/${chantierId}/export.csv`;
// 🆕 V3 — Exports ERP universels (CSV + XML) pour import dans Elcia, Ramasoft, etc.
export const ERP_CSV_URL = (chantierId: string) =>
  `${BASE_URL}/api/chantiers/${chantierId}/export-erp.csv`;
export const ERP_XML_URL = (chantierId: string) =>
  `${BASE_URL}/api/chantiers/${chantierId}/export-erp.xml`;
