import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { authApi } from '../api/services';
import type { StaffUser } from '../types';
import { storage } from '../utils/storage';

interface AuthContextValue {
  user: StaffUser | null;
  token: string | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(storage.getToken());
  const [user, setUser] = useState<StaffUser | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshProfile = async () => {
    if (!storage.getToken()) {
      setUser(null);
      return;
    }
    const profile = await authApi.me();
    setUser(profile);
  };

  useEffect(() => {
    const bootstrap = async () => {
      try {
        if (token) {
          await refreshProfile();
        }
      } catch {
        storage.clearToken();
        setToken(null);
        setUser(null);
      } finally {
        setLoading(false);
      }
    };
    bootstrap();
  }, [token]);

  const value = useMemo<AuthContextValue>(() => ({
    user,
    token,
    loading,
    login: async (username, password) => {
      const result = await authApi.login({ username, password });
      storage.setToken(result.access_token);
      setToken(result.access_token);
      const profile = await authApi.me();
      setUser(profile);
    },
    logout: () => {
      storage.clearToken();
      setToken(null);
      setUser(null);
    },
    refreshProfile,
  }), [user, token, loading]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used inside AuthProvider');
  return context;
}
