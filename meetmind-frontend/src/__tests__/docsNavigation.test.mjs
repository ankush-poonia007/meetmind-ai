/**
 * MeetMind AI — Batch 6.2: Documentation Page & Specifications Test Suite
 *
 * Validates:
 * 1. Documentation navigation hierarchy, groups, and section anchors.
 * 2. 7-agent roster specification, roles, patterns, and model assignments.
 * 3. 12-technology stack architecture catalog and purpose statements.
 * 4. 6-step CSS hybrid RAG pipeline sequence and metadata.
 * 5. Gemini foundation model profiles (3.6-flash, 3.5-flash-lite, embedding-001).
 * 6. Authoritative 21 REST API endpoints catalog, methods, and filtering logic.
 */

import test from 'node:test';
import assert from 'node:assert/strict';

import {
  DOCS_NAV_GROUPS,
  AGENTS_ROSTER_DATA,
  TECH_STACK_DATA,
  RAG_STEPS,
  MODELS_DATA,
  API_ENDPOINTS_DATA,
} from '../data/docsData.js';

/* ── 1. Navigation Structure & Section Anchors ─────────────────────────────── */

test('DOCS_NAV_GROUPS contains all 4 designated groups in order', () => {
  assert.equal(DOCS_NAV_GROUPS.length, 4);
  const titles = DOCS_NAV_GROUPS.map((g) => g.title);
  assert.deepEqual(titles, ['Overview', 'Architecture', 'Features', 'Reference']);
});

