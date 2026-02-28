import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { Shield, Users, Lock, Zap } from "lucide-react";

const EASE: [number, number, number, number] = [0.76, 0, 0.24, 1];

const features = [
  {
    icon: Shield,
    title: "Cryptographic Audit",
    description:
      "SHA-256 Merkle roots anchor every transcript segment to an immutable audit trail. Every hash verifiable, every anchor append-only.",
    colSpan: "md:col-span-2",
  },
  {
    icon: Users,
    title: "Speaker Diarization",
    description:
      "pyannote.audio 3.x real-time pipeline delivers ≤8% DER. Speaker IDs flow through every downstream event — alerts, sentiment, search.",
    colSpan: "md:col-span-1",
  },
  {
    icon: Lock,
    title: "Compliance & PII",
    description:
      "Microsoft Presidio with spaCy + GLiNER strips names, numbers, and accounts before storage. 95%+ recall. Zero-trust by default.",
    colSpan: "md:col-span-1",
  },
  {
    icon: Zap,
    title: "Pluggable ASR",
    description:
      "Hot-swap between Deepgram Nova-2 and Whisper V3 Turbo per-stream. Circuit breaker failover with zero downstream changes.",
    colSpan: "md:col-span-2",
  },
];

function FeatureCard({
  icon: Icon,
  title,
  description,
  colSpan,
  index,
}: {
  icon: typeof Shield;
  title: string;
  description: string;
  colSpan: string;
  index: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, margin: "-80px" });

  return (
    <motion.div
      ref={ref}
      className={`${colSpan} group relative bg-black border border-white/[0.08] p-10 md:p-14 hover:border-white/20 transition-colors duration-700`}
      initial={{ opacity: 0, y: 50 }}
      animate={isInView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.8, delay: index * 0.12, ease: EASE }}
    >
      {/* Subtle top gradient line on hover */}
      <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-white/0 via-white/5 to-white/0 group-hover:via-white/20 transition-all duration-700" />

      <Icon className="w-6 h-6 text-white/25 mb-8" strokeWidth={1} />
      <h3 className="text-xl md:text-2xl font-semibold tracking-tight">
        {title}
      </h3>
      <p className="mt-4 text-sm md:text-base text-white/35 leading-relaxed">
        {description}
      </p>
    </motion.div>
  );
}

export default function FeaturesGrid() {
  return (
    <section className="px-8 md:px-16 lg:px-24 py-40">
      <div className="max-w-[90rem] mx-auto">
        <motion.p
          className="text-[10px] tracking-[0.3em] uppercase text-white/25 mb-6"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 1 }}
        >
          Core Capabilities
        </motion.p>

        <motion.h2
          className="text-4xl md:text-5xl font-bold tracking-[-0.03em] mb-16"
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, ease: EASE }}
        >
          Built Different.
        </motion.h2>

        {/* Bento grid: 3 columns, staggered spans */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-[1px] bg-white/[0.04]">
          {features.map((feature, i) => (
            <FeatureCard key={feature.title} {...feature} index={i} />
          ))}
        </div>
      </div>
    </section>
  );
}
