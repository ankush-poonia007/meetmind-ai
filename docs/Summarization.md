# SUMMARIZATION.md — MeetMind AI Meeting Assistant
# Complete Project Context for AI System Handoff

---

## SECTION 1 — PROJECT IDENTITY

**Project Name:** MeetMind
**Hackathon:** Domain Verse 1.0 — Internal College Hackathon
**Domain:** Agentic AI
**Problem Statement:** PS-09 — AI Meeting Assistant
**Build Window:** 6 hours (3:00 AM to 9:00 AM)
**Presentation:** 2 rounds — Round 1: 10-minute slides presentation, Round 2: Live demo
**Audience:** Mixed panel (technical + non-technical judges)
**Primary Goal:** Demonstrate AI engineering depth — multi-agent orchestration, RAG, tool use, human-in-the-loop. Frontend and backend are supporting infrastructure. AI orchestration is the product.
**GitHub Repository:** https://github.com/ankush-poonia007/meetmind-ai
**Developer:** Ankush Poonia (First-year B.Tech CS, AI specialization, Arya College of Engineering, Jaipur)
**Stakes:** IIT scholarship opportunity

---

## SECTION 2 — PROBLEM STATEMENT (EXACT)

Students and project teams conduct meetings but lose track of decisions, assigned tasks, and deadlines buried inside long transcripts. Manually reviewing transcripts wastes time and critical action items get missed, causing delays and missed deadlines.

**Core user problem:** Meeting participants cannot efficiently extract their personal responsibilities, decisions, and deadlines from long, multi-person transcripts.

**Why agentic AI:** Multiple specialized agents handle different jobs — one ingests, one identifies the user, one extracts tasks, one confirms with the user, one answers questions, one sends alerts. No single model doing everything. Real orchestration.

**Expected outcome:** A working agentic AI system that ingests meeting transcripts, identifies the current user inside the transcript, extracts their tasks and highlights, manages deadlines, enables conversational Q&A on meeting content, and proactively alerts via email.

---

## SECTION 3 — FINAL FROZEN TECH STACK

### Orchestration & Agents
- **LangChain** — individual agent construction, tool binding, prompt templates
- **LangGraph** — multi-agent orchestration, state management, conditional routing, supervisor pattern

### Agentic Patterns (non-negotiable, must be visible in implementation)
- **ReAct** — every sub-agent reasons before acting
- **Plan-and-Execute** — supervisor generates full plan before routing to sub-agents
- **Multi-Agent Coordination** — 7 agents, each with single narrow responsibility
- **Tool Use** — every agent bound to specific tools only

### Models (final locked)

| Role | Model | Provider |
|------|-------|----------|
| Orchestrator Agent | gemini-3.6-flash | Google Gemini API |
| Sub-Agent Executor | gemini-3.5-flash-lite | Google Gemini API |
| Fallback / Complex Reasoning | thinkingmachines/inkling:free | OpenRouter |
| Backup Orchestrator | openai/gpt-oss-120b | OpenRouter |
| Conditional Finance Domain | inclusionai/ling-3.0-flash-fin:free | OpenRouter |
| Embeddings | models/gemini-embedding-001 | Google Gemini API |
| Reranker | BAAI/bge-reranker-v2-m3 | Local via sentence-transformers |

**Model rules:**
- gemini-3.6-flash → all supervisor-level and Q&A reasoning
- gemini-3.5-flash-lite → all sub-agent execution (fast, lightweight)
- OpenRouter models → fallback only if Gemini quota exhausted
- Reranker → runs locally inside FastAPI container, no external API call
- Finance domain flag → swap sub-agent to ling-3.0-flash-fin:free (not applicable for this project)

### Backend
- FastAPI + Uvicorn
- Pydantic (schemas)
- SQLAlchemy (ORM)
- Alembic (migrations)
- PostgreSQL (primary relational DB)

### Frontend
- Streamlit (minimal, functional, clean)

### Vector Database
- Pinecone (cloud, AWS us-east-1, hackathon-index, 3072 dimensions, cosine metric)
- One namespace per meeting: `meeting_{meeting_id}`

### RAG
- Embedding: gemini-embedding-001 (3072-dim dense vectors)
- Chunking: Speaker-aware (200-300 tokens, 50 token overlap, speaker label preserved)
- Search: Hybrid (semantic via Pinecone + BM25 via rank-bm25 on PostgreSQL)
- Reranker: BAAI/bge-reranker-v2-m3 (local CrossEncoder)
- Metadata per chunk: meeting_id, speaker_name, speaker_role, timestamp, chunk_type, involves_user

