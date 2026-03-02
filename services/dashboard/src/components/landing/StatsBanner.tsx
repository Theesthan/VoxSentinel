import { useRef } from "react";
import { motion, useInView } from "framer-motion";

interface Stat {
  value: string;
  label: string;
  suffix?: string;
}

const stats: Stat[] = [
  { value: "< 300", suffix: "ms", label: "End-to-end latency" },
  { value: "20", suffix: "+", label: "Concurrent streams per GPU" },
  { value: "95", suffix: "%+", label: "PII redaction recall" },
  { value: "O(n)", label: "Keyword matching complexity" },
];

export default function StatsBanner() {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: "-10%" });

  return (
    <section
      ref={ref}
      className="relative border-t border-white/[0.06] py-28 md:py-36"
    >
      {/* Background noise texture — subtle radial gradient */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_60%_40%_at_50%_0%,rgba(255,255,255,0.015),transparent)]" />
      </div>

      <div className="relative max-w-7xl mx-auto px-8 md:px-16">
        {/* Section label */}
        <motion.span
          className="block mb-16 text-[9px] font-mono tracking-[0.4em] text-white/20 uppercase"
          initial={{ opacity: 0 }}
          animate={inView ? { opacity: 1 } : {}}
          transition={{ duration: 0.6 }}
        >
          Performance benchmarks
        </motion.span>

        {/* Stats grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-12 md:gap-8">
          {stats.map((stat, i) => (
            <motion.div
              key={stat.label}
              className="group"
              initial={{ opacity: 0, y: 30 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{
                duration: 0.8,
                delay: 0.15 * i,
                ease: [0.22, 1, 0.36, 1],
              }}
            >
              {/* Stat number */}
              <div className="flex items-baseline gap-1">
                <span className="text-[clamp(2.8rem,6vw,5.5rem)] font-medium tracking-[-0.04em] leading-none text-white">
                  {stat.value}
                </span>
                {stat.suffix && (
                  <span className="text-[clamp(1rem,2vw,1.5rem)] font-medium tracking-[-0.02em] text-white/50">
                    {stat.suffix}
                  </span>
                )}
              </div>

              {/* Accent dash */}
              <motion.div
                className="w-6 h-[1px] bg-white/20 mt-4 mb-3"
                initial={{ scaleX: 0, originX: 0 }}
                animate={inView ? { scaleX: 1 } : {}}
                transition={{
                  duration: 0.6,
                  delay: 0.15 * i + 0.3,
                  ease: [0.22, 1, 0.36, 1],
                }}
              />

              {/* Label */}
              <p className="text-[11px] font-mono tracking-[0.08em] text-white/30 uppercase leading-relaxed">
                {stat.label}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
