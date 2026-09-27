import { useState, useEffect } from 'react';
import { X, Sparkles, UserCheck, AlertCircle, Loader2 } from 'lucide-react';

/**
 * TaskExtractionModal — Explicit-Name Task Extraction Trigger (Phase D & Batch 6.1)
 *
 * CRITICAL ARCHITECTURAL REQUIREMENT:
 * The user must explicitly enter the name of the person whose tasks should be extracted.
 * NEVER automatically prefill or fall back to the authenticated user's profile name.
 *
 * @param {object} props
 * @param {boolean} props.isOpen - Whether the modal is visible
 * @param {Function} props.onClose - Callback to close the modal
 * @param {Function} props.onRunExtraction - Async callback receiving explicitly entered name: (personName) => Promise<void>
 * @param {string} [props.meetingTitle] - Meeting title for display context
 * @param {boolean} [props.loading=false] - In-flight execution indicator
 * @param {string|null} [props.error=null] - Execution error message
 */
function TaskExtractionModal({
  isOpen,
  onClose,
  onRunExtraction,
  meetingTitle = 'this meeting',
  loading = false,
  error = null,
}) {
  const [personName, setPersonName] = useState('');
  const [validationError, setValidationError] = useState('');

  // Reset input when opening modal — never prefill with profile name
  useEffect(() => {
    if (isOpen) {
      setPersonName('');
      setValidationError('');
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    const trimmed = personName.trim();
    if (!trimmed) {
      setValidationError('Please explicitly enter the participant name whose tasks should be extracted.');
      return;
    }
    setValidationError('');
    onRunExtraction(trimmed);
  };

  return (
    <div
      className="modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="extraction-modal-title"
      onClick={(e) => {
        if (e.target === e.currentTarget && !loading) onClose();
      }}
    >
      <div className="modal-card extraction-modal-card">
        {/* Header */}
        <div className="modal-header">
          <div className="modal-header-icon-title">
            <div className="modal-icon-badge" aria-hidden="true">
              <Sparkles size={18} />
            </div>
            <div>
              <h2 className="modal-title" id="extraction-modal-title">
                Extract Participant Tasks
              </h2>
              <p className="modal-subtitle">
                Targeted AI extraction for {meetingTitle}
              </p>
            </div>
          </div>
          <button
            type="button"
            className="modal-close-btn"
            onClick={onClose}
            disabled={loading}
            aria-label="Close extraction dialog"
          >
            <X size={18} aria-hidden="true" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="extraction-modal-form">
          <div className="form-group">
            <label htmlFor="extraction-person-name" className="form-label required">
              Target Participant Name
            </label>
            <div className="input-with-icon">
              <UserCheck size={18} className="input-prefix-icon" aria-hidden="true" />
              <input
                type="text"
                id="extraction-person-name"
                className="input extraction-name-input"
                placeholder="e.g. Elena Rostova or Alex Rivera"
                value={personName}
                onChange={(e) => {
                  setPersonName(e.target.value);
                  if (validationError) setValidationError('');
                }}
                disabled={loading}
                autoFocus
                required
              />
            </div>
            <p className="form-help-text">
              Enter the exact name of the participant whose assigned tasks, mentions,
              and deadlines should be extracted from the transcript.
            </p>
            {validationError && (
              <p className="form-field-error" role="alert">
                <AlertCircle size={14} aria-hidden="true" />
                {validationError}
              </p>
            )}
          </div>

          {error && (
            <div className="modal-alert-error" role="alert">
              <AlertCircle size={16} aria-hidden="true" style={{ flexShrink: 0 }} />
              <span>{error}</span>
            </div>
          )}

          {/* Action Footer */}
          <div className="modal-footer">
            <button
              type="button"
              className="btn-secondary"
              onClick={onClose}
              disabled={loading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn-primary btn-run-extraction-submit"
              disabled={loading || !personName.trim()}
              id="confirm-run-extraction-btn"
            >
              {loading ? (
                <>
                  <Loader2 size={16} className="spinner-icon" aria-hidden="true" />
                  Extracting Tasks...
                </>
              ) : (
                <>
                  <Sparkles size={16} aria-hidden="true" />
                  Run Task Extraction
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default TaskExtractionModal;
