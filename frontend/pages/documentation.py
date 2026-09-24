"""
MeetMind AI — Documentation Page.

Provides an overview of the system architecture, agent pipeline,
API endpoints, and database schema for reference.
Draws content from the existing project documentation.
"""

import streamlit as st

from components.layout import render_footer, render_page_header, render_section_divider


def render_documentation_page() -> None:
    """Renders the documentation page with architecture and feature reference."""

    render_page_header(
        "Documentation",
        subtitle="System architecture, agent pipeline, and API reference",
        icon="📖",
    )

    # ── Architecture Overview ────────────────────────────────────────────
    tab_arch, tab_pipeline, tab_api, tab_agents = st.tabs([
        "🏗️  Architecture",
        "⚙️  Pipeline",
        "🔌  API Reference",
        "🤖  Agent Roster",
    ])

    with tab_arch:
        _render_architecture_tab()

    with tab_pipeline:
        _render_pipeline_tab()

    with tab_api:
        _render_api_tab()

    with tab_agents:
        _render_agents_tab()

    render_footer()


def _render_architecture_tab() -> None:
    """Renders the system architecture overview."""

    st.markdown(
        """
        <div class="doc-section">
            <h4>🏗️ System Architecture</h4>
            <p style="color:#94A3B8; line-height:1.6;">
                MeetMind AI is a full-stack agentic meeting intelligence application.
                The frontend is built with <strong>Streamlit</strong>, communicating with a
                <strong>FastAPI</strong> backend that orchestrates a 7-agent
                <strong>LangGraph</strong> pipeline. Data is stored in <strong>PostgreSQL</strong>
                (relational) and <strong>Pinecone</strong> (vector), with hybrid RAG retrieval
                powered by dense embeddings + BM25 keyword search + BGE cross-encoder reranking.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("#### Technology Stack")

    tech_data = {
        "Component": [
            "Frontend", "Backend", "Database", "Vector DB", "Orchestrator",
            "LLM (Primary)", "LLM (Sub-agents)", "Embeddings", "Reranker",
            "Email Service", "Scheduler",
        ],
        "Technology": [
            "Streamlit", "FastAPI + Uvicorn", "PostgreSQL (Supabase/Render)",
            "Pinecone", "LangGraph", "Gemini 3.6 Flash", "Gemini 3.5 Flash Lite",
            "gemini-embedding-001 (3072-dim)", "BAAI/bge-reranker-v2-m3 (local)",
            "Resend", "APScheduler (AsyncIOScheduler)",
        ],
    }
    st.table(tech_data)

    render_section_divider()

    st.markdown("#### Deployment")
    deploy_data = {
        "Service": ["FastAPI Backend", "Streamlit Frontend", "PostgreSQL", "Pinecone", "Resend"],
        "Platform": ["Render (Web Service)", "Vercel / Streamlit Cloud", "Render (Managed)", "Pinecone Cloud", "Resend Cloud"],
    }
    st.table(deploy_data)


def _render_pipeline_tab() -> None:
    """Renders the agent pipeline flow documentation."""

    st.markdown(
        """
        <div class="doc-section">
            <h4>⚙️ Meeting Processing Pipeline</h4>
            <p style="color:#94A3B8; line-height:1.6;">
                When a user submits a meeting transcript, the following multi-agent
                pipeline executes automatically:
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    steps = [
        ("1️⃣", "Form Submission", "User fills in name, role, organization, date, time, and transcript."),
        ("2️⃣", "Data Persistence", "FastAPI saves user, meeting, and participant records to PostgreSQL."),
        ("3️⃣", "Supervisor Plans", "Supervisor Agent reads context and generates execution plan: ingest → identify → extract → confirm."),
        ("4️⃣", "Ingestion", "Ingestion Agent parses transcript, applies speaker-aware chunking, embeds with Gemini, stores to Pinecone + PostgreSQL."),
        ("5️⃣", "Identity Resolution", "Identity Agent reads user name from DB, scans transcript for mentions, marks is_current_user."),
        ("6️⃣", "Task Extraction", "Extraction Agent analyzes mentions + transcript, extracts personalized tasks with priority and deadlines."),
        ("7️⃣", "Human Confirmation", "Confirmation Agent presents tasks to user. User chooses: YES / NO / PARTIAL. Only confirmed tasks are saved."),
        ("8️⃣", "Dashboard Ready", "Confirmed tasks and highlights appear on the workspace dashboard."),
    ]

    for emoji, title, desc in steps:
        st.markdown(
            f"""
            <div class="meetmind-card" style="display:flex; gap:12px; align-items:flex-start;">
                <div style="font-size:1.5rem; flex-shrink:0;">{emoji}</div>
                <div>
                    <div style="font-weight:700; color:#FFFFFE; margin-bottom:4px;">{title}</div>
                    <div style="color:#94A3B8; font-size:0.875rem; line-height:1.5;">{desc}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    render_section_divider()

    st.markdown("#### Q&A Pipeline")
    st.info(
        "The Q&A Agent runs an independent path: user question → hybrid search "
        "(Pinecone + BM25) → BGE reranker → grounded answer synthesis using Gemini. "
        "Strictly scoped to one meeting namespace."
    )

    st.markdown("#### Notification Pipeline")
    st.info(
        "APScheduler fires daily at 08:00 AM. The Notification Agent queries pending "
        "tasks due within 24h, retrieves transcript context via RAG, composes AI emails, "
        "and delivers via Resend. alert_sent is set True only after successful delivery."
    )


def _render_api_tab() -> None:
    """Renders the API endpoint reference."""

    st.markdown(
        """
        <div class="doc-section">
            <h4>🔌 API Endpoints (21 Operations)</h4>
            <p style="color:#94A3B8; line-height:1.6;">
                All endpoints are under <code>/api/v1</code>. The backend is a frozen
                FastAPI application implemented across Gate 1–4.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    endpoints = {
        "#": list(range(1, 22)),
        "Method": [
            "POST", "GET", "PUT",
            "POST", "GET", "GET", "DELETE",
            "GET", "GET", "PUT", "GET",
            "POST", "GET", "DELETE",
            "POST", "GET", "POST",
            "GET", "GET",
            "POST", "GET",
        ],
        "Endpoint": [
            "/users/register", "/users/{user_id}", "/users/{user_id}",
            "/meetings/", "/meetings/{user_id}", "/meetings/{meeting_id}/detail", "/meetings/{meeting_id}",
            "/tasks/{user_id}", "/tasks/{user_id}/meeting/{meeting_id}", "/tasks/{task_id}/status", "/tasks/{user_id}/filter",
            "/chat/{meeting_id}/message", "/chat/{meeting_id}/history", "/chat/{meeting_id}/history",
            "/extraction/{meeting_id}/run", "/extraction/{meeting_id}/preview", "/extraction/{meeting_id}/confirm",
            "/highlights/{user_id}/meeting/{meeting_id}", "/highlights/{user_id}",
            "/notifications/trigger", "/notifications/{user_id}/pending",
        ],
        "Purpose": [
            "Register user", "Get user profile", "Update user",
            "Create meeting", "List user meetings", "Meeting detail", "Delete meeting",
            "All user tasks", "Meeting tasks", "Toggle status", "Filter tasks",
            "Send Q&A message", "Chat history", "Clear history",
            "Run extraction", "Preview extracted", "Confirm tasks",
            "Meeting highlights", "All highlights",
            "Trigger notifications", "Pending alerts",
        ],
    }
    st.dataframe(endpoints, use_container_width=True, hide_index=True)


def _render_agents_tab() -> None:
    """Renders the agent roster and their responsibilities."""

    st.markdown(
        """
        <div class="doc-section">
            <h4>🤖 7-Agent Roster</h4>
            <p style="color:#94A3B8; line-height:1.6;">
                All agents are orchestrated by the LangGraph StateGraph.
                Agents never call each other directly — the Supervisor routes all transitions.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    agents = [
        ("🎯", "Supervisor Agent", "Plan-and-Execute", "gemini-3.6-flash",
         "Reads context, generates execution plan, routes to sub-agents, aggregates outputs."),
        ("📥", "Ingestion Agent", "ReAct", "gemini-3.5-flash-lite",
         "Parses transcript, chunks by speaker, embeds with Gemini, stores to Pinecone + PostgreSQL."),
        ("🔍", "Identity Agent", "Form-First", "gemini-3.5-flash-lite",
         "Reads user identity from DB, scans transcript for mentions, marks is_current_user."),
        ("⛏️", "Extraction Agent", "ReAct", "gemini-3.5-flash-lite",
         "Analyzes mentions + transcript, extracts tasks with priority/deadline, extracts highlights."),
        ("✅", "Confirmation Agent", "ReAct + HITL", "gemini-3.5-flash-lite",
         "Sole agent interacting with user. Presents tasks, waits for YES/NO/PARTIAL, persists to DB."),
        ("💬", "Q&A Agent", "ReAct + RAG", "gemini-3.6-flash",
         "Hybrid RAG retrieval scoped to one meeting. Generates grounded, citation-attributed answers."),
        ("📧", "Notification Agent", "ReAct", "gemini-3.5-flash-lite",
         "Checks deadlines, retrieves RAG context, composes AI emails, delivers via Resend."),
    ]

    for icon, name, pattern, model, desc in agents:
        st.markdown(
            f"""
            <div class="meetmind-card">
                <div style="display:flex; gap:10px; align-items:center; margin-bottom:8px;">
                    <span style="font-size:1.5rem;">{icon}</span>
                    <span style="font-weight:700; color:#FFFFFE; font-size:1rem;">{name}</span>
                    <span class="badge badge-medium" style="margin-left:auto;">{pattern}</span>
                </div>
                <div style="color:#94A3B8; font-size:0.85rem; line-height:1.5; margin-bottom:6px;">{desc}</div>
                <div style="color:#64748B; font-size:0.75rem;">Model: <code>{model}</code></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
