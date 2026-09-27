/**
 * docsData.js — Authoritative Specification Data for MeetMind AI Documentation
 *
 * Source of Truth:
 * - docs/FRONTEND_DESIGN_DOC.md (Section 9)
 * - docs/ARCHITECTURE.md (Section 8)
 * - docs/AGENT_FLOW.md
 */

/* ── Navigation Groups & Section Anchors ───────────────────────────────────── */
export const DOCS_NAV_GROUPS = [
  {
    title: 'Overview',
    items: [
      { id: 'what-is-meetmind', label: 'What is MeetMind' },
      { id: 'how-it-works', label: 'How it works' },
    ],
  },
  {
    title: 'Architecture',
    items: [
      { id: 'system-overview', label: 'System Overview' },
      { id: 'agent-roster', label: 'Agent Roster' },
      { id: 'rag-pipeline', label: 'RAG Pipeline' },
    ],
  },
  {
    title: 'Features',
    items: [
      { id: 'transcript-ingestion', label: 'Transcript Ingestion' },
      { id: 'identity-detection', label: 'Identity Detection' },
      { id: 'task-extraction', label: 'Task Extraction' },
      { id: 'qa-chat', label: 'Q&A Chat' },
      { id: 'email-alerts', label: 'Email Alerts' },
      { id: 'dashboard', label: 'Dashboard' },
    ],
  },
  {
    title: 'Reference',
    items: [
      { id: 'tech-stack', label: 'Tech Stack' },
      { id: 'models-used', label: 'Models Used' },
      { id: 'api-reference', label: 'API Reference' },
    ],
  },
];

/* ── 7 Specialized Agents Roster ─────────────────────────────────────────── */
export const AGENTS_ROSTER_DATA = [
  {
    name: 'Supervisor',
    role: 'Orchestrator',
    responsibility: 'Orchestrates multi-agent pipeline, generates execution plans, and routes conditional execution flow.',
    model: 'gemini-3.6-flash',
    pattern: 'Plan-and-Execute',
  },
  {
    name: 'Ingestion',
    role: 'Parser & Indexer',
    responsibility: 'Parses PDF and TXT transcripts, applies speaker-aware chunking, and writes vector embeddings to Pinecone.',
    model: 'gemini-3.5-flash-lite',
    pattern: 'ReAct',
  },
  {
    name: 'Identity',
    role: 'Participant Resolver',
    responsibility: 'Searches transcript for participant mentions, verifies user context, and isolates personal responsibilities.',
    model: 'gemini-3.5-flash-lite',
    pattern: 'ReAct',
  },
  {
    name: 'Extraction',
    role: 'Task & Highlight Extractor',
    responsibility: 'Extracts assigned action items, drafts clear descriptions, infers task priorities, and isolates meeting highlights.',
    model: 'gemini-3.5-flash-lite',
    pattern: 'ReAct',
  },
  {
    name: 'Confirmation',
    role: 'Human-in-the-Loop',
    responsibility: 'Presents extracted tasks to user in chat, accepts yes/no/partial confirmation, and persists approved items.',
    model: 'gemini-3.5-flash-lite',
    pattern: 'ReAct',
  },
  {
    name: 'Q&A',
    role: 'Hybrid RAG Assistant',
    responsibility: 'Executes semantic vector search and reciprocal reranking to answer meeting questions with grounded source citations.',
    model: 'gemini-3.6-flash',
    pattern: 'ReAct',
  },
  {
    name: 'Notification',
    role: 'Proactive Alerting',
    responsibility: 'Conducts daily deadline audits, retrieves original meeting context, and composes proactive email alerts via Resend.',
    model: 'gemini-3.5-flash-lite',
    pattern: 'ReAct',
  },
];

