import { useRef, useEffect, useState } from "react";
import { motion, useInView } from "framer-motion";
import { Link } from "react-router-dom";

const EASE: [number, number, number, number] = [0.76, 0, 0.24, 1];

/* ── Masked line reveal ───────────────────────────────────────── */
function MaskedLine({
  children,
  delay = 0,
}: {
  children: React.ReactNode;
  delay?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, margin: "-80px" });

  return (
    <div ref={ref} className="overflow-hidden">
      <motion.div
        initial={{ y: "110%" }}
        animate={isInView ? { y: "0%" } : {}}
        transition={{ duration: 1.1, ease: EASE, delay }}
      >
        {children}
      </motion.div>
    </div>
  );
}

/* ── Animated waveform matrix ─────────────────────────────────── */
function WaveformMatrix() {
  const [bars] = useState(() =>
    Array.from({ length: 48 }, (_, i) => ({
      id: i,
      height: 20 + Math.random() * 60,
      delay: Math.random() * 2,
      duration: 1.5 + Math.random() * 2,
    })),
  );

  return (
    <div className="flex items-end gap-[2px] h-full w-full p-8">
      {bars.map((bar) => (
        <motion.div
          key={bar.id}
          className="flex-1 bg-white/[0.06] rounded-t-sm"
          style={{ height: `${bar.height}%` }}
          animate={{
            height: [`${bar.height}%`, `${20 + Math.random() * 70}%`, `${bar.height}%`],
            opacity: [0.3, 0.8, 0.3],
          }}
          transition={{
            duration: bar.duration,
            delay: bar.delay,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />
      ))}
    </div>
  );
}

/* ── Floating data fragments ──────────────────────────────────── */
function DataFragments() {
  const fragments = [
    { text: "SPEAKER_01", x: "10%", y: "15%", delay: 0 },
    { text: '"gun" — exact match', x: "60%", y: "25%", delay: 0.5 },
    { text: "sentiment: negative (0.89)", x: "25%", y: "70%", delay: 1 },
    { text: "latency: 187ms", x: "70%", y: "80%", delay: 1.5 },
    { text: "PII: ████████", x: "45%", y: "45%", delay: 2 },
  ];

  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden">
      {fragments.map((f, i) => (
        <motion.span
          key={i}
          className="absolute font-mono text-[9px] tracking-wider text-white/[0.07] whitespace-nowrap"
          style={{ left: f.x, top: f.y }}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{
            delay: 2 + f.delay,
            duration: 1.2,
            ease: EASE,
          }}
        >
          {f.text}
        </motion.span>
      ))}
    </div>
  );
}

/* ── Floating grid ────────────────────────────────────────────── */
function GridOverlay() {
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <motion.div
      className="absolute inset-0 pointer-events-none"
      initial={{ opacity: 0 }}
      animate={mounted ? { opacity: 1 } : {}}
      transition={{ duration: 2, delay: 0.5 }}
      style={{
        backgroundImage:
          "linear-gradient(rgba(255,255,255,.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.03) 1px, transparent 1px)",
        backgroundSize: "60px 60px",
      }}
    />
  );
}

