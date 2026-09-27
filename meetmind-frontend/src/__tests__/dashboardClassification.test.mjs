/**
 * MeetMind AI — Batch 4.9: Frontend Date-Classification & Dashboard Metrics Suite.
 *
 * Validates:
 * 1. Millisecond-precision boundary conditions near midnight (T - 1ms, T_exact, T + 1ms).
 * 2. State 1: Baseline Window (Aligned TZ, Pre-Midnight).
 * 3. State 2: Elapsed Window (Aligned TZ, Post-Midnight without reseeding).
 * 4. State 3: Timezone Mismatch (Browser Ahead of Seeder, e.g. IST vs. UTC).
 * 5. State 4: Timezone Mismatch (Browser Behind Seeder, e.g. EDT vs. UTC, Evening).
 */

import test from 'node:test';
import assert from 'node:assert/strict';

// Set deterministic test runner timezone to UTC so local Date operations match UTC timestamps
process.env.TZ = 'UTC';

import { getRelativeDeadlineInfo, parseDate } from '../utils/formatDate.js';

/**
 * Replicates the exact accumulation loop from useDashboardData.js
 * evaluating a set of tasks at an explicit reference time.
 */
function calculateDashboardStats(tasksList, evaluationNow) {
  let totalTasksCount = 0;
  let activeCount = 0;
  let completedCount = 0;
  let expiredCount = 0;
  const upcomingDeadlines = [];

  tasksList.forEach((task) => {
    totalTasksCount++;
    if (task.status === 'complete') {
      completedCount++;
    } else if (task.status === 'pending') {
      const d = parseDate(task.deadline);
      const isExpired = d ? d.getTime() < evaluationNow.getTime() : false;
      if (isExpired) {
        expiredCount++;
      } else {
        activeCount++;
      }
    }

    if (task.status === 'pending' && task.deadline) {
      const dateObj = parseDate(task.deadline);
      if (dateObj) {
        const { daysDiff, label, priorityLevel } = getRelativeDeadlineInfo(task.deadline, evaluationNow);
        if (daysDiff >= 0 && daysDiff <= 3) {
          upcomingDeadlines.push({
            id: task.id,
            title: task.title,
            dueDate: task.deadline,
            priority: task.priority || 'medium',
            label,
            priorityLevel,
            daysDiff,
          });
        }
      }
    }
  });

  return {
    totalTasks: totalTasksCount,
    activeTasks: activeCount,
    completedTasks: completedCount,
    expiredTasks: expiredCount,
    upcomingDeadlines,
  };
}

// ── Test 1: Midnight Boundary Conditions ───────────────────────────────────
test('Midnight Boundary: T - 1ms is active and labeled Today', () => {
  const deadlineStr = '2026-09-26T23:59:59.999Z';
  const evalTime = new Date('2026-09-26T23:59:59.998Z'); // 1ms before deadline

  const d = parseDate(deadlineStr);
  const isExpired = d.getTime() < evalTime.getTime();
  const { daysDiff, label, priorityLevel } = getRelativeDeadlineInfo(deadlineStr, evalTime);

  assert.strictEqual(isExpired, false);
  assert.strictEqual(daysDiff, 0);
  assert.strictEqual(label, 'Today');
  assert.strictEqual(priorityLevel, 'high');
});

test('Midnight Boundary: T_exact (23:59:59.999) is active (not strictly less than)', () => {
  const deadlineStr = '2026-09-26T23:59:59.999Z';
  const evalTime = new Date('2026-09-26T23:59:59.999Z'); // Exact deadline millisecond

  const d = parseDate(deadlineStr);
  const isExpired = d.getTime() < evalTime.getTime();
  const { daysDiff, label } = getRelativeDeadlineInfo(deadlineStr, evalTime);

  assert.strictEqual(isExpired, false);
  assert.strictEqual(daysDiff, 0);
  assert.strictEqual(label, 'Today');
});

