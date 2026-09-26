import { useState, useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './components/layout/Sidebar';
import AuthModal from './components/auth/AuthModal';

const DEFAULT_SIDEBAR_WIDTH = 240;
const MIN_SIDEBAR_WIDTH = 200;
const MAX_SIDEBAR_WIDTH = 420;

/**
 * App — Root Application Shell (Gate 2 & Batch 3.1.0)
 * Integrates the fixed left sidebar and the main content area.
 * Supports interactive desktop sidebar width resizing with localStorage persistence.
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

  const [isResizing, setIsResizing] = useState(false);

  useEffect(() => {
    try {
      localStorage.setItem('meetmind_sidebar_width', sidebarWidth.toString());
    } catch {
      // storage unavailable or quota exceeded
    }
  }, [sidebarWidth]);

  return (
    <div
      className={`app-layout ${isResizing ? 'is-resizing' : ''}`}
      style={{ '--sidebar-width': `${sidebarWidth}px` }}
    >
      <Sidebar
        width={sidebarWidth}
        onWidthChange={setSidebarWidth}
        minWidth={MIN_SIDEBAR_WIDTH}
        maxWidth={MAX_SIDEBAR_WIDTH}
        defaultWidth={DEFAULT_SIDEBAR_WIDTH}
        isResizing={isResizing}
        setIsResizing={setIsResizing}
      />
      <main className="main-content" id="main-content" tabIndex="-1">
        <Outlet />
      </main>
      <AuthModal />
    </div>
  );
}

export default App;