export default function Hero() {
  return (
    <section className="relative min-h-screen flex flex-col justify-center overflow-hidden">
      {/* Faint grid */}
      <GridOverlay />

      {/* Top line */}
      <div className="absolute top-0 left-0 w-full h-[1px] bg-white/[0.04]" />

      <div className="relative z-10 max-w-[96rem] mx-auto w-full px-8 md:px-16 lg:px-24">
        <div className="flex flex-col lg:flex-row items-start lg:items-center gap-16 lg:gap-24">
          {/* Left — text stack */}
          <div className="flex-1 max-w-4xl">
            {/* Overline */}
            <motion.div
              className="flex items-center gap-3 mb-10"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 1.2, delay: 0.3 }}
            >
              <div className="w-2 h-2 rounded-full bg-white/20" />
              <span className="text-[10px] tracking-[0.4em] uppercase text-white/25 font-mono">
                Real-Time Auditory Intelligence
              </span>
            </motion.div>

            {/* Main heading */}
            <h1 className="text-[clamp(3.2rem,8vw,9.5rem)] font-bold leading-[0.88] tracking-[-0.045em]">
              <MaskedLine delay={0.15}>
                <span className="block">A New Class</span>
              </MaskedLine>
              <MaskedLine delay={0.3}>
                <span className="block">of Auditory</span>
              </MaskedLine>
              <MaskedLine delay={0.45}>
                <span className="block text-white/40">Intelligence.</span>
              </MaskedLine>
            </h1>

            {/* Subtext */}
            <motion.div
              className="mt-12 max-w-xl"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 1, ease: EASE, delay: 0.9 }}
            >
              <p className="text-base md:text-lg text-white/40 leading-[1.7] tracking-[-0.01em]">
                VoxSentinel ingests live streams and uploaded audio, transcribes
                in real time, and dispatches keyword, sentiment, and compliance
                alerts in under 300&nbsp;ms.
              </p>
              <p className="mt-4 text-sm text-white/20 leading-relaxed">
                Where others see noise, we extract the signal. Live or
                post&#8209;call, every word is accounted for.
              </p>
            </motion.div>

            {/* CTAs */}
            <motion.div
              className="mt-14 flex flex-wrap items-center gap-5"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 1, ease: EASE, delay: 1.1 }}
            >
              <Link
                to="/dashboard"
                className="group relative inline-flex items-center gap-4 border border-white/20 px-10 py-[18px] text-[11px] tracking-[0.22em] uppercase overflow-hidden transition-all duration-600 hover:border-white/40"
              >
                <span className="absolute inset-0 bg-white translate-x-[-101%] group-hover:translate-x-0 transition-transform duration-500 ease-[cubic-bezier(0.76,0,0.24,1)]" />
                <span className="relative z-10 group-hover:text-black transition-colors duration-300">
                  Launch Live Intelligence
                </span>
                <span className="relative z-10 group-hover:text-black transition-colors duration-300 group-hover:translate-x-1 inline-block">
                  →
                </span>
              </Link>

              <a
                href="#pipeline"
                className="inline-flex items-center gap-3 px-6 py-[18px] text-[11px] tracking-[0.22em] uppercase text-white/25 hover:text-white/60 transition-colors duration-400"
              >
                <div className="w-1 h-1 rounded-full bg-white/25" />
                Run a File Analysis
              </a>
            </motion.div>
          </div>

          {/* Right — abstract waveform block */}
          <motion.div
            className="hidden lg:block w-[420px] h-[500px] border border-white/[0.06] relative"
            initial={{ opacity: 0, x: 40 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 1.2, ease: EASE, delay: 0.6 }}
          >
            <DataFragments />
            <WaveformMatrix />

            {/* Corner decorations */}
            <div className="absolute top-0 left-0 w-4 h-[1px] bg-white/20" />
            <div className="absolute top-0 left-0 w-[1px] h-4 bg-white/20" />
            <div className="absolute bottom-0 right-0 w-4 h-[1px] bg-white/20" />
            <div className="absolute bottom-0 right-0 w-[1px] h-4 bg-white/20" />

            {/* Label */}
            <span className="absolute bottom-3 left-4 text-[8px] font-mono tracking-[0.3em] uppercase text-white/10">
              Multi-stream waveform matrix
            </span>
          </motion.div>
        </div>
      </div>

      {/* Scroll indicator */}
      <motion.div
        className="absolute bottom-12 left-1/2 -translate-x-1/2 flex flex-col items-center gap-3"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 2, duration: 1 }}
      >
        <span className="text-[8px] tracking-[0.4em] uppercase text-white/15 font-mono">
          Scroll
        </span>
        <motion.div
          className="w-[1px] h-16 bg-gradient-to-b from-white/15 to-transparent origin-top"
          animate={{ scaleY: [1, 0.3, 1] }}
          transition={{
            duration: 2.5,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />
      </motion.div>
    </section>
  );
}