### Email
- Resend API (free tier: 3000/month, 100/day)
- Sender: onboarding@resend.dev (no domain verification needed)
- Trigger: APScheduler inside FastAPI, daily at 08:00 AM

### Scheduler
- APScheduler with AsyncIOScheduler inside FastAPI lifespan

### Hosting
- Backend → Render (Web Service)
- Frontend → Vercel
- PostgreSQL → Render Managed PostgreSQL
- Pinecone → Pinecone Cloud

### DevOps
- GitHub (branch-per-gate strategy)
- Each gate = one branch named gate/[gate-name]

---

## SECTION 4 — FINAL FROZEN FEATURE LIST (9 FEATURES)

**FEATURE 1 — Multi-Format Transcript Ingestion**
Users submit transcripts via: paste raw text, upload PDF, upload TXT. All three handled in the New Meeting form. Ingestion Agent processes all formats into unified internal representation.

**FEATURE 2 — Form-First Identity Setup**
User provides name, role, organization, meeting date/time, and transcript in the New Meeting form. This data is saved to PostgreSQL immediately. All agents read identity from DB — no conversational prompting for identity. This replaced the "Who are you?" chat flow.

**FEATURE 3 — AI Task Extraction**
Extraction Agent reads user mentions and full transcript from PostgreSQL. Extracts tasks assigned to or relevant to identified user. Generates: title, AI-written description, priority (high/medium/low based on urgency language), deadline (if mentioned).

**FEATURE 4 — Human-in-the-Loop Task Confirmation**
Confirmation Agent is the ONLY agent that interacts with the user directly. Presents tasks showing title + description only (no deadlines, no priority). User responds: yes (save all), no (discard all), partial (select specific tasks). Only confirmed tasks saved to PostgreSQL dashboard.

**FEATURE 5 — Per-Meeting Task Dashboard**
Each meeting has its own task view: title, description, priority (color-coded), deadline, status toggle (pending/complete). Key highlights shown in separate section below tasks.

**FEATURE 6 — Unified Task Dashboard**
All tasks across all meetings in one view. Filterable by: priority, deadline date, status. Sorted by deadline + priority by default. Status toggle available here too.

**FEATURE 7 — Meeting-Scoped Q&A Chat**
Independent chat per meeting. User asks natural language questions. Q&A Agent retrieves from that meeting's Pinecone namespace ONLY — no cross-meeting answers. Identity context carried into every answer. Chat history stored in PostgreSQL and displayed on revisit.

**FEATURE 8 — Context-Rich Email Deadline Alerts**
Daily 08:00 AM check. Tasks where: status=pending, deadline <= tomorrow, alert_sent=false. For each: RAG retrieves transcript context, AI composes full email (task + deadline + description + 2-3 transcript lines), sent via Resend, alert_sent=true updated in DB.

**FEATURE 9 — Important Meeting Highlights**
Beyond personal tasks, Extraction Agent identifies team-wide decisions, announcements, and important context relevant to the identified user. Shown in "Key Highlights" section on per-meeting dashboard.

**EXCLUDED FEATURES:**
- User authentication → no AI value, 45 min waste
- Real-time recording → out of scope
- Multi-user team dashboard → DB complexity without AI depth
- Cross-meeting Q&A → scope creep
- Mobile notifications → email covers alerting
- Contact page → replaced by footer links

---

## SECTION 5 — FINAL FROZEN AGENT DESIGN (7 AGENTS)

### AGENT 1 — Supervisor Agent
- **Model:** gemini-3.6-flash
- **Pattern:** Plan-and-Execute
- **Responsibility:** Reads meeting from PostgreSQL, generates execution plan, routes to correct sub-agent via session_action, aggregates results
- **Tools:** route_to_agent_tool, aggregate_response_tool
- **Fallback:** thinkingmachines/inkling:free via OpenRouter

### AGENT 2 — Ingestion Agent
- **Model:** gemini-3.5-flash-lite
- **Pattern:** ReAct
- **Responsibility:** Reads raw transcript from PostgreSQL, parses PDF/TXT if needed, extracts metadata, applies speaker-aware chunking, embeds with gemini-embedding-001, stores to Pinecone + transcript_chunks table
- **Tools:** parse_pdf_tool, parse_txt_tool, extract_metadata_tool, store_transcript_tool, embed_and_store_tool

