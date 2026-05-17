import React, { createContext, useContext, useEffect, useState, ReactNode, useCallback } from "react";
import { api, clearToken, getToken, onSubscriptionState, saveToken } from "@/src/services/api";
import { registerPushTokenWithBackend } from "@/src/services/notifications";
import PaywallScreen from "@/src/components/PaywallScreen";

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
  subscription_status?: string;
  subscription_expires_at?: string;
  plan?: "free" | "trial" | "pro";
  chantiers_lifetime_count?: number;
  cancel_at_period_end?: boolean;
  cancelled_at?: string | null;
};

export type SubscriptionLock = {
  expired: boolean;
  status?: string;
  expires_at?: string;
};

type AuthCtx = {
  user: User | null;
  company: CompanyProfile | null;
  artisanMode: boolean;
  loading: boolean;
  lock: SubscriptionLock;
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
  const [lock, setLock] = useState<SubscriptionLock>({ expired: false });

  // Subscribe to subscription lock events from the axios response interceptor.
  useEffect(() => {
    const off = onSubscriptionState((s) => setLock(s));
    return () => { off(); };
  }, []);

  const fetchCompany = useCallback(async () => {
    try {
      const res = await api.get<CompanyProfile>("/company/profile");
      setCompany(res.data);
      // Apply subscription state from profile (initial / refresh)
      const status = res.data?.subscription_status;
      const exp = res.data?.subscription_expires_at;
      const expired = (() => {
        if (status === "suspended") return true;
        if (!exp) return false;
        try { return new Date(exp).getTime() < Date.now(); } catch { return false; }
      })();
      setLock({ expired, status, expires_at: exp });
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
        lock,
        signIn,
        signUp,
        signOut,
        refreshCompany: fetchCompany,
        hasRole,
      }}
    >
      {/* Subscription paywall — covers everything when expired/suspended */}
      {user && lock.expired ? (
        <PaywallScreen
          status={lock.status}
          expires_at={lock.expires_at}
          onContactSupport={() => {
            const subject = encodeURIComponent("MesureChâssis — Régularisation abonnement");
            const body = encodeURIComponent(
              `Bonjour,\n\nMon compte (${user.email}) est verrouillé (${lock.status ?? "expiré"}).\nMerci de régulariser mon abonnement.\n\nSociété : ${user.company_id}`
            );
            if (typeof window !== "undefined") {
              try { window.location.href = `mailto:support@mesurechassis.fr?subject=${subject}&body=${body}`; } catch { /* noop */ }
            }
          }}
          onLogout={signOut}
        />
      ) : (
        children
      )}
    </Ctx.Provider>
  );
}

export function useAuth() {
  const c = useContext(Ctx);
  if (!c) throw new Error("useAuth must be used within AuthProvider");
  return c;
}
