import { useState, useEffect, useRef, useCallback } from 'react';
import { X, AlertCircle, Upload, FileText, CheckCircle } from 'lucide-react';
import { createMeeting, formatApiError } from '../../services/api';
import { useUser } from '../../hooks/useUser';

/**
 * Field name and accepted MIME types for each upload tab.
 */
const ACCEPTED_TYPES = {
  txt: { mime: 'text/plain', ext: '.txt', label: 'TXT' },
  pdf: { mime: 'application/pdf', ext: '.pdf', label: 'PDF' },
};

const TABS = [
  { id: 'paste', label: 'Paste Text' },
  { id: 'txt', label: 'Upload TXT' },
  { id: 'pdf', label: 'Upload PDF' },
];

const getTodayDate = () => new Date().toISOString().split('T')[0];

const INITIAL_FORM = {
  full_name: '',
  email: '',
  role: '',
  title: '',
  organization: '',
  date: '',
  time: '',
  transcript_text: '',
};

const INITIAL_ERRORS = {
  full_name: '',
  email: '',
  role: '',
  organization: '',
  date: '',
  transcript: '',
};

/**
 * Extracts plain text content from an uploaded TXT or PDF file.
 *
 * @param {File} file
 * @param {'txt' | 'pdf'} type
 * @returns {Promise<string>}
 */
async function extractTextFromFile(file, type) {
  if (type === 'txt') {
    return await file.text();
  }
  if (type === 'pdf') {
    const buffer = await file.arrayBuffer();
    const decoder = new TextDecoder('utf-8', { fatal: false });
    const content = decoder.decode(buffer);

    // Extract text from standard PDF text operators: (string) Tj or [(string)] TJ
    const textMatches = [];
    const tjRegex = /\(([^)]+)\)\s*(?:Tj|'|")/g;
    let match;
    while ((match = tjRegex.exec(content)) !== null) {
      if (match[1].trim()) {
        textMatches.push(match[1]);
      }
    }

    const bracketRegex = /\[([^\]]+)\]\s*TJ/g;
    while ((match = bracketRegex.exec(content)) !== null) {
      const inner = match[1];
      const innerTj = /\(([^)]+)\)/g;
      let innerMatch;
      while ((innerMatch = innerTj.exec(inner)) !== null) {
        if (innerMatch[1].trim()) {
          textMatches.push(innerMatch[1]);
        }
      }
    }

    if (textMatches.length > 0) {
      return textMatches.join(' ');
    }

    // Fallback: extract printable strings of 4+ characters, ignoring PDF structural keywords
    const tokens = content.match(/[\x20-\x7E]{4,}/g);
    if (tokens && tokens.length > 0) {
      const filtered = tokens.filter(
        (t) =>
          !/^(obj|endobj|stream|endstream|xref|trailer|startxref|Type|Pages|Catalog|Font|FontDescriptor|ProcSet|MediaBox|CropBox|Resources)/i.test(
            t
          )
      );
      if (filtered.length > 0) {
        return filtered.join('\n');
      }
    }
    return content;
  }
  return await file.text();
}

/**
 * NewMeetingForm — Full-screen modal form for creating a new meeting (Section 8 Sub-View 2 / Batch 5.1).
 *
 * Implements the documented three-section form:
 *   1. Your Identity (name, email, role)
 *   2. Meeting Information (title, org, date, time)
 *   3. Transcript Submission (paste / upload TXT / upload PDF)
 *
 * Adheres strictly to backend POST /api/v1/meetings/ contract (MeetingCreate schema).
 *
 * @param {object}   props
 * @param {boolean}  props.isOpen     - Controls modal visibility
 * @param {Function} props.onClose    - Called when the modal should close
 * @param {Function} props.onSuccess  - Called with the created meeting object on success
 */
