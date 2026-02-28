import { useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Plus,
  Trash2,
  RefreshCw,
  Send,
  Loader2,
  X,
  Pencil,
  ToggleLeft,
  ToggleRight,
} from "lucide-react";
import {
  listAlertChannels,
  createAlertChannel,
  updateAlertChannel,
  deleteAlertChannel,
  type AlertChannel,
  type AlertChannelCreateRequest,
} from "../lib/api";

const TYPE_LABELS: Record<string, string> = {
  webhook: "Webhook",
  email: "Email",
  slack: "Slack",
  pagerduty: "PagerDuty",
};

export default function ChannelsPage() {
  const [channels, setChannels] = useState<AlertChannel[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [editChannel, setEditChannel] = useState<AlertChannel | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listAlertChannels();
      setChannels(data.channels);
      setTotal(data.total);
      setError("");
    } catch (e: unknown) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const handleCreate = async (form: AlertChannelCreateRequest) => {
    setSaving(true);
    try {
      await createAlertChannel(form);
      setShowCreate(false);
      await refresh();
    } catch (e: unknown) { setError(String(e)); }
    finally { setSaving(false); }
  };

  const handleUpdate = async (id: string, body: Partial<AlertChannelCreateRequest>) => {
    setSaving(true);
    try {
      await updateAlertChannel(id, body);
      setEditChannel(null);
      await refresh();
    } catch (e: unknown) { setError(String(e)); }
    finally { setSaving(false); }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteAlertChannel(id);
      await refresh();
    } catch (e: unknown) { setError(String(e)); }
  };

  const handleToggle = async (ch: AlertChannel) => {
    try {
      await updateAlertChannel(ch.channel_id, { enabled: !ch.enabled });
      await refresh();
    } catch (e: unknown) { setError(String(e)); }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Alert Channels</h1>
          <p className="text-sm text-white/50 mt-1">{total} channel(s)</p>
        </div>
        <div className="flex gap-2">
          <button onClick={refresh} className="p-2 rounded-lg border border-white/10 text-white/60 hover:text-white hover:bg-white/5 transition-colors">
            <RefreshCw className="w-4 h-4" />
          </button>
          <button onClick={() => setShowCreate(true)} className="flex items-center gap-2 bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg transition-colors">
            <Plus className="w-4 h-4" /> New Channel
          </button>
        </div>
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
      ) : channels.length === 0 ? (
        <div className="border border-white/10 rounded-xl p-12 text-center">
          <Send className="w-10 h-10 text-white/20 mx-auto mb-4" />
          <p className="text-white/40">No alert channels configured</p>
          <button onClick={() => setShowCreate(true)} className="mt-4 text-red-400 hover:text-red-300 text-sm">
            Create your first channel
          </button>
        </div>
      ) : (
        <div className="grid gap-4">
          {channels.map((ch) => (
            <motion.div
              key={ch.channel_id}
              layout
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="border border-white/10 rounded-xl p-5 bg-white/[0.02] hover:bg-white/[0.04] transition-colors"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Send className="w-4 h-4 text-white/40" />
                  <div>
                    <h3 className="text-white font-medium">
                      {TYPE_LABELS[ch.channel_type] ?? ch.channel_type}
                    </h3>
                    <p className="text-xs text-white/40 mt-0.5">
                      {ch.channel_id.slice(0, 8)}… &middot;
                      min severity: {ch.min_severity ?? "any"} &middot;
                      types: {ch.alert_types?.join(", ") ?? "all"}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button onClick={() => handleToggle(ch)} className="text-white/60 hover:text-white transition-colors">
                    {ch.enabled ? <ToggleRight className="w-5 h-5 text-green-400" /> : <ToggleLeft className="w-5 h-5 text-white/30" />}
                  </button>
                  <button onClick={() => setEditChannel(ch)} className="p-1.5 rounded-lg hover:bg-white/10 text-white/40 hover:text-white transition-colors" title="Edit">
                    <Pencil className="w-3.5 h-3.5" />
                  </button>
                  <button onClick={() => handleDelete(ch.channel_id)} className="p-1.5 rounded-lg hover:bg-white/10 text-red-400 transition-colors" title="Delete">
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
              <div className="mt-3 text-xs text-white/30 font-mono bg-white/[0.03] rounded-lg p-3 overflow-x-auto">
                {JSON.stringify(ch.config, null, 2)}
              </div>
            </motion.div>
          ))}
        </div>
      )}

      <AnimatePresence>
        {showCreate && (
          <ChannelModal
            title="New Alert Channel"
            onClose={() => setShowCreate(false)}
            onSubmit={handleCreate}
            loading={saving}
          />
        )}
        {editChannel && (
          <ChannelModal
            title="Edit Channel"
            initial={editChannel}
            onClose={() => setEditChannel(null)}
            onSubmit={(f) => handleUpdate(editChannel.channel_id, f)}
            loading={saving}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

// ── Channel Modal ──

function ChannelModal({
  title,
  initial,
  onClose,
  onSubmit,
  loading,
}: {
  title: string;
  initial?: AlertChannel;
  onClose: () => void;
  onSubmit: (form: AlertChannelCreateRequest) => void;
  loading: boolean;
}) {
  const [channelType, setChannelType] = useState(initial?.channel_type ?? "webhook");
  const [configJson, setConfigJson] = useState(
    initial ? JSON.stringify(initial.config, null, 2) : '{\n  "url": "https://hooks.example.com/vox"\n}'
  );
  const [minSeverity, setMinSeverity] = useState(initial?.min_severity ?? "");
  const [enabled, setEnabled] = useState(initial?.enabled ?? true);
  const [jsonError, setJsonError] = useState("");

  const handleSubmit = () => {
    let config: Record<string, unknown>;
    try {
      config = JSON.parse(configJson);
      setJsonError("");
    } catch {
      setJsonError("Invalid JSON");
      return;
    }
    onSubmit({
      channel_type: channelType,
      config,
      min_severity: minSeverity || undefined,
      enabled,
    });
  };

  return (
    <motion.div
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.95 }} animate={{ scale: 1 }} exit={{ scale: 0.95 }}
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-lg border border-white/10 rounded-xl bg-[#0a0a0a] p-6 space-y-5"
      >
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-white">{title}</h2>
          <button onClick={onClose} className="text-white/40 hover:text-white"><X className="w-5 h-5" /></button>
        </div>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Field label="Channel Type">
              <select value={channelType} onChange={(e) => setChannelType(e.target.value)} className="input-field">
                <option value="webhook">Webhook</option>
                <option value="email">Email</option>
                <option value="slack">Slack</option>
                <option value="pagerduty">PagerDuty</option>
              </select>
            </Field>
            <Field label="Min Severity">
              <select value={minSeverity} onChange={(e) => setMinSeverity(e.target.value)} className="input-field">
                <option value="">Any</option>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </Field>
          </div>
          <Field label="Config (JSON)">
            <textarea
              value={configJson}
              onChange={(e) => setConfigJson(e.target.value)}
              rows={5}
              className="input-field font-mono text-xs"
            />
            {jsonError && <p className="text-red-400 text-xs mt-1">{jsonError}</p>}
          </Field>
          <label className="flex items-center gap-2 text-sm text-white/60 cursor-pointer">
            <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} className="accent-red-500" />
            Enabled
          </label>
        </div>

        <div className="flex justify-end gap-3 pt-2">
          <button onClick={onClose} className="px-4 py-2 rounded-lg border border-white/10 text-white/60 hover:text-white transition-colors">Cancel</button>
          <button
            onClick={handleSubmit}
            disabled={loading}
            className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white transition-colors flex items-center gap-2"
          >
            {loading && <Loader2 className="w-4 h-4 animate-spin" />}
            {initial ? "Save" : "Create"}
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-sm text-white/50 mb-1.5">{label}</label>
      {children}
    </div>
  );
}
