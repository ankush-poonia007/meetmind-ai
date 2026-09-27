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
 * Retrieves the full detail for a single meeting, including task and highlight counts.
 * Contract: GET /api/v1/meetings/{meeting_id}/detail -> MeetingDetailResponse
 *
 * @param {string} meetingId - Meeting UUID
 * @param {import('axios').AxiosRequestConfig} [config={}]
 * @returns {Promise<object>}
 */
export async function getMeetingDetail(meetingId, config = {}) {
  const response = await apiClient.get(`/meetings/${meetingId}/detail`, config);
  return response.data;
}

/**
 * Creates a new meeting with metadata and raw transcript content.
 *
 * Contract: POST /api/v1/meetings/?submitter_name={name}&submitter_role={role}
 * Body (JSON): MeetingCreate {
 *   user_id: string (UUID),
 *   meeting_date: string (YYYY-MM-DD),
 *   raw_transcript: string,
 *   title?: string,
 *   organization?: string,
 *   meeting_time?: string,
 *   input_format?: 'text' | 'txt' | 'pdf'
 * }
 *
 * @param {object} data - MeetingCreate payload object
 * @param {object} [paramsOrConfig={}] - Query parameters (submitter_name, submitter_role) or Axios config
 * @param {import('axios').AxiosRequestConfig} [extraConfig={}]
 * @returns {Promise<object>} MeetingResponse
 */
export async function createMeeting(data, paramsOrConfig = {}, extraConfig = {}) {
  let params = {};
  let config = {};

  if (paramsOrConfig.submitter_name || paramsOrConfig.submitter_role || paramsOrConfig.params) {
    params = paramsOrConfig.params || {
      ...(paramsOrConfig.submitter_name ? { submitter_name: paramsOrConfig.submitter_name } : {}),
      ...(paramsOrConfig.submitter_role ? { submitter_role: paramsOrConfig.submitter_role } : {}),
    };
    config = extraConfig;
  } else if (paramsOrConfig.headers || paramsOrConfig.signal) {
    config = paramsOrConfig;
  } else {
    params = paramsOrConfig;
    config = extraConfig;
  }

  const response = await apiClient.post('/meetings/', data, {
    ...config,
    params: { ...params, ...(config.params || {}) },
  });
  return response.data;
}

/**
 * Retrieves all tasks for a user within a specific meeting.
 * Contract: GET /api/v1/tasks/{user_id}/meeting/{meeting_id} -> list[TaskResponse]
 *
 * @param {string} userId - User UUID
 * @param {string} meetingId - Meeting UUID
 * @param {import('axios').AxiosRequestConfig} [config={}]
 * @returns {Promise<Array<object>>}
 */
export async function getMeetingTasks(userId, meetingId, config = {}) {
  const response = await apiClient.get(`/tasks/${userId}/meeting/${meetingId}`, config);
  return response.data;
}

/**
 * Updates the status of a single task.
 * Contract: PUT /api/v1/tasks/{task_id}/status -> TaskResponse
 *
 * @param {string} taskId - Task UUID
 * @param {'pending' | 'complete'} status - New status value
 * @param {import('axios').AxiosRequestConfig} [config={}]
 * @returns {Promise<object>}
 */
export async function updateTaskStatus(taskId, status, config = {}) {
  const response = await apiClient.put(`/tasks/${taskId}/status`, { status }, config);
  return response.data;
}

/**
 * Fetches filtered tasks for a user.
 * Contract: GET /api/v1/tasks/{user_id}/filter -> list[TaskResponse]
 *
 * @param {string} userId - User UUID
 * @param {object} params - Filter query parameters (meeting_id, status, priority, role, deadline_start, deadline_end)
 * @param {import('axios').AxiosRequestConfig} [config={}]
 * @returns {Promise<Array<object>>}
 */
