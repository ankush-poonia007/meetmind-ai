import { useState, useEffect } from 'react';
import DocsSidebar from '../components/docs/DocsSidebar';
import DocsSection from '../components/docs/DocsSection';
import AgentTable from '../components/docs/AgentTable';
import TechGrid from '../components/docs/TechGrid';
import RagDiagram from '../components/docs/RagDiagram';
import ApiTable from '../components/docs/ApiTable';
import ModelCards from '../components/docs/ModelCards';
import { BookOpen, Cpu, Sparkles, Layers } from 'lucide-react';

/**
 * Documentation — Full Interactive Architecture & System Documentation (Section 9)
 *
 * Implements:
 * - Two-column asymmetric layout (sticky mini-nav left, scrollable content right).
 * - Smooth scrolling and URL hash synchronization.
 * - IntersectionObserver active section tracking.
 * - All 14 documented sections with labels, titles, descriptive body, and visual slots.
 * - Dedicated visual components: AgentTable, TechGrid, RagDiagram, ModelCards, ApiTable.
 */
function Documentation() {
  const [activeId, setActiveId] = useState('what-is-meetmind');

  useEffect(() => {
    // Initial scroll on mount if hash present
    if (window.location.hash) {
      const targetId = window.location.hash.replace('#', '');
      const el = document.getElementById(targetId);
      if (el) {
        setTimeout(() => {
          el.scrollIntoView({ behavior: 'smooth', block: 'start' });
          setActiveId(targetId);
        }, 150);
      }
    }

    const sectionIds = [
      'what-is-meetmind',
      'how-it-works',
      'system-overview',
      'agent-roster',
      'rag-pipeline',
      'transcript-ingestion',
      'identity-detection',
      'task-extraction',
      'qa-chat',
      'email-alerts',
      'dashboard',
      'tech-stack',
      'models-used',
      'api-reference',
    ];

    const elements = sectionIds
      .map((id) => document.getElementById(id))
      .filter(Boolean);

    if (elements.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        // Collect visible sections
        const visibleEntries = entries.filter((e) => e.isIntersecting);
        if (visibleEntries.length > 0) {
          // Select section closest to target header viewport offset
          visibleEntries.sort(
            (a, b) =>
              Math.abs(a.boundingClientRect.top - 90) -
              Math.abs(b.boundingClientRect.top - 90)
          );
          setActiveId(visibleEntries[0].target.id);
        }
      },
      {
        root: null,
        rootMargin: '-80px 0px -55% 0px',
        threshold: [0, 0.15, 0.5, 0.85],
      }
    );

    elements.forEach((el) => observer.observe(el));

    return () => {
      elements.forEach((el) => observer.unobserve(el));
      observer.disconnect();
    };
  }, []);

  return (
    <div className="docs-page page-enter">
      {/* Main Two-Column Layout */}
      <div className="docs-layout-container">
        {/* Left Sticky Sidebar */}
        <aside className="docs-sidebar-col">
          <DocsSidebar activeId={activeId} onSelectSection={(id) => setActiveId(id)} />
        </aside>

        {/* Right Scrollable Content Column */}
        <main className="docs-content-col" id="docs-content">
          {/* Page Header Banner */}
          <header className="docs-header">
            <div className="docs-header-inner">
              <div className="docs-badge-row">
                <span className="docs-pill-badge">
                  <BookOpen size={13} aria-hidden="true" />
                  Developer & System Specification
                </span>
                <span className="docs-version-badge">v1.0 Frozen Specification</span>
              </div>
              <h1 className="docs-page-title">MeetMind AI Documentation</h1>
              <p className="docs-page-subtitle">
                Comprehensive architectural specifications, multi-agent orchestration rosters, hybrid RAG pipelines, and full OpenAPI reference for the MeetMind intelligence platform.
              </p>
            </div>
          </header>
          {/* ── OVERVIEW GROUP ── */}
          <DocsSection
            id="what-is-meetmind"
            label="Overview"
            title="What is MeetMind"
          >
            <p>
              MeetMind is an enterprise-grade AI intelligence system engineered to transform raw, unstructured meeting audio transcripts into structured knowledge, verifiable action items, and proactive alerts. By combining autonomous multi-agent pipelines with hybrid vector retrieval, MeetMind ensures that critical decisions, assigned responsibilities, and key project commitments are never lost in dialogue.
            </p>
            <p>
              Unlike generic transcription summarizers that output passive meeting minutes, MeetMind operates as an active workspace partner. It identifies specific participants, resolves personal task assignments with human-in-the-loop review, grounds conversational answers in exact transcript quotes, and audits upcoming deadlines daily to deliver automated email reminders before deliverables fall through the cracks.
            </p>
          </DocsSection>

          <DocsSection
            id="how-it-works"
            label="Overview"
            title="How it Works"
          >
            <p>
              The MeetMind workflow follows an autonomous four-stage operational loop: Ingestion, Multi-Agent Orchestration, Human Confirmation, and Continuous Proactive Monitoring.
            </p>
            <p>
              When a transcript is uploaded, the system parses conversational speaker turns, generates speaker-aware semantic chunks, and creates vector embeddings stored in Pinecone. The Supervisor Agent dynamically coordinates specialized sub-agents to resolve participant identities and isolate assigned tasks. Before committing tasks to persistent storage, MeetMind presents candidate action items in an interactive review modal, enabling users to verify, modify, or discard items. Once confirmed, tasks sync directly to the dashboard while background workers monitor upcoming due dates.
            </p>
            <div className="docs-callout-card">
              <div className="docs-callout-icon" aria-hidden="true">
                <Sparkles size={18} />
              </div>
              <div className="docs-callout-content">
                <strong>Zero-Loss Principle:</strong> Every extracted action item, highlight, and Q&A response is linked directly back to its source speaker turn and timestamp in the original transcript, eliminating hallucinations and ensuring complete auditability.
              </div>
            </div>
          </DocsSection>

          {/* ── ARCHITECTURE GROUP ── */}
          <DocsSection
            id="system-overview"
            label="Architecture"
            title="System Overview"
          >
            <p>
              MeetMind is architected as a decoupled, micro-service ready system pairing a reactive Vite and React frontend with an asynchronous Python FastAPI backend. State persistence is managed through PostgreSQL via Supabase for structured relational entities (users, meetings, tasks, highlights) and Pinecone Serverless for dense vector representation of conversational chunks.
            </p>
            <p>
              Agentic workflows are orchestrated using LangGraph state machines that blend Plan-and-Execute supervisor coordination with ReAct feedback loops. Inter-service communications rely on standardized JSON schemas enforced by Pydantic models on the backend and validated Axios interceptors on the client.
            </p>
            <div className="docs-callout-card docs-callout-arch">
              <div className="docs-callout-icon" aria-hidden="true">
                <Layers size={18} />
              </div>
              <div className="docs-callout-content">
                <strong>Stateless API Layer:</strong> All FastAPI endpoints are fully stateless and horizontally scalable, delegating durable conversational history to PostgreSQL and vector indexing to Pinecone namespaces scoped per meeting ID.
              </div>
            </div>
          </DocsSection>

          <DocsSection
            id="agent-roster"
            label="Architecture"
            title="Agent Roster"
            visual={<AgentTable />}
          >
            <p>
              MeetMind deploys seven specialized AI agents operating under strict role separation. Rather than relying on a monolithic prompt, each agent specializes in a distinct cognitive phase of the meeting processing pipeline.
            </p>
            <p>
              The roster divides execution between high-reasoning orchestration (Gemini 3.6 Flash) and ultra-fast structured parsing (Gemini 3.5 Flash Lite), optimizing both analytical precision and end-to-end processing cost.
            </p>
          </DocsSection>

          <DocsSection
            id="rag-pipeline"
            label="Architecture"
            title="RAG Pipeline"
            visual={<RagDiagram />}
          >
            <p>
              The Retrieval-Augmented Generation (RAG) pipeline delivers high-accuracy conversational Q&A over lengthy multi-party meeting transcripts. The architecture mitigates standard vector search limitations by combining dense semantic embeddings with sparse keyword retrieval.
            </p>
            <p>
              Incoming queries undergo query expansion and vectorization before executing hybrid search in Pinecone. The resulting top candidate passages pass through a reciprocal reranking stage to reorder chunks by contextual relevance before being supplied to Gemini 3.6 Flash with strict attribution instructions.
            </p>
          </DocsSection>

          {/* ── FEATURES GROUP ── */}
          <DocsSection
            id="transcript-ingestion"
            label="Features"
            title="Transcript Ingestion"
          >
            <p>
              Transcript Ingestion accepts raw multi-speaker transcripts in PDF and plain text formats. The Ingestion Agent segments raw text using speaker-aware boundary detection, ensuring that conversational turns and context windows remain intact across chunk partitions.
            </p>
            <p>
              Chunks are enriched with speaker attribution metadata, relative timestamps, and dialogue classification before being transformed into 3072-dimensional vector embeddings via Gemini Embedding-001 and upserted to Pinecone vector namespaces.
            </p>
          </DocsSection>

          <DocsSection
            id="identity-detection"
            label="Features"
            title="Identity Detection"
          >
            <p>
              Identity Detection resolves ambiguities between registered platform users and spoken conversational names. The Identity Agent parses transcripts for personal names, nicknames, email prefixes, and second-person references (e.g., &ldquo;Ankush, could you take care of the auth endpoints?&rdquo;).
            </p>
            <p>
              By matching spoken participant references to authenticated user profiles, MeetMind ensures that action items and task responsibilities are assigned specifically to the current user rather than general team members.
            </p>
          </DocsSection>

          <DocsSection
            id="task-extraction"
            label="Features"
            title="Task Extraction"
          >
            <p>
              Task Extraction isolates concrete deliverables, owner commitments, and explicit due dates from conversational turns. Using explicit-name targeting, the Extraction Agent queries the transcript to isolate only actionable commitments made by or assigned to the designated participant.
            </p>
            <p>
              Extracted action items are structured with clean descriptive titles, assigned priorities (High, Medium, Low), and parsed ISO 8601 deadlines. The output feeds directly into the human-in-the-loop confirmation modal for review and interactive refinement.
            </p>
          </DocsSection>

          <DocsSection
            id="qa-chat"
            label="Features"
            title="Q&A Chat"
          >
            <p>
              The Q&A Chat interface provides conversational intelligence over indexed meetings. Users can select any ingested meeting and ask targeted questions regarding technical decisions, project timelines, debate outcomes, or specific statements made by attendees.
            </p>
            <p>
              Responses are streamed with typing animations and accompanied by verifiable source citations. Each citation displays the speaker name and quote snippet, allowing users to verify the exact conversational source behind every AI answer.
            </p>
          </DocsSection>

          <DocsSection
            id="email-alerts"
            label="Features"
            title="Email Alerts"
          >
            <p>
              The Notification Agent and automated scheduler run continuous audits against pending task due dates stored in PostgreSQL. When deliverables approach their scheduled deadlines (24-hour and 48-hour thresholds), the agent generates a contextual reminder.
            </p>
            <p>
              Alerts retrieve the original meeting title and task context and dispatch formatted HTML emails via Resend. This proactive push model ensures that team members stay aware of impending milestones without requiring constant dashboard visits.
            </p>
          </DocsSection>

          <DocsSection
            id="dashboard"
            label="Features"
            title="Dashboard"
          >
            <p>
              The MeetMind Dashboard serves as the central command center for personal productivity. It surfaces aggregate statistics including total processed meetings, pending tasks, completion rates, and upcoming critical deadlines.
            </p>
            <p>
              Interactive task cards allow immediate status toggling, priority filtering, and quick navigation back to original meeting transcripts and chat workspaces.
            </p>
          </DocsSection>

          {/* ── REFERENCE GROUP ── */}
          <DocsSection
            id="tech-stack"
            label="Reference"
            title="Tech Stack"
            visual={<TechGrid />}
          >
            <p>
              MeetMind is built on a modern, decoupled production architecture combining cutting-edge AI infrastructure with established web engineering standards.
            </p>
            <p>
              Every layer of the stack has been selected for performance, reliability, and clear separation of concerns—from vanilla CSS design tokens on the frontend to asynchronous Python endpoints and serverless vector indexing on the backend.
            </p>
          </DocsSection>

          <DocsSection
            id="models-used"
            label="Reference"
            title="Models Used"
            visual={<ModelCards />}
          >
            <p>
              MeetMind leverages Google Gemini foundation models, pairing high-reasoning cognitive architectures with ultra-fast structured completion engines.
            </p>
            <p>
              By matching specific agent roles to optimized models, the platform achieves enterprise-grade accuracy while keeping token latency and operational costs minimal.
            </p>
          </DocsSection>

          <DocsSection
            id="api-reference"
            label="Reference"
            title="API Reference"
            visual={<ApiTable />}
          >
            <p>
              The MeetMind backend provides a comprehensive, OpenAPI 3.1.0-compliant REST API serving 21 documented endpoints across user management, meeting processing, task tracking, conversational Q&A, and proactive alerting.
            </p>
            <p>
              All endpoints under <code>/api/v1</code> enforce standard HTTP semantics, JSON payloads, and JWT Bearer token authentication where required.
            </p>
          </DocsSection>
        </main>
      </div>
    </div>
  );
}

export default Documentation;
