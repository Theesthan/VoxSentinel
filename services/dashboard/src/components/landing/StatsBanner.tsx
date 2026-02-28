import { useRef } from "react";
import { motion, useInView } from "framer-motion";

const EASE: [number, number, number, number] = [0.76, 0, 0.24, 1];

const stats = [
  { value: "< 300ms", label: "End-to-End Latency" },
  { value: "20+", label: "Concurrent Streams per GPU" },
  { value: "95%+", label: "PII Redaction Recall" },
  { value: "O(n)", label: "Keyword Matching Complexity" },
];

export default function StatsBanner() {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  return (
    <section
      ref={ref}
      className="border-y border-white/10 py-20 md:py-24 px-8 md:px-16 lg:px-24"
    >
      <div className="max-w-[90rem] mx-auto grid grid-cols-2 md:grid-cols-4 gap-12 md:gap-8">
        {stats.map((stat, i) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 30 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.8, delay: i * 0.15, ease: EASE }}
          >
            <p className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-tighter">
              {stat.value}
            </p>
            <p className="mt-3 text-[10px] md:text-xs tracking-[0.15em] uppercase text-white/40">
              {stat.label}
            </p>
          </motion.div>
        ))}
      </div>
    </section>
  );
}
