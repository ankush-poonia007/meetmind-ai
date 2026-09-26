import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';

/**
 * ProtectedRoute — Route Guard for Workspace & Authenticated Pages (Batch 4.7).
 *
 * Requirements:
 * - Awaits session initialization before evaluating authentication status.
 * - Prevents protected content from briefly rendering before verification.
 * - Preserves the user's intended destination in navigation state.
 * - Redirects unauthenticated users to the dedicated /login route.
 */
export function ProtectedRoute({ children }) {
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

  if (!isAuthenticated) {
    // Preserve requested location and query parameters
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
}

export default ProtectedRoute;