function NewMeetingForm({ isOpen, onClose, onSuccess }) {
  const { user, userId } = useUser();
  const [activeTab, setActiveTab] = useState('paste');
  const [form, setForm] = useState(INITIAL_FORM);
  const [errors, setErrors] = useState(INITIAL_ERRORS);
  const [uploadedFile, setUploadedFile] = useState(null);
  const [uploadError, setUploadError] = useState('');
  const [isDraggingOver, setIsDraggingOver] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const firstFocusableRef = useRef(null);
  const overlayRef = useRef(null);

  /* ── Reset and populate state when modal opens ────────────────────────── */
  useEffect(() => {
    if (isOpen) {
      setForm({
        full_name: user?.name || '',
        email: user?.email || '',
        role: user?.role || '',
        title: '',
        organization: user?.organization || '',
        date: getTodayDate(),
        time: '',
        transcript_text: '',
      });
      setErrors(INITIAL_ERRORS);
      setUploadedFile(null);
      setUploadError('');
      setIsDraggingOver(false);
      setSubmitting(false);
      setSubmitError('');
      setActiveTab('paste');
      // Focus first input after animation settles
      setTimeout(() => firstFocusableRef.current?.focus(), 80);
    }
  }, [isOpen, user]);

  /* ── Close on Escape ───────────────────────────────────────────────────── */
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && !submitting) onClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, submitting, onClose]);

  /* ── Prevent body scroll while open ───────────────────────────────────── */
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => { document.body.style.overflow = ''; };
  }, [isOpen]);

  /* ── Field change handler ──────────────────────────────────────────────── */
  const handleChange = (field) => (e) => {
    setForm((prev) => ({ ...prev, [field]: e.target.value }));
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: '' }));
    }
  };

  /* ── Tab switch ────────────────────────────────────────────────────────── */
  const handleTabChange = (tabId) => {
    setActiveTab(tabId);
    setUploadedFile(null);
    setUploadError('');
    setErrors((prev) => ({ ...prev, transcript: '' }));
  };

  /* ── File validation ───────────────────────────────────────────────────── */
  const validateFile = useCallback((file, tab) => {
    if (!file) return 'Please select a file.';
    const accepted = ACCEPTED_TYPES[tab];
    if (!accepted) return 'Unknown file type.';
    const hasCorrectType =
      file.type === accepted.mime ||
      file.name.toLowerCase().endsWith(accepted.ext);
    if (!hasCorrectType) {
      return `Please select a ${accepted.label} file (${accepted.ext}).`;
    }
    const maxMB = 25;
    if (file.size > maxMB * 1024 * 1024) {
      return `File must be smaller than ${maxMB} MB.`;
    }
    return '';
  }, []);

  /* ── File picker change ────────────────────────────────────────────────── */
  const handleFileChange = (e) => {
    const file = e.target.files?.[0] || null;
    if (!file) return;
    const err = validateFile(file, activeTab);
    if (err) {
      setUploadError(err);
      setUploadedFile(null);
      e.target.value = '';
      return;
    }
    setUploadedFile(file);
    setUploadError('');
    setErrors((prev) => ({ ...prev, transcript: '' }));
  };

  /* ── Drag-and-drop handlers ────────────────────────────────────────────── */
  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDraggingOver(true);
  };
  const handleDragLeave = () => setIsDraggingOver(false);
  const handleDrop = (e) => {
    e.preventDefault();
    setIsDraggingOver(false);
    const file = e.dataTransfer.files?.[0] || null;
    if (!file) return;
    const err = validateFile(file, activeTab);
    if (err) {
      setUploadError(err);
      setUploadedFile(null);
      return;
    }
    setUploadedFile(file);
    setUploadError('');
    setErrors((prev) => ({ ...prev, transcript: '' }));
  };

  const clearFile = () => {
    setUploadedFile(null);
    setUploadError('');
  };

  /* ── Overlay click to close ────────────────────────────────────────────── */
  const handleOverlayClick = (e) => {
    if (!submitting && e.target === overlayRef.current) onClose();
  };

  /* ── Validation ────────────────────────────────────────────────────────── */
  const validate = () => {
    const next = { ...INITIAL_ERRORS };
    let valid = true;

    if (!form.full_name.trim()) {
      next.full_name = 'Full name is required.';
      valid = false;
    }
    if (!form.email.trim()) {
      next.email = 'Email address is required.';
      valid = false;
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) {
      next.email = 'Please enter a valid email address.';
      valid = false;
    }
    if (!form.role.trim()) {
      next.role = 'Your role is required.';
      valid = false;
    }
    if (!form.organization.trim()) {
      next.organization = 'Organization / Team is required.';
      valid = false;
    }
    if (!form.date) {
      next.date = 'Meeting date is required.';
      valid = false;
    }

    if (activeTab === 'paste') {
      if (!form.transcript_text.trim()) {
        next.transcript = 'Please paste your transcript text.';
        valid = false;
      }
    } else {
      if (!uploadedFile) {
        next.transcript = `Please upload a ${ACCEPTED_TYPES[activeTab]?.label} file.`;
        valid = false;
      }
    }

    setErrors(next);
    return valid;
  };

  /* ── Submit handler ────────────────────────────────────────────────────── */
  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitError('');

    if (!validate()) return;

    const activeUserId = user?.id || userId;
    if (!activeUserId) {
      setSubmitError('Unable to resolve authenticated user identity. Please re-authenticate.');
      return;
    }

    setSubmitting(true);

    try {
      let rawTranscript = '';
      if (activeTab === 'paste') {
        rawTranscript = form.transcript_text.trim();
      } else if (uploadedFile) {
        rawTranscript = await extractTextFromFile(uploadedFile, activeTab);
        if (!rawTranscript || !rawTranscript.trim()) {
          throw new Error(`The uploaded ${ACCEPTED_TYPES[activeTab]?.label} file contains no readable text.`);
        }
      }

      // Backend MeetingCreate Pydantic schema
      const payload = {
        user_id: activeUserId,
        title: form.title.trim() || undefined,
        organization: form.organization.trim() || undefined,
        meeting_date: form.date || getTodayDate(),
        meeting_time: form.time ? form.time.trim() : undefined,
        input_format: activeTab === 'paste' ? 'text' : activeTab,
        raw_transcript: rawTranscript.trim(),
      };

      // Submitter participant query parameters
      const params = {};
      if (form.full_name.trim()) params.submitter_name = form.full_name.trim();
      if (form.role.trim()) params.submitter_role = form.role.trim();

      const newMeeting = await createMeeting(payload, params);
      onSuccess(newMeeting);
      onClose();
    } catch (err) {
      const formatted = formatApiError(err);
      setSubmitError(formatted.message || 'Failed to create meeting. Please check form fields and try again.');
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen) return null;

  const disabled = submitting;

  return (
    <div
      className="modal-overlay"
      ref={overlayRef}
      onClick={handleOverlayClick}
      role="dialog"
      aria-modal="true"
      aria-labelledby="new-meeting-modal-title"
    >
      <div className="modal-card">
        {/* ── Modal Header ────────────────────────────────────────────── */}
        <div className="modal-header">
          <div className="modal-title-group">
            <h2 className="modal-title" id="new-meeting-modal-title">
              New Meeting
            </h2>
            <p className="modal-subtitle">
              Add a meeting transcript to analyze and extract your tasks.
            </p>
          </div>
          <button
            type="button"
            className="modal-close-btn"
            onClick={onClose}
            disabled={disabled}
            aria-label="Close modal"
            id="new-meeting-close-btn"
          >
            <X size={16} aria-hidden="true" />
          </button>
        </div>

        {/* ── Form ────────────────────────────────────────────────────── */}
        <form className="modal-form" onSubmit={handleSubmit} noValidate>

          {/* SECTION 1 — Your Identity */}
          <div className="modal-section">
            <p className="modal-section-label">
              <span className="modal-section-label-num" aria-hidden="true">1</span>
              Your Identity
            </p>

            <div className="modal-field">
              <label className="modal-field-label" htmlFor="nm-full-name">
                Full Name <span className="modal-field-required" aria-hidden="true">*</span>
              </label>
              <input
                id="nm-full-name"
                type="text"
                className={`modal-input${errors.full_name ? ' has-error' : ''}`}
                placeholder="Your full name"
                value={form.full_name}
                onChange={handleChange('full_name')}
                disabled={disabled}
                autoComplete="name"
                ref={firstFocusableRef}
                aria-required="true"
                aria-describedby={errors.full_name ? 'nm-full-name-err' : undefined}
              />
              {errors.full_name && (
                <p className="modal-field-error" id="nm-full-name-err" role="alert">
                  {errors.full_name}
                </p>
              )}
            </div>

            <div className="modal-fields-row">
              <div className="modal-field">
                <label className="modal-field-label" htmlFor="nm-email">
                  Email Address <span className="modal-field-required" aria-hidden="true">*</span>
                </label>
                <input
                  id="nm-email"
                  type="email"
                  className={`modal-input${errors.email ? ' has-error' : ''}`}
                  placeholder="you@example.com"
                  value={form.email}
                  onChange={handleChange('email')}
                  disabled={disabled}
                  autoComplete="email"
                  aria-required="true"
                  aria-describedby={errors.email ? 'nm-email-err' : undefined}
                />
                {errors.email && (
                  <p className="modal-field-error" id="nm-email-err" role="alert">
                    {errors.email}
                  </p>
                )}
              </div>

              <div className="modal-field">
                <label className="modal-field-label" htmlFor="nm-role">
                  Your Role in Meeting <span className="modal-field-required" aria-hidden="true">*</span>
                </label>
                <input
                  id="nm-role"
                  type="text"
                  className={`modal-input${errors.role ? ' has-error' : ''}`}
                  placeholder="e.g. Project Manager"
                  value={form.role}
                  onChange={handleChange('role')}
                  disabled={disabled}
                  aria-required="true"
                  aria-describedby={errors.role ? 'nm-role-err' : undefined}
                />
                {errors.role && (
                  <p className="modal-field-error" id="nm-role-err" role="alert">
                    {errors.role}
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* SECTION 2 — Meeting Information */}
          <div className="modal-section">
            <p className="modal-section-label">
              <span className="modal-section-label-num" aria-hidden="true">2</span>
              Meeting Information
            </p>

            <div className="modal-field">
              <label className="modal-field-label" htmlFor="nm-title">
                Meeting Title
                <span className="modal-field-optional">(optional)</span>
              </label>
              <input
                id="nm-title"
                type="text"
                className="modal-input"
                placeholder="e.g. Q4 Planning Kickoff"
                value={form.title}
                onChange={handleChange('title')}
                disabled={disabled}
              />
            </div>

            <div className="modal-field">
              <label className="modal-field-label" htmlFor="nm-organization">
                Organization / Team <span className="modal-field-required" aria-hidden="true">*</span>
              </label>
              <input
                id="nm-organization"
                type="text"
                className={`modal-input${errors.organization ? ' has-error' : ''}`}
                placeholder="e.g. Acme Corp — Engineering"
                value={form.organization}
                onChange={handleChange('organization')}
                disabled={disabled}
                aria-required="true"
                aria-describedby={errors.organization ? 'nm-org-err' : undefined}
              />
              {errors.organization && (
                <p className="modal-field-error" id="nm-org-err" role="alert">
                  {errors.organization}
                </p>
              )}
            </div>

            <div className="modal-fields-row">
              <div className="modal-field">
                <label className="modal-field-label" htmlFor="nm-date">
                  Date <span className="modal-field-required" aria-hidden="true">*</span>
                </label>
                <input
                  id="nm-date"
                  type="date"
                  className={`modal-input${errors.date ? ' has-error' : ''}`}
                  value={form.date}
                  onChange={handleChange('date')}
                  disabled={disabled}
                  aria-required="true"
                  aria-describedby={errors.date ? 'nm-date-err' : undefined}
                />
                {errors.date && (
                  <p className="modal-field-error" id="nm-date-err" role="alert">
                    {errors.date}
                  </p>
                )}
              </div>

              <div className="modal-field">
                <label className="modal-field-label" htmlFor="nm-time">
                  Time
                  <span className="modal-field-optional">(optional)</span>
                </label>
                <input
                  id="nm-time"
                  type="time"
                  className="modal-input"
                  value={form.time}
                  onChange={handleChange('time')}
                  disabled={disabled}
                />
              </div>
            </div>
          </div>

          {/* SECTION 3 — Transcript Submission */}
          <div className="modal-section">
            <p className="modal-section-label">
              <span className="modal-section-label-num" aria-hidden="true">3</span>
              Transcript Submission
            </p>

            {/* Tab toggle */}
            <div
              className="transcript-tab-group"
              role="tablist"
              aria-label="Transcript submission method"
            >
              {TABS.map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  role="tab"
                  id={`nm-tab-${tab.id}`}
                  aria-selected={activeTab === tab.id}
                  aria-controls={`nm-tabpanel-${tab.id}`}
                  className={`transcript-tab-btn${activeTab === tab.id ? ' is-active' : ''}`}
                  onClick={() => handleTabChange(tab.id)}
                  disabled={disabled}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Paste Text panel */}
            {activeTab === 'paste' && (
              <div
                role="tabpanel"
                id="nm-tabpanel-paste"
                aria-labelledby="nm-tab-paste"
              >
                <textarea
                  id="nm-transcript-text"
                  className={`transcript-textarea${errors.transcript ? ' has-error' : ''}`}
                  placeholder="Paste your meeting transcript here…"
                  value={form.transcript_text}
                  onChange={(e) => {
                    setForm((prev) => ({ ...prev, transcript_text: e.target.value }));
                    if (errors.transcript) setErrors((prev) => ({ ...prev, transcript: '' }));
                  }}
                  disabled={disabled}
                  aria-required="true"
                  aria-describedby={errors.transcript ? 'nm-transcript-err' : undefined}
                />
                {errors.transcript && (
                  <p className="modal-field-error" id="nm-transcript-err" role="alert">
                    {errors.transcript}
                  </p>
                )}
              </div>
            )}

            {/* Upload TXT panel */}
            {activeTab === 'txt' && (
              <FileDropZone
                tabId="txt"
                accept=".txt,text/plain"
                label="TXT"
                uploadedFile={uploadedFile}
                uploadError={uploadError || errors.transcript}
                isDraggingOver={isDraggingOver}
                disabled={disabled}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onFileChange={handleFileChange}
                onClear={clearFile}
              />
            )}

            {/* Upload PDF panel */}
            {activeTab === 'pdf' && (
              <FileDropZone
                tabId="pdf"
                accept=".pdf,application/pdf"
                label="PDF"
                uploadedFile={uploadedFile}
                uploadError={uploadError || errors.transcript}
                isDraggingOver={isDraggingOver}
                disabled={disabled}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onFileChange={handleFileChange}
                onClear={clearFile}
              />
            )}
          </div>

          {/* ── Submit footer ──────────────────────────────────────────── */}
          <div className="modal-footer">
            {submitError && (
              <div className="modal-form-error" role="alert">
                <AlertCircle size={16} aria-hidden="true" style={{ flexShrink: 0, marginTop: 1 }} />
                {submitError}
              </div>
            )}
            <button
              type="submit"
              className="modal-submit-btn"
              disabled={disabled}
              id="new-meeting-submit-btn"
            >
              {submitting ? (
                <>
                  <span className="spinner" aria-hidden="true" />
                  Analyzing…
                </>
              ) : (
                'Create Meeting & Analyze'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ────────────────────────────────────────────────────────────────────────── */

/**
 * FileDropZone — Drag-and-drop + file picker sub-component used inside NewMeetingForm.
 * Shared between the TXT and PDF upload panels.
 */
function FileDropZone({
  tabId,
  accept,
  label,
  uploadedFile,
  uploadError,
  isDraggingOver,
  disabled,
  onDragOver,
  onDragLeave,
  onDrop,
  onFileChange,
  onClear,
}) {
  let zoneClass = 'file-drop-zone';
  if (uploadedFile) zoneClass += ' has-file';
  else if (uploadError) zoneClass += ' has-error';
  else if (isDraggingOver) zoneClass += ' is-dragging-over';

  return (
    <div
      role="tabpanel"
      id={`nm-tabpanel-${tabId}`}
      aria-labelledby={`nm-tab-${tabId}`}
    >
      <div
        className={zoneClass}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        aria-label={`Drop zone for ${label} file upload`}
      >
        <div className="file-drop-zone-icon" aria-hidden="true">
          {uploadedFile ? (
            <CheckCircle size={24} />
          ) : (
            <Upload size={24} />
          )}
        </div>

        {uploadedFile ? (
          <p className="file-drop-zone-title">File selected</p>
        ) : (
          <>
            <p className="file-drop-zone-title">
              Drag &amp; drop your {label} file here
            </p>
            <p className="file-drop-zone-desc">
              or click to browse — {label} files only, max 25 MB
            </p>
          </>
        )}

        {/* Invisible file input overlaid on the zone */}
        {!uploadedFile && (
          <input
            id={`nm-file-input-${tabId}`}
            type="file"
            accept={accept}
            className="file-drop-zone-input"
            onChange={onFileChange}
            disabled={disabled}
            aria-label={`Select ${label} file`}
          />
        )}
      </div>

      {/* Selected file info */}
      {uploadedFile && (
        <div className="file-selected-info" style={{ marginTop: 10 }}>
          <FileText size={16} style={{ color: '#15803D', flexShrink: 0 }} aria-hidden="true" />
          <span className="file-selected-name" title={uploadedFile.name}>
            {uploadedFile.name}
          </span>
          <button
            type="button"
            className="file-clear-btn"
            onClick={onClear}
            disabled={disabled}
            aria-label="Remove selected file"
          >
            <X size={14} aria-hidden="true" />
          </button>
        </div>
      )}

      {/* Validation error */}
      {uploadError && (
        <p className="modal-field-error" role="alert" style={{ marginTop: 6 }}>
          {uploadError}
        </p>
      )}
    </div>
  );
}

export default NewMeetingForm;
