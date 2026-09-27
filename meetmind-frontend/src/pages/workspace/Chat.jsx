import { useState, useEffect, useRef, useCallback } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  MessageSquare,
  AlertTriangle,
  RotateCcw,
  Plus,
  Sparkles,
  HelpCircle,
  CheckCircle,
} from 'lucide-react';
import { useUser } from '../../hooks/useUser';
import {
  getMeetings,
  getMeetingDetail,
  getChatHistory,
  sendMessage,
  clearChatHistory,
  runExtraction,
  getExtractionPreview,
  confirmExtraction,
  formatApiError,
} from '../../services/api';
import MeetingSelector from '../../components/workspace/MeetingSelector';
import ChatBubble from '../../components/workspace/ChatBubble';
import ChatInput from '../../components/workspace/ChatInput';
import TypingIndicator from '../../components/ui/TypingIndicator';
import TaskExtractionModal from '../../components/workspace/TaskExtractionModal';
import TaskReviewCard from '../../components/workspace/TaskReviewCard';

const SUGGESTED_PROMPTS = [
  'What tasks were assigned to me in this meeting?',
  'Summarize the key decisions made in this meeting.',
  'What are the critical project deadlines mentioned?',
];

/**
 * Chat — Workspace Sub-View 4 (Section 8 Sub-View 4 & Batch 6.1)
 *
 * Implements:
 * 1. Meeting selection with URL query parameter synchronization (?meeting={id}).
 * 2. Meeting context header (title, date, org, role, participant count).
 * 3. Chronological conversation history loading and clear action.
 * 4. Normal Q&A chat with grounded AI answers, confidence levels, and source citations.
 * 5. Optimistic message rendering with auto-scroll to bottom.
 * 6. Explicit-name task extraction modal and pipeline execution.
 * 7. Interactive task review (description/deadline editing, inclusion/exclusion, confirmation).
 * 8. Loading, error, and empty states.
 */
