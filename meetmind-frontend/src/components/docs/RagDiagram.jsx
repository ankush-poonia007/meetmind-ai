import {
  FileText,
  Layers,
  Database,
  Search,
  Sparkles,
  MessageSquare,
} from 'lucide-react';

import { RAG_STEPS } from '../../data/docsData.js';

export { RAG_STEPS };

const ICONS = {
  FileText,
  Layers,
  Database,
  Search,
  Sparkles,
  MessageSquare,
};

/**
 * RagDiagram — CSS-based RAG Pipeline Diagram (Section 9 Line 759)
 *
 * Implements the required 4 + 2 arrangement:
 * Row 1: [ 01 ] [ 02 ] [ 03 ] [ 04 ]
 * Row 2: [ 05 ] [       06 — Grounded Answer       ]
 *
 * Pure CSS boxes and connecting indicators. No raster images. Fully responsive.
 */
function RagDiagram() {
  return (
    <div className="rag-diagram-container" aria-label="MeetMind AI RAG Pipeline Diagram">
      <div className="rag-pipeline-grid">
        {RAG_STEPS.map((step) => {
          const Icon = ICONS[step.iconName] || FileText;
          const isWide = step.step === '06';

          return (
            <div
              key={step.step}
              className={`rag-grid-step rag-step-${step.step} ${isWide ? 'rag-step-span-3' : ''}`}
            >
              <div className={`rag-step-card ${isWide ? 'rag-card-wide' : ''}`}>
                <div className="rag-step-top">
                  <div className="rag-step-badge-group">
                    <span className="rag-step-num">{step.step}</span>
                    <span className="rag-step-badge">{step.badge}</span>
                  </div>
                  {/* Pipeline flow transition indicator */}
                  {step.step === '01' && <span className="rag-flow-arrow" title="Next step" aria-hidden="true">→</span>}
                  {step.step === '02' && <span className="rag-flow-arrow" title="Next step" aria-hidden="true">→</span>}
                  {step.step === '03' && <span className="rag-flow-arrow" title="Next step" aria-hidden="true">→</span>}
                  {step.step === '04' && <span className="rag-flow-arrow rag-flow-wrap" title="Flows down to Step 05" aria-hidden="true">↓</span>}
                  {step.step === '05' && <span className="rag-flow-arrow" title="Next step" aria-hidden="true">→</span>}
                  {step.step === '06' && <span className="rag-final-pill">Synthesized Output</span>}
                </div>

                <div className={`rag-step-main ${isWide ? 'rag-step-main-wide' : ''}`}>
                  <div className="rag-step-icon-wrapper" aria-hidden="true">
                    <Icon size={isWide ? 22 : 18} />
                  </div>
                  <div className="rag-step-details">
                    <h4 className="rag-step-title">{isWide ? '06 — Grounded Answer' : step.title}</h4>
                    <p className="rag-step-summary">{step.summary}</p>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default RagDiagram;