### AGENT 3 — Identity Agent
- **Model:** gemini-3.5-flash-lite
- **Pattern:** ReAct
- **Responsibility:** Reads user name + role from meeting_participants in PostgreSQL, searches transcript for all user mentions, stores mention context back to DB
- **Tools:** search_participant_tool, extract_user_mentions_tool, confirm_identity_tool

### AGENT 4 — Extraction Agent
- **Model:** gemini-3.5-flash-lite
- **Pattern:** ReAct
- **Responsibility:** Reads mentions + transcript from PostgreSQL, extracts tasks + highlights, generates AI descriptions, assigns priority, stores as unconfirmed to DB
- **Tools:** extract_tasks_tool, generate_task_description_tool, assign_priority_tool, extract_highlights_tool

### AGENT 5 — Confirmation Agent
- **Model:** gemini-3.5-flash-lite
- **Pattern:** ReAct
- **Responsibility:** ONLY human-in-the-loop point. Presents tasks (title + description only) to user in chat, waits for yes/no/partial, saves confirmed data to PostgreSQL, discards rest
- **Tools:** present_tasks_tool, save_confirmed_tasks_tool, save_confirmed_highlights_tool

### AGENT 6 — Q&A Agent
- **Model:** gemini-3.6-flash
- **Pattern:** ReAct
- **Responsibility:** Independent from main pipeline. Hybrid RAG on meeting namespace only. Identity-aware. Reranked. Source-attributed answers. Chat history maintained.
- **Tools:** hybrid_search_tool, rerank_tool, generate_answer_tool

### AGENT 7 — Notification Agent
- **Model:** gemini-3.5-flash-lite
- **Pattern:** ReAct
- **Responsibility:** APScheduler-triggered daily at 08:00 AM. Checks DB for approaching deadlines, retrieves RAG context per task, AI-composes email, sends via Resend, marks alert_sent=true
- **Tools:** check_deadline_tool, retrieve_task_context_tool, compose_email_tool, send_email_tool, mark_alert_sent_tool

---

## SECTION 6 — FINAL FROZEN LANGGRAPH FLOW

### State Schema
```python
class MeetMindState(TypedDict):
    user_id: str
    session_action: str          # ingest|identify|extract|confirm|qa|notify|complete
    meeting_id: str
    meeting_title: str
    meeting_date: str
    input_format: str
    raw_transcript: str
    participants: list[dict]
    chunks_stored: int
    pinecone_namespace: str
    ingestion_complete: bool
    user_name: str
    user_role: str
    user_mentions: list[str]
    identity_confirmed: bool
    extracted_tasks: list[dict]
    extracted_highlights: list[dict]
    extraction_complete: bool
    user_confirmation: str       # yes|no|partial
    confirmed_task_ids: list[str]
    saved_tasks: int
    confirmation_complete: bool
    user_question: str
    retrieved_chunks: list[str]
    reranked_chunks: list[str]
    qa_answer: str
    qa_sources: list[dict]
    tasks_due_soon: list[dict]
    alerts_sent: int
    error: Optional[str]
    final_response: str
```

### Graph Nodes
```
supervisor_node → ingestion_node → identity_node → extraction_node → confirmation_node
                                                                    → qa_node (independent)
                                                                    → notification_node (scheduled)
```

### Routing Logic
```python
def supervisor_router(state: MeetMindState) -> str:
    routes = {
        "ingest":   "ingestion_node",
        "identify": "identity_node",
        "extract":  "extraction_node",
        "confirm":  "confirmation_node",
        "qa":       "qa_node",
        "notify":   "notification_node"
    }
    return routes.get(state["session_action"], END)

def confirmation_router(state: MeetMindState) -> str:
    if state["user_confirmation"] == "yes":      return "save_all"
    elif state["user_confirmation"] == "partial": return "save_partial"
    else:                                         return END
```

### Main Pipeline Sequence (new meeting)
```
Form submitted → FastAPI saves to PostgreSQL → pipeline triggered
→ Supervisor (reads DB, generates plan)
→ Ingestion Agent (parse → chunk → embed → Pinecone + PostgreSQL)
→ Identity Agent (read DB → search transcript → store mentions)
→ Extraction Agent (read DB → extract tasks + highlights → store unconfirmed)
→ Confirmation Agent (present to user → user confirms → save to DB)
→ Dashboard updated via FastAPI
```

