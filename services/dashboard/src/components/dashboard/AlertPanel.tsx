import { motion } from "framer-motion";
import { Bell } from "lucide-react";

interface Alert {
  id: string;
  severity: "critical" | "high" | "medium" | "low";
  type: string;
  matchedRule: string;
  streamName: string;
  time: string;
}

const severityStyles: Record<Alert["severity"], string> = {
  critical: "border-l-red-500/60 bg-red-500/[0.03]",
  high: "border-l-orange-500/60 bg-orange-500/[0.03]",
  medium: "border-l-amber-500/60 bg-amber-500/[0.03]",
  low: "border-l-blue-500/60 bg-blue-500/[0.03]",
};

const MOCK_ALERTS: Alert[] = [
  {
    id: "1",
    severity: "critical",
    type: "keyword",
    matchedRule: "gun",
    streamName: "Lobby Camera 1",
    time: "2s ago",
  },
  {
    id: "2",
    severity: "high",
    type: "sentiment",
    matchedRule: "Negative escalation",
    streamName: "Call Center Line 4",
    time: "14s ago",
  },
  {
    id: "3",
    severity: "medium",
    type: "compliance",
    matchedRule: "account_number",
    streamName: "Meeting Room B",
    time: "1m ago",
  },
  {
    id: "4",
    severity: "low",
    type: "keyword",
    matchedRule: "frustrated",
    streamName: "Call Center Line 2",
    time: "3m ago",
  },
  {
    id: "5",
    severity: "critical",
    type: "keyword",
    matchedRule: "help",
    streamName: "Parking Level 2",
    time: "5m ago",
  },
];

export default function AlertPanel() {
  return (
    <div className="border border-white/[0.08] bg-white/[0.01] h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.06]">
        <div className="flex items-center gap-2">
          <Bell className="w-3.5 h-3.5 text-white/25" strokeWidth={1.5} />
          <h2 className="text-xs font-medium tracking-tight">Alerts</h2>
        </div>
        <span className="text-[9px] bg-red-500/15 text-red-400 px-2 py-0.5 tracking-wider font-mono">
          {MOCK_ALERTS.length} ACTIVE
        </span>
      </div>

      {/* Alert list */}
      <div className="flex-1 overflow-auto divide-y divide-white/[0.04]">
        {MOCK_ALERTS.map((alert, i) => (
          <motion.div
            key={alert.id}
            className={`px-4 py-3 border-l-2 ${severityStyles[alert.severity]} cursor-pointer hover:bg-white/[0.02] transition-colors`}
            initial={{ opacity: 0, x: 10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.08, duration: 0.4 }}
          >
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <p className="text-[11px] font-medium truncate">
                  {alert.matchedRule}
                </p>
                <p className="text-[9px] text-white/25 mt-0.5 truncate">
                  {alert.streamName} · {alert.type}
                </p>
              </div>
              <span className="text-[9px] text-white/15 shrink-0 font-mono">
                {alert.time}
              </span>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
