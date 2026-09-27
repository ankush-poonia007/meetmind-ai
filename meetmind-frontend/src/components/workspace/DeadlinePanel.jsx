import { getRelativeDeadlineInfo, parseDate } from '../../utils/formatDate';

/**
 * DeadlinePanel — Dashboard Upcoming Deadlines Panel (Section 8 Line 567)
 * Displays tasks due within the next 3 days, sorted by deadline date ascending.
 * Each item contains a priority dot (red for today/tomorrow, amber for 2-3 days, green for later),
 * task title, and formatted deadline date.
 *
 * @param {object} props
 * @param {Array<{ id: string | number, title: string, dueDate: string, priority?: string }>} [props.deadlines=[]]
 * @param {boolean} [props.loading=false]
 * @param {string | null} [props.error=null]
 * @param {string} [props.className='']
 */
function DeadlinePanel({ deadlines = [], loading = false, error = null, className = '' }) {
  // Sort tasks by deadline date ascending
  const sortedDeadlines = [...deadlines].sort((a, b) => {
    const dateA = parseDate(a.dueDate);
    const dateB = parseDate(b.dueDate);
    if (!dateA) return 1;
    if (!dateB) return -1;
    return dateA.getTime() - dateB.getTime();
  });

  return (
    <section
      className={`card deadline-panel ${className}`.trim()}
      aria-labelledby="deadlines-panel-title"
    >
      <div className="deadline-panel-header">
        <h2 className="deadline-panel-title" id="deadlines-panel-title">
          Upcoming Deadlines
        </h2>
      </div>

      {loading ? (
        <div className="deadline-skeleton-list" aria-label="Loading upcoming deadlines">
          <div className="skeleton deadline-skeleton-item" />
          <div className="skeleton deadline-skeleton-item" />
          <div className="skeleton deadline-skeleton-item" />
        </div>
      ) : error ? (
        <p className="section-error-message" role="alert">
          {error}
        </p>
      ) : sortedDeadlines.length === 0 ? (
        <p className="panel-empty-text">No deadlines due in the next 3 days.</p>
      ) : (
        <ul className="deadline-list" role="list">
          {sortedDeadlines.map((task) => {
            const { label, priorityLevel } = getRelativeDeadlineInfo(task.dueDate);
            const dotVariantClass = `priority-dot-${priorityLevel}`;

            return (
              <li key={task.id} className="deadline-item">
                <div className="deadline-item-left">
                  <span
                    className={`priority-dot ${dotVariantClass}`}
                    aria-label={`Priority: ${priorityLevel}`}
                    title={`Priority: ${priorityLevel}`}
                  />
                  <span className="deadline-task-title" title={task.title}>
                    {task.title}
                  </span>
                </div>
                <span className="deadline-date">{label}</span>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

export default DeadlinePanel;

