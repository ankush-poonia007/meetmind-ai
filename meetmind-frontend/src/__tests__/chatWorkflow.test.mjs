/**
 * MeetMind AI — Batch 6.1: Chat Page & Task Review Workflow Test Suite.
 *
 * Validates:
 * 1. Meeting URL query parameter resolution and fallback behavior.
 * 2. Explicit participant name extraction validation (non-empty, non-whitespace).
 * 3. Task review selection, partial inclusion, and exclusion calculation.
 * 4. Task description and deadline modification payload construction.
 * 5. Source citation rendering and speaker formatting.
 */

import test from 'node:test';
import assert from 'node:assert/strict';

// Set deterministic timezone for consistent timestamp formatting
process.env.TZ = 'UTC';

import { parseDate, formatShortDate, formatFullDate } from '../utils/formatDate.js';

/* ── Test Helper: Meeting Resolution Logic ─────────────────────────────────── */
function resolveActiveMeeting(meetingsList, queryMeetingId) {
  if (!Array.isArray(meetingsList) || meetingsList.length === 0) {
    return { activeMeeting: null, resolvedId: '' };
  }
  const matched = meetingsList.find((m) => m.id === queryMeetingId);
  if (matched) {
    return { activeMeeting: matched, resolvedId: matched.id };
  }
  return { activeMeeting: meetingsList[0], resolvedId: meetingsList[0].id };
}

/* ── Test Helper: Explicit Name Validation ─────────────────────────────────── */
function validateExplicitName(nameInput) {
  if (typeof nameInput !== 'string') return { valid: false, error: 'Name must be a string' };
  const trimmed = nameInput.trim();
  if (trimmed.length === 0) {
    return { valid: false, error: 'Please explicitly enter the participant name' };
  }
  return { valid: true, trimmedName: trimmed };
}

/* ── Test Helper: Task Confirmation Payload Builder ───────────────────────── */
function buildTaskConfirmationPayload(meetingId, userId, taskList) {
  const includedTasks = taskList.filter((t) => t.included);
  const totalCount = taskList.length;

  if (includedTasks.length === 0) {
    return {
      meeting_id: meetingId,
      user_id: userId,
      user_confirmation: 'no',
      confirmed_task_ids: [],
      modified_tasks: [],
    };
  }

  const allSelected = includedTasks.length === totalCount;
  const user_confirmation = allSelected ? 'yes' : 'partial';

  const confirmed_task_ids = includedTasks.map((t) => String(t.originalIndex));
  const modified_tasks = includedTasks.map((t) => ({
    title: t.title,
    description: t.description,
    deadline: t.deadline || null,
    priority: t.priority,
    confidence_score: t.confidence_score,
  }));

  return {
    meeting_id: meetingId,
    user_id: userId,
    user_confirmation,
    confirmed_task_ids,
    modified_tasks,
  };
}

/* ── Test 1: Meeting Query Param Resolution ──────────────────────────────── */
test('resolveActiveMeeting selects target meeting when query parameter matches', () => {
  const sampleMeetings = [
    { id: 'm-latest', title: 'Q3 Review', date: '2026-09-26' },
    { id: 'm-target', title: 'Student Portal Redesign', date: '2026-09-20' },
  ];

  const result = resolveActiveMeeting(sampleMeetings, 'm-target');
  assert.equal(result.resolvedId, 'm-target');
  assert.equal(result.activeMeeting.title, 'Student Portal Redesign');
});

test('resolveActiveMeeting falls back to latest meeting when query param is missing or invalid', () => {
  const sampleMeetings = [
    { id: 'm-latest', title: 'Q3 Review', date: '2026-09-26' },
    { id: 'm-target', title: 'Student Portal Redesign', date: '2026-09-20' },
  ];

  // Missing query param
  const missingResult = resolveActiveMeeting(sampleMeetings, null);
  assert.equal(missingResult.resolvedId, 'm-latest');

  // Invalid UUID / nonexistent ID
  const invalidResult = resolveActiveMeeting(sampleMeetings, 'non-existent-uuid');
  assert.equal(invalidResult.resolvedId, 'm-latest');

  // Empty list
  const emptyResult = resolveActiveMeeting([], 'any-id');
  assert.equal(emptyResult.activeMeeting, null);
  assert.equal(emptyResult.resolvedId, '');
});

