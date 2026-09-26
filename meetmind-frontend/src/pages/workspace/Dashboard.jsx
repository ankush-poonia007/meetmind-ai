import {
  Calendar,
  CheckSquare,
  Clock,
  CheckCircle,
  AlertCircle,
  AlertTriangle,
  RotateCcw,
} from 'lucide-react';
import StatCard from '../../components/workspace/StatCard';
import HighlightPanel from '../../components/workspace/HighlightPanel';
import DeadlinePanel from '../../components/workspace/DeadlinePanel';
import { useUser } from '../../hooks/useUser';
import { useDashboardData } from '../../hooks/useDashboardData';

/**
 * Dashboard — Workspace Sub-View 1 (Section 8 Line 544 & Batch 4.3 Integration)
 * Composes the top 5-card statistics row and the asymmetric two-column section
 * (60% Recent Highlights, 40% Upcoming Deadlines) within the workspace container,
 * connected to the live FastAPI backend via useUser and useDashboardData.
 */
function Dashboard() {
  const {
    userId,
    loading: userLoading,
    error: userError,
    retrySession,
  } = useUser();

  const {
    loading: dataLoading,
    error: dataError,
    stats,
    highlights,
    deadlines,
    partialErrors,
    refetch,
  } = useDashboardData(userId);

  const isLoading = userLoading || dataLoading;
  const primaryError = userError || dataError;

  const handleRetry = () => {
    if (userError) {
      retrySession();
    } else {
      refetch();
    }
  };

  /**
   * Safe value renderer for StatCards.
   * Renders a skeleton during loading, "—" when request failed, and numerical count on success.
   *
   * @param {number | null} val
   * @returns {React.ReactNode}
   */
  const renderStatValue = (val) => {
    if (isLoading) {
      return <span className="skeleton stat-card-skeleton-value" aria-label="Loading metric..." />;
    }
    if (val === null || val === undefined) {
      return '—';
    }
    return val;
  };

  return (
    <div className="page-enter">
      <div className="workspace-container">
        {/* ── Dashboard Header ──────────────────────────────────────────── */}
        <header className="dashboard-header">
          <p className="text-label dashboard-header-label">Workspace</p>
          <h1 className="text-h1 dashboard-header-title">Dashboard</h1>
          <p className="text-body-lg dashboard-header-desc">
            Overview of total meetings, active tasks, and upcoming deadlines.
          </p>
        </header>

        {/* ── Backend / Session Error Banner (Option A: Live Data Only) ─── */}
        {primaryError && (
          <aside className="dashboard-error-banner" role="alert">
            <div className="error-banner-content">
              <AlertTriangle size={20} className="error-banner-icon" aria-hidden="true" />
              <span>{primaryError}</span>
            </div>
            <button
              type="button"
              className="btn-retry"
              onClick={handleRetry}
              aria-label="Retry loading dashboard data"
            >
              <RotateCcw size={14} aria-hidden="true" />
              Retry
            </button>
          </aside>
        )}

        {/* ── Top Statistics Row (5 Cards) ──────────────────────────────── */}
        <section
          className="dashboard-stat-grid"
          aria-label="Workspace metrics summary"
        >
          <StatCard
            icon={Calendar}
            value={renderStatValue(stats.totalMeetings)}
            label="Total Meetings"
          />
          <StatCard
            icon={CheckSquare}
            value={renderStatValue(stats.totalTasks)}
            label="Total Tasks"
          />
          <StatCard
            icon={Clock}
            value={renderStatValue(stats.activeTasks)}
            label="Active Tasks"
          />
          <StatCard
            icon={CheckCircle}
            value={renderStatValue(stats.completedTasks)}
            label="Completed"
          />
          <StatCard
            icon={AlertCircle}
            value={renderStatValue(stats.expiredTasks)}
            label="Expired"
          />
        </section>

        {/* ── Dashboard Columns (60% Highlights / 40% Deadlines) ───────── */}
        <div className="dashboard-columns">
          <HighlightPanel
            highlights={highlights}
            loading={isLoading}
            error={partialErrors.highlights}
          />
          <DeadlinePanel
            deadlines={deadlines}
            loading={isLoading}
            error={partialErrors.tasks}
          />
        </div>
      </div>
    </div>
  );
}

export default Dashboard;

