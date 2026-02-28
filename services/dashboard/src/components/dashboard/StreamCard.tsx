import { motion } from "framer-motion";
import { Radio, Pause, AlertTriangle } from "lucide-react";

interface StreamCardProps {
  name: string;
  status: "active" | "paused" | "error";
  asrBackend: string;
  alertsCount: number;
  sentiment: string;
}

const statusConfig = {
  active: { color: "bg-emerald-500", icon: Radio, label: "Live" },
  paused: { color: "bg-amber-500", icon: Pause, label: "Paused" },
  error: { color: "bg-red-500", icon: AlertTriangle, label: "Error" },
};

export default function StreamCard({
  name,
  status,
  asrBackend,
  alertsCount,
  sentiment,
}: StreamCardProps) {
  const config = statusConfig[status];
  const StatusIcon = config.icon;

  return (
    <motion.div
      className="border border-white/[0.08] bg-white/[0.01] p-4 hover:border-white/20 transition-all duration-300 cursor-pointer group"
      whileHover={{ y: -2 }}
      transition={{ duration: 0.2 }}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2.5">
          <div
            className={`w-1.5 h-1.5 rounded-full ${config.color} ${
              status === "active" ? "animate-pulse" : ""
            }`}
          />
          <h3 className="text-xs font-medium tracking-tight">{name}</h3>
        </div>
        <StatusIcon
          className="w-3 h-3 text-white/20 group-hover:text-white/40 transition-colors"
          strokeWidth={1.5}
        />
      </div>

      <div className="mt-4 grid grid-cols-3 gap-3 text-[10px]">
        <div>
          <p className="text-white/15 mb-0.5">Engine</p>
          <p className="text-white/50 truncate">{asrBackend}</p>
        </div>
        <div>
          <p className="text-white/15 mb-0.5">Alerts</p>
          <p className={alertsCount > 0 ? "text-red-400" : "text-white/50"}>
            {alertsCount}
          </p>
        </div>
        <div>
          <p className="text-white/15 mb-0.5">Sentiment</p>
          <p className="text-white/50">{sentiment}</p>
        </div>
      </div>
    </motion.div>
  );
}
