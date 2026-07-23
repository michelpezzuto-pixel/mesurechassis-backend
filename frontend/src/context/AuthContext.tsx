import React, { createContext, useContext, useEffect, useRef, useState, ReactNode, useCallback } from "react";
import { Alert } from "react-native";
import { useRouter } from "expo-router";
import { api, clearToken, getToken, onAuthExpired, onSubscriptionState, onValidationRequired, saveToken } from "@/src/services/api";
import { registerPushTokenWithBackend } from "@/src/services/notifications";
import PaywallScreen from "@/src/components/PaywallScreen";
import ValidationRequiredScreen from "@/src/components/ValidationRequiredScreen";
import CompleteVatScreen from "@/src/components/CompleteVatScreen";
import ForceUpdateScreen from "@/src/components/ForceUpdateScreen";
import { checkAppVersion, type AppVersionCheck } from "@/src/services/appVersion";
import i18n, { setArtisanMode as setI18nArtisanMode } from "@/src/i18n";

export type Role = "admin" | "commercial" | "technician";

export type User = {
  id: string;
  name: string;
  email: string;
  role: Role;
  company_id: string;
  /**
   * 🔒 Build 12 (juin 2026) — True quand l'utilisateur doit compléter
   * son numéro de TVA (typiquement après Google Sign-In). Le verrou
   * `CompleteVatScreen` s'affiche en plein écran tant que ce flag
   * est vrai. Le backend calcule la valeur dans /auth/me et
   * /auth/google/session (jamais stockée en DB).
   */
  vat_completion_required?: boolean;
};

