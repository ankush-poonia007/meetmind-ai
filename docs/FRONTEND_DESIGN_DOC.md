# MEETMIND FRONTEND DESIGN DOCUMENT
# Complete specification for AI-assisted React frontend implementation

---

## SECTION 1 — PROJECT IDENTITY

**Project Name:** MeetMind
**Tagline:** "Your meetings, understood."
**Platform:** Web-only application. No desktop app. No mobile app.
**Purpose:** An agentic AI meeting assistant that ingests transcripts, extracts personalized tasks, manages deadlines, and enables Q&A on meeting content.
**Backend API:** FastAPI running at `http://localhost:8000/api/v1` (dev) / `https://meetmind-api.onrender.com/api/v1` (prod)

**Logo:**
- Text: "MeetMind" in serif font, semi-bold weight
- Icon: A small abstract mark — two overlapping speech bubble shapes forming an "M", rendered in the accent color
- Placement: Top-left of left sidebar navbar, icon left of text
- Size: Icon 28x28px, text 20px

---

## SECTION 2 — TECH STACK

- **Framework:** React 18 (via Vite)
- **Build Tool:** Vite 5
- **Styling:** Plain CSS with CSS custom properties (no Tailwind, no CSS-in-JS)
- **Routing:** React Router v6
- **HTTP Client:** Axios
- **Animations:** CSS keyframes + Intersection Observer API for scroll triggers
- **Icons:** Lucide React (lightweight, consistent)
- **Fonts:** Google Fonts (loaded in index.html)
- **No UI library** — everything hand-crafted per this spec

**Install dependencies:**
```bash
npm create vite@latest meetmind-frontend -- --template react
cd meetmind-frontend
npm install react-router-dom axios lucide-react
```

---

## SECTION 3 — COLOR SYSTEM

All colors defined as CSS custom properties in `:root` inside `src/styles/variables.css`.

```css
:root {
  /* Backgrounds */
  --color-bg-primary: #F7F4EE;        /* cream — main page background */
  --color-bg-secondary: #EDEAE2;      /* slightly darker cream — card bg */
  --color-bg-dark: #111111;           /* near black — contrast sections */
  --color-bg-workspace: #F0EDE6;      /* workspace background */

  /* Text */
  --color-text-primary: #1A1A1A;      /* near black — headings */
  --color-text-secondary: #4A4A4A;    /* dark grey — body text */
  --color-text-muted: #888888;        /* light grey — captions, labels */
  --color-text-inverse: #F7F4EE;      /* cream — text on dark bg */

  /* Accent — Blue/Dark Blue */
  --color-accent-primary: #2563EB;    /* blue — primary CTA, active states */
  --color-accent-dark: #1E40AF;       /* dark blue — hover states */
  --color-accent-light: #DBEAFE;      /* light blue — subtle highlights */
  --color-accent-soft: #EFF6FF;       /* very light blue — bg tints */

  /* Status Colors */
  --color-status-high: #DC2626;       /* red — high priority */
  --color-status-medium: #D97706;     /* amber — medium priority */
  --color-status-low: #16A34A;        /* green — low priority */
  --color-status-complete: #6B7280;   /* grey — completed tasks */
  --color-status-pending: #2563EB;    /* blue — pending tasks */
  --color-status-expired: #991B1B;    /* dark red — expired tasks */

  /* Borders */
  --color-border: #E2DDD6;            /* subtle border */
  --color-border-dark: #C8C2B8;       /* stronger border */

  /* Sidebar */
  --color-sidebar-bg: #1A1A1A;        /* dark sidebar */
  --color-sidebar-text: #D1D5DB;      /* light grey sidebar text */
  --color-sidebar-active: #2563EB;    /* blue active link */
  --color-sidebar-hover: #2A2A2A;     /* subtle hover */
  --color-sidebar-border: #2A2A2A;    /* sidebar section divider */

  /* Shadows */
  --shadow-sm: 0 1px 3px rgba(0,0,0,0.08);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.10);
  --shadow-lg: 0 8px 24px rgba(0,0,0,0.12);
  --shadow-hover: 0 8px 32px rgba(37,99,235,0.15);

  /* Spacing */
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 16px;
  --space-lg: 24px;
  --space-xl: 40px;
  --space-2xl: 64px;
  --space-3xl: 96px;

  /* Border Radius */
  --radius-sm: 6px;
  --radius-md: 12px;
  --radius-lg: 20px;
  --radius-pill: 9999px;

  /* Transitions */
  --transition-fast: 150ms ease;
  --transition-base: 250ms ease;
  --transition-slow: 400ms ease;
}
```

