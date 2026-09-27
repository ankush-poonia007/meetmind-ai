/**
 * StatCard — Workspace Dashboard Statistic Card Component (Section 8 Line 550)
 * Renders an icon, large numerical value with accent color, and descriptive label.
 *
 * @param {object} props
 * @param {React.ComponentType} props.icon - Lucide icon component
 * @param {number | string} props.value - Count or numerical metric
 * @param {string} props.label - Small descriptive label
 * @param {string} [props.className=''] - Optional additional classes
 */
function StatCard({ icon: Icon, value, label, className = '' }) {
  return (
    <div className={`card stat-card ${className}`.trim()} aria-label={`${label}: ${value}`}>
      {Icon && (
        <div className="stat-card-icon-wrapper" aria-hidden="true">
          <Icon size={22} className="stat-card-icon" />
        </div>
      )}
      <div className="stat-card-content">
        <div className="stat-card-value">{value}</div>
        <div className="stat-card-label">{label}</div>
      </div>
    </div>
  );
}

export default StatCard;
