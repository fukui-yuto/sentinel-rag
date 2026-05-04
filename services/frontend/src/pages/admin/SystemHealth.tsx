import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Activity, CheckCircle, XCircle } from "lucide-react";

interface HealthData {
  status: string;
  checks: Record<string, string>;
}

export function SystemHealthPage() {
  const { data: readiness, isLoading, refetch } = useQuery({
    queryKey: ["health-ready"],
    queryFn: () => api.get<HealthData>("/health/ready"),
    refetchInterval: 30000,
  });

  const { data: metrics } = useQuery({
    queryKey: ["admin-metrics"],
    queryFn: () => api.get<{ period: string; queries: number }>("/admin/metrics"),
  });

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">System Health</h2>
        <button
          onClick={() => refetch()}
          className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 text-sm"
        >
          Refresh
        </button>
      </div>

      {isLoading ? (
        <p className="text-gray-400">Loading...</p>
      ) : (
        <>
          <div className="flex items-center gap-3 mb-6">
            <Activity
              className={readiness?.status === "ready" ? "text-green-500" : "text-yellow-500"}
            />
            <span className="text-lg font-semibold">
              {readiness?.status === "ready" ? "All Systems Operational" : "Degraded"}
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {readiness?.checks &&
              Object.entries(readiness.checks).map(([name, status]) => (
                <div key={name} className="bg-white rounded-xl border border-gray-200 p-4 flex items-center gap-3">
                  {status === "ok" ? (
                    <CheckCircle className="text-green-500" size={20} />
                  ) : (
                    <XCircle className="text-red-500" size={20} />
                  )}
                  <div>
                    <p className="font-medium capitalize">{name}</p>
                    <p className="text-xs text-gray-500 truncate max-w-[150px]">{status}</p>
                  </div>
                </div>
              ))}
          </div>

          {metrics && (
            <div className="bg-white rounded-xl border border-gray-200 p-6 max-w-sm">
              <h3 className="font-semibold mb-2">Usage (Last 30 days)</h3>
              <p className="text-3xl font-bold text-blue-600">{metrics.queries.toLocaleString()}</p>
              <p className="text-sm text-gray-500">Queries</p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
