import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";

const EASE_OUT_EXPO: [number, number, number, number] = [0.16, 1, 0.3, 1];

const steps = ["Initializing...", "Connecting RTSP Streams...", "Access Granted."];

export default function Preloader({ onComplete }: { onComplete: () => void }) {
  const [currentStep, setCurrentStep] = useState(0);
  const [isExiting, setIsExiting] = useState(false);

  const handleComplete = useCallback(() => {
    setIsExiting(true);
    setTimeout(onComplete, 800);
  }, [onComplete]);

  useEffect(() => {
    const timers = [
      setTimeout(() => setCurrentStep(1), 1000),
      setTimeout(() => setCurrentStep(2), 2200),
      setTimeout(() => handleComplete(), 3400),
    ];
    return () => timers.forEach(clearTimeout);
  }, [handleComplete]);

  return (
    <AnimatePresence>
      {!isExiting && (
        <motion.div
          className="fixed inset-0 z-[100] bg-black flex flex-col items-center justify-center"
          exit={{ opacity: 0 }}
          transition={{ duration: 0.8, ease: EASE_OUT_EXPO }}
        >
          {/* Progress line at top */}
          <motion.div
            className="absolute top-0 left-0 h-[1px] bg-white/30"
            initial={{ width: "0%" }}
            animate={{
              width: `${((currentStep + 1) / steps.length) * 100}%`,
            }}
            transition={{ duration: 0.8, ease: EASE_OUT_EXPO }}
          />

          {/* Ambient pulse behind text */}
          <motion.div
            className="absolute w-64 h-64 rounded-full bg-white/[0.02] blur-3xl"
            animate={{ scale: [1, 1.3, 1], opacity: [0.3, 0.5, 0.3] }}
            transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
          />

          {/* Step text */}
          <div className="relative h-6 flex items-center justify-center">
            <AnimatePresence mode="wait">
              <motion.p
                key={currentStep}
                className="font-mono text-[11px] tracking-[0.3em] uppercase text-white/50"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.4, ease: EASE_OUT_EXPO }}
              >
                {steps[currentStep]}
              </motion.p>
            </AnimatePresence>
          </div>

          {/* Step indicators */}
          <div className="absolute bottom-12 flex gap-2">
            {steps.map((_, i) => (
              <motion.div
                key={i}
                className="w-8 h-[1px]"
                animate={{
                  backgroundColor:
                    i <= currentStep
                      ? "rgba(255,255,255,0.4)"
                      : "rgba(255,255,255,0.08)",
                }}
                transition={{ duration: 0.4 }}
              />
            ))}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
