# GATE_4_ANALYSIS.md — MeetMind AI Backend API + Service Infrastructure

**Gate:** 4 — Backend  
**Branch:** gate-4/agent-orchestration  
**Analysis Date:** 2026-09-24  
**Status:** ANALYSIS ONLY — DO NOT IMPLEMENT  
**Analyst:** Antigravity AI

---

## 1. Executive Summary

Gate 4 is responsible for connecting the three frozen lower gates to the application's HTTP API surface and background execution infrastructure. The database (Gate 1), provider/core infrastructure (Gate 2), and RAG pipeline (Gate 3) are all frozen and must be consumed as-is.

**Key finding:** The repository is exceptionally well-scaffolded for Gate 4. All Pydantic schemas are complete and correct. The exception hierarchy, logging infrastructure, settings, session factory, DB models, and lifespan/scheduler skeleton in `main.py` are production-ready. All 21 endpoint contracts can be recovered directly from the frozen architecture.

**Critical gap:** `graph/graph.py` and `graph/router.py` are **empty**. All `app/agents/*.py`, `app/api/*.py` routers (except stub `router.py`), `app/services/*.py`, and `app/tools/*.py` files are **empty**. This is expected — Gate 4 implements all of these.

**Schema bug discovered (minor):** `TaskCreate` in `schemas/task.py` line 33 references `TaskStatus.PENDING` (uppercase), but the `TaskStatus` enum in `db/models/task.py` uses lowercase values (`pending`, `complete`). Must be resolved before service implementation.

**Schema gap discovered:** `ChatRequest` is missing `user_name` and `user_role` fields that the Q&A Agent requires. Chat service must look these up from `meeting_participants` before graph invocation.

**CORS gap:** `main.py` only allows `localhost:8501` and `localhost:3000`. Production Vercel URL is not listed.

**Architecture conflict:** `Meeting.title` is `NOT NULL` in the DB model, but title is extracted by the Ingestion Agent — not available at form submission time. A placeholder title strategy must be decided before Batch 1.

**Verdict:** PASS WITH CORRECTIONS — 5 critical decisions required before implementation begins.

---

## 2. Current Repository State

### 2.1 Frozen Gate Status

| Gate | Domain | Status | Files State |
|------|--------|--------|------------|
| Gate 1 | DB Foundation | Frozen | All 7 models complete, 1 migration, session factory live |
| Gate 2 | Provider Infrastructure | Frozen | gateway.py, key_pool.py, policies.py, models.py complete |
| Gate 3 | RAG Pipeline | Frozen | chunker.py, embedder.py, reranker.py, retriever.py complete |
| Gate 4 | Backend API | Not Implemented | Scaffold only |

### 2.2 What Exists in Gate 4 Scope (Scaffold vs Complete)

| File/Directory | State | Notes |
|---------------|-------|-------|
| `app/main.py` | Complete | Lifespan, CORS, health probes, router mount, exception handler |
| `app/api/router.py` | Stub | Prefix defined, no domain routers attached |
| `app/api/users.py` | Empty | 0 bytes |
| `app/api/meetings.py` | Empty | 0 bytes |
| `app/api/tasks.py` | Empty | 0 bytes |
| `app/api/chat.py` | Empty | 0 bytes |
| `app/api/extraction.py` | Empty | 0 bytes |
| `app/api/highlights.py` | Empty | 0 bytes |
| `app/api/notifications.py` | Empty | 0 bytes |
| `app/services/*.py` | Empty | 7 files, all 0 bytes |
| `app/schemas/*.py` | Complete | All 7 schema files fully defined |
| `app/graph/state.py` | Complete | MeetMindState TypedDict defined |
| `app/graph/graph.py` | Empty | Gate 4 must implement |
| `app/graph/router.py` | Empty | Gate 4 must implement |
| `app/agents/*.py` | Empty | 7 agent files, all empty |
| `app/tools/*.py` | Empty | 24 tool files, all empty |

---

## 3. Frozen Architecture Dependencies

### 3.1 Gate 1 — Database Foundation

**Key dependency contracts:**

- `get_db()` from `app.db.session` yields `Session` per request; always closed in `finally`
- `SessionLocal()` for background tasks that need their own session
- 7 ORM models: `User`, `Meeting`, `MeetingParticipant`, `Task`, `Highlight`, `ChatMessage`, `TranscriptChunk`
- All primary keys: `UUID(as_uuid=True)` with Python `uuid.UUID`
- `Task` model uses `TaskPriority` and `TaskStatus` Enums defined inline (lowercase: `pending`, `complete`, `high`, `medium`, `low`)
- `ChatMessage` uses `ChatRole` inline enum (lowercase: `user`, `assistant`)
- `MeetingParticipant` has **no `user_id` FK** — identity matched by name/role, not by users.id reference
- `Meeting.title` is `Mapped[str]` (NOT NULL) — conflicts with pre-agent creation

**Conflict: Meeting.title NOT NULL**
`MeetingCreate.title` is Optional (title extracted later by Ingestion Agent). A placeholder must be inserted on creation. This is Open Decision OD-01.

**Conflict: TaskStatus enum case**
`schemas/task.py` imports from `core.constants.TaskStatus` (uppercase `.PENDING`). `db/models/task.py` defines its own `TaskStatus` (lowercase `.pending`). Services bridge these and must use `.value` (lowercase string) for DB writes. This is Open Decision OD-02.

### 3.2 Gate 2 — Provider Infrastructure

**Key dependency contracts:**

- `get_provider_gateway()` returns the singleton `ProviderGateway`
- `gateway.execute(use_case, operation)` is the **only** approved way to call any AI provider
- Valid `use_case` values: `"supervisor"`, `"sub_agent"`, `"qa"`, `"embedding"`, `"fallback"`, `"backup"`, `"web_search"`
- Operation callable receives `(raw_credential, model_string)` — builds LLM client inside closure
- `app.state.provider_gateway` accessible via `Request` in any route
- Gate 4 **must never** access `settings.gemini_api_key_*` directly

### 3.3 Gate 3 — RAG Pipeline

**Key dependency contracts:**

```python
# Top-level hybrid retrieval function
from app.rag.retriever import retrieve
chunks: list[RetrievedChunk] = retrieve(
    meeting_id=meeting_id,   # str or UUID — HARD meeting isolation boundary
    query=user_question,     # str
    db_session=db,           # SQLAlchemy Session (required for BM25 path)
)

# Ingestion embedding interface
from app.rag.embedder import TranscriptEmbedder
embedder = TranscriptEmbedder()
embedder.embed_and_store(chunks, meeting_id, db_session)
```

- Pinecone namespace: `meeting_{meeting_id}` — enforced by `get_meeting_namespace()`
- BM25 path uses the SQLAlchemy `db_session` — must not be None
- `HybridRetriever` is stateless, instantiated per call
- Retrieval is **strictly meeting-scoped** — passing a wrong `meeting_id` is a silent security violation

