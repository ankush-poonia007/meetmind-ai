"""
MeetMind AI — Sidebar Navigation Component.

Provides a unified left-hand sidebar for navigation, user context,
active meeting selection, and backend connectivity status.
"""

from typing import Optional
import streamlit as st

from services.api_client import api


def render_sidebar() -> None:
    """Renders the persistent left sidebar navigation and session status."""
    with st.sidebar:
        # ── Sidebar Brand ────────────────────────────────────────────────
        st.markdown(
            """
            <div style="display:flex; align-items:center; gap:10px; margin-bottom:1rem; padding-bottom:0.75rem; border-bottom:1px solid rgba(108, 92, 231, 0.15);">
                <div style="font-size:1.85rem; line-height:1;">🧠</div>
                <div>
                    <div style="font-size:1.25rem; font-weight:800; background:linear-gradient(135deg, #6C5CE7, #a29bfe); -webkit-background-clip:text; -webkit-text-fill-color:transparent;">MeetMind AI</div>
                    <div style="font-size:0.75rem; color:#94A3B8;">Meeting Intelligence</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ── Navigation Menu ──────────────────────────────────────────────
        st.markdown('<div style="font-size:0.75rem; font-weight:600; color:#64748B; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:0.4rem;">Navigation</div>', unsafe_allow_html=True)
        current_page = st.session_state.get("current_page", "landing")

        pages = [
            ("landing", "🏠 Home"),
            ("workspace", "💼 Workspace"),
            ("documentation", "📖 Docs"),
        ]

        for page_key, label in pages:
            is_active = current_page == page_key
            btn_type = "primary" if is_active else "secondary"
            if st.button(label, use_container_width=True, type=btn_type, key=f"sidebar_nav_{page_key}"):
                st.session_state["current_page"] = page_key
                st.rerun()

        st.markdown('<div class="section-divider" style="margin:0.75rem 0;"></div>', unsafe_allow_html=True)

        # ── User Profile Context ─────────────────────────────────────────
        st.markdown('<div style="font-size:0.75rem; font-weight:600; color:#64748B; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:0.4rem;">User Context</div>', unsafe_allow_html=True)
        user_name = st.session_state.get("user_name", "")
        user_email = st.session_state.get("user_email", "")

        if user_name:
            st.markdown(
                f"""
                <div style="background:rgba(26,26,46,0.8); border:1px solid rgba(108,92,231,0.2); border-radius:10px; padding:0.65rem 0.85rem; margin-bottom:0.5rem;">
                    <div style="font-weight:700; color:#FFFFFE; font-size:0.9rem;">👤 {user_name}</div>
                    <div style="font-size:0.75rem; color:#94A3B8; word-break:break-all;">{user_email}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.caption("No user active. Create a meeting or register below to set user identity.")

        st.markdown('<div class="section-divider" style="margin:0.75rem 0;"></div>', unsafe_allow_html=True)

        # ── Backend Health Indicator ─────────────────────────────────────
        st.markdown('<div style="font-size:0.75rem; font-weight:600; color:#64748B; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:0.4rem;">System Status</div>', unsafe_allow_html=True)
        is_healthy = api.health_check()
        if is_healthy:
            st.markdown('<div style="display:flex; align-items:center; gap:6px; font-size:0.8rem; color:#00B894;">🟢 <span>Backend API Online</span></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="display:flex; align-items:center; gap:6px; font-size:0.8rem; color:#E17055;">🔴 <span>Backend API Offline</span></div>', unsafe_allow_html=True)

        st.markdown('<div class="section-divider" style="margin:0.75rem 0;"></div>', unsafe_allow_html=True)

        # ── Session Reset ────────────────────────────────────────────────
        if st.button("🔄 Reset Session", use_container_width=True, help="Clears local session state and returns to landing page"):
            from utils.session_state import reset_session
            reset_session()
            st.session_state["current_page"] = "landing"
            st.rerun()
