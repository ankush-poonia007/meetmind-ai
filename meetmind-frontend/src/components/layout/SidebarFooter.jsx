import { useNavigate } from 'react-router-dom';
import { Github, Linkedin, LogOut } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';

/**
 * SidebarFooter — MeetMind AI Sidebar Footer (Batch 4.7 Redesign).
 *
 * Requirements:
 * - Exactly four items in strict order:
 *   1. Version label — v1.0.0
 *   2. Logout button (action affordance, sits immediately to the left of LinkedIn)
 *   3. LinkedIn link
 *   4. GitHub link
 * - Intentional, balanced spacing utilizing available sidebar width.
 * - Distinct styling for Logout as an action rather than a passive social link.
 * - Fully responsive across expanded, resized, and collapsed (< 768px) viewports.
 */
function SidebarFooter() {
  const version = import.meta.env.VITE_APP_VERSION || '1.0.0';
  const { isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async (e) => {
    e.preventDefault();
    await logout();
    navigate('/');
  };

  return (
    <footer className="sidebar-footer" aria-label="Sidebar footer">
      {/* ── Position 1: Version Label ──────────────────────────────────── */}
      <span className="sidebar-version sidebar-label" title={`MeetMind Version ${version}`}>
        v{version}
      </span>

      {/* ── Position 2, 3, 4: Action & Social Links Container ─────────── */}
      <div className="sidebar-footer-links">
        {/* Position 2: Logout Button (immediately left of LinkedIn) */}
        {isAuthenticated && (
          <button
            type="button"
            onClick={handleLogout}
            className="sidebar-footer-link sidebar-logout-btn"
            title="Log out"
            aria-label="Log out of your account"
          >
            <LogOut size={15} className="sidebar-logout-icon" aria-hidden="true" />
            <span className="sidebar-logout-text sidebar-label">Logout</span>
            <span className="sidebar-tooltip" role="tooltip" aria-hidden="true">
              Log out
            </span>
          </button>
        )}

        {/* Position 3: LinkedIn Link */}
        <a
          href="https://www.linkedin.com/in/ankush-poonia007/"
          target="_blank"
          rel="noopener noreferrer"
          className="sidebar-footer-link sidebar-social-link"
          title="LinkedIn profile"
          aria-label="LinkedIn profile (opens in new tab)"
        >
          <Linkedin size={17} aria-hidden="true" />
          <span className="sidebar-tooltip" role="tooltip" aria-hidden="true">
            LinkedIn
          </span>
        </a>

        {/* Position 4: GitHub Link */}
        <a
          href="https://github.com/ankush-poonia007/meetmind-ai"
          target="_blank"
          rel="noopener noreferrer"
          className="sidebar-footer-link sidebar-social-link"
          title="MeetMind GitHub Repository"
          aria-label="MeetMind GitHub Repository (opens in new tab)"
        >
          <Github size={17} aria-hidden="true" />
          <span className="sidebar-tooltip" role="tooltip" aria-hidden="true">
            GitHub Repository
          </span>
        </a>
      </div>
    </footer>
  );
}

export default SidebarFooter;
