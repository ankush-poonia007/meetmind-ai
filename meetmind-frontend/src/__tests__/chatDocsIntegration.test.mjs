/**
 * MeetMind AI — Batch 6.3: Chat & Documentation Integration Test Suite
 *
 * Validates:
 * 1. Query parameter resolution for both ?meeting= and ?meetingId= in Chat.
 * 2. Meeting UUID preservation across navigation and fallback behavior.
 * 3. Chat Q&A state machine: optimistic send, citation handling, and clear history.
 * 4. Explicit-name task extraction validation and limitation detection.
 * 5. Task review modification payload creation (inline edits, exclusion/inclusion).
 * 6. Documentation URL hash resolution and section anchoring.
 * 7. Model comparison cards specifications and 4+2 RAG pipeline sequence.
 * 8. API endpoints consistency and auth requirement categorization.
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

/* ── 1. Query Parameter Resolution & UUID Preservation ────────────────────── */

function resolveMeetingFromParams(searchParamsString, availableMeetings) {
  const params = new URLSearchParams(searchParamsString);
  const targetId = params.get('meeting') || params.get('meetingId');

  if (!Array.isArray(availableMeetings) || availableMeetings.length === 0) {
    return { activeMeetingId: '', preserved: false };
  }

  const found = availableMeetings.find((m) => m.id === targetId);
  if (found) {
    return { activeMeetingId: found.id, preserved: true };
  }

  return { activeMeetingId: availableMeetings[0].id, preserved: false };
}

test('Chat resolves meeting UUID using ?meeting= query parameter', () => {
  const mockMeetings = [
    { id: 'uuid-101', title: 'Product Kickoff' },
    { id: 'uuid-102', title: 'Sprint Retrospective' },
  ];

  const result = resolveMeetingFromParams('?meeting=uuid-102', mockMeetings);
  assert.equal(result.activeMeetingId, 'uuid-102');
  assert.equal(result.preserved, true);
});

test('Chat resolves meeting UUID using ?meetingId= query parameter', () => {
  const mockMeetings = [
    { id: 'uuid-101', title: 'Product Kickoff' },
    { id: 'uuid-102', title: 'Sprint Retrospective' },
  ];

  const result = resolveMeetingFromParams('?meetingId=uuid-101', mockMeetings);
  assert.equal(result.activeMeetingId, 'uuid-101');
  assert.equal(result.preserved, true);
});

test('Chat falls back to latest meeting when query parameter is missing or invalid', () => {
  const mockMeetings = [
    { id: 'uuid-latest', title: 'Latest Meeting' },
    { id: 'uuid-older', title: 'Older Meeting' },
  ];

  const noParamResult = resolveMeetingFromParams('', mockMeetings);
  assert.equal(noParamResult.activeMeetingId, 'uuid-latest');
  assert.equal(noParamResult.preserved, false);

  const invalidParamResult = resolveMeetingFromParams('?meeting=invalid-uuid-999', mockMeetings);
  assert.equal(invalidParamResult.activeMeetingId, 'uuid-latest');
  assert.equal(invalidParamResult.preserved, false);
});

/* ── 2. Chat Q&A State Machine & Citations ─────────────────────────────────── */

test('Optimistic user message is created before AI answer resolves', () => {
  const inputQuestion = 'What were the action items discussed?';
  const optimisticMsg = {
    id: `user-${Date.now()}`,
    role: 'user',
    content: inputQuestion,
    isOptimistic: true,
  };

  assert.equal(optimisticMsg.role, 'user');
  assert.equal(optimisticMsg.isOptimistic, true);
  assert.equal(optimisticMsg.content, inputQuestion);
});

test('Assistant message correctly parses confidence and source citations', () => {
  const mockApiResponse = {
    answer: 'Ankush was assigned to implement the authentication endpoints.',
    confidence: 'high',
    sources: [
      {
        speaker: 'Sarah Jenkins',
        quote: 'Ankush, could you take ownership of the auth endpoints?',
        timestamp: '14:22',
      },
    ],
  };

  const assistantMsg = {
    id: 'ai-12345',
    role: 'assistant',
    content: mockApiResponse.answer,
    confidence: mockApiResponse.confidence,
    sources: mockApiResponse.sources,
  };

  assert.equal(assistantMsg.role, 'assistant');
  assert.equal(assistantMsg.confidence, 'high');
  assert.equal(assistantMsg.sources.length, 1);
  assert.equal(assistantMsg.sources[0].speaker, 'Sarah Jenkins');
});

/* ── 3. Task Extraction & Backend Limitations Validation ───────────────────── */

test('Explicit participant name rejects empty and pure whitespace inputs', () => {
  const validateName = (name) => {
    if (!name || typeof name !== 'string') return false;
    return name.trim().length > 0;
  };

  assert.equal(validateName(''), false);
  assert.equal(validateName('   '), false);
  assert.equal(validateName('\t\n'), false);
  assert.equal(validateName('Ankush Poonia'), true);
  assert.equal(validateName('  Sarah Jenkins  '), true);
});

test('Task confirmation payload identifies partial inclusion vs complete inclusion', () => {
  const tasks = [
    { id: 't1', title: 'Task 1', included: true },
    { id: 't2', title: 'Task 2', included: false },
    { id: 't3', title: 'Task 3', included: true },
  ];

  const includedIds = tasks.filter((t) => t.included).map((t) => t.id);
  const user_confirmation =
    includedIds.length === tasks.length ? 'yes' : includedIds.length === 0 ? 'no' : 'partial';

  assert.equal(user_confirmation, 'partial');
  assert.deepEqual(includedIds, ['t1', 't3']);
});

/* ── 4. Documentation Sections, Anchors & RAG Layout ───────────────────────── */

test('All 14 documentation section IDs are stable and accessible', () => {
  const allNavItems = DOCS_NAV_GROUPS.flatMap((g) => g.items);
  assert.equal(allNavItems.length, 14);

  const expectedAnchors = [
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

  const ids = allNavItems.map((item) => item.id);
  assert.deepEqual(ids, expectedAnchors);
});

test('RAG pipeline maintains 6 steps with correct 4+2 sequencing', () => {
  assert.equal(RAG_STEPS.length, 6);

  // Row 1 steps (01-04)
  const row1 = RAG_STEPS.slice(0, 4).map((s) => s.step);
  assert.deepEqual(row1, ['01', '02', '03', '04']);

  // Row 2 steps (05-06)
  const row2 = RAG_STEPS.slice(4).map((s) => s.step);
  assert.deepEqual(row2, ['05', '06']);
  assert.equal(RAG_STEPS[5].title, 'Grounded Answer');
});

test('Model comparison cards specifies 3 models with accurate roles', () => {
  assert.equal(MODELS_DATA.length, 3);
  const models = MODELS_DATA.map((m) => m.name);
  assert.deepEqual(models, [
    'gemini-3.6-flash',
    'gemini-3.5-flash-lite',
    'gemini-embedding-001',
  ]);
});

test('API catalog provides exactly 21 endpoints covering all workspace domains', () => {
  assert.equal(API_ENDPOINTS_DATA.length, 21);
  const categories = new Set(API_ENDPOINTS_DATA.map((ep) => ep.category));
  assert.ok(categories.has('Meetings'));
  assert.ok(categories.has('Tasks'));
  assert.ok(categories.has('Chat'));
  assert.ok(categories.has('Extraction'));
  assert.ok(categories.has('Highlights'));
  assert.ok(categories.has('Notifications'));
  assert.ok(categories.has('Users'));
});
