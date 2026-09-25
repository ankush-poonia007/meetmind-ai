import { Outlet } from 'react-router-dom';

/**
 * Workspace — Layout Wrapper Component (Gate 2)
 * Renders nested workspace sub-routes (Dashboard, Meetings, Tasks, Chat).
 */
function Workspace() {
  return (
    <div className="workspace-layout">
      <Outlet />
    </div>
  );
}

export default Workspace;
