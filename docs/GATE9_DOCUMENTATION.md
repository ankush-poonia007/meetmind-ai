# GATE 9 — BACKEND QA INTELLIGENCE & STABILITY FIX
# Branch: gate/backend-fix-qa
# Status: Pre-implementation documentation

---

## OVERVIEW

The backend is working. The pipeline runs. Agents execute. Data is stored correctly.
The problems are specific and contained to the Q&A layer only.
This gate makes zero schema changes, zero new tables, zero new dependencies beyond what is already installed.
Every change is a targeted fix inside existing files. Nothing else is touched.

---

## ISSUE REGISTER — FULL DIAGNOSIS

---

### ISSUE 1 — New HybridRetriever instance created on every Q&A request
**Severity:** Critical — directly causes slow response times
**File:** `backend/app/rag/retriever.py`
**Line:** 364

**What exists:**
```python
def retrieve(meeting_id, query, db_session=None):
    retriever = HybridRetriever()   # ← new instance every single call
    return retriever.retrieve(...)
```

**Why this is a problem:**
Every time a user sends a message in the chat, this convenience function creates a brand new `HybridRetriever()`. Inside `HybridRetriever.__init__()`, three objects are instantiated fresh:
- `GeminiEmbedder()` — new embedder client
- `PineconeVectorStore()` — new Pinecone client connection
- `get_reranker()` — this one correctly returns a singleton BUT the BGE model lazy-loads on first use inside it

The Pinecone client and Gemini embedder initialization are not free operations. They involve connection setup and authentication. Creating them per-request adds unnecessary overhead on every question.

**Why it exists:**
The convenience wrapper was written for simplicity during Gate 3. It works correctly but is not optimized for repeated use.

**The fix:**
Create a module-level singleton `HybridRetriever` instance. The `get_reranker()` singleton already exists and works — the same pattern applied to the whole `HybridRetriever`.

**What changes:**
Add `_GLOBAL_RETRIEVER` singleton at the bottom of `retriever.py`, exactly matching the pattern already used for `_GLOBAL_RERANKER` in `reranker.py`. The `retrieve()` convenience function uses this singleton instead of creating a new instance.

**Risk:** Zero. The singleton holds no request-specific state. `meeting_id` and `query` are passed as arguments on each call.

---

### ISSUE 2 — QA Agent has no access to the raw transcript
**Severity:** Critical — directly causes "not mentioned" answers for questions whose answers exist in the transcript
**File:** `backend/app/agents/qa.py`

**What exists:**
The QA agent receives only the top 5 reranked chunks from RAG retrieval. If a relevant passage scores low in both semantic and BM25 retrieval, it never reaches the agent. The agent then correctly states it cannot find the answer — because it genuinely cannot see it.

**Concrete example from your screenshots:**
- Question: "what about the date October 5"
- Transcript contains: `[11:12] Aryan: Dev - documentation structure by September 26, decisions log maintained going forward, daily sync with Priya from September 27, progress report template by October 5.`
- Why RAG missed it: "October 5" appears as part of a longer task description sentence. The semantic embedding of this chunk is dominated by "documentation structure", "decisions log", "daily sync" — not "October 5". BM25 finds "october" and "5" but this chunk ranks below other chunks that mention "october" more prominently.
- Result: The chunk doesn't make it into top 5. Agent says not found.

**Another example:**
- Question: "on which date is the soft deadline for free libraries"
- Transcript contains: `[11:00] Aryan: Use free libraries for now. Recommend a few options and I will approve one by September 26. This is a soft deadline but try to finalize it early.`
- Why RAG missed it: "soft deadline" appears once. "free libraries" appears once. The semantic match to "soft deadline for free libraries" is weak because the transcript phrasing is "This is a soft deadline" — separated by several words from "free libraries". BM25 finds "soft", "deadline", "free", "libraries" but the chunk ranks below others that contain more of the query terms in closer proximity.

**Why this exists:**
The Gate 3 RAG design was optimized for specific factual retrieval. It was not designed with a fallback for when retrieval quality is insufficient. This is a known limitation of pure RAG systems — retrieval can fail even when the answer is in the document.

**The fix:**
Two-path approach inside the QA agent:

Path A (existing) — RAG path:
Run hybrid retrieval as before. If top rerank score is above threshold (0.3) → use chunks only.