### Q&A Pipeline (independent, any time after ingestion)
```
User question → Supervisor routes to Q&A Agent
→ Hybrid search (Pinecone semantic + BM25 PostgreSQL)
→ Merge + deduplicate (15-20 chunks)
→ BGE Reranker (local, top 5)
→ Generate answer (gemini-3.6-flash, top 5 chunks + identity context)
→ Store chat message → return answer + sources
```

### Notification Pipeline (daily 08:00 AM)
```
APScheduler fires → Supervisor routes to Notification Agent
→ Check DB (pending tasks, deadline <= tomorrow, alert_sent=false)
→ For each task: RAG retrieval (top 3 chunks) → compose email → send via Resend → mark alert_sent=true
```

### Graph Files
```
backend/app/graph/
├── graph.py     # full graph definition
├── state.py     # MeetMindState TypedDict
└── router.py    # supervisor_router + confirmation_router
```

---

## SECTION 7 — FINAL FROZEN RAG DESIGN

### Chunking Strategy: Speaker-Aware
- Chunk = one speaker's continuous dialogue block
- Size: 200-300 tokens, overlap: 50 tokens
- Speaker label preserved at top of every chunk
- Format: `[SpeakerName - HH:MM]: dialogue text`

### Metadata Per Chunk
```python
{
    "meeting_id": "uuid",
    "user_id": "uuid",
    "speaker_name": "str",
    "speaker_role": "str",
    "timestamp": "HH:MM",
    "chunk_index": int,
    "meeting_date": "YYYY-MM-DD",
    "meeting_title": "str",
    "chunk_type": "dialogue|decision|task_mention",
    "involves_user": bool
}
```

### Pinecone Namespace
- One namespace per meeting: `meeting_{meeting_id}`
- Q&A Agent queries only the relevant meeting namespace
- Zero cross-meeting contamination by design

### Hybrid Search
- **Semantic:** Pinecone similarity_search, top 10
- **BM25:** rank-bm25 on transcript_chunks in PostgreSQL, top 10
- **Merge:** deduplicate by chunk_index, 15-20 combined chunks
- **Rerank:** BAAI/bge-reranker-v2-m3 (local CrossEncoder), returns top 5

### RAG Files
```
backend/app/rag/
├── chunker.py    # speaker-aware chunking
├── embedder.py   # gemini-embedding-001
├── retriever.py  # hybrid search: semantic + BM25
└── reranker.py   # bge-reranker-v2-m3
```

---

## SECTION 8 — FINAL FROZEN DATABASE SCHEMA (8 TABLES)

### users
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| name | VARCHAR(255) | NOT NULL |
| email | VARCHAR(255) | UNIQUE, NOT NULL |
| created_at | TIMESTAMP | DEFAULT now() |

### meetings
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| user_id | UUID FK → users | |
| title | VARCHAR(500) | extracted by Ingestion Agent |
| organization | VARCHAR(255) | from form |
| meeting_date | DATE | from form |
| meeting_time | VARCHAR(10) | from form |
| raw_transcript | TEXT | full original transcript |
| input_format | VARCHAR(10) | pdf/txt/text |
| pinecone_namespace | VARCHAR(255) | meeting_{meeting_id} |
| created_at | TIMESTAMP | DEFAULT now() |

### meeting_participants
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| meeting_id | UUID FK → meetings | |
| name | VARCHAR(255) | |
| role | VARCHAR(255) | |
| is_current_user | BOOLEAN | DEFAULT false |

### tasks
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| meeting_id | UUID FK → meetings | |
| user_id | UUID FK → users | |
| title | VARCHAR(500) | NOT NULL |
| description | TEXT | AI-generated |
| priority | VARCHAR(10) | high/medium/low |
| deadline | DATE | nullable |
| status | VARCHAR(10) | pending/complete |
| alert_sent | BOOLEAN | DEFAULT false |
| created_at | TIMESTAMP | DEFAULT now() |

### highlights
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| meeting_id | UUID FK → meetings | |
| user_id | UUID FK → users | |
| content | TEXT | NOT NULL |
| created_at | TIMESTAMP | DEFAULT now() |

### chat_messages
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| meeting_id | UUID FK → meetings | |
| user_id | UUID FK → users | |
| role | VARCHAR(10) | user/assistant |
| content | TEXT | NOT NULL |
| created_at | TIMESTAMP | DEFAULT now() |

