import { NavLink } from 'react-router-dom';

/**
 * SidebarLink — MeetMind AI Navigation Link
 * Renders an accessible navigation link with icon, text label, active state indicator,
 * native HTML title fallback, and CSS hover tooltip for collapsed sidebar view.
 *
 * @param {string} to - Destination path
 * @param {string} label - Display text and accessible name
 * @param {React.ComponentType} icon - Lucide icon component
 * @param {boolean} [end=false] - Whether to match route strictly at end
 * @param {number} [tabIndex=0] - Keyboard navigation tabindex control
 * @param {Function} [onClick] - Optional click handler
 */
function SidebarLink({ to, label, icon: Icon, end = false, tabIndex = 0, onClick }) {
  return (
    <NavLink
      to={to}
      end={end}
      tabIndex={tabIndex}
      title={label}
      aria-label={label}
      onClick={onClick}
      className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
    >
      {Icon && <Icon className="sidebar-link-icon" size={20} aria-hidden="true" />}
      <span className="sidebar-label">{label}</span>
      <span className="sidebar-tooltip" role="tooltip" aria-hidden="true">
        {label}
      </span>
    </NavLink>
  );
}

export default SidebarLink;
