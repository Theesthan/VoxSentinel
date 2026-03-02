import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import {
  ShieldCheck,
  Users,
  EyeOff,
  Bell,
  Search,
} from "lucide-react";

/* ── Feature tile data ── */

interface Feature {
  icon: React.ReactNode;
  title: string;
  description: string;
  /** A small bespoke visual for the tile body */
  visual: React.ReactNode;
}

/* ── Micro visuals ── */

function HashChain() {
  const hashes = [
    "a9f3c1…d8e7",
    "0b12e4…7fa2",
    "c8d91b…4e60",
    "f2a0b7…1c3d",
  ];
  return (
    <div className="space-y-1">
      {hashes.map((h, i) => (
        <div key={i} className="flex items-center gap-2">
          <div className="w-1 h-1 rounded-full bg-white/20" />
          <span className="text-[10px] font-mono tracking-[0.06em] text-white/20">
            {h}
          </span>
          {i < hashes.length - 1 && (
            <span className="text-[10px] text-white/10 ml-1">↓</span>
          )}
        </div>
      ))}
    </div>
  );
}

function SpeakerRows() {
  const speakers = [
    { id: "SPK_01", width: "72%" },
    { id: "SPK_02", width: "45%" },
    { id: "SPK_03", width: "88%" },
  ];
  return (
    <div className="space-y-2">
      {speakers.map((s) => (
        <div key={s.id} className="flex items-center gap-3">
          <span className="text-[9px] font-mono text-white/25 w-12 shrink-0">
            {s.id}
          </span>
          <div className="h-[3px] bg-white/[0.08] flex-1 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-white/20 rounded-full"
              initial={{ width: 0 }}
              whileInView={{ width: s.width }}
              viewport={{ once: true }}
              transition={{ duration: 1.2, ease: [0.22, 1, 0.36, 1] }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

function RedactedLines() {
  return (
    <div className="space-y-1.5">
      {[82, 55, 70, 40].map((w, i) => (
        <div key={i} className="flex items-center gap-2">
          <div
            className="h-[6px] rounded-[2px] bg-white/[0.06]"
            style={{ width: `${w}%` }}
          />
          {i === 1 && (
            <span className="text-[8px] font-mono text-red-400/50 tracking-wider">
              ████ REDACTED
            </span>
          )}
        </div>
      ))}
    </div>
  );
}

function AlertFanOut() {
  const channels = ["Slack", "Email", "Webhook", "Audit DB"];
  return (
    <div className="flex items-center">
      <div className="w-2 h-2 rounded-full bg-white/30 shrink-0" />
      <div className="w-8 h-[1px] bg-white/10" />
      <div className="space-y-1">
        {channels.map((ch) => (
          <div key={ch} className="flex items-center gap-2">
            <div className="w-4 h-[1px] bg-white/10" />
            <span className="text-[9px] font-mono tracking-[0.1em] text-white/25 uppercase">
              {ch}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function SearchGrid() {
  return (
    <div className="grid grid-cols-3 gap-1">
      {Array.from({ length: 9 }).map((_, i) => (
        <motion.div
          key={i}
          className="h-4 bg-white/[0.04] rounded-[1px]"
          whileInView={{ opacity: [0, 1] }}
          viewport={{ once: true }}
          transition={{ delay: i * 0.05 }}
        />
      ))}
    </div>
  );
}

/* ── Feature definitions ── */

const features: Feature[] = [
  {
    icon: <ShieldCheck className="w-4 h-4" />,
    title: "Cryptographic Audit",
    description:
      "Every transcript chunk is SHA-256-chained on write. Tamper-proof logs that survive legal discovery.",
    visual: <HashChain />,
  },
  {
    icon: <Users className="w-4 h-4" />,
    title: "Speaker Diarization",
    description:
      "Cluster speakers across multi-party calls. Attribute words to voices without pre-enrollment.",
    visual: <SpeakerRows />,
  },
  {
    icon: <EyeOff className="w-4 h-4" />,
    title: "Compliance & PII",
    description:
      "Names, credit cards, health data — identified and redacted in real time before storage.",
    visual: <RedactedLines />,
  },
  {
    icon: <Bell className="w-4 h-4" />,
    title: "Multi-Channel Alerts",
    description:
      "Rules fire into Slack, webhooks, email, and an immutable audit database atomically.",
    visual: <AlertFanOut />,
  },
  {
    icon: <Search className="w-4 h-4" />,
    title: "Search Every Word",
    description:
      "Full-text search across every transcript ever captured. Instant recall across terabytes of audio.",
    visual: <SearchGrid />,
  },
];

/* ── Tile layout classes (asymmetric bento) ── */

const tileClasses = [
  "md:col-span-7 md:row-span-2", // Cryptographic Audit — tall left
  "md:col-span-5",                // Speaker Diarization — top right
  "md:col-span-5",                // Compliance — bottom right
  "md:col-span-6",                // Multi-Channel Alerts — bottom left
  "md:col-span-6",                // Search — bottom right
];

/* ── Main component ── */

export default function FeaturesGrid() {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: "-5%" });

  return (
    <section
      ref={ref}
      className="relative border-t border-white/[0.06] py-28 md:py-36"
    >
      <div className="max-w-7xl mx-auto px-8 md:px-16">
        {/* Section header */}
        <motion.div
          className="mb-16"
          initial={{ opacity: 0 }}
          animate={inView ? { opacity: 1 } : {}}
          transition={{ duration: 0.6 }}
        >
          <span className="block mb-4 text-[9px] font-mono tracking-[0.4em] text-white/20 uppercase">
            Capabilities
          </span>
          <h2 className="text-[clamp(2rem,4vw,3.8rem)] font-medium tracking-[-0.03em] leading-[1.1]">
            Everything built for
            <br />
            <span className="text-white/30">what others ignore.</span>
          </h2>
        </motion.div>

        {/* Bento grid */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
          {features.map((feature, i) => (
            <motion.div
              key={feature.title}
              className={`${tileClasses[i]} group relative p-8 border border-white/[0.06] bg-white/[0.01] hover:bg-white/[0.025] transition-colors duration-500`}
              initial={{ opacity: 0, y: 40 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{
                duration: 0.7,
                delay: 0.1 * i,
                ease: [0.22, 1, 0.36, 1],
              }}
            >
              {/* Icon + title */}
              <div className="flex items-center gap-3 mb-3">
                <span className="text-white/30">{feature.icon}</span>
                <h3 className="text-[13px] font-mono tracking-[0.08em] text-white/50 uppercase">
                  {feature.title}
                </h3>
              </div>

              {/* Description */}
              <p className="text-[14px] leading-[1.7] text-white/30 mb-8 max-w-sm">
                {feature.description}
              </p>

              {/* Visual */}
              <div className="mt-auto">{feature.visual}</div>

              {/* Corner accent on hover */}
              <div className="absolute top-0 right-0 w-6 h-6 border-t border-r border-white/0 group-hover:border-white/10 transition-colors duration-500" />
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
