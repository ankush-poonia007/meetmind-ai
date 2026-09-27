import { useAuth } from './useAuth';

/**
 * useUser — Thin compatibility wrapper deriving user identity from centralized authentication state (Batch 4.7).
 *
 * Requirements:
 * - Derives user and userId strictly from centralized authentication state.
 * - Does not maintain independent authentication state.
 * - Zero fallback to hardcoded UUIDs or VITE_DEV_USER_ID.
 * - Preserves { userId, user, loading, error, retrySession } contract for consumers.
 */
export function useUser() {
  const { user, isInitializing, error, validateSession } = useAuth();

  return {
    userId: isInitializing ? null : (user?.id || null),
    user: isInitializing ? null : (user || null),
    loading: isInitializing,
    error: error || null,
    retrySession: validateSession,
  };
}

export default useUser;