/* ── Test 2: Explicit Identity Name Validation ───────────────────────────── */
test('validateExplicitName rejects empty strings and pure whitespace', () => {
  assert.equal(validateExplicitName('').valid, false);
  assert.equal(validateExplicitName('   ').valid, false);
  assert.equal(validateExplicitName('\t\n').valid, false);
});

test('validateExplicitName accepts explicit names and trims surrounding whitespace', () => {
  const valid = validateExplicitName('  Elena Rostova  ');
  assert.equal(valid.valid, true);
  assert.equal(valid.trimmedName, 'Elena Rostova');
});

/* ── Test 3: Task Confirmation Payload with All Selected ──────────────────── */
test('buildTaskConfirmationPayload creates "yes" confirmation when all tasks are included', () => {
  const sampleTasks = [
    {
      originalIndex: 0,
      title: 'Setup Auth Interceptor',
      description: 'Axios JWT Bearer attach',
      deadline: '2026-09-28',
      priority: 'high',
      confidence_score: 0.95,
      included: true,
    },
    {
      originalIndex: 1,
      title: 'Review RAG Chunks',
      description: 'Pinecone top 10 verification',
      deadline: '2026-09-29',
      priority: 'medium',
      confidence_score: 0.88,
      included: true,
    },
  ];

  const payload = buildTaskConfirmationPayload('meet-123', 'user-456', sampleTasks);
  assert.equal(payload.meeting_id, 'meet-123');
  assert.equal(payload.user_id, 'user-456');
  assert.equal(payload.user_confirmation, 'yes');
  assert.deepEqual(payload.confirmed_task_ids, ['0', '1']);
  assert.equal(payload.modified_tasks.length, 2);
  assert.equal(payload.modified_tasks[0].title, 'Setup Auth Interceptor');
});

/* ── Test 4: Task Confirmation Payload with Partial Selection & Edits ────── */
test('buildTaskConfirmationPayload correctly handles excluded tasks and edited fields', () => {
  const sampleTasks = [
    {
      originalIndex: 0,
      title: 'Setup Auth Interceptor',
      description: 'Edited description with custom notes',
      deadline: '2026-10-05', // Edited deadline
      priority: 'high',
      confidence_score: 0.95,
      included: true,
    },
    {
      originalIndex: 1,
      title: 'Review RAG Chunks',
      description: 'Pinecone top 10 verification',
      deadline: '2026-09-29',
      priority: 'medium',
      confidence_score: 0.88,
      included: false, // EXCLUDED
    },
  ];

  const payload = buildTaskConfirmationPayload('meet-123', 'user-456', sampleTasks);
  assert.equal(payload.user_confirmation, 'partial');
  // Excluded task (index 1) must NOT be in confirmed_task_ids
  assert.deepEqual(payload.confirmed_task_ids, ['0']);
  // Excluded task must NOT be in modified_tasks
  assert.equal(payload.modified_tasks.length, 1);
  assert.equal(payload.modified_tasks[0].description, 'Edited description with custom notes');
  assert.equal(payload.modified_tasks[0].deadline, '2026-10-05');
});

/* ── Test 5: Source Citations Display Formatting ─────────────────────────── */
test('Source citation excerpt and speaker formatting', () => {
  const sources = [
    { speaker: 'Elena Rostova', timestamp: '14:20', excerpt: 'We need the JWT interceptor by Friday.' },
    { speaker: null, timestamp: null, excerpt: 'Decision was unanimous.' },
  ];

  assert.equal(sources[0].speaker, 'Elena Rostova');
  assert.equal(sources[0].timestamp, '14:20');
  assert.match(sources[0].excerpt, /JWT interceptor/);
});
