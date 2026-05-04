import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "@/lib/store";
import { api } from "@/lib/api";

export function LoginPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const login = useAuthStore((s) => s.login);
  const navigate = useNavigate();

  const handleDevLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const tokenRes = await api.post<{ access_token: string }>(
        `/auth/dev-login?email=${encodeURIComponent(email)}`
      );
      const token = tokenRes.access_token;

      // Temporarily set token to fetch user info
      useAuthStore.setState({ token });
      const user = await api.get<{
        id: string;
        tenant_id: string;
        email: string;
        display_name: string;
        role: string;
      }>("/auth/me");

      login(token, user);
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full bg-white rounded-xl shadow-sm border border-gray-200 p-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Sentinel RAG</h1>
        <p className="text-gray-500 mb-6">Enterprise RAG Platform</p>

        {error && (
          <div className="bg-red-50 text-red-700 px-4 py-3 rounded-lg mb-4 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleDevLogin} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Email (Dev Login)
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="admin@sentinel.local"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 font-medium"
          >
            {loading ? "Logging in..." : "Login"}
          </button>
        </form>

        <p className="mt-4 text-xs text-gray-400 text-center">
          Development mode only. Production uses SSO.
        </p>
      </div>
    </div>
  );
}