/* ── 12 Technology Stack Catalog ─────────────────────────────────────────── */
export const TECH_STACK_DATA = [
  {
    name: 'React 18',
    category: 'Frontend Framework',
    purpose: 'Declarative component-based architecture powering the interactive workspace shell, real-time chat, and task review.',
    iconName: 'Code',
  },
  {
    name: 'Vite 5',
    category: 'Build Tool',
    purpose: 'Next-generation ES module frontend build engine providing lightning-fast Hot Module Replacement (HMR).',
    iconName: 'Zap',
  },
  {
    name: 'Vanilla CSS',
    category: 'Design System',
    purpose: 'Pure CSS custom properties implementing the authoritative Muted Blue theme with zero runtime UI library dependencies.',
    iconName: 'Palette',
  },
  {
    name: 'React Router v6',
    category: 'Client-Side Routing',
    purpose: 'Declarative routing enabling nested workspace views, query parameter state synchronization, and route guards.',
    iconName: 'Route',
  },
  {
    name: 'Axios',
    category: 'HTTP Client',
    purpose: 'Centralized API client with automatic JWT Bearer token attachment, unified error formatting, and request abort signals.',
    iconName: 'Globe',
  },
  {
    name: 'Lucide React',
    category: 'Iconography',
    purpose: 'Lightweight, accessible SVG iconography maintaining consistent visual rhythm across all workspace cards and tables.',
    iconName: 'Feather',
  },
  {
    name: 'FastAPI',
    category: 'Backend Framework',
    purpose: 'Asynchronous Python web framework serving OpenAPI 3.1.0 endpoints for meetings, chat Q&A, and tasks.',
    iconName: 'Server',
  },
  {
    name: 'PostgreSQL / Supabase',
    category: 'Relational Database',
    purpose: 'Primary persistence layer maintaining referential integrity across users, meetings, participants, tasks, and highlights.',
    iconName: 'Database',
  },
  {
    name: 'LangGraph',
    category: 'Agent Orchestration',
    purpose: 'Stateful multi-agent execution graph implementing Plan-and-Execute supervisor orchestration and ReAct tool loops.',
    iconName: 'GitFork',
  },
  {
    name: 'Pinecone',
    category: 'Vector Database',
    purpose: 'Serverless vector store holding speaker-aware transcript chunk embeddings indexed under meeting-scoped namespaces.',
    iconName: 'Layers',
  },
  {
    name: 'Resend',
    category: 'Email Delivery',
    purpose: 'Transactional email infrastructure delivering automated daily deadline alerts with meeting context summaries.',
    iconName: 'Mail',
  },
  {
    name: 'Google Gemini',
    category: 'Foundation Models',
    purpose: 'Gemini 3.6 Flash & 3.5 Flash Lite powering high-reasoning Q&A, task extraction, identity detection, and vector embeddings.',
    iconName: 'Cpu',
  },
];

/* ── 6-Step RAG Pipeline Sequence ────────────────────────────────────────── */
export const RAG_STEPS = [
  {
    step: '01',
    title: 'Transcript Ingestion',
    shortName: 'Transcript',
    iconName: 'FileText',
    summary: 'Raw TXT or PDF uploaded and parsed with speaker-aware turn segmentation.',
    badge: 'Input',
  },
  {
    step: '02',
    title: 'Chunk & Embed',
    shortName: 'Chunk + Embed',
    iconName: 'Layers',
    summary: '500-token conversational chunks vectorized via gemini-embedding-001.',
    badge: 'Vectorize',
  },
  {
    step: '03',
    title: 'Pinecone Vector Store',
    shortName: 'Pinecone',
    iconName: 'Database',
    summary: '3072-dimension dense embeddings indexed under meeting-scoped namespaces.',
    badge: 'Index',
  },
  {
    step: '04',
    title: 'Hybrid Search',
    shortName: 'Hybrid Search',
    iconName: 'Search',
    summary: 'Cosine vector similarity combined with sparse BM25 lexical keyword matching.',
    badge: 'Retrieve',
  },
  {
    step: '05',
    title: 'Reciprocal Rerank',
    shortName: 'Rerank',
    iconName: 'Sparkles',
    summary: 'Reciprocal rank fusion and cross-encoder relevance reordering of top-k passages.',
    badge: 'Score',
  },
  {
    step: '06',
    title: 'Grounded Answer',
    shortName: 'Answer',
    iconName: 'MessageSquare',
    summary: 'Gemini 3.6 Flash synthesizes response backed by verbatim speaker citations.',
    badge: 'Synthesis',
  },
];

