import { Bot, Layers, Activity } from 'lucide-react';

/**
 * TechHighlight — Home Page Section 5 (Section 7)
 * Light contrast section highlighting AI engineering architecture:
 * 3 horizontal feature cards:
 * 1. 7 Specialized Agents (Bot)
 * 2. Hybrid RAG Pipeline (Layers)
 * 3. Real-Time Tracing (Activity)
 */
function TechHighlight() {
  const highlights = [
    {
      icon: Bot,
      stat: '7 Specialized Agents',
      explanation:
        'Orchestrated by a supervisor for extraction, RAG, and notification.',
    },
    {
      icon: Layers,
      stat: 'Hybrid RAG Pipeline',
      explanation:
        'Vector embeddings and reranked retrieval for transcript Q&A.',
    },
    {
      icon: Activity,
      stat: 'Real-Time Tracing',
      explanation:
        'Full visibility and auditability into agent execution steps.',
    },
  ];

  return (
    <section className="tech-highlight-section" id="tech-highlight" aria-labelledby="tech-highlight-heading">
      <div className="container">
        <div className="tech-highlight-header">
          <p className="text-label tech-highlight-label">Built with</p>
          <h2 className="text-h2 tech-highlight-heading" id="tech-highlight-heading">
            AI Engineering Depth
          </h2>
        </div>

        <div className="tech-highlight-grid">
          {highlights.map((item) => {
            const Icon = item.icon;
            return (
              <div key={item.stat} className="tech-stat-block">
                <div className="tech-stat-icon-wrapper" aria-hidden="true">
                  <Icon className="tech-stat-icon" size={24} />
                </div>
                <h3 className="tech-stat-title">{item.stat}</h3>
                <p className="tech-stat-desc">{item.explanation}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

export default TechHighlight;
