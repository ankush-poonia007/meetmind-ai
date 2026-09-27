import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';

/**
 * PublicOnlyRoute — Reverse Route Guard for Login and Registration (Batch 4.7).
 *
 * Prevents authenticated users from unnecessarily revisiting login and registration routes.
 * Redirects authenticated users to their intended destination or the default Workspace dashboard.
 */
export function PublicOnlyRoute({ children }) {
  const { isAuthenticated, isInitializing } = useAuth();
  const location = useLocation();

  if (isInitializing) {
    return (
      <div className="auth-init-screen" role="status" aria-live="polite">
        <div className="auth-init-card">
          <div className="auth-init-spinner" aria-hidden="true" />
          <p className="auth-init-text">Verifying session...</p>
        </div>
      </div>
    );
  }

  if (isAuthenticated) {
    const rawTarget =
      location.state?.from?.pathname ||
      (location.state?.from ? String(location.state.from) : '/workspace/dashboard');

    // Prevent open redirect vulnerabilities
    const safeTarget =
      rawTarget.startsWith('/') && !rawTarget.startsWith('//')
        ? rawTarget
        : '/workspace/dashboard';

    return <Navigate to={safeTarget} replace />;
  }

  return children;
}

export default PublicOnlyRoute;
