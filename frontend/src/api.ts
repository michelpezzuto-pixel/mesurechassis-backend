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
  async updateProfile(payload: { full_name?: string; company_name?: string; solo_mode?: boolean }) {
    const { data } = await api.put('/auth/me', payload);
    return data as User;
  },
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
  assign: async (id: string, technicien_id: string) => (await api.post(`/projects/${id}/assign`, { technicien_id })).data,
};

export const Measurements = {
  save: async (pid: string, payload: any) => (await api.post(`/projects/${pid}/measurement`, payload)).data,
  preview: async (pid: string, payload: any) => (await api.post(`/projects/${pid}/measurement/preview`, payload)).data,
  validate: async (pid: string) => (await api.post(`/projects/${pid}/measurement/validate`)).data,
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
  pdfUrl: (id: string) => `${BASE}/api/projects/${id}/export/pdf`,
  dxfUrl: (id: string) => `${BASE}/api/projects/${id}/export/dxf`,
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