---

## 4. Backend Responsibility Boundary

```
HTTP Request
     ↓
FastAPI Router  (path/query param validation, Pydantic body parsing)
     ↓
Service Layer   (business logic, ORM queries, orchestration)
     ↓
┌──────────────────────────────────────────────────────────┐
│  Gate 1: DB Session (get_db / SessionLocal)              │
│  Gate 2: ProviderGateway.execute()                       │
│  Gate 3: retrieve() / TranscriptEmbedder                 │
│  LangGraph Graph (graph.py — new in Gate 4)              │
│  APScheduler (job registration — new in Gate 4)          │
└──────────────────────────────────────────────────────────┘
     ↓
HTTP Response (Pydantic-serialized ORM objects)
```

**Routes must NOT contain:** Direct ORM queries, agent reasoning, RAG calls, API key access, scheduler logic, business validation beyond schema validation.

**Services must NOT contain:** HTTP constructs, provider key handling, Pydantic serialization, duplicate RAG logic.

---

## 5. API Inventory

All 21 endpoints recovered from `ARCHITECTURE.md` Section 8. All router files currently empty.

| # | Method | Endpoint | Request Schema | Response Schema |
|---|--------|----------|---------------|-----------------|
| 1 | POST | `/api/v1/users/register` | `UserCreate` | `UserResponse` (201) |
| 2 | GET | `/api/v1/users/{user_id}` | — | `UserResponse` |
| 3 | PUT | `/api/v1/users/{user_id}` | `UserUpdate` | `UserResponse` |
| 4 | POST | `/api/v1/meetings/` | `MeetingCreate` | `MeetingResponse` (202) |
| 5 | GET | `/api/v1/meetings/{user_id}` | — | `list[MeetingListItem]` |
| 6 | GET | `/api/v1/meetings/{meeting_id}/detail` | — | `MeetingDetail` |
| 7 | DELETE | `/api/v1/meetings/{meeting_id}` | — | 204 |
| 8 | GET | `/api/v1/tasks/{user_id}` | — | `list[TaskResponse]` |
| 9 | GET | `/api/v1/tasks/{user_id}/meeting/{meeting_id}` | — | `list[TaskResponse]` |
| 10 | PUT | `/api/v1/tasks/{task_id}/status` | `TaskStatusUpdate` | `TaskResponse` |
| 11 | GET | `/api/v1/tasks/{user_id}/filter` | `TaskFilterParams` (query) | `list[TaskResponse]` |
| 12 | POST | `/api/v1/chat/{meeting_id}/message` | `ChatRequest` | `ChatResponse` |
| 13 | GET | `/api/v1/chat/{meeting_id}/history` | — | `ChatHistoryResponse` |
| 14 | DELETE | `/api/v1/chat/{meeting_id}/history` | — | 204 |
| 15 | POST | `/api/v1/extraction/{meeting_id}/run` | `ExtractionRunRequest` | `MeetingResponse` (202) |
| 16 | GET | `/api/v1/extraction/{meeting_id}/preview` | — | `ExtractionPreviewResponse` |
| 17 | POST | `/api/v1/extraction/{meeting_id}/confirm` | `ExtractionConfirmRequest` | `ExtractionResult` |
| 18 | GET | `/api/v1/highlights/{user_id}/meeting/{meeting_id}` | — | `HighlightListResponse` |
| 19 | GET | `/api/v1/highlights/{user_id}` | — | `HighlightListResponse` |
| 20 | POST | `/api/v1/notifications/trigger` | `NotificationTriggerRequest` | `NotificationStatusResponse` |
| 21 | GET | `/api/v1/notifications/{user_id}/pending` | — | `list[PendingAlertResponse]` |

### 5.1 Path Ambiguity Issues

**Meetings router:** `GET /meetings/{meeting_id}/detail` vs `GET /meetings/{user_id}` — FastAPI cannot distinguish by UUID type alone. Must register `/meetings/{meeting_id}/detail` **before** `/meetings/{user_id}`. This is Open Decision OD-03.

**Tasks router:** `GET /tasks/{user_id}/filter` and `GET /tasks/{user_id}/meeting/{meeting_id}` must be registered **before** `GET /tasks/{user_id}` to prevent premature path matching.

### 5.2 Schema Issues Found

| Schema | Issue |
|--------|-------|
| `MeetingCreate.title` | Optional but `Meeting.title` NOT NULL — needs placeholder |
| `TaskCreate.status` | References `TaskStatus.PENDING` (uppercase enum member) |
| `ChatRequest` | Missing `user_name`, `user_role` needed by Q&A Agent (service must look up) |
| `ExtractionRunRequest` | Has `meeting_id` AND `user_id` — redundant with path param |

---

## 6. Service Layer Plan

### 6.1 `user_service.py`

| Function | Responsibility |
|----------|---------------|
| `create_user(db, data: UserCreate) → User` | Check duplicate email → `DuplicateUserError`, create + commit |
| `get_user(db, user_id: UUID) → User` | Query PK → `UserNotFoundError` if absent |
| `update_user(db, user_id, data: UserUpdate) → User` | Partial update, check email uniqueness if changing, commit |

### 6.2 `meeting_service.py`

| Function | Responsibility |
|----------|---------------|
| `create_meeting(db, data: MeetingCreate) → Meeting` | Verify user exists, create Meeting with placeholder title, create MeetingParticipant (is_current_user=True), commit |
| `list_meetings(db, user_id: UUID) → list[Meeting]` | Filter by user_id, order by `created_at DESC` |
| `get_meeting_detail(db, meeting_id: UUID) → Meeting` | Load with participants, raise `MeetingNotFoundError` if absent |
| `delete_meeting(db, meeting_id: UUID) → None` | Verify ownership, cascade via FK constraints, commit |

### 6.3 `task_service.py`

| Function | Responsibility |
|----------|---------------|
| `list_user_tasks(db, user_id: UUID) → list[Task]` | Filter by user_id, order by deadline ASC NULLS LAST + priority case() |
| `list_meeting_tasks(db, user_id, meeting_id) → list[Task]` | Filter by both user_id AND meeting_id; verify meeting ownership |
| `update_task_status(db, task_id, status) → Task` | Verify task.user_id matches param; update status; do NOT reset alert_sent |
| `filter_tasks(db, user_id, params: TaskFilterParams) → list[Task]` | Dynamic AND filter: priority, status, deadline_before, deadline_after |

### 6.4 `chat_service.py`

| Function | Responsibility |
|----------|---------------|
| `send_message(db, meeting_id, request, gateway) → ChatResponse` | Verify meeting ownership; look up identity from meeting_participants; get last 5 chat messages; invoke Q&A graph; persist user + assistant messages |
| `get_history(db, meeting_id, user_id) → ChatHistoryResponse` | Query chat_messages by meeting_id + user_id, order by created_at ASC |
| `clear_history(db, meeting_id, user_id) → None` | Delete all chat_messages for meeting + user |