### transcript_chunks
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| meeting_id | UUID FK → meetings | |
| chunk_index | INTEGER | NOT NULL |
| speaker_name | VARCHAR(255) | |
| speaker_role | VARCHAR(255) | |
| content | TEXT | raw chunk text |
| timestamp | VARCHAR(20) | from transcript |
| chunk_type | VARCHAR(20) | dialogue/decision/task_mention |
| involves_user | BOOLEAN | DEFAULT false |
| pinecone_vector_id | VARCHAR(255) | matching vector ID in Pinecone |

### Relationships
```
users
  └── meetings (one → many)
        ├── meeting_participants (one → many)
        ├── tasks (one → many)
        ├── highlights (one → many)
        ├── chat_messages (one → many)
        └── transcript_chunks (one → many)
tasks → users (task belongs to user)
highlights → users
chat_messages → users
```

---

## SECTION 9 — FINAL FROZEN API DESIGN (21 ENDPOINTS)

### Base URL
```
Backend: https://meetmind-api.onrender.com
Prefix: /api/v1
```

### All Endpoints

| # | Method | Endpoint | Purpose |
|---|--------|----------|---------|
| 1 | POST | /api/v1/users/register | Register user |
| 2 | GET | /api/v1/users/{user_id} | Get user profile |
| 3 | PUT | /api/v1/users/{user_id} | Update user |
| 4 | POST | /api/v1/meetings/ | Create meeting + trigger pipeline |
| 5 | GET | /api/v1/meetings/{user_id} | All meetings for user |
| 6 | GET | /api/v1/meetings/{meeting_id}/detail | Single meeting detail |
| 7 | DELETE | /api/v1/meetings/{meeting_id} | Delete meeting |
| 8 | GET | /api/v1/tasks/{user_id} | All tasks across meetings |
| 9 | GET | /api/v1/tasks/{user_id}/meeting/{meeting_id} | Tasks for one meeting |
| 10 | PUT | /api/v1/tasks/{task_id}/status | Toggle task status |
| 11 | GET | /api/v1/tasks/{user_id}/filter | Filter tasks by priority + date |
| 12 | POST | /api/v1/chat/{meeting_id}/message | Send Q&A message |
| 13 | GET | /api/v1/chat/{meeting_id}/history | Get chat history |
| 14 | DELETE | /api/v1/chat/{meeting_id}/history | Clear chat history |
| 15 | POST | /api/v1/extraction/{meeting_id}/run | Run extraction pipeline |
| 16 | GET | /api/v1/extraction/{meeting_id}/preview | Preview extracted tasks |
| 17 | POST | /api/v1/extraction/{meeting_id}/confirm | Confirm + save tasks |
| 18 | GET | /api/v1/highlights/{user_id}/meeting/{meeting_id} | Meeting highlights |
| 19 | GET | /api/v1/highlights/{user_id} | All highlights |
| 20 | POST | /api/v1/notifications/trigger | Manual notification trigger |
| 21 | GET | /api/v1/notifications/{user_id}/pending | Pending deadline alerts |

### Router Files
```
backend/app/api/
├── router.py         # aggregates all routers
├── users.py
├── meetings.py
├── tasks.py
├── chat.py
├── extraction.py
├── highlights.py
└── notifications.py
```

### Service Files
```
backend/app/services/
├── user_service.py
├── meeting_service.py
├── task_service.py
├── chat_service.py
├── extraction_service.py
├── highlight_service.py
└── notification_service.py
```

---

## SECTION 10 — FINAL FROZEN FRONTEND STRUCTURE

### Pages (3 total)

**PAGE 1 — Landing Page**
- Hero section: tagline + CTA button to Workspace
- Feature highlights: 3 key features of MeetMind
- Footer: GitHub, LinkedIn, Email links (on every page)

**PAGE 2 — Workspace**
Two views inside Workspace:

*Dashboard View:*
- All tasks across all meetings (unified view)
- Filter: priority (high/medium/low) + deadline date + status
- Sort: deadline + priority (default)
- Toggle: complete/incomplete per task

*Meetings View:*
- List of all meetings submitted by user
- "New Meeting" button → opens form (modal or separate page)
- New Meeting Form fields:
  - Meeting date + time
  - Organization name
  - Your name
  - Your role
  - Transcript input (3 options in same UI component: paste text / upload PDF / upload TXT)
- Click any meeting → opens that meeting's page with:
  - Task list for that meeting (with highlights section)
  - Chat interface (setup flow runs once, Q&A chat ongoing)

