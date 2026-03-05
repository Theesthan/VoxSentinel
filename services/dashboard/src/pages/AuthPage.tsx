import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Link, useNavigate } from "react-router-dom";
import {
  Loader2,
  Mail,
  Lock,
  User,
  ArrowRight,
  Eye,
  EyeOff,
  AlertCircle,
  CheckCircle,
  ChevronRight,
} from "lucide-react";
import { useAuth } from "../lib/AuthContext";

/* ── Animation constants ── */
const EASE: [number, number, number, number] = [0.76, 0, 0.24, 1];

/* ── Ambient floating particles ── */
function AmbientParticles() {
  const [particles] = useState(() =>
    Array.from({ length: 35 }, (_, i) => ({
      id: i,
      x: Math.random() * 100,
      y: Math.random() * 100,
      size: 1 + Math.random() * 2,
      duration: 15 + Math.random() * 25,
      delay: Math.random() * 10,
      opacity: 0.03 + Math.random() * 0.06,
    })),
  );

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {particles.map((p) => (
        <motion.div
          key={p.id}
          className="absolute rounded-full bg-white"
          style={{
            width: p.size,
            height: p.size,
            left: `${p.x}%`,
            top: `${p.y}%`,
            opacity: p.opacity,
          }}
          animate={{
            y: [0, -80, 0],
            x: [0, 30 * (Math.random() - 0.5), 0],
            opacity: [p.opacity, p.opacity * 2, p.opacity],
          }}
          transition={{
            duration: p.duration,
            delay: p.delay,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />
      ))}
    </div>
  );
}

/* ── Audio waveform animation ── */
function WaveformStrip() {
  const [bars] = useState(() =>
    Array.from({ length: 60 }, (_, i) => ({
      id: i,
      h: 8 + Math.random() * 32,
      delay: Math.random() * 3,
      dur: 1.8 + Math.random() * 2.5,
    })),
  );

  return (
    <div className="flex items-end gap-[1.5px] h-10 w-full opacity-40">
      {bars.map((b) => (
        <motion.div
          key={b.id}
          className="flex-1 bg-white/10 rounded-t-[1px]"
          style={{ height: `${b.h}%` }}
          animate={{
            height: [`${b.h}%`, `${8 + Math.random() * 80}%`, `${b.h}%`],
          }}
          transition={{
            duration: b.dur,
            delay: b.delay,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />
      ))}
    </div>
  );
}

/* ── Scrolling data ticker ── */
function DataTicker() {
  const items = [
    "RTSP • HLS • DASH",
    "Deepgram Nova-2",
    "Aho-Corasick",
    "RapidFuzz",
    "PII Redaction",
    "SHA-256 Audit",
    "WebSocket Alerts",
    "DistilBERT NLP",
    "pyannote.audio",
    "Sub-300ms Latency",
    "Multi-Channel",
  ];

  return (
    <div className="overflow-hidden whitespace-nowrap">
      <motion.div
        className="inline-flex gap-8"
        animate={{ x: ["0%", "-50%"] }}
        transition={{ duration: 30, repeat: Infinity, ease: "linear" }}
      >
        {[...items, ...items].map((item, i) => (
          <span
            key={i}
            className="text-[9px] font-mono tracking-[0.25em] text-white/10 uppercase"
          >
            {item}
          </span>
        ))}
      </motion.div>
    </div>
  );
}

/* ── Floating data fragments (background) ── */
function FloatingFragments() {
  const fragments = [
    { text: 'keyword: "threat" — exact', x: "8%", y: "12%" },
    { text: "sentiment: 0.92 negative", x: "72%", y: "18%" },
    { text: "SPEAKER_02 identified", x: "15%", y: "78%" },
    { text: "latency: 187ms", x: "80%", y: "72%" },
    { text: "PII: ████████ redacted", x: "55%", y: "88%" },
    { text: "stream_04 active", x: "35%", y: "8%" },
  ];

  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden">
      {fragments.map((f, i) => (
        <motion.span
          key={i}
          className="absolute font-mono text-[8px] tracking-[0.15em] text-white/[0.04] whitespace-nowrap"
          style={{ left: f.x, top: f.y }}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.5 + i * 0.3, duration: 2 }}
        >
          {f.text}
        </motion.span>
      ))}
    </div>
  );
}

