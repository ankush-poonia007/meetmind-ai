import { useState, useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './components/layout/Sidebar';
import AuthModal from './components/auth/AuthModal';

const DEFAULT_SIDEBAR_WIDTH = 240;
const MIN_SIDEBAR_WIDTH = 200;
const MAX_SIDEBAR_WIDTH = 420;
const COLLAPSED_SIDEBAR_WIDTH = 64;

/**
 * App — Root Application Shell (Gate 2 & Batch 5.2 UI Refinement)
 * Integrates the fixed left sidebar and the main content area.
 * Supports interactive desktop sidebar width resizing and full desktop collapse/expand
 * with localStorage persistence.
 */
function App() {
  const [sidebarWidth, setSidebarWidth] = useState(() => {
    try {
      const saved = localStorage.getItem('meetmind_sidebar_width');
      const parsed = parseInt(saved, 10);
      return !isNaN(parsed) && parsed >= MIN_SIDEBAR_WIDTH && parsed <= MAX_SIDEBAR_WIDTH
        ? parsed
        : DEFAULT_SIDEBAR_WIDTH;
    } catch {
      return DEFAULT_SIDEBAR_WIDTH;
    }
  });

  const [isCollapsed, setIsCollapsed] = useState(() => {
    try {
      return localStorage.getItem('meetmind_sidebar_collapsed') === 'true';
    } catch {
      return false;
    }
  });

  const [isResizing, setIsResizing] = useState(false);

  useEffect(() => {
    try {
      localStorage.setItem('meetmind_sidebar_width', sidebarWidth.toString());
    } catch {
      // storage unavailable or quota exceeded
    }
  }, [sidebarWidth]);

  useEffect(() => {
    try {
      localStorage.setItem('meetmind_sidebar_collapsed', isCollapsed.toString());
    } catch {
      // storage unavailable or quota exceeded
    }
  }, [isCollapsed]);

  const handleToggleCollapse = () => {
    setIsCollapsed((prev) => !prev);
  };

  const effectiveWidth = isCollapsed ? COLLAPSED_SIDEBAR_WIDTH : sidebarWidth;

  return (
    <div
      className={`app-layout ${isResizing ? 'is-resizing' : ''} ${isCollapsed ? 'is-sidebar-collapsed' : ''}`}
      style={{ '--sidebar-width': `${effectiveWidth}px` }}
    >
      <Sidebar
        width={effectiveWidth}
        onWidthChange={setSidebarWidth}
        minWidth={MIN_SIDEBAR_WIDTH}
        maxWidth={MAX_SIDEBAR_WIDTH}
        defaultWidth={DEFAULT_SIDEBAR_WIDTH}
        isResizing={isResizing}
        setIsResizing={setIsResizing}
        isCollapsed={isCollapsed}
        onToggleCollapse={handleToggleCollapse}
      />
      <main className="main-content" id="main-content" tabIndex="-1">
        <Outlet />
      </main>
      <AuthModal />
    </div>
  );
}

export default App;
