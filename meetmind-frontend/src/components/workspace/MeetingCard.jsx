import { useNavigate } from 'react-router-dom';
import { MessageSquare, CheckSquare, ArrowRight } from 'lucide-react';
import { formatFullDate, formatShortDate } from '../../utils/formatDate';

/**
 * MeetingCard — Individual Meeting Card Component (Section 8 Sub-View 2 / Batch 5.1)
 *
 * Renders a single meeting entry in the Meetings page list.
 * Displays: date chip, title, organization, user's role, meeting time,
 * task-count chip, highlight-count chip (when available), and "Open Chat →" button.
 *
 * @param {object}        props
 * @param {string}        props.id            - Meeting UUID
 * @param {string}        props.title         - Meeting title
 * @param {string}        [props.organization] - Organization or team name
 * @param {string}        [props.user_role]   - Authenticated user's role in this meeting
 * @param {string}        [props.date]        - ISO date string for the meeting
 * @param {string}        [props.time]        - Time string (e.g. "14:30" or "2:30 PM")
 * @param {number|null}   [props.task_count]  - Number of extracted tasks (null = not available)
 * @param {number|null}   [props.highlight_count] - Number of highlights (null = not available)
 */
function MeetingCard({
  id,
  title,
  organization,
  user_role,
  date,
  time,
  task_count,
  highlight_count,
}) {
  const navigate = useNavigate();

  const handleOpenChat = () => {
    navigate(`/workspace/chat?meeting=${id}`);
  };

  const displayTitle = title || 'Untitled Meeting';
  const dateChip = date ? formatShortDate(date, '—') : '—';
  const dateAriaLabel = date ? formatFullDate(date, 'Unknown date') : 'Unknown date';

  return (
    <li className="meeting-card" aria-label={`Meeting: ${displayTitle}`}>
      {/* ── Top Row: title block + chat button ───────────────────────────── */}
      <div className="meeting-card-top">
        <div className="meeting-card-title-row">
          {/* Date chip */}
          <span
            className="meeting-card-date-chip"
            aria-label={`Meeting date: ${dateAriaLabel}`}
          >
            {dateChip}
          </span>

          {/* Meeting title */}
          <h3 className="meeting-card-title" title={displayTitle}>
            {displayTitle}
          </h3>
        </div>

        {/* Open Chat button */}
        <div className="meeting-card-actions">
          <button
            type="button"
            className="btn-open-chat"
            onClick={handleOpenChat}
            aria-label={`Open chat for meeting: ${displayTitle}`}
            id={`open-chat-${id}`}
          >
            Open Chat
            <ArrowRight size={14} aria-hidden="true" />
          </button>
        </div>
      </div>

      {/* ── Meta row: org, role, time ─────────────────────────────────── */}
      {(organization || user_role || time) && (
        <p className="meeting-card-meta">
          {organization && (
            <span className="meeting-card-meta-value">{organization}</span>
          )}
          {organization && (user_role || time) && (
            <span className="meeting-card-meta-sep" aria-hidden="true">•</span>
          )}
          {user_role && (
            <span className="meeting-card-meta-value">{user_role}</span>
          )}
          {user_role && time && (
            <span className="meeting-card-meta-sep" aria-hidden="true">•</span>
          )}
          {time && (
            <time className="meeting-card-meta-value" dateTime={time}>
              {time}
            </time>
          )}
        </p>
      )}

      {/* ── Chips row: task count + highlight count ───────────────────── */}
      {(task_count != null || highlight_count != null) && (
        <div className="meeting-card-chips">
          {task_count != null && (
            <span
              className="meeting-card-count-chip"
              aria-label={`${task_count} task${task_count !== 1 ? 's' : ''}`}
            >
              <CheckSquare size={12} aria-hidden="true" />
              {task_count} {task_count === 1 ? 'Task' : 'Tasks'}
            </span>
          )}
          {highlight_count != null && (
            <span
              className="meeting-card-count-chip"
              aria-label={`${highlight_count} highlight${highlight_count !== 1 ? 's' : ''}`}
            >
              <MessageSquare size={12} aria-hidden="true" />
              {highlight_count} {highlight_count === 1 ? 'Highlight' : 'Highlights'}
            </span>
          )}
        </div>
      )}
    </li>
  );
}

export default MeetingCard;
