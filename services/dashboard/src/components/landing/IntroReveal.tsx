import { useRef } from "react";
import { motion, useScroll, useTransform, type MotionValue } from "framer-motion";

const paragraph =
  "There are threats in the world that can't be seen — only heard. Where others rely on delayed logs, we process live streams with unmatched precision. This is a gateway to complete auditory awareness. Not every system is built to handle it.";

/**
 * Individual word component whose opacity is driven by scroll progress.
 * As the user scrolls, words progressively brighten from dim ghosted text
 * to full white — creating the signature scroll-linked text reveal.
 */
function Word({
  children,
  progress,
  range,
}: {
  children: string;
  progress: MotionValue<number>;
  range: [number, number];
}) {
  const opacity = useTransform(progress, range, [0.1, 1]);

  return (
    <motion.span
      className="inline-block mr-[0.3em] will-change-[opacity]"
      style={{ opacity }}
    >
      {children}
    </motion.span>
  );
}

export default function IntroReveal() {
  const containerRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start 0.9", "start 0.15"],
  });

  const words = paragraph.split(" ");

  return (
    <section
      ref={containerRef}
      className="min-h-screen flex items-center px-8 md:px-16 lg:px-24 py-40"
    >
      <p className="text-[clamp(1.5rem,3.5vw,3.5rem)] font-medium leading-[1.35] tracking-[-0.02em] max-w-[70rem]">
        {words.map((word, i) => {
          const start = i / words.length;
          const end = start + 1 / words.length;
          return (
            <Word key={i} progress={scrollYProgress} range={[start, end]}>
              {word}
            </Word>
          );
        })}
      </p>
    </section>
  );
}
