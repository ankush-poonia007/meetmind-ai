import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import {
  getMe,
  loginUser,
  registerAuthUser,
  logoutUser,
  formatApiError,
  setOnUnauthorizedCallback,
} from '../services/api';

const TOKEN_KEY = 'meetmind_token';
const USER_KEY = 'meetmind_user';
const LEGACY_USER_ID_KEY = 'meetmind_user_id';

/**
 * Helpers for safe localStorage operations.
 */
function getStoredItem(key) {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function setStoredItem(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch {
    // restricted or quota exceeded
  }
}

function removeStoredItem(key) {
  try {
    localStorage.removeItem(key);
  } catch {
    // ignore
  }
}

function getUserIdFromToken(token) {
  if (!token || typeof token !== 'string') return null;
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    const json = atob(base64);
    const parsed = JSON.parse(json);
    return parsed.sub || null;
  } catch {
    return null;
  }
}

export const AuthContext = createContext(null);

/**
 * AuthProvider — Centralized Authentication State Singleton (Batch 4.7 & 5.1 Correction).
 *
 * Responsibilities:
 * - Single source of truth for authentication across the entire application.
 * - Manages token, authenticated user identity, session initialization, and loading states.
 * - Validates persisted JWT on application startup via GET /api/v1/auth/me.
 * - Prevents stale localStorage user identity mismatches against active JWT token.
 * - Handles token expiration without clearing valid tokens on network failures.
 * - Synchronizes login, registration, and explicit logout across all components.
 */
export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => getStoredItem(TOKEN_KEY));
  const [user, setUser] = useState(() => {
    const storedToken = getStoredItem(TOKEN_KEY);
    const raw = getStoredItem(USER_KEY);
    if (!storedToken || !raw) {
      if (!storedToken) {
        removeStoredItem(USER_KEY);
        removeStoredItem(LEGACY_USER_ID_KEY);
      }
      return null;
    }
    try {
      const parsed = JSON.parse(raw);
      const tokenSub = getUserIdFromToken(storedToken);
      // If token has a subject UUID and cached user does not match it, purge stale user data
      if (tokenSub && parsed?.id && parsed.id !== tokenSub) {
        removeStoredItem(USER_KEY);
        removeStoredItem(LEGACY_USER_ID_KEY);
        return null;
      }
      return parsed;
    } catch {
      removeStoredItem(USER_KEY);
      removeStoredItem(LEGACY_USER_ID_KEY);
      return null;
    }
  });

  const [isInitializing, setIsInitializing] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [networkError, setNetworkError] = useState(false);

  /**
   * Validates the persisted JWT against the backend GET /api/v1/auth/me endpoint.
   */
  const validateSession = useCallback(async () => {
    const storedToken = getStoredItem(TOKEN_KEY);
    if (!storedToken) {
      setToken(null);
      setUser(null);
      removeStoredItem(USER_KEY);
      removeStoredItem(LEGACY_USER_ID_KEY);
      setIsInitializing(false);
      setNetworkError(false);
      return;
    }

    try {
      const verifiedUser = await getMe();
      setUser(verifiedUser);
      setToken(storedToken);
      setStoredItem(USER_KEY, JSON.stringify(verifiedUser));
      if (verifiedUser.id) {
        setStoredItem(LEGACY_USER_ID_KEY, verifiedUser.id);
      }
      setNetworkError(false);
      setError(null);
    } catch (err) {
      const formatted = formatApiError(err);
      if (formatted.status === 401 || formatted.status === 403 || formatted.status === 404) {
        // Genuinely expired, forbidden, or non-existent user account
        removeStoredItem(TOKEN_KEY);
        removeStoredItem(USER_KEY);
        removeStoredItem(LEGACY_USER_ID_KEY);
        setToken(null);
        setUser(null);
        setNetworkError(false);
      } else if (!formatted.status || formatted.status >= 500) {
        // Network failure or temporary backend unavailability:
        // DO NOT delete the persisted token. Keep state for retry.
        setNetworkError(true);
        setError('Unable to verify session due to a network error. Your session will be restored once connected.');
      }
    } finally {
      setIsInitializing(false);
    }
  }, []);

  // Run startup session validation on mount
  useEffect(() => {
    validateSession();
  }, [validateSession]);

  // Hook into Axios 401 response interceptor for runtime token expiration
  useEffect(() => {
    const handleUnauthorized = () => {
      removeStoredItem(TOKEN_KEY);
      removeStoredItem(USER_KEY);
      removeStoredItem(LEGACY_USER_ID_KEY);
      setToken(null);
      setUser(null);
    };

    setOnUnauthorizedCallback(handleUnauthorized);
    return () => setOnUnauthorizedCallback(null);
  }, []);

  /**
   * Authenticates user with credentials.
   *
   * @param {{ email: string, password: string }} credentials
   * @returns {Promise<object>} AuthTokenResponse
   */
  const login = useCallback(async (credentials) => {
    setLoading(true);
    setError(null);
    try {
      const data = await loginUser(credentials);
      setStoredItem(TOKEN_KEY, data.access_token);
      setStoredItem(USER_KEY, JSON.stringify(data.user));
      if (data.user?.id) {
        setStoredItem(LEGACY_USER_ID_KEY, data.user.id);
      }
      setToken(data.access_token);
      setUser(data.user);
      setNetworkError(false);
      return data;
    } catch (err) {
      const formatted = formatApiError(err);
      setError(formatted.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Registers a new user account with credentials.
   *
   * @param {object} registrationData
   * @returns {Promise<object>} AuthTokenResponse
   */
  const register = useCallback(async (registrationData) => {
    setLoading(true);
    setError(null);
    try {
      const data = await registerAuthUser(registrationData);
      setStoredItem(TOKEN_KEY, data.access_token);
      setStoredItem(USER_KEY, JSON.stringify(data.user));
      if (data.user?.id) {
        setStoredItem(LEGACY_USER_ID_KEY, data.user.id);
      }
      setToken(data.access_token);
      setUser(data.user);
      setNetworkError(false);
      return data;
    } catch (err) {
      const formatted = formatApiError(err);
      setError(formatted.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Performs explicit user logout.
   * Clears centralized state and purges persisted credentials.
   */
  const logout = useCallback(async () => {
    setLoading(true);
    try {
      await logoutUser();
    } catch {
      // Ignore network errors on logout
    } finally {
      removeStoredItem(TOKEN_KEY);
      removeStoredItem(USER_KEY);
      removeStoredItem(LEGACY_USER_ID_KEY);
      setToken(null);
      setUser(null);
      setError(null);
      setNetworkError(false);
      setLoading(false);
    }
  }, []);

  const value = {
    token,
    user,
    isAuthenticated: Boolean(token && user),
    isInitializing,
    loading,
    error,
    networkError,
    login,
    register,
    logout,
    validateSession,
    setError,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/**
 * useAuth hook consuming centralized AuthContext.
 */
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export default AuthContext;
