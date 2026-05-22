// Auth context
import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { Auth, User } from './api';

interface Ctx {
  user: User | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<User>;
  signUp: (payload: { full_name: string; email: string; password: string; company_name?: string }) => Promise<User>;
  signOut: () => Promise<void>;
  refresh: () => Promise<void>;
}
const AuthCtx = createContext<Ctx | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    const u = await Auth.me();
    setUser(u);
  }, []);

  useEffect(() => {
    (async () => {
      await refresh();
      setLoading(false);
    })();
  }, [refresh]);

  const signIn = async (email: string, password: string) => {
    const u = await Auth.login(email, password);
    setUser(u);
    return u;
  };
  const signUp = async (payload: any) => {
    const u = await Auth.register(payload);
    setUser(u);
    return u;
  };
  const signOut = async () => {
    await Auth.logout();
    setUser(null);
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
