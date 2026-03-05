import {
  createContext,
  useContext,
  useState,
  useEffect,
  type ReactNode,
} from "react";
import {
  onAuthStateChanged,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signInWithPopup,
  signOut,
  sendPasswordResetEmail,
  updateProfile,
  type User,
} from "firebase/auth";
import { auth, googleProvider } from "./firebase";
import { setApiKey } from "./api";

/* ── Types ── */

interface AuthContextValue {
  user: User | null;
  isAuthenticated: boolean;
  loading: boolean;
  loginEmail: (email: string, password: string) => Promise<void>;
  signupEmail: (email: string, password: string, displayName: string) => Promise<void>;
  loginGoogle: () => Promise<void>;
  resetPassword: (email: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthCtx = createContext<AuthContextValue>({
  user: null,
  isAuthenticated: false,
  loading: true,
  loginEmail: async () => {},
  signupEmail: async () => {},
  loginGoogle: async () => {},
  resetPassword: async () => {},
  logout: async () => {},
});

export const useAuth = () => useContext(AuthCtx);

/* ── Default API key (keeps backend requests working without per-user tokens) ── */
const DEFAULT_API_KEY = "dlbegt0aWo_i_htATSI9lCoV1sJV7QvjBeePCFNWICk";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  /* Listen to Firebase auth state */
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (firebaseUser) => {
      setUser(firebaseUser);
      /* Always keep the default API key in localStorage for backend calls */
      setApiKey(DEFAULT_API_KEY);
      setLoading(false);
    });
    return unsubscribe;
  }, []);

  /* ── Auth methods ── */

  const loginEmail = async (email: string, password: string) => {
    await signInWithEmailAndPassword(auth, email, password);
  };

  const signupEmail = async (email: string, password: string, displayName: string) => {
    const cred = await createUserWithEmailAndPassword(auth, email, password);
    await updateProfile(cred.user, { displayName });
  };

  const loginGoogle = async () => {
    await signInWithPopup(auth, googleProvider);
  };

  const resetPassword = async (email: string) => {
    await sendPasswordResetEmail(auth, email);
  };

  const logout = async () => {
    await signOut(auth);
  };

  return (
    <AuthCtx.Provider
      value={{
        user,
        isAuthenticated: !!user,
        loading,
        loginEmail,
        signupEmail,
        loginGoogle,
        resetPassword,
        logout,
      }}
    >
      {children}
    </AuthCtx.Provider>
  );
}