**PAGE 3 — Documentation Page**
- What is MeetMind (plain English)
- Agent roster table (all 7 agents)
- Model assignments table
- RAG pipeline explanation
- Workflow diagram (Mermaid rendered)
- Tech stack table
- Capabilities list

### Design
- Color: light background, blue + dark blue hue
- Animations: hover effects, text floating on hover, transition effects, entrance animations
- No custom cursor (risk during hackathon)
- No screenshots anywhere — live demo handles proof

### Frontend Files
```
frontend/
├── app.py
├── pages/
│   ├── landing.py
│   ├── workspace.py
│   └── documentation.py
├── components/
│   ├── task_card.py
│   ├── meeting_card.py
│   ├── chat_bubble.py
│   ├── new_meeting_form.py
│   ├── task_filter.py
│   └── highlight_card.py
├── services/
│   └── api_client.py
├── utils/
│   └── session_state.py
└── assets/
    └── styles.css
```

---

## SECTION 11 — FINAL FROZEN EMAIL + SCHEDULER

**Email Service:** Resend
**Sender:** onboarding@resend.dev
**SDK:** resend Python package
**Trigger:** APScheduler AsyncIOScheduler inside FastAPI lifespan
**Schedule:** Daily at 08:00 AM (configurable via NOTIFICATION_HOUR + NOTIFICATION_MINUTE env vars)
**Email content:** AI-composed (not template) — task title, deadline, AI description, 2-3 transcript lines from RAG

```python
# APScheduler setup inside FastAPI lifespan
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()
scheduler.add_job(notification_agent.run, trigger="cron", hour=8, minute=0)

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    yield
    scheduler.shutdown()
```

---

## SECTION 12 — FINAL FROZEN FOLDER STRUCTURE

```
meetmind-ai/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── supervisor.py
│   │   │   ├── ingestion.py
│   │   │   ├── identity.py
│   │   │   ├── extraction.py
│   │   │   ├── confirmation.py
│   │   │   ├── qa.py
│   │   │   └── notification.py
│   │   ├── tools/
│   │   │   ├── __init__.py
│   │   │   ├── parse_pdf_tool.py
│   │   │   ├── parse_txt_tool.py
│   │   │   ├── extract_metadata_tool.py
│   │   │   ├── store_transcript_tool.py
│   │   │   ├── embed_and_store_tool.py
│   │   │   ├── search_participant_tool.py
│   │   │   ├── extract_user_mentions_tool.py
│   │   │   ├── confirm_identity_tool.py
│   │   │   ├── extract_tasks_tool.py
│   │   │   ├── generate_task_description_tool.py
│   │   │   ├── assign_priority_tool.py
│   │   │   ├── extract_highlights_tool.py
│   │   │   ├── present_tasks_tool.py
│   │   │   ├── save_confirmed_tasks_tool.py
│   │   │   ├── save_confirmed_highlights_tool.py
│   │   │   ├── hybrid_search_tool.py
│   │   │   ├── rerank_tool.py
│   │   │   ├── generate_answer_tool.py
│   │   │   ├── check_deadline_tool.py
│   │   │   ├── retrieve_task_context_tool.py
│   │   │   ├── compose_email_tool.py
│   │   │   ├── send_email_tool.py
│   │   │   └── mark_alert_sent_tool.py
│   │   ├── graph/
│   │   │   ├── __init__.py
│   │   │   ├── graph.py
│   │   │   ├── state.py
│   │   │   └── router.py
│   │   ├── rag/
│   │   │   ├── __init__.py
│   │   │   ├── chunker.py
│   │   │   ├── embedder.py
│   │   │   ├── retriever.py
│   │   │   └── reranker.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── router.py
│   │   │   ├── users.py
│   │   │   ├── meetings.py
│   │   │   ├── tasks.py
│   │   │   ├── chat.py
│   │   │   ├── extraction.py
│   │   │   ├── highlights.py
│   │   │   └── notifications.py
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── session.py
│   │   │   └── models/
│   │   │       ├── __init__.py
│   │   │       ├── user.py
│   │   │       ├── meeting.py
│   │   │       ├── meeting_participant.py
│   │   │       ├── task.py
│   │   │       ├── highlight.py
│   │   │       ├── chat_message.py
│   │   │       └── transcript_chunk.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── user_service.py
│   │   │   ├── meeting_service.py
│   │   │   ├── task_service.py
│   │   │   ├── chat_service.py
│   │   │   ├── extraction_service.py
│   │   │   ├── highlight_service.py
│   │   │   └── notification_service.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── meeting.py
│   │   │   ├── task.py
│   │   │   ├── chat.py
│   │   │   ├── extraction.py
│   │   │   ├── highlight.py
│   │   │   └── notification.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── settings.py
│   │   │   ├── config.py
│   │   │   └── constants.py
│   │   └── main.py
│   ├── alembic/
│   │   ├── versions/
│   │   └── env.py
│   ├── alembic.ini
│   ├── .env
│   ├── .env.example
│   └── requirements.txt
├── frontend/
│   ├── app.py
│   ├── pages/
│   │   ├── landing.py
│   │   ├── workspace.py
│   │   └── documentation.py
│   ├── components/
│   │   ├── __init__.py
│   │   ├── task_card.py
│   │   ├── meeting_card.py
│   │   ├── chat_bubble.py
│   │   ├── new_meeting_form.py
│   │   ├── task_filter.py
│   │   └── highlight_card.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── api_client.py
│   ├── utils/
│   │   ├── __init__.py
│   │   └── session_state.py
│   ├── assets/
│   │   └── styles.css
│   ├── .env
│   ├── .env.example
│   └── requirements.txt
├── docs/
│   ├── ARCHITECTURE.md
│   ├── FEATURES.md
│   └── AGENT_FLOW.md
├── data/
│   └── sample_transcripts/
│       ├── transcript_kickoff.txt
│       ├── transcript_sprint_review.txt
│       └── transcript_emergency_bug.txt
├── .env.common
├── .env.common.example
├── requirements.common.txt
├── .gitignore
└── README.md
```

