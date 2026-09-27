import HeroSection from '../components/home/HeroSection';
import ProblemSection from '../components/home/ProblemSection';
import FeatureCards from '../components/home/FeatureCards';
import HowItWorks from '../components/home/HowItWorks';
import TechHighlight from '../components/home/TechHighlight';
import CTABanner from '../components/home/CTABanner';

/**
 * Home — Landing Page (Section 7)
 * Composes the complete 6-section structural layout in documented order:
 * 1. HeroSection — Full height intro with CTA buttons and spinning text mark
 * 2. ProblemSection — Distinct pale blue section detailing the transcript pain point
 * 3. FeatureCards — 4 feature highlights with Lucide icons and hover animations
 * 4. HowItWorks — 3 alternating chronological workflow steps
 * 5. TechHighlight — AI engineering depth showcasing agent roster, RAG pipeline, and tracing
 * 6. CTABanner — Centered conversion banner with workspace navigation link
 */
function Home() {
  return (
    <div className="page-enter home-page">
      {/* ── Section 1: Hero ────────────────────────────────────────────── */}
      <HeroSection />

      {/* ── Section 2: Problem Statement ───────────────────────────────── */}
      <ProblemSection />

      {/* ── Section 3: Feature Highlights ──────────────────────────────── */}
      <FeatureCards />

      {/* ── Section 4: How It Works ────────────────────────────────────── */}
      <HowItWorks />

      {/* ── Section 5: Tech Highlight ──────────────────────────────────── */}
      <TechHighlight />

      {/* ── Section 6: CTA Banner ──────────────────────────────────────── */}
      <CTABanner />
    </div>
  );
}

export default Home;