function Chat() {
  const { userId, loading: userLoading, error: userError } = useUser();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  // Meetings state
  const [meetings, setMeetings] = useState([]);
  const [meetingsLoading, setMeetingsLoading] = useState(true);
  const [meetingsError, setMeetingsError] = useState(null);

  // Active meeting selection & enriched detail
  const [activeMeetingId, setActiveMeetingId] = useState('');
  const [meetingDetail, setMeetingDetail] = useState(null);

  // Chat conversation state
  const [messages, setMessages] = useState([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState(null);
  const [isThinking, setIsThinking] = useState(false);
  const [isClearing, setIsClearing] = useState(false);

  // Extraction & Task Review state
  const [isExtractionModalOpen, setIsExtractionModalOpen] = useState(false);
  const [extractionLoading, setExtractionLoading] = useState(false);
  const [extractionError, setExtractionError] = useState(null);
  const [reviewTasks, setReviewTasks] = useState([]);
  const [reviewHighlights, setReviewHighlights] = useState([]);
  const [reviewTargetName, setReviewTargetName] = useState('');
  const [confirmLoading, setConfirmLoading] = useState(false);
  const [confirmError, setConfirmError] = useState(null);
  const [isTaskConfirmed, setIsTaskConfirmed] = useState(false);

  // Message scroll anchor ref
  const messagesEndRef = useRef(null);
  const chatStreamRef = useRef(null);

  const scrollToBottom = useCallback((behavior = 'smooth') => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior });
    }
  }, []);

  /* ── 1. Load user meetings on mount ────────────────────────────────────── */
  useEffect(() => {
    if (userLoading || !userId) return;

    let ignore = false;
    setMeetingsLoading(true);
    setMeetingsError(null);

    getMeetings(userId)
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

        // Resolve meeting ID from query parameter (?meeting= or ?meetingId=) or default to latest
        const queryMeetingId = searchParams.get('meeting') || searchParams.get('meetingId');
        const matched = list.find((m) => m.id === queryMeetingId);

        if (matched) {
          setActiveMeetingId(matched.id);
        } else if (list.length > 0) {
          const fallbackId = list[0].id;
          setActiveMeetingId(fallbackId);
          setSearchParams({ meeting: fallbackId }, { replace: true });
        } else {
          setActiveMeetingId('');
        }
      })
      .catch((err) => {
        if (ignore) return;
        const formatted = formatApiError(err);
        setMeetingsError(formatted.message || 'Failed to load meetings.');
      })
      .finally(() => {
        if (!ignore) setMeetingsLoading(false);
      });

    return () => {
      ignore = true;
    };
  }, [userId, userLoading, setSearchParams]);

  /* ── 2. Handle meeting switching ────────────────────────────────────────── */
  const handleSelectMeeting = useCallback(
    (meetingId) => {
      if (meetingId === activeMeetingId) return;
      setActiveMeetingId(meetingId);
      setSearchParams({ meeting: meetingId }, { replace: true });
      // Reset current chat state & extraction review for new meeting
      setMessages([]);
      setChatError(null);
      setReviewTasks([]);
      setReviewHighlights([]);
      setReviewTargetName('');
      setIsTaskConfirmed(false);
    },
    [activeMeetingId, setSearchParams]
  );

  /* ── 3. Load meeting details, chat history, and extraction preview ──────── */
  useEffect(() => {
    if (!activeMeetingId || !userId) return;

    let ignore = false;
    setChatLoading(true);
    setChatError(null);

    // Concurrently fetch meeting detail and history
    const detailPromise = getMeetingDetail(activeMeetingId).catch(() => null);
    const historyPromise = getChatHistory(activeMeetingId).catch((err) => {
      throw err;
    });
    const previewPromise = getExtractionPreview(activeMeetingId, userId).catch(() => null);

    Promise.all([detailPromise, historyPromise, previewPromise])
      .then(([detail, historyRes, previewRes]) => {
        if (ignore) return;
        if (detail) setMeetingDetail(detail);

        // Populate messages from history
        const loadedMsgs = historyRes?.messages || [];
        setMessages(loadedMsgs);

        // Check for existing unconfirmed extraction items
        if (previewRes?.tasks && previewRes.tasks.length > 0 && !previewRes.confirmation_complete) {
          setReviewTasks(previewRes.tasks);
          setReviewHighlights(previewRes.highlights || []);
        }

        setTimeout(() => scrollToBottom('auto'), 80);
      })
      .catch((err) => {
        if (ignore) return;
        const formatted = formatApiError(err);
        setChatError(formatted.message || 'Failed to load conversation history.');
      })
      .finally(() => {
        if (!ignore) setChatLoading(false);
      });

    return () => {
      ignore = true;
    };
  }, [activeMeetingId, userId, scrollToBottom]);

  /* ── 4. Send Message & Q&A Response ─────────────────────────────────────── */
  const handleSendMessage = async (question) => {
    if (!activeMeetingId || !userId || !question.trim()) return;

    const optimisticId = `user-${Date.now()}`;
    const optimisticMsg = {
      id: optimisticId,
      role: 'user',
      content: question,
      created_at: new Date().toISOString(),
      isOptimistic: true,
    };

    setMessages((prev) => [...prev, optimisticMsg]);
    setIsThinking(true);
    setChatError(null);
    setTimeout(() => scrollToBottom('smooth'), 50);

    try {
      const response = await sendMessage(activeMeetingId, {
        question,
        user_id: userId,
      });

      // Update optimistic message and append assistant response
      const assistantMsg = {
        id: `ai-${Date.now()}`,
        role: 'assistant',
        content: response.answer,
        sources: response.sources || [],
        confidence: response.confidence || 'high',
        created_at: new Date().toISOString(),
      };

      setMessages((prev) =>
        prev
          .map((m) => (m.id === optimisticId ? { ...m, isOptimistic: false } : m))
          .concat(assistantMsg)
      );
    } catch (err) {
      const formatted = formatApiError(err);
      setChatError(formatted.message || 'Failed to get answer from Q&A pipeline.');
      // Remove optimistic message on error so user can retry
      setMessages((prev) => prev.filter((m) => m.id !== optimisticId));
    } finally {
      setIsThinking(false);
      setTimeout(() => scrollToBottom('smooth'), 80);
    }
  };

  /* ── 5. Clear Conversation History ──────────────────────────────────────── */
  const handleClearHistory = async () => {
    if (!activeMeetingId) return;
    const confirmed = window.confirm(
      'Are you sure you want to clear the conversation history for this meeting? This action cannot be undone.'
    );
    if (!confirmed) return;

    setIsClearing(true);
    setChatError(null);
    try {
      await clearChatHistory(activeMeetingId);
      setMessages([]);
    } catch (err) {
      const formatted = formatApiError(err);
      setChatError(formatted.message || 'Failed to clear chat history.');
    } finally {
      setIsClearing(false);
    }
  };

  /* ── 6. Task Extraction Execution (Explicit Participant Name) ──────────── */
  const handleRunExtraction = async (explicitPersonName) => {
    if (!activeMeetingId || !userId || !explicitPersonName.trim()) return;

    setExtractionLoading(true);
    setExtractionError(null);
    try {
      const result = await runExtraction(activeMeetingId, {
        meeting_id: activeMeetingId,
        user_id: userId,
        person_name: explicitPersonName.trim(),
      });

      setIsExtractionModalOpen(false);
      setReviewTargetName(explicitPersonName.trim());
      setReviewTasks(result?.tasks || []);
      setReviewHighlights(result?.highlights || []);
      setIsTaskConfirmed(false);
      setTimeout(() => scrollToBottom('smooth'), 100);
    } catch (err) {
      const formatted = formatApiError(err);
      setExtractionError(
        formatted.message || 'Extraction pipeline failed. Please check participant name and try again.'
      );
    } finally {
      setExtractionLoading(false);
    }
  };

  /* ── 7. Task Confirmation & Persistence ─────────────────────────────────── */
  const handleConfirmTasks = async ({ user_confirmation, confirmed_task_ids, modified_tasks }) => {
    if (!activeMeetingId || !userId) return;

    setConfirmLoading(true);
    setConfirmError(null);
    try {
      await confirmExtraction(activeMeetingId, {
        meeting_id: activeMeetingId,
        user_id: userId,
        user_confirmation,
        confirmed_task_ids,
        modified_tasks,
      });

      setIsTaskConfirmed(true);
      // Optional notice in chat
      const confirmNotice = {
        id: `notice-${Date.now()}`,
        role: 'assistant',
        content: `Tasks for ${reviewTargetName || 'participant'} have been successfully confirmed and persisted to your dashboard!`,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, confirmNotice]);
      setTimeout(() => scrollToBottom('smooth'), 80);
    } catch (err) {
      const formatted = formatApiError(err);
      setConfirmError(formatted.message || 'Failed to save confirmed tasks.');
    } finally {
      setConfirmLoading(false);
    }
  };

  /* ── Render Fallbacks: Loading, Auth Error, Empty Meetings ─────────────── */
  const isLoading = userLoading || meetingsLoading;
  const primaryError = userError || meetingsError;

  if (isLoading) {
    return (
      <div className="page-enter">
        <div className="workspace-container chat-page-container">
          <div className="chat-loading-state" role="status" aria-busy="true">
            <div className="skeleton chat-selector-skeleton" />
            <div className="skeleton chat-stream-skeleton" />
            <div className="skeleton chat-input-skeleton" />
          </div>
        </div>
      </div>
    );
  }

  if (primaryError) {
    return (
      <div className="page-enter">
        <div className="workspace-container chat-page-container">
          <aside className="chat-error-banner" role="alert">
            <div className="chat-error-content">
              <AlertTriangle size={20} aria-hidden="true" style={{ flexShrink: 0 }} />
              <span>{primaryError}</span>
            </div>
            <button
              type="button"
              className="btn-retry"
              onClick={() => window.location.reload()}
              aria-label="Reload page"
            >
              <RotateCcw size={14} aria-hidden="true" />
              Reload
            </button>
          </aside>
        </div>
      </div>
    );
  }

  if (meetings.length === 0) {
    return (
      <div className="page-enter">
        <div className="workspace-container chat-page-container">
          <header className="chat-page-header">
            <p className="text-label chat-header-label">Workspace</p>
            <h1 className="text-h1 chat-header-title">Meeting Chat</h1>
          </header>

          <div className="chat-empty-meetings-card" role="status">
            <div className="chat-empty-icon" aria-hidden="true">
              <MessageSquare size={36} />
            </div>
            <h2 className="chat-empty-title">No Meetings Available</h2>
            <p className="chat-empty-desc">
              To chat with your meeting assistant and query transcript intelligence,
              you must first create a meeting and upload or paste a transcript.
            </p>
            <button
              type="button"
              className="btn-primary btn-empty-create-meeting"
              onClick={() => navigate('/workspace/meetings')}
              id="chat-empty-create-meeting-btn"
            >
              <Plus size={16} aria-hidden="true" />
              Go to Meetings
            </button>
          </div>
        </div>
      </div>
    );
  }

  /* ── Main Chat Interface ────────────────────────────────────────────────── */
  const activeMeeting = meetings.find((m) => m.id === activeMeetingId) || meetings[0];

  return (
    <div className="page-enter">
      <div className="workspace-container chat-page-container">
        {/* ── Meeting Selector Top Bar & Context Banner ──────────────────── */}
        <MeetingSelector
          meetings={meetings}
          selectedMeetingId={activeMeetingId}
          onSelectMeeting={handleSelectMeeting}
          onOpenExtraction={() => setIsExtractionModalOpen(true)}
          onClearHistory={handleClearHistory}
          meetingDetail={meetingDetail}
          isClearing={isClearing}
          hasMessages={messages.length > 0}
        />

        {/* ── Chat Error Alert Banner (if any) ───────────────────────────── */}
        {chatError && (
          <aside className="chat-alert-banner alert-warning" role="alert">
            <div className="chat-alert-text">
              <AlertTriangle size={16} aria-hidden="true" style={{ flexShrink: 0 }} />
              <span>{chatError}</span>
            </div>
            <button
              type="button"
              className="btn-alert-dismiss"
              onClick={() => setChatError(null)}
              aria-label="Dismiss error banner"
            >
              Dismiss
            </button>
          </aside>
        )}

        {/* ── Interactive Task Review Panel (if extracted tasks pending) ─── */}
        {reviewTasks.length > 0 && (
          <TaskReviewCard
            tasks={reviewTasks}
            highlights={reviewHighlights}
            targetName={reviewTargetName}
            onConfirmTasks={handleConfirmTasks}
            onDiscard={() => {
              setReviewTasks([]);
              setReviewHighlights([]);
            }}
            loading={confirmLoading}
            error={confirmError}
            isConfirmed={isTaskConfirmed}
          />
        )}

        {/* ── Chat Stream (Scrollable message history) ──────────────────── */}
        <main
          className="chat-stream-card"
          ref={chatStreamRef}
          aria-label={`Conversation history for ${activeMeeting?.title || 'meeting'}`}
          tabIndex={0}
        >
          {chatLoading && messages.length === 0 ? (
            <div className="chat-stream-loading" aria-label="Loading conversation history">
              <TypingIndicator label="Loading meeting conversation..." />
            </div>
          ) : messages.length === 0 ? (
            /* Empty conversation welcome state */
            <div className="chat-conversation-empty">
              <div className="chat-conversation-empty-icon" aria-hidden="true">
                <Sparkles size={32} />
              </div>
              <h2 className="chat-conversation-empty-title">
                Ask anything about {activeMeeting?.title || 'this meeting'}
              </h2>
              <p className="chat-conversation-empty-desc">
                MeetMind AI will search the transcript, attribute speakers, and answer your questions directly with grounded citations.
              </p>

              {/* Suggested prompt chips */}
              <div className="chat-suggested-prompts" aria-label="Suggested questions">
                {SUGGESTED_PROMPTS.map((prompt, pIdx) => (
                  <button
                    key={pIdx}
                    type="button"
                    className="chat-suggested-prompt-chip"
                    onClick={() => handleSendMessage(prompt)}
                    aria-label={`Ask: ${prompt}`}
                  >
                    <HelpCircle size={14} aria-hidden="true" />
                    <span>{prompt}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            /* Rendered message bubbles */
            <div className="chat-messages-list" role="log" aria-live="polite">
              {messages.map((msg) => (
                <ChatBubble
                  key={msg.id}
                  message={msg}
                  isOptimistic={msg.isOptimistic}
                />
              ))}

              {/* Thinking Indicator when awaiting AI answer */}
              {isThinking && (
                <div className="chat-thinking-row" aria-live="polite">
                  <div className="chat-bubble-avatar ai-avatar" aria-hidden="true">
                    <Sparkles size={16} />
                  </div>
                  <TypingIndicator label="Searching transcript & generating answer..." />
                </div>
              )}

              <div ref={messagesEndRef} aria-hidden="true" style={{ height: 1 }} />
            </div>
          )}
        </main>

        {/* ── Chat Input Bar (Sticky at bottom) ──────────────────────────── */}
        <ChatInput
          onSendMessage={handleSendMessage}
          disabled={isThinking || !activeMeetingId}
          placeholder={
            isThinking
              ? 'MeetMind AI is generating an answer...'
              : `Ask a question about ${activeMeeting?.title || 'this meeting'}...`
          }
        />
      </div>

      {/* ── Task Extraction Modal (Explicit participant name required) ──── */}
      <TaskExtractionModal
        isOpen={isExtractionModalOpen}
        onClose={() => setIsExtractionModalOpen(false)}
        onRunExtraction={handleRunExtraction}
        meetingTitle={activeMeeting?.title || 'this meeting'}
        loading={extractionLoading}
        error={extractionError}
      />
    </div>
  );
}

export default Chat;