### 6.5 `extraction_service.py`

| Function | Responsibility |
|----------|---------------|
| `run_pipeline(db, meeting_id, user_id, gateway) → dict` | Build initial state, invoke graph (reaches HITL pause at confirmation), return status + extracted_tasks |
| `get_preview(db, meeting_id) → ExtractionPreviewResponse` | Read extracted items from interrupted graph state via checkpointer |
| `confirm(db, meeting_id, request, gateway) → ExtractionResult` | Resume graph with user_confirmation + confirmed_task_ids |

### 6.6 `highlight_service.py`

| Function | Responsibility |
|----------|---------------|
| `get_meeting_highlights(db, user_id, meeting_id) → HighlightListResponse` | Filter by both user_id AND meeting_id; verify meeting ownership |
| `get_user_highlights(db, user_id) → HighlightListResponse` | Filter by user_id across all meetings, order by created_at DESC |

### 6.7 `notification_service.py`

| Function | Responsibility |
|----------|---------------|
| `get_pending_alerts(db, user_id) → list[PendingAlertResponse]` | Filter: user_id + status=pending + deadline≤tomorrow + alert_sent=false |
| `trigger(db, request, gateway) → NotificationStatusResponse` | Invoke Notification Agent graph with trigger type |
| `run_notification_job() → None` | APScheduler async job; creates own SessionLocal(); invokes notification graph; closes session in finally |

---

## 7. LangGraph Integration Plan

### 7.1 Current State

`app/graph/graph.py` and `app/graph/router.py` are empty. `app/graph/state.py` (MeetMindState) is complete. Gate 4 must implement full graph compilation.

### 7.2 Three Pipeline Entry Points

| Pipeline | Initial `session_action` | Node Sequence |
|----------|--------------------------|---------------|
| New Meeting | `"ingest"` | supervisor → ingestion → identity → extraction → **INTERRUPT at confirmation** |
| Q&A | `"qa"` | supervisor → qa → END |
| Notification | `"notify"` | supervisor → notification → END |

### 7.3 Graph Compilation (Analysis Only)

```python
# graph/graph.py — conceptual structure, DO NOT implement
graph = StateGraph(MeetMindState)
graph.add_node("supervisor", supervisor_node)
graph.add_node("ingestion", ingestion_node)
graph.add_node("identity", identity_node)
graph.add_node("extraction", extraction_node)
graph.add_node("confirmation", confirmation_node)   # HITL interrupt
graph.add_node("qa", qa_node)
graph.add_node("notification", notification_node)
graph.add_conditional_edges("supervisor", route_supervisor, {
    "ingest": "ingestion",
    "identify": "identity",
    "extract": "extraction",
    "confirm": "confirmation",
    "qa": "qa",
    "notify": "notification",
    "complete": END,
})
graph.set_entry_point("supervisor")

compiled = graph.compile(
    checkpointer=checkpointer,      # OD-05: MemorySaver or PostgresSaver
    interrupt_before=["confirmation"],
)
```

### 7.4 Thread Identification

| Pipeline | `thread_id` |
|----------|-------------|
| Main pipeline | `str(meeting_id)` |
| Q&A | `f"{meeting_id}:qa"` |
| Notification | `f"notify:{today.isoformat()}"` |

### 7.5 Checkpointer Selection

**Open Decision OD-05:** `MemorySaver` (simple, lost on restart) vs `PostgresSaver` (persistent, requires `langgraph-checkpoint-postgres` dependency).

### 7.6 Initial State Construction

```python
# In extraction_service.run_pipeline() — analysis only
initial_state: MeetMindState = {
    "user_id": str(user_id),
    "meeting_id": str(meeting_id),
    "session_action": "ingest",
    "input_format": meeting.input_format,
    "raw_transcript": meeting.raw_transcript,
    "user_name": participant.name,
    "user_role": participant.role or "",
}
thread_config = {"configurable": {"thread_id": str(meeting_id)}}
```

---

## 8. HITL Integration Plan

### 8.1 The Pause/Resume Flow

```
POST /api/v1/extraction/{meeting_id}/run
  → extraction_service.run_pipeline()
  → graph.invoke(initial_state) → runs to confirmation INTERRUPT
  → Service returns: {"status": "awaiting_confirmation", "extracted_tasks": [...]}

GET /api/v1/extraction/{meeting_id}/preview
  → extraction_service.get_preview()
  → Read state from checkpointer by thread_id=meeting_id
  → Returns: ExtractionPreviewResponse

POST /api/v1/extraction/{meeting_id}/confirm
  → extraction_service.confirm()
  → graph.invoke(
       {"user_confirmation": "yes/no/partial", "confirmed_task_ids": [...]},
       config={"configurable": {"thread_id": str(meeting_id)}}
     )
  → Confirmation Agent saves/discards tasks
  → Returns: ExtractionResult
```

### 8.2 HITL Not an Error

LangGraph interrupt is not an exception. The service detects it by checking the returned state:
- `state.get("session_action") != "complete"` and no `state.get("error")` → HITL pause
- `state.get("error")` → pipeline failure → raise `PipelineError`
- `state.get("session_action") == "complete"` → pipeline finished

### 8.3 Unconfirmed State Handling

If user never confirms: graph state persists in checkpointer (or is lost if MemorySaver + restart). `extracted_tasks` remain in state. Per AGENT_FLOW.md: "tasks remain as unconfirmed in DB, surfaced again on next visit." The `preview` endpoint covers this use case.

---

## 9. Q&A Integration Plan

### 9.1 Meeting Isolation — Dual Check

Service must verify ownership AND RAG enforces namespace isolation:

```python
# In chat_service.send_message() — analysis only
# Check 1: Service-level ownership check
meeting = db.query(Meeting).filter(
    Meeting.id == meeting_id,
    Meeting.user_id == user_id,  # CRITICAL
).first()
if not meeting:
    raise MeetingNotFoundError(...)

# Check 2: RAG enforces meeting_{meeting_id} namespace automatically
chunks = retrieve(meeting_id=meeting_id, query=question, db_session=db)
```

### 9.2 Identity Context Resolution

Chat service must look up identity before graph invocation (ChatRequest has no identity fields):

```python
participant = db.query(MeetingParticipant).filter(
    MeetingParticipant.meeting_id == meeting_id,
    MeetingParticipant.is_current_user == True,
).first()
```

### 9.3 Chat History for Q&A Context

```python
# Retrieved by Q&A Agent or injected via state
history = db.query(ChatMessage).filter_by(
    meeting_id=meeting_id, user_id=user_id
).order_by(ChatMessage.created_at.desc()).limit(5).all()
```

### 9.4 Dual Message Persistence

Both user question and assistant answer saved to `chat_messages` after each Q&A cycle.

---

## 10. Task/Highlight API Plan

### 10.1 Task Endpoints Detail