/* ── Grid overlay ── */
function GridOverlay() {
  return (
    <div
      className="absolute inset-0 pointer-events-none opacity-30"
      style={{
        backgroundImage:
          "linear-gradient(rgba(255,255,255,.015) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.015) 1px, transparent 1px)",
        backgroundSize: "80px 80px",
      }}
    />
  );
}

/* ── Glowing orbs behind the glass card ── */
function GlowOrbs() {
  return (
    <>
      <motion.div
        className="absolute -top-32 -left-32 w-64 h-64 bg-red-500/[0.06] rounded-full blur-[100px]"
        animate={{
          scale: [1, 1.2, 1],
          opacity: [0.06, 0.1, 0.06],
        }}
        transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute -bottom-24 -right-24 w-56 h-56 bg-blue-500/[0.04] rounded-full blur-[80px]"
        animate={{
          scale: [1, 1.15, 1],
          opacity: [0.04, 0.08, 0.04],
        }}
        transition={{ duration: 10, repeat: Infinity, ease: "easeInOut", delay: 2 }}
      />
      <motion.div
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-40 h-40 bg-white/[0.02] rounded-full blur-[60px]"
        animate={{
          scale: [1, 1.3, 1],
        }}
        transition={{ duration: 6, repeat: Infinity, ease: "easeInOut", delay: 1 }}
      />
    </>
  );
}

/* ── Animated input component ── */
function AuthInput({
  icon: Icon,
  type,
  placeholder,
  value,
  onChange,
  delay = 0,
}: {
  icon: React.ComponentType<{ className?: string }>;
  type: string;
  placeholder: string;
  value: string;
  onChange: (v: string) => void;
  delay?: number;
}) {
  const [focused, setFocused] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const isPassword = type === "password";

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: EASE, delay }}
      className="relative group"
    >
      <div
        className={`flex items-center gap-3 px-4 py-3.5 rounded-xl border transition-all duration-300 backdrop-blur-sm ${
          focused
            ? "border-red-500/40 bg-white/[0.06] shadow-[0_0_20px_rgba(239,68,68,0.08)]"
            : "border-white/[0.08] bg-white/[0.03] hover:border-white/15 hover:bg-white/[0.04]"
        }`}
      >
        <Icon
          className={`w-4 h-4 shrink-0 transition-colors duration-300 ${
            focused ? "text-red-400/70" : "text-white/20"
          }`}
        />
        <input
          type={isPassword && showPassword ? "text" : type}
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          className="flex-1 bg-transparent text-sm text-white placeholder-white/20 focus:outline-none tracking-wide"
          autoComplete={isPassword ? "current-password" : type === "email" ? "email" : "off"}
        />
        {isPassword && value && (
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="text-white/20 hover:text-white/40 transition-colors"
            tabIndex={-1}
          >
            {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        )}
      </div>
      {/* Subtle glow line at bottom when focused */}
      <motion.div
        className="absolute bottom-0 left-4 right-4 h-[1px] bg-gradient-to-r from-transparent via-red-500/30 to-transparent"
        initial={{ scaleX: 0 }}
        animate={{ scaleX: focused ? 1 : 0 }}
        transition={{ duration: 0.3 }}
      />
    </motion.div>
  );
}

/* ═══════════════════════════════════════════════
   Main Auth Page
   ═══════════════════════════════════════════════ */

type Mode = "login" | "signup" | "forgot";

