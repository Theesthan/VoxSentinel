import { useState, useEffect, useRef, useCallback, type FormEvent } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Radio,
  FileAudio,
  AlertTriangle,
  Settings,
  Mic,
  Plus,
  Trash2,
  Pause,
  Play,
  Upload,
  RefreshCw,
  X,
  Shield,
  Bell,
  Activity,
  Home,
  Download,
  Sparkles,
  Check,
  Loader2,
} from "lucide-react";
import * as api from "../lib/api";
import type {
  Stream,
  Rule,
  Alert,
  AlertChannel,
  FileAnalyzeStatusResponse,
  FileAnalyzeJobSummary,
  TranscriptSegment,
  SuggestedKeyword,
} from "../lib/api";

/* ═══════════════════════════════════════════════
   Constants & helpers
   ═══════════════════════════════════════════════ */

type Tab = "live" | "file" | "alerts" | "settings";

const NAV_ITEMS: { id: Tab; label: string; icon: React.ReactNode }[] = [
  { id: "live", label: "Live Streams", icon: <Radio className="w-4 h-4" /> },
  { id: "file", label: "File Analyze", icon: <FileAudio className="w-4 h-4" /> },
  { id: "alerts", label: "Alerts", icon: <AlertTriangle className="w-4 h-4" /> },
  { id: "settings", label: "Settings", icon: <Settings className="w-4 h-4" /> },
];

const PAGE_TRANSITION = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -8 },
  transition: { duration: 0.25, ease: [0.22, 1, 0.36, 1] },
};

function severityColor(s?: string) {
  switch (s) {
    case "critical":
      return "text-red-400";
    case "high":
      return "text-orange-400";
    case "medium":
      return "text-yellow-400";
    default:
      return "text-white/40";
  }
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <span className="block mb-4 text-[9px] font-mono tracking-[0.35em] text-white/20 uppercase select-none">
      {children}
    </span>
  );
}

function EmptyState({ text }: { text: string }) {
  return (
    <div className="py-16 text-center text-[12px] font-mono text-white/15 tracking-wider uppercase">
      {text}
    </div>
  );
}