| Endpoint | Security Check | ORM Logic |
|----------|---------------|-----------|
| GET tasks/{user_id} | user_id from path | Filter by user_id; order by deadline ASC NULLS LAST, priority case() |
| GET tasks/{user_id}/meeting/{meeting_id} | Verify Meeting.user_id == user_id | Filter by both user_id AND meeting_id |
| PUT tasks/{task_id}/status | Verify Task.user_id matches user_id in body | Update status only; do NOT reset alert_sent |
| GET tasks/{user_id}/filter | user_id from path | Dynamic AND filter on priority, status, deadline range |

### 10.2 Priority Sort Order

SQLAlchemy `case()` expression required since PostgreSQL enum ordering is not semantic:

```python
# analysis only
from sqlalchemy import case
priority_order = case(
    {"high": 1, "medium": 2, "low": 3},
    value=Task.priority
)
query.order_by(Task.deadline.asc().nullslast(), priority_order.asc())
```

This is Open Decision OD-06.

### 10.3 Highlight Endpoints Detail

| Endpoint | Filter Logic |
|----------|-------------|
| GET highlights/{user_id}/meeting/{meeting_id} | user_id AND meeting_id; verify meeting ownership |
| GET highlights/{user_id} | user_id only; order by created_at DESC |

---

## 11. Notification/Scheduler Plan

### 11.1 Current Scheduler State

`main.py` already starts `AsyncIOScheduler` in lifespan and stores on `app.state.scheduler`. **Missing:** no job is registered. The scheduler starts with an empty job list.

### 11.2 Required Addition to `main.py` Lifespan

```python
# In lifespan startup (analysis only):
from app.services.notification_service import run_notification_job
scheduler.add_job(
    run_notification_job,
    trigger="cron",
    hour=settings.notification_hour,
    minute=settings.notification_minute,
    id="daily_notification",
    replace_existing=True,
)
```

### 11.3 Notification Job Function

```python
# In notification_service.py (analysis only):
async def run_notification_job() -> None:
    """APScheduler entry point — must create and close its own DB session."""
    db = SessionLocal()
    try:
        gateway = get_provider_gateway()
        result = await invoke_notification_graph(db, gateway)
        logger.info(f"Notification job: {result.alerts_sent} alerts sent")
    except Exception as exc:
        logger.error(f"Notification job failed: {type(exc).__name__}: {exc}")
    finally:
        db.close()
```

### 11.4 Duplicate Alert Prevention

`Task.alert_sent` flag prevents duplicate emails:
- `check_deadline_tool`: queries `status=pending AND deadline<=tomorrow AND alert_sent=false`
- `mark_alert_sent_tool`: sets `alert_sent=true` immediately after successful send
- If server restarts between query and mark: task retried next day (acceptable for hackathon)

### 11.5 Per-Task Failure Isolation

Per AGENT_FLOW.md: Resend failure → retry once, log, **continue to next task**. Failed task IDs recorded in `NotificationOutput.failed_alerts`. Those tasks retain `alert_sent=false` and are retried in next job run.

### 11.6 Manual Trigger (Endpoint 20)

`POST /api/v1/notifications/trigger` invokes the same notification graph logic with `trigger="manual"`. Useful for testing without waiting for 08:00.

---

## 12. Error Handling Plan

### 12.1 Existing Infrastructure (Gate 2)

Complete exception hierarchy in `app/core/exceptions.py`. Global handler in `main.py` maps to HTTP status codes:

| Exception | HTTP Status |
|-----------|-------------|
| `EntityNotFoundError` subtypes | 404 |
| `DuplicateUserError` | 409 |
| `ProviderRateLimitError`, `AllKeysCooldownError` | 429 |
| `ProviderAuthError` | 502 |
| `ProviderNotConfiguredError`, `ProviderExhaustedError`, `ProviderKeyFailoverExhaustedError` | 503 |
| All other `MeetMindError` | 500 |

### 12.2 Gate 4 Exception Usage

| Scenario | Exception |
|----------|-----------|
| User not found | `UserNotFoundError` |
| Meeting not found | `MeetingNotFoundError` |
| Task not found | `TaskNotFoundError` |
| Duplicate email | `DuplicateUserError` |
| Graph/agent failure | `PipelineError` (or subtype) |
| Q&A failure | `QAError` |
| Email failure | `EmailDeliveryError` |
| Pinecone failure | `PineconeError` |
| Embedding failure | `EmbeddingError` |
| Notification failure | `NotificationError` |

### 12.3 Rules

- Routes do NOT wrap calls in try/except — let global handler catch `MeetMindError` subtypes
- FastAPI handles `ValidationError` → 422 automatically
- SQLAlchemy `IntegrityError` caught in services, re-raised as domain exception
- HITL interrupt is NOT an exception — detected via state inspection
- Error messages must never contain raw API key text, transcript content, or provider SDK error details

---

## 13. Configuration Plan

### 13.1 Current Settings Coverage

All required Gate 4 config already exists in `settings.py`:

| Config | Field | Default |
|--------|-------|---------|
| Database | `database_url` | Required |
| Resend key | `resend_api_key` | Required for notifications |
| Resend sender | `resend_sender` | `"onboarding@resend.dev"` |
| Pinecone key | `pinecone_api_key` | Required for RAG |
| Pinecone index | `pinecone_index_name` | `"hackathon-index"` |
| Scheduler hour | `notification_hour` | `8` |
| Scheduler minute | `notification_minute` | `0` |

### 13.2 Missing Configuration (Report Only)

| Missing | Impact | Open Decision |
|---------|--------|---------------|
| `CORS_ORIGINS` env var | Hardcoded in main.py, blocks production | OD-07 |
| `MAX_TRANSCRIPT_SIZE_BYTES` | No input size limit | OD-08 |
| `PIPELINE_TIMEOUT_SECONDS` | No LangGraph invocation timeout | Optional |

### 13.3 Configuration Compliance

- ✅ `settings.py` owns all env vars
- ✅ `config.py` owns all static values
- ✅ `constants.py` owns all enums
- ✅ No `os.environ` usage outside settings found
- ✅ No hardcoded credentials found

---

## 14. Security Analysis

### 14.1 IDOR Risk Matrix

| Endpoint | Risk | Required Mitigation |
|----------|------|---------------------|
| `GET /tasks/{user_id}/meeting/{meeting_id}` | User A passes meeting B's ID | Verify `Meeting.user_id == user_id` in service |
| `PUT /tasks/{task_id}/status` | User A updates User B's task | Verify `Task.user_id == request.user_id` |
| `GET /highlights/{user_id}/meeting/{meeting_id}` | Cross-meeting highlights | Verify meeting ownership |
| `GET /chat/{meeting_id}/history` | Read another user's chat | Verify `Meeting.user_id == request.user_id` |
| `POST /chat/{meeting_id}/message` | Q&A against another user's meeting | Verify meeting ownership before graph |
| `DELETE /meetings/{meeting_id}` | Delete another user's meeting | Verify `Meeting.user_id` before delete |