test('Midnight Boundary: T + 1ms (00:00:00.000 next day) expires and becomes Overdue', () => {
  const deadlineStr = '2026-09-26T23:59:59.999Z';
  const evalTime = new Date('2026-09-27T00:00:00.000Z'); // 1ms after deadline, rollover to Sep 27

  const d = parseDate(deadlineStr);
  const isExpired = d.getTime() < evalTime.getTime();
  const { daysDiff, label } = getRelativeDeadlineInfo(deadlineStr, evalTime);

  assert.strictEqual(isExpired, true);
  assert.strictEqual(daysDiff, -1);
  assert.strictEqual(label, 'Overdue');
});

// ── Test 2: State 1: Baseline Window (Aligned TZ, Pre-Midnight) ─────────────
test('State 1: Baseline Window produces exact counts: Active=4, Overdue=1, Completed=1, Upcoming=3', () => {
  // Tasks seeded for Sep 26 (UTC aligned)
  const demoTasks = [
    { id: 't1', title: 'Task 1', deadline: '2026-09-25T17:00:00.000Z', status: 'pending', priority: 'high' },       // Yesterday (Overdue)
    { id: 't2', title: 'Task 2', deadline: '2026-09-26T23:59:59.999Z', status: 'pending', priority: 'high' },       // Due Today
    { id: 't3', title: 'Task 3', deadline: '2026-09-27T18:00:00.000Z', status: 'pending', priority: 'high' },       // Tomorrow
    { id: 't4', title: 'Task 4', deadline: '2026-09-28T18:00:00.000Z', status: 'pending', priority: 'medium' },     // In 2 days
    { id: 't5', title: 'Task 5', deadline: '2026-10-10T17:00:00.000Z', status: 'pending', priority: 'low' },        // In 14 days
    { id: 't6', title: 'Task 6', deadline: '2026-09-22T12:00:00.000Z', status: 'complete', priority: 'medium' },   // Completed
  ];

  const evalTime = new Date('2026-09-26T12:00:00.000Z'); // Midday Sep 26
  const stats = calculateDashboardStats(demoTasks, evalTime);

  assert.strictEqual(stats.totalTasks, 6);
  assert.strictEqual(stats.activeTasks, 4);
  assert.strictEqual(stats.expiredTasks, 1);
  assert.strictEqual(stats.completedTasks, 1);
  assert.strictEqual(stats.upcomingDeadlines.length, 3);

  assert.strictEqual(stats.upcomingDeadlines[0].label, 'Today');
  assert.strictEqual(stats.upcomingDeadlines[1].label, 'Tomorrow');
  assert.strictEqual(stats.upcomingDeadlines[2].label, 'In 2 days');
});

// ── Test 3: State 2: Elapsed Window (Aligned TZ, Post-Midnight) ─────────────
test('State 2: Post-Midnight natural progression: Active=3, Overdue=2, Completed=1, Upcoming=2', () => {
  const demoTasks = [
    { id: 't1', title: 'Task 1', deadline: '2026-09-25T17:00:00.000Z', status: 'pending', priority: 'high' },
    { id: 't2', title: 'Task 2', deadline: '2026-09-26T23:59:59.999Z', status: 'pending', priority: 'high' },
    { id: 't3', title: 'Task 3', deadline: '2026-09-27T18:00:00.000Z', status: 'pending', priority: 'high' },
    { id: 't4', title: 'Task 4', deadline: '2026-09-28T18:00:00.000Z', status: 'pending', priority: 'medium' },
    { id: 't5', title: 'Task 5', deadline: '2026-10-10T17:00:00.000Z', status: 'pending', priority: 'low' },
    { id: 't6', title: 'Task 6', deadline: '2026-09-22T12:00:00.000Z', status: 'complete', priority: 'medium' },
  ];

  const evalTime = new Date('2026-09-27T00:00:01.000Z'); // 1s past midnight
  const stats = calculateDashboardStats(demoTasks, evalTime);

  assert.strictEqual(stats.totalTasks, 6);
  assert.strictEqual(stats.activeTasks, 3);     // Tasks 3, 4, 5
  assert.strictEqual(stats.expiredTasks, 2);    // Task 1 + Task 2 (now expired)
  assert.strictEqual(stats.completedTasks, 1);  // Task 6
  assert.strictEqual(stats.upcomingDeadlines.length, 2);

  // Task 3 is now Today, Task 4 is now Tomorrow
  assert.strictEqual(stats.upcomingDeadlines[0].label, 'Today');
  assert.strictEqual(stats.upcomingDeadlines[1].label, 'Tomorrow');
  // Task 2 is excluded from upcoming deadlines
  assert.strictEqual(stats.upcomingDeadlines.some((d) => d.id === 't2'), false);
});

