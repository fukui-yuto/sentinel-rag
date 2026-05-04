import { Link, useLocation } from "react-router-dom";
import { useAuthStore } from "@/lib/store";
import {
  LayoutDashboard,
  MessageSquare,
  FileText,
  Settings,
  Users,
  Building2,
  Shield,
  Activity,
  Cpu,
  LogOut,
} from "lucide-react";

const navItems = [
  { path: "/", label: "Dashboard", icon: LayoutDashboard },
  { path: "/chat", label: "Chat", icon: MessageSquare },
  { path: "/documents", label: "Documents", icon: FileText },
  { path: "/settings", label: "Settings", icon: Settings },
];

const adminItems = [
  { path: "/admin/tenants", label: "Tenants", icon: Building2, roles: ["system_admin"] },
  { path: "/admin/users", label: "Users", icon: Users, roles: ["system_admin", "tenant_admin"] },
  { path: "/admin/providers", label: "Providers", icon: Cpu, roles: ["system_admin"] },
  { path: "/admin/audit-log", label: "Audit Log", icon: Shield, roles: ["system_admin", "auditor"] },
  { path: "/admin/health", label: "Health", icon: Activity, roles: ["system_admin", "tenant_admin"] },
];

export function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const { user, logout } = useAuthStore();
  const role = user?.role || "";

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <nav className="w-64 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <h1 className="text-xl font-bold text-gray-900">Sentinel RAG</h1>
          <p className="text-sm text-gray-500 truncate">{user?.email}</p>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm ${
                  active
                    ? "bg-blue-50 text-blue-700 font-medium"
                    : "text-gray-700 hover:bg-gray-100"
                }`}
              >
                <Icon size={18} />
                {item.label}
              </Link>
            );
          })}

          {adminItems.some((i) => i.roles.includes(role)) && (
            <>
              <div className="pt-4 pb-1 px-3 text-xs font-semibold text-gray-400 uppercase">
                Admin
              </div>
              {adminItems
                .filter((i) => i.roles.includes(role))
                .map((item) => {
                  const Icon = item.icon;
                  const active = location.pathname === item.path;
                  return (
                    <Link
                      key={item.path}
                      to={item.path}
                      className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm ${
                        active
                          ? "bg-blue-50 text-blue-700 font-medium"
                          : "text-gray-700 hover:bg-gray-100"
                      }`}
                    >
                      <Icon size={18} />
                      {item.label}
                    </Link>
                  );
                })}
            </>
          )}
        </div>

        <div className="p-2 border-t border-gray-200">
          <button
            onClick={logout}
            className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-gray-700 hover:bg-gray-100 w-full"
          >
            <LogOut size={18} />
            Logout
          </button>
        </div>
      </nav>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto p-6">{children}</main>
    </div>
  );
}
