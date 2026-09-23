# FEATURES.md — MeetMind AI Meeting Assistant

---

## 1. PROJECT SUMMARY

MeetMind is an agentic AI meeting assistant that transforms raw meeting transcripts into personalized, structured, and actionable intelligence for individual users. A user submits their meeting transcript along with their name, role, and organization through a structured form, and a multi-agent AI pipeline automatically extracts their assigned tasks, key highlights, and important decisions — presenting them for confirmation before adding them to a personal dashboard. MeetMind goes beyond simple summarization by knowing who the user is inside the meeting, speaking directly to their responsibilities, and proactively alerting them via email when deadlines are approaching.

---

## 2. WHAT MAKES MEETMIND UNIQUE

- **Identity-Aware Intelligence:** MeetMind does not extract tasks for everyone — it identifies the specific user inside the transcript using their name and role submitted via the form, and extracts only what is relevant to them. This is personalization at the agent level, not the UI level.

- **PostgreSQL-Driven Agent Pipeline:** Every agent in the pipeline reads its inputs from PostgreSQL, not from chat prompts. The form submission is the single trigger — the database becomes the source of truth for all agent operations. This is a production-grade agentic pattern, not a toy chatbot.

- **Human-in-the-Loop at Confirmation Only:** The only point where the user interacts with the agent pipeline is the Confirmation Agent — which presents extracted tasks and waits for explicit user approval before saving anything. Nothing is added to the dashboard without user consent. This is a deliberate, controlled human-in-the-loop design.

- **Speaker-Aware RAG:** Transcripts are chunked by speaker turn, preserving speaker identity and timestamp in every chunk's metadata. This means retrieval is not just semantically relevant — it is speaker-attributed and identity-filtered, giving the Q&A Agent the ability to answer questions like "What did Rahul say about the schema?" with precision.

- **Context-Rich AI Email Alerts:** Deadline alerts are not templates. The Notification Agent retrieves transcript context for each approaching task using RAG, then composes a natural language email containing the task, its deadline, its description, and the relevant discussion from the original meeting. The user receives everything they need to act, in one email.

- **Meeting-Scoped Q&A with Identity Context:** The Q&A Agent answers questions scoped strictly to one meeting's Pinecone namespace. It also carries the user's identity context into every answer — so responses are personalized to what the user was involved in, not generic meeting summaries.

- **Hybrid Retrieval + Reranking:** MeetMind uses semantic search (Pinecone dense vectors) combined with BM25 keyword search (on PostgreSQL chunks) and a local cross-encoder reranker (BAAI/bge-reranker-v2-m3) — a three-stage retrieval pipeline that significantly outperforms single-method RAG.

---

## 3. FEATURE BREAKDOWN

---

### FEATURE 1 — Multi-Format Transcript Ingestion

**What it does:**
Users can submit their meeting transcript in three ways within the New Meeting form: paste raw text directly into a text area, upload a PDF file, or upload a TXT file. All three input paths are handled by the same UI component and processed by the Ingestion Agent into a unified internal representation.

**Which agent handles it:**
Ingestion Agent — reads the raw transcript from PostgreSQL after form submission, parses PDF or TXT if needed, extracts meeting metadata (title, date, participant names), applies speaker-aware chunking, embeds chunks using gemini-embedding-001, stores vectors to Pinecone under a meeting-specific namespace, and stores raw chunks to the transcript_chunks table in PostgreSQL.

**Why it was included:**
Real meeting data comes in multiple formats. Supporting all three input types removes friction and makes the system usable across different workflows — some users copy-paste from a notes app, others export PDFs from meeting tools. This also demonstrates file parsing as an agentic tool capability.

---

### FEATURE 2 — Form-First Identity Setup

**What it does:**
Before any agent runs, the user provides their name, role, and organization through a structured New Meeting form in the Streamlit frontend. This data is saved to PostgreSQL immediately on form submission. All downstream agents read this identity data directly from the database — no conversational prompt is needed to establish who the user is.

**Which agent handles it:**
Identity Agent — reads the user's name and role from the meeting_participants table in PostgreSQL, searches the transcript chunks for all lines mentioning the user, extracts the user's mentions and role context, and stores the results back to PostgreSQL for the Extraction Agent to consume.

