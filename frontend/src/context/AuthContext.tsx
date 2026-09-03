import React, { createContext, useContext, useEffect, useRef, useState } from 'react';
import { authApi, setAccessToken, type AuthUser } from '../lib/api';

interface AuthContextType {
  user: AuthUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (body: {
    org_name: string;
    org_slug: string;
    full_name: string;
    email: string;
    password: string;
  }) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ---------------------------------------------------------------------------
  // Schedule silent refresh ~1 min before the 15-min access token expires
  // ---------------------------------------------------------------------------
  const scheduleRefresh = () => {
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    // Refresh at 14 minutes (access token lives 15 min)
    refreshTimerRef.current = setTimeout(async () => {
      const newToken = await authApi.refresh();
      if (!newToken) {
        // Refresh token also expired — force logout
        setUser(null);
        setAccessToken(null);
        return;
      }
      scheduleRefresh(); // chain next refresh
    }, 14 * 60 * 1000);
  };

  // ---------------------------------------------------------------------------
  // Bootstrap — attempt silent refresh on page load to restore session
  // ---------------------------------------------------------------------------
  useEffect(() => {
    let cancelled = false;

    const bootstrap = async () => {
      try {
        // Try to refresh; if the httpOnly cookie is present this will succeed
        // and restore the session without the user needing to log in again.
        const token = await authApi.refresh();
        if (cancelled) return;

        if (token) {
          const me = await authApi.me();
          if (!cancelled) {
            setUser(me);
            scheduleRefresh();
          }
        }
      } catch {
        // Refresh failed → user is not authenticated; that's fine
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };

    bootstrap();
    return () => {
      cancelled = true;
      if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    };
  }, []);

  // ---------------------------------------------------------------------------
  // Login
  // ---------------------------------------------------------------------------
  const login = async (email: string, password: string) => {
    const { access_token } = await authApi.login(email, password);
    setAccessToken(access_token);
    const me = await authApi.me();
    setUser(me);
    scheduleRefresh();
  };

  // ---------------------------------------------------------------------------
  // Signup
  // ---------------------------------------------------------------------------
  const signup = async (body: Parameters<typeof authApi.signup>[0]) => {
    const { access_token } = await authApi.signup(body);
    setAccessToken(access_token);
    const me = await authApi.me();
    setUser(me);
    scheduleRefresh();
  };

  // ---------------------------------------------------------------------------
  // Logout
  // ---------------------------------------------------------------------------
  const logout = async () => {
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    try {
      await authApi.logout();
    } finally {
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        signup,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
};
