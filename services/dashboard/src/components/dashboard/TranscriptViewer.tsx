import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface TranscriptLine {
  id: string;
  speaker: string;
  text: string;
  timestamp: string;
  sentiment: "positive" | "neutral" | "negative";
  highlight?: string;
}

const MOCK_TRANSCRIPT: TranscriptLine[] = [
  {
    id: "1",
    speaker: "SPEAKER_00",
    text: "Good morning, I'd like to check on my account balance.",
    timestamp: "10:03:14",
    sentiment: "neutral",
  },
  {
    id: "2",
    speaker: "SPEAKER_01",
    text: "Of course, let me pull that up for you. Can I have your [ACCOUNT_ID]?",
    timestamp: "10:03:18",
    sentiment: "positive",
  },
  {
    id: "3",
    speaker: "SPEAKER_00",
    text: "Yes, it's [ACCOUNT_ID]. I've been having issues with the transfer.",
    timestamp: "10:03:24",
    sentiment: "neutral",
  },
  {
    id: "4",
    speaker: "SPEAKER_01",
    text: "I see the pending transfer. It looks like there was a hold placed on it.",
    timestamp: "10:03:31",
    sentiment: "neutral",
  },
  {
    id: "5",
    speaker: "SPEAKER_00",
    text: "This is very frustrating, I've been waiting for days and nobody can give me an answer.",
    timestamp: "10:03:38",
    sentiment: "negative",
    highlight: "frustrating",
  },
  {
    id: "6",
    speaker: "SPEAKER_01",
    text: "I completely understand your frustration. Let me escalate this to our transfers team right now.",
    timestamp: "10:03:45",
    sentiment: "positive",
  },
  {
    id: "7",
    speaker: "SPEAKER_00",
    text: "I need this resolved today. I have payments due and this is unacceptable.",
    timestamp: "10:03:52",
    sentiment: "negative",
    highlight: "unacceptable",
  },
];

const speakerColors: Record<string, string> = {
  SPEAKER_00: "text-blue-400/70",
  SPEAKER_01: "text-emerald-400/70",
};

const sentimentDot: Record<string, string> = {
  positive: "bg-emerald-500",
  neutral: "bg-white/15",
  negative: "bg-red-500",
};

export default function TranscriptViewer() {
  const [lines, setLines] = useState<TranscriptLine[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Simulate streaming transcript lines
  useEffect(() => {
    const timers = MOCK_TRANSCRIPT.map((line, i) =>
      setTimeout(() => {
        setLines((prev) => [...prev, line]);
      }, i * 900),
    );
    return () => timers.forEach(clearTimeout);
  }, []);

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [lines]);

  /**
   * Render text with keyword highlights.
   */
  function renderText(text: string, highlight?: string) {
    if (!highlight) return text;

    const parts = text.split(new RegExp(`(${highlight})`, "gi"));
    return parts.map((part, i) =>
      part.toLowerCase() === highlight.toLowerCase() ? (
        <mark
          key={i}
          className="bg-red-500/15 text-red-400 px-0.5 rounded-sm"
        >
          {part}
        </mark>
      ) : (
        part
      ),
    );
  }

  return (
    <div className="border border-white/[0.08] bg-white/[0.01] h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.06]">
        <div className="flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
          <h2 className="text-xs font-medium tracking-tight">
            Live Transcript
          </h2>
        </div>
        <span className="text-[9px] text-white/20 tracking-wider font-mono">
          LOBBY CAMERA 1
        </span>
      </div>

      {/* Transcript lines */}
      <div ref={scrollRef} className="flex-1 overflow-auto p-4 space-y-3">
        <AnimatePresence>
          {lines.map((line) => (
            <motion.div
              key={line.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className="flex gap-3"
            >
              {/* Sentiment dot */}
              <div className="flex flex-col items-center shrink-0 pt-1.5">
                <div
                  className={`w-1 h-1 rounded-full ${sentimentDot[line.sentiment]}`}
                />
              </div>

              {/* Content */}
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span
                    className={`text-[9px] font-mono tracking-wider ${
                      speakerColors[line.speaker] || "text-white/30"
                    }`}
                  >
                    {line.speaker}
                  </span>
                  <span className="text-[9px] text-white/15 font-mono">
                    {line.timestamp}
                  </span>
                </div>
                <p className="mt-0.5 text-[12px] text-white/60 leading-relaxed">
                  {renderText(line.text, line.highlight)}
                </p>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Typing indicator */}
        {lines.length < MOCK_TRANSCRIPT.length && (
          <motion.div
            className="flex items-center gap-1 pt-2"
            animate={{ opacity: [0.3, 0.7, 0.3] }}
            transition={{ duration: 1.5, repeat: Infinity }}
          >
            <div className="w-1 h-1 rounded-full bg-white/20" />
            <div className="w-1 h-1 rounded-full bg-white/20" />
            <div className="w-1 h-1 rounded-full bg-white/20" />
          </motion.div>
        )}
      </div>
    </div>
  );
}
