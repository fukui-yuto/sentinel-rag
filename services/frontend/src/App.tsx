import { Routes, Route, Navigate } from "react-router-dom";
import { useAuthStore } from "./lib/store";
import { Layout } from "./components/Layout";
import { LoginPage } from "./pages/auth/Login";
import { DashboardPage } from "./pages/Dashboard";
import { ChatPage } from "./pages/Chat";
import { DocumentsPage } from "./pages/Documents";
import { SettingsPage } from "./pages/Settings";
import { TenantsPage } from "./pages/admin/Tenants";
import { UsersPage } from "./pages/admin/Users";
import { ProvidersPage } from "./pages/admin/Providers";
import { AuditLogPage } from "./pages/admin/AuditLog";
import { SystemHealthPage } from "./pages/admin/SystemHealth";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <Layout>
              <Routes>
                <Route path="/" element={<DashboardPage />} />
                <Route path="/chat" element={<ChatPage />} />
                <Route path="/documents" element={<DocumentsPage />} />
                <Route path="/settings" element={<SettingsPage />} />
                <Route path="/admin/tenants" element={<TenantsPage />} />
                <Route path="/admin/users" element={<UsersPage />} />
                <Route path="/admin/providers" element={<ProvidersPage />} />
                <Route path="/admin/audit-log" element={<AuditLogPage />} />
                <Route path="/admin/health" element={<SystemHealthPage />} />
                <Route path="*" element={
                  <div className="text-center py-20">
                    <p className="text-6xl font-bold text-gray-200">404</p>
                    <p className="text-gray-500 mt-2">Page not found</p>
                  </div>
                } />
              </Routes>
            </Layout>
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
