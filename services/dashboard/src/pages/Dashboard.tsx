import { motion } from "framer-motion";
import DashboardShell from "@/components/dashboard/DashboardShell";
import StreamCard from "@/components/dashboard/StreamCard";
import AlertPanel from "@/components/dashboard/AlertPanel";
import TranscriptViewer from "@/components/dashboard/TranscriptViewer";
import { Badge } from "@/components/ui/badge";

const MOCK_STREAMS = [
  {
    name: "Lobby Camera 1",
    status: "active" as const,
    asrBackend: "Deepgram Nova-2",
    alertsCount: 3,
    sentiment: "Negative",
  },
  {
    name: "Lobby Camera 2",
    status: "active" as const,
    asrBackend: "Whisper V3",
    alertsCount: 0,
    sentiment: "Neutral",
  },
  {
    name: "Call Center Line 4",
    status: "active" as const,
    asrBackend: "Deepgram Nova-2",
    alertsCount: 1,
    sentiment: "Negative",
  },
  {
    name: "Meeting Room B",
    status: "paused" as const,
    asrBackend: "Whisper V3",
    alertsCount: 0,
    sentiment: "Neutral",
  },
  {
    name: "Parking Level 2",
    status: "error" as const,
    asrBackend: "Deepgram Nova-2",
    alertsCount: 0,
    sentiment: "N/A",
  },
  {
    name: "Main Entrance",
    status: "active" as const,
    asrBackend: "Deepgram Nova-2",
    alertsCount: 0,
    sentiment: "Positive",
  },
];

export default function Dashboard() {
  const activeCount = MOCK_STREAMS.filter(
    (s) => s.status === "active",
  ).length;

  return (
    <DashboardShell>
      {/* Header bar */}
      <div className="h-14 flex items-center justify-between px-6 border-b border-white/[0.06] shrink-0">
        <div>
          <h1 className="text-xs font-semibold tracking-tight">Live Monitor</h1>
          <p className="text-[9px] text-white/25 tracking-wider mt-0.5 font-mono">
            {activeCount} STREAMS ACTIVE
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant="success">SYSTEM OK</Badge>
          <motion.div
            className="w-7 h-7 rounded bg-white/5 flex items-center justify-center text-[10px] font-mono text-white/40 cursor-pointer hover:bg-white/10 transition-colors"
            whileHover={{ scale: 1.05 }}
          >
            ?
          </motion.div>
        </div>
      </div>

      {/* Content grid */}
      <div className="flex-1 p-5 grid grid-cols-1 xl:grid-cols-3 gap-5 overflow-auto min-h-0">
        {/* Left column: Streams + Transcript */}
        <div className="xl:col-span-2 flex flex-col gap-5 min-h-0">
          {/* Stream cards grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {MOCK_STREAMS.map((stream, i) => (
              <motion.div
                key={stream.name}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.06, duration: 0.4 }}
              >
                <StreamCard {...stream} />
              </motion.div>
            ))}
          </div>

          {/* Live transcript (takes remaining height) */}
          <div className="flex-1 min-h-[300px]">
            <TranscriptViewer />
          </div>
        </div>

        {/* Right column: Alerts */}
        <div className="min-h-[400px] xl:min-h-0">
          <AlertPanel />
        </div>
      </div>
    </DashboardShell>
  );
}