**Why it was included:**
Moving identity input to the form rather than a chat prompt makes the pipeline deterministic, faster, and more reliable. It also reflects a production-grade design decision: structured data collection happens at the boundary of the system (the form), and agents operate on stored data — not on conversational inference.

---

### FEATURE 3 — AI Task Extraction

**What it does:**
After identity is confirmed from the database, the Extraction Agent analyzes the full transcript and the user's extracted mentions to identify every task assigned to or relevant to the identified user. For each task, the agent generates: a short title, an AI-written description explaining what needs to be done, a priority level (high, medium, or low) based on urgency language detected in the transcript, and a deadline if one was mentioned.

**Which agent handles it:**
Extraction Agent — reads user mentions and raw transcript from PostgreSQL, applies ReAct reasoning to identify tasks, calls generate_task_description_tool for each task, calls assign_priority_tool to score urgency, calls extract_highlights_tool for meeting-wide announcements relevant to the user.

**Why it was included:**
This is the core intelligence of MeetMind. Manually reading a 100-line transcript to find your tasks takes time and is error-prone. The Extraction Agent does this in seconds with structured, typed output. It also demonstrates multi-tool ReAct reasoning in a real workflow.

---

### FEATURE 4 — Human-in-the-Loop Task Confirmation

**What it does:**
After extraction, the Confirmation Agent presents the extracted task list to the user in the meeting chat interface. Only the task title and description are shown — no deadlines or priority scores at this stage. The user responds with yes (add all tasks), no (discard all), or partial (select specific tasks). Only confirmed tasks are permanently saved to the tasks table in PostgreSQL and appear on the dashboard.

**Which agent handles it:**
Confirmation Agent — the only agent that interacts with the user directly. Presents tasks via chat, waits for user response, calls save_confirmed_tasks_tool for approved tasks, calls save_confirmed_highlights_tool for approved highlights, discards the rest.

**Why it was included:**
This is a deliberate human-in-the-loop design pattern. AI extraction can make mistakes — a task mentioned near the user's name might not actually be assigned to them. Giving the user final authority over what enters their dashboard prevents noise and builds trust. It also demonstrates a real agentic pattern: AI proposes, human approves, system executes.

---

### FEATURE 5 — Per-Meeting Task Dashboard

**What it does:**
Every meeting has its own task view inside the Workspace. The meeting dashboard shows all confirmed tasks for that meeting with their title, AI-generated description, priority (color-coded: red for high, yellow for medium, green for low), deadline, and current status. Users can toggle any task between pending and complete directly from this view. Key highlights and important announcements from that meeting are shown in a separate highlights section below the task list.

**Which agent handles it:**
No agent — this is served directly by FastAPI reading from PostgreSQL. GET /api/v1/tasks/{user_id}/meeting/{meeting_id} and GET /api/v1/highlights/{user_id}/meeting/{meeting_id}.

**Why it was included:**
Meeting-specific task views allow users to understand the context of each task — which meeting it came from, what was discussed around it, and what else was decided in that session. It mirrors how people naturally think about their work: by the meeting or project, not just by deadline.

---

### FEATURE 6 — Unified Task Dashboard

**What it does:**
The main dashboard view in the Workspace shows all tasks across all meetings in a single unified view. Tasks can be filtered by priority (high, medium, low), by deadline date, and by status (pending, complete). The dashboard is sorted by deadline and priority by default — the most urgent pending tasks appear at the top. Users can toggle task status from this view as well.

**Which agent handles it:**
No agent — served by FastAPI. GET /api/v1/tasks/{user_id} and GET /api/v1/tasks/{user_id}/filter with query parameters.

**Why it was included:**
Users attend multiple meetings and accumulate tasks from many sources. A unified view that cuts across all meetings gives users a single place to manage their full workload. The filter system makes it practical for daily use, not just post-meeting review.

---

### FEATURE 7 — Meeting-Scoped Q&A Chat

**What it does:**
Each meeting has a dedicated chat interface. Users can ask any natural language question about that specific meeting and receive a grounded, source-attributed answer. The Q&A Agent retrieves relevant chunks from that meeting's Pinecone namespace only — answers never bleed across meetings. The agent also carries the user's identity context into every answer, so responses are personalized to what the user was involved in. Chat history is stored in PostgreSQL and displayed on every visit to that meeting's chat page.

