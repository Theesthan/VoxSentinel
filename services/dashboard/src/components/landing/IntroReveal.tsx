import { useRef } from "react";
import { motion, useScroll, useTransform, type MotionValue } from "framer-motion";

const paragraphs = [
  "There are threats in the world that exist only in sound — not in logs, not in dashboards, not in any system designed around text.",
  "Most platforms operate on delayed, batch transcripts. Hours after the words were spoken. Hours after the signal mattered.",
  "VoxSentinel operates on the waveform in real time. Every syllable captured, classified, and acted upon before an operator could manually react.",
  "This is not transcription. This is auditory intelligence — engineered for the threats that hide in plain hearing.",
];

/**
 * Individual word whose opacity is driven by a scroll-linked MotionValue.
 * As the user scrolls, each word brightens from ghosted to full white.
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
  const opacity = useTransform(progress, range, [0.08, 1]);
  const y = useTransform(progress, range, [4, 0]);

  return (
    <motion.span
      className="inline-block mr-[0.32em] will-change-[opacity,transform]"
      style={{ opacity, y }}
    >
      {children}
    </motion.span>
  );
}

/**
 * One paragraph block with its own scroll range, turning words from
 * near-invisible to full opacity as they enter the viewport center.
 */
function RevealParagraph({
  text,
  index,
  totalCount,
}: {
  text: string;
  index: number;
  totalCount: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start 0.85", "start 0.25"],
  });

  const words = text.split(" ");
  // Slight y-transform on the whole block for parallax feel
  const blockY = useTransform(scrollYProgress, [0, 1], [30, 0]);

  return (
    <motion.div ref={ref} style={{ y: blockY }}>
      {/* Paragraph number */}
      <span className="block mb-4 text-[9px] font-mono tracking-[0.4em] text-white/10 uppercase">
        {String(index + 1).padStart(2, "0")} / {String(totalCount).padStart(2, "0")}
      </span>
      <p className="text-[clamp(1.4rem,3vw,3rem)] font-medium leading-[1.4] tracking-[-0.015em]">
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
    </motion.div>
  );
}

export default function IntroReveal() {
  return (
    <section className="relative py-40 md:py-56">
      {/* Vertical accent line */}
      <div className="absolute left-8 md:left-16 top-0 bottom-0 w-[1px] bg-white/[0.04]" />

      <div className="max-w-[56rem] mx-auto px-8 md:px-16 lg:px-24 space-y-40 md:space-y-56">
        {paragraphs.map((text, i) => (
          <RevealParagraph
            key={i}
            text={text}
            index={i}
            totalCount={paragraphs.length}
          />
        ))}
      </div>
    </section>
  );
}
