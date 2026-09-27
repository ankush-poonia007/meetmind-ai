import { useAuth } from '../context/AuthContext';

/**
 * useAuth — Compatibility hook re-exporting centralized authentication state (Batch 4.7).
 *
 * Ensures all existing consumers throughout the application share a single,
 * synchronized source of truth for user identity, JWT token, and authentication status.
 */
export { useAuth };
export default useAuth;