/* ── 3 Gemini Foundation Models Specifications ───────────────────────────── */
export const MODELS_DATA = [
  {
    name: 'gemini-3.6-flash',
    roleTag: 'High-Reasoning Orchestration & Synthesis',
    badgeClass: 'model-card-primary',
    iconName: 'Cpu',
    contextWindow: '1,000,000 tokens',
    latency: '~400ms TTFT',
    throughput: 'High concurrency',
    assignedAgents: ['Supervisor Agent', 'Q&A Assistant Agent'],
    summary:
      'Powers the complex cognitive workloads in MeetMind AI. Responsible for high-level Plan-and-Execute pipeline decomposition and answering conversational questions with strict grounding and verifiable transcript citations.',
    highlights: [
      'Multi-step reasoning and sub-goal task graph generation',
      'Hallucination-resistant transcript synthesis with quote extraction',
      'Reciprocal reranking and contextual answer evaluation',
    ],
  },
  {
    name: 'gemini-3.5-flash-lite',
    roleTag: 'Ultra-Fast Structured Information Extraction',
    badgeClass: 'model-card-lite',
    iconName: 'Zap',
    contextWindow: '1,000,000 tokens',
    latency: '~150ms TTFT',
    throughput: 'Maximum throughput',
    assignedAgents: [
      'Ingestion Agent',
      'Identity Agent',
      'Extraction Agent',
      'Confirmation Agent',
      'Notification Agent',
    ],
    summary:
      'Optimized for rapid, cost-effective structured JSON schema compliance. Drives five specialized ReAct agents to parse transcripts, resolve participant identities, classify action items, and draft proactive alerts.',
    highlights: [
      'Deterministic Pydantic/Zod JSON schema enforcement',
      'Sub-second entity extraction and action-item priority tagging',
      'Ultra-low token latency for rapid human-in-the-loop chat interactions',
    ],
  },
  {
    name: 'gemini-embedding-001',
    roleTag: 'Dense Semantic Vector Representation',
    badgeClass: 'model-card-embed',
    iconName: 'Binary',
    contextWindow: '2,048 tokens per chunk',
    latency: '<50ms vectorization',
    throughput: 'Batch-optimized',
    assignedAgents: ['Ingestion Agent', 'Q&A Assistant Agent'],
    summary:
      'Creates dense 3072-dimensional vector representations of transcript chunks. Indexed in Pinecone serverless vector stores with cosine similarity metrics to enable multi-speaker semantic search.',
    highlights: [
      'Captures semantic dialogue nuances across meeting turns',
      'Generates 3072-dim embeddings stored in Pinecone namespaces',
      'Enables hybrid search by bridging dense vector and sparse BM25 retrieval',
    ],
  },
];

