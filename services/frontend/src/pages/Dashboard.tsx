import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { FileText, MessageSquare, Users, Loader2 } from "lucide-react";

export function DashboardPage() {
  const user = useAuthStore((s) => s.user);
  const isAdmin = user?.role === "system_admin" || user?.role === "tenant_admin";

  const { data: health, isLoading: healthLoading } = useQuery({
    queryKey: ["admin-health"],
    queryFn: () => api.get<{ stats: { total_documents: number; total_users: number; total_queries: number } }>("/admin/health"),
    enabled: isAdmin,
  });

  const { data: docs, isLoading: docsLoading } = useQuery({
    queryKey: ["documents-summary"],
    queryFn: () => api.get<{ total: number }>("/documents?page_size=1"),
  });

  const { data: history } = useQuery({
    queryKey: ["qa-history-recent"],
    queryFn: () => api.get<Array<{ id: string; query: string; created_at: string }>>("/qa/history?limit=5"),
  });

  const stats = health?.stats;

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Dashboard</h2>
      <p className="text-gray-600">Welcome, {user?.display_name}</p>

      {(healthLoading || docsLoading) && (
        <div className="flex items-center gap-2 text-gray-400 text-sm">
          <Loader2 size={14} className="animate-spin" />
          Loading stats...
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard
          icon={<FileText className="text-blue-500" />}
          label="Documents"
          value={stats?.total_documents ?? docs?.total ?? 0}
        />
        <StatCard
          icon={<MessageSquare className="text-green-500" />}
          label="Total Queries"
          value={stats?.total_queries ?? 0}
        />
        {isAdmin && (
          <StatCard
            icon={<Users className="text-purple-500" />}
            label="Users"
            value={stats?.total_users ?? 0}
          />
        )}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-lg font-semibold mb-4">Recent Queries</h3>
        {history && history.length > 0 ? (
          <ul className="space-y-3">
            {history.map((item) => (
              <li key={item.id} className="flex justify-between items-center text-sm">
                <span className="text-gray-700 truncate max-w-md">{item.query}</span>
                <span className="text-gray-400 text-xs whitespace-nowrap ml-4">
                  {new Date(item.created_at).toLocaleString("ja-JP")}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-gray-400 text-sm">No recent queries.</p>
        )}
      </div>
    </div>
  );
}

function StatCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: number }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 flex items-center gap-4">
      <div className="p-3 bg-gray-50 rounded-lg">{icon}</div>
      <div>
        <p className="text-2xl font-bold text-gray-900">{value.toLocaleString()}</p>
        <p className="text-sm text-gray-500">{label}</p>
      </div>
    </div>
  );
}
