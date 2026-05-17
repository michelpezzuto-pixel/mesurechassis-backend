import React, { createContext, useContext, useEffect, useState, ReactNode, useCallback } from "react";
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

export type CompanyProfile = {
  company_id: string;
  name: string;
  artisan_mode: boolean;
};

type AuthCtx = {
  user: User | null;
  company: CompanyProfile | null;
  artisanMode: boolean;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (name: string, email: string, password: string, role: Role, companyId?: string) => Promise<void>;
  signOut: () => Promise<void>;
  refreshCompany: () => Promise<void>;
  /**
   * Returns true if the current user can access functionality reserved to a role list.
   * Artisan-mode bypasses all role checks.
   */
  hasRole: (roles: Role[]) => boolean;
};

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [company, setCompany] = useState<CompanyProfile | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchCompany = useCallback(async () => {
    try {
      const res = await api.get<CompanyProfile>("/company/profile");
      setCompany(res.data);
    } catch {
      setCompany(null);
    }
  }, []);

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
        await fetchCompany();
        registerPushTokenWithBackend();
      } catch {
        await clearToken();
      } finally {
        setLoading(false);
      }
    })();
  }, [fetchCompany]);

  const signIn = async (email: string, password: string) => {
    const res = await api.post("/auth/login", { email, password });
    await saveToken(res.data.access_token);
    setUser(res.data.user);
    await fetchCompany();
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
    await fetchCompany();
    registerPushTokenWithBackend();
  };

  const signOut = async () => {
    await clearToken();
    setUser(null);
    setCompany(null);
  };

  const artisanMode = !!company?.artisan_mode;

  const hasRole = (roles: Role[]) => {
    if (artisanMode) return true;
    if (!user) return false;
    return roles.includes(user.role);
  };

  return (
    <Ctx.Provider
      value={{
        user,
        company,
        artisanMode,
        loading,
        signIn,
        signUp,
        signOut,
        refreshCompany: fetchCompany,
        hasRole,
      }}
    >
      {children}
    </Ctx.Provider>
  );
}

export function useAuth() {
  const c = useContext(Ctx);
  if (!c) throw new Error("useAuth must be used within AuthProvider");
  return c;
}
