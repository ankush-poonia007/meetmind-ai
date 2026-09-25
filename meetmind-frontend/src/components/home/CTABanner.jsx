import { Link } from 'react-router-dom';

/**
 * CTABanner — Home Page Section 6 (Section 7)
 * Final conversion banner on cream background.
 * Features centered H2 headline and primary action button routing to the workspace.
 */
function CTABanner() {
  return (
    <section className="cta-banner-section" id="cta-banner" aria-labelledby="cta-banner-heading">
      <div className="container">
        <div className="cta-banner-container">
          <h2 className="text-h2 cta-banner-heading" id="cta-banner-heading">
            Ready to understand your meetings?
          </h2>
          <Link to="/workspace/dashboard" className="btn-primary">
            Get Started
          </Link>
        </div>
      </div>
    </section>
  );
}

export default CTABanner;
