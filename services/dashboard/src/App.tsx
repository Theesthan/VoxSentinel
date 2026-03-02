import { Routes, Route, Navigate } from "react-router-dom";
import Landing from "@/pages/Landing";
import TabbedDashboard from "@/pages/TabbedDashboard";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  // Auto-login is always active; user is never unauthenticated
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      {/* Login route redirects to dashboard — auto-login handles auth */}
      <Route path="/login" element={<Navigate to="/dashboard" replace />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <TabbedDashboard />
          </ProtectedRoute>
        }
      />
      {/* Redirect old sub-routes to the unified tabbed dashboard */}
      <Route path="/dashboard/*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
