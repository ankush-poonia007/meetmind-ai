/**
 * DocsSidebar — Sticky Left Navigation for Documentation (Section 9 Line 707)
 *
 * Implements:
 * - Hierarchical navigation groups (Overview, Architecture, Features, Additional).
 * - Active section highlighting using IntersectionObserver data.
 * - Smooth scrolling to sections with URL hash update.
 *
 * @param {object} props
 * @param {string} props.activeId - Currently visible section ID
 * @param {Function} [props.onSelectSection] - Optional callback when user clicks a link
 */

import { DOCS_NAV_GROUPS } from '../../data/docsData.js';

export { DOCS_NAV_GROUPS };

function DocsSidebar({ activeId, onSelectSection }) {
  const handleClick = (e, targetId) => {
    e.preventDefault();
    const el = document.getElementById(targetId);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      // Update hash without jumping
      window.history.replaceState(null, '', `#${targetId}`);
    }
    if (onSelectSection) onSelectSection(targetId);
  };

  return (
    <nav className="docs-sidebar" aria-label="Documentation navigation">
      <div className="docs-sidebar-inner">
        <div className="docs-sidebar-title">Documentation</div>
        {DOCS_NAV_GROUPS.map((group) => (
          <div key={group.title} className="docs-nav-group">
            <h3 className="docs-nav-group-title">{group.title}</h3>
            <ul className="docs-nav-list">
              {group.items.map((item) => {
                const isActive = activeId === item.id;
                return (
                  <li key={item.id} className="docs-nav-item">
                    <a
                      href={`#${item.id}`}
                      className={`docs-nav-link ${isActive ? 'is-active' : ''}`}
                      onClick={(e) => handleClick(e, item.id)}
                      aria-current={isActive ? 'location' : undefined}
                    >
                      {item.label}
                    </a>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </div>
    </nav>
  );
}

export default DocsSidebar;
