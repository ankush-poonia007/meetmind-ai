import { Github, Linkedin } from 'lucide-react';

/**
 * SidebarFooter — MeetMind AI Sidebar Footer
 * Displays application version and social/profile links (LinkedIn, GitHub).
 * In desktop view, links are horizontally aligned beside the version number.
 * In collapsed view (< 768px), the version text hides while icons remain accessible with tooltips.
 */
function SidebarFooter() {
  const version = import.meta.env.VITE_APP_VERSION || '1.0.0';

  return (
    <footer className="sidebar-footer" aria-label="Sidebar footer">
      <span className="sidebar-version sidebar-label">v{version}</span>
      <div className="sidebar-footer-links">
        <a
          href="https://www.linkedin.com/in/ankush-poonia007/"
          target="_blank"
          rel="noopener noreferrer"
          className="sidebar-footer-link"
          title="LinkedIn profile"
          aria-label="LinkedIn profile (opens in new tab)"
        >
          <Linkedin size={18} aria-hidden="true" />
          <span className="sidebar-tooltip" role="tooltip" aria-hidden="true">
            LinkedIn
          </span>
        </a>
        <a
          href="https://github.com/ankush-poonia007/meetmind-ai"
          target="_blank"
          rel="noopener noreferrer"
          className="sidebar-footer-link"
          title="MeetMind GitHub Repository"
          aria-label="MeetMind GitHub Repository (opens in new tab)"
        >
          <Github size={18} aria-hidden="true" />
          <span className="sidebar-tooltip" role="tooltip" aria-hidden="true">
            GitHub Repository
          </span>
        </a>
      </div>
    </footer>
  );
}

export default SidebarFooter;
