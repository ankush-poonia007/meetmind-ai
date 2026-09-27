import { Link } from 'react-router-dom';

/**
 * NotFound — 404 Error Fallback Placeholder (Gate 2)
 * Rendered when navigation hits an unknown route.
 */
function NotFound() {
  return (
    <div className="page-enter">
      <section className="content-section">
        <div className="container">
          <p className="text-label">Error 404</p>
          <h1 className="text-h1">Page Not Found</h1>
          <p className="text-body-lg" style={{ marginTop: 'var(--space-md)' }}>
            The requested page does not exist.
          </p>
          <div style={{ marginTop: 'var(--space-lg)' }}>
            <Link to="/" className="btn-primary" style={{ display: 'inline-block' }}>
              Return to Home
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}

export default NotFound;
