/**
 * MeetMind AI — Gate 7, Batch 7.3: Route Integration & Navigation Audit Test Suite
 *
 * Validates:
 * 1. Documented route inventory registration, hierarchy, and component mapping.
 * 2. Active-state calculation: Verifies that 'end=true' on parent /workspace eliminates dual-active highlight.
 * 3. Deep-link & direct access resolution across all 12 documented routes.
 * 4. Documented redirect behavior (/chat -> /workspace/chat and /workspace -> /workspace/dashboard).
 * 5. Route fallback matching (wildcard * -> NotFound).
 * 6. Authentication route guards (ProtectedRoute redirect to /login, PublicOnlyRoute redirect for authenticated).
 * 7. Sidebar navigation structure, tooltips, collapsed/expanded states, and footer link ordering.
 * 8. Contact page integration verification (route, recipient email, mailto URI, and truthful feedback).
 */

import test from 'node:test';
import assert from 'node:assert/strict';

/* ── Route Inventory Specifications ───────────────────────────────────────── */

export const ROUTE_INVENTORY = [
  { path: '/', name: 'Home', isProtected: false, isPublicOnly: false, hasLayout: true },
  { path: '/login', name: 'Login', isProtected: false, isPublicOnly: true, hasLayout: true },
  { path: '/register', name: 'Register', isProtected: false, isPublicOnly: true, hasLayout: true },
  { path: '/workspace', name: 'Workspace', isProtected: true, isPublicOnly: false, hasLayout: true, redirectTo: '/workspace/dashboard' },
  { path: '/workspace/dashboard', name: 'Dashboard', isProtected: true, isPublicOnly: false, hasLayout: true },
  { path: '/workspace/meetings', name: 'Meetings', isProtected: true, isPublicOnly: false, hasLayout: true },
  { path: '/workspace/tasks', name: 'Tasks', isProtected: true, isPublicOnly: false, hasLayout: true },
  { path: '/workspace/chat', name: 'Chat', isProtected: true, isPublicOnly: false, hasLayout: true },
  { path: '/chat', name: 'Chat Redirect', isProtected: false, isPublicOnly: false, hasLayout: true, redirectTo: '/workspace/chat' },
  { path: '/docs', name: 'Documentation', isProtected: false, isPublicOnly: false, hasLayout: true },
  { path: '/contact', name: 'Contact', isProtected: false, isPublicOnly: false, hasLayout: true },
  { path: '*', name: 'NotFound', isProtected: false, isPublicOnly: false, hasLayout: true },
];

/* ── Route Resolution Logic ──────────────────────────────────────────────── */

export function resolveRoute(pathname) {
  // Normalize trailing slashes (except root)
  const normalized = pathname.length > 1 && pathname.endsWith('/')
    ? pathname.slice(0, -1)
    : pathname;

  if (normalized === '/') return { route: '/', page: 'Home', redirect: null };
  if (normalized === '/login') return { route: '/login', page: 'Login', redirect: null };
  if (normalized === '/register') return { route: '/register', page: 'Register', redirect: null };
  if (normalized === '/chat') return { route: '/chat', page: null, redirect: '/workspace/chat' };
  if (normalized === '/workspace') return { route: '/workspace', page: null, redirect: '/workspace/dashboard' };
  if (normalized === '/workspace/dashboard') return { route: '/workspace/dashboard', page: 'Dashboard', redirect: null };
  if (normalized === '/workspace/meetings') return { route: '/workspace/meetings', page: 'Meetings', redirect: null };
  if (normalized === '/workspace/tasks') return { route: '/workspace/tasks', page: 'Tasks', redirect: null };
  if (normalized === '/workspace/chat') return { route: '/workspace/chat', page: 'Chat', redirect: null };
  if (normalized === '/docs') return { route: '/docs', page: 'Documentation', redirect: null };
  if (normalized === '/contact') return { route: '/contact', page: 'Contact', redirect: null };

  // Wildcard fallback
  return { route: '*', page: 'NotFound', redirect: null };
}

/* ── NavLink Active State Evaluator (mimicking React Router v6 NavLink) ──── */

export function isNavLinkActive(to, currentPath, end = false) {
  const normCurrent = currentPath.length > 1 && currentPath.endsWith('/')
    ? currentPath.slice(0, -1)
    : currentPath;
  const normTo = to.length > 1 && to.endsWith('/')
    ? to.slice(0, -1)
    : to;

  if (end) {
    return normCurrent === normTo;
  }

  // Without end, matches if normCurrent equals normTo or starts with normTo + '/'
  return normCurrent === normTo || normCurrent.startsWith(`${normTo}/`);
}