**Note:** No authentication in scope. All ownership checks rely on `user_id` in request body/path. This is an inherent limitation of the auth-free design — documented, not fixed.

### 14.2 Q&A Meeting Isolation

Two independent boundaries:
1. **Service layer:** `Meeting.user_id == request.user_id` — prevents graph invocation for wrong user
2. **RAG layer:** Pinecone namespace `meeting_{meeting_id}` — enforces vector isolation

Both must be present. The RAG boundary alone is insufficient (service must refuse the request before reaching RAG).

### 14.3 Transcript Leakage

`MeetingResponse` schema includes `raw_transcript`. This is intentional for the detail endpoint. `MeetingListItem` correctly omits it. The list endpoint must use `MeetingListItem`, not `MeetingResponse`.

### 14.4 Secret Leakage in Errors

Global exception handler returns `exc.message` and `exc.details` only. Services must not set these fields to raw provider error text. Wrap provider errors with sanitized messages before raising.

### 14.5 File Upload Scope

`MeetingCreate.raw_transcript` is a pre-parsed string (PDF/TXT parsed by Ingestion Agent). The raw binary is not stored. However, no maximum size is enforced. See OD-08.

### 14.6 SQL Injection

All queries use SQLAlchemy ORM with bound parameters. No raw SQL found in Gate 4 scope. Risk: low.

### 14.7 Scheduler Duplication

`add_job(..., id="daily_notification", replace_existing=True)` prevents duplicate registration on hot reload.

---

## 15. Performance Analysis

### 15.1 DB Session Lifecycle

`get_db()` provides one session per HTTP request, guaranteed cleanup in `finally`. Services must not create additional sessions within a request. Scheduler job creates its own session independently.

### 15.2 N+1 Risks

| Endpoint | Risk |
|----------|------|
| `GET /meetings/{user_id}` | Accessing `.participants` or `.tasks` per meeting = N queries |
| `GET /highlights/{user_id}` | Accessing `highlight.meeting` per highlight = N queries |

All relationships use `lazy="select"`. Services must use `joinedload()` or `subqueryload()` for list endpoints that include related data.

### 15.3 Graph Invocation Latency

Main pipeline (ingest → identify → extract → HITL) will take 15–60 seconds due to Gemini calls. `POST /meetings/` must NOT block synchronously. See Open Decision OD-09 (BackgroundTasks vs synchronous).

### 15.4 BGE Reranker Memory

`BAAI/bge-reranker-v2-m3` lazy-loaded on first Q&A request. On Render free tier (512MB RAM), this may cause memory pressure. The lazy-load pattern in `get_reranker()` (Gate 3) is already correct.

### 15.5 Scheduler Query

Daily notification query touches all tasks across all users. Composite index `ix_tasks_user_id_status_deadline` (Gate 1) supports this efficiently.

---

## 16. Dependency Analysis

### 16.1 All Required Packages Already in requirements.txt

| Package | Gate 4 Use |
|---------|-----------|
| `fastapi`, `uvicorn[standard]`, `python-multipart` | API server |
| `sqlalchemy>=2.0`, `psycopg2-binary` | ORM queries |
| `pydantic`, `pydantic-settings` | Schema validation, settings |
| `langgraph` | Graph compilation, HITL interrupt |
| `langchain`, `langchain-core`, `langchain-community` | Agent tooling, LCEL |
| `langchain-google-genai`, `langchain-openai` | Provider LLM clients |
| `langchain-pinecone` | Vector store integration |
| `google-generativeai` | Gemini embeddings |
| `openai` | OpenRouter via OpenAI client |
| `pinecone-client` | Pinecone index operations |
| `sentence-transformers` | BGE reranker |
| `rank-bm25` | BM25 lexical search |
| `pypdf` | PDF parsing tool |
| `resend` | Email delivery |
| `apscheduler` | AsyncIOScheduler |
| `loguru` | Structured logging |
| `httpx` | Async HTTP |

### 16.2 Conditionally Required (Not Yet Present)

| Package | Condition |
|---------|-----------|
| `langgraph-checkpoint-postgres` | Only if OD-05 resolves to PostgresSaver |
| `pytest`, `pytest-asyncio` | Test dependencies (dev only) |

### 16.3 Unused (Present, Not Required)

| Package | Note |
|---------|------|
| `python-jose` | No JWT/auth in this product — not to be used in Gate 4 |
| `python-docx` | No DOCX format in frozen features |

---

## 17. File-Scope Matrix

### 17.A Files Gate 4 Will Modify

| File | Change |
|------|--------|
| `app/api/router.py` | Add `include_router()` for all 7 domain routers |
| `app/main.py` | Add scheduler job registration in lifespan; add CORS_ORIGINS from env (OD-07) |

### 17.B Files Gate 4 Will Create / Fully Implement

All API routers, all services, all agents, all tools, graph.py, graph router.py, and test files — see full list in Section 18 (Batch plans).

### 17.C Files That Must Remain Untouched

| Protected File/Dir | Gate Owner |
|-------------------|-----------|
| `app/db/models/*.py` | Gate 1 |
| `app/db/base.py`, `app/db/session.py` | Gate 1 |
| `alembic/versions/653117d884bd_*.py` | Gate 1 |
| `alembic/env.py` | Gate 1 |
| `app/core/settings.py` | Gate 2 |
| `app/core/config.py` | Gate 2 |
| `app/core/constants.py` | Gate 2 |
| `app/core/exceptions.py` | Gate 2 |
| `app/core/logging.py` | Gate 2 |
| `app/core/providers/*.py` | Gate 2 |
| `app/rag/chunker.py` | Gate 3 |
| `app/rag/embedder.py` | Gate 3 |
| `app/rag/reranker.py` | Gate 3 |
| `app/rag/retriever.py` | Gate 3 |
| `app/rag/__init__.py` | Gate 3 |
| `app/schemas/*.py` | Gate 3 (corrections OD-01/OD-02 are schema-level fixes, not modifications) |
| `app/graph/state.py` | Gate 3 |
| `backend/tests/test_chunker.py` | Gate 3 |
| `backend/tests/test_embedder.py` | Gate 3 |
| `backend/tests/test_retriever.py` | Gate 3 |

---

## 18. Four-Batch Implementation Plan

---

### BATCH 1 — Backend Service Layer

**Objective:** Implement all 7 service modules with full business logic, ORM queries, and domain exception usage. No API, no graph.

**Files to Create:**
- `app/services/user_service.py`
- `app/services/meeting_service.py`
- `app/services/task_service.py`
- `app/services/highlight_service.py`
- `app/services/chat_service.py` (DB-only: history, clear, persist_message)
- `app/services/notification_service.py` (DB-only: get_pending_alerts)
- `backend/tests/test_services.py`

