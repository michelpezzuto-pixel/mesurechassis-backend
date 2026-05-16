import NetInfo from "@react-native-community/netinfo";
import { storage } from "@/src/utils/storage";
import { api } from "@/src/services/api";

const QUEUE_KEY = "mc_pending_mesures";

export type PendingMesure = {
  local_id: string;
  payload: Record<string, unknown>;
  created_at: string;
};

type Listener = (count: number) => void;
const listeners = new Set<Listener>();

export async function getQueue(): Promise<PendingMesure[]> {
  return (await storage.getItem<PendingMesure[]>(QUEUE_KEY, [])) ?? [];
}

async function setQueue(items: PendingMesure[]): Promise<void> {
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

export async function enqueueMesure(payload: Record<string, unknown>): Promise<PendingMesure> {
  const item: PendingMesure = {
    local_id: `local-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
    payload,
    created_at: new Date().toISOString(),
  };
  const q = await getQueue();
  q.push(item);
  await setQueue(q);
  return item;
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
    const remaining: PendingMesure[] = [];
    for (const item of q) {
      try {
        await api.post("/mesures", item.payload);
        ok += 1;
      } catch {
        remaining.push(item);
        failed += 1;
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
  // Try once at startup
  syncQueue();
  return unsubscribe;
}

export async function isOnline(): Promise<boolean> {
  const s = await NetInfo.fetch();
  return !!s.isConnected && s.isInternetReachable !== false;
}