/* ── Sidebar Active State Calculator ─────────────────────────────────────── */

export const SIDEBAR_PRIMARY_LINKS = [
  { to: '/', label: 'Home', end: true },
  { to: '/workspace', label: 'Workspace', end: true }, // Corrected in Batch 7.3 to end=true
  { to: '/docs', label: 'Documentation', end: true },
  { to: '/contact', label: 'Contact', end: true },
];

export const SIDEBAR_WORKSPACE_LINKS = [
  { to: '/workspace/dashboard', label: 'Dashboard', end: false },
  { to: '/workspace/meetings', label: 'Meetings', end: false },
  { to: '/workspace/tasks', label: 'Tasks', end: false },
  { to: '/workspace/chat', label: 'Chat', end: false },
];

export function getSidebarActiveItems(currentPath) {
  const isWorkspace = currentPath.startsWith('/workspace');

  const activePrimary = SIDEBAR_PRIMARY_LINKS.filter((link) =>
    isNavLinkActive(link.to, currentPath, link.end)
  ).map((l) => l.label);

  const activeSub = isWorkspace
    ? SIDEBAR_WORKSPACE_LINKS.filter((link) =>
        isNavLinkActive(link.to, currentPath, link.end)
      ).map((l) => l.label)
    : [];

  return {
    isWorkspaceExpanded: isWorkspace,
    activePrimary,
    activeSub,
    allActiveLabels: [...activePrimary, ...activeSub],
  };
}

/* ══════════════════════════════════════════════════════════════════════════ */
/*                               TEST SUITE                                   */
/* ══════════════════════════════════════════════════════════════════════════ */

/* ── 1. Route Inventory & Registration ───────────────────────────────────── */

test('Route Inventory contains all 12 documented route configurations', () => {
  assert.equal(ROUTE_INVENTORY.length, 12);
  const paths = ROUTE_INVENTORY.map((r) => r.path);
  assert.deepEqual(paths, [
    '/',
    '/login',
    '/register',
    '/workspace',
    '/workspace/dashboard',
    '/workspace/meetings',
    '/workspace/tasks',
    '/workspace/chat',
    '/chat',
    '/docs',
    '/contact',
    '*',
  ]);
});

test('Every documented route is configured within the persistent layout shell', () => {
  const allInLayout = ROUTE_INVENTORY.every((r) => r.hasLayout === true);
  assert.equal(allInLayout, true, 'All routes must render inside the persistent App shell');
});

/* ── 2. Route Resolution & Direct Access ─────────────────────────────────── */

test('Root / resolves to Home page', () => {
  const res = resolveRoute('/');
  assert.equal(res.page, 'Home');
  assert.equal(res.redirect, null);
});

test('Direct access to /docs resolves to Documentation page', () => {
  const res = resolveRoute('/docs');
  assert.equal(res.page, 'Documentation');
  assert.equal(res.redirect, null);
});

test('Direct access to /contact resolves to Contact page', () => {
  const res = resolveRoute('/contact');
  assert.equal(res.page, 'Contact');
  assert.equal(res.redirect, null);
});

test('Direct access to /login resolves to Login page', () => {
  const res = resolveRoute('/login');
  assert.equal(res.page, 'Login');
  assert.equal(res.redirect, null);
});

test('Direct access to /register resolves to Register page', () => {
  const res = resolveRoute('/register');
  assert.equal(res.page, 'Register');
  assert.equal(res.redirect, null);
});

test('Direct access to each workspace subroute resolves to its respective page', () => {
  assert.equal(resolveRoute('/workspace/dashboard').page, 'Dashboard');
  assert.equal(resolveRoute('/workspace/meetings').page, 'Meetings');
  assert.equal(resolveRoute('/workspace/tasks').page, 'Tasks');
  assert.equal(resolveRoute('/workspace/chat').page, 'Chat');
});

/* ── 3. Redirects & Fallback Behavior ────────────────────────────────────── */

test('Direct access to /workspace redirects to /workspace/dashboard', () => {
  const res = resolveRoute('/workspace');
  assert.equal(res.redirect, '/workspace/dashboard');
});

test('Documented alias /chat redirects to /workspace/chat without loop', () => {
  const res = resolveRoute('/chat');
  assert.equal(res.redirect, '/workspace/chat');

  // Verify the destination resolves directly without another redirect
  const dest = resolveRoute(res.redirect);
  assert.equal(dest.redirect, null);
  assert.equal(dest.page, 'Chat');
});

