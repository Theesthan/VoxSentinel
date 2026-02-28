import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { Link } from "react-router-dom";

const EASE: [number, number, number, number] = [0.76, 0, 0.24, 1];

/**
 * Masked line reveal: text slides up from below an overflow-hidden wrapper.
 * This is the signature scroll-triggered text reveal effect.
 */
function MaskedLine({
  children,
  delay = 0,
}: {
  children: React.ReactNode;
  delay?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  return (
    <div ref={ref} className="overflow-hidden">
      <motion.div
        initial={{ y: "100%" }}
        animate={isInView ? { y: "0%" } : {}}
        transition={{ duration: 1, ease: EASE, delay }}
      >
        {children}
      </motion.div>
    </div>
  );
}

export default function Hero() {
  return (
    <section className="relative min-h-screen flex flex-col justify-center px-8 md:px-16 lg:px-24">
      {/* Top border line */}
      <div className="absolute top-0 left-0 w-full h-[1px] bg-white/5" />

      <div className="max-w-[90rem] mx-auto w-full">
        {/* Overline */}
        <motion.p
          className="text-[10px] md:text-xs tracking-[0.3em] uppercase text-white/30 mb-8"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1, delay: 0.5 }}
        >
          VoxSentinel Intelligence Platform
        </motion.p>

        {/* Main heading — massive, geometric, tracked tight */}
        <h1 className="text-[clamp(3rem,8vw,9rem)] font-bold leading-[0.9] tracking-[-0.04em]">
          <MaskedLine delay={0.2}>A New Class</MaskedLine>
          <MaskedLine delay={0.35}>of Intelligence.</MaskedLine>
        </h1>

        {/* Subtext */}
        <motion.p
          className="mt-10 text-base md:text-xl text-white/50 max-w-2xl leading-relaxed tracking-tight"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, ease: EASE, delay: 0.8 }}
        >
          Sub-300ms end-to-end latency. Where others see noise, we extract the
          signal. Elite multi-source transcription and alerting.
        </motion.p>

        {/* CTA */}
        <motion.div
          className="mt-12 flex items-center gap-6"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, ease: EASE, delay: 1 }}
        >
          <Link
            to="/dashboard"
            className="group inline-flex items-center gap-3 border border-white/20 px-8 py-4 text-xs tracking-[0.2em] uppercase hover:bg-white hover:text-black transition-all duration-500"
          >
            Launch Dashboard
            <span className="inline-block transition-transform duration-300 group-hover:translate-x-1">
              →
            </span>
          </Link>
          <a
            href="#pipeline"
            className="text-xs tracking-[0.2em] uppercase text-white/30 hover:text-white/60 transition-colors duration-300"
          >
            Explore
          </a>
        </motion.div>
      </div>

      {/* Scroll indicator */}
      <motion.div
        className="absolute bottom-12 left-1/2 -translate-x-1/2 flex flex-col items-center gap-3"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.5, duration: 1 }}
      >
        <span className="text-[9px] tracking-[0.3em] uppercase text-white/20">
          Scroll
        </span>
        <motion.div
          className="w-[1px] h-12 bg-gradient-to-b from-white/20 to-transparent origin-top"
          animate={{ scaleY: [1, 0.4, 1] }}
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