export default function AuthPage() {
  const { loginEmail, signupEmail, loginGoogle, resetPassword, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const formRef = useRef<HTMLFormElement>(null);

  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  /* Redirect if already authenticated */
  useEffect(() => {
    if (isAuthenticated) navigate("/dashboard", { replace: true });
  }, [isAuthenticated, navigate]);

  const clearForm = () => {
    setEmail("");
    setPassword("");
    setConfirmPassword("");
    setDisplayName("");
    setError("");
    setSuccess("");
  };

  const switchMode = (newMode: Mode) => {
    clearForm();
    setMode(newMode);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    setLoading(true);

    try {
      if (mode === "forgot") {
        if (!email.trim()) throw new Error("Enter your email address");
        await resetPassword(email.trim());
        setSuccess("Password reset email sent. Check your inbox.");
        setLoading(false);
        return;
      }

      if (mode === "signup") {
        if (!displayName.trim()) throw new Error("Enter your name");
        if (password.length < 6) throw new Error("Password must be at least 6 characters");
        if (password !== confirmPassword) throw new Error("Passwords do not match");
        await signupEmail(email.trim(), password, displayName.trim());
      } else {
        await loginEmail(email.trim(), password);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Something went wrong";
      // Clean up Firebase error messages
      const cleaned = msg
        .replace("Firebase: ", "")
        .replace(/\(auth\/.*\)\.?/, "")
        .trim();
      setError(cleaned || msg);
    }
    setLoading(false);
  };

  const handleGoogle = async () => {
    setError("");
    setLoading(true);
    try {
      await loginGoogle();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Google sign-in failed";
      const cleaned = msg.replace("Firebase: ", "").replace(/\(auth\/.*\)\.?/, "").trim();
      setError(cleaned || msg);
    }
    setLoading(false);
  };

  /* ── Title & description per mode ── */
  const titles: Record<Mode, string> = {
    login: "Welcome Back",
    signup: "Create Account",
    forgot: "Reset Password",
  };
  const descriptions: Record<Mode, string> = {
    login: "Sign in to your VoxSentinel dashboard",
    signup: "Start monitoring in under 2 minutes",
    forgot: "We'll send a reset link to your email",
  };

  return (
    <div className="relative min-h-screen bg-black flex items-center justify-center overflow-hidden">
      {/* ── Background layers ── */}
      <GridOverlay />
      <AmbientParticles />
      <FloatingFragments />

      {/* ── Top bar ── */}
      <motion.div
        className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-8 py-4"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: EASE, delay: 0.2 }}
      >
        <Link to="/" className="group">
          <span className="text-[10px] font-mono tracking-[0.35em] text-white/30 uppercase group-hover:text-white/50 transition-colors">
            VoxSentinel
          </span>
        </Link>
        <span className="text-[9px] font-mono tracking-[0.2em] text-white/10 uppercase hidden sm:block">
          Auditory Intelligence Platform
        </span>
      </motion.div>

      {/* ── Main card ── */}
      <div className="relative z-10 w-full max-w-[420px] px-6">
        <GlowOrbs />

        <motion.div
          initial={{ opacity: 0, y: 30, scale: 0.97 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.8, ease: EASE, delay: 0.3 }}
          className="relative"
        >
          {/* Glass card */}
          <div className="relative rounded-2xl border border-white/[0.08] bg-white/[0.02] backdrop-blur-xl overflow-hidden">
            {/* Top gradient line */}
            <div className="h-[1px] bg-gradient-to-r from-transparent via-red-500/20 to-transparent" />

            {/* Inner content with scrollable area for signup */}
            <div className="p-6 sm:p-8 max-h-[calc(100vh-140px)] overflow-y-auto scrollbar-thin">
              {/* ── Header ── */}
              <AnimatePresence mode="wait">
                <motion.div
                  key={mode}
                  initial={{ opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 12 }}
                  transition={{ duration: 0.3, ease: EASE }}
                  className="mb-6"
                >
                  <h1 className="text-xl font-bold text-white tracking-tight mb-1.5">
                    {titles[mode]}
                  </h1>
                  <p className="text-[13px] text-white/30 tracking-wide">
                    {descriptions[mode]}
                  </p>
                </motion.div>
              </AnimatePresence>

              {/* ── Google sign-in (not on forgot page) ── */}
              {mode !== "forgot" && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, ease: EASE, delay: 0.1 }}
                  className="mb-6"
                >
                  <button
                    type="button"
                    onClick={handleGoogle}
                    disabled={loading}
                    className="w-full flex items-center justify-center gap-3 px-4 py-3.5 rounded-xl border border-white/[0.08] bg-white/[0.03] hover:bg-white/[0.06] hover:border-white/15 transition-all duration-300 group disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {/* Google G icon */}
                    <svg className="w-4 h-4" viewBox="0 0 24 24">
                      <path
                        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"
                        fill="#4285F4"
                      />
                      <path
                        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                        fill="#34A853"
                      />
                      <path
                        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                        fill="#FBBC05"
                      />
                      <path
                        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                        fill="#EA4335"
                      />
                    </svg>
                    <span className="text-[12px] font-mono tracking-[0.08em] text-white/50 group-hover:text-white/70 transition-colors uppercase">
                      Continue with Google
                    </span>
                  </button>
                </motion.div>
              )}

              {/* ── Divider (not on forgot page) ── */}
              {mode !== "forgot" && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.2 }}
                  className="flex items-center gap-4 mb-6"
                >
                  <div className="flex-1 h-[1px] bg-white/[0.06]" />
                  <span className="text-[9px] font-mono tracking-[0.25em] text-white/15 uppercase">
                    or
                  </span>
                  <div className="flex-1 h-[1px] bg-white/[0.06]" />
                </motion.div>
              )}

              {/* ── Form ── */}
              <form ref={formRef} onSubmit={handleSubmit} className="space-y-4">
                <AnimatePresence mode="wait">
                  <motion.div
                    key={mode}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                    transition={{ duration: 0.25 }}
                    className="space-y-4"
                  >
                    {/* Name field (signup only) */}
                    {mode === "signup" && (
                      <AuthInput
                        icon={User}
                        type="text"
                        placeholder="Full name"
                        value={displayName}
                        onChange={setDisplayName}
                        delay={0.05}
                      />
                    )}

                    {/* Email */}
                    <AuthInput
                      icon={Mail}
                      type="email"
                      placeholder="Email address"
                      value={email}
                      onChange={setEmail}
                      delay={mode === "signup" ? 0.1 : 0.05}
                    />

                    {/* Password (not on forgot page) */}
                    {mode !== "forgot" && (
                      <AuthInput
                        icon={Lock}
                        type="password"
                        placeholder="Password"
                        value={password}
                        onChange={setPassword}
                        delay={mode === "signup" ? 0.15 : 0.1}
                      />
                    )}

                    {/* Confirm password (signup only) */}
                    {mode === "signup" && (
                      <AuthInput
                        icon={Lock}
                        type="password"
                        placeholder="Confirm password"
                        value={confirmPassword}
                        onChange={setConfirmPassword}
                        delay={0.2}
                      />
                    )}
                  </motion.div>
                </AnimatePresence>

                {/* ── Forgot password link (login only) ── */}
                {mode === "login" && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.3 }}
                    className="flex justify-end"
                  >
                    <button
                      type="button"
                      onClick={() => switchMode("forgot")}
                      className="text-[11px] font-mono text-white/20 hover:text-red-400/60 transition-colors tracking-wide"
                    >
                      Forgot password?
                    </button>
                  </motion.div>
                )}

                {/* ── Error message ── */}
                <AnimatePresence>
                  {error && (
                    <motion.div
                      initial={{ opacity: 0, y: -4, height: 0 }}
                      animate={{ opacity: 1, y: 0, height: "auto" }}
                      exit={{ opacity: 0, y: -4, height: 0 }}
                      className="flex items-start gap-2 px-4 py-3 rounded-lg border border-red-500/20 bg-red-500/[0.06]"
                    >
                      <AlertCircle className="w-4 h-4 text-red-400/70 shrink-0 mt-0.5" />
                      <span className="text-[12px] text-red-300/80 leading-relaxed">
                        {error}
                      </span>
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* ── Success message ── */}
                <AnimatePresence>
                  {success && (
                    <motion.div
                      initial={{ opacity: 0, y: -4, height: 0 }}
                      animate={{ opacity: 1, y: 0, height: "auto" }}
                      exit={{ opacity: 0, y: -4, height: 0 }}
                      className="flex items-start gap-2 px-4 py-3 rounded-lg border border-green-500/20 bg-green-500/[0.06]"
                    >
                      <CheckCircle className="w-4 h-4 text-green-400/70 shrink-0 mt-0.5" />
                      <span className="text-[12px] text-green-300/80 leading-relaxed">
                        {success}
                      </span>
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* ── Submit button ── */}
                <motion.button
                  type="submit"
                  disabled={loading}
                  className="relative w-full group overflow-hidden rounded-xl border border-red-500/30 bg-red-600/20 hover:bg-red-600/30 py-3.5 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
                  whileTap={{ scale: 0.985 }}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: 0.35 }}
                >
                  {/* Shine effect */}
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/[0.04] to-transparent translate-x-[-200%] group-hover:translate-x-[200%] transition-transform duration-1000" />

                  <span className="relative z-10 flex items-center justify-center gap-2.5 text-[12px] font-mono tracking-[0.15em] uppercase text-white/80">
                    {loading ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span>
                          {mode === "login"
                            ? "Signing in…"
                            : mode === "signup"
                              ? "Creating account…"
                              : "Sending…"}
                        </span>
                      </>
                    ) : (
                      <>
                        <span>
                          {mode === "login"
                            ? "Sign In"
                            : mode === "signup"
                              ? "Create Account"
                              : "Send Reset Link"}
                        </span>
                        <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform duration-300" />
                      </>
                    )}
                  </span>
                </motion.button>
              </form>

              {/* ── Mode toggle ── */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.5 }}
                className="mt-8 pt-6 border-t border-white/[0.04]"
              >
                {mode === "forgot" ? (
                  <button
                    type="button"
                    onClick={() => switchMode("login")}
                    className="flex items-center gap-2 mx-auto text-[11px] font-mono text-white/25 hover:text-white/50 transition-colors tracking-wide group"
                  >
                    <ChevronRight className="w-3 h-3 rotate-180 group-hover:-translate-x-0.5 transition-transform" />
                    <span>Back to sign in</span>
                  </button>
                ) : (
                  <p className="text-center text-[12px] text-white/20 tracking-wide">
                    {mode === "login" ? "Don't have an account?" : "Already have an account?"}{" "}
                    <button
                      type="button"
                      onClick={() => switchMode(mode === "login" ? "signup" : "login")}
                      className="text-red-400/60 hover:text-red-400/90 transition-colors font-medium"
                    >
                      {mode === "login" ? "Sign up" : "Sign in"}
                    </button>
                  </p>
                )}
              </motion.div>
            </div>

            {/* Bottom gradient line */}
            <div className="h-[1px] bg-gradient-to-r from-transparent via-white/[0.04] to-transparent" />
          </div>

          {/* ── Corner decorations ── */}
          <div className="absolute -top-1 -left-1 w-3 h-[1px] bg-white/15" />
          <div className="absolute -top-1 -left-1 w-[1px] h-3 bg-white/15" />
          <div className="absolute -top-1 -right-1 w-3 h-[1px] bg-white/15" />
          <div className="absolute -top-1 -right-1 w-[1px] h-3 bg-white/15" />
          <div className="absolute -bottom-1 -left-1 w-3 h-[1px] bg-white/15" />
          <div className="absolute -bottom-1 -left-1 w-[1px] h-3 bg-white/15" />
          <div className="absolute -bottom-1 -right-1 w-3 h-[1px] bg-white/15" />
          <div className="absolute -bottom-1 -right-1 w-[1px] h-3 bg-white/15" />
        </motion.div>
      </div>

      {/* ── Waveform strip ── bottom decoration */}
      <motion.div
        className="absolute bottom-12 left-1/2 -translate-x-1/2 w-full max-w-[420px] px-6"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.8, duration: 1 }}
      >
        <WaveformStrip />
        <motion.div
          className="mt-3"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1, duration: 1 }}
        >
          <DataTicker />
        </motion.div>
      </motion.div>

      {/* ── Bottom bar ── */}
      <motion.div
        className="fixed bottom-0 left-0 right-0 flex items-center justify-center py-5"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.2, duration: 0.8 }}
      >
        <span className="text-[8px] font-mono tracking-[0.35em] text-white/10 uppercase">
          End-to-end encrypted &nbsp;·&nbsp; Sub-300ms latency &nbsp;·&nbsp; Multi-source ingestion
        </span>
      </motion.div>
    </div>
  );
}
