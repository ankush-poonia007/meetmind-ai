import { ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react';
import TaskRow from './TaskRow';

/**
 * TaskTable — Complete Task Data Table Component (Section 8 Sub-View 3 / Batch 5.2)
 *
 * Renders the 7-column table layout:
 *   | Task Title | Meeting | Priority | Deadline | Status | Role | Actions |
 *
 * Supports column sorting, accessible headings, responsive overflow, and row hover styling.
 *
 * @param {object} props
 * @param {Array<object>} props.tasks - Array of task objects to render
 * @param {object} props.meetingsMap - Map of meeting UUID -> meeting object
 * @param {object} props.rolesMap - Map of meeting UUID -> participant role
 * @param {string} [props.defaultRole] - Fallback user role
 * @param {Function} props.onStatusToggle - Callback (taskId, nextStatus)
 * @param {string|null} [props.updatingTaskId] - ID of task currently updating status
 * @param {string} [props.sortField] - Current sort column
 * @param {'asc'|'desc'} [props.sortDirection] - Current sort direction
 * @param {Function} [props.onSort] - Callback to change sort column
 */
function TaskTable({
  tasks = [],
  meetingsMap = {},
  rolesMap = {},
  defaultRole = '—',
  onStatusToggle,
  updatingTaskId = null,
  sortField = 'deadline',
  sortDirection = 'asc',
  onSort,
}) {
  const renderSortIndicator = (field) => {
    if (!onSort) return null;
    if (sortField !== field) {
      return <ArrowUpDown size={12} className="th-sort-icon th-sort-inactive" aria-hidden="true" />;
    }
    return sortDirection === 'asc' ? (
      <ArrowUp size={12} className="th-sort-icon th-sort-active" aria-hidden="true" />
    ) : (
      <ArrowDown size={12} className="th-sort-icon th-sort-active" aria-hidden="true" />
    );
  };

  const handleHeaderClick = (field) => {
    if (onSort) onSort(field);
  };

  return (
    <div className="task-table-wrapper" tabIndex={0} role="region" aria-label="Tasks table">
      <table className="task-table">
        <thead>
          <tr>
            {/* 1. Task Title */}
            <th
              scope="col"
              className="th-task-title sortable"
              onClick={() => handleHeaderClick('title')}
              aria-sort={sortField === 'title' ? (sortDirection === 'asc' ? 'ascending' : 'descending') : 'none'}
            >
              <div className="th-content">
                <span>Task Title</span>
                {renderSortIndicator('title')}
              </div>
            </th>

            {/* 2. Meeting */}
            <th
              scope="col"
              className="th-task-meeting sortable"
              onClick={() => handleHeaderClick('meeting')}
              aria-sort={sortField === 'meeting' ? (sortDirection === 'asc' ? 'ascending' : 'descending') : 'none'}
            >
              <div className="th-content">
                <span>Meeting</span>
                {renderSortIndicator('meeting')}
              </div>
            </th>

            {/* 3. Priority */}
            <th
              scope="col"
              className="th-task-priority sortable"
              onClick={() => handleHeaderClick('priority')}
              aria-sort={sortField === 'priority' ? (sortDirection === 'asc' ? 'ascending' : 'descending') : 'none'}
            >
              <div className="th-content">
                <span>Priority</span>
                {renderSortIndicator('priority')}
              </div>
            </th>

            {/* 4. Deadline */}
            <th
              scope="col"
              className="th-task-deadline sortable"
              onClick={() => handleHeaderClick('deadline')}
              aria-sort={sortField === 'deadline' ? (sortDirection === 'asc' ? 'ascending' : 'descending') : 'none'}
            >
              <div className="th-content">
                <span>Deadline</span>
                {renderSortIndicator('deadline')}
              </div>
            </th>

            {/* 5. Status */}
            <th
              scope="col"
              className="th-task-status sortable"
              onClick={() => handleHeaderClick('status')}
              aria-sort={sortField === 'status' ? (sortDirection === 'asc' ? 'ascending' : 'descending') : 'none'}
            >
              <div className="th-content">
                <span>Status</span>
                {renderSortIndicator('status')}
              </div>
            </th>

            {/* 6. Role */}
            <th scope="col" className="th-task-role">
              <div className="th-content">
                <span>Role</span>
              </div>
            </th>

            {/* 7. Actions */}
            <th scope="col" className="th-task-actions">
              <div className="th-content">
                <span>Actions</span>
              </div>
            </th>
          </tr>
        </thead>
        <tbody>
          {tasks.map((task) => {
            const meeting = meetingsMap[task.meeting_id];
            const meetingTitle = meeting?.title || 'Untitled Meeting';
            const role =
              rolesMap[task.meeting_id] ||
              meeting?.user_role ||
              defaultRole;

            return (
              <TaskRow
                key={task.id}
                task={task}
                meetingTitle={meetingTitle}
                role={role}
                onStatusToggle={onStatusToggle}
                isUpdating={updatingTaskId === task.id}
              />
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default TaskTable;
