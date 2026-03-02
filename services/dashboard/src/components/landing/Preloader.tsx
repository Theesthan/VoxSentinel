import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";

const EASE_OUT_EXPO: [number, number, number, number] = [0.16, 1, 0.3, 1];
const EASE_CUBIC: [number, number, number, number] = [0.76, 0, 0.24, 1];

const steps = [
  "Initializing…",
  "Linking RTSP streams…",
  "Compiling keyword graphs…",
  "Calibrating VAD thresholds…",
  "Access granted.",
];

export default function Preloader({ onComplete }: { onComplete: () => void }) {
  const [currentStep, setCurrentStep] = useState(0);
  const [isExiting, setIsExiting] = useState(false);

  const handleComplete = useCallback(() => {
    setIsExiting(true);
    setTimeout(onComplete, 900);
  }, [onComplete]);

  useEffect(() => {
    const timers = [
      setTimeout(() => setCurrentStep(1), 800),
      setTimeout(() => setCurrentStep(2), 1700),
      setTimeout(() => setCurrentStep(3), 2500),
      setTimeout(() => setCurrentStep(4), 3400),
      setTimeout(() => handleComplete(), 4200),
    ];
    return () => timers.forEach(clearTimeout);
  }, [handleComplete]);

  return (
    <AnimatePresence>
      {!isExiting && (
        <motion.div
          className="fixed inset-0 z-[100] bg-black flex flex-col items-center justify-center"
          exit={{ opacity: 0, filter: "blur(8px)" }}
          transition={{ duration: 0.9, ease: EASE_OUT_EXPO }}
        >
          {/* Horizontal scan line */}
          <motion.div
            className="absolute top-0 left-0 h-[1px] bg-gradient-to-r from-transparent via-white/40 to-transparent"
            initial={{ width: "0%" }}
            animate={{
              width: `${((currentStep + 1) / steps.length) * 100}%`,
            }}
            transition={{ duration: 0.7, ease: EASE_OUT_EXPO }}
          />

          {/* Grid overlay */}
          <div
            className="absolute inset-0 opacity-[0.015]"
            style={{
              backgroundImage:
                "linear-gradient(rgba(255,255,255,.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.1) 1px, transparent 1px)",
              backgroundSize: "80px 80px",
            }}
          />

          {/* Ambient pulse */}
          <motion.div
            className="absolute w-[400px] h-[400px] rounded-full"
            style={{
              background:
                "radial-gradient(circle, rgba(255,255,255,0.02) 0%, transparent 70%)",
            }}
            animate={{ scale: [1, 1.4, 1], opacity: [0.4, 0.7, 0.4] }}
            transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
          />

          {/* VoxSentinel wordmark */}
          <motion.div
            className="mb-16"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 1.5, ease: EASE_CUBIC }}
          >
            <span className="text-[10px] font-mono tracking-[0.5em] uppercase text-white/15">
              VoxSentinel
            </span>
          </motion.div>

          {/* Step text */}
          <div className="relative h-8 flex items-center justify-center">
            <AnimatePresence mode="wait">
              <motion.p
                key={currentStep}
                className="font-mono text-[11px] tracking-[0.3em] uppercase text-white/50"
                initial={{ opacity: 0, y: 10, filter: "blur(4px)" }}
                animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                exit={{ opacity: 0, y: -10, filter: "blur(4px)" }}
                transition={{ duration: 0.45, ease: EASE_OUT_EXPO }}
              >
                {steps[currentStep]}
              </motion.p>
            </AnimatePresence>
          </div>

          {/* Step dot indicators */}
          <div className="absolute bottom-16 flex gap-3">
            {steps.map((_, i) => (
              <motion.div
                key={i}
                className="w-6 h-[1px]"
                animate={{
                  backgroundColor:
                    i <= currentStep
                      ? "rgba(255,255,255,0.5)"
                      : "rgba(255,255,255,0.06)",
                }}
                transition={{ duration: 0.4 }}
              />
            ))}
          </div>

          {/* Version stamp */}
          <motion.span
            className="absolute bottom-6 right-8 text-[9px] font-mono text-white/10 tracking-wider"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5, duration: 1 }}
          >
            v1.0.0
          </motion.span>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