test('DOCS_NAV_GROUPS contains exactly 14 unique section anchors', () => {
  const allItems = DOCS_NAV_GROUPS.flatMap((g) => g.items);
  assert.equal(allItems.length, 14);

  const ids = allItems.map((item) => item.id);
  const uniqueIds = new Set(ids);
  assert.equal(uniqueIds.size, 14, 'Every section must have a unique ID');

  const expectedIds = [
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
  assert.deepEqual(ids, expectedIds);
});

/* ── 2. Agent Roster Specifications ────────────────────────────────────────── */

test('AGENTS_ROSTER_DATA registers exactly 7 specialized agents', () => {
  assert.equal(AGENTS_ROSTER_DATA.length, 7);

  const agentNames = AGENTS_ROSTER_DATA.map((a) => a.name);
  const expectedNames = [
    'Supervisor',
    'Ingestion',
    'Identity',
    'Extraction',
    'Confirmation',
    'Q&A',
    'Notification',
  ];
  assert.deepEqual(agentNames, expectedNames);
});

test('AGENTS_ROSTER_DATA verifies high-reasoning vs fast-lite model assignments', () => {
  const supervisor = AGENTS_ROSTER_DATA.find((a) => a.name === 'Supervisor');
  assert.ok(supervisor);
  assert.equal(supervisor.model, 'gemini-3.6-flash');
  assert.equal(supervisor.pattern, 'Plan-and-Execute');

  const qaAgent = AGENTS_ROSTER_DATA.find((a) => a.name === 'Q&A');
  assert.ok(qaAgent);
  assert.equal(qaAgent.model, 'gemini-3.6-flash');
  assert.equal(qaAgent.pattern, 'ReAct');

  const liteAgents = AGENTS_ROSTER_DATA.filter((a) =>
    ['Ingestion', 'Identity', 'Extraction', 'Confirmation', 'Notification'].includes(a.name)
  );
  assert.equal(liteAgents.length, 5);
  for (const agent of liteAgents) {
    assert.equal(agent.model, 'gemini-3.5-flash-lite');
    assert.equal(agent.pattern, 'ReAct');
    assert.ok(agent.responsibility.length > 20);
  }
});

/* ── 3. Tech Stack Catalog ─────────────────────────────────────────────────── */

test('TECH_STACK_DATA catalogs 12 core architecture technologies', () => {
  assert.equal(TECH_STACK_DATA.length, 12);

  const techNames = TECH_STACK_DATA.map((t) => t.name);
  assert.ok(techNames.some((n) => n.includes('React 18')));
  assert.ok(techNames.some((n) => n.includes('Vite 5')));
  assert.ok(techNames.some((n) => n.includes('Vanilla CSS')));
  assert.ok(techNames.some((n) => n.includes('FastAPI')));
  assert.ok(techNames.some((n) => n.includes('PostgreSQL / Supabase')));
  assert.ok(techNames.some((n) => n.includes('LangGraph')));
  assert.ok(techNames.some((n) => n.includes('Pinecone')));
  assert.ok(techNames.some((n) => n.includes('Resend')));
  assert.ok(techNames.some((n) => n.includes('Google Gemini')));

  for (const tech of TECH_STACK_DATA) {
    assert.ok(tech.category);
    assert.ok(tech.purpose && tech.purpose.length > 15);
    assert.ok(tech.iconName);
  }
});

/* ── 4. RAG Pipeline Flow ──────────────────────────────────────────────────── */

test('RAG_STEPS defines the 6 sequential hybrid RAG stages', () => {
  assert.equal(RAG_STEPS.length, 6);

  const stepNums = RAG_STEPS.map((s) => s.step);
  assert.deepEqual(stepNums, ['01', '02', '03', '04', '05', '06']);

  const shortNames = RAG_STEPS.map((s) => s.shortName);
  assert.deepEqual(shortNames, [
    'Transcript',
    'Chunk + Embed',
    'Pinecone',
    'Hybrid Search',
    'Rerank',
    'Answer',
  ]);

  for (const step of RAG_STEPS) {
    assert.ok(step.title);
    assert.ok(step.summary);
    assert.ok(step.badge);
  }
});

/* ── 5. Foundation Models ──────────────────────────────────────────────────── */

test('MODELS_DATA specifies all 3 Gemini models accurately', () => {
  assert.equal(MODELS_DATA.length, 3);

  const modelNames = MODELS_DATA.map((m) => m.name);
  assert.deepEqual(modelNames, [
    'gemini-3.6-flash',
    'gemini-3.5-flash-lite',
    'gemini-embedding-001',
  ]);

  const flash36 = MODELS_DATA.find((m) => m.name === 'gemini-3.6-flash');
  assert.ok(flash36.assignedAgents.includes('Supervisor Agent'));
  assert.ok(flash36.assignedAgents.includes('Q&A Assistant Agent'));

  const flash35 = MODELS_DATA.find((m) => m.name === 'gemini-3.5-flash-lite');
  assert.equal(flash35.assignedAgents.length, 5);

  const embed001 = MODELS_DATA.find((m) => m.name === 'gemini-embedding-001');
  assert.ok(embed001.summary.includes('3072'));
});

/* ── 6. REST API Endpoints Specification ───────────────────────────────────── */

test('API_ENDPOINTS_DATA contains exactly 21 documented endpoints', () => {
  assert.equal(API_ENDPOINTS_DATA.length, 21);

  // Validate sequential IDs 1 to 21
  const ids = API_ENDPOINTS_DATA.map((ep) => ep.id);
  const expectedIds = Array.from({ length: 21 }, (_, i) => i + 1);
  assert.deepEqual(ids, expectedIds);

  // Validate all paths start with /api/v1/
  for (const ep of API_ENDPOINTS_DATA) {
    assert.ok(ep.path.startsWith('/api/v1/'), `Path ${ep.path} must start with /api/v1/`);
    assert.ok(['GET', 'POST', 'PUT', 'DELETE'].includes(ep.method));
    assert.ok(['Bearer', 'None'].includes(ep.auth));
    assert.ok(ep.purpose && ep.purpose.length > 10);
  }
});

test('API filtering logic correctly filters by category and search term', () => {
  // Filter by category: Meetings
  const meetingEndpoints = API_ENDPOINTS_DATA.filter((ep) => ep.category === 'Meetings');
  assert.equal(meetingEndpoints.length, 4); // Create, All, Single detail, Delete

  // Filter by category: Tasks
  const taskEndpoints = API_ENDPOINTS_DATA.filter((ep) => ep.category === 'Tasks');
  assert.equal(taskEndpoints.length, 4); // All, By meeting, Toggle status, Filter

  // Filter by category: Chat
  const chatEndpoints = API_ENDPOINTS_DATA.filter((ep) => ep.category === 'Chat');
  assert.equal(chatEndpoints.length, 3); // Message, Get history, Clear history

  // Filter by category: Extraction
  const extractionEndpoints = API_ENDPOINTS_DATA.filter((ep) => ep.category === 'Extraction');
  assert.equal(extractionEndpoints.length, 3); // Run, Preview, Confirm

  // Search query 'preview'
  const searchResults = API_ENDPOINTS_DATA.filter(
    (ep) =>
      ep.path.toLowerCase().includes('preview') ||
      ep.purpose.toLowerCase().includes('preview')
  );
  assert.equal(searchResults.length, 1);
  assert.equal(searchResults[0].path, '/api/v1/extraction/{meeting_id}/preview');
});
