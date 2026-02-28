import { useRef } from "react";
import { useScroll, useTransform, type MotionValue } from "framer-motion";

interface UseScrollRevealOptions {
  offset?: [string, string];
}

/**
 * Hook for scroll-linked reveal animations.
 * Returns a ref to attach to a container and the scroll progress MotionValue.
 */
export function useScrollReveal(options?: UseScrollRevealOptions) {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    offset: (options?.offset as any) || ["start end", "end start"],
  });

  return { ref, scrollYProgress };
}

/**
 * Transform scroll progress into a parallax offset.
 */
export function useParallax(value: MotionValue<number>, distance: number) {
  return useTransform(value, [0, 1], [-distance, distance]);
}
