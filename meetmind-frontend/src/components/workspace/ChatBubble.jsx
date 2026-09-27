import { useState } from 'react';
import { Bot, User, ChevronRight, ChevronDown, Quote, Sparkles } from 'lucide-react';

/**
 * Helper to format ISO timestamp to short local time (e.g. "14:32" or "2:32 PM").
 */
function formatMessageTime(dateString) {
  if (!dateString) return '';
  try {
    const d = new Date(dateString);
    if (isNaN(d.getTime())) return '';
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}

/**
 * ChatBubble — User and Assistant Message Bubble (Section 8 Sub-View 4 & Batch 6.1)
 *
 * Requirements:
 * - User messages: right-aligned, vivid blue background (#266FF2), white text.
 * - AI messages: left-aligned, soft white card surface (#FFFFFF), subtle border (#E3E8ED).
 * - Source citations: speaker name, timestamp, and expandable verbatim transcript excerpt.
 *
 * @param {object} props
 * @param {object} props.message
 * @param {'user'|'assistant'} props.message.role
 * @param {string} props.message.content
 * @param {string} [props.message.created_at]
 * @param {Array<object>} [props.message.sources] - Citations attached to AI response
 * @param {'high'|'medium'|'low'} [props.message.confidence]
 * @param {boolean} [props.isOptimistic=false]
 */
function ChatBubble({ message, isOptimistic = false }) {
  const isUser = message.role === 'user';
  const [expandedSources, setExpandedSources] = useState(false);

  const sources = Array.isArray(message.sources) ? message.sources : [];
  const hasSources = sources.length > 0;
  const timeFormatted = formatMessageTime(message.created_at);

  return (
    <article
      className={`chat-bubble-row ${isUser ? 'is-user' : 'is-ai'}`}
      aria-label={`${isUser ? 'You' : 'MeetMind AI'} said:`}
    >
      <div className="chat-bubble-avatar" aria-hidden="true">
        {isUser ? <User size={16} /> : <Bot size={16} />}
      </div>

      <div className="chat-bubble-content-col">
        {/* Author & Timestamp Header */}
        <div className="chat-bubble-header">
          <span className="chat-bubble-author">
            {isUser ? 'You' : 'MeetMind AI'}
          </span>
          {timeFormatted && (
            <time className="chat-bubble-time" dateTime={message.created_at}>
              {timeFormatted}
            </time>
          )}
          {isOptimistic && (
            <span className="chat-bubble-sending-badge">Sending...</span>
          )}
          {!isUser && message.confidence && (
            <span
              className={`chat-confidence-badge confidence-${message.confidence}`}
              title={`Answer grounding confidence: ${message.confidence}`}
            >
              {message.confidence} confidence
            </span>
          )}
        </div>

        {/* Message Bubble Surface */}
        <div className={`chat-bubble-body ${isUser ? 'bubble-user' : 'bubble-ai'}`}>
          <div className="chat-message-text">
            {message.content.split('\n\n').map((paragraph, idx) => (
              <p key={idx}>{paragraph}</p>
            ))}
          </div>

          {/* ── Grounding Source Citations (AI only) ───────────────────────── */}
          {!isUser && hasSources && (
            <div className="chat-sources-container">
              <button
                type="button"
                className="chat-sources-toggle"
                onClick={() => setExpandedSources((prev) => !prev)}
                aria-expanded={expandedSources}
                aria-label={`Toggle ${sources.length} transcript source citations`}
              >
                <Quote size={13} className="chat-sources-icon" aria-hidden="true" />
                <span className="chat-sources-toggle-label">
                  {sources.length} Source{sources.length !== 1 ? 's' : ''} Cited:
                  {' '}
                  {sources
                    .map((s) => s.speaker ? `${s.speaker}${s.timestamp ? ` (${s.timestamp})` : ''}` : s.timestamp || 'Transcript')
                    .slice(0, 2)
                    .join(', ')}
                  {sources.length > 2 ? `, +${sources.length - 2} more` : ''}
                </span>
                {expandedSources ? (
                  <ChevronDown size={14} aria-hidden="true" />
                ) : (
                  <ChevronRight size={14} aria-hidden="true" />
                )}
              </button>

              {expandedSources && (
                <ul className="chat-sources-list">
                  {sources.map((src, sIdx) => (
                    <li key={sIdx} className="chat-source-item">
                      <div className="chat-source-meta">
                        <span className="chat-source-speaker">
                          {src.speaker || 'Speaker'}
                        </span>
                        {src.timestamp && (
                          <span className="chat-source-timestamp">
                            {src.timestamp}
                          </span>
                        )}
                      </div>
                      <blockquote className="chat-source-excerpt">
                        &ldquo;{src.excerpt}&rdquo;
                      </blockquote>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      </div>
    </article>
  );
}

export default ChatBubble;
