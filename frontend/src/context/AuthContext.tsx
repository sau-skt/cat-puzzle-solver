import { createContext, useContext, useEffect, useRef, useState } from "react";
import { api } from "../services/api";
import type { User } from "../types";

type AuthValue = {
  user: User | null;
  loading: boolean;
  setUser: (user: User | null) => void;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUserState] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const settled = useRef(false);

  const setUser = (next: User | null) => {
    settled.current = true;
    setUserState(next);
  };

  const refresh = async () => {
    const response = await api.get<User>("/auth/me");
    setUser(response.data);
  };

  useEffect(() => {
    api
      .get<User>("/auth/me")
      .then((response) => {
        if (!settled.current) setUserState(response.data);
      })
      .catch(() => {
        if (!settled.current) setUserState(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const logout = async () => {
    await api.post("/auth/logout");
    setUser(null);
  };

  return <AuthContext.Provider value={{ user, loading, setUser, refresh, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}
