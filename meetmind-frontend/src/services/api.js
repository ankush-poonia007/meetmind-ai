import axios from 'axios';

/**
 * MeetMind AI — Centralized API Client (Batch 4.3)
 * Provides centralized Axios instance with baseURL from environment variables,
 * consistent error formatting, and request cancellation support.
 */

const rawBaseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

// In browser development, if API base URL points to localhost:8000, route through Vite proxy (/api/v1)
// to prevent browser CORS rejection (FastAPI CORS only permits ports 8501 and 3000).
export const baseURL =
  typeof window !== 'undefined' && rawBaseURL.includes('localhost:8000')
    ? rawBaseURL.replace(/https?:\/\/localhost:8000/, '')
    : rawBaseURL;

export const apiClient = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 15000,
});

// Attach Bearer token to outgoing requests if authenticated
apiClient.interceptors.request.use((config) => {
  try {
    const token = localStorage.getItem('meetmind_token');
    if (token && !config.headers.Authorization) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  } catch {
    // localStorage unavailable or restricted
  }
  return config;
});

let onUnauthorizedCallback = null;

/**
 * Registers a callback invoked when a protected API request encounters HTTP 401 Unauthorized.
 *
 * @param {Function | null} cb
 */
export function setOnUnauthorizedCallback(cb) {
  onUnauthorizedCallback = cb;
}

// Intercept 401 Unauthorized responses to notify centralized auth state
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    const url = error?.config?.url || '';
    const isAuthEndpoint = url.includes('/auth/login') || url.includes('/auth/register');

    if (status === 401 && !isAuthEndpoint) {
      if (typeof onUnauthorizedCallback === 'function') {
        onUnauthorizedCallback();
      }
    }

    return Promise.reject(error);
  }
);

/**
 * Standardized API error formatter.
 * Extracts user-friendly error messages from Axios responses or network failures.
 *
 * @param {any} error
 * @returns {{ isCanceled: boolean, status: number | null, message: string }}
 */
export function formatApiError(error) {
  if (axios.isCancel(error) || error?.name === 'CanceledError' || error?.code === 'ERR_CANCELED') {
    return { isCanceled: true, status: null, message: 'Request was canceled.' };
  }

  const status = error?.response?.status || null;
  const data = error?.response?.data;
  let message = 'An unexpected network error occurred.';

  if (data?.message && typeof data.message === 'string') {
    message = data.message;
  } else if (data?.detail) {
    if (typeof data.detail === 'string') {
      message = data.detail;
    } else if (Array.isArray(data.detail)) {
      message = data.detail
        .map((err) => {
          if (err.loc && err.msg) {
            const field = err.loc[err.loc.length - 1];
            return `${field}: ${err.msg}`;
          }
          return err.msg || JSON.stringify(err);
        })
        .join(', ');
    } else {
      message = JSON.stringify(data.detail);
    }
  } else if (error?.message) {
    message = error.message;
  }

  return { isCanceled: false, status, message };
}

/**
 * Lists all meetings for a specific user.
 * Contract: GET /api/v1/meetings/{user_id} -> list[MeetingListItem]
 *
 * @param {string} userId - User UUID
 * @param {import('axios').AxiosRequestConfig} [config={}]
 * @returns {Promise<Array<object>>}
 */
export async function getMeetings(userId, config = {}) {
  const url = userId ? `/meetings/${userId}` : '/meetings';
  const response = await apiClient.get(url, config);
  return response.data;
}

/**
 * Retrieves all tasks assigned to a specific user.
 * Contract: GET /api/v1/tasks/{user_id} or GET /api/v1/tasks -> list[TaskResponse]
 *
 * @param {string} [userId] - User UUID (optional; derives from JWT principal if omitted)
 * @param {import('axios').AxiosRequestConfig} [config={}]
 * @returns {Promise<Array<object>>}
 */
export async function getAllTasks(userId, config = {}) {
  const url = userId ? `/tasks/${userId}` : '/tasks';
  const response = await apiClient.get(url, config);
  return response.data;
}

/**
 * Retrieves all highlights relevant to a user across all meetings.
 * Contract: GET /api/v1/highlights/{user_id} or GET /api/v1/highlights -> HighlightListResponse
 *
 * @param {string} [userId] - User UUID (optional; derives from JWT principal if omitted)
 * @param {import('axios').AxiosRequestConfig} [config={}]
 * @returns {Promise<{ user_id: string, meeting_id: string | null, highlights: Array<object> }>}
 */
export async function getAllHighlights(userId, config = {}) {
  const url = userId ? `/highlights/${userId}` : '/highlights';
  const response = await apiClient.get(url, config);
  return response.data;
}

/**
 * Retrieves a user profile by unique user identifier.
 * Contract: GET /api/v1/users/{user_id} -> UserResponse
 *
 * @param {string} userId - User UUID
 * @param {import('axios').AxiosRequestConfig} [config={}]
 * @returns {Promise<object>}
 */
export async function getUser(userId, config = {}) {
  const response = await apiClient.get(`/users/${userId}`, config);
  return response.data;
}

/**
 * Registers a new user.
 * Contract: POST /api/v1/users/register -> UserResponse
 *
 * @param {{ name: string, email: string }} data
 * @param {import('axios').AxiosRequestConfig} [config={}]
 * @returns {Promise<object>}
 */
export async function registerUser(data, config = {}) {
  const response = await apiClient.post('/users/register', data, config);
  return response.data;
}

/**
 * Authenticates user credentials via email and password.
 * Contract: POST /api/v1/auth/login -> AuthTokenResponse
 *
 * @param {{ email: string, password: string }} credentials
 * @param {import('axios').AxiosRequestConfig} [config={}]
 * @returns {Promise<{ access_token: string, token_type: string, expires_in: number, user: object }>}
 */
export async function loginUser(credentials, config = {}) {
  const response = await apiClient.post('/auth/login', credentials, config);
  return response.data;
}

/**
 * Registers a new user account with credentials.
 * Contract: POST /api/v1/auth/register -> AuthTokenResponse
 *
 * @param {{
 *   first_name: string,
 *   last_name: string,
 *   email: string,
 *   password: string,
 *   mobile_number?: string,
 *   confirm_password?: string
 * }} registrationData
 * @param {import('axios').AxiosRequestConfig} [config={}]
 * @returns {Promise<{ access_token: string, token_type: string, expires_in: number, user: object }>}
 */
export async function registerAuthUser(registrationData, config = {}) {
  const response = await apiClient.post('/auth/register', registrationData, config);
  return response.data;
}

/**
 * Retrieves authenticated user profile from access token.
 * Contract: GET /api/v1/auth/me -> UserResponse
 *
 * @param {import('axios').AxiosRequestConfig} [config={}]
 * @returns {Promise<object>}
 */
export async function getMe(config = {}) {
  const response = await apiClient.get('/auth/me', config);
  return response.data;
}

/**
 * Performs stateless logout acknowledgment.
 * Contract: POST /api/v1/auth/logout -> LogoutResponse
 *
 * @param {import('axios').AxiosRequestConfig} [config={}]
 * @returns {Promise<object>}
 */
export async function logoutUser(config = {}) {
  try {
    const response = await apiClient.post('/auth/logout', {}, config);
    return response.data;
  } finally {
    try {
      localStorage.removeItem('meetmind_token');
      localStorage.removeItem('meetmind_user');
    } catch {
      // localStorage restriction
    }
  }
}

export default apiClient;
