import { useState, useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";
import Preloader from "../components/landing/Preloader";
import Hero from "../components/landing/Hero";
import IntroReveal from "../components/landing/IntroReveal";
import StatsBanner from "../components/landing/StatsBanner";
import StickyPipeline from "../components/landing/StickyPipeline";
import FeaturesGrid from "../components/landing/FeaturesGrid";
import Footer from "../components/landing/Footer";

export default function Landing() {
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Prevent scroll during preloader
    if (loading) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [loading]);

  return (
    <>
      <AnimatePresence mode="wait">
        {loading && <Preloader onComplete={() => setLoading(false)} />}
      </AnimatePresence>

      <motion.main
        className="bg-black min-h-screen"
        initial={{ opacity: 0 }}
        animate={{ opacity: loading ? 0 : 1 }}
        transition={{ duration: 0.8, delay: 0.1 }}
      >
        <Hero />
        <IntroReveal />
        <StatsBanner />
        <StickyPipeline />
        <FeaturesGrid />
        <Footer />
      </motion.main>
    </>
  );
}
