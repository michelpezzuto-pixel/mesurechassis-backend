/**
 * 📱 App Version Service — v1.1.3
 *
 * Récupère la config `min_version` / `latest_version` depuis le backend
 * (endpoint public `GET /api/config/app-version`) et détermine si :
 *   - Une mise à jour est disponible (banner soft)
 *   - Une mise à jour est REQUISE (écran bloquant)
 *
 * Piloté par les vars Railway :
 *   - APP_MIN_VERSION      : min accepté (< → écran bloquant si force_update)
 *   - APP_LATEST_VERSION   : dernière dispo (< → banner soft)
 *   - APP_FORCE_UPDATE     : true pour activer le blocage
 *   - APP_UPDATE_MESSAGE   : texte affiché à l'utilisateur
 *   - APP_UPDATE_HIGHLIGHTS: liste des nouveautés (séparées par "|")
 */
import Constants from "expo-constants";
import { api } from "./api";

export type AppVersionCheck = {
  currentVersion: string;
  minVersion: string;
  latestVersion: string;
  updateAvailable: boolean; // current < latest (banner soft)
  forceUpdate: boolean;     // force_update && current < min (écran bloquant)
  message: string;
  highlights: string[];
  appStoreUrl: string;
  playStoreUrl: string | null;
};

const DEFAULT_MESSAGE =
  "Une nouvelle version de MesureChâssis est disponible. Mettez à jour pour profiter des dernières améliorations.";

// Compare deux versions semver simplifiées ("1.2.3" vs "1.2.4") — renvoie
// true si v1 < v2. Robuste aux formats bizarres (ex: "1.0" ou "1.0.0-rc1").
export function isVersionBelow(v1: string, v2: string): boolean {
  const parse = (v: string) =>
    (v || "0.0.0")
      .split("-")[0]
      .split(".")
      .map((n) => parseInt(n, 10) || 0);
  const p1 = parse(v1);
  const p2 = parse(v2);
  const len = Math.max(p1.length, p2.length);
  for (let i = 0; i < len; i++) {
    const a = p1[i] || 0;
    const b = p2[i] || 0;
    if (a < b) return true;
    if (a > b) return false;
  }
  return false;
}

// Cache mémoire pour éviter de spammer l'endpoint au démarrage
let _cache: AppVersionCheck | null = null;
let _cacheTs = 0;
const CACHE_TTL_MS = 5 * 60 * 1000; // 5 min

export async function checkAppVersion(
  options: { force?: boolean } = {},
): Promise<AppVersionCheck | null> {
  if (!options.force && _cache && Date.now() - _cacheTs < CACHE_TTL_MS) {
    return _cache;
  }

  const currentVersion =
    (Constants.expoConfig?.version as string | undefined) || "0.0.0";

  try {
    const { data } = await api.get<{
      min_version: string;
      latest_version: string;
      force_update: boolean;
      message: string;
      highlights: string[];
      app_store_url: string;
      play_store_url: string | null;
    }>("/config/app-version", { timeout: 8000 });

    const result: AppVersionCheck = {
      currentVersion,
      minVersion: data.min_version,
      latestVersion: data.latest_version,
      updateAvailable: isVersionBelow(currentVersion, data.latest_version),
      forceUpdate:
        Boolean(data.force_update) &&
        isVersionBelow(currentVersion, data.min_version),
      message: data.message || DEFAULT_MESSAGE,
      highlights: Array.isArray(data.highlights) ? data.highlights : [],
      appStoreUrl: data.app_store_url,
      playStoreUrl: data.play_store_url ?? null,
    };
    _cache = result;
    _cacheTs = Date.now();
    return result;
  } catch (err) {
    // Fallback silencieux : si le backend est down ou l'endpoint absent,
    // on ne bloque JAMAIS l'utilisateur (l'app reste 100% fonctionnelle).
    if (__DEV__) {
      console.warn("[checkAppVersion] Backend unavailable, skip update check", err);
    }
    return null;
  }
}

export function clearAppVersionCache() {
  _cache = null;
  _cacheTs = 0;
}
