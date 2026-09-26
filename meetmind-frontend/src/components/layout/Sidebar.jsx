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
import { useAuth } from '../../hooks/useAuth';
import { useAuthModal } from '../../context/AuthModalContext';

/**
 * Sidebar — MeetMind AI Main Navigation Sidebar
 * Deep Muted Slate Blue sidebar with subtle glossy finish.
 * Fixed 240px default width on desktop with horizontal resize support.
 * Collapses to 48px icons on viewports strictly < 768px.
 *
 * Features:
 * - Brand logo with SVG mark and serif typography
 * - Primary navigation links with active state indicator
 * - Persistent workspace subnavigation with smooth height and opacity transitions
 * - Interactive right-edge resize handle with keyboard accessibility & persistence
 * - Responsive tooltip labels in collapsed view
 * - Accessible footer with versioning and repository links
 */
function Sidebar({
  width = 240,
  onWidthChange,
  minWidth = 200,
  maxWidth = 420,
  defaultWidth = 240,
  isResizing = false,
  setIsResizing,
}) {
  const location = useLocation();
  const isWorkspace = location.pathname.startsWith('/workspace');
  const { isAuthenticated } = useAuth();
  const { openAuthModal } = useAuthModal();

  const handleWorkspaceClick = (e) => {
    if (!isAuthenticated) {
      e.preventDefault();
      openAuthModal('login');
    }
  };

  /* ── Mouse Drag Resize Handlers ────────────────────────────────────────── */
  const handleMouseDown = (e) => {
    if (e.button !== 0 || !onWidthChange) return;
    e.preventDefault();
    if (setIsResizing) setIsResizing(true);

    const startX = e.clientX;
    const startWidth = width;

    const handleMouseMove = (moveEvent) => {
      const deltaX = moveEvent.clientX - startX;
      const newWidth = Math.min(Math.max(startWidth + deltaX, minWidth), maxWidth);
      onWidthChange(newWidth);
    };

    const handleMouseUp = () => {
      if (setIsResizing) setIsResizing(false);
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.removeProperty('cursor');
      document.body.style.removeProperty('user-select');
    };

    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  };

  /* ── Keyboard Accessibility Handlers ───────────────────────────────────── */
  const handleKeyDown = (e) => {
    if (!onWidthChange) return;
    const step = e.shiftKey ? 20 : 10;

    if (e.key === 'ArrowLeft') {
      e.preventDefault();
      onWidthChange(Math.max(width - step, minWidth));
    } else if (e.key === 'ArrowRight') {
      e.preventDefault();
      onWidthChange(Math.min(width + step, maxWidth));
    } else if (e.key === 'Home') {
      e.preventDefault();
      onWidthChange(minWidth);
    } else if (e.key === 'End') {
      e.preventDefault();
      onWidthChange(maxWidth);
    } else if (e.key === 'Enter' || e.key === 'Escape') {
      e.preventDefault();
      onWidthChange(defaultWidth);
    }
  };

  return (
    <aside
      className={`sidebar ${isResizing ? 'is-resizing' : ''}`}
      aria-label="Application navigation"
    >
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
        <SidebarLink
          to="/workspace"
          label="Workspace"
          icon={LayoutDashboard}
          end={false}
          onClick={handleWorkspaceClick}
        />
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
            onClick={handleWorkspaceClick}
          />
          <SidebarLink
            to="/workspace/meetings"
            label="Meetings"
            icon={MessageSquare}
            tabIndex={isWorkspace ? 0 : -1}
            onClick={handleWorkspaceClick}
          />
          <SidebarLink
            to="/workspace/tasks"
            label="Tasks"
            icon={CheckSquare}
            tabIndex={isWorkspace ? 0 : -1}
            onClick={handleWorkspaceClick}
          />
          <SidebarLink
            to="/workspace/chat"
            label="Chat"
            icon={Bot}
            tabIndex={isWorkspace ? 0 : -1}
            onClick={handleWorkspaceClick}
          />
        </div>
      </div>

      {/* ── Sidebar Footer ────────────────────────────────────────────── */}
      <SidebarFooter />

      {/* ── Desktop Resizable Edge Handle ────────────────────────────── */}
      <div
        className={`sidebar-resize-handle ${isResizing ? 'is-resizing' : ''}`}
        role="separator"
        tabIndex={0}
        aria-label="Resize sidebar"
        aria-orientation="vertical"
        aria-valuenow={width}
        aria-valuemin={minWidth}
        aria-valuemax={maxWidth}
        onMouseDown={handleMouseDown}
        onKeyDown={handleKeyDown}
        title="Drag to resize sidebar (or use Left/Right arrow keys)"
      >
        <div className="sidebar-resize-handle-line" aria-hidden="true" />
      </div>
    </aside>
  );
}

export default Sidebar;
