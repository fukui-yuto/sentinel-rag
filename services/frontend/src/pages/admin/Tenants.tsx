import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Plus } from "lucide-react";

interface Tenant {
  id: string;
  name: string;
  slug: string;
  is_active: boolean;
  max_storage_bytes: number;
  max_documents: number;
  created_at: string;
}

export function TenantsPage() {
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const queryClient = useQueryClient();

  const { data: tenants, isLoading } = useQuery({
    queryKey: ["tenants"],
    queryFn: () => api.get<Tenant[]>("/admin/tenants"),
  });

  const createMutation = useMutation({
    mutationFn: (data: { name: string; slug: string }) =>
      api.post("/admin/tenants", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tenants"] });
      setShowCreate(false);
      setName("");
      setSlug("");
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Tenants</h2>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          <Plus size={16} />
          New Tenant
        </button>
      </div>

      {showCreate && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 max-w-md space-y-4">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Tenant Name"
            className="w-full px-3 py-2 border rounded-lg"
          />
          <input
            value={slug}
            onChange={(e) => setSlug(e.target.value)}
            placeholder="Slug (e.g. engineering)"
            className="w-full px-3 py-2 border rounded-lg"
          />
          <button
            onClick={() => createMutation.mutate({ name, slug })}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg"
          >
            Create
          </button>
        </div>
      )}

      {isLoading ? (
        <p className="text-gray-400">Loading...</p>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Name</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Slug</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Max Docs</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Created</th>
              </tr>
            </thead>
            <tbody>
              {tenants?.map((t) => (
                <tr key={t.id} className="border-b border-gray-100">
                  <td className="px-4 py-3 font-medium">{t.name}</td>
                  <td className="px-4 py-3 text-gray-500 font-mono text-xs">{t.slug}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${t.is_active ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-800"}`}>
                      {t.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500">{t.max_documents.toLocaleString()}</td>
                  <td className="px-4 py-3 text-gray-500">{new Date(t.created_at).toLocaleDateString("ja-JP")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
