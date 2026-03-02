import { useRef } from "react";
import { motion, useScroll, useTransform } from "framer-motion";

interface PipelineStep {
  number: string;
  title: string;
  description: string;
  contrast: string;
  visual: React.ReactNode;
}

/* ── Tiny bespoke visuals for each pipeline card ── */

function WaveformBars() {
  return (
    <div className="flex items-end gap-[2px] h-8">
      {Array.from({ length: 28 }).map((_, i) => {
        const h = 8 + Math.sin(i * 0.7) * 18 + Math.random() * 6;
        return (
          <motion.div
            key={i}
            className="w-[3px] bg-white/20 rounded-[1px]"
            style={{ height: `${h}px` }}
            animate={{ height: [`${h}px`, `${h * 0.4}px`, `${h}px`] }}
            transition={{
              duration: 1.6 + Math.random() * 0.8,
              repeat: Infinity,
              ease: "easeInOut",
              delay: i * 0.05,
            }}
          />
        );
      })}
    </div>
  );
}

function ASRBadges() {
  return (
    <div className="flex flex-wrap gap-2">
      {["Whisper", "Deepgram", "Vosk", "Custom"].map((label) => (
        <span
          key={label}
          className="px-3 py-1 border border-white/10 text-[10px] font-mono tracking-[0.1em] text-white/40 uppercase"
        >
          {label}
        </span>
      ))}
    </div>
  );
}

function NLPStream() {
  const labels = ["PII_DETECTED", "SENTIMENT: 0.87", "KEYWORD_HIT", "SPEAKER_02"];
  return (
    <div className="space-y-1.5">
      {labels.map((l, i) => (
        <motion.div
          key={l}
          className="text-[10px] font-mono tracking-[0.08em] text-white/25"
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: i * 0.2, duration: 0.4 }}
        >
          <span className="text-white/40">→</span> {l}
        </motion.div>
      ))}
    </div>
  );
}

function AlertPulse() {
  return (
    <div className="flex items-center gap-4">
      {["Slack", "Webhook", "DB"].map((ch, i) => (
        <div key={ch} className="flex items-center gap-2">
          <motion.div
            className="w-2 h-2 rounded-full bg-white/40"
            animate={{ scale: [1, 1.6, 1], opacity: [0.4, 0.9, 0.4] }}
            transition={{
              duration: 2,
              repeat: Infinity,
              delay: i * 0.4,
            }}
          />
          <span className="text-[10px] font-mono tracking-[0.1em] text-white/30 uppercase">
            {ch}
          </span>
        </div>
      ))}
    </div>
  );
}

/* ── Pipeline step data ── */

const steps: PipelineStep[] = [
  {
    number: "01",
    title: "Ingestion",
    contrast: "vs Blind Spots",
    description:
      "RTSP, SRT, raw PCM, microphone — every audio source lands in a unified ring buffer. Zero frames dropped, zero format wars.",
    visual: <WaveformBars />,
  },
  {
    number: "02",
    title: "Pluggable ASR",
    contrast: "vs Vendor Lock-In",
    description:
      "Swap speech-to-text engines without touching a single pipeline config. Whisper today, Deepgram tomorrow, your own fine-tune next week.",
    visual: <ASRBadges />,
  },
  {
    number: "03",
    title: "Real-Time NLP",
    contrast: "vs Batch Processing",
    description:
      "Sentiment, PII, keyword graphs, speaker diarization — all computed on the partial transcript, not after the conversation ends.",
    visual: <NLPStream />,
  },
  {
    number: "04",
    title: "Engineered Alerts",
    contrast: "vs Missed Threats",
    description:
      "Rule engine evaluates every chunk against user-defined patterns. Hits fan-out to Slack, webhooks, and the audit log atomically.",
    visual: <AlertPulse />,
  },
];

/* ── Main component ── */

export default function StickyPipeline() {
  const containerRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start start", "end end"],
  });

  // Subtle vertical progress line
  const lineScaleY = useTransform(scrollYProgress, [0, 1], [0, 1]);

  return (
    <section
      ref={containerRef}
      className="relative border-t border-white/[0.06]"
    >
      <div className="max-w-7xl mx-auto px-8 md:px-16">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-0 lg:gap-16">
          {/* ── Left column: sticky heading ── */}
          <div className="lg:col-span-4 pt-28 lg:pt-0">
            <div className="lg:sticky lg:top-0 lg:h-screen lg:flex lg:flex-col lg:justify-center">
              <span className="block mb-4 text-[9px] font-mono tracking-[0.4em] text-white/20 uppercase">
                Architecture
              </span>
              <h2 className="text-[clamp(2.2rem,4.5vw,4.5rem)] font-medium tracking-[-0.03em] leading-[1.05]">
                From Capture
                <br />
                <span className="text-white/30">to Alert.</span>
              </h2>

              {/* Progress indicator */}
              <div className="relative mt-12 h-20 w-[1px] bg-white/[0.06] hidden lg:block">
                <motion.div
                  className="absolute top-0 left-0 w-full bg-white/40 origin-top"
                  style={{ scaleY: lineScaleY, height: "100%" }}
                />
              </div>
            </div>
          </div>

          {/* ── Right column: scrolling cards ── */}
          <div className="lg:col-span-8 py-28 lg:py-40 space-y-32 md:space-y-40">
            {steps.map((step) => (
              <PipelineCard key={step.number} step={step} />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

/* ── Individual pipeline card ── */

function PipelineCard({ step }: { step: PipelineStep }) {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start 0.8", "start 0.3"],
  });

  const opacity = useTransform(scrollYProgress, [0, 1], [0, 1]);
  const y = useTransform(scrollYProgress, [0, 1], [60, 0]);

  return (
    <motion.div ref={ref} style={{ opacity, y }}>
      {/* Step number + contrast label */}
      <div className="flex items-center gap-4 mb-6">
        <span className="text-[10px] font-mono tracking-[0.3em] text-white/15">
          {step.number}
        </span>
        <div className="h-[1px] w-8 bg-white/10" />
        <span className="text-[10px] font-mono tracking-[0.15em] text-white/20 uppercase">
          {step.contrast}
        </span>
      </div>

      {/* Title */}
      <h3 className="text-[clamp(1.6rem,3vw,2.8rem)] font-medium tracking-[-0.02em] leading-[1.15] mb-6">
        {step.title}
      </h3>

      {/* Description */}
      <p className="text-[15px] leading-[1.8] text-white/40 max-w-xl mb-8">
        {step.description}
      </p>

      {/* Visual element */}
      <div className="p-6 border border-white/[0.06] bg-white/[0.01]">
        {step.visual}
      </div>
    </motion.div>
  );
}
