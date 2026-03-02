import {
  createContext,
  useContext,
  useState,
  type ReactNode,
} from "react";
import { getApiKey, setApiKey, getHealth } from "./api";

interface AuthContextValue {
  apiKey: string;
  isAuthenticated: boolean;
  login: (key: string) => Promise<boolean>;
  logout: () => void;
  loading: boolean;
}

const AuthCtx = createContext<AuthContextValue>({
  apiKey: "",
  isAuthenticated: false,
  login: async () => false,
  logout: () => {},
  loading: true,
});

export const useAuth = () => useContext(AuthCtx);

const DEFAULT_API_KEY = "dlbegt0aWo_i_htATSI9lCoV1sJV7QvjBeePCFNWICk";

export function AuthProvider({ children }: { children: ReactNode }) {
  // Always initialise with the default key so the user is never prompted
  const [apiKey, setKey] = useState(() => {
    const stored = getApiKey();
    if (stored) return stored;
    setApiKey(DEFAULT_API_KEY);
    return DEFAULT_API_KEY;
  });
  const [loading] = useState(false); // never in loading state

  const login = async (key: string): Promise<boolean> => {
    setApiKey(key);
    try {
      await getHealth();
      setKey(key);
      return true;
    } catch {
      // On failure, restore default key so user is never locked out
      setApiKey(DEFAULT_API_KEY);
      setKey(DEFAULT_API_KEY);
      return false;
    }
  };

  const logout = () => {
    // Re-set default key instead of clearing — user is never locked out
    setApiKey(DEFAULT_API_KEY);
    setKey(DEFAULT_API_KEY);
  };

  return (
    <AuthCtx.Provider
      value={{
        apiKey,
        isAuthenticated: apiKey.length > 0,
        login,
        logout,
        loading,
      }}
    >
      {children}
    </AuthCtx.Provider>
  );
}
