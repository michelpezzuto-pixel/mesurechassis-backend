// API client
import axios from 'axios';
import { storage } from '@/src/utils/storage';

const BASE = process.env.EXPO_PUBLIC_BACKEND_URL || '';

export const api = axios.create({
  baseURL: `${BASE}/api`,
  timeout: 30000,
});

const TOKEN_KEY = 'me_token';

export async function setToken(token: string | null) {
  if (token) await storage.secureSet(TOKEN_KEY, token);
  else await storage.secureRemove(TOKEN_KEY);
}
export async function getToken(): Promise<string | null> {
  return await storage.secureGet(TOKEN_KEY, '');
}

api.interceptors.request.use(async (config) => {
  const t = await getToken();
  if (t) config.headers.Authorization = `Bearer ${t}`;
  return config;
});

export type Role = 'admin' | 'commercial' | 'technicien';
export interface User {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  company_name?: string;
  solo_mode?: boolean;
  company_logo_base64?: string | null;
  // Trial / subscription state
  trial_start_date?: string;
  trial_days_remaining?: number;
  is_trial_active?: boolean;
  subscription_active?: boolean;
  is_locked?: boolean;
}
export interface ProjectPhoto {
  id: string;
  base64: string;
  caption: string;
  created_at: string;
}
export interface Project {
  id: string;
  client_nom: string;
  client_prenom?: string;
  address: string;
  postal_code?: string;
  city?: string;
  phone?: string;
  notes?: string;
  appointment_date?: string | null;
  status: string;
  commercial_id: string;
  technicien_id?: string | null;
  company_name?: string;
  locked: boolean;
  created_at: string;
  updated_at: string;
  photos?: ProjectPhoto[];
}

export const Auth = {
  async login(email: string, password: string) {
    const { data } = await api.post('/auth/login', { email, password });
    await setToken(data.token);
    return data.user as User;
  },
  async register(payload: { full_name: string; email: string; password: string; company_name?: string }) {
    const { data } = await api.post('/auth/register', payload);
    await setToken(data.token);
    return data.user as User;
  },
  async me(): Promise<User | null> {
    try {
      const { data } = await api.get('/auth/me');
      return data;
    } catch {
      return null;
    }
  },
  async logout() {
    await setToken(null);
  },
  async updateProfile(payload: {
    full_name?: string;
    company_name?: string;
    solo_mode?: boolean;
    company_logo_base64?: string | null;
  }) {
    const { data } = await api.put('/auth/me', payload);
    return data as User;
  },
};

export const Photos = {
  list: async (pid: string) => (await api.get(`/projects/${pid}/photos`)).data as ProjectPhoto[],
  add: async (pid: string, base64: string, caption?: string) =>
    (await api.post(`/projects/${pid}/photos`, { base64, caption: caption || '' })).data as ProjectPhoto,
  updateCaption: async (pid: string, photoId: string, caption: string) =>
    (await api.patch(`/projects/${pid}/photos/${photoId}`, { caption })).data,
  remove: async (pid: string, photoId: string) =>
    (await api.delete(`/projects/${pid}/photos/${photoId}`)).data,
};

export const Projects = {
  list: async (status?: string) => {
    const { data } = await api.get('/projects', { params: status && status !== 'tous' ? { status_filter: status } : {} });
    return data as Project[];
  },
  get: async (id: string) => (await api.get(`/projects/${id}`)).data,
  create: async (payload: Partial<Project>) => (await api.post('/projects', payload)).data as Project,
  update: async (id: string, payload: Partial<Project>) => (await api.put(`/projects/${id}`, payload)).data as Project,
  remove: async (id: string) => (await api.delete(`/projects/${id}`)).data,
  transmit: async (id: string) => (await api.post(`/projects/${id}/transmit`)).data,
  unlock:   async (id: string) => (await api.post(`/projects/${id}/unlock`)).data,
  assign: async (id: string, technicien_id: string) => (await api.post(`/projects/${id}/assign`, { technicien_id })).data,
};