/* ── 21 Documented REST API Endpoints (ARCHITECTURE.md Section 8) ─────────── */
export const API_ENDPOINTS_DATA = [
  {
    id: 1,
    method: 'POST',
    path: '/api/v1/users/register',
    category: 'Users',
    purpose: 'Register new user account and initialize personal profile.',
    auth: 'None',
  },
  {
    id: 2,
    method: 'GET',
    path: '/api/v1/users/{user_id}',
    category: 'Users',
    purpose: 'Retrieve authenticated user profile by user ID.',
    auth: 'Bearer',
  },
  {
    id: 3,
    method: 'PUT',
    path: '/api/v1/users/{user_id}',
    category: 'Users',
    purpose: 'Update user profile settings and notification preferences.',
    auth: 'Bearer',
  },
  {
    id: 4,
    method: 'POST',
    path: '/api/v1/meetings/',
    category: 'Meetings',
    purpose: 'Create meeting record, parse transcript, and trigger ingestion pipeline.',
    auth: 'Bearer',
  },
  {
    id: 5,
    method: 'GET',
    path: '/api/v1/meetings/{user_id}',
    category: 'Meetings',
    purpose: 'Retrieve all meetings associated with the specified user ID.',
    auth: 'Bearer',
  },
  {
    id: 6,
    method: 'GET',
    path: '/api/v1/meetings/{meeting_id}/detail',
    category: 'Meetings',
    purpose: 'Retrieve single meeting details, full transcript, and participant list.',
    auth: 'Bearer',
  },
  {
    id: 7,
    method: 'DELETE',
    path: '/api/v1/meetings/{meeting_id}',
    category: 'Meetings',
    purpose: 'Delete meeting and cascade purge indexed vectors and associated artifacts.',
    auth: 'Bearer',
  },
  {
    id: 8,
    method: 'GET',
    path: '/api/v1/tasks/{user_id}',
    category: 'Tasks',
    purpose: 'Retrieve all tasks assigned to user across all meetings.',
    auth: 'Bearer',
  },
  {
    id: 9,
    method: 'GET',
    path: '/api/v1/tasks/{user_id}/meeting/{meeting_id}',
    category: 'Tasks',
    purpose: 'Retrieve action items assigned to user for a specific meeting.',
    auth: 'Bearer',
  },
  {
    id: 10,
    method: 'PUT',
    path: '/api/v1/tasks/{task_id}/status',
    category: 'Tasks',
    purpose: 'Toggle task completion status between Pending and Completed.',
    auth: 'Bearer',
  },
  {
    id: 11,
    method: 'GET',
    path: '/api/v1/tasks/{user_id}/filter',
    category: 'Tasks',
    purpose: 'Filter tasks by priority level (High, Medium, Low) and deadline range.',
    auth: 'Bearer',
  },
  {
    id: 12,
    method: 'POST',
    path: '/api/v1/chat/{meeting_id}/message',
    category: 'Chat',
    purpose: 'Send natural language query and stream grounded Q&A response with citations.',
    auth: 'Bearer',
  },
  {
    id: 13,
    method: 'GET',
    path: '/api/v1/chat/{meeting_id}/history',
    category: 'Chat',
    purpose: 'Retrieve stored conversation history for the given meeting ID.',
    auth: 'Bearer',
  },
  {
    id: 14,
    method: 'DELETE',
    path: '/api/v1/chat/{meeting_id}/history',
    category: 'Chat',
    purpose: 'Clear conversation message history for the given meeting ID.',
    auth: 'Bearer',
  },
  {
    id: 15,
    method: 'POST',
    path: '/api/v1/extraction/{meeting_id}/run',
    category: 'Extraction',
    purpose: 'Run explicit-name multi-agent pipeline to extract assigned action items.',
    auth: 'Bearer',
  },
  {
    id: 16,
    method: 'GET',
    path: '/api/v1/extraction/{meeting_id}/preview',
    category: 'Extraction',
    purpose: 'Preview extracted action items pending human-in-the-loop confirmation.',
    auth: 'Bearer',
  },
  {
    id: 17,
    method: 'POST',
    path: '/api/v1/extraction/{meeting_id}/confirm',
    category: 'Extraction',
    purpose: 'Confirm selected action items, apply inline edits, and persist to database.',
    auth: 'Bearer',
  },
  {
    id: 18,
    method: 'GET',
    path: '/api/v1/highlights/{user_id}/meeting/{meeting_id}',
    category: 'Highlights',
    purpose: 'Retrieve executive summary, key decisions, and highlights for a meeting.',
    auth: 'Bearer',
  },
  {
    id: 19,
    method: 'GET',
    path: '/api/v1/highlights/{user_id}',
    category: 'Highlights',
    purpose: 'Retrieve aggregated meeting highlights across all user meetings.',
    auth: 'Bearer',
  },
  {
    id: 20,
    method: 'POST',
    path: '/api/v1/notifications/trigger',
    category: 'Notifications',
    purpose: 'Manually trigger proactive deadline audit and dispatch email alerts via Resend.',
    auth: 'Bearer',
  },
  {
    id: 21,
    method: 'GET',
    path: '/api/v1/notifications/{user_id}/pending',
    category: 'Notifications',
    purpose: 'Retrieve pending deadline notification alerts queued for user.',
    auth: 'Bearer',
  },
];
