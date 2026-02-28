import { useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Plus,
  Pause,
  Play,
  Trash2,
  RefreshCw,
  Radio,
  Loader2,
  X,
} from "lucide-react";
import {
  listStreams,
  createStream,
  deleteStream,
  pauseStream,
  resumeStream,
  type Stream,
  type StreamCreateRequest,
} from "../lib/api";

const STATUS_COLORS: Record<string, string> = {
  active: "bg-green-500",
  paused: "bg-yellow-500",
  error: "bg-red-500",
  idle: "bg-white/30",
};

export default function StreamsPage() {
  const [streams, setStreams] = useState<Stream[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listStreams();
      setStreams(data.streams);
      setTotal(data.total);
      setError("");
    } catch (e: unknown) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleCreate = async (form: StreamCreateRequest) => {
    setCreating(true);
    try {
      await createStream(form);
      setShowCreate(false);
      await refresh();
    } catch (e: unknown) {
      setError(String(e));
    } finally {
      setCreating(false);
    }
  };

  const handleAction = async (
    id: string,
    action: "pause" | "resume" | "delete",
  ) => {
    setActionLoading(id);
    try {
      if (action === "pause") await pauseStream(id);
      else if (action === "resume") await resumeStream(id);
      else await deleteStream(id);
      await refresh();
    } catch (e: unknown) {
      setError(String(e));
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Streams</h1>
          <p className="text-sm text-white/50 mt-1">{total} stream(s)</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={refresh}
            className="p-2 rounded-lg border border-white/10 text-white/60 hover:text-white hover:bg-white/5 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" /> New Stream
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 text-red-400 text-sm flex items-center justify-between">
          {error}
          <button onClick={() => setError("")}>
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-6 h-6 text-white/40 animate-spin" />
        </div>
      ) : streams.length === 0 ? (
        <div className="border border-white/10 rounded-xl p-12 text-center">
          <Radio className="w-10 h-10 text-white/20 mx-auto mb-4" />
          <p className="text-white/40">No streams yet</p>
          <button
            onClick={() => setShowCreate(true)}
            className="mt-4 text-red-400 hover:text-red-300 text-sm"
          >
            Create your first stream
          </button>
        </div>
      ) : (
        <div className="grid gap-4">
          {streams.map((s) => (
            <motion.div
              key={s.stream_id}
              layout
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="border border-white/10 rounded-xl p-5 bg-white/[0.02] hover:bg-white/[0.04] transition-colors"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div
                    className={`w-2.5 h-2.5 rounded-full ${STATUS_COLORS[s.status] ?? "bg-gray-500"}`}
                  />
                  <div>
                    <h3 className="text-white font-medium">{s.name}</h3>
                    <p className="text-xs text-white/40 mt-0.5">
                      {s.stream_id.slice(0, 8)}… &middot; {s.source_type} &middot; {s.asr_backend}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs px-2 py-1 rounded-full border border-white/10 text-white/50 capitalize">
                    {s.status}
                  </span>
                  {actionLoading === s.stream_id ? (
                    <Loader2 className="w-4 h-4 text-white/40 animate-spin" />
                  ) : (
                    <>
                      {s.status === "active" && (
                        <button
                          onClick={() => handleAction(s.stream_id, "pause")}
                          className="p-1.5 rounded-lg hover:bg-white/10 text-yellow-400 transition-colors"
                          title="Pause"
                        >
                          <Pause className="w-4 h-4" />
                        </button>
                      )}
                      {s.status === "paused" && (
                        <button
                          onClick={() => handleAction(s.stream_id, "resume")}
                          className="p-1.5 rounded-lg hover:bg-white/10 text-green-400 transition-colors"
                          title="Resume"
                        >
                          <Play className="w-4 h-4" />
                        </button>
                      )}
                      <button
                        onClick={() => handleAction(s.stream_id, "delete")}
                        className="p-1.5 rounded-lg hover:bg-white/10 text-red-400 transition-colors"
                        title="Delete"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </>
                  )}
                </div>
              </div>
              {s.source_url && (
                <p className="text-xs text-white/30 mt-2 truncate">
                  {s.source_url}
                </p>
              )}
            </motion.div>
          ))}
        </div>
      )}

      {/* Create stream modal */}
      <AnimatePresence>
        {showCreate && (
          <CreateStreamModal
            onClose={() => setShowCreate(false)}
            onSubmit={handleCreate}
            loading={creating}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

// ── Create Stream Modal ──

function CreateStreamModal({
  onClose,
  onSubmit,
  loading,
}: {
  onClose: () => void;
  onSubmit: (form: StreamCreateRequest) => void;
  loading: boolean;
}) {
  const [form, setForm] = useState<StreamCreateRequest>({
    name: "",
    source_type: "url",
    source_url: "",
    asr_backend: "deepgram",
  });

  const set = (key: keyof StreamCreateRequest, val: string) =>
    setForm((f) => ({ ...f, [key]: val }));

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.95 }}
        animate={{ scale: 1 }}
        exit={{ scale: 0.95 }}
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-lg border border-white/10 rounded-xl bg-[#0a0a0a] p-6 space-y-5"
      >
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-white">New Stream</h2>
          <button onClick={onClose} className="text-white/40 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-4">
          <Field label="Name">
            <input
              value={form.name}
              onChange={(e) => set("name", e.target.value)}
              placeholder="e.g. Support Line 1"
              className="input-field"
            />
          </Field>
          <Field label="Source URL">
            <input
              value={form.source_url}
              onChange={(e) => set("source_url", e.target.value)}
              placeholder="wss://stream.example.com/audio"
              className="input-field"
            />
          </Field>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Source Type">
              <select
                value={form.source_type}
                onChange={(e) => set("source_type", e.target.value)}
                className="input-field"
              >
                <option value="url">URL</option>
                <option value="sip">SIP</option>
                <option value="upload">Upload</option>
              </select>
            </Field>
            <Field label="ASR Backend">
              <select
                value={form.asr_backend}
                onChange={(e) => set("asr_backend", e.target.value)}
                className="input-field"
              >
                <option value="deepgram">Deepgram</option>
                <option value="whisper">Whisper</option>
                <option value="vosk">Vosk</option>
              </select>
            </Field>
          </div>
        </div>

        <div className="flex justify-end gap-3 pt-2">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg border border-white/10 text-white/60 hover:text-white transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => onSubmit(form)}
            disabled={loading || !form.name || !form.source_url}
            className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white transition-colors flex items-center gap-2"
          >
            {loading && <Loader2 className="w-4 h-4 animate-spin" />}
            Create
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="block text-sm text-white/50 mb-1.5">{label}</label>
      {children}
    </div>
  );
}