// ── Measurements API (V1 legacy) supprimée — utiliser Stairs.* (V2) à la place ──

// ── Multi-stair v2 (Stairs > Niveaux > Tronçons) ─────────────────────────
export type TronconType = 'droit' | 'palier' | 'quart_bas' | 'quart_haut';
/**
 * Formes officielles d'escalier :
 * - 'droit'           → 1 volée linéaire (UI ultra-épurée : H/L/Long)
 * - 'quart_tournant'  → 1/4 tournant (UI multi-section avec 1 quart-tournant)
 * - 'demi_tournant'   → 2/4 tournant (UI multi-section avec 2 quart-tournants ou palier intermédiaire)
 * - 'helicoidal'      → escalier hélicoïdal (UI dédiée — bientôt disponible)
 * - 'tournant'        → alias de rétrocompat V2.0 (== quart_tournant par défaut)
 */
export type StairShape = 'droit' | 'quart_tournant' | 'demi_tournant' | 'helicoidal' | 'tournant';

export interface ApiTroncon { id: string; type: TronconType; longueur_mm: number; largeur_mm: number; order: number }
export interface ApiNiveau  {
  id: string;
  label: string;
  floor_index: number;          // -3..+7 (0=RDC)
  is_ghost: boolean;            // "Pas d'escalier ici"
  hauteur_mm: number;           // HT — Hauteur Totale
  sol_fini: boolean;            // niveau bas fini ?
  reserve_mm: number;
  // Champs liés HT/ED/HSP (mai 2025)
  epaisseur_dalle_mm: number;        // ED
  hauteur_sous_plafond_mm: number;   // HSP = HT - ED
  entry_mode: 'hauteur' | 'hsp';     // quel champ a été saisi par l'utilisateur
  troncons: ApiTroncon[];
  order: number;
}
export interface ApiStair {
  id: string;
  name: string;
  shape: StairShape;
  niveaux: ApiNiveau[];
  created_at: string;
  updated_at: string;
}

// Floor index helpers (mirror du backend)
export function floorIndexToLabel(idx: number): string {
  if (idx === 0) return 'RDC';
  if (idx === -1) return 'Sous-sol';
  if (idx < 0) return `Sous-sol ${idx}`;
  return `R+${idx}`;
}
export const FLOOR_INDEX_RANGE: number[] = [-3, -2, -1, 0, 1, 2, 3, 4, 5, 6, 7];

export interface StairCompute {
  stair_id: string; name: string; n_niveaux: number;
  total_height: number; total_steps: number; total_reculement: number; limon_length: number;
  niveaux_calc: Array<{
    niveau_id: string; label: string; hauteur_mm: number; hauteur_effective: number;
    n_steps_niveau: number; h: number; g: number; blondel_value: number; valid_blondel: boolean;
    slope_angle: number; total_reculement_marches: number; total_reculement_paliers: number; total_reculement: number;
    troncons_calc: Array<{ troncon_id: string; type: TronconType; longueur_mm: number; n_marches: number }>;
    warnings: string[];
  }>;
  warnings: string[];
}