function Pill({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 text-[9px] font-mono tracking-[0.1em] border border-white/10 uppercase ${className}`}
    >
      {children}
    </span>
  );
}

/* ═══════════════════════════════════════════════
   Main dashboard shell
   ═══════════════════════════════════════════════ */

export default function TabbedDashboard() {
  const [tab, setTab] = useState<Tab>("live");
  const [health, setHealth] = useState<string>("checking");

  // Periodic health check
  useEffect(() => {
    let alive = true;
    const check = () =>
      api
        .getHealth()
        .then((h) => alive && setHealth(h.status))
        .catch(() => alive && setHealth("error"));
    check();
    const id = setInterval(check, 15_000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  return (
    <div className="flex h-screen bg-black text-white overflow-hidden">
      {/* ── Sidebar ── */}
      <aside className="w-56 shrink-0 border-r border-white/[0.06] flex flex-col">
        {/* Brand */}
        <div className="h-14 flex items-center px-5 border-b border-white/[0.06]">
          <span className="text-[10px] font-mono tracking-[0.35em] text-white/40 uppercase">
            VoxSentinel
          </span>
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-4 px-2 space-y-0.5">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              onClick={() => setTab(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-none text-[11px] font-mono tracking-[0.08em] uppercase transition-colors duration-200
                ${
                  tab === item.id
                    ? "bg-white/[0.05] text-white"
                    : "text-white/25 hover:text-white/50 hover:bg-white/[0.02]"
                }`}
            >
              <span className={tab === item.id ? "text-white/60" : "text-white/15"}>
                {item.icon}
              </span>
              {item.label}
            </button>
          ))}
        </nav>

        {/* Footer */}
        <div className="border-t border-white/[0.06] p-3 space-y-2">
          {/* Health indicator */}
          <div className="flex items-center gap-2 px-2 py-1">
            <div
              className={`w-1.5 h-1.5 rounded-full ${
                health === "healthy"
                  ? "bg-emerald-400"
                  : health === "error"
                    ? "bg-red-400"
                    : health === "degraded"
                      ? "bg-yellow-400"
                      : "bg-yellow-400 animate-pulse"
              }`}
            />
            <span className="text-[9px] font-mono tracking-[0.1em] text-white/20 uppercase">
              {health === "healthy" ? "API connected" : health === "error" ? "API offline" : health === "degraded" ? "API degraded" : "Checking…"}
            </span>
          </div>

          <button
            onClick={() => window.location.href = '/'}
            className="w-full flex items-center gap-2 px-3 py-2 text-[10px] font-mono tracking-[0.1em] text-white/20 hover:text-white/40 transition-colors uppercase"
          >
            <Home className="w-3 h-3" />
            Home
          </button>
        </div>
      </aside>

      {/* ── Main content ── */}
      <main className="flex-1 overflow-y-auto">
        {/* Top bar */}
        <header className="sticky top-0 z-30 h-14 flex items-center justify-between px-8 border-b border-white/[0.06] bg-black/80 backdrop-blur-md">
          <h1 className="text-[11px] font-mono tracking-[0.2em] text-white/40 uppercase">
            {NAV_ITEMS.find((n) => n.id === tab)?.label}
          </h1>
          <div className="flex items-center gap-3">
            <Activity className="w-3 h-3 text-white/10" />
            <span className="text-[9px] font-mono text-white/15 tracking-wider">
              v0.9.0-alpha
            </span>
          </div>
        </header>

        {/* Page content */}
        <div className="p-8">
          <AnimatePresence mode="wait">
            {tab === "live" && (
              <motion.div key="live" {...PAGE_TRANSITION}>
                <LiveStreamsPanel />
              </motion.div>
            )}
            {tab === "file" && (
              <motion.div key="file" {...PAGE_TRANSITION}>
                <FileAnalyzePanel />
              </motion.div>
            )}
            {tab === "alerts" && (
              <motion.div key="alerts" {...PAGE_TRANSITION}>
                <AlertsPanel />
              </motion.div>
            )}
            {tab === "settings" && (
              <motion.div key="settings" {...PAGE_TRANSITION}>
                <SettingsPanel />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
}

/* ═══════════════════════════════════════════════
   1. LIVE STREAMS
   ═══════════════════════════════════════════════ */

function LiveStreamsPanel() {
  const [streams, setStreams] = useState<Stream[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [selected, setSelected] = useState<Stream | null>(null);
  const [micActive, setMicActive] = useState(false);
  const [micTranscript, setMicTranscript] = useState<{ text: string; isAlert?: boolean; severity?: string }[]>([]);
  const [micAlerts, setMicAlerts] = useState<{ keyword: string; severity: string; text: string }[]>([]);

  const load = useCallback(() => {
    setLoading(true);
    api
      .listStreams({ exclude_source_type: "file" })
      .then((r) => setStreams(r.streams))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 10_000);
    return () => clearInterval(id);
  }, [load]);

  return (
    <div className="space-y-8">
      {/* Actions bar */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => setShowCreate((v) => !v)}
          className="inline-flex items-center gap-2 px-4 py-2 border border-white/10 text-[10px] font-mono tracking-[0.15em] uppercase hover:bg-white/[0.04] transition-colors"
        >
          <Plus className="w-3 h-3" /> New Stream
        </button>
        <button
          onClick={() => {
            if (micActive) {
              setMicActive(false);
            } else {
              setMicTranscript([]);
              setMicAlerts([]);
              setMicActive(true);
            }
          }}
          className={`inline-flex items-center gap-2 px-4 py-2 border text-[10px] font-mono tracking-[0.15em] uppercase transition-colors ${
            micActive
              ? "border-red-400/40 text-red-400 bg-red-400/5"
              : "border-white/10 hover:bg-white/[0.04]"
          }`}
        >
          <Mic className="w-3 h-3" /> {micActive ? "Stop Mic" : "Mic Input"}
        </button>
        <button
          onClick={load}
          className="ml-auto p-2 text-white/20 hover:text-white/40 transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Create form */}
      <AnimatePresence>
        {showCreate && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <CreateStreamForm
              onCreated={() => {
                load();
                setShowCreate(false);
              }}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Mic panel */}
      <AnimatePresence>
        {micActive && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <MicPanel
              onStop={() => setMicActive(false)}
              onTranscript={(t) => setMicTranscript((prev) => [...prev.slice(-200), { text: t }])}
              onAlert={(a) => {
                setMicAlerts((prev) => [...prev, a]);
                setMicTranscript((prev) => [
                  ...prev,
                  { text: `⚠ Keyword: "${a.keyword}" (${a.severity})`, isAlert: true, severity: a.severity },
                ]);
              }}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Mic transcript (shown after stop) */}
      {!micActive && micTranscript.length > 0 && (
        <div className="p-6 border border-white/[0.06] bg-white/[0.01]">
          <div className="flex items-center justify-between mb-4">
            <SectionLabel>Microphone recording transcript</SectionLabel>
            <div className="flex items-center gap-2">
              {micAlerts.length > 0 && (
                <span className="text-[10px] font-mono text-red-400">
                  {micAlerts.length} alert{micAlerts.length !== 1 ? "s" : ""}
                </span>
              )}
              <button
                onClick={() => { setMicTranscript([]); setMicAlerts([]); }}
                className="p-1.5 text-white/20 hover:text-red-400 transition-colors"
                title="Clear"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
          <div className="max-h-64 overflow-y-auto space-y-1 pr-2">
            {micTranscript.map((t, i) => (
              <p
                key={i}
                className={`text-[12px] leading-relaxed ${
                  t.isAlert
                    ? t.severity === "critical"
                      ? "text-red-400 font-semibold"
                      : t.severity === "high"
                        ? "text-orange-400"
                        : "text-yellow-400"
                    : "text-white/50"
                }`}
              >
                {t.text}
              </p>
            ))}
          </div>
        </div>
      )}

      {/* Stream grid */}
      <SectionLabel>Active streams</SectionLabel>
      {loading && streams.length === 0 ? (
        <EmptyState text="Loading streams…" />
      ) : streams.length === 0 ? (
        <EmptyState text="No streams configured" />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {streams.map((s) => (
            <StreamCard
              key={s.stream_id}
              stream={s}
              active={selected?.stream_id === s.stream_id}
              onSelect={() => setSelected(selected?.stream_id === s.stream_id ? null : s)}
              onDelete={() => {
                api.deleteStream(s.stream_id).then(load);
                if (selected?.stream_id === s.stream_id) setSelected(null);
              }}
              onToggle={() => {
                (s.status === "active" ? api.pauseStream : api.resumeStream)(s.stream_id).then(load);
              }}
            />
          ))}
        </div>
      )}

      {/* Transcript viewer */}
      <AnimatePresence>
        {selected && (
          <motion.div
            key={selected.stream_id}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 12 }}
          >
            <TranscriptViewer stream={selected} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/* ── Stream card ── */

function StreamCard({
  stream,
  active,
  onSelect,
  onDelete,
  onToggle,
}: {
  stream: Stream;
  active: boolean;
  onSelect: () => void;
  onDelete: () => void;
  onToggle: () => void;
}) {
  const isActive = stream.status === "active";
  // YouTube live streams are stored as source_type="hls" with metadata.stream_type="youtube_live"
  const isYtLive =
    stream.source_type === "youtube_live" ||
    (stream.metadata as Record<string, unknown> | null)?.stream_type === "youtube_live";

  // For youtube_live streams, check actual liveness on mount
  const [liveChecked, setLiveChecked] = useState(false);
  const [isActuallyLive, setIsActuallyLive] = useState(isActive);

  useEffect(() => {
    if (isYtLive && isActive) {
      api.getYouTubeLiveStatus(stream.stream_id)
        .then((r) => { setIsActuallyLive(r.is_running); setLiveChecked(true); })
        .catch(() => { setIsActuallyLive(false); setLiveChecked(true); });
    } else {
      setIsActuallyLive(isActive);
      setLiveChecked(true);
    }
  }, [stream.stream_id, stream.status, isYtLive, isActive]);

  const showGreen = liveChecked ? isActuallyLive : isActive;
  const statusLabel = isYtLive
    ? (showGreen ? "live" : "offline")
    : stream.status;

  return (
    <div
      className={`group relative p-5 border transition-colors duration-300 cursor-pointer ${
        active ? "border-white/20 bg-white/[0.03]" : "border-white/[0.06] hover:border-white/10"
      }`}
      onClick={onSelect}
    >
      {/* Status dot */}
      <div className="flex items-center gap-2 mb-3">
        <div
          className={`w-1.5 h-1.5 rounded-full ${
            showGreen ? "bg-emerald-400 animate-pulse" : "bg-red-400/60"
          }`}
        />
        <span className="text-[10px] font-mono tracking-[0.15em] text-white/30 uppercase">
          {statusLabel}
        </span>
      </div>

      {/* Name */}
      <h3 className="text-[14px] font-medium tracking-[-0.01em] mb-1 truncate">{stream.name}</h3>

      {/* Meta */}
      <div className="flex items-center gap-2 flex-wrap mt-2">
        <Pill>{isYtLive ? "youtube live" : stream.source_type}</Pill>
        <Pill>{stream.asr_backend}</Pill>
      </div>

      {/* Actions */}
      <div className="absolute top-3 right-3 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          onClick={(e) => {
            e.stopPropagation();
            onToggle();
          }}
          className="p-1.5 text-white/20 hover:text-white/60 transition-colors"
          title={isActive ? "Pause" : "Resume"}
        >
          {isActive ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3" />}
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          className="p-1.5 text-white/20 hover:text-red-400 transition-colors"
          title="Delete"
        >
          <Trash2 className="w-3 h-3" />
        </button>
      </div>
    </div>
  );
}

/* ── Create stream form ── */

function CreateStreamForm({ onCreated }: { onCreated: () => void }) {
  const [name, setName] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [statusMsg, setStatusMsg] = useState<{ type: "ok" | "err" | "info"; text: string } | null>(null);

  const isYouTubeUrl = (url: string) =>
    /youtube\.com|youtu\.be/i.test(url);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!sourceUrl) return;
    setSubmitting(true);
    setStatusMsg(null);

    try {
      if (isYouTubeUrl(sourceUrl)) {
        // YouTube flow: resolve → check liveness → start live transcription
        setStatusMsg({ type: "info", text: "Checking YouTube stream status…" });
        const resolved = await api.resolveYouTubeUrl(sourceUrl);

        if (!resolved.is_live) {
          setStatusMsg({ type: "info", text: "This is a recorded video. Redirecting to File Analyze tab is recommended — or use Download & Analyze there." });
          setSubmitting(false);
          return;
        }

        // It's live — start live transcription directly
        setStatusMsg({ type: "ok", text: `✓ Live stream detected: ${resolved.title}. Starting transcription…` });
        await api.startYouTubeLive(sourceUrl, name || resolved.title);
        setStatusMsg(null);
        setName("");
        setSourceUrl("");
        onCreated();
      } else {
        // Non-YouTube: create a regular stream (HLS/RTSP/etc)
        if (!name) {
          setStatusMsg({ type: "err", text: "Stream name is required for non-YouTube sources" });
          setSubmitting(false);
          return;
        }

        // Auto-detect source type from URL
        let sourceType = "hls";
        if (sourceUrl.startsWith("rtsp://")) sourceType = "rtsp";
        else if (sourceUrl.includes(".mpd")) sourceType = "dash";
        else if (sourceUrl.startsWith("wss://") || sourceUrl.startsWith("ws://")) sourceType = "webrtc";
        else if (sourceUrl.startsWith("sip:")) sourceType = "sip";

        await api.createStream({
          name,
          source_type: sourceType,
          source_url: sourceUrl,
          asr_backend: "deepgram_nova2",
        });
        setName("");
        setSourceUrl("");
        onCreated();
      }
    } catch (err: unknown) {
      const msg = err instanceof api.ApiError ? err.body : "Failed to create stream";
      setStatusMsg({ type: "err", text: msg });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={submit} className="p-6 border border-white/[0.06] space-y-4">
      <SectionLabel>Create stream</SectionLabel>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <input
          className="input-field"
          placeholder="Stream name (auto-filled for YouTube)"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <input
          className="input-field"
          placeholder="YouTube live URL, HLS/RTSP/DASH URL"
          value={sourceUrl}
          onChange={(e) => { setSourceUrl(e.target.value); setStatusMsg(null); }}
        />
      </div>

      {isYouTubeUrl(sourceUrl) && (
        <p className="text-[10px] font-mono tracking-wider text-red-400/50">
          YouTube URL detected — will check liveness and start live transcription automatically
        </p>
      )}

      {statusMsg && (
        <p className={`text-[10px] font-mono tracking-wider ${
          statusMsg.type === "ok" ? "text-emerald-400/60" :
          statusMsg.type === "err" ? "text-red-400/60" : "text-yellow-400/60"
        }`}>
          {statusMsg.text}
        </p>
      )}

      <button
        type="submit"
        disabled={submitting || !sourceUrl}
        className="px-6 py-2 border border-white/15 text-[10px] font-mono tracking-[0.15em] uppercase hover:bg-white/[0.04] disabled:opacity-30 transition-colors"
      >
        {submitting ? "Starting…" : isYouTubeUrl(sourceUrl) ? "Start Live Transcription" : "Create Stream"}
      </button>
    </form>
  );
}

/* ── Transcript viewer (WebSocket) ── */

function TranscriptViewer({ stream }: { stream: Stream }) {
  const [segments, setSegments] = useState<TranscriptSegment[]>([]);
  const [live, setLive] = useState<{ text: string; speaker_id?: string }[]>([]);
  const endRef = useRef<HTMLDivElement>(null);

  // Load existing transcript
  useEffect(() => {
    if (stream.session_id) {
      api
        .getTranscript(stream.session_id)
        .then((t) => setSegments(t.segments))
        .catch(() => {});
    }
  }, [stream.session_id]);

  // WebSocket for live updates
  useEffect(() => {
    const ws = api.createTranscriptSocket(stream.stream_id);
    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        if (data.text) {
          setLive((prev) => [...prev.slice(-200), { text: data.text, speaker_id: data.speaker_id }]);
        }
      } catch {}
    };
    return () => ws.close();
  }, [stream.stream_id]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [live]);

  const allLines = [
    ...segments.map((s) => ({ text: s.text, speaker_id: s.speaker_id, sentiment: s.sentiment_label })),
    ...live.map((l) => ({ text: l.text, speaker_id: l.speaker_id, sentiment: null as string | null })),
  ];

  return (
    <div className="border border-white/[0.06] p-6">
      <div className="flex items-center justify-between mb-4">
        <SectionLabel>Transcript — {stream.name}</SectionLabel>
        <Pill className={stream.status === "active" ? "text-emerald-400 border-emerald-400/20" : ""}>
          {stream.status === "active" ? "● LIVE" : stream.status}
        </Pill>
      </div>

      <div className="max-h-80 overflow-y-auto space-y-1.5 pr-2">
        {allLines.length === 0 && <EmptyState text="No transcript data yet" />}
        {allLines.map((line, i) => (
          <div key={i} className="flex gap-3 text-[12px] leading-relaxed">
            <span className="shrink-0 w-16 text-right text-[10px] font-mono text-white/15">
              {line.speaker_id ?? "—"}
            </span>
            <span
              className={`flex-1 ${
                line.sentiment === "negative"
                  ? "text-red-300/70"
                  : line.sentiment === "positive"
                    ? "text-emerald-300/70"
                    : "text-white/50"
              }`}
            >
              {line.text}
            </span>
          </div>
        ))}
        <div ref={endRef} />
      </div>
    </div>
  );
}

