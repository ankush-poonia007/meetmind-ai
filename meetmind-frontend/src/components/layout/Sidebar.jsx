import { Link, useLocation } from 'react-router-dom';
import {
  Home,
  LayoutDashboard,
  BookOpen,
  Mail,
  BarChart2,
  MessageSquare,
  CheckSquare,
  Bot,
} from 'lucide-react';
import SidebarLink from './SidebarLink';
import SidebarFooter from './SidebarFooter';

/**
 * Sidebar — MeetMind AI Main Navigation Sidebar
 * Fixed 240px wide sidebar on desktop, collapsing to 48px icons on viewports strictly < 768px.
 * Features:
 * - Brand logo with SVG mark and serif typography
 * - Primary navigation links with active state indicator
 * - Persistent workspace subnavigation with smooth height and opacity transitions
 * - Responsive tooltip labels in collapsed view
 * - Accessible footer with versioning and repository link
 */
function Sidebar() {
  const location = useLocation();
  const isWorkspace = location.pathname.startsWith('/workspace');

  return (
    <aside className="sidebar" aria-label="Application navigation">
      {/* ── Brand Logo Header ─────────────────────────────────────────── */}
      <div className="sidebar-header">
        <Link to="/" className="sidebar-logo" aria-label="MeetMind Home">
          <svg
            className="sidebar-logo-icon"
            width="28"
            height="28"
            viewBox="0 0 32 32"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            aria-hidden="true"
          >
            <rect width="32" height="32" rx="8" fill="var(--color-accent-primary)" />
            <path
              d="M6 8C6 6.895 6.895 6 8 6H16C17.105 6 18 6.895 18 8V16C18 17.105 17.105 18 16 18H10L6 22V8Z"
              fill="white"
              opacity="0.95"
            />
            <path
              d="M14 12C14 10.895 14.895 10 16 10H24C25.105 10 26 10.895 26 12V20C26 21.105 25.105 22 24 22H22L18 26V12Z"
              fill="white"
              opacity="0.7"
            />
          </svg>
          <span className="sidebar-logo-text sidebar-label">MeetMind</span>
        </Link>
      </div>

      {/* ── Primary Navigation ────────────────────────────────────────── */}
      <nav className="sidebar-nav" aria-label="Primary navigation">
        <SidebarLink to="/" label="Home" icon={Home} end={true} />
        <SidebarLink to="/workspace" label="Workspace" icon={LayoutDashboard} end={false} />
        <SidebarLink to="/docs" label="Documentation" icon={BookOpen} end={true} />
        <SidebarLink to="/contact" label="Contact" icon={Mail} end={true} />
      </nav>

      {/* ── Section Divider ───────────────────────────────────────────── */}
      <div className="sidebar-divider" role="separator" aria-hidden="true" />

      {/* ── Workspace Sub-Navigation (Expanded on /workspace/*) ───────── */}
      <div
        className={`sidebar-workspace-nav ${isWorkspace ? 'is-expanded' : ''}`}
        id="sidebar-workspace-navigation"
        aria-label="Workspace sub-navigation"
        aria-expanded={isWorkspace}
        aria-hidden={!isWorkspace}
      >
        <div className="sidebar-workspace-nav-inner">
          <div className="sidebar-section-title sidebar-label">Workspace</div>
          <SidebarLink
            to="/workspace/dashboard"
            label="Dashboard"
            icon={BarChart2}
            tabIndex={isWorkspace ? 0 : -1}
          />
          <SidebarLink
            to="/workspace/meetings"
            label="Meetings"
            icon={MessageSquare}
            tabIndex={isWorkspace ? 0 : -1}
          />
          <SidebarLink
            to="/workspace/tasks"
            label="Tasks"
            icon={CheckSquare}
            tabIndex={isWorkspace ? 0 : -1}
          />
          <SidebarLink
            to="/workspace/chat"
            label="Chat"
            icon={Bot}
            tabIndex={isWorkspace ? 0 : -1}
          />
        </div>
      </div>

      {/* ── Sidebar Footer ────────────────────────────────────────────── */}
      <SidebarFooter />
    </aside>
  );
}

export default Sidebar;