export async function filterTasks(userId, params = {}, config = {}) {
  const response = await apiClient.get(`/tasks/${userId}/filter`, { ...config, params });
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

/**
 * Submits a question to the meeting-scoped Q&A pipeline.
 * Contract: POST /api/v1/chat/{meeting_id}/message -> ChatResponse
 *
 * @param {string} meetingId - Meeting UUID
 * @param {{ question: string, user_id: string }} data
 * @param {import('axios').AxiosRequestConfig} [config={}]
 * @returns {Promise<{ meeting_id: string, answer: string, sources: Array<{ speaker?: string, timestamp?: string, excerpt: string }>, confidence: 'high' | 'medium' | 'low' }>}
 */
export async function sendMessage(meetingId, data, config = {}) {
  const response = await apiClient.post(`/chat/${meetingId}/message`, data, config);
  return response.data;
}

/**
 * Retrieves chronological conversation history for a specific meeting.
 * Contract: GET /api/v1/chat/{meeting_id}/history -> ChatHistoryResponse
 *
 * @param {string} meetingId - Meeting UUID
 * @param {import('axios').AxiosRequestConfig} [config={}]
 * @returns {Promise<{ meeting_id: string, messages: Array<{ id: string, meeting_id: string, user_id: string, role: 'user' | 'assistant', content: string, created_at: string }> }>}
 */
export async function getChatHistory(meetingId, config = {}) {
  const response = await apiClient.get(`/chat/${meetingId}/history`, config);
  return response.data;
}

/**
 * Deletes all conversation messages for a specific meeting.
 * Contract: DELETE /api/v1/chat/{meeting_id}/history -> 204 No Content
 *
 * @param {string} meetingId - Meeting UUID
 * @param {import('axios').AxiosRequestConfig} [config={}]
 * @returns {Promise<void>}
 */
export async function clearChatHistory(meetingId, config = {}) {
  const response = await apiClient.delete(`/chat/${meetingId}/history`, config);
  return response.data;
}

/**
 * Triggers multi-agent extraction pipeline on meeting transcript.
 * Contract: POST /api/v1/extraction/{meeting_id}/run -> ExtractionPreviewResponse
 * Note: person_name is forwarded in payload for explicit identity extraction.
 *
 * @param {string} meetingId - Meeting UUID
 * @param {{ user_id: string, meeting_id?: string, person_name?: string }} data
 * @param {import('axios').AxiosRequestConfig} [config={}]
 * @returns {Promise<{ meeting_id: string, tasks: Array<object>, highlights: Array<object>, task_count: number, highlight_count: number, extraction_complete: boolean }>}
 */
export async function runExtraction(meetingId, data, config = {}) {
  const payload = {
    meeting_id: meetingId,
    user_id: data.user_id,
    ...(data.person_name ? { person_name: data.person_name } : {}),
  };
  const response = await apiClient.post(`/extraction/${meetingId}/run`, payload, config);
  return response.data;
}

/**
 * Retrieves extracted action items and highlights awaiting human-in-the-loop confirmation.
 * Contract: GET /api/v1/extraction/{meeting_id}/preview?user_id={user_id} -> ExtractionPreviewResponse
 *
 * @param {string} meetingId - Meeting UUID
 * @param {string} userId - User UUID
 * @param {import('axios').AxiosRequestConfig} [config={}]
 * @returns {Promise<{ meeting_id: string, tasks: Array<object>, highlights: Array<object>, task_count: number, highlight_count: number, extraction_complete: boolean }>}
 */
export async function getExtractionPreview(meetingId, userId, config = {}) {
  const response = await apiClient.get(`/extraction/${meetingId}/preview`, {
    ...config,
    params: { user_id: userId, ...(config.params || {}) },
  });
  return response.data;
}

/**
 * Processes human-in-the-loop confirmation decision (yes, no, or partial) and persists approved items.
 * Contract: POST /api/v1/extraction/{meeting_id}/confirm -> ExtractionResult
 * Note: includes modified_tasks payload to support edited task descriptions and deadlines.
 *
 * @param {string} meetingId - Meeting UUID
 * @param {{ user_id: string, meeting_id?: string, user_confirmation: 'yes' | 'no' | 'partial', confirmed_task_ids?: Array<string>, modified_tasks?: Array<object> }} data
 * @param {import('axios').AxiosRequestConfig} [config={}]
 * @returns {Promise<{ meeting_id: string, saved_tasks: number, discarded_tasks: number, saved_highlights: number, confirmation_complete: boolean, dashboard_ready: boolean }>}
 */
export async function confirmExtraction(meetingId, data, config = {}) {
  const payload = {
    meeting_id: meetingId,
    user_id: data.user_id,
    user_confirmation: data.user_confirmation,
    ...(data.confirmed_task_ids ? { confirmed_task_ids: data.confirmed_task_ids } : {}),
    ...(data.modified_tasks ? { modified_tasks: data.modified_tasks } : {}),
  };
  const response = await apiClient.post(`/extraction/${meetingId}/confirm`, payload, config);
  return response.data;
}

/**
 * Retrieves highlights for a specific meeting, scoped to the specified user.
 * Contract: GET /api/v1/highlights/{user_id}/meeting/{meeting_id} -> HighlightListResponse
 *
 * @param {string} userId - User UUID
 * @param {string} meetingId - Meeting UUID
 * @param {import('axios').AxiosRequestConfig} [config={}]
 * @returns {Promise<{ user_id: string, meeting_id: string | null, highlights: Array<object> }>}
 */
export async function getMeetingHighlights(userId, meetingId, config = {}) {
  const response = await apiClient.get(`/highlights/${userId}/meeting/${meetingId}`, config);
  return response.data;
}

export default apiClient;
