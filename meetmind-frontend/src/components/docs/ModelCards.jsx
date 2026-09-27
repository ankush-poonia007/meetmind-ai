import { Cpu, Zap, Binary, CheckCircle2 } from 'lucide-react';
import { MODELS_DATA } from '../../data/docsData.js';

export { MODELS_DATA };

const ICONS = {
  Cpu,
  Zap,
  Binary,
};

function ModelCards() {
  return (
    <div className="models-grid" aria-label="Google Gemini Foundation Models Grid">
      {MODELS_DATA.map((model) => {
        const Icon = ICONS[model.iconName] || Cpu;
        return (
          <div key={model.name} className={`model-card card ${model.badgeClass}`}>
            <div className="model-card-header">
              <div className="model-card-icon" aria-hidden="true">
                <Icon size={22} />
              </div>
              <div>
                <h3 className="model-card-name">{model.name}</h3>
                <span className="model-card-role-tag">{model.roleTag}</span>
              </div>
            </div>

            <p className="model-card-summary">{model.summary}</p>

            <div className="model-card-specs">
              <div className="model-spec-item">
                <span className="spec-label">Context Window</span>
                <span className="spec-value">{model.contextWindow}</span>
              </div>
              <div className="model-spec-item">
                <span className="spec-label">Latency</span>
                <span className="spec-value">{model.latency}</span>
              </div>
              <div className="model-spec-item">
                <span className="spec-label">Deployment</span>
                <span className="spec-value">{model.throughput}</span>
              </div>
            </div>

            <div className="model-card-agents">
              <span className="model-agents-title">Assigned Agents</span>
              <div className="model-agent-tags">
                {model.assignedAgents.map((agent) => (
                  <span key={agent} className="model-agent-tag">
                    {agent}
                  </span>
                ))}
              </div>
            </div>

            <ul className="model-card-highlights">
              {model.highlights.map((h, i) => (
                <li key={i} className="model-highlight-item">
                  <CheckCircle2 size={13} className="model-highlight-icon" aria-hidden="true" />
                  <span>{h}</span>
                </li>
              ))}
            </ul>
          </div>
        );
      })}
    </div>
  );
}

export default ModelCards;