**Existing Dependencies:** Gate 1 session + models, Gate 2 exceptions + constants

**Implementation Responsibilities:**
- `user_service`: create (duplicate check), get, update
- `meeting_service`: create (placeholder title + participant creation), list (ordered), detail (load participants), delete (ownership check + cascade)
- `task_service`: list_user, list_meeting (ownership check), status_toggle (preserve alert_sent), filter (dynamic AND, case() sort)
- `highlight_service`: get_meeting (ownership check), get_user
- `chat_service`: get_history, clear_history, persist_message (both roles)
- `notification_service`: get_pending_alerts (correct 3-way filter)

**Tests:** Unit tests with test DB; all exception paths; meeting ownership checks; task filter combinations.

**Out of Scope:** Graph invocation, Pydantic serialization, HTTP status codes.

**Acceptance Criteria:** All services pass unit tests; `create_user` raises DuplicateUserError; task filter returns correct subset; meeting creates participant with is_current_user=True.

**Risks:** TaskStatus enum inconsistency (OD-02) must be resolved before writing task_service.

---

### BATCH 2 — FastAPI API Layer

**Objective:** Implement all 7 router modules. Wire into `api/router.py`. No agent/graph calls.

**Files to Create:**
- `app/api/users.py` (3 endpoints)
- `app/api/meetings.py` (4 endpoints; POST returns 202 + meeting_id)
- `app/api/tasks.py` (4 endpoints)
- `app/api/chat.py` (history + clear only; Q&A stub returns 501)
- `app/api/extraction.py` (all 3 as stubs returning 501 until Batch 3)
- `app/api/highlights.py` (2 endpoints)
- `app/api/notifications.py` (pending only; trigger stub returns 501)
- `backend/tests/test_api.py`

**Files to Modify:**
- `app/api/router.py` → include all 7 sub-routers

**Implementation Responsibilities:**
- Each route: parse → call service → serialize response
- `POST /users/register` → 201; `DELETE /meetings/{meeting_id}` → 204
- `GET /tasks/{user_id}/filter` → query params via `Depends(TaskFilterParams)`
- Path registration order: detail/filter paths before generic `{user_id}` paths (OD-03)
- Inject `db: Session = Depends(get_db)` on all routes; `Request` where gateway needed

**Tests:** FastAPI TestClient; all 21 endpoints; 422 validation errors; mock service layer.

**Dependencies on Batch 1:** All service modules must be implemented.

**Acceptance Criteria:** All 21 endpoints match correct routes; correct status codes; Pydantic validation enforced; no logic inside route functions.

---

### BATCH 3 — Pipeline + Background Infrastructure

**Objective:** Implement all 7 agents, all 24 tools, LangGraph graph, graph router, full pipeline invocation in services, scheduler job.

**Files to Create:** All agent files, all tool files, `graph/graph.py`, `graph/router.py`

**Files to Modify:**
- `app/services/meeting_service.py` → add pipeline trigger via BackgroundTasks
- `app/services/chat_service.py` → implement Q&A graph invocation
- `app/services/extraction_service.py` → implement run/preview/confirm
- `app/services/notification_service.py` → add trigger() and run_notification_job()
- `app/api/chat.py` → implement Q&A endpoint
- `app/api/extraction.py` → implement all 3 endpoints
- `app/api/notifications.py` → implement trigger endpoint
- `app/main.py` → add scheduler.add_job() in lifespan
- `backend/tests/test_graph.py`, `tests/test_scheduler.py`

**Critical implementation rules:**
- Each agent: one file, one factory function, `gateway.execute(use_case, ...)` only
- Each tool: one file, one `@tool` decorated function
- DB session injection into tools: via `contextvars.ContextVar` (OD-10 recommended)
- `embed_and_store_tool` delegates to `TranscriptEmbedder` (Gate 3)
- `hybrid_search_tool` delegates to `retrieve()` (Gate 3)
- `rerank_tool` delegates to `get_reranker()` (Gate 3)

**Tests:** Graph compilation; HITL pause/resume cycle; Q&A graph returns answer+sources; notification processes correct tasks; scheduler registers one job.

**Risks:** Longest batch; agent implementation quality is critical; DB session injection pattern (OD-10) must be decided upfront.

---

### BATCH 4 — Backend Integration + Hardening

**Objective:** End-to-end integration testing, security hardening, regression verification.

**Files to Create:**
- `tests/test_integration.py`
- `tests/test_security.py`
- `tests/conftest.py` (if not already created)

**Files to Modify:**
- `app/main.py` → CORS from env (OD-07)
- `app/schemas/task.py` → fix TaskStatus enum reference (OD-02)
- Optionally: transcript size limit (OD-08)

**Responsibilities:**
- Full pipeline cycle: POST /meetings/ → pipeline → HITL → confirm → GET /tasks
- Meeting isolation: Q&A for meeting A cannot retrieve chunks from meeting B
- IDOR: user A cannot update user B's task
- alert_sent not reset on status toggle
- Scheduler: single job, no duplicates
- Regression: Gate 3 tests (`test_chunker`, `test_embedder`, `test_retriever`) pass

**Acceptance Criteria:** All 44 G4-AC criteria pass; Gate 3 tests pass; no secrets in error responses; CORS allows configured origins.

---

## 19. Proposed G4 Acceptance Criteria

