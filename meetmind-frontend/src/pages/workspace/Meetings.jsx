import { useState, useEffect, useCallback, useRef } from 'react';
import { Plus, MessageSquare, AlertTriangle, RotateCcw } from 'lucide-react';
import MeetingCard from '../../components/workspace/MeetingCard';
import NewMeetingForm from '../../components/workspace/NewMeetingForm';
import { useUser } from '../../hooks/useUser';
import { getMeetings, formatApiError } from '../../services/api';

/**
 * MeetingCardSkeleton — Placeholder card shown during data loading.
 */
function MeetingCardSkeleton({ index = 0 }) {
  return (
    <li
      className="meeting-card-skeleton"
      aria-hidden="true"
      style={{ animationDelay: `${index * 80}ms` }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <div className="skeleton-line skeleton-line-sm" />
        <div className="skeleton-line skeleton-line-lg" />
      </div>
      <div className="skeleton-line skeleton-line-md" />
      <div className="skeleton-line skeleton-line-chips" />
    </li>
  );
}

/**
 * Meetings — Workspace Sub-View 2 (Section 8 Sub-View 2 / Batch 5.1)
 *
 * Fetches and displays the authenticated user's meetings from the FastAPI backend.
 * Provides a "+ New Meeting" button that opens the NewMeetingForm modal.
 * Refreshes the meeting list after successful creation.
 *
 * API integration:
 *   - GET /meetings/{user_id} to list meetings (via getMeetings)
 *   - POST /meetings/ for creation (delegated to NewMeetingForm → createMeeting)
 *
 * No mock data is used. Loading, error, and empty states are all handled explicitly.
 */
function Meetings() {
  const { userId, loading: userLoading, error: userError } = useUser();

  const [meetings, setMeetings] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [refetchTrigger, setRefetchTrigger] = useState(0);
  const abortRef = useRef(null);

  /* ── Load meetings from API ──────────────────────────────────────────────── */
  useEffect(() => {
    if (userLoading || !userId) return;

    // Cancel any in-flight request
    if (abortRef.current) abortRef.current.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    let ignore = false;
    setLoading(true);
    setError(null);

    getMeetings(userId, { signal: controller.signal })
      .then((data) => {
        if (ignore) return;
        const list = Array.isArray(data) ? data : [];
        // Sort descending by date (most recent first)
        list.sort((a, b) => {
          const rawA = a.meeting_date ?? a.date ?? a.created_at;
          const rawB = b.meeting_date ?? b.date ?? b.created_at;
          const da = rawA ? new Date(rawA).getTime() : 0;
          const db = rawB ? new Date(rawB).getTime() : 0;
          return db - da;
        });
        setMeetings(list);
        setError(null);
      })
      .catch((err) => {
        if (ignore) return;
        const formatted = formatApiError(err);
        if (!formatted.isCanceled) {
          setError(formatted.message || 'Failed to load meetings.');
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

  const refetch = useCallback(() => setRefetchTrigger((c) => c + 1), []);

  /* ── Modal handlers ──────────────────────────────────────────────────────── */
  const openModal = () => setIsModalOpen(true);
  const closeModal = () => setIsModalOpen(false);

  /**
   * Called when NewMeetingForm successfully creates a meeting.
   * Prepends the new meeting to the list optimistically, then triggers a full refetch
   * to ensure the list is consistent with the server response.
   *
   * @param {object} newMeeting - The MeetingResponse returned by POST /meetings/
   */
  const handleMeetingCreated = useCallback((newMeeting) => {
    if (newMeeting && newMeeting.id) {
      setMeetings((prev) => [newMeeting, ...prev]);
    }
    // Full refetch for canonical server state
    refetch();
  }, [refetch]);

  /* ── Derived state ───────────────────────────────────────────────────────── */
  const isLoading = userLoading || loading;
  const primaryError = userError || error;

  /* ── Render ──────────────────────────────────────────────────────────────── */
  return (
    <div className="page-enter">
      <div className="workspace-container">

        {/* ── Page Header ───────────────────────────────────────────────── */}
        <header className="meetings-header">
          <div className="meetings-header-text">
            <p className="text-label meetings-header-label">Workspace</p>
            <h1 className="text-h1 meetings-header-title">Meetings</h1>
            <p className="meetings-header-desc">
              Your transcript repository and meeting intelligence extraction.
            </p>
          </div>
          <button
            type="button"
            className="btn-new-meeting"
            onClick={openModal}
            id="new-meeting-open-btn"
            aria-label="Create a new meeting"
          >
            <Plus size={16} aria-hidden="true" />
            New Meeting
          </button>
        </header>

        {/* ── Error Banner ──────────────────────────────────────────────── */}
        {primaryError && !isLoading && (
          <aside className="meetings-error-banner" role="alert">
            <div className="meetings-error-content">
              <AlertTriangle size={18} aria-hidden="true" style={{ flexShrink: 0 }} />
              <span>{primaryError}</span>
            </div>
            <button
              type="button"
              className="btn-retry"
              onClick={refetch}
              aria-label="Retry loading meetings"
            >
              <RotateCcw size={13} aria-hidden="true" />
              Retry
            </button>
          </aside>
        )}

        {/* ── Loading Skeletons ─────────────────────────────────────────── */}
        {isLoading && (
          <ul className="meetings-list" aria-label="Loading meetings" aria-busy="true">
            {[0, 1, 2].map((i) => (
              <MeetingCardSkeleton key={i} index={i} />
            ))}
          </ul>
        )}

        {/* ── Meeting List ──────────────────────────────────────────────── */}
        {!isLoading && !primaryError && meetings.length > 0 && (
          <ul
            className="meetings-list"
            aria-label={`${meetings.length} meeting${meetings.length !== 1 ? 's' : ''}`}
          >
            {meetings.map((meeting, idx) => (
              <MeetingCard
                key={meeting.id}
                id={meeting.id}
                title={meeting.title}
                organization={meeting.organization}
                user_role={meeting.user_role ?? meeting.role}
                date={meeting.meeting_date ?? meeting.date ?? meeting.created_at}
                time={meeting.meeting_time ?? meeting.time}
                task_count={meeting.task_count ?? null}
                highlight_count={meeting.highlight_count ?? null}
                style={{ animationDelay: `${idx * 60}ms` }}
              />
            ))}
          </ul>
        )}

        {/* ── Empty State ───────────────────────────────────────────────── */}
        {!isLoading && !primaryError && meetings.length === 0 && (
          <div className="meetings-empty-state" role="status">
            <div className="meetings-empty-icon" aria-hidden="true">
              <MessageSquare size={28} />
            </div>
            <h2 className="meetings-empty-title">No meetings yet</h2>
            <p className="meetings-empty-desc">
              Create your first meeting by uploading or pasting a transcript.
              MeetMind will identify your role, extract your tasks, and make
              the content searchable.
            </p>
            <button
              type="button"
              className="btn-new-meeting"
              onClick={openModal}
              id="meetings-empty-create-btn"
              aria-label="Create your first meeting"
            >
              <Plus size={15} aria-hidden="true" />
              Create Meeting
            </button>
          </div>
        )}
      </div>

      {/* ── New Meeting Modal ─────────────────────────────────────────────── */}
      <NewMeetingForm
        isOpen={isModalOpen}
        onClose={closeModal}
        onSuccess={handleMeetingCreated}
      />
    </div>
  );
}

export default Meetings;
