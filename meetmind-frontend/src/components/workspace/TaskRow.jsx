import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Check, RotateCcw, ChevronDown, ChevronUp, Calendar } from 'lucide-react';
import Badge from '../ui/Badge';
import { formatShortDate, formatFullDate, parseDate } from '../../utils/formatDate';

/**
 * Checks if a deadline is in the past compared to now.
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
 * TaskRow — Individual Row in the Task Table (Section 8 Sub-View 3 / Batch 5.2)
 *
 * Columns:
 *   | Task Title | Meeting | Priority | Deadline | Status | Role | Actions |
 *
 * - Priority: colored dot + label (red for high, amber for medium, green for low)
 * - Status: pill badge (blue=pending, grey=complete, red=expired)
 * - Actions: toggle button — "Mark Done" if pending, "Reopen" if complete
 * - Row hover: subtle blue-tinted background
 *
 * @param {object} props
 * @param {object} props.task - Task object from API
 * @param {string} props.meetingTitle - Resolved title of parent meeting
 * @param {string} [props.role] - User's role in the meeting
 * @param {Function} props.onStatusToggle - Callback (taskId, nextStatus)
 * @param {boolean} [props.isUpdating=false] - Whether this specific task is currently updating
 */
function TaskRow({
  task,
  meetingTitle,
  role = '—',
  onStatusToggle,
  isUpdating = false,
}) {
  const navigate = useNavigate();
  const [isExpanded, setIsExpanded] = useState(false);

  const isComplete = task.status === 'complete';
  const isExpired = !isComplete && isTaskExpired(task.deadline);

  // Compute status variant for Badge component
  const statusVariant = isComplete ? 'complete' : isExpired ? 'expired' : 'pending';
  const statusLabel = isComplete ? 'Complete' : isExpired ? 'Expired' : 'Pending';

  // Priority metadata
  const priorityKey = (task.priority || 'medium').toLowerCase();
  const priorityLabels = {
    high: 'High',
    medium: 'Medium',
    low: 'Low',
  };
  const priorityLabel = priorityLabels[priorityKey] || 'Medium';

  const deadlineFormatted = task.deadline ? formatShortDate(task.deadline, '—') : '—';
  const deadlineFull = task.deadline ? formatFullDate(task.deadline) : '';

  const handleActionClick = () => {
    if (isUpdating) return;
    const nextStatus = isComplete ? 'pending' : 'complete';
    onStatusToggle(task.id, nextStatus);
  };

  const handleMeetingClick = () => {
    if (task.meeting_id) {
      navigate(`/workspace/chat?meeting=${task.meeting_id}`);
    }
  };

  return (
    <>
      <tr
        className={`task-row${isComplete ? ' is-completed' : ''}${isExpanded ? ' is-expanded' : ''}`}
        id={`task-row-${task.id}`}
      >
        {/* ── 1. Task Title ────────────────────────────────────────────── */}
        <td className="task-cell-title">
          <div className="task-title-content">
            <span className="task-title-text" title={task.title}>
              {task.title}
            </span>
            {task.description && (
              <button
                type="button"
                className="task-desc-toggle"
                onClick={() => setIsExpanded((prev) => !prev)}
                aria-expanded={isExpanded}
                aria-label={isExpanded ? 'Hide task description' : 'Show task description'}
                title={isExpanded ? 'Hide description' : 'View description'}
              >
                {isExpanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
              </button>
            )}
          </div>
        </td>

        {/* ── 2. Meeting ──────────────────────────────────────────────── */}
        <td className="task-cell-meeting">
          {task.meeting_id ? (
            <button
              type="button"
              className="task-meeting-link"
              onClick={handleMeetingClick}
              title={`Open chat for ${meetingTitle || 'meeting'}`}
            >
              {meetingTitle || 'Meeting'}
            </button>
          ) : (
            <span className="task-meeting-name">{meetingTitle || '—'}</span>
          )}
        </td>

        {/* ── 3. Priority ─────────────────────────────────────────────── */}
        <td className="task-cell-priority">
          <span className={`priority-indicator priority-${priorityKey}`} aria-label={`Priority: ${priorityLabel}`}>
            <span className="priority-dot" aria-hidden="true" />
            <span className="priority-text">{priorityLabel}</span>
          </span>
        </td>

        {/* ── 4. Deadline ─────────────────────────────────────────────── */}
        <td className="task-cell-deadline">
          {task.deadline ? (
            <span
              className={`task-deadline-badge${isExpired ? ' is-expired' : ''}`}
              title={deadlineFull ? `Due: ${deadlineFull}` : undefined}
            >
              <Calendar size={12} className="task-deadline-icon" aria-hidden="true" />
              <time dateTime={task.deadline}>{deadlineFormatted}</time>
            </span>
          ) : (
            <span className="task-deadline-empty">—</span>
          )}
        </td>

        {/* ── 5. Status ───────────────────────────────────────────────── */}
        <td className="task-cell-status">
          <Badge variant={statusVariant} id={`task-badge-${task.id}`}>
            {statusLabel}
          </Badge>
        </td>

        {/* ── 6. Role ─────────────────────────────────────────────────── */}
        <td className="task-cell-role">
          <span className="task-role-text" title={role}>
            {role}
          </span>
        </td>

        {/* ── 7. Actions ──────────────────────────────────────────────── */}
        <td className="task-cell-actions">
          <button
            type="button"
            className={`btn-task-action ${isComplete ? 'btn-task-reopen' : 'btn-task-done'}`}
            onClick={handleActionClick}
            disabled={isUpdating}
            aria-label={isComplete ? `Reopen task: ${task.title}` : `Mark task done: ${task.title}`}
            id={`task-toggle-btn-${task.id}`}
          >
            {isUpdating ? (
              <span className="spinner spinner-sm spinner-dark" aria-hidden="true" />
            ) : isComplete ? (
              <>
                <RotateCcw size={13} aria-hidden="true" />
                Reopen
              </>
            ) : (
              <>
                <Check size={14} aria-hidden="true" />
                Mark Done
              </>
            )}
          </button>
        </td>
      </tr>

      {/* ── Expandable Description Row ───────────────────────────────── */}
      {isExpanded && task.description && (
        <tr className="task-desc-row" aria-label={`Description for ${task.title}`}>
          <td colSpan={7} className="task-desc-cell">
            <div className="task-desc-box">
              <span className="task-desc-label">Task Details:</span>
              <p className="task-desc-text">{task.description}</p>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

export default TaskRow;
