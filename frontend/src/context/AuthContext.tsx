import React, { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { api, clearToken, getToken, saveToken } from "@/src/services/api";
import { registerPushTokenWithBackend } from "@/src/services/notifications";

export type Role = "admin" | "commercial" | "technician";

export type User = {
  id: string;
  name: string;
  email: string;
  role: Role;
  company_id: string;
};

type AuthCtx = {
  user: User | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (name: string, email: string, password: string, role: Role, companyId?: string) => Promise<void>;
  signOut: () => Promise<void>;
};

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      const token = await getToken();
      if (!token) {
        setLoading(false);
        return;
      }
      try {
        const res = await api.get<User>("/auth/me");
        setUser(res.data);
        registerPushTokenWithBackend();
      } catch {
        await clearToken();
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const signIn = async (email: string, password: string) => {
    const res = await api.post("/auth/login", { email, password });
    await saveToken(res.data.access_token);
    setUser(res.data.user);
    registerPushTokenWithBackend();
  };

  const signUp = async (name: string, email: string, password: string, role: Role, companyId?: string) => {
    const res = await api.post("/auth/register", {
      name,
      email,
      password,
      role,
      company_id: companyId && companyId.length > 0 ? companyId : "default",
    });
    await saveToken(res.data.access_token);
    setUser(res.data.user);
    registerPushTokenWithBackend();
  };

  const signOut = async () => {
    await clearToken();
    setUser(null);
  };

  return (
    <Ctx.Provider value={{ user, loading, signIn, signUp, signOut }}>
      {children}
    </Ctx.Provider>
  );
}

export function useAuth() {
  const c = useContext(Ctx);
  if (!c) throw new Error("useAuth must be used within AuthProvider");
  return c;
}