---

## SECTION 4 — TYPOGRAPHY SYSTEM

**Google Fonts to load in `index.html`:**
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
```

**Font Assignments:**
```css
:root {
  --font-serif: 'Playfair Display', Georgia, serif;   /* headings */
  --font-sans: 'Inter', system-ui, sans-serif;         /* body, UI */
}
```

**Type Scale — define in `src/styles/typography.css`:**

```css
/* DISPLAY — hero headline only */
.text-display {
  font-family: var(--font-serif);
  font-size: clamp(48px, 7vw, 96px);
  font-weight: 700;
  line-height: 1.05;
  letter-spacing: -0.02em;
  color: var(--color-text-primary);
}

/* H1 — page titles */
.text-h1 {
  font-family: var(--font-serif);
  font-size: clamp(36px, 5vw, 64px);
  font-weight: 600;
  line-height: 1.15;
  letter-spacing: -0.01em;
  color: var(--color-text-primary);
}

/* H2 — section titles */
.text-h2 {
  font-family: var(--font-serif);
  font-size: clamp(28px, 3.5vw, 48px);
  font-weight: 600;
  line-height: 1.2;
  color: var(--color-text-primary);
}

/* H3 — card titles, sub-sections */
.text-h3 {
  font-family: var(--font-sans);
  font-size: 20px;
  font-weight: 600;
  line-height: 1.3;
  color: var(--color-text-primary);
}

/* BODY LARGE — intro paragraphs */
.text-body-lg {
  font-family: var(--font-sans);
  font-size: 18px;
  font-weight: 400;
  line-height: 1.7;
  color: var(--color-text-secondary);
}

/* BODY — standard text */
.text-body {
  font-family: var(--font-sans);
  font-size: 15px;
  font-weight: 400;
  line-height: 1.6;
  color: var(--color-text-secondary);
}

/* LABEL — tags, status, small caps */
.text-label {
  font-family: var(--font-sans);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--color-text-muted);
}

/* MONO — code, timestamps */
.text-mono {
  font-family: 'Courier New', monospace;
  font-size: 13px;
  color: var(--color-text-secondary);
}
```

**Italic rule:** Use `font-style: italic` on select serif words inside hero headlines for the Wispr-style mixed upright/italic effect. Example: "Your meetings, *understood.*"

---

## SECTION 5 — LAYOUT & NAVIGATION

### Global Layout Structure

```
┌─────────────────────────────────────────────────────────┐
│  LEFT SIDEBAR (fixed, 240px wide, full height)          │
│  Dark background (#1A1A1A)                              │
│  ─────────────────────────────────────────────────────  │
│  [Icon] MeetMind          ← logo at top                 │
│                                                         │
│  NAVIGATION                                             │
│  • Home                                                 │
│  • Workspace                                            │
│  • Documentation                                        │
│  • Contact                                              │
│                                                         │
│  ─────────────────────────────────────────────────────  │
│  WORKSPACE (shown only when on Workspace page)          │
│  • Dashboard                                            │
│  • Meetings                                             │
│  • Tasks                                                │
│  • Chat                                                 │
│                                                         │
│  ─────────────────────────────────────────────────────  │
│  Footer area: version number, GitHub link               │
├─────────────────────────────────────────────────────────┤
│  MAIN CONTENT AREA (margin-left: 240px, full height)    │
│  Scrollable. Each page renders here.                    │
└─────────────────────────────────────────────────────────┘
```

### Sidebar Behavior
- Fixed position, does not scroll with content
- Width: 240px on desktop
- On screens < 768px: sidebar collapses to icons only (48px wide) with tooltip labels on hover
- Active link: left border 3px solid `var(--color-accent-primary)` + text color changes to white
- Hover: background `var(--color-sidebar-hover)` + text brightens
- Workspace sub-links: shown only when current route starts with `/workspace`, hidden otherwise
- Smooth height transition when workspace sub-links expand/collapse

### Sidebar Component Structure
```
<Sidebar>
  <SidebarLogo />           ← icon + "MeetMind" text
  <SidebarNav>              ← main 4 links
    <SidebarLink to="/" label="Home" icon={Home} />
    <SidebarLink to="/workspace" label="Workspace" icon={LayoutDashboard} />
    <SidebarLink to="/docs" label="Documentation" icon={BookOpen} />
    <SidebarLink to="/contact" label="Contact" icon={Mail} />
  </SidebarNav>
  <SidebarDivider />
  <SidebarWorkspaceNav>     ← only visible on /workspace/* routes
    <SidebarLink to="/workspace/dashboard" label="Dashboard" icon={BarChart2} />
    <SidebarLink to="/workspace/meetings" label="Meetings" icon={MessageSquare} />
    <SidebarLink to="/workspace/tasks" label="Tasks" icon={CheckSquare} />
    <SidebarLink to="/workspace/chat" label="Chat" icon={Bot} />
  </SidebarWorkspaceNav>
  <SidebarFooter />         ← version + GitHub icon
</Sidebar>
```

---

## SECTION 6 — ANIMATION SYSTEM

All animations defined in `src/styles/animations.css`.

### Animation 1 — Scroll Fade-Up (most common)
Used on: feature cards, section headings, stat blocks, any content block entering viewport.

```css
@keyframes fadeUp {
  from {
    opacity: 0;
    transform: translateY(32px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.animate-fade-up {
  opacity: 0;
  animation: fadeUp 0.6s ease forwards;
}

.animate-fade-up.visible {
  /* triggered by Intersection Observer adding .visible class */
}
```

Implementation: `useScrollAnimation` custom hook uses `IntersectionObserver` to add `.visible` class when element enters viewport. Apply `data-animate="fade-up"` to any element that should animate on scroll.

### Animation 2 — Spinning Text (hero section only)
A circular rotating text ring around an icon, similar to Wispr's dictation page.

```css
@keyframes spinText {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}