/* ── Microphone panel ── */

function MicPanel({
  onStop,
  onTranscript,
  onAlert,
}: {
  onStop: () => void;
  onTranscript: (text: string) => void;
  onAlert: (alert: { keyword: string; severity: string; text: string }) => void;
}) {
  const [transcript, setTranscript] = useState<string[]>([]);
  const [alerts, setAlerts] = useState<{ keyword: string; severity: string }[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const mediaRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);

  useEffect(() => {
    let stopped = false;
    const ws = api.createMicSocket();
    wsRef.current = ws;

    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        if (data.type === "keyword_match") {
          // Keyword alert from server
          setAlerts((prev) => [...prev, { keyword: data.keyword, severity: data.severity }]);
          onAlert({ keyword: data.keyword, severity: data.severity, text: data.text });
        } else if (data.text) {
          setTranscript((prev) => [...prev.slice(-100), data.text]);
          if (data.is_final) {
            onTranscript(data.text);
          }
        }
      } catch {}
    };

    ws.onopen = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        if (stopped) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        mediaRef.current = stream;
        const ctx = new AudioContext({ sampleRate: 16000 });
        const source = ctx.createMediaStreamSource(stream);
        const processor = ctx.createScriptProcessor(4096, 1, 1);
        processorRef.current = processor;
        processor.onaudioprocess = (e) => {
          if (ws.readyState === WebSocket.OPEN) {
            const pcm = e.inputBuffer.getChannelData(0);
            const i16 = new Int16Array(pcm.length);
            for (let j = 0; j < pcm.length; j++) {
              i16[j] = Math.max(-32768, Math.min(32767, pcm[j] * 32768));
            }
            ws.send(i16.buffer);
          }
        };
        source.connect(processor);
        processor.connect(ctx.destination);
      } catch {}
    };

    return () => {
      stopped = true;
      ws.close();
      mediaRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="p-6 border border-red-400/10 bg-red-400/[0.02]">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-red-400 animate-pulse" />
          <SectionLabel>Microphone active</SectionLabel>
          {alerts.length > 0 && (
            <span className="text-[10px] font-mono text-red-400 ml-2">
              {alerts.length} alert{alerts.length !== 1 ? "s" : ""}
            </span>
          )}
        </div>
        <button
          onClick={onStop}
          className="p-1.5 text-white/20 hover:text-red-400 transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
      <div className="max-h-48 overflow-y-auto space-y-1 pr-2">
        {transcript.length === 0 && (
          <span className="text-[11px] font-mono text-white/15">Listening…</span>
        )}
        {transcript.map((t, i) => (
          <p key={i} className="text-[12px] text-white/50 leading-relaxed">
            {t}
          </p>
        ))}
      </div>
      {alerts.length > 0 && (
        <div className="mt-3 pt-3 border-t border-red-400/10 space-y-1">
          <span className="text-[10px] font-mono text-red-400/60 uppercase tracking-wider">Keyword alerts</span>
          {alerts.map((a, i) => (
            <p key={i} className="text-[11px] text-red-400/80">
              ◆ <span className="font-medium">{a.keyword}</span>{" "}
              <span className="text-white/30">({a.severity})</span>
            </p>
          ))}
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════
   2. FILE ANALYZE
   ═══════════════════════════════════════════════ */

/* ── Streaming transcript overlay shown during processing ── */
function StreamingTranscript({ words }: { words: { text: string; speaker: string }[] }) {
  const endRef = useRef<HTMLDivElement>(null);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [words.length]);

  if (words.length === 0) return (
    <div className="p-6 border border-white/[0.06] text-center">
      <span className="text-[10px] font-mono text-white/20 animate-pulse">Waiting for transcript…</span>
    </div>
  );

  // Group words by speaker for nice display
  const groups: { speaker: string; text: string }[] = [];
  for (const w of words) {
    const last = groups[groups.length - 1];
    if (last && last.speaker === w.speaker) {
      last.text += " " + w.text;
    } else {
      groups.push({ speaker: w.speaker, text: w.text });
    }
  }

  return (
    <div className="p-4 border border-white/[0.06] max-h-[380px] overflow-y-auto space-y-2">
      <div className="flex items-center gap-2 mb-3">
        <Activity className="w-3 h-3 text-emerald-400/60 animate-pulse" />
        <span className="text-[10px] font-mono tracking-wider text-emerald-400/50 uppercase">
          Live transcription
        </span>
      </div>
      {groups.map((g, i) => (
        <div key={i} className="flex gap-2">
          <span className="text-[9px] font-mono text-white/15 w-14 shrink-0 pt-0.5">{g.speaker}</span>
          <span className="text-[12px] text-white/60 leading-relaxed">{g.text}</span>
        </div>
      ))}
      <div ref={endRef} />
    </div>
  );
}

function FileAnalyzePanel() {
  const [jobs, setJobs] = useState<FileAnalyzeJobSummary[]>([]);
  const [selectedJob, setSelectedJob] = useState<FileAnalyzeStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [ytUrl, setYtUrl] = useState("");
  const [ytProcessing, setYtProcessing] = useState(false);
  const [ytError, setYtError] = useState("");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [streamingWords, setStreamingWords] = useState<{ text: string; speaker: string }[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  /* Connect to transcript WebSocket for live word-by-word display */
  const startStreaming = useCallback((streamId: string) => {
    setStreamingWords([]);
    setIsStreaming(true);
    if (wsRef.current) { try { wsRef.current.close(); } catch {} }
    const ws = api.createTranscriptSocket(streamId);
    wsRef.current = ws;
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.type === "complete") { return; }
        if (msg.is_word && msg.text) {
          setStreamingWords((prev) => [...prev, { text: msg.text, speaker: msg.speaker_id || "?" }]);
        } else if (msg.text) {
          // Handle non-word messages (full segments from live transcription)
          const wordList = msg.text.split(/\s+/).filter(Boolean);
          const speaker = msg.speaker_id || msg.speaker || "?";
          setStreamingWords((prev) => [...prev, ...wordList.map((w: string) => ({ text: w, speaker }))]);
        }
      } catch {}
    };
    ws.onerror = () => { ws.close(); };
    ws.onclose = () => { wsRef.current = null; };
  }, []);

  const stopStreaming = useCallback(() => {
    setIsStreaming(false);
    if (wsRef.current) { try { wsRef.current.close(); } catch {} wsRef.current = null; }
  }, []);

  const load = useCallback(() => {
    setLoading(true);
    api
      .listFileAnalyzeJobs()
      .then((r) => setJobs(r.jobs))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
      if (wsRef.current) { try { wsRef.current.close(); } catch {} }
    };
  }, [load]);

  const upload = async (file: File) => {
    setUploading(true);
    setUploadError("");
    try {
      const res = await api.submitFileForAnalysis(file);

      // Immediately add a "processing" entry to the jobs list and reset upload area
      const newJob: FileAnalyzeJobSummary = {
        job_id: res.job_id,
        status: "processing",
        file_name: res.file_name,
        duration_seconds: null,
        total_alerts: 0,
        created_at: res.created_at,
        completed_at: null,
      };
      setJobs((prev) => [newJob, ...prev]);
      setUploading(false);

      // Start streaming transcript words via WebSocket
      startStreaming(res.stream_id);

      // Poll until done in background
      if (pollRef.current) clearInterval(pollRef.current);
      const poll = setInterval(async () => {
        try {
          const s = await api.getFileAnalyzeJob(res.job_id);
          if (s.status === "completed" || s.status === "failed") {
            clearInterval(poll);
            pollRef.current = null;
            stopStreaming();
            load(); // refresh full list
            setSelectedJob(s);
            if (s.status === "failed" && s.error_message) {
              setUploadError(s.error_message);
            }
          } else {
            // Update status in local jobs list while processing
            setJobs((prev) => prev.map((j) =>
              j.job_id === res.job_id ? { ...j, status: s.status } : j
            ));
          }
        } catch {
          clearInterval(poll);
          pollRef.current = null;
        }
      }, 2000);
      pollRef.current = poll;
    } catch (err: unknown) {
      const msg = err instanceof api.ApiError ? err.body : "Upload failed";
      setUploadError(msg);
      setUploading(false);
    }
  };

  const viewJob = async (jobId: string) => {
    try {
      const j = await api.getFileAnalyzeJob(jobId);
      setSelectedJob(j);
    } catch {}
  };

  const analyzeYouTube = async () => {
    if (!ytUrl.trim()) return;
    setYtProcessing(true);
    setYtError("");
    try {
      const res = await api.youtubeDownloadAnalyze(ytUrl.trim());

      // Start streaming transcript words via WebSocket
      startStreaming(res.stream_id);

      // Poll until done
      if (pollRef.current) clearInterval(pollRef.current);
      const poll = setInterval(async () => {
        try {
          const s = await api.getFileAnalyzeJob(res.job_id);
          if (s.status === "completed" || s.status === "failed") {
            clearInterval(poll);
            pollRef.current = null;
            stopStreaming();
            load();
            setSelectedJob(s);
            setYtProcessing(false);
            setYtUrl("");
          }
        } catch {
          clearInterval(poll);
          pollRef.current = null;
          setYtProcessing(false);
        }
      }, 3000);
      pollRef.current = poll;
    } catch (err: unknown) {
      const msg = err instanceof api.ApiError ? err.body : "Failed to process YouTube URL";
      setYtError(msg);
      setYtProcessing(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Upload area */}
      <div
        className={`relative flex flex-col items-center justify-center p-12 border border-dashed transition-colors cursor-pointer ${
          uploading ? "border-white/10 opacity-50" : "border-white/[0.08] hover:border-white/20"
        }`}
        onClick={() => fileRef.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          const f = e.dataTransfer.files[0];
          if (f) upload(f);
        }}
      >
        <input
          ref={fileRef}
          type="file"
          className="hidden"
          accept="audio/*,video/*,.mp4,.mkv,.avi,.mov,.webm,.flv,.wmv,.m4v,.ts,.wav,.mp3,.m4a,.ogg,.flac,.aac,.wma"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) upload(f);
            if (fileRef.current) fileRef.current.value = "";
          }}
        />
        <Upload className="w-5 h-5 text-white/15 mb-3" />
        <span className="text-[11px] font-mono tracking-[0.1em] text-white/25 uppercase">
          {uploading ? "Uploading…" : "Drop audio or video file to upload"}
        </span>
      </div>
      {uploadError && (
        <p className="text-[10px] font-mono text-red-400/60 px-1">{uploadError}</p>
      )}

      {/* YouTube URL section */}
      <div className="p-4 border border-white/[0.06] space-y-3">
        <SectionLabel>YouTube video analysis</SectionLabel>
        <div className="flex gap-2">
          <input
            className="input-field flex-1"
            placeholder="Paste YouTube URL (e.g. https://youtube.com/watch?v=...)"
            value={ytUrl}
            onChange={(e) => { setYtUrl(e.target.value); setYtError(""); }}
            disabled={ytProcessing}
          />
          <button
            type="button"
            onClick={analyzeYouTube}
            disabled={ytProcessing || !ytUrl.trim()}
            className="px-4 py-2 border border-red-400/30 text-[10px] font-mono tracking-wider text-red-400/70 hover:bg-red-400/5 disabled:opacity-30 transition-colors whitespace-nowrap"
          >
            {ytProcessing ? "Downloading…" : "Download & Analyze"}
          </button>
        </div>
        {ytError && (
          <p className="text-[10px] font-mono text-red-400/60">{ytError}</p>
        )}
        {ytProcessing && (
          <p className="text-[10px] font-mono text-yellow-400/50 animate-pulse">
            Downloading audio from YouTube and transcribing — this may take a few minutes…
          </p>
        )}
      </div>

      {/* Streaming transcript display during processing */}
      {isStreaming && (
        <StreamingTranscript words={streamingWords} />
      )}

      {/* Job list */}
      <SectionLabel>Analysis jobs</SectionLabel>
      {loading && jobs.length === 0 ? (
        <EmptyState text="Loading jobs…" />
      ) : jobs.length === 0 ? (
        <EmptyState text="No file analyses yet" />
      ) : (
        <div className="space-y-2">
          {jobs.map((job) => (
            <button
              key={job.job_id}
              onClick={() => viewJob(job.job_id)}
              className={`w-full text-left p-4 border transition-colors ${
                selectedJob?.job_id === job.job_id
                  ? "border-white/15 bg-white/[0.03]"
                  : "border-white/[0.06] hover:border-white/10"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-[13px] font-medium truncate">{job.file_name}</span>
                <Pill
                  className={
                    job.status === "completed"
                      ? "text-emerald-400 border-emerald-400/20"
                      : job.status === "failed"
                        ? "text-red-400 border-red-400/20"
                        : "text-yellow-400 border-yellow-400/20"
                  }
                >
                  {job.status}
                </Pill>
              </div>
              <div className="flex items-center gap-4 mt-2 text-[10px] font-mono text-white/20">
                {job.duration_seconds != null && <span>{job.duration_seconds.toFixed(1)}s</span>}
                <span>{job.total_alerts} alerts</span>
                <span>{new Date(job.created_at).toLocaleString()}</span>
              </div>
            </button>
          ))}
        </div>
      )}

      {/* Job detail */}
      <AnimatePresence>
        {selectedJob && (
          <motion.div
            key={selectedJob.job_id}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
          >
            <FileJobDetail job={selectedJob} onClose={() => setSelectedJob(null)} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function FileJobDetail({
  job,
  onClose,
}: {
  job: FileAnalyzeStatusResponse;
  onClose: () => void;
}) {
  const [showTab, setShowTab] = useState<"transcript" | "alerts" | "summary" | "suggested">("transcript");
  const [suggestions, setSuggestions] = useState<SuggestedKeyword[]>([]);
  const [sugLoading, setSugLoading] = useState(false);
  const [sugError, setSugError] = useState("");
  const [addedKeywords, setAddedKeywords] = useState<Set<string>>(new Set());

  const loadSuggestions = useCallback(() => {
    setSugLoading(true);
    setSugError("");
    api
      .suggestKeywords(job.job_id)
      .then((r) => setSuggestions(r.suggestions))
      .catch((e) => setSugError(e.message ?? "Failed to load suggestions"))
      .finally(() => setSugLoading(false));
  }, [job.job_id]);

  const addAsRule = useCallback(
    async (kw: SuggestedKeyword) => {
      try {
        await api.createRule({
          keyword: kw.keyword,
          rule_set_name: "ai-suggested",
          match_type: kw.match_type,
          severity: kw.severity,
          category: kw.category,
        });
        setAddedKeywords((prev) => new Set(prev).add(kw.keyword));
      } catch {
        // ignore
      }
    },
    [],
  );

  return (
    <div className="border border-white/[0.06] p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-[14px] font-medium truncate">{job.file_name}</h3>
        <button onClick={onClose} className="p-1 text-white/20 hover:text-white/40 transition-colors">
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Sub-tabs */}
      <div className="flex items-center gap-4 border-b border-white/[0.06] pb-2">
        {(["transcript", "alerts", "summary", "suggested"] as const).map((t) => (
          <button
            key={t}
            onClick={() => {
              setShowTab(t);
              if (t === "suggested" && suggestions.length === 0 && !sugLoading) loadSuggestions();
            }}
            className={`text-[10px] font-mono tracking-[0.15em] uppercase pb-1 transition-colors ${
              showTab === t ? "text-white border-b border-white/30" : "text-white/20 hover:text-white/40"
            }`}
          >
            {t === "suggested" ? (
              <span className="inline-flex items-center gap-1"><Sparkles className="w-3 h-3" /> AI Keywords</span>
            ) : t}
          </button>
        ))}
      </div>

      {showTab === "transcript" && (
        <div className="max-h-96 overflow-y-auto space-y-1.5 pr-2">
          {job.transcript.length === 0 ? (
            <EmptyState text="No transcript segments" />
          ) : (
            job.transcript.map((seg) => (
              <div key={seg.segment_id} className="flex gap-3 text-[12px] leading-relaxed">
                <span className="shrink-0 w-14 text-right font-mono text-[10px] text-white/15">
                  {seg.speaker_id ?? "—"}
                </span>
                <span className="flex-1 text-white/50">{seg.text}</span>
                {seg.keywords_matched.length > 0 && (
                  <span className="shrink-0 text-[9px] font-mono text-orange-400/60">
                    {seg.keywords_matched.map((k) => k.keyword).join(", ")}
                  </span>
                )}
              </div>
            ))
          )}
        </div>
      )}

      {showTab === "alerts" && (
        <div className="max-h-96 overflow-y-auto space-y-2 pr-2">
          {job.alerts.length === 0 ? (
            <EmptyState text="No alerts generated" />
          ) : (
            job.alerts.map((a) => (
              <div
                key={a.alert_id}
                className="p-3 border border-white/[0.06] flex items-start gap-3"
              >
                <AlertTriangle className={`w-3.5 h-3.5 mt-0.5 shrink-0 ${severityColor(a.severity)}`} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <Pill>{a.alert_type}</Pill>
                    <Pill className={severityColor(a.severity)}>{a.severity}</Pill>
                  </div>
                  {a.matched_text && (
                    <p className="text-[12px] text-white/40 truncate">{a.matched_text}</p>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {showTab === "summary" && job.summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <MiniStat label="Segments" value={String(job.summary.total_segments)} />
          <MiniStat label="Alerts" value={String(job.summary.total_alerts)} />
          <MiniStat label="Speakers" value={String(job.summary.speakers_detected)} />
          <MiniStat
            label="Languages"
            value={job.summary.languages_detected.join(", ") || "—"}
          />
          {Object.entries(job.summary.sentiments).map(([k, v]) => (
            <MiniStat key={k} label={k} value={String(v)} />
          ))}
        </div>
      )}

      {showTab === "suggested" && (
        <div className="space-y-4">
          {sugLoading ? (
            <div className="flex items-center gap-2 text-white/30 text-[12px]">
              <Loader2 className="w-4 h-4 animate-spin" /> Analyzing transcript with AI…
            </div>
          ) : sugError ? (
            <div className="space-y-2">
              <p className="text-[12px] text-red-400/60">{sugError}</p>
              <button
                onClick={loadSuggestions}
                className="text-[10px] font-mono text-white/30 hover:text-white/50 underline"
              >
                Retry
              </button>
            </div>
          ) : suggestions.length === 0 ? (
            <EmptyState text="No keyword suggestions — click the tab to analyze" />
          ) : (
            <>
              <p className="text-[10px] font-mono text-white/20 tracking-[0.1em] uppercase">
                Click a keyword to add it as a rule
              </p>
              <div className="flex flex-wrap gap-2">
                {suggestions.map((kw) => {
                  const added = addedKeywords.has(kw.keyword);
                  return (
                    <button
                      key={kw.keyword}
                      onClick={() => !added && addAsRule(kw)}
                      disabled={added}
                      title={kw.reason}
                      className={`group relative inline-flex items-center gap-1.5 px-3 py-1.5 border text-[11px] font-medium transition-all ${
                        added
                          ? "border-green-500/30 text-green-400/60 cursor-default"
                          : `border-white/10 hover:border-white/20 hover:bg-white/[0.04] ${severityColor(kw.severity)}`
                      }`}
                    >
                      {added ? (
                        <Check className="w-3 h-3" />
                      ) : (
                        <Plus className="w-3 h-3 opacity-40 group-hover:opacity-80" />
                      )}
                      {kw.keyword}
                      <span className={`ml-1 text-[9px] font-mono opacity-50 ${severityColor(kw.severity)}`}>
                        {kw.severity}
                      </span>
                    </button>
                  );
                })}
              </div>
              <button
                onClick={loadSuggestions}
                className="inline-flex items-center gap-1.5 text-[10px] font-mono text-white/20 hover:text-white/40 transition-colors"
              >
                <RefreshCw className="w-3 h-3" /> Re-analyze
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="p-4 border border-white/[0.06]">
      <span className="block text-[9px] font-mono tracking-[0.2em] text-white/20 uppercase mb-1">
        {label}
      </span>
      <span className="text-[18px] font-medium tracking-[-0.02em]">{value}</span>
    </div>
  );
}

/* ═══════════════════════════════════════════════
   3. ALERTS
   ═══════════════════════════════════════════════ */

function AlertsPanel() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .listAlerts({ limit: 100 })
      .then((r) => setAlerts(r.alerts))
      .catch(() => {})
      .finally(() => setLoading(false));

    // Also listen for live alerts via WebSocket
    const ws = api.createAlertSocket();
    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        if (data.alert_id) {
          setAlerts((prev) => [data as Alert, ...prev].slice(0, 200));
        }
      } catch {}
    };
    return () => ws.close();
  }, []);

  return (
    <div className="space-y-6">
      <SectionLabel>Alert feed</SectionLabel>
      {loading && alerts.length === 0 ? (
        <EmptyState text="Loading alerts…" />
      ) : alerts.length === 0 ? (
        <EmptyState text="No alerts yet" />
      ) : (
        <div className="space-y-2">
          {alerts.map((a) => (
            <div
              key={a.alert_id}
              className="p-4 border border-white/[0.06] hover:border-white/10 transition-colors flex items-start gap-4"
            >
              <AlertTriangle
                className={`w-4 h-4 mt-0.5 shrink-0 ${severityColor(a.severity)}`}
              />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  <Pill>{a.alert_type}</Pill>
                  <Pill className={severityColor(a.severity)}>{a.severity}</Pill>
                  {a.stream_name && <Pill>{a.stream_name}</Pill>}
                </div>
                {a.matched_text && (
                  <p className="text-[12px] text-white/40 mt-1">
                    Match: <span className="text-white/60">{a.matched_text}</span>
                  </p>
                )}
                {a.surrounding_context && (
                  <p className="text-[11px] text-white/20 mt-1 truncate">
                    {a.surrounding_context}
                  </p>
                )}
                {a.created_at && (
                  <span className="text-[9px] font-mono text-white/10 mt-2 block">
                    {new Date(a.created_at).toLocaleString()}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════
   4. SEARCH
   ═══════════════════════════════════════════════ */

/* ═══════════════════════════════════════════════
   5. SETTINGS (Rules + Channels)
   ═══════════════════════════════════════════════ */

function SettingsPanel() {
  const [settingsTab, setSettingsTab] = useState<"rules" | "channels">("rules");

  return (
    <div className="space-y-6">
      {/* Sub-tabs */}
      <div className="flex items-center gap-6 border-b border-white/[0.06] pb-3">
        {(["rules", "channels"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setSettingsTab(t)}
            className={`flex items-center gap-2 text-[10px] font-mono tracking-[0.15em] uppercase pb-1 transition-colors ${
              settingsTab === t
                ? "text-white border-b border-white/30"
                : "text-white/20 hover:text-white/40"
            }`}
          >
            {t === "rules" ? <Shield className="w-3 h-3" /> : <Bell className="w-3 h-3" />}
            {t === "rules" ? "Keyword Rules" : "Alert Channels"}
          </button>
        ))}
      </div>

      {settingsTab === "rules" ? <RulesSubPanel /> : <ChannelsSubPanel />}
    </div>
  );
}

/* ── Rules sub-panel ── */

function RulesSubPanel() {
  const [rules, setRules] = useState<Rule[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [importStatus, setImportStatus] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const load = useCallback(() => {
    setLoading(true);
    api
      .listRules()
      .then((r) => setRules(r.rules))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleImport = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImportStatus("Importing…");
    try {
      const result = await api.importRules(file);
      setImportStatus(`Imported ${result.created} rules (${result.skipped} skipped)`);
      load();
    } catch {
      setImportStatus("Import failed");
    }
    // Reset file input so the same file can be re-imported
    if (fileInputRef.current) fileInputRef.current.value = "";
    setTimeout(() => setImportStatus(""), 4000);
  }, [load]);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3 flex-wrap">
        <button
          onClick={() => setShowCreate((v) => !v)}
          className="inline-flex items-center gap-2 px-4 py-2 border border-white/10 text-[10px] font-mono tracking-[0.15em] uppercase hover:bg-white/[0.04] transition-colors"
        >
          <Plus className="w-3 h-3" /> New Rule
        </button>
        <button
          onClick={() => api.exportRules()}
          className="inline-flex items-center gap-2 px-4 py-2 border border-white/10 text-[10px] font-mono tracking-[0.15em] uppercase hover:bg-white/[0.04] transition-colors"
        >
          <Download className="w-3 h-3" /> Export
        </button>
        <label className="inline-flex items-center gap-2 px-4 py-2 border border-white/10 text-[10px] font-mono tracking-[0.15em] uppercase hover:bg-white/[0.04] transition-colors cursor-pointer">
          <Upload className="w-3 h-3" /> Import
          <input
            ref={fileInputRef}
            type="file"
            accept=".json"
            className="hidden"
            onChange={handleImport}
          />
        </label>
        {importStatus && (
          <span className="text-[10px] font-mono text-white/40">{importStatus}</span>
        )}
      </div>

      <AnimatePresence>
        {showCreate && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <CreateRuleForm
              onCreated={() => {
                load();
                setShowCreate(false);
              }}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {loading && rules.length === 0 ? (
        <EmptyState text="Loading rules…" />
      ) : rules.length === 0 ? (
        <EmptyState text="No rules configured" />
      ) : (
        <div className="space-y-2">
          {rules.map((rule) => (
            <div
              key={rule.rule_id}
              className="p-4 border border-white/[0.06] hover:border-white/10 transition-colors flex items-center justify-between"
            >
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[13px] font-medium">{rule.keyword}</span>
                  <Pill>{rule.match_type}</Pill>
                  <Pill className={severityColor(rule.severity)}>{rule.severity}</Pill>
                </div>
                <span className="text-[10px] font-mono text-white/20">
                  {rule.rule_set_name} · {rule.category}
                </span>
              </div>
              <button
                onClick={() => api.deleteRule(rule.rule_id).then(load)}
                className="p-1.5 text-white/15 hover:text-red-400 transition-colors"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function CreateRuleForm({ onCreated }: { onCreated: () => void }) {
  const [keyword, setKeyword] = useState("");
  const [ruleSetName, setRuleSetName] = useState("default");
  const [matchType, setMatchType] = useState("exact");
  const [severity, setSeverity] = useState("medium");
  const [category, setCategory] = useState("general");
  const [submitting, setSubmitting] = useState(false);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!keyword) return;
    setSubmitting(true);
    api
      .createRule({
        keyword,
        rule_set_name: ruleSetName,
        match_type: matchType,
        severity,
        category,
      })
      .then(onCreated)
      .catch(() => {})
      .finally(() => setSubmitting(false));
  };

  return (
    <form onSubmit={submit} className="p-6 border border-white/[0.06] space-y-4">
      <SectionLabel>Create rule</SectionLabel>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <input
          className="input-field"
          placeholder="Keyword"
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
        />
        <input
          className="input-field"
          placeholder="Rule Set Name"
          value={ruleSetName}
          onChange={(e) => setRuleSetName(e.target.value)}
        />
        <select className="input-field" value={matchType} onChange={(e) => setMatchType(e.target.value)}>
          <option value="exact">Exact</option>
          <option value="fuzzy">Fuzzy</option>
          <option value="regex">Regex</option>
          <option value="phonetic">Phonetic</option>
        </select>
        <select className="input-field" value={severity} onChange={(e) => setSeverity(e.target.value)}>
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
          <option value="critical">Critical</option>
        </select>
        <input
          className="input-field"
          placeholder="Category"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
        />
      </div>
      <button
        type="submit"
        disabled={submitting}
        className="px-6 py-2 border border-white/15 text-[10px] font-mono tracking-[0.15em] uppercase hover:bg-white/[0.04] disabled:opacity-30 transition-colors"
      >
        {submitting ? "Creating…" : "Create Rule"}
      </button>
    </form>
  );
}

/* ── Channels sub-panel ── */

function ChannelsSubPanel() {
  const [channels, setChannels] = useState<AlertChannel[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    api
      .listAlertChannels()
      .then((r) => setChannels(r.channels))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-6">
      <button
        onClick={() => setShowCreate((v) => !v)}
        className="inline-flex items-center gap-2 px-4 py-2 border border-white/10 text-[10px] font-mono tracking-[0.15em] uppercase hover:bg-white/[0.04] transition-colors"
      >
        <Plus className="w-3 h-3" /> New Channel
      </button>

      <AnimatePresence>
        {showCreate && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <CreateChannelForm
              onCreated={() => {
                load();
                setShowCreate(false);
              }}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {loading && channels.length === 0 ? (
        <EmptyState text="Loading channels…" />
      ) : channels.length === 0 ? (
        <EmptyState text="No alert channels configured" />
      ) : (
        <div className="space-y-2">
          {channels.map((ch) => (
            <div
              key={ch.channel_id}
              className="p-4 border border-white/[0.06] hover:border-white/10 transition-colors flex items-center justify-between"
            >
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[13px] font-medium">{ch.channel_type}</span>
                  <Pill>{ch.enabled ? "Enabled" : "Disabled"}</Pill>
                  {ch.min_severity && (
                    <Pill className={severityColor(ch.min_severity)}>≥ {ch.min_severity}</Pill>
                  )}
                </div>
                <span className="text-[10px] font-mono text-white/20">
                  {JSON.stringify(ch.config).slice(0, 60)}
                  {JSON.stringify(ch.config).length > 60 ? "…" : ""}
                </span>
              </div>
              <button
                onClick={() => api.deleteAlertChannel(ch.channel_id).then(load)}
                className="p-1.5 text-white/15 hover:text-red-400 transition-colors"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function CreateChannelForm({ onCreated }: { onCreated: () => void }) {
  const [channelType, setChannelType] = useState("slack");
  const [webhookUrl, setWebhookUrl] = useState("");
  const [minSeverity, setMinSeverity] = useState("medium");
  const [submitting, setSubmitting] = useState(false);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!webhookUrl) return;
    setSubmitting(true);
    api
      .createAlertChannel({
        channel_type: channelType,
        config: channelType === "email" ? { email_address: webhookUrl } : { webhook_url: webhookUrl },
        min_severity: minSeverity,
        enabled: true,
      })
      .then(onCreated)
      .catch(() => {})
      .finally(() => setSubmitting(false));
  };

  return (
    <form onSubmit={submit} className="p-6 border border-white/[0.06] space-y-4">
      <SectionLabel>Create alert channel</SectionLabel>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <select
          className="input-field"
          value={channelType}
          onChange={(e) => setChannelType(e.target.value)}
        >
          <option value="slack">Slack</option>
          <option value="webhook">Webhook</option>
          <option value="email">Email</option>
        </select>
        <input
          className="input-field"
          placeholder={channelType === "email" ? "Email address" : "Webhook URL"}
          value={webhookUrl}
          onChange={(e) => setWebhookUrl(e.target.value)}
        />
        <select
          className="input-field"
          value={minSeverity}
          onChange={(e) => setMinSeverity(e.target.value)}
        >
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
          <option value="critical">Critical</option>
        </select>
      </div>
      <button
        type="submit"
        disabled={submitting}
        className="px-6 py-2 border border-white/15 text-[10px] font-mono tracking-[0.15em] uppercase hover:bg-white/[0.04] disabled:opacity-30 transition-colors"
      >
        {submitting ? "Creating…" : "Create Channel"}
      </button>
    </form>
  );
}