Path B (new) — Transcript fallback path:
If top rerank score is below 0.3 OR question contains temporal/identity/decision keywords ("when", "which date", "what date", "who", "role of", "what did", "decision", "decided", "deadline", "october", "september", "november", month names) → fetch `meeting.raw_transcript` from PostgreSQL and include it alongside the retrieved chunks as additional context.

The raw transcript is already stored in `meetings.raw_transcript` (TEXT column). It is already fetched in `chat_service.py` as the `meeting` object. It just needs to be passed through to the QA agent.

**What changes:**
- `backend/app/services/chat_service.py` — pass `meeting.raw_transcript` to `_invoke_qa_pipeline`
- `backend/app/agents/qa.py` — accept `raw_transcript` parameter, implement two-path logic, update prompt

**Risk:** Low. The raw transcript is read-only. It is only used as additional prompt context. It does not change any stored data. The existing RAG path runs first and is unchanged.

---

### ISSUE 3 — Chat history not used in QA context
**Severity:** Medium — causes follow-up questions to fail
**File:** `backend/app/agents/qa.py`

**What exists:**
Every question is answered in complete isolation. The agent has no memory of what was just asked or answered. If a user asks "what was Sneha's task?" and then asks "and when is it due?" — the second question has no context about Sneha or her task.

**Why this exists:**
Chat history is stored correctly in the `chat_messages` table but was never wired into the QA prompt. The `get_chat_history` function exists in `chat_service.py` but is only used for the history display endpoint, not for the QA pipeline.

**The fix:**
Before invoking the QA agent, fetch the last 5 messages from `chat_messages` for this meeting and user, and pass them as conversation history to the QA agent. Include them in the prompt as a "Recent conversation" block.

**What changes:**
- `backend/app/services/chat_service.py` — fetch last 5 chat messages before calling pipeline, pass to agent
- `backend/app/agents/qa.py` — accept `chat_history` parameter, include in prompt

**Risk:** Zero. Read-only operation on already stored data. Only affects prompt construction.

---

### ISSUE 4 — QA prompt is too restrictive
**Severity:** Medium — causes correct rejections even when answer is available
**File:** `backend/app/agents/qa.py`

**What exists:**
```python
prompt = """Answer the user's question based ONLY on the provided meeting excerpts.
If the answer is not contained in the excerpts, state clearly that it is not discussed."""
```

**Why this is a problem:**
"ONLY on the provided meeting excerpts" combined with top 5 chunks means the model will correctly refuse to answer anything not in those 5 chunks — even if the answer would be obvious from context. The model is doing exactly what it was told. The instruction is too narrow for a prototype demo.

**The fix:**
When raw transcript is included as fallback context, the prompt changes to acknowledge both sources. When only RAG chunks are available, the prompt stays similar but is slightly less aggressive about refusing — it should say "based primarily on" rather than "ONLY on".

**What changes:**
- `backend/app/agents/qa.py` — two prompt templates: one for RAG-only, one for RAG + transcript fallback

**Risk:** Zero. Prompt change only.

---

### ISSUE 5 — CORS missing Vite port 5173
**Severity:** High in production, medium in development (may be working via proxy)
**File:** `backend/app/main.py`

**What exists:**
```python
allow_origins=[
    "http://localhost:8501",   # Streamlit — no longer used
    "http://127.0.0.1:8501",   # Streamlit — no longer used
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
```

**Why this is a problem:**
Your React/Vite frontend runs on port 5173 by default. If direct API calls are made from the browser (not through the Vite proxy), they will be blocked by CORS. For the hosted version on Vercel, the actual Vercel domain must also be in this list.

**Why it exists:**
CORS list was set up during early development when Streamlit was the frontend. It was never updated for Vite.

**The fix:**
Add port 5173 and the Vercel production domain. Also remove the Streamlit entries since they are no longer needed.

**What changes:**
- `backend/app/main.py` — update `allow_origins` list

**Risk:** Zero. Adding origins to CORS never breaks anything.

---

### ISSUE 6 — No timeout on Gemini API calls in QA agent
**Severity:** Medium — causes indefinite hanging on slow API responses
**File:** `backend/app/agents/qa.py`

**What exists:**
```python
resp = model.generate_content(prompt)
```

No timeout. If Gemini is slow or rate-limited, this call hangs until the connection times out at the OS level — which can be minutes.

**Why this exists:**
Standard SDK usage. Timeouts are rarely added in prototype code.

**The fix:**
Wrap the Gemini call with a Python threading timeout or use the SDK's built-in request options. The `google.generativeai` SDK accepts `request_options` with a timeout parameter.

