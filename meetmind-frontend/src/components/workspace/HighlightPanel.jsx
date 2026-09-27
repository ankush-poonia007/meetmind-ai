import { Link } from 'react-router-dom';
import Badge from '../ui/Badge';
import { formatShortDate } from '../../utils/formatDate';

/**
 * HighlightPanel — Dashboard Recent Highlights Panel (Section 8 Line 561)
 * Displays extracted meeting highlights (max 8) with meeting name, text, date chip,
 * and a "View all" link to /workspace/meetings.
 *
 * @param {object} props
 * @param {Array<{ id: string | number, meetingTitle: string, text: string, date: string }>} [props.highlights=[]]
 * @param {boolean} [props.loading=false]
 * @param {string | null} [props.error=null]
 * @param {string} [props.className='']
 */
function HighlightPanel({ highlights = [], loading = false, error = null, className = '' }) {
  // Enforce maximum 8 highlights per design specification
  const displayedHighlights = highlights.slice(0, 8);

  return (
    <section
      className={`card highlight-panel ${className}`.trim()}
      aria-labelledby="highlights-panel-title"
    >
      <div className="highlight-panel-header">
        <h2 className="highlight-panel-title" id="highlights-panel-title">
          Recent Highlights
        </h2>
      </div>

      {loading ? (
        <div className="highlight-skeleton-list" aria-label="Loading highlights">
          <div className="skeleton highlight-skeleton-item" />
          <div className="skeleton highlight-skeleton-item" />
          <div className="skeleton highlight-skeleton-item" />
        </div>
      ) : error ? (
        <p className="section-error-message" role="alert">
          {error}
        </p>
      ) : displayedHighlights.length === 0 ? (
        <p className="panel-empty-text">No recent highlights.</p>
      ) : (
        <ul className="highlight-list" role="list">
          {displayedHighlights.map((item) => (
            <li key={item.id} className="highlight-item">
              <div className="highlight-meta">
                <span className="highlight-meeting-name">
                  {item.meetingTitle || 'Meeting'}
                </span>
                <Badge variant="pending">
                  {formatShortDate(item.date, 'Recent')}
                </Badge>
              </div>
              <p className="highlight-text">{item.text}</p>
            </li>
          ))}
        </ul>
      )}

      <div className="highlight-footer">
        <Link
          to="/workspace/meetings"
          className="highlight-view-all"
          aria-label="View all meeting highlights in meetings view"
        >
          View all &rarr;
        </Link>
      </div>
    </section>
  );
}

export default HighlightPanel;

