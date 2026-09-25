/**
 * TechHighlight — Home Page Section 5 (Section 7)
 * Dark contrast background section highlighting AI engineering architecture:
 * 3 horizontal stat blocks:
 * 1. 7 Specialized Agents (Supervisor, Ingestion, Identity, Extraction, Confirmation, Q&A, Notification)
 * 2. Hybrid RAG Pipeline (Vector embeddings + reranked retrieval)
 * 3. Real-Time Tracing (Execution tracing and observability)
 */
function TechHighlight() {
  const highlights = [
    {
      stat: '7 Specialized Agents',
      explanation:
        'Orchestrated by a supervisor for extraction, RAG, and notification.',
    },
    {
      stat: 'Hybrid RAG Pipeline',
      explanation:
        'Vector embeddings and reranked retrieval for transcript Q&A.',
    },
    {
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
          {highlights.map((item) => (
            <div key={item.stat} className="tech-stat-block">
              <h3 className="tech-stat-title">{item.stat}</h3>
              <p className="tech-stat-desc">{item.explanation}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export default TechHighlight;