| ID | Criterion | Scope |
|----|-----------|-------|
| G4-AC-01 | POST /users/register with valid payload returns 201 + UserResponse with UUID | API |
| G4-AC-02 | POST /users/register with duplicate email returns 409 with DuplicateUserError JSON | API |
| G4-AC-03 | GET /users/{user_id} with valid UUID returns UserResponse | API |
| G4-AC-04 | GET /users/{user_id} with non-existent UUID returns 404 | API |
| G4-AC-05 | POST /meetings/ creates Meeting + MeetingParticipant (is_current_user=True) | Service |
| G4-AC-06 | POST /meetings/ with nonexistent user_id returns 404 | API |
| G4-AC-07 | GET /meetings/{user_id} returns list ordered by created_at DESC, no raw_transcript | API |
| G4-AC-08 | GET /meetings/{meeting_id}/detail returns MeetingDetail with participants list | API |
| G4-AC-09 | DELETE /meetings/{meeting_id} returns 204; cascade deletes tasks, highlights, chat | Service |
| G4-AC-10 | GET /tasks/{user_id} returns all tasks, ordered by deadline ASC NULLS LAST, priority | API |
| G4-AC-11 | GET /tasks/{user_id}/meeting/{meeting_id} returns only that meeting's tasks for user | Service |
| G4-AC-12 | GET /tasks/{user_id}/meeting/{meeting_id} returns 404 if meeting belongs to other user | Security |
| G4-AC-13 | PUT /tasks/{task_id}/status updates status; alert_sent is NOT reset | Service |
| G4-AC-14 | PUT /tasks/{task_id}/status for task owned by other user returns 404 | Security |
| G4-AC-15 | GET /tasks/{user_id}/filter with priority=high returns only high tasks | Service |
| G4-AC-16 | GET /tasks/{user_id}/filter with deadline_before returns tasks ≤ that date | Service |
| G4-AC-17 | POST /chat/{meeting_id}/message invokes Q&A graph, persists user + assistant messages | Service |
| G4-AC-18 | POST /chat/{meeting_id}/message returns 404 for meeting not owned by user | Security |
| G4-AC-19 | Q&A retrieval uses Pinecone namespace meeting_{meeting_id} only; no cross-meeting chunks | Security |
| G4-AC-20 | GET /chat/{meeting_id}/history returns messages ordered by created_at ASC | API |
| G4-AC-21 | DELETE /chat/{meeting_id}/history returns 204; all messages for meeting+user deleted | API |
| G4-AC-22 | POST /extraction/{meeting_id}/run triggers pipeline; returns awaiting_confirmation state | Pipeline |
| G4-AC-23 | GET /extraction/{meeting_id}/preview returns ExtractionPreviewResponse from graph state | Pipeline |
| G4-AC-24 | POST /extraction/{meeting_id}/confirm with yes saves all tasks | HITL |
| G4-AC-25 | POST /extraction/{meeting_id}/confirm with no saves zero tasks | HITL |
| G4-AC-26 | POST /extraction/{meeting_id}/confirm with partial saves only confirmed_task_ids | HITL |
| G4-AC-27 | GET /highlights/{user_id}/meeting/{meeting_id} returns highlights for user + meeting only | Service |
| G4-AC-28 | GET /highlights/{user_id} returns highlights across all meetings for user | Service |
| G4-AC-29 | POST /notifications/trigger invokes Notification Agent, returns NotificationStatusResponse | Pipeline |
| G4-AC-30 | GET /notifications/{user_id}/pending returns tasks matching 3-way filter correctly | Service |
| G4-AC-31 | APScheduler registers exactly one daily_notification job with replace_existing=True | Scheduler |
| G4-AC-32 | APScheduler fires at notification_hour:notification_minute from settings | Scheduler |
| G4-AC-33 | Notification job creates own SessionLocal() and closes in finally | Scheduler |
| G4-AC-34 | After email sent, Task.alert_sent=True; task not processed in next run | Scheduler |
| G4-AC-35 | Resend failure for one task does not halt processing of remaining tasks | Scheduler |
| G4-AC-36 | All agent/tool AI calls use gateway.execute() — no raw API key access anywhere | Security |
| G4-AC-37 | Error responses never include raw provider text, API keys, or transcript content | Security |
| G4-AC-38 | Invalid UUID path param returns 422 with Pydantic error detail | API |
| G4-AC-39 | All MeetMindError subtypes map to correct HTTP status codes via global handler | Error |
| G4-AC-40 | DB session is always closed after request (verified via finally in get_db) | DB |
| G4-AC-41 | Gate 3 tests (test_chunker, test_embedder, test_retriever) pass after Gate 4 | Regression |
| G4-AC-42 | No Base.metadata.create_all() in any production code path | DB |
| G4-AC-43 | GET /meetings/{user_id} response items do not include raw_transcript | Security |
| G4-AC-44 | CORS middleware allows configured production origin from settings/env | Config |

---

## 20. Test Strategy

### 20.1 Test Structure

```
backend/tests/
├── __init__.py
├── conftest.py              # fixtures: test DB, mock gateway, TestClient
├── test_chunker.py          # Gate 3 — frozen, must pass
├── test_embedder.py         # Gate 3 — frozen, must pass
├── test_retriever.py        # Gate 3 — frozen, must pass
├── test_services.py         # Batch 1 — service unit tests
├── test_api.py              # Batch 2 — API route tests
├── test_graph.py            # Batch 3 — graph + HITL tests
├── test_scheduler.py        # Batch 3 — scheduler tests
├── test_integration.py      # Batch 4 — full pipeline tests
└── test_security.py         # Batch 4 — IDOR + isolation tests
```

### 20.2 Mocking Strategy

| External Service | Mock |
|-----------------|------|
| Gemini API | Mock `gateway.execute()` → return fixture data |
| Pinecone | Mock `PineconeVectorStore.get_index()` |
| BGE Reranker | Identity reranker (returns input order) |
| Resend | Mock `resend.Emails.send()` |
| APScheduler | No actual scheduling in tests |

### 20.3 Key Test Cases

**Service:** user duplicate; meeting create (participant check); task filter combinations; chat history order; notification 3-way filter

**API:** all 21 status codes; path ordering (filter/detail before generic); 422 validation; 404 not found

**Graph/HITL:** graph compiles; pipeline reaches interrupt; yes/no/partial resume paths; Q&A returns answer+sources

**Scheduler:** one job registered; failure isolation per task; SessionLocal pattern

**Security:** IDOR attempts return 404; Q&A meeting isolation; error responses clean of secrets

---

## 21. Open Decisions

### OD-01 — Meeting Title Placeholder

**Question:** What placeholder title on `Meeting` creation before Ingestion Agent extracts real title?

**Options:**
1. `"Processing..."` — explicit pending state
2. `"Untitled Meeting"` — generic
3. Derived: `f"Meeting — {org} — {meeting_date}"` — meaningful before agent runs

**Recommended:** Option 3 — most useful to user before pipeline completes.

**Consequence:** Without resolution, first `INSERT` fails with NOT NULL violation.

---

### OD-02 — TaskStatus Enum Case

**Question:** `schemas/task.py` uses `TaskStatus.PENDING` (core.constants, uppercase). `db/models/task.py` uses `TaskStatus.pending` (lowercase). Services bridge both.

**Options:**
1. Use `db/models/task.py.TaskStatus` as canonical in services; use `.value` for comparisons (recommended)
2. Normalize all imports to `core.constants.TaskStatus` and use `.value` for DB writes

**Recommended:** Option 1 — minimizes changes to frozen schema files.

**Consequence:** Services must explicitly use `.value` (lowercase string) when writing to PostgreSQL enum columns.

---

### OD-03 — FastAPI Path Ordering

**Question:** `/meetings/{meeting_id}/detail` vs `/meetings/{user_id}` — both use UUID path params.

**Options:**
1. Register longer/more-specific paths first in router (recommended by FastAPI docs)
2. Rename to avoid ambiguity: `/meetings/by-user/{user_id}` vs `/meetings/{meeting_id}/detail`

**Recommended:** Option 1 — no breaking change to frozen API contract.

**Consequence:** Must be enforced in router registration order. Must be tested explicitly.

---

### OD-04 — ChatRequest Identity Context

**Question:** `ChatRequest` has only `question` and `user_id`. Q&A Agent needs `user_name` and `user_role`.

**Options:**
1. Chat service looks up from `meeting_participants` before graph invocation (recommended)
2. Add fields to `ChatRequest` schema (frontend must pass them)