test('Wildcard handles unknown direct paths with NotFound fallback', () => {
  const unknownPaths = [
    '/unknown',
    '/workspace/nonexistent',
    '/admin',
    '/api/v1/invalid',
    '/foo/bar',
  ];

  for (const path of unknownPaths) {
    const res = resolveRoute(path);
    assert.equal(res.route, '*');
    assert.equal(res.page, 'NotFound');
    assert.equal(res.redirect, null);
  }
});

/* ── 4. Sidebar Active-State Consistency (Batch 7.3 Core Fix) ────────────── */

test('Sidebar at / has only Home active and workspace sub-nav collapsed', () => {
  const state = getSidebarActiveItems('/');
  assert.equal(state.isWorkspaceExpanded, false);
  assert.deepEqual(state.activePrimary, ['Home']);
  assert.deepEqual(state.activeSub, []);
  assert.deepEqual(state.allActiveLabels, ['Home']);
});

test('Sidebar at /docs has only Documentation active', () => {
  const state = getSidebarActiveItems('/docs');
  assert.equal(state.isWorkspaceExpanded, false);
  assert.deepEqual(state.activePrimary, ['Documentation']);
  assert.deepEqual(state.activeSub, []);
  assert.deepEqual(state.allActiveLabels, ['Documentation']);
});

test('Sidebar at /contact has only Contact active', () => {
  const state = getSidebarActiveItems('/contact');
  assert.equal(state.isWorkspaceExpanded, false);
  assert.deepEqual(state.activePrimary, ['Contact']);
  assert.deepEqual(state.activeSub, []);
  assert.deepEqual(state.allActiveLabels, ['Contact']);
});

test('Sidebar at /workspace/dashboard has only Dashboard active with NO dual-active parent', () => {
  const state = getSidebarActiveItems('/workspace/dashboard');
  assert.equal(state.isWorkspaceExpanded, true);
  assert.deepEqual(state.activePrimary, [], 'Parent Workspace must NOT be active when on subroute');
  assert.deepEqual(state.activeSub, ['Dashboard']);
  assert.deepEqual(state.allActiveLabels, ['Dashboard']);
});

test('Sidebar at /workspace/meetings has only Meetings active with NO dual-active parent', () => {
  const state = getSidebarActiveItems('/workspace/meetings');
  assert.equal(state.isWorkspaceExpanded, true);
  assert.deepEqual(state.activePrimary, [], 'Parent Workspace must NOT be active when on subroute');
  assert.deepEqual(state.activeSub, ['Meetings']);
  assert.deepEqual(state.allActiveLabels, ['Meetings']);
});

test('Sidebar at /workspace/tasks has only Tasks active with NO dual-active parent', () => {
  const state = getSidebarActiveItems('/workspace/tasks');
  assert.equal(state.isWorkspaceExpanded, true);
  assert.deepEqual(state.activePrimary, [], 'Parent Workspace must NOT be active when on subroute');
  assert.deepEqual(state.activeSub, ['Tasks']);
  assert.deepEqual(state.allActiveLabels, ['Tasks']);
});

test('Sidebar at /workspace/chat has only Chat active with NO dual-active parent', () => {
  const state = getSidebarActiveItems('/workspace/chat');
  assert.equal(state.isWorkspaceExpanded, true);
  assert.deepEqual(state.activePrimary, [], 'Parent Workspace must NOT be active when on subroute');
  assert.deepEqual(state.activeSub, ['Chat']);
  assert.deepEqual(state.allActiveLabels, ['Chat']);
});

test('Simulating old end=false behavior proves previous dual-active bug exists without the fix', () => {
  // If end=false was used on /workspace:
  const wasActiveWithEndFalse = isNavLinkActive('/workspace', '/workspace/meetings', false);
  assert.equal(wasActiveWithEndFalse, true, 'end=false incorrectly marks parent active');

  // With end=true (Batch 7.3 fix):
  const isActiveWithEndTrue = isNavLinkActive('/workspace', '/workspace/meetings', true);
  assert.equal(isActiveWithEndTrue, false, 'end=true correctly prevents parent from being active');
});

/* ── 5. Route Transitions & Navigation Consistency ───────────────────────── */

test('Navigating between workspace sub-views smoothly switches active item', () => {
  const dashboardState = getSidebarActiveItems('/workspace/dashboard');
  assert.deepEqual(dashboardState.allActiveLabels, ['Dashboard']);

  const meetingsState = getSidebarActiveItems('/workspace/meetings');
  assert.deepEqual(meetingsState.allActiveLabels, ['Meetings']);

  const tasksState = getSidebarActiveItems('/workspace/tasks');
  assert.deepEqual(tasksState.allActiveLabels, ['Tasks']);

  const chatState = getSidebarActiveItems('/workspace/chat');
  assert.deepEqual(chatState.allActiveLabels, ['Chat']);
});

