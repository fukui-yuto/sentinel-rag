import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

interface Provider {
  id: string;
  name: string;
  display_name: string;
  provider_type: string;
  is_enabled: boolean;
  config: Record<string, unknown>;
}

export function ProvidersPage() {
  const queryClient = useQueryClient();

  const { data: providers, isLoading } = useQuery({
    queryKey: ["providers"],
    queryFn: () => api.get<Provider[]>("/admin/providers"),
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, is_enabled }: { id: string; is_enabled: boolean }) =>
      api.put(`/admin/providers/${id}`, { is_enabled }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["providers"] }),
  });

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">LLM Providers</h2>

      {isLoading ? (
        <p className="text-gray-400">Loading...</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {providers?.map((p) => (
            <div key={p.id} className="bg-white rounded-xl border border-gray-200 p-6">
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="font-semibold text-lg">{p.display_name}</h3>
                  <p className="text-sm text-gray-500 font-mono">{p.provider_type}</p>
                </div>
                <button
                  onClick={() => toggleMutation.mutate({ id: p.id, is_enabled: !p.is_enabled })}
                  className={`px-3 py-1 rounded-full text-sm font-medium ${
                    p.is_enabled
                      ? "bg-green-100 text-green-800"
                      : "bg-gray-100 text-gray-600"
                  }`}
                >
                  {p.is_enabled ? "Enabled" : "Disabled"}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