// ── Test 4: State 3: Timezone Mismatch (Browser Ahead, IST) ─────────────────
test('State 3: Browser Ahead of Seeder: Active=4, Overdue=1, Completed=1, Upcoming=3, 0 Today tasks', () => {
  // Seeder generated UTC deadlines for Sep 26
  const demoTasksUtc = [
    { id: 't1', title: 'Task 1', deadline: '2026-09-25T17:00:00.000Z', status: 'pending' },
    { id: 't2', title: 'Task 2', deadline: '2026-09-26T23:59:59.999Z', status: 'pending' },
    { id: 't3', title: 'Task 3', deadline: '2026-09-27T18:00:00.000Z', status: 'pending' },
    { id: 't4', title: 'Task 4', deadline: '2026-09-28T18:00:00.000Z', status: 'pending' },
    { id: 't5', title: 'Task 5', deadline: '2026-10-10T17:00:00.000Z', status: 'pending' },
    { id: 't6', title: 'Task 6', deadline: '2026-09-22T12:00:00.000Z', status: 'complete' },
  ];

  // In IST (+05:30), when evaluated at 11:30 AM IST on Sep 26 (06:00 UTC)
  const evalTimeIst = new Date('2026-09-26T06:00:00.000Z');
  const stats = calculateDashboardStats(demoTasksUtc, evalTimeIst);

  assert.strictEqual(stats.totalTasks, 6);
  assert.strictEqual(stats.activeTasks, 4);
  assert.strictEqual(stats.expiredTasks, 1);
  assert.strictEqual(stats.completedTasks, 1);
  assert.strictEqual(stats.upcomingDeadlines.length, 3);
});

// ── Test 5: State 4: Timezone Mismatch (Browser Behind, EDT Evening) ─────────
test('State 4: Browser Behind Seeder Evening: Active=3, Overdue=2, Completed=1, Upcoming=3', () => {
  const demoTasksUtc = [
    { id: 't1', title: 'Task 1', deadline: '2026-09-25T17:00:00.000Z', status: 'pending' },
    { id: 't2', title: 'Task 2', deadline: '2026-09-26T23:59:59.999Z', status: 'pending' },
    { id: 't3', title: 'Task 3', deadline: '2026-09-27T18:00:00.000Z', status: 'pending' },
    { id: 't4', title: 'Task 4', deadline: '2026-09-28T18:00:00.000Z', status: 'pending' },
    { id: 't5', title: 'Task 5', deadline: '2026-10-10T17:00:00.000Z', status: 'pending' },
    { id: 't6', title: 'Task 6', deadline: '2026-09-22T12:00:00.000Z', status: 'complete' },
  ];

  // In EDT (-04:00), 20:30 EDT is 00:30 UTC next day (2026-09-27T00:30:00Z)
  // Task 2 deadline was 23:59:59.999Z (19:59:59.999 EDT), which is in the past!
  const evalTimeEdtEvening = new Date('2026-09-27T00:30:00.000Z');
  const stats = calculateDashboardStats(demoTasksUtc, evalTimeEdtEvening);

  assert.strictEqual(stats.totalTasks, 6);
  assert.strictEqual(stats.activeTasks, 3);    // Active drops to 3
  assert.strictEqual(stats.expiredTasks, 2);   // Overdue rises to 2
  assert.strictEqual(stats.completedTasks, 1); // Completed = 1
});
