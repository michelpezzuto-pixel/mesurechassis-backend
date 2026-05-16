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
