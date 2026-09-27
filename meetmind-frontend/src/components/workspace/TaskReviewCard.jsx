import { useState } from 'react';
import {
  CheckSquare,
  Square,
  Calendar,
  AlertTriangle,
  CheckCircle2,
  Edit2,
  Save,
  Check,
  X,
  Sparkles,
  Loader2,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import Badge from '../ui/Badge';

/**
 * TaskReviewCard — Interactive Task Review, Editing & Confirmation Panel (Phase E & Batch 6.1)
 *
 * Requirements:
 * - Inclusion checkbox (include/exclude per task).
 * - Editable task description.
 * - Editable task deadline (date input).
 * - Priority badge and confidence score display.
 * - Confirm & Save to Dashboard action button.
 * - Excluded tasks omitted from confirmation payload.
 *
 * @param {object} props
 * @param {Array<object>} props.tasks - Extracted task items awaiting confirmation
 * @param {Array<object>} [props.highlights=[]] - Extracted highlights
 * @param {string} [props.targetName=''] - Target participant name entered explicitly
 * @param {Function} props.onConfirmTasks - Callback ({ user_confirmation, confirmed_task_ids, modified_tasks }) => Promise<void>
 * @param {Function} [props.onDiscard] - Callback when user explicitly discards all tasks
 * @param {boolean} [props.loading=false] - In-flight confirmation state
 * @param {string|null} [props.error=null] - Confirmation error banner
 * @param {boolean} [props.isConfirmed=false] - Whether tasks were successfully confirmed
 */
function TaskReviewCard({
  tasks = [],
  highlights = [],
  targetName = '',
  onConfirmTasks,
  onDiscard,
  loading = false,
  error = null,
  isConfirmed = false,
}) {
  // Initialize local editable state for each task
  const [taskState, setTaskState] = useState(() =>
    tasks.map((task, idx) => ({
      id: task.id || `task-${idx}`,
      originalIndex: idx,
      title: task.title,
      description: task.description || '',
      deadline: task.deadline ? task.deadline.split('T')[0] : '',
      priority: task.priority || 'medium',
      confidence_score: task.confidence_score,
      included: true,
      isEditing: false,
    }))
  );

  const [expandedHighlights, setExpandedHighlights] = useState(false);

  // Toggle inclusion of an individual task
  const handleToggleInclude = (idx) => {
    setTaskState((prev) =>
      prev.map((t, i) => (i === idx ? { ...t, included: !t.included } : t))
    );
  };

  // Select / Deselect All
  const handleToggleAll = (select) => {
    setTaskState((prev) => prev.map((t) => ({ ...t, included: select })));
  };

  // Update description or deadline
  const handleFieldChange = (idx, field, value) => {
    setTaskState((prev) =>
      prev.map((t, i) => (i === idx ? { ...t, [field]: value } : t))
    );
  };

  const selectedCount = taskState.filter((t) => t.included).length;
  const totalCount = taskState.length;

  const handleConfirm = () => {
    const includedTasks = taskState.filter((t) => t.included);
    if (includedTasks.length === 0) {
      if (onDiscard) onDiscard();
      return;
    }

    const allSelected = includedTasks.length === totalCount;
    const userConfirmation = allSelected ? 'yes' : 'partial';

    // Prepare confirmed identifiers or indices
    const confirmedTaskIds = includedTasks.map((t) => String(t.originalIndex));

    // Prepare modified task objects with edited descriptions and deadlines
    const modifiedTasks = includedTasks.map((t) => ({
      title: t.title,
      description: t.description,
      deadline: t.deadline || null,
      priority: t.priority,
      confidence_score: t.confidence_score,
    }));

    onConfirmTasks({
      user_confirmation: userConfirmation,
      confirmed_task_ids: confirmedTaskIds,
      modified_tasks: modifiedTasks,
    });
  };

  if (isConfirmed) {
    return (
      <div className="task-review-card is-success" role="status" aria-live="polite">
        <div className="task-review-success-header">
          <CheckCircle2 size={24} className="text-status-low" aria-hidden="true" />
          <div>
            <h3 className="task-review-title">Tasks Confirmed &amp; Saved</h3>
            <p className="task-review-subtitle">
              Action items for <strong>{targetName || 'participant'}</strong> have been saved to your workspace dashboard.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <section className="task-review-card" aria-label="Extracted task review and editing">
      {/* ── Card Header ─────────────────────────────────────────────────── */}
      <div className="task-review-header">
        <div className="task-review-title-group">
          <div className="task-review-icon" aria-hidden="true">
            <Sparkles size={18} />
          </div>
          <div>
            <h3 className="task-review-title">
              Extracted Action Items
              {targetName && <span className="task-review-target"> &mdash; {targetName}</span>}
            </h3>
            <p className="task-review-subtitle">
              Review, edit descriptions or deadlines, and select tasks to confirm.
            </p>
          </div>
        </div>

        {/* Inclusion Summary Badge & Bulk Toggles */}
        <div className="task-review-selection-controls">
          <span className="task-selection-count">
            {selectedCount} of {totalCount} selected
          </span>
          <div className="task-selection-bulk-buttons">
            <button
              type="button"
              className="btn-link-action"
              onClick={() => handleToggleAll(true)}
              disabled={loading || selectedCount === totalCount}
            >
              Select All
            </button>
            <span className="btn-link-sep" aria-hidden="true">|</span>
            <button
              type="button"
              className="btn-link-action"
              onClick={() => handleToggleAll(false)}
              disabled={loading || selectedCount === 0}
            >
              Deselect All
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="task-review-alert-error" role="alert">
          <AlertTriangle size={16} aria-hidden="true" style={{ flexShrink: 0 }} />
          <span>{error}</span>
        </div>
      )}

      {/* ── Tasks Review List ───────────────────────────────────────────── */}
      <ul className="task-review-list" aria-label="Extracted tasks list">
        {taskState.map((task, idx) => {
          const confidencePct =
            task.confidence_score != null
              ? Math.round(task.confidence_score * 100)
              : null;

          return (
            <li
              key={task.id}
              className={`task-review-item ${task.included ? 'is-included' : 'is-excluded'}`}
            >
              {/* Checkbox */}
              <div className="task-review-item-checkbox">
                <button
                  type="button"
                  className="checkbox-btn"
                  onClick={() => handleToggleInclude(idx)}
                  disabled={loading}
                  aria-label={`${task.included ? 'Exclude' : 'Include'} task: ${task.title}`}
                  aria-checked={task.included}
                  role="checkbox"
                >
                  {task.included ? (
                    <CheckSquare size={20} className="checkbox-icon checked" />
                  ) : (
                    <Square size={20} className="checkbox-icon" />
                  )}
                </button>
              </div>

              {/* Task Details and Inline Inputs */}
              <div className="task-review-item-body">
                <div className="task-review-item-top">
                  <span className="task-review-item-title">
                    {task.title}
                  </span>

                  <div className="task-review-item-badges">
                    <Badge variant={task.priority}>
                      {task.priority}
                    </Badge>
                    {confidencePct != null && (
                      <span
                        className="task-confidence-chip"
                        title={`Extraction confidence: ${confidencePct}%`}
                      >
                        {confidencePct}% conf
                      </span>
                    )}
                  </div>
                </div>

                {/* Editable Description */}
                <div className="task-review-field-group">
                  <label htmlFor={`task-desc-${idx}`} className="task-field-label">
                    Description:
                  </label>
                  <textarea
                    id={`task-desc-${idx}`}
                    className="task-field-textarea"
                    rows={2}
                    value={task.description}
                    onChange={(e) => handleFieldChange(idx, 'description', e.target.value)}
                    disabled={loading || !task.included}
                    placeholder="Enter task details..."
                  />
                </div>

                {/* Editable Deadline Date Picker */}
                <div className="task-review-field-group task-deadline-row">
                  <label htmlFor={`task-deadline-${idx}`} className="task-field-label">
                    <Calendar size={13} aria-hidden="true" />
                    Deadline:
                  </label>
                  <input
                    type="date"
                    id={`task-deadline-${idx}`}
                    className="task-field-date-input"
                    value={task.deadline}
                    onChange={(e) => handleFieldChange(idx, 'deadline', e.target.value)}
                    disabled={loading || !task.included}
                  />
                </div>
              </div>
            </li>
          );
        })}
      </ul>

      {/* ── Extracted Highlights Accordion (Optional auxiliary data) ────── */}
      {highlights.length > 0 && (
        <div className="task-review-highlights-section">
          <button
            type="button"
            className="highlights-accordion-toggle"
            onClick={() => setExpandedHighlights((prev) => !prev)}
            aria-expanded={expandedHighlights}
          >
            <span>{highlights.length} Extracted Highlight{highlights.length !== 1 ? 's' : ''}</span>
            {expandedHighlights ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>

          {expandedHighlights && (
            <ul className="review-highlights-list">
              {highlights.map((h, hIdx) => (
                <li key={hIdx} className="review-highlight-item">
                  <p className="review-highlight-text">{h.content}</p>
                  {h.relevance_reason && (
                    <span className="review-highlight-reason">Why: {h.relevance_reason}</span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* ── Card Action Footer ──────────────────────────────────────────── */}
      <div className="task-review-footer">
        {onDiscard && (
          <button
            type="button"
            className="btn-secondary btn-discard-review"
            onClick={onDiscard}
            disabled={loading}
          >
            Discard All
          </button>
        )}

        <button
          type="button"
          className="btn-primary btn-confirm-tasks"
          onClick={handleConfirm}
          disabled={loading || selectedCount === 0}
          id="confirm-save-tasks-btn"
        >
          {loading ? (
            <>
              <Loader2 size={16} className="spinner-icon" aria-hidden="true" />
              Saving to Dashboard...
            </>
          ) : (
            <>
              <Check size={16} aria-hidden="true" />
              Confirm &amp; Save ({selectedCount}) to Dashboard
            </>
          )}
        </button>
      </div>
    </section>
  );
}

export default TaskReviewCard;