export type CompanyProfile = {
  company_id: string;
  name: string;
  artisan_mode: boolean;
  /** Lot D — "artisan" (solo) ou "entreprise" (équipe). */
  account_type?: "artisan" | "entreprise";
  subscription_status?: string;
  subscription_expires_at?: string;
  plan?: "free" | "trial" | "pro";
  chantiers_lifetime_count?: number;
  cancel_at_period_end?: boolean;
  cancelled_at?: string | null;
  /** 🚧 Quand True → mode Beta Gratuite (pas de paywall, accès illimité). */
  beta_mode?: boolean;
  /**
   * 💎 Freemium — Date de fin de l'essai gratuit de 14 jours (ISO string).
   * Pendant cette période, l'utilisateur a accès à TOUTES les formes (12).
   * Passé ce délai et sans abonnement actif, retour au mode gratuit (5 formes).
   */
  freemium_trial_ends_at?: string | null;
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
  /** 📱 v1.1.3 — État de la vérification de version app (null tant que non chargé). */
  versionCheck: AppVersionCheck | null;
  signIn: (email: string, password: string) => Promise<void>;
  signInWithGoogle: (sessionId: string, stationId?: string) => Promise<void>;
  signUp: (
    name: string,
    email: string,
    password: string,
    companyName?: string,
    accountType?: "artisan" | "entreprise" | "pro",
    referralCode?: string,
    vatNumber?: string,
    stationId?: string,
  ) => Promise<{ verification_link?: string; message?: string }>;
  verifyEmail: (token: string) => Promise<void>;
  acceptInvitation: (
    token: string,
    password: string,
    name?: string
  ) => Promise<void>;
  signOut: () => Promise<void>;
  refreshCompany: () => Promise<void>;
  refreshUser: () => Promise<void>;
  /**
   * Returns true if the current user can access functionality reserved to a role list.
   * Artisan-mode bypasses all role checks.
   */
  hasRole: (roles: Role[]) => boolean;
};

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [company, setCompany] = useState<CompanyProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [lock, setLock] = useState<SubscriptionLock>({ expired: false });
  // 🔒 Validation-required lock (403 PAYWALL_VALIDATION_REQUIRED — Phase 2)
  const [validationLock, setValidationLock] = useState<{
    required: boolean;
    message?: string;
    reason?: string;
  }>({ required: false });

  // 📱 v1.1.3 — App version check (banner + éventuel écran bloquant)
  const [versionCheck, setVersionCheck] = useState<AppVersionCheck | null>(null);
  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      const res = await checkAppVersion();
      if (!cancelled) setVersionCheck(res);
    };
    // Immédiat au boot puis toutes les 15 min tant que l'app tourne
    run();
    const iv = setInterval(run, 15 * 60 * 1000);
    return () => {
      cancelled = true;
      clearInterval(iv);
    };
  }, []);

  // Subscribe to subscription lock events from the axios response interceptor.
  useEffect(() => {
    const off = onSubscriptionState((s) => setLock(s));
    return () => { off(); };
  }, []);

  // 🔒 Écoute des events 403 PAYWALL_VALIDATION_REQUIRED
  useEffect(() => {
    const off = onValidationRequired((s) => setValidationLock(s));
    return () => { off(); };
  }, []);

  // 🔐 Session expirée (401 hors routes d'auth) → déconnexion automatique.
  // Sans ça, l'utilisateur reste bloqué sur un écran avec des alertes
  // « Chargement impossible » (JWT expiré après 7 jours).
  const userRef = useRef<User | null>(null);
  useEffect(() => {
    userRef.current = user;
  }, [user]);
  useEffect(() => {
    const off = onAuthExpired(() => {
      if (!userRef.current) return; // déjà déconnecté / pas connecté
      userRef.current = null; // évite les alertes multiples (requêtes en vol)
      Alert.alert(
        "Session expirée",
        "Votre session a expiré. Veuillez vous reconnecter."
      );
      signOut();
    });
    return () => { off(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

  /**
   * 🔑 Connexion / inscription via Google Sign-In (Emergent-managed).
   *
   * Le frontend a déjà obtenu un `session_id` via le flow OAuth Emergent.
   * On l'échange côté backend (POST /api/auth/google/session) contre NOTRE
   * JWT applicatif — même shape que le login classique.
   */
  const signInWithGoogle = async (sessionId: string, stationId?: string) => {
    const body: Record<string, unknown> = { session_id: sessionId };
    if (stationId && stationId.trim()) body.station_id = stationId.trim();
    const res = await api.post("/auth/google/session", body);
    await saveToken(res.data.access_token);
    setUser(res.data.user);
    await fetchCompany();
    registerPushTokenWithBackend();
  };

  /**
   * Inscription Master Admin (création d'une nouvelle société).
   * Le compte est créé en `pending_verification`. La réponse contient
   * `verification_link` (MOCK MVP) qui permet de simuler le clic email.
   */
  const signUp = async (
    name: string,
    email: string,
    password: string,
    companyName?: string,
    accountType?: "artisan" | "entreprise" | "pro",
    referralCode?: string,
    vatNumber?: string,
    stationId?: string,
  ): Promise<{ verification_link?: string; message?: string }> => {
    const body: Record<string, unknown> = {
      name,
      email,
      password,
      company_name:
        companyName && companyName.length > 0 ? companyName : name,
    };
    if (accountType) body.account_type = accountType;
    // 🆕 Build 9 — Code parrainage optionnel
    if (referralCode && referralCode.trim()) {
      body.referral_code = referralCode.trim();
    }
    // 🆕 Build 11.3 — Numéro de TVA européen obligatoire (Apple 3.1.3(c))
    if (vatNumber && vatNumber.trim()) {
      body.vat_number = vatNumber.trim();
    }
    // ☕ Priorité 4 — Tag campagne Jeton Café (QR code station partenaire)
    if (stationId && stationId.trim()) {
      body.station_id = stationId.trim();
    }
    const res = await api.post("/auth/register", body);
    // Pas de token : compte en pending_verification.
    return {
      verification_link: res.data?.verification_link,
      message: res.data?.message,
    };
  };

  /** Vérification email via token reçu en lien (deep-link /verify?token=). */
  const verifyEmail = async (token: string) => {
    const res = await api.post("/auth/verify", { token });
    await saveToken(res.data.access_token);
    setUser(res.data.user);
    await fetchCompany();
    registerPushTokenWithBackend();
  };

  /** Acceptation d'invitation : token reçu en /invite?token= */
  const acceptInvitation = async (
    token: string,
    password: string,
    name?: string
  ) => {
    const res = await api.post(
      `/admin/invitations/${encodeURIComponent(token)}/accept`,
      { password, name }
    );
    await saveToken(res.data.access_token);
    setUser(res.data.user);
    await fetchCompany();
    registerPushTokenWithBackend();
  };

  const signOut = async () => {
    // 1) On purge le token AVANT de reset les states pour qu'aucune
    //    requête en vol ne réussisse avec l'ancienne identité.
    try {
      await clearToken();
    } catch {
      /* ignore — secureRemove peut échouer en mode privé navigateur */
    }
    // 2) Reset complet de l'état d'auth (user, company, paywall lock)
    setUser(null);
    setCompany(null);
    setLock({ expired: false });
    setValidationLock({ required: false });
    // 3) On revient FORCÉMENT à l'écran de connexion. `replace` détruit
    //    la pile de navigation : ainsi les écrans protégés (dashboard,
    //    chantier/[id]…) qui étaient encore montés sont démontés et ne
    //    relanceront plus aucun fetch authentifié.
    try {
      router.replace("/");
    } catch {
      /* router peut ne pas être prêt en SSR — sans danger */
    }
  };

  const artisanMode = !!company?.artisan_mode;

  // 🆕 Build 9 — Synchronise le postProcessor i18n "artisan" pour adapter
  // automatiquement le vocabulaire (commercial / technicien → vous / atelier).
  // `i18n.emit("languageChanged")` force le re-render des composants i18n
  // sans changer la langue, pour que `t()` repasse par le postProcessor.
  useEffect(() => {
    setI18nArtisanMode(artisanMode);
    try {
      i18n.emit("languageChanged", i18n.language);
    } catch {
      /* silent — i18n peut ne pas être prêt en SSR */
    }
  }, [artisanMode]);

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
        versionCheck,
        signIn,
        signInWithGoogle,
        signUp,
        verifyEmail,
        acceptInvitation,
        signOut,
        refreshCompany: fetchCompany,
        refreshUser: async () => {
          try {
            const res = await api.get<User>("/auth/me");
            setUser(res.data);
          } catch {
            /* silent — token might be expired, caller handles */
          }
        },
        hasRole,
      }}
    >
      {/* 🔴 v1.1.3 — Force Update SCREEN — priorité MAX (avant tout autre verrou).
          Bloque totalement l'usage de l'app si la version installée est <
          APP_MIN_VERSION ET que le backend a activé APP_FORCE_UPDATE=true. */}
      {versionCheck?.forceUpdate ? (
        <ForceUpdateScreen
          currentVersion={versionCheck.currentVersion}
          latestVersion={versionCheck.latestVersion}
          minVersion={versionCheck.minVersion}
          message={versionCheck.message}
          highlights={versionCheck.highlights}
          appStoreUrl={versionCheck.appStoreUrl}
          playStoreUrl={versionCheck.playStoreUrl}
          onLogout={user ? signOut : undefined}
        />
      ) : /* Subscription paywall — covers everything when expired/suspended.
          🚧 BETA GRATUITE : on désactive ce verrou tant que la société est
          flaggée `beta_mode=true` côté backend. */
      user && lock.expired && !company?.beta_mode ? (
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
      ) : user && user.vat_completion_required ? (
        /* 🔒 Compte Google Sign-In sans TVA — verrou plein écran.
            Priorité MAX : avant même la validation gérant, car aucun
            usage payant ne peut être fait sans TVA (Apple 3.1.3(c)). */
        <CompleteVatScreen
          defaultCompanyName={company?.name || user.name}
          onLogout={signOut}
          onCompleted={async () => {
            // Rafraîchit /auth/me → le flag doit repasser à undefined,
            // ce qui lève automatiquement ce verrou.
            try {
              const res = await api.get<User>("/auth/me");
              setUser(res.data);
              await fetchCompany();
            } catch {
              /* silent — au prochain rafraîchissement le flag sera bon */
            }
          }}
        />
      ) : user && validationLock.required ? (
        /* 🔒 403 PAYWALL_VALIDATION_REQUIRED — compte en attente de validation
            par le gérant. Verrouille l'app en plein écran. */
        <ValidationRequiredScreen
          message={validationLock.message}
          reason={validationLock.reason}
          onLogout={signOut}
          onRefresh={async () => {
            try {
              // Tente un /auth/me pour vérifier si le compte est validé.
              // Si succès → on lève le verrou. Sinon l'interceptor le
              // remontera automatiquement via onValidationRequired.
              const res = await api.get<User>("/auth/me");
              setUser(res.data);
              setValidationLock({ required: false });
            } catch {
              // Rien de plus à faire : le verrou reste actif.
            }
          }}
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