---

## SECTION 13 — FINAL FROZEN CODING STRATEGY (10 RULES)

**RULE 1 — File & Responsibility:** One file = one responsibility. One function = one job. No business logic in route files. No cross-concern imports at same level.

**RULE 2 — Project Structure:** Exact folder structure as above. No deviation.

**RULE 3 — Environment Variables:** Three env files: backend/.env, frontend/.env, .env.common. All backend vars loaded exclusively through backend/app/core/settings.py using Pydantic BaseSettings. No os.environ calls anywhere else.

**RULE 4 — Settings & Config:**
- settings.py → Pydantic BaseSettings, all env vars, singleton instance
- config.py → static config, model names, retry counts, chunk sizes
- constants.py → Python Enums, string constants, agent names, state keys

**RULE 5 — Database Layer:** SQLAlchemy models in db/models/, one file per table. All changes via Alembic migrations. No Base.metadata.create_all() in production. Session via FastAPI dependency injection.

**RULE 6 — Agent & Orchestration Rules:** One agent per file. One tool per file. LangGraph graph entirely in graph/graph.py. Agents never call each other directly. Every agent has explicit Pydantic input + output schema. No untyped dicts between agents.

**RULE 7 — RAG Layer:** Separate files for chunker, embedder, retriever, reranker. Reranker always runs after retrieval. Every chunk stored with full metadata.

**RULE 8 — API Layer:** One router file per domain. All routers registered in api/router.py. Routes: validate → call service → return response. All bodies are Pydantic schemas.

**RULE 9 — GitHub Branch Strategy:** main always stable. Branch per gate: gate/db-architecture, gate/ai-agents, gate/rag-pipeline, gate/backend, gate/frontend, gate/integration. On gate closure: commit → push → PR → merge → delete → checkout main → pull → new branch.

**RULE 10 — Code Quality:** Docstrings on every function. Type hints on every signature. No unused imports. No commented-out code. Error handling on every external call. No bare except. logging module over print statements.

---

## SECTION 14 — FINAL FROZEN GATE PLAN

| Gate | Branch | Covers | Est. Time |
|------|--------|--------|-----------|
| 1 | gate/db-architecture | SQLAlchemy models (all 8 tables), Alembic setup, DB session, base | 25 min |
| 2 | gate/ai-agents | LangGraph state + graph + router, all 7 agents, all 25 tools | 60 min |
| 3 | gate/rag-pipeline | chunker, embedder, retriever (hybrid), reranker, Pinecone integration | 40 min |
| 4 | gate/backend | FastAPI routes (21 endpoints), services, schemas, main.py, APScheduler | 45 min |
| 5 | gate/frontend | Streamlit: landing, workspace, documentation, components, api_client | 30 min |
| 6 | gate/integration | End-to-end wiring, env vars, error handling, .env files, final testing | 30 min |

**Total estimated: ~3h 50min leaving ~2h for PPT + buffer**

