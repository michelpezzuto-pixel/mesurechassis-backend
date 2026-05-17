import axios from "axios";
import { storage } from "@/src/utils/storage";

const BASE_URL = process.env.EXPO_PUBLIC_BACKEND_URL;
const TOKEN_KEY = "mc_access_token";

export const api = axios.create({
  baseURL: `${BASE_URL}/api`,
  timeout: 30000,
});

api.interceptors.request.use(async (config) => {
  const token = await storage.secureGet<string>(TOKEN_KEY, "");
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
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

export const PDF_URL = (chantierId: string) =>
  `${BASE_URL}/api/chantiers/${chantierId}/export.pdf`;
export const JSON_URL = (chantierId: string) =>
  `${BASE_URL}/api/chantiers/${chantierId}/export.json`;
export const XLSX_URL = (chantierId: string) =>
  `${BASE_URL}/api/chantiers/${chantierId}/export.xlsx`;
export const CSV_URL = (chantierId: string) =>
  `${BASE_URL}/api/chantiers/${chantierId}/export.csv`;
