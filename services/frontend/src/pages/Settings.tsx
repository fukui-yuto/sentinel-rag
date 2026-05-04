import { useAuthStore } from "@/lib/store";

export function SettingsPage() {
  const user = useAuthStore((s) => s.user);

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Settings</h2>

      <div className="bg-white rounded-xl border border-gray-200 p-6 max-w-xl space-y-4">
        <h3 className="text-lg font-semibold">Profile</h3>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-gray-500">Email</p>
            <p className="font-medium">{user?.email}</p>
          </div>
          <div>
            <p className="text-gray-500">Display Name</p>
            <p className="font-medium">{user?.display_name}</p>
          </div>
          <div>
            <p className="text-gray-500">Role</p>
            <p className="font-medium">{user?.role}</p>
          </div>
          <div>
            <p className="text-gray-500">Tenant ID</p>
            <p className="font-mono text-xs">{user?.tenant_id}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
