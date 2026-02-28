import { Routes, Route, Navigate } from "react-router-dom";
import Landing from "@/pages/Landing";
import Dashboard from "@/pages/Dashboard";
import LoginPage from "@/pages/LoginPage";
import StreamsPage from "@/pages/StreamsPage";
import RulesPage from "@/pages/RulesPage";
import AlertsPage from "@/pages/AlertsPage";
import ChannelsPage from "@/pages/ChannelsPage";
import SearchPage from "@/pages/SearchPage";
import { useAuth } from "@/lib/AuthContext";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return null;
  if (!isAuthenticated) return <LoginPage />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      >
        <Route index element={<StreamsPage />} />
        <Route path="streams" element={<StreamsPage />} />
        <Route path="rules" element={<RulesPage />} />
        <Route path="alerts" element={<AlertsPage />} />
        <Route path="channels" element={<ChannelsPage />} />
        <Route path="search" element={<SearchPage />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Route>
    </Routes>
  );
}
