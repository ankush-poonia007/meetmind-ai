import { useState, useRef, useEffect } from 'react';
import { Send, CornerDownLeft } from 'lucide-react';

/**
 * ChatInput — Sticky Bottom Message Bar (Section 8 Sub-View 4 & Batch 6.1)
 *
 * Requirements:
 * - Auto-expanding textarea (min-height 48px, max-height 140px).
 * - Enter sends message.
 * - Shift + Enter inserts a newline.
 * - Disabled when input is empty or while a request is in progress.
 *
 * @param {object} props
 * @param {Function} props.onSendMessage - Callback receiving trimmed question string
 * @param {boolean} [props.disabled=false] - Whether sending is prohibited (in-flight request)
 * @param {string} [props.placeholder='Type your question about this meeting...']
 */
function ChatInput({
  onSendMessage,
  disabled = false,
  placeholder = 'Type your question about this meeting...',
}) {
  const [text, setText] = useState('');
  const textareaRef = useRef(null);

  // Auto-resize textarea based on scrollHeight
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    const newHeight = Math.min(Math.max(el.scrollHeight, 48), 140);
    el.style.height = `${newHeight}px`;
  }, [text]);

  const handleSubmit = (e) => {
    if (e) e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSendMessage(trimmed);
    setText('');
    if (textareaRef.current) {
      textareaRef.current.style.height = '48px';
      textareaRef.current.focus();
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const canSubmit = Boolean(text.trim()) && !disabled;

  return (
    <form className="chat-input-form" onSubmit={handleSubmit} aria-label="Ask a question">
      <div className="chat-input-wrapper">
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          rows={1}
          className="chat-textarea"
          aria-label="Message question"
          id="chat-message-input"
        />

        <button
          type="submit"
          disabled={!canSubmit}
          className="chat-send-btn"
          aria-label="Send message"
          id="chat-submit-btn"
          title="Send (Enter)"
        >
          <Send size={18} aria-hidden="true" />
        </button>
      </div>

      <div className="chat-input-hints" aria-hidden="true">
        <span>Press <kbd>Enter ↵</kbd> to send, <kbd>Shift + Enter</kbd> for newline</span>
      </div>
    </form>
  );
}

export default ChatInput;
