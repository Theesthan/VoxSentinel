import { useState, useCallback } from "react";
import { AnimatePresence } from "framer-motion";
import Preloader from "@/components/landing/Preloader";
import Hero from "@/components/landing/Hero";
import IntroReveal from "@/components/landing/IntroReveal";
import StatsBanner from "@/components/landing/StatsBanner";
import StickyPipeline from "@/components/landing/StickyPipeline";
import FeaturesGrid from "@/components/landing/FeaturesGrid";
import Footer from "@/components/landing/Footer";

export default function Landing() {
  const [loading, setLoading] = useState(true);

  const handlePreloaderComplete = useCallback(() => {
    setLoading(false);
  }, []);

  return (
    <>
      <AnimatePresence>{loading && <Preloader onComplete={handlePreloaderComplete} />}</AnimatePresence>

      <main className="bg-black">
        <Hero />
        <IntroReveal />
        <StatsBanner />
        <StickyPipeline />
        <FeaturesGrid />
        <Footer />
      </main>
    </>
  );
}
