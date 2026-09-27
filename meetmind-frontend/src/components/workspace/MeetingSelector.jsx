import { useState, useRef, useEffect } from 'react';
import {
  ChevronDown,
  Calendar,
  Clock,
  Building2,
  Users,
  Sparkles,
  Trash2,
  Check,
} from 'lucide-react';
import { formatFullDate, formatShortDate } from '../../utils/formatDate';

/**
 * MeetingSelector — Workspace Chat Header & Meeting Context Selector (Section 8 Sub-View 4)
 *
 * Provides:
 * 1. Dropdown select populated with all user meetings.
 * 2. Active context banner: "Chatting about: {meeting_title} — {meeting_date}".
 * 3. Meeting metadata chips (Organization, Submitter Role, Date, Time, Participants).
 * 4. Action triggers: "Run Task Extraction" and "Clear History".
 *
 * @param {object} props
 * @param {Array<object>} props.meetings - List of user meetings
 * @param {string} props.selectedMeetingId - Active meeting UUID
 * @param {Function} props.onSelectMeeting - Callback when user chooses a different meeting
 * @param {Function} props.onOpenExtraction - Callback to trigger explicit-name extraction modal
 * @param {Function} props.onClearHistory - Callback to clear chat history
 * @param {object|null} [props.meetingDetail] - Enriched meeting detail (participants, transcript)
 * @param {boolean} [props.isClearing=false] - Whether history is currently being cleared
 * @param {boolean} [props.hasMessages=false] - Whether conversation currently contains messages
 */
function MeetingSelector({
  meetings = [],
  selectedMeetingId,
  onSelectMeeting,
  onOpenExtraction,
  onClearHistory,
  meetingDetail = null,
  isClearing = false,
  hasMessages = false,
}) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const activeMeeting =
    meetings.find((m) => m.id === selectedMeetingId) ||
    (meetingDetail && meetingDetail.id === selectedMeetingId ? meetingDetail : null) ||
    meetings[0] ||
    null;

  const displayTitle = activeMeeting?.title || 'Select a Meeting';
  const meetingDate = activeMeeting?.meeting_date ?? activeMeeting?.date ?? activeMeeting?.created_at;
  const formattedDate = meetingDate ? formatFullDate(meetingDate) : 'Unknown date';
  const shortDate = meetingDate ? formatShortDate(meetingDate) : '—';
  const org = activeMeeting?.organization || meetingDetail?.organization;
  const role = activeMeeting?.user_role ?? activeMeeting?.role ?? (
    meetingDetail?.participants?.find((p) => p.is_current_user)?.role
  );
  const time = activeMeeting?.meeting_time ?? activeMeeting?.time ?? meetingDetail?.meeting_time;
  const participantsCount = meetingDetail?.participants?.length ?? null;

  return (
    <section className="meeting-selector-card" aria-label="Meeting context and selection">
      <div className="meeting-selector-top">
        {/* ── Left: Dropdown Trigger & Context Banner ─────────────────────── */}
        <div className="meeting-selector-dropdown-wrapper" ref={dropdownRef}>
          <button
            type="button"
            className="meeting-selector-btn"
            onClick={() => setIsOpen((prev) => !prev)}
            aria-haspopup="listbox"
            aria-expanded={isOpen}
            id="meeting-selector-trigger"
          >
            <span className="meeting-selector-btn-label">
              <span className="meeting-selector-date-chip">{shortDate}</span>
              <span className="meeting-selector-title-text" title={displayTitle}>
                {displayTitle}
              </span>
            </span>
            <ChevronDown
              size={18}
              className={`meeting-selector-chevron ${isOpen ? 'is-open' : ''}`}
              aria-hidden="true"
            />
          </button>

          {/* ── Dropdown Menu ────────────────────────────────────────────── */}
          {isOpen && (
            <div
              className="meeting-selector-menu"
              role="listbox"
              aria-label="Select meeting for Q&A"
              id="meeting-selector-listbox"
            >
              <div className="meeting-selector-menu-header">
                Select Meeting ({meetings.length})
              </div>
              <ul className="meeting-selector-menu-list">
                {meetings.map((m) => {
                  const isSelected = m.id === selectedMeetingId;
                  const mDate = m.meeting_date ?? m.date ?? m.created_at;
                  return (
                    <li
                      key={m.id}
                      role="option"
                      aria-selected={isSelected}
                      className={`meeting-selector-item ${isSelected ? 'is-selected' : ''}`}
                      onClick={() => {
                        onSelectMeeting(m.id);
                        setIsOpen(false);
                      }}
                    >
                      <div className="meeting-selector-item-text">
                        <span className="meeting-selector-item-title">{m.title || 'Untitled Meeting'}</span>
                        <span className="meeting-selector-item-meta">
                          {mDate ? formatShortDate(mDate) : '—'}
                          {m.organization ? ` • ${m.organization}` : ''}
                        </span>
                      </div>
                      {isSelected && (
                        <Check size={16} className="meeting-selector-check" aria-hidden="true" />
                      )}
                    </li>
                  );
                })}
              </ul>
            </div>
          )}
        </div>

        {/* ── Right: Header Actions (Extraction & Clear History) ──────────── */}
        <div className="meeting-selector-actions">
          <button
            type="button"
            className="btn-extract-tasks"
            onClick={onOpenExtraction}
            disabled={!selectedMeetingId}
            title="Trigger task extraction for an explicit participant name"
            aria-label="Run task extraction for this meeting"
            id="run-task-extraction-btn"
          >
            <Sparkles size={15} aria-hidden="true" />
            <span>Extract Tasks</span>
          </button>

          {hasMessages && (
            <button
              type="button"
              className="btn-clear-chat"
              onClick={onClearHistory}
              disabled={isClearing || !selectedMeetingId}
              title="Clear all chat messages for this meeting"
              aria-label="Clear chat history"
              id="clear-chat-history-btn"
            >
              <Trash2 size={15} aria-hidden="true" />
              <span>{isClearing ? 'Clearing...' : 'Clear'}</span>
            </button>
          )}
        </div>
      </div>

      {/* ── Context Subtext Banner (Design Doc Section 8 Line 666) ──────── */}
      {activeMeeting && (
        <div className="meeting-context-banner">
          <p className="meeting-context-caption">
            Chatting about:{' '}
            <strong className="meeting-context-highlight">{displayTitle}</strong>
            {' '}&mdash; {formattedDate}
          </p>

          {/* Metadata badges row */}
          <div className="meeting-context-chips">
            {org && (
              <span className="meeting-context-chip" title="Organization">
                <Building2 size={13} aria-hidden="true" />
                {org}
              </span>
            )}
            {role && (
              <span className="meeting-context-chip" title="Your role in meeting">
                Role: {role}
              </span>
            )}
            {time && (
              <span className="meeting-context-chip" title="Meeting time">
                <Clock size={13} aria-hidden="true" />
                {time}
              </span>
            )}
            {participantsCount != null && (
              <span className="meeting-context-chip" title="Detected participants">
                <Users size={13} aria-hidden="true" />
                {participantsCount} participant{participantsCount !== 1 ? 's' : ''}
              </span>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

export default MeetingSelector;