**Recommended:** Option 1 — keeps API surface clean; DB lookup is cheap.

**Consequence:** Every Q&A call incurs one extra DB query for participant lookup.

---

### OD-05 — LangGraph Checkpointer

**Question:** `MemorySaver` (simple, lost on restart) vs `PostgresSaver` (persistent, adds dependency)?

**Options:**
1. `MemorySaver` — hackathon simplicity; HITL state lost on restart
2. `PostgresSaver` (langgraph-checkpoint-postgres) — survives restarts; adds migration tables

**Recommended:** Option 1 for hackathon scope. Document the restart limitation.

**Consequence:** If server restarts between pipeline run and user confirmation, user must re-run pipeline.

---

### OD-06 — Task Priority Sort in SQL

**Question:** How to sort tasks high→medium→low using SQLAlchemy?

**Options:**
1. SQLAlchemy `case()` expression mapping enum values to integers (recommended)
2. Python-level sort after DB query

**Recommended:** Option 1 — correct sort at DB level.

**Consequence:** Minor implementation complexity; must be applied in list_user_tasks and filter_tasks.

---

### OD-07 — CORS Origins from Environment

**Question:** `main.py` hardcodes `localhost:8501/3000`. Production Vercel URL not included.

**Options:**
1. Add `cors_origins: list[str]` field to `settings.py`; update `main.py` to use it (recommended)
2. Set `allow_origins=["*"]` for hackathon

**Recommended:** Option 1 — proper security boundary.

**Consequence:** Without this, frontend calls fail with CORS error in production.

---

### OD-08 — Maximum Transcript Size

**Question:** Should `raw_transcript` have a size limit?

**Options:**
1. Add FastAPI body size middleware (recommended — no schema change)
2. Add `max_length` to schema field (requires schema modification)
3. No limit for hackathon

**Recommended:** Option 1 — 1MB body size limit via middleware.

**Consequence:** Pathological transcripts rejected at HTTP layer with 413.

---

### OD-09 — Pipeline Invocation Latency Strategy

**Question:** How to handle 15–60s pipeline execution on `POST /meetings/`?

**Options:**
1. Return 202 immediately; trigger pipeline via `BackgroundTasks`; frontend polls `/extraction/{id}/preview` (recommended)
2. Block synchronously until HITL pause (may HTTP timeout)
3. WebSocket streaming (out of scope)

**Recommended:** Option 1 — `POST /meetings/` saves to DB, returns 202 with meeting_id. Explicit `POST /extraction/{meeting_id}/run` triggers the graph when frontend is ready.

**Consequence:** Frontend must implement a poll loop or display "Processing" status after meeting creation.

---

### OD-10 — DB Session Injection into Tools

**Question:** How do tools that write to DB receive the session?

**Options:**
1. `contextvars.ContextVar` — set before graph invocation; tools read from context (recommended)
2. Tool input schema includes `db_session` field — explicit but complex
3. Each tool creates own `SessionLocal()` — anti-pattern, session proliferation

**Recommended:** Option 1 — cleanest tool signatures; session injected at graph invocation point.

**Consequence:** Tools must import and use the context variable. Graph invocation code must set context before `invoke()`.

---

## 22. Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| TaskStatus enum inconsistency causes ORM write failures | High | High | Resolve OD-02 before Batch 1 |
| Meeting title NOT NULL violation on first INSERT | High | High | Resolve OD-01 before Batch 1 |
| FastAPI path ambiguity makes endpoints unreachable | Medium | High | Resolve OD-03; test path ordering in Batch 2 |
| LangGraph graph fails to compile due to agent gaps | High | High | Implement stub nodes first; add real agents progressively |
| MemorySaver state lost on restart during HITL | Medium | Medium | Document limitation; user re-runs pipeline |
| BGE reranker OOM on Render 512MB free tier | Medium | High | Lazy load (Gate 3 already correct); monitor |
| Long pipeline HTTP timeout | High | Medium | Resolve OD-09 (BackgroundTasks pattern) |
| CORS blocks Vercel frontend | High | High | Resolve OD-07 before first deployment |
| DB session leak in scheduler job | Low | Medium | Guaranteed by SessionLocal + finally pattern |
| Agent output diverges from state schema contracts | Medium | High | Pin each agent's output to MeetMindState fields during implementation |

---

## 23. Out-of-Scope Verification

| Excluded | Verified |
|----------|----------|
| User authentication / JWT | Not in any schema or route |
| Real-time meeting recording | Not referenced |
| Multi-user team dashboard | All queries scoped to single user_id |
| Cross-meeting Q&A | Pinecone namespace isolation enforced |
| Mobile push notifications | Not referenced |
| Task analytics / charts | Not in endpoint inventory |
| New Alembic migration | No new tables required |
| `Base.metadata.create_all()` | Not present in any file |
| Second exception system | Using only existing hierarchy |
| Weighted fusion / RRF in RAG | Gate 3 uses simple merge+dedup |

---

## 24. Final Readiness Verdict

### Assessment Summary

| Domain | Ready |
|--------|-------|
| 21 API endpoints recoverable from source | Yes |
| All schemas complete | Yes (2 minor fixes needed) |
| Service boundaries fully defined | Yes |
| DB session lifecycle understood | Yes |
| LangGraph entry points and state understood | Yes |
| HITL interrupt/resume pattern understood | Yes |
| Q&A meeting isolation understood | Yes |
| Scheduler skeleton exists; job registration understood | Yes |
| Error handling infrastructure ready | Yes |
| ProviderGateway boundary understood | Yes |
| Security risks identified with mitigations | Yes |
| No unresolved architecture contradictions | Yes |
| Gate 1/2/3 interfaces compatible | Yes |
| Open decisions (10): all actionable, none blocking architecture | Yes |

### Required Corrections Before Batch 1

| Decision | Action |
|----------|--------|
| OD-01 | Decide placeholder title strategy |
| OD-02 | Normalize TaskStatus enum usage in services |
| OD-03 | Decide FastAPI path ordering strategy |
| OD-05 | Decide LangGraph checkpointer before Batch 3 |
| OD-07 | Add CORS_ORIGINS to settings before deployment |

---

```
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   PASS WITH CORRECTIONS                                      ║
║   GATE 4 REQUIRES SPECIFIC DECISIONS/FIXES                   ║
║                                                              ║
║   5 critical decisions required before implementation:       ║
║   • OD-01: Meeting title placeholder strategy                ║
║   • OD-02: TaskStatus enum case resolution                   ║
║   • OD-03: FastAPI path ordering strategy                    ║
║   • OD-05: LangGraph checkpointer selection                  ║
║   • OD-07: CORS origins from environment                     ║
║                                                              ║
║   All corrections are within Gate 4 scope.                   ║
║   No frozen architecture redesign required.                  ║
║   Gate 4 is ready to implement after owner review.           ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
```
