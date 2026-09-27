import { RotateCcw, Filter, Calendar } from 'lucide-react';

/**
 * FilterBar — Sticky Horizontal Filter Bar for Tasks Page (Section 8 Sub-View 3 / Batch 5.2)
 *
 * Implements documented filters:
 *   [Meeting ▼]  [Status ▼]  [Priority ▼]  [Role ▼]  [Deadline range]  [Clear filters]
 *
 * Sticky at the top of the tasks view, responsive across viewport sizes.
 *
 * @param {object} props
 * @param {Array<object>} props.meetings - User's meetings list ({ id, title })
 * @param {Array<string>} props.roles - Distinct roles list
 * @param {object} props.filters - Active filter values
 * @param {string} props.filters.meetingId
 * @param {string} props.filters.status
 * @param {string} props.filters.priority
 * @param {string} props.filters.role
 * @param {string} props.filters.deadlineFrom
 * @param {string} props.filters.deadlineTo
 * @param {Function} props.onFilterChange - Callback (key, value)
 * @param {Function} props.onClearFilters - Callback to reset all filters
 * @param {boolean} props.hasActiveFilters - Flag indicating whether any filter is set
 * @param {number} props.filteredCount - Number of tasks currently displayed
 * @param {number} props.totalCount - Total number of tasks available
 */
function FilterBar({
  meetings = [],
  roles = [],
  filters,
  onFilterChange,
  onClearFilters,
  hasActiveFilters = false,
  filteredCount = 0,
  totalCount = 0,
}) {
  return (
    <div className="tasks-filter-bar" role="search" aria-label="Task filters">
      <div className="filter-controls-group">
        {/* ── 1. Meeting Filter ────────────────────────────────────────── */}
        <div className="filter-control">
          <label htmlFor="filter-meeting" className="filter-label visually-hidden">
            Filter by meeting
          </label>
          <select
            id="filter-meeting"
            className={`filter-select${filters.meetingId ? ' is-filtered' : ''}`}
            value={filters.meetingId}
            onChange={(e) => onFilterChange('meetingId', e.target.value)}
            aria-label="Filter by meeting"
          >
            <option value="">All Meetings</option>
            {meetings.map((m) => (
              <option key={m.id} value={m.id}>
                {m.title || 'Untitled Meeting'}
              </option>
            ))}
          </select>
        </div>

        {/* ── 2. Status Filter ─────────────────────────────────────────── */}
        <div className="filter-control">
          <label htmlFor="filter-status" className="filter-label visually-hidden">
            Filter by status
          </label>
          <select
            id="filter-status"
            className={`filter-select${filters.status ? ' is-filtered' : ''}`}
            value={filters.status}
            onChange={(e) => onFilterChange('status', e.target.value)}
            aria-label="Filter by status"
          >
            <option value="">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="complete">Complete</option>
            <option value="expired">Expired</option>
          </select>
        </div>

        {/* ── 3. Priority Filter ───────────────────────────────────────── */}
        <div className="filter-control">
          <label htmlFor="filter-priority" className="filter-label visually-hidden">
            Filter by priority
          </label>
          <select
            id="filter-priority"
            className={`filter-select${filters.priority ? ' is-filtered' : ''}`}
            value={filters.priority}
            onChange={(e) => onFilterChange('priority', e.target.value)}
            aria-label="Filter by priority"
          >
            <option value="">All Priorities</option>
            <option value="high">High Priority</option>
            <option value="medium">Medium Priority</option>
            <option value="low">Low Priority</option>
          </select>
        </div>

        {/* ── 4. Role Filter ───────────────────────────────────────────── */}
        <div className="filter-control">
          <label htmlFor="filter-role" className="filter-label visually-hidden">
            Filter by role
          </label>
          <select
            id="filter-role"
            className={`filter-select${filters.role ? ' is-filtered' : ''}`}
            value={filters.role}
            onChange={(e) => onFilterChange('role', e.target.value)}
            aria-label="Filter by role"
          >
            <option value="">All Roles</option>
            {roles.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </div>

        {/* ── 5. Deadline Range (Two Date Inputs) ───────────────────────── */}
        <div className="filter-control filter-date-range" aria-label="Deadline date range">
          <Calendar size={14} className="filter-date-icon" aria-hidden="true" />
          <input
            id="filter-deadline-from"
            type="date"
            className={`filter-date-input${filters.deadlineFrom ? ' is-filtered' : ''}`}
            value={filters.deadlineFrom}
            onChange={(e) => onFilterChange('deadlineFrom', e.target.value)}
            title="Deadline from date"
            aria-label="Deadline from"
          />
          <span className="filter-date-separator" aria-hidden="true">
            –
          </span>
          <input
            id="filter-deadline-to"
            type="date"
            className={`filter-date-input${filters.deadlineTo ? ' is-filtered' : ''}`}
            value={filters.deadlineTo}
            onChange={(e) => onFilterChange('deadlineTo', e.target.value)}
            title="Deadline to date"
            aria-label="Deadline to"
          />
        </div>

        {/* ── 6. Clear Filters Button ──────────────────────────────────── */}
        {hasActiveFilters && (
          <button
            type="button"
            className="filter-clear-btn"
            onClick={onClearFilters}
            aria-label="Clear all applied filters"
            id="tasks-clear-filters-btn"
          >
            <RotateCcw size={13} aria-hidden="true" />
            Clear filters
          </button>
        )}
      </div>

      {/* ── Filtered count display ─────────────────────────────────────── */}
      <div className="filter-results-summary" aria-live="polite">
        {hasActiveFilters ? (
          <span className="filter-count-text">
            Showing <strong>{filteredCount}</strong> of {totalCount} tasks
          </span>
        ) : (
          <span className="filter-count-text">
            <strong>{totalCount}</strong> task{totalCount !== 1 ? 's' : ''} total
          </span>
        )}
      </div>
    </div>
  );
}

export default FilterBar;
