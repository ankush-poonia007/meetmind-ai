import { Link } from 'react-router-dom';
import SpinningText from './SpinningText';

/**
 * HeroSection — Home Page Section 1 (Section 7)
 * Full viewport height, cream background, centered content container.
 * Features:
 * - Small caps category label
 * - Display serif headline with italic emphasis
 * - Intro subtext paragraph
 * - Dual CTA links to Workspace and Documentation
 * - Circular spinning text SVG badge with MeetMind mark
 */
function HeroSection() {
  return (
    <section className="hero-section" id="hero" aria-labelledby="hero-heading">
      <div className="container hero-container">
        <div className="hero-content-wrapper">
          <div className="hero-text-block">
            <p className="text-label hero-label">AI Meeting Assistant</p>
            <h1 className="text-display hero-title" id="hero-heading">
              Your meetings, <em className="text-italic">understood.</em>
            </h1>
            <p className="text-body-lg hero-subtext">
              MeetMind ingests your meeting transcripts, identifies your role,
              extracts your tasks, and answers your questions — automatically.
            </p>
            <div className="hero-cta-group">
              <Link to="/workspace/dashboard" className="btn-primary">
                Open Workspace
              </Link>
              <Link to="/docs" className="btn-secondary">
                Read the Docs
              </Link>
            </div>
          </div>

          <div className="hero-visual-block">
            <SpinningText />
          </div>
        </div>
      </div>
    </section>
  );
}

export default HeroSection;
