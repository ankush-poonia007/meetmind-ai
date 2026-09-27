/**
 * MeetMind AI — Dashboard Presentation Mock Data (Section 8 & Section 12)
 * Clean, structured presentation values for Batch 4.2 UI verification.
 * Decoupled from presentation components so it can be replaced seamlessly in Batch 4.3 with live API calls.
 */

export const mockDashboardStats = {
  totalMeetings: 12,
  totalTasks: 47,
  activeTasks: 18,
  completedTasks: 24,
  expiredTasks: 5,
};

export const mockHighlights = [
  {
    id: 'hl-1',
    meetingTitle: 'Platform Core Sprint Planning',
    text: 'Agreed to prioritize WebSocket reconnect resilience and supervisor trace auditing before the sprint close.',
    date: '2026-09-25',
  },
  {
    id: 'hl-2',
    meetingTitle: 'Architecture Review: RAG Pipeline',
    text: 'Reranker model latency reduced by 40% with the introduction of dual vector embedding cache.',
    date: '2026-09-24',
  },
  {
    id: 'hl-3',
    meetingTitle: 'Product Sync: Agent Tracing',
    text: 'Frontend audit log will capture tool calls and supervisor handoffs for complete auditability.',
    date: '2026-09-23',
  },
  {
    id: 'hl-4',
    meetingTitle: 'Client Onboarding: Alpha Feedback',
    text: 'Enterprise pilot requested inline task confirmation buttons directly inside the meeting chat bubble.',
    date: '2026-09-22',
  },
  {
    id: 'hl-5',
    meetingTitle: 'Security & Permissions Workshop',
    text: 'Session storage strategy verified for single-user local credential store with zero third-party token leaks.',
    date: '2026-09-20',
  },
  {
    id: 'hl-6',
    meetingTitle: 'Design System Polish',
    text: 'Finalized Muted Blue theme with Deep Muted Slate Blue sidebar and warm ivory workspace surfaces.',
    date: '2026-09-19',
  },
];

export const mockDeadlines = [
  {
    id: 'task-101',
    title: 'Submit RAG pipeline latency benchmark report',
    dueDate: '2026-09-26',
    priority: 'high',
  },
  {
    id: 'task-102',
    title: 'Finalize identity extraction confidence threshold',
    dueDate: '2026-09-27',
    priority: 'high',
  },
  {
    id: 'task-103',
    title: 'Review supervisor agent orchestration traces',
    dueDate: '2026-09-28',
    priority: 'medium',
  },
  {
    id: 'task-104',
    title: 'Update API endpoint contract for transcript ingestion',
    dueDate: '2026-09-29',
    priority: 'medium',
  },
];
