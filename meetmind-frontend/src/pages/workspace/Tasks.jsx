import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  CheckSquare,
  AlertTriangle,
  RotateCcw,
  Calendar,
  Filter,
  ArrowRight,
  Clock,
  CheckCircle,
  AlertCircle,
} from 'lucide-react';
import { useUser } from '../../hooks/useUser';
import { getAllTasks, getMeetings, updateTaskStatus, formatApiError } from '../../services/api';
import FilterBar from '../../components/workspace/FilterBar';
import TaskTable from '../../components/workspace/TaskTable';
import { parseDate } from '../../utils/formatDate';

/**
 * Checks whether a deadline timestamp is strictly earlier than current client time.
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
 * Priority rank map for sorting (High > Medium > Low).
 */
const PRIORITY_ORDER = {
  high: 3,
  medium: 2,
  low: 1,
};

const INITIAL_FILTERS = {
  meetingId: '',
  status: '',
  priority: '',
  role: '',
  deadlineFrom: '',
  deadlineTo: '',
};

/**
 * TaskTableSkeleton — Skeleton loader rows shown during data fetch.
 */
function TaskTableSkeleton() {
  return (
    <div className="task-table-wrapper" aria-hidden="true">
      <table className="task-table">
        <thead>
          <tr>
            <th scope="col">Task Title</th>
            <th scope="col">Meeting</th>
            <th scope="col">Priority</th>
            <th scope="col">Deadline</th>
            <th scope="col">Status</th>
            <th scope="col">Role</th>
            <th scope="col">Actions</th>
          </tr>
        </thead>
        <tbody>
          {[...Array(5)].map((_, i) => (
            <tr key={i} className="task-row-skeleton" style={{ animationDelay: `${i * 70}ms` }}>
              <td><div className="skeleton skeleton-task-title" /></td>
              <td><div className="skeleton skeleton-task-meeting" /></td>
              <td><div className="skeleton skeleton-task-priority" /></td>
              <td><div className="skeleton skeleton-task-deadline" /></td>
              <td><div className="skeleton skeleton-task-badge" /></td>
              <td><div className="skeleton skeleton-task-role" /></td>
              <td><div className="skeleton skeleton-task-action" /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/**
 * Tasks — Workspace Sub-View 3 (Section 8 Sub-View 3 / Batch 5.2)
 *
 * Route: /workspace/tasks
 *
 * Implements:
 *   - Header with metric summaries (Total, Active, Complete, Expired)
 *   - Horizontal, sticky Filter Bar (Meeting, Status, Priority, Role, Deadline range, Clear filters)
 *   - 7-Column Task Table with row hover, expandable descriptions, and inline status toggling
 *   - Optimistic status updates persisted via PUT /api/v1/tasks/{task_id}/status
 *   - Loading skeleton, error with retry, and empty states
 *
 * Uses real authenticated user identity and live FastAPI backend data.
 */
function Tasks() {
  const navigate = useNavigate();
  const { userId, user, loading: userLoading, error: userError, retrySession } = useUser();

  const [tasks, setTasks] = useState([]);
  const [meetings, setMeetings] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [updatingTaskId, setUpdatingTaskId] = useState(null);

  // Filters & Sorting state
  const [filters, setFilters] = useState(INITIAL_FILTERS);
  const [sortField, setSortField] = useState('deadline');
  const [sortDirection, setSortDirection] = useState('asc');
  const [refetchTrigger, setRefetchTrigger] = useState(0);

  const abortRef = useRef(null);

  /* ── Load user tasks and meetings concurrently ─────────────────────────── */
  useEffect(() => {
    if (userLoading || !userId) return;

    if (abortRef.current) abortRef.current.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    let ignore = false;
    setLoading(true);
    setError(null);
    setActionError(null);

    Promise.all([
      getAllTasks(userId, { signal: controller.signal }),
      getMeetings(userId, { signal: controller.signal }),
    ])
      .then(([tasksData, meetingsData]) => {
        if (ignore) return;
        setTasks(Array.isArray(tasksData) ? tasksData : []);
        setMeetings(Array.isArray(meetingsData) ? meetingsData : []);
        setError(null);
      })
      .catch((err) => {
        if (ignore) return;
        const formatted = formatApiError(err);
        if (!formatted.isCanceled) {
          setError(formatted.message || 'Failed to load tasks. Please try again.');
        }
      })
      .finally(() => {
        if (!ignore) setLoading(false);
      });

    return () => {
      ignore = true;
      controller.abort();
    };
  }, [userId, userLoading, refetchTrigger]);

  const refetch = useCallback(() => {
    setRefetchTrigger((c) => c + 1);
  }, []);

  /* ── Lookup maps for meetings and participant roles ────────────────────── */
  const meetingsMap = useMemo(() => {
    const map = {};
    meetings.forEach((m) => {
      if (m.id) map[m.id] = m;
    });
    return map;
  }, [meetings]);

  const rolesMap = useMemo(() => {
    const map = {};
    meetings.forEach((m) => {
      if (m.id) {
        map[m.id] = m.user_role || m.role || user?.role || 'Team Member';
      }
    });
    return map;
  }, [meetings, user]);

  /* ── Extract distinct roles across all tasks and meetings ─────────────── */
  const distinctRoles = useMemo(() => {
    const roleSet = new Set();
    if (user?.role) roleSet.add(user.role);
    meetings.forEach((m) => {
      if (m.user_role) roleSet.add(m.user_role);
      if (m.role) roleSet.add(m.role);
    });
    return Array.from(roleSet).filter(Boolean);
  }, [meetings, user]);

  /* ── Filter change handlers ────────────────────────────────────────────── */
  const handleFilterChange = useCallback((key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  }, []);

  const handleClearFilters = useCallback(() => {
    setFilters(INITIAL_FILTERS);
  }, []);

  const hasActiveFilters = useMemo(() => {
    return Boolean(
      filters.meetingId ||
      filters.status ||
      filters.priority ||
      filters.role ||
      filters.deadlineFrom ||
      filters.deadlineTo
    );
  }, [filters]);

  /* ── Filtered & Sorted Tasks ───────────────────────────────────────────── */
  const filteredTasks = useMemo(() => {
    return tasks.filter((t) => {
      // 1. Meeting filter
      if (filters.meetingId && t.meeting_id !== filters.meetingId) {
        return false;
      }

      // 2. Status filter
      if (filters.status) {
        const isComplete = t.status === 'complete';
        const isExpired = !isComplete && isTaskExpired(t.deadline);
        const isPending = t.status === 'pending' && !isExpired;

        if (filters.status === 'complete' && !isComplete) return false;
        if (filters.status === 'expired' && !isExpired) return false;
        if (filters.status === 'pending' && !isPending) return false;
      }

      // 3. Priority filter
      if (filters.priority) {
        const taskPriority = (t.priority || '').toLowerCase();
        if (taskPriority !== filters.priority.toLowerCase()) {
          return false;
        }
      }

      // 4. Role filter
      if (filters.role) {
        const taskRole = rolesMap[t.meeting_id] || user?.role;
        if (taskRole !== filters.role) {
          return false;
        }
      }

      // 5. Deadline From filter
      if (filters.deadlineFrom) {
        if (!t.deadline) return false;
        const taskDate = parseDate(t.deadline);
        const fromDate = parseDate(filters.deadlineFrom);
        if (!taskDate || !fromDate) return false;
        // Strip time component for date-only comparison
        taskDate.setHours(0, 0, 0, 0);
        fromDate.setHours(0, 0, 0, 0);
        if (taskDate.getTime() < fromDate.getTime()) return false;
      }

      // 6. Deadline To filter
      if (filters.deadlineTo) {
        if (!t.deadline) return false;
        const taskDate = parseDate(t.deadline);
        const toDate = parseDate(filters.deadlineTo);
        if (!taskDate || !toDate) return false;
        taskDate.setHours(0, 0, 0, 0);
        toDate.setHours(23, 59, 59, 999);
        if (taskDate.getTime() > toDate.getTime()) return false;
      }

      return true;
    });
  }, [tasks, filters, rolesMap, user]);

  const sortedTasks = useMemo(() => {
    const list = [...filteredTasks];
    list.sort((a, b) => {
      let comparison = 0;

      switch (sortField) {
        case 'title': {
          comparison = (a.title || '').localeCompare(b.title || '');
          break;
        }
        case 'meeting': {
          const mA = meetingsMap[a.meeting_id]?.title || '';
          const mB = meetingsMap[b.meeting_id]?.title || '';
          comparison = mA.localeCompare(mB);
          break;
        }
        case 'priority': {
          const pA = PRIORITY_ORDER[(a.priority || '').toLowerCase()] || 0;
          const pB = PRIORITY_ORDER[(b.priority || '').toLowerCase()] || 0;
          comparison = pB - pA; // High first by default
          break;
        }
        case 'status': {
          const sA = a.status === 'complete' ? 2 : isTaskExpired(a.deadline) ? 1 : 0;
          const sB = b.status === 'complete' ? 2 : isTaskExpired(b.deadline) ? 1 : 0;
          comparison = sA - sB;
          break;
        }
        case 'deadline':
        default: {
          const dA = a.deadline ? parseDate(a.deadline)?.getTime() || 0 : 0;
          const dB = b.deadline ? parseDate(b.deadline)?.getTime() || 0 : 0;
          // Put tasks with deadlines before tasks without
          if (!dA && dB) return 1;
          if (dA && !dB) return -1;
          comparison = dA - dB;
          break;
        }
      }

      return sortDirection === 'asc' ? comparison : -comparison;
    });
    return list;
  }, [filteredTasks, sortField, sortDirection, meetingsMap]);

  /* ── Sort header toggler ───────────────────────────────────────────────── */
  const handleSort = useCallback((field) => {
    setSortField((currentField) => {
      if (currentField === field) {
        setSortDirection((prevDir) => (prevDir === 'asc' ? 'desc' : 'asc'));
        return field;
      }
      setSortDirection('asc');
      return field;
    });
  }, []);

  /* ── Status toggle action (PUT /tasks/{task_id}/status) ────────────────── */
  const handleStatusToggle = useCallback(
    async (taskId, nextStatus) => {
      setUpdatingTaskId(taskId);
      setActionError(null);

      // Optimistic update in local state
      const prevTasks = [...tasks];
      setTasks((prev) =>
        prev.map((t) => (t.id === taskId ? { ...t, status: nextStatus } : t))
      );

      try {
        await updateTaskStatus(taskId, nextStatus);
      } catch (err) {
        // Revert on failure
        setTasks(prevTasks);
        const formatted = formatApiError(err);
        setActionError(
          formatted.message || 'Failed to update task status. Please try again.'
        );
      } finally {
        setUpdatingTaskId(null);
      }
    },
    [tasks]
  );

  /* ── Metric calculations for header summary chips ───────────────────────── */
  const metrics = useMemo(() => {
    let pendingCount = 0;
    let completeCount = 0;
    let expiredCount = 0;

    tasks.forEach((t) => {
      if (t.status === 'complete') {
        completeCount++;
      } else if (isTaskExpired(t.deadline)) {
        expiredCount++;
      } else {
        pendingCount++;
      }
    });

    return {
      total: tasks.length,
      pending: pendingCount,
      complete: completeCount,
      expired: expiredCount,
    };
  }, [tasks]);

  const isLoading = userLoading || loading;
  const primaryError = userError || error;

  return (
    <div className="page-enter tasks-page">
      <div className="workspace-container tasks-container">
        {/* ── Page Header ───────────────────────────────────────────────── */}
        <header className="tasks-header">
          <div className="tasks-header-left">
            <p className="text-label" id="tasks-page-label">
              Workspace
            </p>
            <h1 className="tasks-title" id="tasks-page-title">
              Tasks
            </h1>
            <p className="tasks-subtitle">
              Manage your action items, priorities, and deadlines across all meetings.
            </p>
          </div>

          <div className="tasks-header-right">
            {/* Summary metric chips */}
            {!isLoading && !primaryError && (
              <div className="tasks-summary-chips" aria-label="Task metric counters">
                <span className="task-summary-chip chip-total" title="Total Tasks">
                  <CheckSquare size={13} aria-hidden="true" />
                  <strong>{metrics.total}</strong> Total
                </span>
                <span className="task-summary-chip chip-pending" title="Active Pending Tasks">
                  <Clock size={13} aria-hidden="true" />
                  <strong>{metrics.pending}</strong> Active
                </span>
                <span className="task-summary-chip chip-complete" title="Completed Tasks">
                  <CheckCircle size={13} aria-hidden="true" />
                  <strong>{metrics.complete}</strong> Done
                </span>
                {metrics.expired > 0 && (
                  <span className="task-summary-chip chip-expired" title="Expired Tasks">
                    <AlertCircle size={13} aria-hidden="true" />
                    <strong>{metrics.expired}</strong> Expired
                  </span>
                )}
              </div>
            )}

            <button
              type="button"
              className="tasks-refresh-btn"
              onClick={refetch}
              disabled={isLoading}
              aria-label="Refresh tasks data"
              title="Refresh tasks"
            >
              <RotateCcw size={14} className={isLoading ? 'spinner-rotate' : ''} aria-hidden="true" />
              <span>Refresh</span>
            </button>
          </div>
        </header>

        {/* ── Action error banner (e.g. status toggle failure) ─────────── */}
        {actionError && (
          <div className="tasks-alert-banner alert-warning" role="alert">
            <AlertTriangle size={16} aria-hidden="true" style={{ flexShrink: 0 }} />
            <div className="alert-content">
              <span className="alert-title">Update Failed</span>
              <span className="alert-message">{actionError}</span>
            </div>
            <button
              type="button"
              className="alert-dismiss-btn"
              onClick={() => setActionError(null)}
              aria-label="Dismiss alert"
            >
              ✕
            </button>
          </div>
        )}

        {/* ── Primary fetch error banner ───────────────────────────────── */}
        {primaryError && !isLoading && (
          <div className="tasks-alert-banner alert-error" role="alert">
            <AlertTriangle size={18} aria-hidden="true" style={{ flexShrink: 0 }} />
            <div className="alert-content">
              <span className="alert-title">Unable to Load Tasks</span>
              <span className="alert-message">{primaryError}</span>
            </div>
            <button
              type="button"
              className="alert-retry-btn"
              onClick={userError ? retrySession : refetch}
              aria-label="Retry loading tasks"
            >
              <RotateCcw size={13} aria-hidden="true" />
              Retry
            </button>
          </div>
        )}

        {/* ── Sticky Filter Bar ─────────────────────────────────────────── */}
        {!primaryError && (
          <FilterBar
            meetings={meetings}
            roles={distinctRoles}
            filters={filters}
            onFilterChange={handleFilterChange}
            onClearFilters={handleClearFilters}
            hasActiveFilters={hasActiveFilters}
            filteredCount={sortedTasks.length}
            totalCount={tasks.length}
          />
        )}

        {/* ── Main Tasks Content ────────────────────────────────────────── */}
        {isLoading && <TaskTableSkeleton />}

        {!isLoading && !primaryError && sortedTasks.length > 0 && (
          <TaskTable
            tasks={sortedTasks}
            meetingsMap={meetingsMap}
            rolesMap={rolesMap}
            defaultRole={user?.role || 'Team Member'}
            onStatusToggle={handleStatusToggle}
            updatingTaskId={updatingTaskId}
            sortField={sortField}
            sortDirection={sortDirection}
            onSort={handleSort}
          />
        )}

        {/* ── Empty State: Filtered Result Empty ────────────────────────── */}
        {!isLoading && !primaryError && tasks.length > 0 && sortedTasks.length === 0 && (
          <div className="tasks-empty-state" role="status">
            <div className="tasks-empty-icon" aria-hidden="true">
              <Filter size={28} />
            </div>
            <h2 className="tasks-empty-title">No tasks found</h2>
            <p className="tasks-empty-desc">
              No tasks matched your current filter criteria. Try adjusting or clearing your filters.
            </p>
            <button
              type="button"
              className="btn-clear-filters-action"
              onClick={handleClearFilters}
              id="tasks-empty-clear-filters-btn"
            >
              <RotateCcw size={14} aria-hidden="true" />
              Clear Filters
            </button>
          </div>
        )}

        {/* ── Empty State: Zero Tasks in Account ────────────────────────── */}
        {!isLoading && !primaryError && tasks.length === 0 && (
          <div className="tasks-empty-state" role="status">
            <div className="tasks-empty-icon" aria-hidden="true">
              <CheckSquare size={28} />
            </div>
            <h2 className="tasks-empty-title">No tasks yet</h2>
            <p className="tasks-empty-desc">
              Upload a meeting transcript on the Meetings page. MeetMind will automatically extract
              your personalized tasks, deadlines, and priorities.
            </p>
            <button
              type="button"
              className="btn-go-meetings"
              onClick={() => navigate('/workspace/meetings')}
              id="tasks-empty-go-meetings-btn"
            >
              Go to Meetings
              <ArrowRight size={14} aria-hidden="true" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default Tasks;