.spinning-text-ring {
  animation: spinText 20s linear infinite;
}
```

Implementation: SVG `<textPath>` on a circular `<path>`. Text reads: "AI • Agentic • Meeting Intelligence • Task Extraction • " repeated. Placed around the hero logo mark illustration.

### Animation 3 — Hover Scale + Shadow
Applied to all cards and buttons.

```css
.card {
  transition: transform var(--transition-base), box-shadow var(--transition-base);
}

.card:hover {
  transform: translateY(-4px) scale(1.01);
  box-shadow: var(--shadow-hover);
}

.btn-primary {
  transition: background var(--transition-fast), transform var(--transition-fast), box-shadow var(--transition-fast);
}

.btn-primary:hover {
  background: var(--color-accent-dark);
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(37,99,235,0.3);
}
```

### Animation 4 — Page Transition
When navigating between routes, content fades in.

```css
@keyframes pageFadeIn {
  from { opacity: 0; transform: translateY(16px); }
  to   { opacity: 1; transform: translateY(0); }
}

.page-enter {
  animation: pageFadeIn 0.35s ease forwards;
}
```

Apply `.page-enter` class to the root div of every page component.

### Animation 5 — Sidebar Link Hover
```css
.sidebar-link {
  transition: background var(--transition-fast), border-color var(--transition-fast), color var(--transition-fast);
}
```

### Animation 6 — Loading Skeleton Pulse
For async data loading states in workspace views.

```css
@keyframes skeletonPulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.4; }
}

.skeleton {
  background: var(--color-bg-secondary);
  border-radius: var(--radius-sm);
  animation: skeletonPulse 1.5s ease-in-out infinite;
}
```

---

## SECTION 7 — PAGE 1: LANDING / HOME

Route: `/`
File: `src/pages/Home.jsx`

### Section 1 — Hero
Full viewport height. Cream background.

**Layout:**
- Centered content, max-width 900px, horizontally centered in content area
- Vertically centered with flexbox

**Content:**
```
[LABEL — small caps, muted]
"AI Meeting Assistant"

[HEADLINE — display size, serif]
"Your meetings,
understood."
← "understood." in italic

[SUBTEXT — body large]
"MeetMind ingests your meeting transcripts, identifies your role,
extracts your tasks, and answers your questions — automatically."

[CTA BUTTONS — two]
[Primary] "Open Workspace"  → navigates to /workspace/dashboard
[Secondary] "Read the Docs" → navigates to /docs

