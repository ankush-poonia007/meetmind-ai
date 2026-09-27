import {
  Code,
  Zap,
  Palette,
  Route,
  Globe,
  Feather,
  Server,
  Database,
  GitFork,
  Layers,
  Mail,
  Cpu,
} from 'lucide-react';

import { TECH_STACK_DATA } from '../../data/docsData.js';

export { TECH_STACK_DATA };

const ICONS = {
  Code,
  Zap,
  Palette,
  Route,
  Globe,
  Feather,
  Server,
  Database,
  GitFork,
  Layers,
  Mail,
  Cpu,
};

/**
 * TechGrid — Two-Column Technology Stack Grid (Section 9 Line 754)
 */
function TechGrid() {
  return (
    <div className="tech-grid" aria-label="Technology stack cards grid">
      {TECH_STACK_DATA.map((tech) => {
        const IconComponent = ICONS[tech.iconName] || Code;
        return (
          <div key={tech.name} className="tech-card card">
            <div className="tech-card-header">
              <div className="tech-card-icon-badge" aria-hidden="true">
                <IconComponent size={20} />
              </div>
              <div>
                <h3 className="tech-card-name">{tech.name}</h3>
                <span className="tech-card-category">{tech.category}</span>
              </div>
            </div>
            <p className="tech-card-purpose">{tech.purpose}</p>
          </div>
        );
      })}
    </div>
  );
}

export default TechGrid;
