import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

interface AuditLogEntry {
  id: number;
  category: string;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  result: string;
  ip_address: string | null;
  created_at: string;
  user_id: string | null;
}

const categories = ["", "auth", "authz", "data_access", "data_change", "system", "security"];

export function AuditLogPage() {
  const [category, setCategory] = useState("");
  const [action, setAction] = useState("");
  const [page, setPage] = useState(0);
  const limit = 50;

  const { data: logs, isLoading } = useQuery({
    queryKey: ["audit-logs", category, action, page],
    queryFn: () =>
      api.get<AuditLogEntry[]>(
        `/admin/audit-logs?limit=${limit}&offset=${page * limit}${category ? `&category=${category}` : ""}${action ? `&action=${action}` : ""}`
      ),
  });

  const resultColor: Record<string, string> = {
    success: "text-green-600",
    failure: "text-red-600",
    denied: "text-orange-600",
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Audit Log</h2>

      <div className="flex gap-4 items-center">
        <select
          value={category}
          onChange={(e) => { setCategory(e.target.value); setPage(0); }}
          className="px-3 py-2 border rounded-lg text-sm"
        >
          <option value="">All categories</option>
          {categories.filter(Boolean).map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
        <input
          value={action}
          onChange={(e) => { setAction(e.target.value); setPage(0); }}
          placeholder="Filter by action..."
          className="px-3 py-2 border rounded-lg text-sm w-48"
        />
      </div>

      {isLoading ? (
        <p className="text-gray-400">Loading...</p>
      ) : (
        <>
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Time</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Category</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Action</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Resource</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Result</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">IP</th>
                </tr>
              </thead>
              <tbody>
                {logs?.map((log) => (
                  <tr key={log.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">
                      {new Date(log.created_at).toLocaleString("ja-JP")}
                    </td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-1 bg-gray-100 rounded text-xs">{log.category}</span>
                    </td>
                    <td className="px-4 py-3">{log.action}</td>
                    <td className="px-4 py-3 text-gray-500 text-xs font-mono">
                      {log.resource_type}{log.resource_id ? `:${log.resource_id.slice(0, 8)}` : ""}
                    </td>
                    <td className={`px-4 py-3 font-medium ${resultColor[log.result] || ""}`}>
                      {log.result}
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-xs">{log.ip_address}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex justify-center gap-2">
            <button onClick={() => setPage((p) => Math.max(0, p - 1))} disabled={page === 0} className="px-3 py-1 border rounded disabled:opacity-50">Prev</button>
            <span className="px-3 py-1 text-gray-600">Page {page + 1}</span>
            <button onClick={() => setPage((p) => p + 1)} disabled={(logs?.length || 0) < limit} className="px-3 py-1 border rounded disabled:opacity-50">Next</button>
          </div>
        </>
      )}
    </div>
  );
}