```python
resp = model.generate_content(
    prompt,
    request_options={"timeout": 25}
)
```

**What changes:**
- `backend/app/agents/qa.py` — add timeout to `generate_content` call

**Risk:** Zero. Adds a 25 second ceiling. If exceeded, falls through to the existing extractive fallback.

---

### ISSUE 7 — Top-K values are too conservative
**Severity:** Medium — limits answer quality for broad questions
**File:** `backend/app/core/config.py`

**What exists:**
- `PINECONE_TOP_K = 10` — retrieve top 10 semantic
- `BM25_TOP_K = 10` — retrieve top 10 lexical
- `RERANKER_TOP_K = 5` — keep top 5 after reranking

**Why this is a problem:**
For broad questions like "what are all the important decisions in this meeting" — 5 chunks from a 100+ line transcript is not enough. Important decisions can be spread across the entire transcript. The reranker picks the 5 most relevant but misses others that are also relevant.

**The fix:**
- `PINECONE_TOP_K`: 10 → 15
- `BM25_TOP_K`: 10 → 15
- `RERANKER_TOP_K`: 5 → 8

More candidates into the reranker → better selection → more comprehensive answers.

**What changes:**
- `backend/app/core/config.py` — update three constants

**Risk:** Minimal. Slightly more tokens in the prompt. The transcript fallback already handles cases where even 8 chunks aren't enough.

---

## BATCH PLAN

---

### BATCH 1 — Performance + CORS + Timeout
**Goal:** Fix the slow response and CORS issues. No intelligence changes.
**Files changed:** `retriever.py`, `main.py`, `config.py`, `qa.py` (timeout only)
**Risk:** Zero — no logic changes, only structural improvements
**Expected result:** QA response time drops significantly. CORS fixed for Vite.

Changes:
1. `retriever.py` — singleton HybridRetriever
2. `main.py` — CORS origins updated
3. `config.py` — top_k values increased
4. `qa.py` — 25s timeout on Gemini call

---

### BATCH 2 — QA Intelligence
**Goal:** Fix "not found" answers by adding transcript fallback and chat history context.
**Files changed:** `qa.py`, `chat_service.py`
**Risk:** Low — read-only additions to existing pipeline
**Expected result:** Date questions, role questions, decision questions answered correctly.

Changes:
1. `chat_service.py` — pass `raw_transcript` and last 5 `chat_history` messages to QA pipeline
2. `qa.py` — two-path logic (RAG path + transcript fallback path), updated prompts, chat history in context

---

### BATCH 3 — Final Code Review
**Goal:** Read all modified files end to end. Verify no regressions. Verify LangSmith traces are clean.
**Files reviewed:** All 5 modified files + `graph.py` to verify QA node wiring
**No code changes unless a bug is found during review.**

Review checklist:
- Singleton retriever used correctly, no thread safety issues
- CORS origins correct for both local and Vercel
- Transcript fallback only triggers when needed, not on every query
- Chat history fetch is scoped to correct meeting_id and user_id
- Prompt templates are clean, no formatting issues
- Timeout applied correctly, fallback path still works
- Top-K values consistent across config and retriever
- LangSmith trace shows QA node completing in under 10 seconds
- No import errors introduced
- All existing tests still pass

---

## FILES CHANGED SUMMARY

| File | Batch | Change Type | Risk |
|------|-------|-------------|------|
| `backend/app/rag/retriever.py` | 1 | Singleton pattern | Zero |
| `backend/app/main.py` | 1 | CORS origins | Zero |
| `backend/app/core/config.py` | 1 | Constants only | Zero |
| `backend/app/agents/qa.py` | 1+2 | Timeout + fallback logic | Low |
| `backend/app/services/chat_service.py` | 2 | Pass additional context | Low |

**Files NOT touched:**
- `graph.py` — no changes
- `state.py` — no changes
- `reranker.py` — already correct, no changes
- `embedder.py` — no changes
- `chunker.py` — no changes
- `settings.py` — no changes
- All API route files — no changes
- All DB model files — no changes
- All schema files — no changes
- All migration files — no changes

---

## WHAT THIS DOES NOT FIX

- Extraction agent taking 154 seconds (seen in LangSmith) — that is the ingestion pipeline, not QA. Separate concern, not blocking demo.
- Notification agent — working correctly per LangSmith traces (1.6-1.7s). No changes needed.
- Any frontend issues — Gate 9 is backend only.
