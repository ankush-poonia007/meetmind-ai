import { useState, useEffect, useCallback } from 'react';
import {
  getMeetings,
  getAllTasks,
  getAllHighlights,
  formatApiError,
} from '../services/api';
import { getRelativeDeadlineInfo, parseDate } from '../utils/formatDate';

/**
 * Checks if a task deadline is earlier than current time.
 * Handles missing, null, or invalid dates safely.
 *
 * @param {string | null | undefined} deadline
 * @returns {boolean}
 */
function isTaskExpired(deadline) {
  if (!deadline) return false;
  const d = parseDate(deadline);
  if (!d) return false;
  return d.getTime() < Date.now();
}

/**
 * useDashboardData — Central data integration hook for Dashboard (Batch 4.3).
 *
 * Concurrently fetches meetings, tasks, and highlights using Promise.allSettled.
 * Performs client-side metric calculations, highlight resolution, and deadline filtering.
 * Resilient against partial failures without masking errors with fake data.
 *
 * @param {string | null} userId - Valid user UUID
 * @returns {{
 *   loading: boolean,
 *   error: string | null,
 *   stats: {
 *     totalMeetings: number | null,
 *     totalTasks: number | null,
 *     activeTasks: number | null,
 *     completedTasks: number | null,
 *     expiredTasks: number | null,
 *   },
 *   highlights: Array<object>,
 *   deadlines: Array<object>,
 *   partialErrors: {
 *     meetings: string | null,
 *     tasks: string | null,
 *     highlights: string | null,
 *   },
 *   refetch: () => void,
 * }}
 */
export function useDashboardData(userId) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState({
    totalMeetings: null,
    totalTasks: null,
    activeTasks: null,
    completedTasks: null,
    expiredTasks: null,
  });
  const [highlights, setHighlights] = useState([]);
  const [deadlines, setDeadlines] = useState([]);
  const [partialErrors, setPartialErrors] = useState({
    meetings: null,
    tasks: null,
    highlights: null,
  });
  const [refetchTrigger, setRefetchTrigger] = useState(0);

  const refetch = useCallback(() => {
    setRefetchTrigger((c) => c + 1);
  }, []);

  useEffect(() => {
    if (!userId) {
      return;
    }

    let ignore = false;
    const controller = new AbortController();
    const { signal } = controller;

    async function loadData() {
      setLoading(true);
      setError(null);

      try {
        const results = await Promise.allSettled([
          getMeetings(userId, { signal }),
          getAllTasks(userId, { signal }),
          getAllHighlights(userId, { signal }),
        ]);

        if (ignore) return;

        const [meetingsResult, tasksResult, highlightsResult] = results;

        // Check if all requests were canceled
        const wasCanceled = results.some(
          (r) => r.status === 'rejected' && formatApiError(r.reason).isCanceled
        );
        if (wasCanceled) {
          return;
        }

        // Check if all 3 requests failed completely
        const allFailed = results.every((r) => r.status === 'rejected');
        if (allFailed) {
          const firstError = formatApiError(meetingsResult.reason);
          setError(`Failed to connect to backend: ${firstError.message}`);
          setLoading(false);
          return;
        }

        const newPartialErrors = {
          meetings: null,
          tasks: null,
          highlights: null,
        };

        // ── 1. Process Meetings ────────────────────────────────────────────
        let meetingsList = [];
        const meetingLookup = {};

        if (meetingsResult.status === 'fulfilled') {
          meetingsList = Array.isArray(meetingsResult.value) ? meetingsResult.value : [];
          meetingsList.forEach((m) => {
            if (m?.id && m?.title) {
              meetingLookup[m.id] = m.title;
            }
          });
        } else {
          newPartialErrors.meetings = formatApiError(meetingsResult.reason).message;
        }

        // ── 2. Process Tasks & Deadlines ───────────────────────────────────
        let tasksList = [];
        let calculatedStats = {
          totalMeetings: meetingsResult.status === 'fulfilled' ? meetingsList.length : null,
          totalTasks: null,
          activeTasks: null,
          completedTasks: null,
          expiredTasks: null,
        };
        let upcomingDeadlines = [];

        if (tasksResult.status === 'fulfilled') {
          tasksList = Array.isArray(tasksResult.value) ? tasksResult.value : [];

          let totalTasksCount = 0;
          let activeCount = 0;
          let completedCount = 0;
          let expiredCount = 0;

          tasksList.forEach((task) => {
            totalTasksCount++;
            if (task.status === 'complete') {
              completedCount++;
            } else if (task.status === 'pending') {
              if (isTaskExpired(task.deadline)) {
                expiredCount++;
              } else {
                activeCount++;
              }
            }

            // Upcoming deadlines criteria:
            // - pending tasks only (exclude completed)
            // - has valid deadline
            // - within next 3 days (daysDiff >= 0 && daysDiff <= 3)
            if (task.status === 'pending' && task.deadline) {
              const dateObj = parseDate(task.deadline);
              if (dateObj) {
                const { daysDiff } = getRelativeDeadlineInfo(task.deadline);
                if (daysDiff >= 0 && daysDiff <= 3) {
                  upcomingDeadlines.push({
                    id: task.id,
                    title: task.title,
                    dueDate: task.deadline,
                    priority: task.priority || 'medium',
                  });
                }
              }
            }
          });

          // Sort upcoming deadlines ascending chronologically
          upcomingDeadlines.sort((a, b) => {
            const dateA = parseDate(a.dueDate)?.getTime() || 0;
            const dateB = parseDate(b.dueDate)?.getTime() || 0;
            return dateA - dateB;
          });

          calculatedStats = {
            ...calculatedStats,
            totalTasks: totalTasksCount,
            activeTasks: activeCount,
            completedTasks: completedCount,
            expiredTasks: expiredCount,
          };
        } else {
          newPartialErrors.tasks = formatApiError(tasksResult.reason).message;
        }

        // ── 3. Process Highlights ──────────────────────────────────────────
        let mappedHighlights = [];

        if (highlightsResult.status === 'fulfilled') {
          const rawHighlightsData = highlightsResult.value;
          const rawList = Array.isArray(rawHighlightsData)
            ? rawHighlightsData
            : rawHighlightsData?.highlights || [];

          mappedHighlights = rawList.map((item) => ({
            id: item.id,
            meetingTitle: meetingLookup[item.meeting_id] || 'Meeting Highlight',
            text: item.content,
            date: item.created_at,
          }));

          // Sort highlights descending by date (most recent first)
          mappedHighlights.sort((a, b) => {
            const timeA = parseDate(a.date)?.getTime() || 0;
            const timeB = parseDate(b.date)?.getTime() || 0;
            return timeB - timeA;
          });
        } else {
          newPartialErrors.highlights = formatApiError(highlightsResult.reason).message;
        }

        if (!ignore) {
          setStats(calculatedStats);
          setDeadlines(upcomingDeadlines);
          setHighlights(mappedHighlights);
          setPartialErrors(newPartialErrors);
          setError(null);
        }
      } catch (err) {
        if (!ignore) {
          const formatted = formatApiError(err);
          if (!formatted.isCanceled) {
            setError(formatted.message || 'Failed to load dashboard data.');
          }
        }
      } finally {
        if (!ignore) {
          setLoading(false);
        }
      }
    }

    loadData();

    return () => {
      ignore = true;
      controller.abort();
    };
  }, [userId, refetchTrigger]);

  return {
    loading,
    error,
    stats,
    highlights,
    deadlines,
    partialErrors,
    refetch,
  };
}

export default useDashboardData;
