import {
  createContext,
  useContext,
  useState,
  useEffect,
  type ReactNode,
} from "react";
import { getApiKey, setApiKey, clearApiKey, getHealth } from "./api";

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

export function AuthProvider({ children }: { children: ReactNode }) {
  const [apiKey, setKey] = useState("");
  const [loading, setLoading] = useState(true);

  // Check stored key on mount
  useEffect(() => {
    const stored = getApiKey();
    if (stored) {
      setKey(stored);
    }
    setLoading(false);
  }, []);

  const login = async (key: string): Promise<boolean> => {
    setApiKey(key);
    try {
      await getHealth(); // validate connectivity
      setKey(key);
      return true;
    } catch {
      clearApiKey();
      return false;
    }
  };

  const logout = () => {
    clearApiKey();
    setKey("");
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
