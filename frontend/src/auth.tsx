// Auth context — avec cache local pour éviter de bloquer l'écran sur /auth/me au cold start.
import React, { createContext, useContext, useEffect, useState, useCallback, useRef } from 'react';
import { Auth, User } from './api';
import { storage } from './utils/storage';

interface Ctx {
  user: User | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<User>;
  signUp: (payload: { full_name: string; email: string; password: string; company_name?: string }) => Promise<User>;
  signOut: () => Promise<void>;
  refresh: () => Promise<void>;
}
const AuthCtx = createContext<Ctx | null>(null);

const USER_CACHE_KEY = 'me_user_cache';

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  // Pour éviter les re-fetch en boucle dans la même session
  const hasFetchedRef = useRef(false);

  // Refresh appelle l'API et met à jour le cache local (transparent)
  const refresh = useCallback(async () => {
    try {
      const u = await Auth.me();
      setUser(u);
      // Persiste le user pour le prochain cold start
      await storage.setItem(USER_CACHE_KEY, JSON.stringify(u));
    } catch {
      // Token invalide ou réseau : on garde le cache si présent
    }
  }, []);

  useEffect(() => {
    if (hasFetchedRef.current) return;
    hasFetchedRef.current = true;
    (async () => {
      // 1) Charge l'user depuis le cache local immédiatement (rendu instantané)
      try {
        const cached = await storage.getItem(USER_CACHE_KEY, '' as string);
        if (cached && typeof cached === 'string') {
          const parsed = JSON.parse(cached) as User;
          if (parsed?.id) setUser(parsed);
        }
      } catch { /* ignore */ }
      setLoading(false);
      // 2) Rafraîchit en arrière-plan sans bloquer l'UI
      refresh().catch(() => {});
    })();
  }, [refresh]);

  const signIn = async (email: string, password: string) => {
    const u = await Auth.login(email, password);
    setUser(u);
    await storage.setItem(USER_CACHE_KEY, JSON.stringify(u));
    return u;
  };
  const signUp = async (payload: any) => {
    const u = await Auth.register(payload);
    setUser(u);
    await storage.setItem(USER_CACHE_KEY, JSON.stringify(u));
    return u;
  };
  const signOut = async () => {
    await Auth.logout();
    setUser(null);
    await storage.removeItem(USER_CACHE_KEY);
    await storage.removeItem('me_projects_cache');
  };

  return (
    <AuthCtx.Provider value={{ user, loading, signIn, signUp, signOut, refresh }}>
      {children}
    </AuthCtx.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthCtx);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
