import { useRef } from "react";
import { motion, useInView } from "framer-motion";

const EASE: [number, number, number, number] = [0.76, 0, 0.24, 1];

const blocks = [
  {
    number: "01",
    title: "Ingestion vs Blind Spots",
    ours: "Extract audio from RTSP/HLS streams instantly. FF&#8203;mpeg + PyAV normalize to 16 kHz mono PCM in real time.",
    theirs:
      "The Old World: Silent cameras and unmonitored calls. Blind spots where threats go undetected.",
  },
  {
    number: "02",
    title: "Pluggable ASR vs Vendor Lock-In",
    ours: "Deepgram Nova-2, Whisper V3 Turbo — swap engines on the fly, per stream. Zero downstream changes.",
    theirs:
      "The Old World: Locked into a single slow, expensive vendor. No fallback when it goes down.",
  },
  {
    number: "03",
    title: "Real-Time NLP vs Batch Processing",
    ours: "Aho-Corasick exact matching in O(n). RapidFuzz fuzzy detection. DistilBERT sentiment in <30ms.",
    theirs:
      "The Old World: Waiting hours for batch transcript processing. Threats discovered after the fact.",
  },
  {
    number: "04",
    title: "Engineered Alerts vs Missed Threats",
    ours: "WebSockets, Slack, and Webhooks dispatched in <50ms. Throttled, deduplicated, and retried.",
    theirs:
      "The Old World: Finding out when it's already too late. Alerts buried in unread emails.",
  },
];

function PipelineBlock({
  number,
  title,
  ours,
  theirs,
  index,
}: (typeof blocks)[number] & { index: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, margin: "-150px" });

  return (
    <motion.div
      ref={ref}
      className="border-t border-white/10 pt-10"
      initial={{ opacity: 0, y: 50 }}
      animate={isInView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.8, delay: index * 0.05, ease: EASE }}
    >
      <span className="text-[10px] font-mono tracking-[0.3em] text-white/25">
        {number}
      </span>
      <h3 className="mt-4 text-2xl md:text-3xl font-semibold tracking-tight">
        {title}
      </h3>
      <p className="mt-4 text-sm md:text-base text-white/60 leading-relaxed max-w-lg">
        {ours}
      </p>
      <p className="mt-3 text-sm text-white/25 leading-relaxed max-w-lg italic">
        {theirs}
      </p>
    </motion.div>
  );
}

export default function StickyPipeline() {
  return (
    <section
      id="pipeline"
      className="relative px-8 md:px-16 lg:px-24 py-40"
    >
      <div className="max-w-[90rem] mx-auto flex flex-col lg:flex-row gap-16 lg:gap-24">
        {/* Left sticky heading */}
        <div className="lg:w-1/2 lg:relative">
          <div className="lg:sticky lg:top-[30vh]">
            <motion.p
              className="text-[10px] tracking-[0.3em] uppercase text-white/25 mb-6"
              initial={{ opacity: 0 }}
              whileInView={{ opacity: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 1 }}
            >
              The Pipeline
            </motion.p>
            <h2 className="text-5xl md:text-6xl lg:text-7xl font-bold tracking-[-0.04em] leading-[0.95]">
              From Capture
              <br />
              to Alert.
            </h2>
            <p className="mt-6 text-sm text-white/30 max-w-sm leading-relaxed">
              Four stages. Sub-300ms. Each engineered to eliminate the blind
              spots that legacy systems leave behind.
            </p>
          </div>
        </div>

        {/* Right scrolling blocks */}
        <div className="lg:w-1/2 space-y-24 lg:space-y-32 lg:pt-[40vh] lg:pb-[30vh]">
          {blocks.map((block, i) => (
            <PipelineBlock key={block.number} {...block} index={i} />
          ))}
        </div>
      </div>
    </section>
  );
}
