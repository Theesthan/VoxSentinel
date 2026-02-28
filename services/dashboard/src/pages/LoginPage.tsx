import { useState } from "react";
import { motion } from "framer-motion";
import { Shield, Loader2 } from "lucide-react";
import { useAuth } from "../lib/AuthContext";

export default function LoginPage() {
  const { login } = useAuth();
  const [key, setKey] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!key.trim()) return;
    setLoading(true);
    setError("");
    const ok = await login(key.trim());
    if (!ok) {
      setError("Could not connect. Check your API key and that the API is running.");
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-black flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md"
      >
        <div className="flex items-center gap-3 mb-8 justify-center">
          <Shield className="w-8 h-8 text-red-500" />
          <h1 className="text-3xl font-bold text-white tracking-tight">
            VoxSentinel
          </h1>
        </div>

        <form
          onSubmit={handleSubmit}
          className="border border-white/10 rounded-xl p-8 bg-white/[0.02] space-y-6"
        >
          <div>
            <label className="block text-sm text-white/60 mb-2">
              API Key
            </label>
            <input
              type="password"
              value={key}
              onChange={(e) => setKey(e.target.value)}
              placeholder="Enter your TG_API_KEY"
              className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white placeholder-white/30 focus:outline-none focus:border-red-500/50 transition-colors"
              autoFocus
            />
          </div>

          {error && (
            <p className="text-red-400 text-sm">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading || !key.trim()}
            className="w-full bg-red-600 hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium py-3 rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Connecting…
              </>
            ) : (
              "Sign In"
            )}
          </button>

          <p className="text-xs text-white/30 text-center">
            The API key is stored locally and sent as a Bearer token.
          </p>
        </form>
      </motion.div>
    </div>
  );
}
