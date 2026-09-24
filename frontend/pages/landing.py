"""
MeetMind AI — Landing Page.

The public-facing landing page presenting MeetMind's value proposition,
key features, and a call-to-action to enter the workspace.
"""

import streamlit as st

from components.layout import render_footer


def render_landing_page() -> None:
    """Renders the full landing page with hero section and feature grid."""

    # ── Hero Section ─────────────────────────────────────────────────────
    st.markdown(
        """
        <div class="hero-section">
            <div class="hero-title">Turn Meetings<br/>Into Action</div>
            <div class="hero-subtitle">
                MeetMind AI transforms your meeting transcripts into personalized tasks,
                key highlights, and intelligent Q&A — powered by a multi-agent AI pipeline
                that knows who you are in the meeting.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── CTA Button ───────────────────────────────────────────────────────
    col_left, col_center, col_right = st.columns([1.15, 1, 1.15])
    with col_center:
        if st.button("🚀  Enter Workspace", use_container_width=True, type="primary"):
            st.session_state["current_page"] = "workspace"
            st.rerun()

    # ── Feature Grid ─────────────────────────────────────────────────────
    st.markdown(
        '<div class="section-header">✨ What MeetMind Does For You</div>',
        unsafe_allow_html=True,
    )

    features = [
        {
            "icon": "📝",
            "title": "Multi-Format Ingestion",
            "desc": "Submit transcripts via paste, PDF, or TXT. The Ingestion Agent parses, chunks, and embeds everything automatically.",
        },
        {
            "icon": "🎯",
            "title": "Identity-Aware Extraction",
            "desc": "MeetMind identifies you inside the transcript and extracts only the tasks and highlights relevant to you.",
        },
        {
            "icon": "✅",
            "title": "Human-in-the-Loop Confirmation",
            "desc": "Review extracted tasks before they reach your dashboard. Accept all, reject all, or select specific items.",
        },
        {
            "icon": "💬",
            "title": "Meeting-Scoped Q&A",
            "desc": "Ask natural language questions about any meeting. Answers are grounded in your transcript using hybrid RAG.",
        },
        {
            "icon": "📊",
            "title": "Unified Task Dashboard",
            "desc": "View all your tasks across meetings. Filter by priority, status, and deadline. Toggle completion with one click.",
        },
        {
            "icon": "📧",
            "title": "AI Email Notifications",
            "desc": "Automated daily deadline alerts with context-rich emails composed by AI using your original meeting discussion.",
        },
    ]

    # Render features in 2 distinct rows of 3 columns to ensure exact row alignment
    for row_start in range(0, len(features), 3):
        row_cols = st.columns(3)
        for col, feature in zip(row_cols, features[row_start : row_start + 3]):
            with col:
                st.markdown(
                    f"""
                    <div class="feature-card">
                        <div class="feature-icon">{feature["icon"]}</div>
                        <div class="feature-title">{feature["title"]}</div>
                        <div class="feature-desc">{feature["desc"]}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    # ── Tech Stack Section ───────────────────────────────────────────────
    st.markdown(
        '<div class="section-header">⚡ Powered By</div>',
        unsafe_allow_html=True,
    )

    tech_cols = st.columns(4)
    tech_items = [
        ("🧠", "LangGraph", "Multi-agent orchestration"),
        ("💎", "Gemini 3.6", "LLM reasoning & embeddings"),
        ("🔍", "Pinecone + BM25", "Hybrid RAG retrieval"),
        ("⚡", "FastAPI", "Production-grade API layer"),
    ]

    for col, (icon, name, desc) in zip(tech_cols, tech_items):
        with col:
            st.markdown(
                f"""
                <div class="tech-card">
                    <div class="tech-icon">{icon}</div>
                    <div class="tech-name">{name}</div>
                    <div class="tech-desc">{desc}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    render_footer()
