"""
MeetMind AI — Highlight Card Component.

Renders an extracted meeting highlight (decision, milestone, announcement)
with optional relevance reasoning.
"""

from typing import Any
import streamlit as st


def render_highlight_card(highlight: dict[str, Any]) -> None:
    """
    Renders an individual meeting highlight card.

    Args:
        highlight: Highlight data dictionary containing 'content' and optional 'relevance_reason'.
    """
    content = highlight.get("content", "")
    reason = highlight.get("relevance_reason")

    st.markdown(
        f"""
        <div class="meetmind-card" style="margin-bottom:0.65rem; border-left:3px solid #6C5CE7;">
            <div style="display:flex; gap:10px; align-items:flex-start;">
                <div style="font-size:1.25rem; line-height:1; flex-shrink:0;">💡</div>
                <div style="flex:1;">
                    <div style="color:#FFFFFE; font-size:0.925rem; line-height:1.5; font-weight:500;">
                        {content}
                    </div>
                    {f'<div style="color:#94A3B8; font-size:0.78rem; margin-top:0.35rem; font-style:italic;">Why it matters: {reason}</div>' if reason else ''}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
