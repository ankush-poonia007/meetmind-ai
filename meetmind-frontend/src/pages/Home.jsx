import HeroSection from '../components/home/HeroSection';
import FeatureCards from '../components/home/FeatureCards';
import HowItWorks from '../components/home/HowItWorks';
import TechHighlight from '../components/home/TechHighlight';
import CTABanner from '../components/home/CTABanner';

/**
 * Home — Landing Page (Section 7)
 * Implements the complete 6-section structural layout in documented order:
 * 1. HeroSection — Full height intro with CTA buttons and spinning text mark
 * 2. Problem Statement — High-contrast dark section detailing the transcript pain point
 * 3. FeatureCards — 4 feature highlights with Lucide icons and fade-up animation hooks
 * 4. HowItWorks — 3 alternating chronological workflow steps
 * 5. TechHighlight — Dark section showcasing AI agent roster, RAG pipeline, and tracing
 * 6. CTABanner — Centered conversion banner with workspace navigation link
 */
function Home() {
  return (
    <div className="page-enter home-page">
      {/* ── Section 1: Hero ────────────────────────────────────────────── */}
      <HeroSection />

      {/* ── Section 2: Problem Statement ───────────────────────────────── */}
      <section
        className="problem-section"
        id="problem"
        aria-labelledby="problem-heading"
      >
        <div className="container">
          <div className="problem-content">
            <p className="text-label problem-label">The problem</p>
            <h2 className="text-h2 problem-heading" id="problem-heading">
              Meetings happen. <br />
              <em className="text-italic">Details get lost.</em>
            </h2>
            <div className="problem-body">
              <p className="text-body-lg">
                Every meeting produces tasks, decisions, and deadlines buried in
                long transcripts. Finding yours takes time you don't have.
              </p>
              <p className="text-body-lg">
                MeetMind reads the transcript, finds you in it, and gives you
                only what matters.
              </p>
            </div>
          </div>
        </div>
      </section>

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
