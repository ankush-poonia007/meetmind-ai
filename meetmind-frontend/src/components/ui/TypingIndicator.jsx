/**
 * TypingIndicator — Animated 3-dot pulse for chat loading state (Section 11 Line 946).
 *
 * Reuses the existing @keyframes typingDot and .typing-dot classes from animations.css.
 *
 * @param {object} props
 * @param {string} [props.label='Thinking...'] - Accessible label and optional visible hint
 * @param {string} [props.className=''] - Additional CSS classes
 */
function TypingIndicator({ label = 'Thinking...', className = '' }) {
  return (
    <div
      className={`typing-indicator-container ${className}`.trim()}
      role="status"
      aria-live="polite"
      aria-label={label}
    >
      <div className="typing-indicator-dots" aria-hidden="true">
        <span className="typing-dot" />
        <span className="typing-dot" />
        <span className="typing-dot" />
      </div>
      {label && <span className="typing-indicator-label">{label}</span>}
    </div>
  );
}

export default TypingIndicator;