**Which agent handles it:**
Q&A Agent — runs hybrid search (semantic + BM25), reranks with bge-reranker-v2-m3 locally, generates answer using gemini-3.6-flash with top 5 reranked chunks as context plus user identity context.

**Why it was included:**
Transcripts contain far more information than just tasks. Users need to ask follow-up questions: what was decided about a topic, what someone said, what the timeline is. A RAG-powered chat that is scoped to one meeting and personalized to the user is significantly more useful than a generic summary.

---

### FEATURE 8 — Context-Rich Email Deadline Alerts

**What it does:**
Every day at 8:00 AM, the Notification Agent automatically checks PostgreSQL for tasks that are due within the next 24 hours, are still marked as pending, and have not yet had an alert sent. For each qualifying task, the agent retrieves the relevant transcript context from Pinecone using RAG, composes a natural language email containing the task title, deadline, AI-written description, and 2-3 lines of relevant meeting context, and sends it to the user's email via Resend. The alert_sent flag is updated in PostgreSQL after each email is sent to prevent duplicate alerts.

**Which agent handles it:**
Notification Agent — triggered by APScheduler inside FastAPI, calls check_deadline_tool, retrieve_task_context_tool, compose_email_tool, send_email_tool, and mark_alert_sent_tool in sequence.

**Why it was included:**
Deadlines get missed when they live only in a dashboard the user might not check. Proactive email alerts with full context — not just a reminder, but everything the user needs to act — is what separates MeetMind from a simple task manager. The AI-composed email body demonstrates the Notification Agent's tool use and reasoning capability in a tangible, real-world output.

---

### FEATURE 9 — Important Meeting Highlights

**What it does:**
Beyond personal tasks, the Extraction Agent also identifies meeting-wide announcements, decisions, and important information that are relevant to the identified user — even if not directly assigned to them. Examples include team-wide deadlines, critical decisions made in the meeting, or important context about other team members' work that the user should be aware of. These highlights are shown in a dedicated section on the per-meeting dashboard.

**Which agent handles it:**
Extraction Agent — calls extract_highlights_tool after task extraction. Highlights are saved by the Confirmation Agent after user approval and served by FastAPI from the highlights table.

**Why it was included:**
Meetings contain important context beyond personal task assignments. A team decision that affects the user's work, a deadline that shifts the project timeline, or an announcement about a team member's blocker — all of these matter to the user even if they are not their personal task. Highlights ensure MeetMind captures the full intelligence of a meeting, not just the action items.

---

## 4. FEATURE DECISION LOG

| Feature | Decision | Reason |
|---------|----------|--------|
| Multi-format transcript ingestion (PDF, TXT, text) | ✅ Included | Core requirement, removes input friction |
| Form-first identity setup | ✅ Included | Production-grade pattern, faster pipeline, no chat prompts for identity |
| AI task extraction with priority + description | ✅ Included | Core intelligence of the system |
| Human-in-the-loop task confirmation | ✅ Included | Prevents noise, demonstrates agentic human-in-the-loop pattern |
| Per-meeting task dashboard | ✅ Included | Meeting-contextual task view, essential UX |
| Unified task dashboard with filters | ✅ Included | Cross-meeting workload management |
| Meeting-scoped Q&A chat | ✅ Included | RAG showcase, high demo value |
| Context-rich email deadline alerts | ✅ Included | Proactive AI output, strongest demo moment |
| Important meeting highlights | ✅ Included | Full meeting intelligence, beyond just tasks |
| User authentication / login system | ❌ Excluded | 45 min build time, zero AI value, single user system |
| Real-time meeting recording | ❌ Excluded | Requires external services, out of 6hr scope |
| Multi-user team dashboard | ❌ Excluded | Adds DB complexity without AI engineering depth |
| Cross-meeting Q&A mode | ❌ Excluded | Scope creep, meeting-scoped Q&A is cleaner and more controllable |
| Mobile push notifications | ❌ Excluded | Email covers alerting, mobile stack adds deployment complexity |
| Contact page | ❌ Excluded | No AI value, replaced by footer links on all pages |
| Task analytics / charts | ❌ Excluded | Time risk, not a core AI engineering showcase |