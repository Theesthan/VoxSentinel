import { motion } from "framer-motion";
import { Link } from "react-router-dom";

export default function Footer() {
  return (
    <footer className="border-t border-white/[0.06] px-8 md:px-16 lg:px-24 py-20">
      <div className="max-w-[90rem] mx-auto">
        {/* CTA Banner */}
        <motion.div
          className="border border-white/10 p-12 md:p-20 text-center mb-20"
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, ease: [0.76, 0, 0.24, 1] }}
        >
          <h2 className="text-3xl md:text-5xl font-bold tracking-[-0.03em]">
            Ready to listen.
          </h2>
          <p className="mt-4 text-sm text-white/30 max-w-md mx-auto">
            Deploy the full pipeline in minutes. Monitor, detect, alert — in
            real time.
          </p>
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-3 border border-white/20 px-10 py-5 mt-10 text-xs tracking-[0.2em] uppercase hover:bg-white hover:text-black transition-all duration-500"
          >
            Enter Dashboard →
          </Link>
        </motion.div>

        {/* Bottom bar */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-8">
          <div>
            <p className="text-sm font-semibold tracking-tight">VoxSentinel</p>
            <p className="mt-1 text-[10px] text-white/20 tracking-wider">
              Real-Time Intelligence Platform
            </p>
          </div>

          <div className="flex items-center gap-8 text-[10px] text-white/20 tracking-wider uppercase">
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-white/50 transition-colors"
            >
              GitHub
            </a>
            <a href="/docs" className="hover:text-white/50 transition-colors">
              API Docs
            </a>
            <span>© 2026</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
