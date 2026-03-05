import { Routes, Route, Navigate } from "react-router-dom";
import Landing from "@/pages/Landing";
import TabbedDashboard from "@/pages/TabbedDashboard";
import AuthPage from "@/pages/AuthPage";
import { useAuth } from "@/lib/AuthContext";
import { Loader2 } from "lucide-react";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <Loader2 className="w-6 h-6 text-white/30 animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/auth" replace />;
  }

  return <>{children}</>;
}

export default function App() {
  const { isAuthenticated, loading } = useAuth();

  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route
        path="/auth"
        element={
          loading ? (
            <div className="min-h-screen bg-black flex items-center justify-center">
              <Loader2 className="w-6 h-6 text-white/30 animate-spin" />
            </div>
          ) : isAuthenticated ? (
            <Navigate to="/dashboard" replace />
          ) : (
            <AuthPage />
          )
        }
      />
      {/* Keep /login redirecting for backwards compat */}
      <Route path="/login" element={<Navigate to="/auth" replace />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <TabbedDashboard />
          </ProtectedRoute>
        }
      />
      <Route path="/dashboard/*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
