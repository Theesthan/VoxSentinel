import { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import { RefreshCw, Bell, Loader2, X, AlertTriangle } from "lucide-react";
import { listAlerts, type Alert } from "../lib/api";

const SEVERITY_COLORS: Record<string, string> = {
  critical: "bg-red-500/10 border-red-500/30 text-red-400",
  high: "bg-orange-500/10 border-orange-500/30 text-orange-400",
  medium: "bg-yellow-500/10 border-yellow-500/30 text-yellow-400",
  low: "bg-blue-500/10 border-blue-500/30 text-blue-400",
};

const SEV_BADGE: Record<string, string> = {
  critical: "text-red-400 border-red-500/30",
  high: "text-orange-400 border-orange-500/30",
  medium: "text-yellow-400 border-yellow-500/30",
  low: "text-blue-400 border-blue-500/30",
};

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [severity, setSeverity] = useState("");
  const [alertType, setAlertType] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const params: { severity?: string; alert_type?: string; limit?: number } = { limit: 100 };
      if (severity) params.severity = severity;
      if (alertType) params.alert_type = alertType;
      const data = await listAlerts(params);
      setAlerts(data.alerts);
      setTotal(data.total);
      setError("");
    } catch (e: unknown) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [severity, alertType]);

  useEffect(() => { refresh(); }, [refresh]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Alerts</h1>
          <p className="text-sm text-white/50 mt-1">{total} alert(s)</p>
        </div>
        <button onClick={refresh} className="p-2 rounded-lg border border-white/10 text-white/60 hover:text-white hover:bg-white/5 transition-colors">
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <select
          value={severity}
          onChange={(e) => setSeverity(e.target.value)}
          className="input-field !w-auto"
        >
          <option value="">All Severities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
        <select
          value={alertType}
          onChange={(e) => setAlertType(e.target.value)}
          className="input-field !w-auto"
        >
          <option value="">All Types</option>
          <option value="keyword_match">Keyword Match</option>
          <option value="sentiment_spike">Sentiment Spike</option>
          <option value="anomaly">Anomaly</option>
        </select>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 text-red-400 text-sm flex items-center justify-between">
          {error}
          <button onClick={() => setError("")}><X className="w-4 h-4" /></button>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-6 h-6 text-white/40 animate-spin" />
        </div>
      ) : alerts.length === 0 ? (
        <div className="border border-white/10 rounded-xl p-12 text-center">
          <Bell className="w-10 h-10 text-white/20 mx-auto mb-4" />
          <p className="text-white/40">No alerts found</p>
        </div>
      ) : (
        <div className="grid gap-3">
          {alerts.map((a) => (
            <motion.div
              key={a.alert_id}
              layout
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className={`border rounded-xl p-4 ${SEVERITY_COLORS[a.severity] ?? "border-white/10 bg-white/[0.02]"}`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-3 min-w-0">
                  <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`text-xs px-2 py-0.5 rounded-full border capitalize font-medium ${SEV_BADGE[a.severity] ?? "text-white/50 border-white/10"}`}>
                        {a.severity}
                      </span>
                      <span className="text-xs text-white/40 capitalize">
                        {a.alert_type?.replace(/_/g, " ")}
                      </span>
                    </div>
                    {a.matched_text && (
                      <p className="text-sm text-white mt-2 font-mono">
                        "{a.matched_text}"
                      </p>
                    )}
                    {a.surrounding_context && (
                      <p className="text-xs text-white/40 mt-1 truncate">
                        …{a.surrounding_context}…
                      </p>
                    )}
                    <div className="flex items-center gap-3 mt-2 text-xs text-white/30">
                      {a.matched_rule && <span>Rule: {a.matched_rule}</span>}
                      {a.speaker_id && <span>Speaker: {a.speaker_id}</span>}
                      {a.stream_id && <span title={a.stream_id}>Stream: {a.stream_name ?? a.stream_id.slice(0, 8)}…</span>}
                    </div>
                  </div>
                </div>
                <span className="text-xs text-white/30 whitespace-nowrap">
                  {a.created_at ? new Date(a.created_at).toLocaleString() : "—"}
                </span>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
