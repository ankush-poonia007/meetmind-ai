import { Outlet } from 'react-router-dom';
import Sidebar from './components/layout/Sidebar';

/**
 * App — Root Application Shell (Gate 2)
 * Integrates the fixed left sidebar and the main content area.
 * Nested routes are rendered within the main content region via React Router's Outlet.
 */
function App() {
  return (
    <div className="app-layout">
      <Sidebar />
      <main className="main-content" id="main-content" tabIndex="-1">
        <Outlet />
      </main>
    </div>
  );
}

export default App;
