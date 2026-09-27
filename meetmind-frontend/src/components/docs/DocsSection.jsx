/**
 * DocsSection — Reusable Documentation Section Wrapper (Section 9 Line 735)
 *
 * Consistent pattern:
 * - [LABEL] small caps accent above
 * - [H2] section title
 * - Body text (2-3 short paragraphs)
 * - Dedicated visual element slot (table, diagram, tech cards, etc.)
 *
 * @param {object} props
 * @param {string} props.id - Unique DOM anchor ID for navigation
 * @param {string} [props.label] - Uppercase category label
 * @param {string} props.title - Main H2 section title
 * @param {React.ReactNode} [props.children] - Descriptive paragraphs / body content
 * @param {React.ReactNode} [props.visual] - Visual component slot
 * @param {string} [props.className='']
 */
function DocsSection({
  id,
  label,
  title,
  children,
  visual,
  className = '',
}) {
  return (
    <section
      id={id}
      className={`docs-section ${className}`.trim()}
      aria-labelledby={`${id}-heading`}
    >
      <div className="docs-section-header">
        {label && <p className="docs-section-label">{label}</p>}
        <h2 id={`${id}-heading`} className="docs-section-title">
          {title}
        </h2>
      </div>

      <div className="docs-section-body">
        {children}
      </div>

      {visual && (
        <div className="docs-section-visual">
          {visual}
        </div>
      )}
    </section>
  );
}

export default DocsSection;