export const Stairs = {
  list: async (pid: string) => (await api.get(`/projects/${pid}/stairs`)).data as ApiStair[],
  create: async (pid: string, payload: { name: string; shape: StairShape }) =>
    (await api.post(`/projects/${pid}/stairs`, payload)).data as ApiStair,
  get: async (pid: string, sid: string) => (await api.get(`/projects/${pid}/stairs/${sid}`)).data as ApiStair,
  update: async (pid: string, sid: string, patch: { name?: string; shape?: StairShape }) =>
    (await api.patch(`/projects/${pid}/stairs/${sid}`, patch)).data as ApiStair,
  rename: async (pid: string, sid: string, name: string) => (await api.patch(`/projects/${pid}/stairs/${sid}`, { name })).data,
  remove: async (pid: string, sid: string) => (await api.delete(`/projects/${pid}/stairs/${sid}`)).data,
  compute: async (pid: string, sid: string) => (await api.get(`/projects/${pid}/stairs/${sid}/compute`)).data as StairCompute,

  addNiveau: async (pid: string, sid: string, niveau: {
    floor_index: number;
    is_ghost?: boolean;
    label?: string;
    hauteur_mm: number;
    sol_fini: boolean;
    reserve_mm?: number;
  }) =>
    (await api.post(`/projects/${pid}/stairs/${sid}/niveaux`, niveau)).data as ApiNiveau,
  updateNiveau: async (pid: string, sid: string, nid: string, patch: Partial<ApiNiveau>) =>
    (await api.patch(`/projects/${pid}/stairs/${sid}/niveaux/${nid}`, patch)).data as ApiNiveau,
  removeNiveau: async (pid: string, sid: string, nid: string) =>
    (await api.delete(`/projects/${pid}/stairs/${sid}/niveaux/${nid}`)).data,

  addTroncon: async (pid: string, sid: string, nid: string, t: { type: TronconType; longueur_mm: number; largeur_mm?: number }) =>
    (await api.post(`/projects/${pid}/stairs/${sid}/niveaux/${nid}/troncons`, t)).data as ApiTroncon,
  updateTroncon: async (pid: string, sid: string, nid: string, tid: string, patch: Partial<ApiTroncon>) =>
    (await api.patch(`/projects/${pid}/stairs/${sid}/niveaux/${nid}/troncons/${tid}`, patch)).data as ApiTroncon,
  removeTroncon: async (pid: string, sid: string, nid: string, tid: string) =>
    (await api.delete(`/projects/${pid}/stairs/${sid}/niveaux/${nid}/troncons/${tid}`)).data,
};

export const Team = {
  list: async () => (await api.get('/users')).data as User[],
  invite: async (payload: { full_name: string; email: string; password: string; role?: 'technicien' }) =>
    (await api.post('/users', { ...payload, role: payload.role || 'technicien' })).data as User,
  remove: async (id: string) => (await api.delete(`/users/${id}`)).data,
};

export const Stats = {
  get: async () => (await api.get('/stats')).data as {
    total_projects: number;
    by_status: Record<string, number>;
    total_measurements: number;
    validated_measurements: number;
    average_steps: number | null;
    team_size: number | null;
  },
};

export const Exports = {
  pdfUrl: (id: string, opts?: { stair_id?: string; include_photos?: boolean; include_notes?: boolean; include_logo?: boolean }) => {
    const params = new URLSearchParams();
    if (opts?.stair_id) params.set('stair_id', opts.stair_id);
    if (opts?.include_photos !== undefined) params.set('include_photos', String(opts.include_photos));
    if (opts?.include_notes !== undefined) params.set('include_notes', String(opts.include_notes));
    if (opts?.include_logo !== undefined) params.set('include_logo', String(opts.include_logo));
    const qs = params.toString();
    return `${BASE}/api/projects/${id}/export/pdf${qs ? `?${qs}` : ''}`;
  },
  dxfUrl: (id: string, opts?: { stair_id?: string }) => {
    const params = new URLSearchParams();
    if (opts?.stair_id) params.set('stair_id', opts.stair_id);
    const qs = params.toString();
    return `${BASE}/api/projects/${id}/export/dxf${qs ? `?${qs}` : ''}`;
  },
};

export const Voice = {
  transcribe: async (uri: string) => {
    const form = new FormData();
    // @ts-ignore - RN multipart
    form.append('audio', { uri, name: 'voice.m4a', type: 'audio/m4a' });
    const t = await getToken();
    const r = await fetch(`${BASE}/api/transcribe`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${t}` },
      body: form as any,
    });
    if (!r.ok) throw new Error('Échec transcription');
    return (await r.json()) as { text: string };
  },
};
