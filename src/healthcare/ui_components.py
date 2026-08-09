"""Shared Phase 6 visual and state primitives for the Streamlit product UI."""

from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st


STATUS_TONES = {
    "VALIDATED": "success",
    "VALID": "success",
    "APPROVED": "success",
    "FINAL": "success",
    "FRESH": "success",
    "CURRENT": "success",
    "SUPPORTED": "success",
    "NEEDS REVIEW": "warning",
    "NEEDS_REVIEW": "warning",
    "WARNING": "warning",
    "AGING": "warning",
    "PARTIALLY_SUPPORTED": "warning",
    "PARTIALLY SUPPORTED": "warning",
    "IN_REVIEW": "info",
    "IN REVIEW": "info",
    "DRAFT": "neutral",
    "PENDING": "neutral",
    "SYNTHETIC": "info",
    "OUTDATED": "danger",
    "UNSUPPORTED": "danger",
    "INVALID": "danger",
    "REJECTED": "danger",
    "NEEDS_REVISION": "danger",
    "NEEDS REVISION": "danger",
}


def inject_design_system() -> None:
    """Install a restrained enterprise healthcare intelligence design system."""
    st.markdown(
        """
        <style>
        :root {
          --hmi-navy: #12304a;
          --hmi-blue: #176b87;
          --hmi-blue-soft: #eaf4f7;
          --hmi-ink: #17212b;
          --hmi-muted: #5c6b78;
          --hmi-line: #dce4e9;
          --hmi-surface: #ffffff;
          --hmi-canvas: #f5f7f9;
          --hmi-success: #237a57;
          --hmi-success-soft: #eaf6f0;
          --hmi-warning: #956519;
          --hmi-warning-soft: #fff6df;
          --hmi-danger: #a34444;
          --hmi-danger-soft: #fbeeee;
          --hmi-info: #315f8c;
          --hmi-info-soft: #edf4fb;
          --hmi-radius: 12px;
          --hmi-shadow: 0 1px 2px rgba(18, 48, 74, .05), 0 8px 24px rgba(18, 48, 74, .04);
        }
        .stApp { background: var(--hmi-canvas); color: var(--hmi-ink); }
        [data-testid="stHeader"] { background: rgba(245,247,249,.88); }
        [data-testid="stSidebar"] { background: #102b3f; }
        [data-testid="stSidebar"] * { color: #eef6fa; }
        [data-testid="stSidebar"] [role="radiogroup"] label {
          padding: .42rem .55rem; border-radius: 8px; margin-bottom: .12rem;
        }
        [data-testid="stSidebar"] [role="radiogroup"] label:hover { background: rgba(255,255,255,.08); }
        [data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.14); }
        .block-container { max-width: 1480px; padding-top: 1.5rem; padding-bottom: 3rem; }
        h1, h2, h3, h4 { color: var(--hmi-navy); letter-spacing: -.018em; }
        h1 { font-size: 2rem !important; line-height: 1.18 !important; margin-bottom: .25rem !important; }
        h2 { font-size: 1.36rem !important; margin-top: 1.55rem !important; }
        h3 { font-size: 1.08rem !important; }
        p, li { line-height: 1.55; }
        [data-testid="stVerticalBlockBorderWrapper"] {
          background: var(--hmi-surface); border-color: var(--hmi-line) !important;
          border-radius: var(--hmi-radius); box-shadow: var(--hmi-shadow);
        }
        [data-testid="stMetric"] {
          background: var(--hmi-surface); border: 1px solid var(--hmi-line);
          border-radius: var(--hmi-radius); padding: .9rem 1rem; box-shadow: var(--hmi-shadow);
        }
        [data-testid="stMetricLabel"] { color: var(--hmi-muted); }
        [data-testid="stMetricValue"] { color: var(--hmi-navy); font-weight: 680; }
        .stButton > button, .stDownloadButton > button {
          min-height: 2.45rem; border-radius: 9px; border-color: #b8c7d1;
          font-weight: 600; box-shadow: none;
        }
        .stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {
          background: var(--hmi-blue); border-color: var(--hmi-blue);
        }
        [data-testid="stDataFrame"], [data-testid="stTable"] {
          border: 1px solid var(--hmi-line); border-radius: 10px; overflow: hidden;
        }
        [data-testid="stExpander"] {
          border: 1px solid var(--hmi-line); border-radius: 10px; background: var(--hmi-surface);
        }
        .hmi-eyebrow { color: var(--hmi-blue); font-weight: 700; font-size: .74rem; letter-spacing: .09em; text-transform: uppercase; }
        .hmi-subtitle { color: var(--hmi-muted); font-size: .98rem; max-width: 830px; margin: .1rem 0 .65rem; }
        .hmi-section { display:flex; align-items:baseline; justify-content:space-between; gap:1rem; margin:1.55rem 0 .6rem; }
        .hmi-section h2 { margin:0 !important; }
        .hmi-section span { color:var(--hmi-muted); font-size:.82rem; }
        .hmi-kpi { background:var(--hmi-surface); border:1px solid var(--hmi-line); border-radius:var(--hmi-radius); padding:1rem 1.05rem; box-shadow:var(--hmi-shadow); min-height:112px; }
        .hmi-kpi-label { color:var(--hmi-muted); font-size:.78rem; font-weight:650; text-transform:uppercase; letter-spacing:.045em; }
        .hmi-kpi-value { color:var(--hmi-navy); font-size:1.75rem; font-weight:730; line-height:1.25; margin:.25rem 0 .1rem; }
        .hmi-kpi-note { color:var(--hmi-muted); font-size:.76rem; }
        .hmi-badge { display:inline-flex; align-items:center; width:max-content; border-radius:999px; padding:.2rem .52rem; font-size:.68rem; font-weight:750; letter-spacing:.025em; text-transform:uppercase; white-space:nowrap; }
        .hmi-badge-success { color:var(--hmi-success); background:var(--hmi-success-soft); }
        .hmi-badge-warning { color:var(--hmi-warning); background:var(--hmi-warning-soft); }
        .hmi-badge-danger { color:var(--hmi-danger); background:var(--hmi-danger-soft); }
        .hmi-badge-info { color:var(--hmi-info); background:var(--hmi-info-soft); }
        .hmi-badge-neutral { color:#586876; background:#edf1f3; }
        .hmi-card { background:var(--hmi-surface); border:1px solid var(--hmi-line); border-radius:var(--hmi-radius); padding:1rem 1.05rem; box-shadow:var(--hmi-shadow); margin-bottom:.65rem; }
        .hmi-card-title { color:var(--hmi-navy); font-weight:700; margin-bottom:.22rem; }
        .hmi-card-meta { color:var(--hmi-muted); font-size:.76rem; margin-bottom:.5rem; }
        .hmi-card-body { color:var(--hmi-ink); font-size:.9rem; line-height:1.5; }
        .hmi-state { border:1px dashed #bdcbd4; border-radius:var(--hmi-radius); background:#fbfcfd; padding:1.15rem; margin:.5rem 0; }
        .hmi-state-title { color:var(--hmi-navy); font-weight:700; }
        .hmi-state-body { color:var(--hmi-muted); margin-top:.25rem; font-size:.88rem; }
        .hmi-demo { border-left:4px solid var(--hmi-blue); background:var(--hmi-blue-soft); border-radius:8px; padding:.72rem .9rem; color:#21485d; margin:.2rem 0 1rem; font-size:.84rem; }
        .hmi-callout-evidence { border-left:4px solid var(--hmi-success); }
        .hmi-callout-inference { border-left:4px solid var(--hmi-info); }
        .hmi-callout-recommendation { border-left:4px solid var(--hmi-warning); }
        .hmi-divider { border-top:1px solid var(--hmi-line); margin:1rem 0; }
        div[data-baseweb="tab-list"] { gap:.2rem; }
        button[data-baseweb="tab"] { border-radius:8px 8px 0 0; padding-left:.8rem; padding-right:.8rem; }
        @media (max-width: 900px) {
          .block-container { padding-left:1rem; padding-right:1rem; }
          .hmi-kpi { min-height:96px; }
          .hmi-kpi-value { font-size:1.45rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(eyebrow: str, title: str, subtitle: str) -> None:
    st.markdown(f'<div class="hmi-eyebrow">{escape(eyebrow)}</div>', unsafe_allow_html=True)
    st.title(title)
    st.markdown(f'<div class="hmi-subtitle">{escape(subtitle)}</div>', unsafe_allow_html=True)


def section_header(title: str, context: str = "") -> None:
    suffix = f"<span>{escape(context)}</span>" if context else ""
    st.markdown(
        f'<div class="hmi-section"><h2>{escape(title)}</h2>{suffix}</div>',
        unsafe_allow_html=True,
    )


def status_badge(label: str) -> str:
    shown = str(label or "Unknown").replace("_", " ")
    tone = STATUS_TONES.get(str(label or "").upper(), "neutral")
    return f'<span class="hmi-badge hmi-badge-{tone}">{escape(shown)}</span>'


def metric_card(label: str, value: Any, note: str = "") -> None:
    st.markdown(
        '<div class="hmi-kpi">'
        f'<div class="hmi-kpi-label">{escape(label)}</div>'
        f'<div class="hmi-kpi-value">{escape(str(value))}</div>'
        f'<div class="hmi-kpi-note">{escape(note)}</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def info_card(title: str, body: str, meta: str = "", *, css_class: str = "") -> None:
    st.markdown(
        f'<div class="hmi-card {escape(css_class)}">'
        f'<div class="hmi-card-title">{escape(title)}</div>'
        f'<div class="hmi-card-meta">{escape(meta)}</div>'
        f'<div class="hmi-card-body">{escape(body)}</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def empty_state(title: str, body: str, next_step: str = "") -> None:
    action = f" Next step: {next_step}" if next_step else ""
    st.markdown(
        '<div class="hmi-state">'
        f'<div class="hmi-state-title">{escape(title)}</div>'
        f'<div class="hmi-state-body">{escape(body + action)}</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def error_state(title: str, body: str, detail: str = "") -> None:
    st.error(f"{title}: {body}")
    if detail:
        with st.expander("Technical details", expanded=False):
            st.code(detail, language="text")


def demo_banner() -> None:
    st.markdown(
        '<div class="hmi-demo"><strong>DEMO MODE</strong> · Synthetic Evaluation Data — '
        'records are designed for workflow evaluation and do not represent real companies, '
        'hospitals, procurement events, or market claims.</div>',
        unsafe_allow_html=True,
    )