[SPINNING TEXT ELEMENT]
Positioned to the right of or below the headline block.
A circular SVG with spinning text ring around a central abstract icon.
The icon is the MeetMind logo mark (two overlapping speech bubbles).
Text on ring: "Agentic AI • Task Extraction • RAG Pipeline • Meeting Intelligence • "
Ring diameter: 220px
```

### Section 2 — Problem Statement
Dark background section (`var(--color-bg-dark)`). Cream text.

**Content:**
```
[LABEL — muted, on dark]
"The problem"

[HEADLINE — H2, serif, inverse color]
"Meetings happen.
*Details get lost.*"

[BODY TEXT — two short paragraphs]
"Every meeting produces tasks, decisions, and deadlines buried in long transcripts.
Finding yours takes time you don't have."

"MeetMind reads the transcript, finds you in it, and gives you only what matters."
```

### Section 3 — Feature Highlights (3 cards)
Back to cream background. Three feature cards side by side.

**Card 1 — Identity-Aware Extraction**
- Icon: `UserCheck` from Lucide
- Title: "Knows who you are"
- Body: "Tell MeetMind your name once. It finds you in the transcript and extracts only your tasks, mentions, and responsibilities."

**Card 2 — Meeting Q&A**
- Icon: `MessageCircle` from Lucide
- Title: "Ask anything"
- Body: "Each meeting has its own AI chat. Ask what was decided, what someone said, or what your deadline is — answered from the transcript."

**Card 3 — Deadline Alerts**
- Icon: `Bell` from Lucide
- Title: "Alerts before it's late"
- Body: "MeetMind monitors your deadlines daily and emails you before they arrive — with full context from the original meeting."

**Card 4 — Multi-Meeting Dashboard**
- Icon: `LayoutDashboard` from Lucide
- Title: "One view, all meetings"
- Body: "Every task across every meeting in one filterable dashboard. Filter by priority, deadline, or status."

Cards animate in with fade-up on scroll, staggered 100ms delay per card.

### Section 4 — How It Works (3 steps)
Alternating layout: step number large on one side, content on the other.

**Step 1:** Upload your transcript (PDF, TXT, or paste)
**Step 2:** MeetMind identifies you and extracts your tasks
**Step 3:** Confirm tasks, then chat, track, and get alerted

### Section 5 — Tech Highlight (dark section)
Dark background. Shows the AI engineering depth simply.

**Content:**
```
[LABEL] "Built with"

