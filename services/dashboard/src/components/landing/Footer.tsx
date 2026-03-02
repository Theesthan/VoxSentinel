import { motion, useInView } from "framer-motion";
import { useRef } from "react";
import { Link } from "react-router-dom";

export default function Footer() {
  const ctaRef = useRef<HTMLDivElement>(null);
  const ctaInView = useInView(ctaRef, { once: true, margin: "-10%" });

  return (
    <footer className="border-t border-white/[0.06]">
      {/* ── CTA Banner ── */}
      <div ref={ctaRef} className="py-32 md:py-44">
        <div className="max-w-7xl mx-auto px-8 md:px-16 text-center">
          <motion.h2
            className="text-[clamp(2.4rem,5.5vw,5rem)] font-medium tracking-[-0.03em] leading-[1.05] mb-8"
            initial={{ opacity: 0, y: 40 }}
            animate={ctaInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
          >
            Ready to listen.
          </motion.h2>

          <motion.p
            className="text-[15px] text-white/30 mb-12 max-w-md mx-auto leading-relaxed"
            initial={{ opacity: 0 }}
            animate={ctaInView ? { opacity: 1 } : {}}
            transition={{ duration: 0.6, delay: 0.3 }}
          >
            Enter the dashboard, connect a stream, and hear what your systems
            have been missing.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={ctaInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6, delay: 0.5 }}
          >
            <Link
              to="/login"
              className="group relative inline-flex items-center gap-3 px-10 py-4 border border-white/20 text-[12px] font-mono tracking-[0.2em] uppercase overflow-hidden transition-colors duration-500 hover:text-black"
            >
              {/* Sliding fill */}
              <span className="absolute inset-0 bg-white translate-x-[-101%] group-hover:translate-x-0 transition-transform duration-500 ease-[cubic-bezier(0.22,1,0.36,1)]" />
              <span className="relative z-10">Enter Dashboard</span>
              <span className="relative z-10 text-white/40 group-hover:text-black/40 transition-colors duration-500">
                →
              </span>
            </Link>
          </motion.div>
        </div>
      </div>

      {/* ── Bottom bar ── */}
      <div className="border-t border-white/[0.04] py-8">
        <div className="max-w-7xl mx-auto px-8 md:px-16 flex flex-col md:flex-row items-center justify-between gap-4">
          {/* Left — Brand */}
          <span className="text-[10px] font-mono tracking-[0.3em] text-white/20 uppercase">
            VoxSentinel
          </span>

          {/* Center links */}
          <div className="flex items-center gap-8">
            {[
              { label: "GitHub", href: "#" },
              { label: "API Docs", href: "#" },
              { label: "Architecture", href: "#" },
            ].map((link) => (
              <a
                key={link.label}
                href={link.href}
                className="text-[10px] font-mono tracking-[0.15em] text-white/15 hover:text-white/40 transition-colors duration-300 uppercase"
              >
                {link.label}
              </a>
            ))}
          </div>

          {/* Right — Copyright */}
          <span className="text-[10px] font-mono tracking-[0.15em] text-white/10">
            © {new Date().getFullYear()} VoxSentinel
          </span>
        </div>
      </div>
    </footer>
  );
}
