<div align="center">

<!-- Hero Banner -->
<img src="docs/assets/hero_banner.jpg" alt="MeetMind AI — Agentic AI Meeting Intelligence" width="100%"/>

<br/><br/>

# 🧠 MeetMind AI

### *MeetMind doesn't just read your meetings — it knows who you are in them.*

**An agentic AI meeting assistant that transforms raw transcripts into personalized, structured, and actionable intelligence — powered by a 7-agent LangGraph pipeline with hybrid RAG, human-in-the-loop confirmation, and proactive email deadline alerts.**

<br/>

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.x-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Primary_DB-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![Pinecone](https://img.shields.io/badge/Pinecone-Vector_DB-00B3A4?style=for-the-badge&logo=pinecone&logoColor=white)
![Google Gemini](https://img.shields.io/badge/Gemini-AI_Models-4285F4?style=for-the-badge&logo=google&logoColor=white)
![Resend](https://img.shields.io/badge/Resend-Email_Alerts-000000?style=for-the-badge)

<br/>

**[Overview](#-project-overview) • [Features](#-key-features) • [Architecture](#-system-architecture) • [Agents](#-agent-architecture) • [RAG Pipeline](#-rag-pipeline) • [API](#-api-overview) • [Installation](#-local-installation--execution) • [Contact](#-contact)**

</div>

---

## 📋 Table of Contents

<details>
<summary>Expand full table of contents</summary>

1. [Project Overview](#-project-overview)
2. [The Problem & Solution](#-the-problem--solution)
3. [Key Features](#-key-features)
4. [Languages & Technology Stack](#-languages--technology-stack)
5. [System Architecture](#-system-architecture)
6. [Agent Architecture](#-agent-architecture)
7. [End-to-End Workflow](#-end-to-end-workflow)
8. [RAG Pipeline](#-rag-pipeline)
9. [Database Architecture](#-database-architecture)
10. [Application Flow](#-application-flow)
11. [API Overview](#-api-overview)
12. [Project Folder Structure](#-project-folder-structure)
13. [Security & Data Isolation](#-security--data-isolation)
14. [Testing & Validation](#-testing--validation)
15. [Limitations & Scope](#-limitations--scope)
16. [Roadmap](#-roadmap)
17. [Contribution Guidelines](#-contribution-guidelines)
18. [License](#-license)
19. [Local Installation & Execution](#-local-installation--execution)
20. [Contact](#-contact)

</details>

---

## 🔍 Project Overview

**MeetMind AI** is a multi-agent AI system that takes a raw meeting transcript and a user's name + role, and produces structured, personalized output: tasks assigned to that user, key meeting highlights, a natural-language Q&A interface scoped to that meeting, and automated email deadline alerts — all without requiring the user to ask conversational prompts.

| Attribute | Details |
|-----------|---------|
| **Domain** | Agentic AI / AI Meeting Assistant |
| **Architecture** | 7-agent LangGraph pipeline (Plan-and-Execute + ReAct) |
| **Backend** | FastAPI + SQLAlchemy + PostgreSQL |
| **Frontend** | Streamlit (3-page application) |
| **Vector DB** | Pinecone (per-meeting namespaced) |
| **AI Models** | Google Gemini (gemini-3.6-flash, gemini-3.5-flash-lite, gemini-embedding-001) |
| **Retrieval** | Hybrid RAG: Semantic (Pinecone) + BM25 (PostgreSQL) + BGE cross-encoder reranking |
| **Email** | Resend API with AI-composed bodies |
| **Scheduler** | APScheduler (AsyncIOScheduler, daily 08:00 AM) |

### Who is it for?

- Students and project teams conducting meetings with long transcripts
- Individual contributors who need to know *their* tasks without reading everything
- Anyone whose meeting notes contain buried action items, deadlines, and decisions

### What makes MeetMind distinct?

Unlike generic AI summarizers, MeetMind:

1. **Identifies you specifically** inside the transcript using form-submitted identity — not conversational guessing
2. **Reads from the database** — every agent operates on PostgreSQL data, not chat prompts
3. **Confirms before saving** — the Confirmation Agent is the only human-facing step; nothing enters the dashboard without explicit approval
4. **Scopes retrieval to one meeting** — the Q&A Agent queries only the relevant Pinecone namespace; answers never contaminate across meetings
5. **Composes emails with RAG** — deadline alerts include actual transcript context retrieved per task, not generic templates

---

## ⚡ The Problem & Solution

Students and project teams conduct meetings but lose track of decisions, assigned tasks, and deadlines buried inside long transcripts. Manually reviewing transcripts wastes time and critical action items get missed.

| Traditional Meeting Workflow | MeetMind AI Workflow |
|-----------------------------|----------------------|
| Manually scan 100-line transcript for your name | AI identifies you using your form-submitted name |
| Copy-paste tasks by hand into a to-do list | Extraction Agent generates tasks with title, description, and priority |
| No verification — AI decides what your tasks are | Confirmation Agent presents tasks; you approve, reject, or select |
| Check your calendar for deadlines | Email alert at 08:00 AM with context from the original discussion |
| Ask a colleague what was said about a topic | Ask the Q&A chat, get a source-attributed answer scoped to that meeting |
| PDF or TXT or pasted text handled differently | One form handles paste, PDF upload, and TXT upload uniformly |
| No awareness of who said what | Speaker-aware chunking preserves speaker identity in every retrieved chunk |
| Single model doing everything | 7 specialized agents, each with one job, coordinated by a supervisor |

---

## ✨ Key Features

### Feature 1 — Multi-Format Transcript Ingestion

> **Submit transcripts as pasted text, PDF upload, or TXT file upload — all handled by the same form component.**

The Ingestion Agent reads the raw transcript from PostgreSQL after form submission, parses PDF or TXT formats using pypdf, applies speaker-aware chunking (200–300 tokens, 50-token overlap, speaker label preserved), embeds chunks with `gemini-embedding-001` (3072 dimensions), stores vectors to Pinecone under a per-meeting namespace, and saves raw chunks to the `transcript_chunks` table.

**Benefit:** Removes input friction — works with any meeting tool that can export a file or allow copy-paste.

---

### Feature 2 — Form-First Identity Detection

> **User provides their name, role, and organization in the New Meeting form. No conversational prompting needed.**

Identity data is saved to PostgreSQL at form submission time. The Identity Agent reads directly from `meeting_participants`, searches transcript chunks for all lines mentioning the user, extracts mention context, and stores results back to the database.

**Benefit:** Makes the pipeline deterministic and production-grade — agents read from structured storage, not unstructured chat.

---

### Feature 3 — AI Task Extraction

> **The Extraction Agent analyzes the full transcript and user mentions to find every task assigned to or relevant to the identified user.**

For each extracted task: generates a short title, writes an AI description, assigns priority (high / medium / low) based on urgency language, and extracts deadline if mentioned.

**Benefit:** Replaces manual transcript scanning — surfaces tasks in seconds with typed, structured output.

---

### Feature 4 — Human-in-the-Loop Task Confirmation

> **The Confirmation Agent is the ONLY point where the user interacts with the agent pipeline.**

Presents extracted tasks showing title and description only. The user responds with **Yes** (save all), **No** (discard all), or **Partial** (select specific tasks). Only confirmed tasks are permanently written to the `tasks` table.

**Benefit:** AI proposes, human approves, system executes. Prevents noise from incorrect extractions and builds trust.

---

### Feature 5 — Per-Meeting Task Dashboard

> **Every meeting has its own task view with color-coded priority, deadline, status toggle, and highlights section.**

Tasks display: title, AI-generated description, priority (🔴 high / 🟡 medium / 🟢 low), deadline, and status toggle. Key highlights appear below the task list.

**Benefit:** Meeting-contextual task management — users see which discussion each task came from.

---

### Feature 6 — Unified Task Dashboard

> **All tasks across all meetings in one filterable, sortable view.**

Filter by: priority, deadline date, status. Default sort: deadline + priority. Status toggle available from this view.

**Benefit:** A single place to manage the full workload across multiple meetings.

---

### Feature 7 — Meeting-Scoped Q&A Chat

> **Ask any natural language question about a specific meeting and receive a grounded, source-attributed answer.**

The Q&A Agent runs hybrid retrieval (Pinecone semantic + BM25 keyword), reranks results with `BAAI/bge-reranker-v2-m3` locally, and generates a grounded answer using the top 5 chunks plus user identity context. Chat history is stored in PostgreSQL. Answers are scoped strictly to that meeting's namespace.

**Benefit:** Unlocks the full information in every meeting beyond just the task list.

---

### Feature 8 — Context-Rich Email Deadline Alerts

> **Daily at 08:00 AM, the Notification Agent emails users about tasks due within 24 hours.**

For each qualifying task (pending, deadline ≤ tomorrow, `alert_sent = false`): the agent retrieves relevant transcript context from Pinecone via RAG, AI-composes an email with task title, deadline, description, and 2–3 lines of transcript context, and sends it via Resend.

**Benefit:** Proactive alerts with full context — everything needed to act, delivered to the inbox.

---

### Feature 9 — Important Meeting Highlights

> **Beyond personal tasks, the Extraction Agent identifies team-wide decisions, announcements, and important context relevant to the user.**

Shown in a dedicated "Key Highlights" section on the per-meeting dashboard.

**Benefit:** Captures the full intelligence of a meeting, not just personal action items.

---

## 💻 Languages & Technology Stack

### Programming Languages

| Language | Role |
|----------|------|
| **Python 3.11+** | Entire backend (FastAPI, LangGraph agents, RAG pipeline, services, tools) and entire frontend (Streamlit) |

> Python is the sole programming language used across both the backend and frontend.

---

### Backend Technologies

| Category | Technology | Purpose |
|----------|------------|---------|
| Web Framework | FastAPI | REST API, pipeline trigger, CORS, global error handling |
| ASGI Server | Uvicorn | Production ASGI server |
| ORM | SQLAlchemy ≥ 2.0 | Database models and query interface |
| Migrations | Alembic | Schema version control |
| DB Driver | psycopg2-binary | PostgreSQL adapter |
| Validation | Pydantic + pydantic-settings | Request/response schemas and settings |
| Multipart | python-multipart | File upload support |
| HTTP Client | httpx | Async HTTP requests |
| Async Files | aiofiles | Async file I/O |
| Logging | loguru | Structured application logging |

---

### Frontend Technologies

| Category | Technology | Purpose |
|----------|------------|---------|
| UI Framework | Streamlit | 3-page web application |
| HTTP Client | httpx, requests | API calls to FastAPI backend |
| PDF Preview | pypdf | Client-side PDF reading before upload |
| Data Display | pandas | Tabular data rendering |
| Date Handling | python-dateutil | Date parsing and formatting |

---

### AI & Agentic Frameworks

| Category | Technology | Purpose |
|----------|------------|---------|
| Agent Construction | LangChain | Tool binding, prompt templates, agent loops |
| Multi-Agent Orchestration | LangGraph | Agent graph, state management, conditional routing |
| LLM — Supervisor + Q&A | `gemini-3.6-flash` | Plan-and-Execute supervisor; Q&A answer generation |
| LLM — Sub-agents | `gemini-3.5-flash-lite` | Ingestion, Identity, Extraction, Confirmation, Notification |
| LLM Integration | langchain-google-genai | LangChain ↔ Gemini bridge |
| Fallback LLM | `thinkingmachines/inkling:free` via OpenRouter | Fallback if Gemini quota exhausted |
| Backup Orchestrator | `openai/gpt-oss-120b` via OpenRouter | Backup for supervisor-level reasoning |
| OpenAI Client | openai | OpenRouter API access (OpenAI-compatible) |

---

### Database & Retrieval

| Category | Technology | Purpose |
|----------|------------|---------|
| Primary DB | PostgreSQL | Users, meetings, tasks, highlights, chat, transcript chunks |
| Vector DB | Pinecone (AWS us-east-1) | Dense vector store, one namespace per meeting |
| Embedding Model | `gemini-embedding-001` | 3072-dim dense vectors |
| Semantic Search | Pinecone similarity search | Top-10 semantically relevant chunks per query |
| Keyword Search | rank-bm25 (BM25) | Top-10 keyword-matched chunks from PostgreSQL |
| Reranker | `BAAI/bge-reranker-v2-m3` | Local cross-encoder via sentence-transformers |
| PDF Parsing | pypdf | Extract text from uploaded PDF transcripts |
| DOCX Support | python-docx | Additional document format support |

---

### Infrastructure & Integrations

| Category | Technology | Purpose |
|----------|------------|---------|
| Scheduler | APScheduler (AsyncIOScheduler) | Daily 08:00 AM notification job inside FastAPI lifespan |
| Email | Resend API + `resend` Python SDK | AI-composed deadline alert emails |
| Email Sender | `onboarding@resend.dev` | No domain verification required |
| Backend Hosting | Render (Web Service) | uvicorn, auto-deploy from `main` |
| DB Hosting | Render Managed PostgreSQL | Free tier, 1 GB storage |
| Frontend Hosting | Vercel | Streamlit deployment |
| Environment Config | python-dotenv | Three `.env` files |

---

## 🏗 System Architecture

MeetMind AI is a three-layer system: a Streamlit frontend communicates with a FastAPI backend, which orchestrates a multi-agent LangGraph pipeline backed by PostgreSQL (primary) and Pinecone (vectors).

```mermaid
flowchart TD
    A["User - Streamlit Frontend"] -->|Fill New Meeting Form| B["FastAPI Backend"]
    B -->|Save user, meeting, identity| C[("PostgreSQL")]
    B -->|Trigger pipeline| D["LangGraph Supervisor"]

    D -->|Read transcript from DB| E["Ingestion Agent"]
    E -->|Chunk + Embed gemini-embedding-001| F[("Pinecone - meeting namespace")]
    E -->|Store chunks| C

    D -->|Read name + role from DB| G["Identity Agent"]
    G -->|Search transcript chunks| G
    G -->|Store mentions| C

    D -->|Read mentions + transcript from DB| H["Extraction Agent"]
    H -->|Extract tasks + highlights| H
    H -->|Temp store extracted data| C

    D -->|Present tasks to user| I["Confirmation Agent"]
    I -->|User yes/no/partial via chat| A
    I -->|Save confirmed tasks + highlights| C

    A -->|Ask question about meeting| J["Q&A Agent"]
    J -->|Semantic search - top 10| F
    J -->|BM25 keyword search - top 10| C
    J -->|Rerank locally| K["BGE Reranker - BAAI/bge-reranker-v2-m3"]
    K -->|Top 5 chunks| J
    J -->|Grounded answer + sources| A

    L["APScheduler - 8AM daily"] -->|Trigger| M["Notification Agent"]
    M -->|Query pending tasks| C
    M -->|RAG context retrieval - top 3| F
    M -->|Compose + Send email| N["Resend API"]
    N -->|Email alert| O["User Email Inbox"]

    A -->|View tasks + toggle status| B
    B -->|Read/Update tasks| C
```

### Deployment Architecture

```
┌─────────────────┐         ┌──────────────────────────────────────┐
│   Vercel        │  HTTPS  │   Render                             │
│   Streamlit UI  │────────►│   FastAPI + LangGraph                │
│   (Frontend)    │◄────────│   APScheduler (Notification)         │
└─────────────────┘         │   BGE Reranker (local, no ext. API)  │
                            └────────────┬─────────────────────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    │                    │                     │
                    ▼                    ▼                     ▼
             ┌──────────┐       ┌──────────────┐     ┌──────────────┐
             │PostgreSQL│       │   Pinecone   │     │  Resend API  │
             │ (Render) │       │  (AWS Cloud) │     │   (Email)    │
             └──────────┘       └──────────────┘     └──────────────┘
                                         │
                                         ▼
                                 ┌──────────────────┐
                                 │  Google Gemini   │
                                 │  OpenRouter      │
                                 │  (Fallback LLM)  │
                                 └──────────────────┘
```

---

## 🤖 Agent Architecture

MeetMind uses a **Plan-and-Execute** supervisor pattern with **ReAct** sub-agents.

### Agent Roster

| Agent | Pattern | Model | Responsibility | Position |
|-------|---------|-------|----------------|----------|
| **Supervisor Agent** | Plan-and-Execute | `gemini-3.6-flash` | Reads meeting from DB, generates execution plan, routes to sub-agents via `session_action`, aggregates results | Orchestrates all others |
| **Ingestion Agent** | ReAct | `gemini-3.5-flash-lite` | Parses transcript, speaker-aware chunking, embeds with `gemini-embedding-001`, stores to Pinecone + PostgreSQL | 2nd in pipeline |
| **Identity Agent** | ReAct | `gemini-3.5-flash-lite` | Reads user name/role from DB, searches transcript for user mentions, stores mention context | 3rd in pipeline |
| **Extraction Agent** | ReAct | `gemini-3.5-flash-lite` | Extracts tasks with title/description/priority/deadline, extracts highlights, stores as unconfirmed | 4th in pipeline |
| **Confirmation Agent** | ReAct | `gemini-3.5-flash-lite` | **Only human-facing agent.** Presents tasks in chat, waits for yes/no/partial, saves confirmed data | 5th in pipeline |
| **Q&A Agent** | ReAct | `gemini-3.6-flash` | Independent hybrid RAG Q&A scoped to meeting namespace, BGE reranking, source attribution | Independent |
| **Notification Agent** | ReAct | `gemini-3.5-flash-lite` | Daily deadline check, RAG context retrieval per task, AI email composition, Resend delivery | Daily 08:00 AM |

### Agent Tools (24 total)

| Agent | Tools |
|-------|-------|
| Supervisor | `route_to_agent_tool`, `aggregate_response_tool` |
| Ingestion | `parse_pdf_tool`, `parse_txt_tool`, `extract_metadata_tool`, `store_transcript_tool`, `embed_and_store_tool` |
| Identity | `search_participant_tool`, `extract_user_mentions_tool`, `confirm_identity_tool` |
| Extraction | `extract_tasks_tool`, `generate_task_description_tool`, `assign_priority_tool`, `extract_highlights_tool` |
| Confirmation | `present_tasks_tool`, `save_confirmed_tasks_tool`, `save_confirmed_highlights_tool` |
| Q&A | `hybrid_search_tool`, `rerank_tool`, `generate_answer_tool` |
| Notification | `check_deadline_tool`, `retrieve_task_context_tool`, `compose_email_tool`, `send_email_tool`, `mark_alert_sent_tool` |

### Agent Orchestration Diagram

```mermaid
flowchart TD
    START(["Form Submitted"]) --> SUP

    SUP{"Supervisor Agent\nReads session_action\nRoutes to sub-agent"}

    SUP -->|"session_action = ingest"| ING["Ingestion Agent\nParse - Chunk - Embed\nPinecone + PostgreSQL"]
    ING -->|"ingestion_complete = true"| SUP

    SUP -->|"session_action = identify"| IDENT["Identity Agent\nSearch transcript for user\nStore mentions to DB"]
    IDENT -->|"identity_confirmed = true"| SUP
    IDENT -->|"user not found"| ERR(["Error State - User notified"])

    SUP -->|"session_action = extract"| EXT["Extraction Agent\nExtract tasks + highlights\nStore as unconfirmed"]
    EXT -->|"extraction_complete = true"| SUP

    SUP -->|"session_action = confirm"| CONF["Confirmation Agent\nPresent tasks to user\nWait for response"]
    CONF -->|"yes"| SAVE_ALL["Save all tasks + highlights"]
    CONF -->|"partial"| SAVE_PARTIAL["Save selected tasks"]
    CONF -->|"no"| DISCARD["Discard all"]
    SAVE_ALL --> DASH(["Dashboard Updated"])
    SAVE_PARTIAL --> DASH
    DISCARD --> DASH

    SUP -->|"session_action = qa"| QA["Q&A Agent\nHybrid RAG - meeting namespace only\nBGE reranking - grounded answer"]
    QA --> ANS(["Answer + Sources to User"])

    SUP -->|"session_action = notify"| NOTIF["Notification Agent\nCheck deadlines in DB\nRAG context - AI email - Resend"]
    NOTIF --> EMAIL(["Email Sent to User"])

    Q_START(["User types question"]) -.->|"independent trigger"| SUP
    N_START(["APScheduler 08:00 AM"]) -.->|"independent trigger"| SUP
```

### Fallback Routing

```
gemini-3.6-flash (primary)
    ↓ if quota exhausted or error
thinkingmachines/inkling:free via OpenRouter
    ↓ if also fails
Error state set — user notified — operation halted gracefully
```

---

## 🔄 End-to-End Workflow

```mermaid
flowchart TD
    A(["User fills New Meeting Form\nname - role - org - date - transcript"]) --> B
    B["FastAPI POST /api/v1/meetings/\nSave: users, meetings, meeting_participants"] --> C
    C["LangGraph pipeline triggered\nmeeting_id + user_id"] --> D

    D["Supervisor Agent\nPlan: ingest - identify - extract - confirm"] --> E

    E["Ingestion Agent\nParse PDF / TXT / text\nSpeaker-aware chunking 200-300 tokens\nEmbed: gemini-embedding-001\nStore to Pinecone + transcript_chunks"] --> F

    F["Identity Agent\nRead user from meeting_participants\nSearch transcript_chunks for user mentions\nStore mentions - mark is_current_user=true"] --> G

    G["Extraction Agent\nExtract tasks: title, description, priority, deadline\nExtract highlights: decisions, announcements\nStore as unconfirmed"] --> H

    H["Confirmation Agent\nPresent task list in chat\nShow title + description only\nAwait user response"] --> I

    I{"User Response?"}
    I -->|"Yes"| J["Save all tasks + highlights"]
    I -->|"Partial"| K["Save selected tasks"]
    I -->|"No"| L["Discard tasks"]

    J --> M(["Dashboard Updated via FastAPI"])
    K --> M
    L --> M

    M -.->|"User asks question"| QA_PATH
    M -.->|"08:00 AM daily"| NOTIF_PATH

    subgraph QA_PATH["Q&A Path - Independent"]
        Q1["User types question in meeting chat"]
        Q2["Hybrid search: Pinecone top-10 + BM25 top-10"]
        Q3["Merge + Deduplicate - 15-20 chunks"]
        Q4["BGE Reranker - top 5"]
        Q5["gemini-3.6-flash generates grounded answer"]
        Q6["Store to chat_messages - return answer + sources"]
        Q1 --> Q2 --> Q3 --> Q4 --> Q5 --> Q6
    end

    subgraph NOTIF_PATH["Notification Path - Daily 08:00 AM"]
        N1["APScheduler fires"]
        N2["Query: pending AND deadline <= tomorrow AND alert_sent=false"]
        N3["RAG retrieval: top-3 chunks per task"]
        N4["AI compose email: title + deadline + description + transcript context"]
        N5["Send via Resend - Update alert_sent=true"]
        N1 --> N2 --> N3 --> N4 --> N5
    end
```

---

## 🔍 RAG Pipeline

MeetMind uses a three-stage retrieval pipeline: hybrid search → cross-encoder reranking → grounded generation.

### Pipeline Stages

| Stage | Component | Details |
|-------|-----------|---------|
| **1. Chunking** | `rag/chunker.py` | 200–300 tokens, 50-token overlap, speaker label preserved: `[SpeakerName - HH:MM]: text` |
| **2. Embedding** | `rag/embedder.py` — `gemini-embedding-001` | 3072-dim dense vectors |
| **3. Storage** | Pinecone + PostgreSQL | Vectors → namespace `meeting_{id}`; raw chunks → `transcript_chunks` table |
| **4. Semantic Search** | Pinecone similarity | Top-10 chunks by cosine similarity in meeting namespace |
| **5. Keyword Search** | BM25 via `rank-bm25` | Top-10 chunks by BM25 score on `transcript_chunks` in PostgreSQL |
| **6. Merge & Deduplicate** | `rag/retriever.py` | Combined by `chunk_index`, deduplicated → 15–20 chunks |
| **7. Reranking** | `BAAI/bge-reranker-v2-m3` — `rag/reranker.py` | Local CrossEncoder via `sentence-transformers`, returns top 5 |
| **8. Answer Generation** | `gemini-3.6-flash` | Top 5 reranked chunks + user identity context → grounded, source-attributed answer |
| **9. Citation** | Q&A Agent output | Each source: `{speaker, timestamp, excerpt}` |

### Chunk Metadata Schema

```python
{
    "meeting_id":    "uuid",
    "user_id":       "uuid",
    "speaker_name":  "str",
    "speaker_role":  "str",
    "timestamp":     "HH:MM",
    "chunk_index":   int,
    "meeting_date":  "YYYY-MM-DD",
    "meeting_title": "str",
    "chunk_type":    "dialogue | decision | task_mention",
    "involves_user": bool
}
```

### RAG Pipeline Diagram

```mermaid
flowchart LR
    Q(["User Question"]) --> HYBS

    subgraph HYBS["Hybrid Search - Parallel"]
        SEM["Pinecone\nSemantic Search\nmeeting namespace\nTop 10"]
        KW["BM25\nPostgreSQL transcript_chunks\nSame meeting_id\nTop 10"]
    end

    SEM --> MERGE
    KW --> MERGE

    MERGE["Merge + Deduplicate\nby chunk_index\n15-20 chunks"] --> RERANK

    RERANK["BGE Reranker\nBAAI/bge-reranker-v2-m3\nLocal CrossEncoder\nReturns Top 5"] --> GEN

    GEN["Answer Generation\ngemini-3.6-flash\nTop 5 chunks + identity context\nGrounded, source-attributed"] --> OUT

    OUT(["Answer + Sources\nEach: speaker, timestamp, excerpt"])
```

---

## 🗄 Database Architecture

PostgreSQL is the single source of truth. All agent inputs and outputs flow through the database.

### Entity-Relationship Diagram

```mermaid
erDiagram
    users {
        UUID id PK
        VARCHAR name
        VARCHAR email
        TIMESTAMP created_at
    }

    meetings {
        UUID id PK
        UUID user_id FK
        VARCHAR title
        VARCHAR organization
        DATE meeting_date
        VARCHAR meeting_time
        TEXT raw_transcript
        VARCHAR input_format
        VARCHAR pinecone_namespace
        TIMESTAMP created_at
    }

    meeting_participants {
        UUID id PK
        UUID meeting_id FK
        VARCHAR name
        VARCHAR role
        BOOLEAN is_current_user
    }

    tasks {
        UUID id PK
        UUID meeting_id FK
        UUID user_id FK
        VARCHAR title
        TEXT description
        VARCHAR priority
        DATE deadline
        VARCHAR status
        BOOLEAN alert_sent
        TIMESTAMP created_at
    }

    highlights {
        UUID id PK
        UUID meeting_id FK
        UUID user_id FK
        TEXT content
        TIMESTAMP created_at
    }

    chat_messages {
        UUID id PK
        UUID meeting_id FK
        UUID user_id FK
        VARCHAR role
        TEXT content
        TIMESTAMP created_at
    }

    transcript_chunks {
        UUID id PK
        UUID meeting_id FK
        INTEGER chunk_index
        VARCHAR speaker_name
        VARCHAR speaker_role
        TEXT content
        VARCHAR timestamp
        VARCHAR chunk_type
        BOOLEAN involves_user
        VARCHAR pinecone_vector_id
    }

    users ||--o{ meetings : "owns"
    meetings ||--o{ meeting_participants : "has"
    meetings ||--o{ tasks : "produces"
    meetings ||--o{ highlights : "produces"
    meetings ||--o{ chat_messages : "has"
    meetings ||--o{ transcript_chunks : "contains"
    users ||--o{ tasks : "assigned to"
    users ||--o{ highlights : "relevant to"
    users ||--o{ chat_messages : "authored by"
```

### Data Isolation

- Every table references `meeting_id` — all data is scoped to a single meeting
- Pinecone namespaces: `meeting_{meeting_id}` — semantic search never crosses meeting boundaries
- The Q&A Agent queries its namespace exclusively — cross-meeting contamination is architecturally impossible

### Agent State Persistence Map

| Agent Output | PostgreSQL Table | Column |
|-------------|-----------------|--------|
| User registration | `users` | id, name, email |
| Meeting creation | `meetings` | all columns |
| User identity | `meeting_participants` | name, role, is_current_user |
| Transcript chunks | `transcript_chunks` | all columns |
| User mentions flag | `transcript_chunks` | involves_user |
| Confirmed tasks | `tasks` | all columns |
| Confirmed highlights | `highlights` | all columns |
| Q&A messages | `chat_messages` | role, content |
| Alert tracking | `tasks` | alert_sent |

---

## 📱 Application Flow

MeetMind has three pages: **Landing**, **Workspace** (Dashboard + Meetings + Chat), and **Documentation**.

```mermaid
flowchart TD
    LAND["Landing Page\nHero section + CTA + Feature highlights"] -->|Navigate| WORK

    WORK["Workspace"] --> DASH_V & MEET_V

    DASH_V["Dashboard View\nAll tasks - all meetings unified\nFilter: priority, deadline, status\nToggle: pending/complete"]

    MEET_V["Meetings View\nList of all submitted meetings\nNew Meeting button"]

    MEET_V -->|Click New Meeting| FORM["New Meeting Form\nMeeting date + time\nOrganization, name, role\nTranscript: paste / PDF / TXT"]

    FORM -->|Submit| PIPE["Agent Pipeline\nIngestion - Identity - Extraction - Confirmation"]

    MEET_V -->|Click any meeting| MDET["Meeting Detail\nTask list for this meeting\nKey Highlights section"]

    MDET -->|Open chat| CHAT["Meeting Q&A Chat\nHybrid RAG scoped to this meeting\nChat history persisted in PostgreSQL"]

    WORK -.->|Navigate| DOCS["Documentation Page\nAgent roster, Models, RAG pipeline\nWorkflow diagram, Tech stack"]
```

---

## 🌐 API Overview

All endpoints are prefixed with `/api/v1`. API version: `1.0.0`.

### Users

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/v1/users/register` | Register a new user |
| `GET` | `/api/v1/users/{user_id}` | Get user profile |
| `PUT` | `/api/v1/users/{user_id}` | Update user details |

### Meetings

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/v1/meetings/` | Create meeting + trigger LangGraph pipeline |
| `GET` | `/api/v1/meetings/{user_id}` | Get all meetings for a user |
| `GET` | `/api/v1/meetings/{meeting_id}/detail` | Get single meeting detail |
| `DELETE` | `/api/v1/meetings/{meeting_id}` | Delete a meeting |

### Tasks

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/api/v1/tasks/{user_id}` | All tasks across all meetings |
| `GET` | `/api/v1/tasks/{user_id}/meeting/{meeting_id}` | Tasks for one specific meeting |
| `PUT` | `/api/v1/tasks/{task_id}/status` | Toggle task status (pending ↔ complete) |
| `GET` | `/api/v1/tasks/{user_id}/filter` | Filter tasks by priority, date, status |

### Chat (Q&A)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/v1/chat/{meeting_id}/message` | Send a Q&A message |
| `GET` | `/api/v1/chat/{meeting_id}/history` | Retrieve chat history |
| `DELETE` | `/api/v1/chat/{meeting_id}/history` | Clear chat history |

### Extraction

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/v1/extraction/{meeting_id}/run` | Run extraction pipeline |
| `GET` | `/api/v1/extraction/{meeting_id}/preview` | Preview extracted tasks |
| `POST` | `/api/v1/extraction/{meeting_id}/confirm` | Confirm and save tasks |

### Highlights

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/api/v1/highlights/{user_id}/meeting/{meeting_id}` | Meeting highlights |
| `GET` | `/api/v1/highlights/{user_id}` | All highlights across meetings |

### Notifications

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/v1/notifications/trigger` | Manually trigger notification check |
| `GET` | `/api/v1/notifications/{user_id}/pending` | Get pending deadline alerts |

### Health Probes

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/health` | Liveness probe |
| `GET` | `/health/db` | Database connectivity probe |
| `GET` | `/health/providers` | AI provider health summary (zero secrets exposed) |

---

## 📁 Project Folder Structure

```
meetmind-ai/
│
├── backend/                        # FastAPI backend
│   ├── app/
│   │   ├── agents/                 # One file per agent (7 agents)
│   │   │   ├── supervisor.py       # Plan-and-Execute orchestrator
│   │   │   ├── ingestion.py        # Transcript parsing + embedding
│   │   │   ├── identity.py         # User identification in transcript
│   │   │   ├── extraction.py       # Task + highlight extraction
│   │   │   ├── confirmation.py     # Human-in-the-loop confirmation
│   │   │   ├── qa.py               # Hybrid RAG Q&A
│   │   │   └── notification.py     # Deadline check + email
│   │   │
│   │   ├── tools/                  # One file per tool (24 tools)
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
│   │   │
│   │   ├── graph/                  # LangGraph orchestration
│   │   │   ├── graph.py            # Full graph definition
│   │   │   ├── state.py            # MeetMindState TypedDict
│   │   │   └── router.py           # supervisor_router + confirmation_router
│   │   │
│   │   ├── rag/                    # RAG pipeline
│   │   │   ├── chunker.py          # Speaker-aware chunking
│   │   │   ├── embedder.py         # gemini-embedding-001
│   │   │   ├── retriever.py        # Hybrid search: Pinecone + BM25
│   │   │   └── reranker.py         # BAAI/bge-reranker-v2-m3
│   │   │
│   │   ├── api/                    # FastAPI routers (21 endpoints)
│   │   │   ├── router.py           # Aggregates all routers
│   │   │   ├── users.py
│   │   │   ├── meetings.py
│   │   │   ├── tasks.py
│   │   │   ├── chat.py
│   │   │   ├── extraction.py
│   │   │   ├── highlights.py
│   │   │   └── notifications.py
│   │   │
│   │   ├── db/                     # Database layer
│   │   │   ├── base.py             # SQLAlchemy declarative base
│   │   │   ├── session.py          # Session factory + dependency
│   │   │   └── models/             # One file per table (7 tables)
│   │   │       ├── user.py
│   │   │       ├── meeting.py
│   │   │       ├── meeting_participant.py
│   │   │       ├── task.py
│   │   │       ├── highlight.py
│   │   │       ├── chat_message.py
│   │   │       └── transcript_chunk.py
│   │   │
│   │   ├── services/               # Business logic (one file per domain)
│   │   │   ├── user_service.py
│   │   │   ├── meeting_service.py
│   │   │   ├── task_service.py
│   │   │   ├── chat_service.py
│   │   │   ├── extraction_service.py
│   │   │   ├── highlight_service.py
│   │   │   └── notification_service.py
│   │   │
│   │   ├── schemas/                # Pydantic request/response schemas
│   │   │   ├── user.py
│   │   │   ├── meeting.py
│   │   │   ├── task.py
│   │   │   ├── chat.py
│   │   │   ├── extraction.py
│   │   │   ├── highlight.py
│   │   │   └── notification.py
│   │   │
│   │   ├── core/                   # App configuration
│   │   │   ├── settings.py         # Pydantic BaseSettings — all env vars
│   │   │   ├── config.py           # Static config: model names, chunk sizes
│   │   │   └── constants.py        # Enums, string constants
│   │   │
│   │   └── main.py                 # FastAPI app factory + lifespan
│   │
│   ├── alembic/                    # DB migration management
│   │   └── versions/               # Migration scripts
│   ├── alembic.ini
│   ├── .env.example
│   ├── requirements.txt
│   └── tests/                      # Backend tests
│       ├── api/
│       ├── test_chunker.py
│       ├── test_embedder.py
│       ├── test_retriever.py
│       ├── test_services.py
│       ├── test_batch3.py
│       ├── test_batch4.py
│       ├── test_batch6_deadline_semantics.py
│       ├── test_notifications_hardening.py
│       ├── test_notifications_rules.py
│       └── test_qa_validation.py
│
├── frontend/                       # Streamlit frontend
│   ├── app.py                      # Entry point — navigation + page dispatch
│   ├── pages/
│   │   ├── landing.py
│   │   ├── workspace.py
│   │   └── documentation.py
│   ├── components/
│   │   ├── task_card.py
│   │   ├── meeting_card.py
│   │   ├── chat_bubble.py
│   │   ├── new_meeting_form.py
│   │   ├── task_filter.py
│   │   ├── highlight_card.py
│   │   ├── layout.py
│   │   ├── sidebar.py
│   │   └── state_displays.py
│   ├── services/
│   │   └── api_client.py           # HTTP client wrapping all FastAPI calls
│   ├── utils/
│   │   └── session_state.py
│   ├── assets/
│   │   └── styles.css
│   ├── .env.example
│   ├── requirements.txt
│   └── tests/
│       └── test_frontend_workflows.py
│
├── tests/                          # Top-level integration tests
│   └── integration/
│       ├── test_e2e_pipeline.py
│       └── test_security_isolation.py
│
├── docs/                           # Project documentation
│   ├── AGENT_FLOW.md
│   ├── ARCHITECTURE.md
│   ├── FEATURES.md
│   ├── Summarization.md
│   └── assets/
│       └── hero_banner.jpg
│
├── data/
│   └── sample_transcripts/         # 3 realistic test transcripts
│       ├── transcript_kickoff.txt
│       ├── transcript_sprint_review.txt
│       └── transcript_emergency_bug.txt
│
├── .env.common.example
├── requirements.common.txt
├── .gitignore
└── README.md
```

---

## 🔐 Security & Data Isolation

### Implemented Protections

| Area | Implementation |
|------|---------------|
| **Meeting-scoped retrieval** | Q&A Agent queries only `meeting_{meeting_id}` Pinecone namespace — cross-meeting contamination is architecturally impossible |
| **Per-meeting DB isolation** | All tables reference `meeting_id` — every query filters to a specific meeting |
| **Environment-based secrets** | All API keys loaded exclusively through `core/settings.py` (Pydantic BaseSettings) — no `os.environ` calls in application code |
| **Secret-safe error responses** | Global `MeetMindError` exception handler strips raw credentials and stack traces from HTTP responses |
| **API key rotation** | Provider gateway supports up to 20 Gemini keys with round-robin rotation, health-aware selection, and exponential cooldown |
| **Input validation** | All API request/response bodies are Pydantic schemas — no unvalidated raw input reaches business logic |
| **Error handling** | All external API calls have retry logic with exponential backoff; no bare `except` blocks |
| **CORS configuration** | Explicit allowlist: `localhost:8501`, `localhost:3000` |

### Not Yet Implemented

> The following are outside the current project scope:
> - User authentication or session tokens
> - Rate limiting on API endpoints
> - Role-based access control
> - HTTPS enforcement (delegated to Render/Vercel)

---

## 🧪 Testing & Validation

### Testing Framework

All tests use **pytest** as the primary test runner.

### Test Categories

| Test File | Coverage Area |
|-----------|--------------|
| `tests/integration/test_e2e_pipeline.py` | Full pipeline end-to-end tests |
| `tests/integration/test_security_isolation.py` | Meeting data isolation tests |
| `backend/tests/test_chunker.py` | Speaker-aware chunker unit tests |
| `backend/tests/test_embedder.py` | Embedding generation tests |
| `backend/tests/test_retriever.py` | Hybrid retriever tests |
| `backend/tests/test_services.py` | Service layer tests |
| `backend/tests/test_batch3.py` | RAG pipeline integration tests |
| `backend/tests/test_batch4.py` | Backend service + agent integration |
| `backend/tests/test_batch6_deadline_semantics.py` | Deadline handling edge cases |
| `backend/tests/test_notifications_hardening.py` | Notification failure handling |
| `backend/tests/test_notifications_rules.py` | Notification business rule tests |
| `backend/tests/test_qa_validation.py` | Q&A agent output validation |
| `frontend/tests/test_frontend_workflows.py` | Frontend component tests |

### Running Tests

```bash
# Backend tests
cd backend
python -m pytest tests/ -v

# Specific test file
python -m pytest tests/test_chunker.py -v

# Integration tests (from project root)
python -m pytest tests/integration/ -v

# All tests with output
python -m pytest tests/ -v -s
```

> **Note:** Some tests require active database connectivity and configured API keys. Verify your `.env` file before running integration tests.

---

## ⚠️ Limitations & Scope

The following capabilities are **outside the current project scope** and are not implemented:

| Out-of-Scope Capability | Reason |
|------------------------|--------|
| **User authentication / login** | No AI engineering value; single-user system by design |
| **Real-time meeting recording** | Requires external audio/video services; out of scope |
| **Multi-user team dashboards** | Adds DB complexity without AI depth |
| **Cross-meeting Q&A** | Scope creep; meeting-scoped Q&A is cleaner and more controlled |
| **Mobile push notifications** | Email covers alerting adequately |
| **Task analytics / charts** | Not a core AI engineering showcase |

### Single-User Design

MeetMind is a **single-user system** with no authentication layer. Users identify themselves through the New Meeting form. Each form submission creates a user record using the submitted email as a unique identifier.

---

## 🗺 Roadmap

### ✅ Completed (All 6 Gates)

- [x] **Gate 1 — DB Architecture:** SQLAlchemy models (7 tables), Alembic migrations, DB session
- [x] **Gate 2 — AI Agents:** LangGraph state + graph + router, all 7 agents, all 24 tools
- [x] **Gate 3 — RAG Pipeline:** Speaker-aware chunker, embedder, hybrid retriever, BGE reranker, Pinecone
- [x] **Gate 4 — Backend:** FastAPI (21 endpoints), services, schemas, APScheduler, provider gateway with key rotation
- [x] **Gate 5 — Frontend:** Streamlit landing, workspace, documentation; all components; `api_client.py`
- [x] **Gate 6 — Integration:** End-to-end wiring, deadline data audit, integration + security tests

### 🔮 Future Enhancements

> *Potential future directions — not committed milestones.*

- [ ] User authentication (JWT or OAuth)
- [ ] Multi-user team dashboards with shared meeting visibility
- [ ] Cross-meeting Q&A mode with explicit user opt-in
- [ ] Meeting recording → transcript transcription integration
- [ ] Task analytics and deadline completion trends

---

## 🤝 Contribution Guidelines

Contributions are welcome. Please follow these guidelines to maintain code quality.

### Branch Strategy

```
main                  ← always stable, deploy-ready
gate/{gate-name}     ← development gate branches
feature/{name}       ← new feature additions
fix/{description}    ← bug fixes
```

### Workflow

1. Fork the repository
2. Create a branch from `main`: `git checkout -b feature/your-feature`
3. Make changes following the coding rules below
4. Run all tests: `python -m pytest tests/ -v`
5. Commit with a descriptive message
6. Push and open a Pull Request against `main`

### Coding Rules

| Rule | Requirement |
|------|-------------|
| **One file, one responsibility** | No mixed concerns; no business logic in route files |
| **Type hints** | Required on every function signature |
| **Docstrings** | Required on every function |
| **No bare except** | Always catch specific exception types |
| **Error handling** | Every external API call must have retry or fallback logic |
| **Settings** | All env vars loaded exclusively via `core/settings.py` |
| **DB changes** | All schema changes via Alembic migrations only |
| **Agent isolation** | Agents never call each other directly — coordination via LangGraph state |
| **Testing** | New features should include corresponding tests |

---

## 📄 License

License information has not yet been specified.

---

## 🖥 Local Installation & Execution

Follow these steps to run MeetMind AI on your local machine. Two terminal sessions are required.

### Prerequisites

| Requirement | Notes |
|-------------|-------|
| Python 3.11+ | Required |
| PostgreSQL | Running instance (local or cloud) |
| Git | For cloning |
| Pinecone Account | Index: `hackathon-index`, 3072 dims, cosine metric, AWS us-east-1 |
| Google Gemini API Key | At least 1 key from [aistudio.google.com](https://aistudio.google.com) |
| Resend Account | API key from [resend.com](https://resend.com) |
| OpenRouter API Key | Optional — for fallback LLM (free models available) |

---

### Step 1 — Clone the Repository

```bash
git clone https://github.com/ankush-poonia007/meetmind-ai.git
cd meetmind-ai
```

### Step 2 — Create a Virtual Environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### Step 3 — Install Dependencies

```bash
# Backend
cd backend
pip install -r requirements.txt
```

```bash
# Frontend (new terminal)
cd frontend
pip install -r requirements.txt
```

### Step 4 — Configure Environment Variables

**Backend** (`backend/.env`):
```bash
cd backend
cp .env.example .env
```

Edit `backend/.env` with your actual credentials:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/meetmind_db

# Google Gemini (at least 1 key required)
GOOGLE_API_KEY_1=your_google_api_key_here

# OpenRouter (optional fallback)
OPENROUTER_API_KEY_1=your_openrouter_api_key_here

# Pinecone
PINECONE_API_KEY=your_pinecone_api_key_here
PINECONE_INDEX_NAME=hackathon-index

# Resend Email
RESEND_API_KEY=your_resend_api_key_here
RESEND_SENDER=onboarding@resend.dev

# Scheduler
NOTIFICATION_HOUR=8
NOTIFICATION_MINUTE=0

# App
APP_ENV=development
DEBUG=true
```

**Frontend** (`frontend/.env`):
```bash
cd frontend
cp .env.example .env
```

Set `BACKEND_URL=http://localhost:8000` in `frontend/.env`.

**Common** (project root):
```bash
cp .env.common.example .env.common
```

### Step 5 — Set Up the Database

```bash
createdb meetmind_db
```

### Step 6 — Run Migrations

```bash
cd backend
alembic upgrade head
```

This creates all 7 tables: `users`, `meetings`, `meeting_participants`, `tasks`, `highlights`, `chat_messages`, `transcript_chunks`.

### Step 7 — Start the Backend

**Terminal 1** (from `backend/`):
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verify at:
- API Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health
- DB Health: http://localhost:8000/health/db

### Step 8 — Start the Frontend

**Terminal 2** (from `frontend/`):
```bash
python -m streamlit run app.py
```

Opens at: **http://localhost:8501**

### Step 9 — Test the Setup

1. Open http://localhost:8501 in your browser
2. Navigate to **Workspace** → **New Meeting**
3. Fill in your name, role, organization, and paste content from `data/sample_transcripts/transcript_kickoff.txt`
4. Submit — the LangGraph pipeline triggers automatically
5. The Confirmation Agent will present extracted tasks in the chat
6. Confirm tasks to see them appear on the dashboard

### Troubleshooting

| Issue | Solution |
|-------|---------|
| `DATABASE_URL` connection refused | Ensure PostgreSQL is running and credentials are correct |
| Gemini API key errors | Verify key is active at [aistudio.google.com](https://aistudio.google.com) |
| `alembic upgrade head` fails | Check `DATABASE_URL` and that `meetmind_db` exists |
| Pinecone connection error | Verify `PINECONE_API_KEY` and that `hackathon-index` has 3072 dimensions |
| Streamlit cannot reach backend | Confirm FastAPI is on port 8000; check `BACKEND_URL` in `frontend/.env` |
| BGE Reranker slow on first run | Model downloaded on first use (~500 MB); cached afterwards |
| Emails not sending | Verify `RESEND_API_KEY`; check FastAPI logs for scheduler confirmation |

---

## 📬 Contact

**Developer:** Ankush Poonia

- **GitHub:** [ankush-poonia007](https://github.com/ankush-poonia007/)
- **LinkedIn:** [Ankush Poonia](https://www.linkedin.com/in/ankush-poonia007/)
- **Email:** [pooniaankush007@gmail.com](mailto:pooniaankush007@gmail.com)

---

<div align="center">

*Built for Domain Verse 1.0 Hackathon — Agentic AI Domain — PS-09: AI Meeting Assistant*

**"MeetMind doesn't just read your meetings — it knows who you are in them."**

</div>

