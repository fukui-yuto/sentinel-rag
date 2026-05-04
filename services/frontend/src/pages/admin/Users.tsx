import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Plus } from "lucide-react";

interface User {
  id: string;
  email: string;
  display_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export function UsersPage() {
  const [showCreate, setShowCreate] = useState(false);
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [role, setRole] = useState("user");
  const queryClient = useQueryClient();

  const { data: users, isLoading } = useQuery({
    queryKey: ["users"],
    queryFn: () => api.get<User[]>("/admin/users"),
  });

  const createMutation = useMutation({
    mutationFn: (data: { email: string; display_name: string; role: string }) =>
      api.post("/admin/users", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      setShowCreate(false);
      setEmail("");
      setDisplayName("");
      setRole("user");
    },
  });

  const roles = ["system_admin", "tenant_admin", "content_manager", "user", "auditor", "read_only"];

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Users</h2>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          <Plus size={16} />
          New User
        </button>
      </div>

      {showCreate && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 max-w-md space-y-4">
          <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" className="w-full px-3 py-2 border rounded-lg" />
          <input value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder="Display Name" className="w-full px-3 py-2 border rounded-lg" />
          <select value={role} onChange={(e) => setRole(e.target.value)} className="w-full px-3 py-2 border rounded-lg">
            {roles.map((r) => (<option key={r} value={r}>{r}</option>))}
          </select>
          <button onClick={() => createMutation.mutate({ email, display_name: displayName, role })} className="px-4 py-2 bg-blue-600 text-white rounded-lg">Create</button>
        </div>
      )}

      {isLoading ? (
        <p className="text-gray-400">Loading...</p>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Email</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Name</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Role</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
              </tr>
            </thead>
            <tbody>
              {users?.map((u) => (
                <tr key={u.id} className="border-b border-gray-100">
                  <td className="px-4 py-3">{u.email}</td>
                  <td className="px-4 py-3">{u.display_name}</td>
                  <td className="px-4 py-3"><span className="px-2 py-1 bg-gray-100 rounded text-xs font-mono">{u.role}</span></td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded-full text-xs ${u.is_active ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"}`}>
                      {u.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