[3 horizontal stat blocks]
7 Specialized Agents   |   Hybrid RAG Pipeline   |   Real-Time Tracing
Each with one-line explanation below.
```

### Section 6 — CTA Banner
Cream background. Centered.

```
[H2] "Ready to understand your meetings?"
[Button Primary] "Get Started" → /workspace/dashboard
```

---

## SECTION 8 — PAGE 2: WORKSPACE

Route: `/workspace/*` with sub-routes
File: `src/pages/Workspace.jsx` (layout wrapper)

The workspace is a nested route layout. The left sidebar shows the workspace sub-nav when on any `/workspace/*` route. The main content area renders the active sub-view.

---

### SUB-VIEW 1 — DASHBOARD
Route: `/workspace/dashboard`
File: `src/pages/workspace/Dashboard.jsx`

**Layout: top stat row + two columns below**

**Stat Row (5 cards, horizontal):**
Each stat card: icon + number (large) + label (small).
```
[Calendar]        [CheckSquare]     [Clock]           [CheckCircle]     [AlertCircle]
Total Meetings    Total Tasks       Active Tasks      Completed         Expired
    12                47               18                24                5
```
Cards use `var(--color-bg-secondary)` background, blue accent for the number, hover scale animation.

**Main Content (two columns):**

Left column (60% width):
- **Highlights Panel** — "Recent Highlights" heading
- List of extracted highlights from recent meetings
- Each highlight: meeting name (small, muted) + highlight text + date chip
- Max 8 highlights, "View all" link at bottom

Right column (40% width):
- **Upcoming Deadlines** — tasks due in next 3 days
- Each item: colored priority dot + task title + deadline date
- Color coded: red for today/tomorrow, amber for 2-3 days, green for later

---

### SUB-VIEW 2 — MEETINGS
Route: `/workspace/meetings`
File: `src/pages/workspace/Meetings.jsx`

**Layout: header row + meeting list + new meeting form modal**

**Header Row:**
```
"Meetings"  [h2]                    [Button] "+ New Meeting"
```

**Meeting List:**
Each meeting card (full width, stacked):
```
┌──────────────────────────────────────────────────────┐
│  [Date chip]  Meeting Title                          │
│  Organization • Your Role • HH:MM                   │
│  [Task count chip]  [Highlight count chip]           │
│                              [Open Chat →] button    │
└──────────────────────────────────────────────────────┘
```
Hover: scale + shadow animation.
Click "Open Chat →" navigates to `/workspace/chat?meeting={id}`.

**New Meeting Modal:**
Triggered by "+ New Meeting" button. Full-screen overlay with centered card.

Form sections in order:
```
SECTION 1 — Your Identity
  - Full Name (text input, required)
  - Email Address (email input, required)
  - Your Role in Meeting (text input, required, placeholder: "e.g. Project Manager")

SECTION 2 — Meeting Information
  - Meeting Title (text input, optional)
  - Organization / Team (text input, required)
  - Date (date picker)
  - Time (time picker)

SECTION 3 — Transcript Submission
  Three tab options (pill toggle):
  [Paste Text]  [Upload TXT]  [Upload PDF]

  - Paste Text: large textarea, min-height 240px
  - Upload TXT: drag-and-drop zone + file picker button
  - Upload PDF: drag-and-drop zone + file picker button

[Submit Button] "Create Meeting & Analyze"
← full-width primary button at bottom
← shows loading spinner while API call is in progress
```

---

### SUB-VIEW 3 — TASKS
Route: `/workspace/tasks`
File: `src/pages/workspace/Tasks.jsx`

**Layout: filter bar + task table**

**Filter Bar (horizontal, sticky at top of content):**
```
[Meeting ▼]  [Status ▼]  [Priority ▼]  [Role ▼]  [Deadline range]  [Clear filters]
```
Each filter is a dropdown select. Deadline is a date range picker (two date inputs).

**Task Table:**
```
┌──────────────────────────────────────────────────────────────────────────┐
│ Task Title │ Meeting │ Priority │ Deadline │ Status │ Role │ Actions     │
├────────────┼─────────┼──────────┼──────────┼────────┼──────┼────────────┤
│ Task name  │ Kickoff │ ● High   │ Sep 27   │Pending │ PM   │ [✓ Mark Done]│
└──────────────────────────────────────────────────────────────────────────┘
```
- Priority: colored dot + label (red/amber/green)
- Status: pill badge (blue=pending, grey=complete, red=expired)
- Actions: toggle button — "Mark Done" if pending, "Reopen" if complete
- Row hover: subtle blue-tinted background
- Empty state: centered illustration + "No tasks found. Try adjusting your filters."

---

### SUB-VIEW 4 — CHAT
Route: `/workspace/chat`
File: `src/pages/workspace/Chat.jsx`

**Layout: meeting selector header + chat area**

**Meeting Selector (top bar):**
```
[Select Meeting ▼]   ← dropdown of all meetings
"Chatting about: Project Kickoff — Sep 25, 2026"
```

**Chat Interface:**
Standard chatbot style — messages left/right aligned.

```
┌─────────────────────────────────────────────────────┐
│  Chat area (scrollable)                             │
│                                                     │
│    ┌────────────────────────────┐                   │
│    │ [AI] What tasks were you  │  ← left aligned   │
│    │ assigned in this meeting? │     grey bubble    │
│    └────────────────────────────┘                   │
│                                                     │
│              ┌──────────────────────────────────┐   │
│              │ You have 3 tasks assigned... [AI]│   │
│              └──────────────────────────────────┘   │
│                                   right aligned     │
│                                   blue bubble       │
├─────────────────────────────────────────────────────┤
│  [Type your question...]           [Send →]         │
└─────────────────────────────────────────────────────┘
```

- User messages: right-aligned, blue background (`var(--color-accent-primary)`), white text
- AI messages: left-aligned, `var(--color-bg-secondary)` background, primary text
- AI messages show source attribution below: `Source: [speaker name, timestamp]` in muted small text
- Loading state: three-dot animated typing indicator
- Smooth scroll to bottom on new message
- Confirmation flow (first time for a meeting): AI presents task list, user clicks "Yes, add to dashboard" or "No thanks" buttons rendered as action buttons inside the AI message bubble

---

## SECTION 9 — PAGE 3: DOCUMENTATION

Route: `/docs`
File: `src/pages/Documentation.jsx`

**Layout:** Two-column. Left: sticky mini-nav (like FastAPI docs sidebar). Right: scrollable content.

**Left mini-nav (sticky, 200px wide inside content area):**
```
Overview
├── What is MeetMind
└── How it works

Architecture
├── System Overview
├── Agent Roster
└── RAG Pipeline

Features
├── Transcript Ingestion
├── Identity Detection
├── Task Extraction
├── Q&A Chat
├── Email Alerts
└── Dashboard

Tech Stack
Models Used
API Reference
```

Clicking a link smooth-scrolls to that section heading on the right. Active section highlighted in mini-nav.

**Right content sections:**

Each section uses a consistent pattern:
- `[LABEL]` small caps above
- `[H2]` section title
- Body text (2-3 short paragraphs max)
- One visual element: table, or simple diagram, or code block

**Section: Agent Roster** — rendered as a table:
```
| Agent | Responsibility | Model |
|-------|---------------|-------|
| Supervisor | Orchestrates pipeline | gemini-3.6-flash |
| Ingestion | Parses + embeds transcript | gemini-3.5-flash-lite |
| Identity | Finds user in transcript | gemini-3.5-flash-lite |
| Extraction | Extracts tasks + highlights | gemini-3.5-flash-lite |
| Confirmation | Gets user approval | gemini-3.5-flash-lite |
| Q&A | Answers meeting questions | gemini-3.6-flash |
| Notification | Sends deadline emails | gemini-3.5-flash-lite |
```

**Section: Tech Stack** — rendered as a two-column grid of tech cards:
Each card: technology name + one-line purpose.

**Section: RAG Pipeline** — simple three-step visual:
```
[Transcript] → [Chunk + Embed] → [Pinecone] → [Hybrid Search] → [Rerank] → [Answer]
```
Rendered as horizontal steps with connecting arrows, box per step.

---

## SECTION 10 — PAGE 4: CONTACT

Route: `/contact`
File: `src/pages/Contact.jsx`

**Layout:** Two columns. Left: contact info. Right: contact form.

**Left column:**
```
[H2] "Get in touch"
[Body] "Have a question about MeetMind, want to collaborate, or
just want to say hello?"

[Icon + Text links]
📧 ankush@email.com
🐙 github.com/ankush-poonia007
💼 linkedin.com/in/ankush
📱 +91 XXXXXXXXXX
```

**Right column — Contact Form:**
```
Full Name        (text input)
Email Address    (email input)
Category         (select: General Query / Collaboration / Bug Report / Other)
Subject          (text input)
Message          (textarea, min-height 160px)

[Send Message →] (primary button, full width)
```

On submit: form data composes a mailto link and opens the user's email client. No backend needed for this form. Simple and reliable.

**Below form:** Three social link cards (GitHub, LinkedIn, Email) with icon + label + hover animation.

---

## SECTION 11 — COMPONENT LIBRARY

All reusable components in `src/components/`.

### Buttons
```jsx
// Primary
<Button variant="primary" onClick={fn}>Label</Button>
// Secondary (outlined)
<Button variant="secondary" onClick={fn}>Label</Button>
// Ghost (text only with hover)
<Button variant="ghost" onClick={fn}>Label</Button>
// Icon button
<IconButton icon={Send} onClick={fn} label="Send" />
```

CSS:
```css
.btn-primary {
  background: var(--color-accent-primary);
  color: white;
  padding: 12px 24px;
  border-radius: var(--radius-pill);
  font-family: var(--font-sans);
  font-size: 15px;
  font-weight: 500;
  border: none;
  cursor: pointer;
  transition: background var(--transition-fast), transform var(--transition-fast), box-shadow var(--transition-fast);
}

.btn-primary:hover {
  background: var(--color-accent-dark);
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(37,99,235,0.3);
}

.btn-secondary {
  background: transparent;
  color: var(--color-text-primary);
  border: 1.5px solid var(--color-border-dark);
  padding: 12px 24px;
  border-radius: var(--radius-pill);
  font-family: var(--font-sans);
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  transition: border-color var(--transition-fast), color var(--transition-fast), transform var(--transition-fast);
}

.btn-secondary:hover {
  border-color: var(--color-accent-primary);
  color: var(--color-accent-primary);
  transform: translateY(-2px);
}
```

### Cards
```css
.card {
  background: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  padding: var(--space-lg);
  transition: transform var(--transition-base), box-shadow var(--transition-base);
}

.card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-hover);
}
```

### Badge / Chip
```css
.badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: var(--radius-pill);
  font-family: var(--font-sans);
  font-size: 12px;
  font-weight: 500;
}

.badge-high     { background: #FEE2E2; color: #DC2626; }
.badge-medium   { background: #FEF3C7; color: #D97706; }
.badge-low      { background: #DCFCE7; color: #16A34A; }
.badge-pending  { background: #DBEAFE; color: #2563EB; }
.badge-complete { background: #F3F4F6; color: #6B7280; }
.badge-expired  { background: #FEE2E2; color: #991B1B; }
```

### Input
```css
.input {
  width: 100%;
  padding: 10px 14px;
  border: 1.5px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-family: var(--font-sans);
  font-size: 15px;
  color: var(--color-text-primary);
  background: white;
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
  outline: none;
}

.input:focus {
  border-color: var(--color-accent-primary);
  box-shadow: 0 0 0 3px rgba(37,99,235,0.12);
}
```

### Modal Overlay
```css
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.5);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-card {
  background: white;
  border-radius: var(--radius-lg);
  padding: var(--space-xl);
  max-width: 600px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
}
```

### Skeleton Loader
```jsx
<Skeleton width="100%" height="20px" />
<Skeleton width="60%" height="20px" />
```

### Typing Indicator (chat)
```css
@keyframes typingDot {
  0%, 60%, 100% { transform: translateY(0); }
  30%           { transform: translateY(-6px); }
}

.typing-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--color-text-muted);
  animation: typingDot 1.2s infinite;
}

.typing-dot:nth-child(2) { animation-delay: 0.2s; }
.typing-dot:nth-child(3) { animation-delay: 0.4s; }
```

---

## SECTION 12 — API INTEGRATION MAP

All API calls in `src/services/api.js`.

```javascript
import axios from 'axios';

const API = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  headers: { 'Content-Type': 'application/json' }
});

// Users
export const registerUser = (data) => API.post('/users/register', data);
export const getUser = (userId) => API.get(`/users/${userId}`);

// Meetings
export const createMeeting = (data) => API.post('/meetings/', data);
export const getMeetings = (userId) => API.get(`/meetings/${userId}`);
export const getMeetingDetail = (meetingId) => API.get(`/meetings/${meetingId}/detail`);

// Tasks
export const getAllTasks = (userId) => API.get(`/tasks/${userId}`);
export const getMeetingTasks = (userId, meetingId) => API.get(`/tasks/${userId}/meeting/${meetingId}`);
export const updateTaskStatus = (taskId, status) => API.put(`/tasks/${taskId}/status`, { status });
export const filterTasks = (userId, params) => API.get(`/tasks/${userId}/filter`, { params });

// Chat
export const sendMessage = (meetingId, data) => API.post(`/chat/${meetingId}/message`, data);
export const getChatHistory = (meetingId) => API.get(`/chat/${meetingId}/history`);

// Extraction
export const runExtraction = (meetingId) => API.post(`/extraction/${meetingId}/run`);
export const getExtractionPreview = (meetingId) => API.get(`/extraction/${meetingId}/preview`);
export const confirmExtraction = (meetingId, data) => API.post(`/extraction/${meetingId}/confirm`, data);

// Highlights
export const getMeetingHighlights = (userId, meetingId) => API.get(`/highlights/${userId}/meeting/${meetingId}`);
export const getAllHighlights = (userId) => API.get(`/highlights/${userId}`);
```

**Environment variable:**
```
VITE_API_BASE_URL=http://localhost:8000/api/v1
```
In `frontend/.env`.

**User session:** Store `user_id` in `localStorage` after registration. Read on every API call. No auth token needed (single user system).

---

## SECTION 13 — FOLDER STRUCTURE

```
meetmind-frontend/
├── public/
│   └── favicon.svg          ← MeetMind logo mark as SVG
│
├── src/
│   ├── main.jsx             ← React entry, Router setup
│   ├── App.jsx              ← Root layout: Sidebar + <Outlet>
│   │
│   ├── pages/
│   │   ├── Home.jsx
│   │   ├── Documentation.jsx
│   │   ├── Contact.jsx
│   │   └── workspace/
│   │       ├── Workspace.jsx    ← layout wrapper for workspace
│   │       ├── Dashboard.jsx
│   │       ├── Meetings.jsx
│   │       ├── Tasks.jsx
│   │       └── Chat.jsx
│   │
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Sidebar.jsx
│   │   │   ├── SidebarLink.jsx
│   │   │   └── SidebarFooter.jsx
│   │   ├── ui/
│   │   │   ├── Button.jsx
│   │   │   ├── Badge.jsx
│   │   │   ├── Card.jsx
│   │   │   ├── Input.jsx
│   │   │   ├── Modal.jsx
│   │   │   ├── Skeleton.jsx
│   │   │   ├── Spinner.jsx
│   │   │   └── TypingIndicator.jsx
│   │   ├── home/
│   │   │   ├── HeroSection.jsx
│   │   │   ├── SpinningText.jsx
│   │   │   ├── FeatureCards.jsx
│   │   │   ├── HowItWorks.jsx
│   │   │   ├── TechHighlight.jsx
│   │   │   └── CTABanner.jsx
│   │   ├── workspace/
│   │   │   ├── StatCard.jsx
│   │   │   ├── HighlightPanel.jsx
│   │   │   ├── DeadlinePanel.jsx
│   │   │   ├── MeetingCard.jsx
│   │   │   ├── NewMeetingForm.jsx
│   │   │   ├── TaskTable.jsx
│   │   │   ├── TaskRow.jsx
│   │   │   ├── FilterBar.jsx
│   │   │   ├── ChatBubble.jsx
│   │   │   ├── ChatInput.jsx
│   │   │   └── MeetingSelector.jsx
│   │   └── docs/
│   │       ├── DocsSidebar.jsx
│   │       ├── DocsSection.jsx
│   │       ├── AgentTable.jsx
│   │       ├── TechGrid.jsx
│   │       └── RagDiagram.jsx
│   │
│   ├── hooks/
│   │   ├── useScrollAnimation.js   ← Intersection Observer hook
│   │   ├── useUser.js              ← reads/writes userId from localStorage
│   │   └── useApi.js               ← generic fetch hook with loading/error state
│   │
│   ├── services/
│   │   └── api.js                  ← all axios calls
│   │
│   ├── styles/
│   │   ├── variables.css           ← all CSS custom properties
│   │   ├── typography.css          ← type scale classes
│   │   ├── animations.css          ← all keyframes + animation classes
│   │   ├── global.css              ← reset, body, * box-sizing
│   │   └── layout.css              ← sidebar + main content layout
│   │
│   └── utils/
│       └── formatDate.js           ← date formatting helpers
│
├── index.html                      ← Google Fonts loaded here
├── vite.config.js
├── .env
├── .env.example
└── package.json
```

---

## SECTION 14 — WHAT THE AI MUST NOT DO

These are hard rules. The AI implementing this must follow them without exception.

1. **Do not use Tailwind CSS.** All styling is plain CSS with CSS custom properties defined in variables.css.
2. **Do not install any UI component library** (no MUI, no Chakra, no Radix, no shadcn). Build all components from scratch per this spec.
3. **Do not use inline styles** except for dynamic values (e.g., animation delay on staggered cards). All static styles go in CSS files.
4. **Do not create any backend code.** This document covers frontend only.
5. **Do not invent API endpoints.** Use only the 21 endpoints listed in Section 12.
6. **Do not add pages or routes not listed** in this document.
7. **Do not use screenshots** anywhere in the UI. All visuals are CSS-based diagrams, SVG illustrations, or icon + text.
8. **Do not add authentication flows.** User identity is stored in localStorage. No login page. No auth tokens.
9. **Do not over-animate.** Use only the 6 animation types defined in Section 6. No additional animation libraries.
10. **Do not use class names from Tailwind** (no `flex`, `p-4`, `text-xl` etc. as class names). Use the class names defined in this document.
11. **Do not change the color values.** Use only the hex codes and CSS variables defined in Section 3.
12. **Do not change the fonts.** Playfair Display for headings, Inter for body. No substitutions.
13. **Do not add a top horizontal navbar.** Navigation is sidebar-only.
14. **Do not make the contact form post to a backend.** Use mailto: link on submit.
15. **Do not add any feature not described in this document.** If something is unclear, leave a TODO comment and move on. Do not invent.
