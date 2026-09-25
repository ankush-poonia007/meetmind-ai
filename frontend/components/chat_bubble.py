"""
MeetMind AI — Meeting Chat / Q&A Component.

Provides a meeting-scoped conversational interface for asking natural language questions
grounded in the meeting's transcript via hybrid RAG.
Renders message history, assistant answers, confidence ratings, and source citations.
"""

from typing import Any, Optional
import streamlit as st

from services.api_client import APIError, api


def render_chat_message(role: str, content: str, sources: Optional[list[dict]] = None, confidence: Optional[str] = None) -> None:
    """
    Renders an individual chat message bubble.

    Args:
        role: "user" or "assistant".
        content: Message text.
        sources: Optional list of retrieved chunk citations.
        confidence: Optional confidence level ("high", "medium", "low").
    """
    if role == "user":
        st.markdown(
            f"""
            <div style="display:flex; justify-content:flex-end; margin-bottom:0.75rem;">
                <div style="background:linear-gradient(135deg, rgba(108, 92, 231, 0.35), rgba(108, 92, 231, 0.2)); border:1px solid rgba(108, 92, 231, 0.4); border-radius:14px 14px 2px 14px; padding:0.75rem 1rem; max-width:80%; color:#FFFFFE; font-size:0.9rem; line-height:1.5;">
                    <div style="font-weight:700; color:#a29bfe; font-size:0.75rem; margin-bottom:2px;">You</div>
                    {content}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        conf_badge = ""
        if confidence:
            c_low = confidence.lower()
            badge_class = f"badge-{c_low}" if c_low in ["high", "medium", "low"] else "badge-medium"
            conf_badge = f'<span class="badge {badge_class}" style="margin-left:8px; font-size:0.68rem;">{confidence.upper()} CONFIDENCE</span>'

        st.markdown(
            f"""
            <div style="display:flex; justify-content:flex-start; margin-bottom:0.75rem;">
                <div style="background:rgba(26, 26, 46, 0.85); border:1px solid rgba(108, 92, 231, 0.2); border-radius:14px 14px 14px 2px; padding:0.85rem 1.15rem; max-width:85%; color:#FFFFFE; font-size:0.9rem; line-height:1.55;">
                    <div style="display:flex; align-items:center; margin-bottom:4px;">
                        <span style="font-weight:700; color:#00B894; font-size:0.8rem;">🤖 MeetMind Q&A</span>
                        {conf_badge}
                    </div>
                    {content}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if sources:
            with st.expander(f"📚 {len(sources)} Transcript Source Citation(s)", expanded=False):
                for idx, src in enumerate(sources, 1):
                    speaker = src.get("speaker") or "Unknown Speaker"
                    ts = f" at {src.get('timestamp')}" if src.get("timestamp") else ""
                    excerpt = src.get("excerpt", "")
                    st.markdown(
                        f"""
                        <div style="background:rgba(15, 14, 23, 0.6); border-left:2px solid #6C5CE7; padding:6px 10px; margin-bottom:6px; border-radius:0 6px 6px 0; font-size:0.8rem; color:#94A3B8;">
                            <strong style="color:#FFFFFE;">[{idx}] {speaker}{ts}:</strong> <em>"{excerpt}"</em>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )


def render_meeting_chat(meeting_id: str, user_id: str) -> None:
    """
    Renders the meeting Q&A conversation panel, connecting to the backend Q&A pipeline.

    Args:
        meeting_id: UUID of current meeting context.
        user_id: UUID of active user.
    """
    st.markdown('<div class="section-header" style="font-size:1.1rem; margin-top:1rem;">💬 Meeting Q&A (RAG Grounded)</div>', unsafe_allow_html=True)
    st.caption("Ask questions strictly scoped to this meeting's transcript. The Q&A Agent synthesizes answers with source citations.")

    # ── Load History ─────────────────────────────────────────────────────
    chat_key = f"chat_history_{meeting_id}"
    if chat_key not in st.session_state:
        try:
            hist_resp = api.get(f"/chat/{meeting_id}/history")
            messages = hist_resp.get("messages", []) if isinstance(hist_resp, dict) else []
            st.session_state[chat_key] = [
                {"role": m.get("role", "user"), "content": m.get("content", "")}
                for m in messages
            ]
        except Exception:
            st.session_state[chat_key] = []

    # Display History
    history = st.session_state.get(chat_key, [])
    if not history:
        st.info("No questions asked yet. Ask anything about this meeting's discussion or decisions!")
    else:
        for msg in history:
            render_chat_message(
                role=msg.get("role", "user"),
                content=msg.get("content", ""),
                sources=msg.get("sources"),
                confidence=msg.get("confidence"),
            )

    # ── Ask Question Input ───────────────────────────────────────────────
    with st.form(f"chat_form_{meeting_id}", clear_on_submit=True):
        col_q, col_ask = st.columns([4, 1])
        with col_q:
            question = st.text_input(
                "Your Question",
                placeholder="What action items were assigned to engineering? What decisions were made?",
                label_visibility="collapsed",
            )
        with col_ask:
            ask_submitted = st.form_submit_button("Ask Agent", type="primary", use_container_width=True)

    if ask_submitted and question.strip():
        # Append user message immediately
        st.session_state[chat_key].append({"role": "user", "content": question.strip()})

        with st.spinner("Q&A Agent retrieving transcript context and synthesizing answer..."):
            try:
                chat_res = api.post(
                    f"/chat/{meeting_id}/message",
                    json={"question": question.strip(), "user_id": user_id},
                )
                answer = chat_res.get("answer", "No answer generated.")
                sources = chat_res.get("sources", [])
                confidence = chat_res.get("confidence", "medium")

                st.session_state[chat_key].append({
                    "role": "assistant",
                    "content": answer,
                    "sources": sources,
                    "confidence": confidence,
                })
                st.rerun()

            except APIError as exc:
                if st.session_state[chat_key] and st.session_state[chat_key][-1].get("role") == "user":
                    st.session_state[chat_key].pop()
                st.error(f"Failed to get answer: {exc.message}")
            except Exception as exc:
                if st.session_state[chat_key] and st.session_state[chat_key][-1].get("role") == "user":
                    st.session_state[chat_key].pop()
                st.error(f"Unexpected error: {exc}")

    # Clear History action
    if history:
        if st.button("🗑️ Clear Chat History", key=f"clear_chat_{meeting_id}", help="Clears conversation history for this meeting"):
            try:
                api.delete(f"/chat/{meeting_id}/history")
                st.session_state[chat_key] = []
                st.success("Chat history cleared.")
                st.rerun()
            except APIError as exc:
                st.error(f"Failed to clear history: {exc.message}")