**Gate execution per gate:**
1. Analysis Prompt → paste into Antigravity → Antigravity analyzes codebase
2. Implementation Prompt → paste into Antigravity → Antigravity implements
3. Gate Verdict → review output → commit → push → PR → merge → next gate

---

## SECTION 15 — ALL API KEYS REQUIRED

| Key | Env Variable | Source |
|-----|-------------|--------|
| Google Gemini | GOOGLE_API_KEY | aistudio.google.com (20 keys available) |
| OpenRouter | OPENROUTER_API_KEY | openrouter.ai (13 keys available) |
| Pinecone | PINECONE_API_KEY | pinecone.io — "Agentic" key created |
| Resend | RESEND_API_KEY | resend.com — needs account creation |
| Tavily (if web search needed) | TAVILY_API_KEY | tavily.com (5 keys available) |
| PostgreSQL | DATABASE_URL | Render Managed PostgreSQL |

**Pinecone index already created:**
- Index name: hackathon-index
- Dimensions: 3072
- Metric: cosine
- Cloud: AWS us-east-1
- Namespace strategy: meeting_{meeting_id}

---

## SECTION 16 — DEMO DATA (3 SAMPLE TRANSCRIPTS)

Three realistic meeting transcripts are stored in data/sample_transcripts/. Each has 5 team members with distinct roles:
- Aryan (Project Manager)
- Sneha (Frontend Developer)
- Rahul (Database Designer)
- Priya (Schema Architect)
- Dev (Documentation Lead)

**Transcript 1:** transcript_kickoff.txt — Project Kickoff Meeting (Sep 25, 2026) — tasks assigned, deadlines set, tech decisions made

**Transcript 2:** transcript_sprint_review.txt — Sprint 1 Review (Oct 5, 2026) — progress updates, blockers, Sprint 2 goals assigned

**Transcript 3:** transcript_emergency_bug.txt — Emergency Bug Review (Oct 13, 2026) — production issue, immediate fixes, incident report assignments

Each transcript is 100+ lines. Used for testing ingestion, identity detection, extraction, Q&A, and notification features during development and demo.

---

## SECTION 17 — WHAT MAKES MEETMIND UNIQUE (JUDGE TALKING POINTS)

**One-liner:** "MeetMind doesn't just read your meetings — it knows who you are in them."

**For technical judges:**
- 7 specialized agents, each with single responsibility, coordinated by LangGraph supervisor
- Plan-and-Execute at supervisor level, ReAct at sub-agent level — both patterns visible
- Form-first design: agents read from PostgreSQL, not from conversational prompts — production-grade
- Human-in-the-loop at Confirmation Agent only — deliberate, controlled, principled design
- 3-stage RAG: hybrid search (semantic + BM25) → cross-encoder reranking → grounded generation
- Speaker-aware chunking preserves identity context in every vector
- AI-composed (not templated) email alerts using RAG-retrieved context per task
- APScheduler inside FastAPI lifespan — no separate worker process needed

**For non-technical judges:**
- "You upload your meeting, tell it your name, and it finds everything you need to do"
- "It emails you before your deadlines with everything you need to know"
- "You can ask it anything about your meeting and it only answers from that meeting"
- Clean dashboard, clear task list, simple toggle

---

## SECTION 18 — INSTRUCTIONS FOR AI SYSTEM RECEIVING THIS DOCUMENT

You are the AI co-pilot continuing the MeetMind project implementation. Everything in this document is final and frozen. Do not suggest changes to the architecture, features, agents, or tech stack unless Ankush explicitly raises a new requirement.

**Your role from this point:**
- Open gates one by one in order: DB → AI Agents → RAG → Backend → Frontend → Integration
- For each gate: generate Analysis Prompt → wait for Antigravity output → generate Implementation Prompt → wait for completion → generate Gate Closure summary
- Generate all Antigravity prompts in the exact format specified in the system prompt (bordered with ═══ separators)
- Follow all 10 coding rules in every prompt you generate
- Every decision communicated to Ankush. Nothing skipped silently.
- If any ambiguity arises mid-gate, ask Ankush — never invent missing context
- README generated after all 6 gates close, before deployment

**Current status:** All pre-implementation discussion complete. 3 docs generated (ARCHITECTURE.md, FEATURES.md, AGENT_FLOW.md). Ready to open Gate 1: gate/db-architecture.

**First action:** Ask Ankush to confirm he is ready to open Gate 1, then generate the Gate 1 Analysis Prompt for Antigravity.