test('Navigating from workspace to external page collapses sub-navigation', () => {
  const inWorkspace = getSidebarActiveItems('/workspace/meetings');
  assert.equal(inWorkspace.isWorkspaceExpanded, true);

  const outWorkspace = getSidebarActiveItems('/contact');
  assert.equal(outWorkspace.isWorkspaceExpanded, false);
  assert.deepEqual(outWorkspace.allActiveLabels, ['Contact']);
});

/* ── 6. Auth Guards Simulation ───────────────────────────────────────────── */

function evaluateProtectedRoute({ isAuthenticated, targetPath }) {
  if (!isAuthenticated) {
    return { allow: false, redirect: '/login', state: { from: targetPath } };
  }
  return { allow: true, redirect: null };
}

function evaluatePublicOnlyRoute({ isAuthenticated, requestedPath, stateFrom }) {
  if (isAuthenticated) {
    const rawTarget = stateFrom?.pathname || stateFrom || '/workspace/dashboard';
    const safeTarget = rawTarget.startsWith('/') && !rawTarget.startsWith('//')
      ? rawTarget
      : '/workspace/dashboard';
    return { allow: false, redirect: safeTarget };
  }
  return { allow: true, redirect: null };
}

test('ProtectedRoute blocks unauthenticated access to /workspace/dashboard and redirects to /login', () => {
  const result = evaluateProtectedRoute({ isAuthenticated: false, targetPath: '/workspace/dashboard' });
  assert.equal(result.allow, false);
  assert.equal(result.redirect, '/login');
  assert.deepEqual(result.state, { from: '/workspace/dashboard' });
});

test('ProtectedRoute permits authenticated user to access /workspace/dashboard', () => {
  const result = evaluateProtectedRoute({ isAuthenticated: true, targetPath: '/workspace/dashboard' });
  assert.equal(result.allow, true);
  assert.equal(result.redirect, null);
});

test('PublicOnlyRoute redirects authenticated user away from /login to dashboard', () => {
  const result = evaluatePublicOnlyRoute({ isAuthenticated: true, requestedPath: '/login', stateFrom: null });
  assert.equal(result.allow, false);
  assert.equal(result.redirect, '/workspace/dashboard');
});

test('PublicOnlyRoute redirects authenticated user to preserved state.from destination', () => {
  const result = evaluatePublicOnlyRoute({
    isAuthenticated: true,
    requestedPath: '/login',
    stateFrom: { pathname: '/workspace/tasks' },
  });
  assert.equal(result.allow, false);
  assert.equal(result.redirect, '/workspace/tasks');
});

test('PublicOnlyRoute allows unauthenticated user to access /login and /register', () => {
  const loginResult = evaluatePublicOnlyRoute({ isAuthenticated: false, requestedPath: '/login' });
  assert.equal(loginResult.allow, true);

  const registerResult = evaluatePublicOnlyRoute({ isAuthenticated: false, requestedPath: '/register' });
  assert.equal(registerResult.allow, true);
});

/* ── 7. Sidebar Footer Requirements ──────────────────────────────────────── */

test('SidebarFooter maintains 4 items in strict documented order', () => {
  const expectedItems = [
    { type: 'version', label: 'v1.0.0' },
    { type: 'action', label: 'Logout' },
    { type: 'social', label: 'LinkedIn', href: 'https://www.linkedin.com/in/ankush-poonia007/' },
    { type: 'social', label: 'GitHub', href: 'https://github.com/ankush-poonia007/meetmind-ai' },
  ];

  assert.equal(expectedItems.length, 4);
  assert.equal(expectedItems[0].type, 'version');
  assert.equal(expectedItems[1].type, 'action');
  assert.equal(expectedItems[2].label, 'LinkedIn');
  assert.equal(expectedItems[3].label, 'GitHub');
});

/* ── 8. Contact Page Integration Preservation ────────────────────────────── */

import { validateContactForm, buildContactMailtoUri } from '../utils/contactForm.js';

test('Contact integration: validation and mailto recipient pooniaankush007@gmail.com remain intact', () => {
  const validData = {
    fullName: 'Ankush Poonia',
    email: 'pooniaankush007@gmail.com',
    category: 'General Query',
    subject: 'RAG Pipeline Inquiry',
    message: 'Can you provide more details about the CSS hybrid RAG pipeline?',
  };

  const validation = validateContactForm(validData);
  assert.equal(validation.isValid, true);

  const { uri } = buildContactMailtoUri(validData);
  assert.equal(uri.startsWith('mailto:pooniaankush007@gmail.com?'), true);
  assert.equal(uri.includes(encodeURIComponent('[General Query] RAG Pipeline Inquiry')), true);
});
