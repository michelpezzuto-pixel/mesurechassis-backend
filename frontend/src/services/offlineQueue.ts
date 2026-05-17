import NetInfo from "@react-native-community/netinfo";
import { storage } from "@/src/utils/storage";
import { api } from "@/src/services/api";

const QUEUE_KEY = "mc_pending_mesures"; // conservé pour rétrocompat (legacy)

export type QueueKind = "mesure" | "chantier";

export type PendingItem = {
  local_id: string;
  kind: QueueKind; // "mesure" pour les anciens items sans champ kind
  endpoint: string; // ex. "/mesures", "/chantiers"
  payload: Record<string, unknown>;
  created_at: string;
};

// --- Alias rétrocompatible (ancien nom utilisé ailleurs dans l'app) -------
export type PendingMesure = PendingItem;

type Listener = (count: number) => void;
const listeners = new Set<Listener>();

function normalize(raw: any): PendingItem {
  // Migration : items créés avant l'ajout de kind/endpoint
  if (!raw.kind || !raw.endpoint) {
    return {
      local_id: raw.local_id ?? `local-${Date.now()}`,
      kind: "mesure",
      endpoint: "/mesures",
      payload: raw.payload ?? {},
      created_at: raw.created_at ?? new Date().toISOString(),
    };
  }
  return raw as PendingItem;
}

export async function getQueue(): Promise<PendingItem[]> {
  const raw = (await storage.getItem<any[]>(QUEUE_KEY, [])) ?? [];
  return raw.map(normalize);
}

async function setQueue(items: PendingItem[]): Promise<void> {
  await storage.setItem(QUEUE_KEY, items);
  listeners.forEach((l) => l(items.length));
}

export function subscribeQueueSize(listener: Listener): () => void {
  listeners.add(listener);
  getQueue().then((q) => listener(q.length));
  return () => {
    listeners.delete(listener);
  };
}

// --- Enqueue helpers ------------------------------------------------------
async function enqueue(
  kind: QueueKind,
  endpoint: string,
  payload: Record<string, unknown>,
): Promise<PendingItem> {
  const item: PendingItem = {
    local_id: `local-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
    kind,
    endpoint,
    payload,
    created_at: new Date().toISOString(),
  };
  const q = await getQueue();
  q.push(item);
  await setQueue(q);
  return item;
}

export function enqueueMesure(
  payload: Record<string, unknown>,
): Promise<PendingItem> {
  return enqueue("mesure", "/mesures", payload);
}

export function enqueueChantier(
  payload: Record<string, unknown>,
): Promise<PendingItem> {
  return enqueue("chantier", "/chantiers", payload);
}

// --- Détection erreur réseau (vs erreur HTTP métier) ----------------------
export function isNetworkError(err: any): boolean {
  if (!err) return false;
  // Axios : pas de response = pas de réponse serveur (offline, DNS, timeout…)
  if (err.response) return false;
  if (err.code === "ECONNABORTED") return true;
  if (err.message && /network|timeout|fetch|failed/i.test(String(err.message))) {
    return true;
  }
  // Web : navigator.onLine false
  if (typeof navigator !== "undefined" && navigator.onLine === false) return true;
  // Mobile : pas de response signifie connexion impossible
  return !err.response;
}

let syncing = false;

export async function syncQueue(): Promise<{ ok: number; failed: number }> {
  if (syncing) return { ok: 0, failed: 0 };
  syncing = true;
  let ok = 0;
  let failed = 0;
  try {
    const q = await getQueue();
    if (q.length === 0) return { ok: 0, failed: 0 };
    const remaining: PendingItem[] = [];
    for (const item of q) {
      try {
        await api.post(item.endpoint, item.payload);
        ok += 1;
      } catch (err) {
        // On garde l'item uniquement si c'est une erreur réseau.
        // Si le backend rejette (400/422), inutile de retenter en boucle.
        if (isNetworkError(err)) {
          remaining.push(item);
          failed += 1;
        } else {
          failed += 1; // drop côté offline (déjà perdu côté serveur)
        }
      }
    }
    await setQueue(remaining);
    return { ok, failed };
  } finally {
    syncing = false;
  }
}

export function startQueueAutoSync(): () => void {
  const unsubscribe = NetInfo.addEventListener((state) => {
    if (state.isConnected && state.isInternetReachable !== false) {
      syncQueue();
    }
  });
  // Tentative au démarrage
  syncQueue();
  return unsubscribe;
}

export async function isOnline(): Promise<boolean> {
  const s = await NetInfo.fetch();
  return !!s.isConnected && s.isInternetReachable !== false;
}
