"""Shared Phase 6 visual and state primitives for the Streamlit product UI."""

from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st


STATUS_TONES = {
    "HIGH": "danger",
    "MEDIUM": "warning",
    "LOW": "neutral",
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

STATUS_LABELS_ZH = {
    "HIGH": "高",
    "MEDIUM": "中",
    "LOW": "低",
    "VALIDATED": "已验证",
    "VALID": "有效",
    "APPROVED": "已批准",
    "FINAL": "已定稿",
    "FRESH": "最新",
    "CURRENT": "当前",
    "SUPPORTED": "有证据支持",
    "NEEDS REVIEW": "待审核",
    "NEEDS_REVIEW": "待审核",
    "WARNING": "需注意",
    "AGING": "临近过期",
    "PARTIALLY_SUPPORTED": "部分支持",
    "PARTIALLY SUPPORTED": "部分支持",
    "IN_REVIEW": "审核中",
    "IN REVIEW": "审核中",
    "DRAFT": "草稿",
    "PENDING": "待处理",
    "SYNTHETIC": "模拟数据",
    "OUTDATED": "已过期",
    "UNSUPPORTED": "无证据支持",
    "INVALID": "无效",
    "REJECTED": "已驳回",
    "NEEDS_REVISION": "需修改",
    "NEEDS REVISION": "需修改",
}


def inject_design_system() -> None:
    """Install the enterprise healthcare intelligence design system."""
    st.markdown(
        """
        <style>
        :root {
          --hmi-navy: #0b2942;
          --hmi-blue: #0b7595;
          --hmi-blue-strong: #075e7b;
          --hmi-blue-soft: #e8f5f8;
          --hmi-ink: #152431;
          --hmi-muted: #60717f;
          --hmi-line: #d9e3e8;
          --hmi-surface: #ffffff;
          --hmi-surface-muted: #f7fafb;
          --hmi-canvas: #f3f6f8;
          --hmi-success: #197054;
          --hmi-success-soft: #eaf6f0;
          --hmi-warning: #8a5a10;
          --hmi-warning-soft: #fff4d9;
          --hmi-danger: #a13d46;
          --hmi-danger-soft: #fbeeee;
          --hmi-info: #315f8c;
          --hmi-info-soft: #edf4fb;
          --hmi-cyan: #48b6c8;
          --hmi-sidebar: #08263c;
          --hmi-radius: 14px;
          --hmi-shadow: 0 1px 2px rgba(11, 41, 66, .05), 0 12px 30px rgba(11, 41, 66, .05);
          --hmi-shadow-hover: 0 2px 4px rgba(11, 41, 66, .06), 0 18px 40px rgba(11, 41, 66, .09);
        }
        html, body, [class*="css"] { font-family: Inter, "IBM Plex Sans", "Segoe UI", Arial, sans-serif; }
        .stApp {
          background:
            radial-gradient(circle at 78% -8%, rgba(72,182,200,.09), transparent 28rem),
            linear-gradient(180deg, #f8fafb 0, var(--hmi-canvas) 24rem);
          color: var(--hmi-ink);
        }
        [data-testid="stHeader"] {
          background: rgba(248,250,251,.82); backdrop-filter: blur(16px);
          border-bottom: 1px solid rgba(217,227,232,.55);
        }
        [data-testid="stSidebar"] {
          background:
            radial-gradient(circle at 10% 0, rgba(72,182,200,.18), transparent 15rem),
            linear-gradient(180deg, var(--hmi-sidebar) 0%, #0b314a 58%, #0a2b42 100%);
          border-right: 1px solid rgba(255,255,255,.06);
        }
        [data-testid="stSidebar"] * { color: #eef6fa; }
        [data-testid="stSidebar"] [data-testid="stSidebarContent"] { padding-top: 1.15rem; }
        [data-testid="stSidebar"] [role="radiogroup"] label {
          padding: .57rem .7rem; border-radius: 10px; margin-bottom: .12rem;
          font-size: .86rem; font-weight: 570;
          transition: background .15s ease, transform .15s ease, box-shadow .15s ease;
        }
        [data-testid="stSidebar"] [role="radiogroup"] label:hover { background: rgba(255,255,255,.08); transform: translateX(2px); }
        [data-testid="stSidebar"] [role="radiogroup"] label > div:first-child { display:none !important; }
        [data-testid="stSidebar"] [role="radiogroup"] label > div:last-child > div:first-child > div:first-child { display:none !important; }
        [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
          background: rgba(109, 211, 231, .15);
          box-shadow: inset 3px 0 0 #65d0e5, 0 7px 18px rgba(0,0,0,.08);
        }
        [data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.14); }
        [data-testid="stSidebar"] .stCaption { color: rgba(238,246,250,.68) !important; }
        .block-container { max-width: 1460px; padding-top: 1.15rem; padding-bottom: 3.5rem; }
        h1, h2, h3, h4 { color: var(--hmi-navy); letter-spacing: -.018em; }
        h1 { font-size: 2.12rem !important; line-height: 1.12 !important; margin-bottom: .25rem !important; }
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
          min-height: 2.5rem; border-radius: 10px; border-color: #b8c7d1;
          background:#fff; color:var(--hmi-navy); font-weight: 650; box-shadow: 0 1px 2px rgba(11,41,66,.04);
          transition: transform .12s ease, box-shadow .12s ease, border-color .12s ease;
        }
        .stButton > button:hover, .stDownloadButton > button:hover { transform: translateY(-1px); border-color:#8fa6b4; box-shadow: 0 7px 18px rgba(11,41,66,.1); }
        .stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {
          background: var(--hmi-blue); border-color: var(--hmi-blue);
        }
        .stButton > button[kind="primary"]:hover, .stDownloadButton > button[kind="primary"]:hover { background: var(--hmi-blue-strong); }
        [data-testid="stDataFrame"], [data-testid="stTable"] {
          background:#fff; border: 1px solid var(--hmi-line); border-radius: 12px; overflow: hidden;
          box-shadow: 0 8px 22px rgba(11,41,66,.035);
        }
        [data-testid="stExpander"] {
          border: 1px solid var(--hmi-line); border-radius: 12px; background: var(--hmi-surface);
          box-shadow: 0 4px 14px rgba(11,41,66,.025); overflow:hidden;
        }
        [data-testid="stMain"] [data-baseweb="input"] > div,
        [data-testid="stMain"] [data-baseweb="select"] > div,
        [data-testid="stMain"] [data-baseweb="textarea"] > div {
          background:#fff; border-color:#c8d5dc; border-radius:10px;
          transition:border-color .15s ease, box-shadow .15s ease;
        }
        [data-testid="stMain"] [data-baseweb="input"] > div:focus-within,
        [data-testid="stMain"] [data-baseweb="select"] > div:focus-within,
        [data-testid="stMain"] [data-baseweb="textarea"] > div:focus-within {
          border-color:var(--hmi-blue); box-shadow:0 0 0 3px rgba(11,117,149,.11);
        }
        [data-testid="stMain"] [data-testid="stAlert"] { border-radius:12px; }
        [data-testid="stMain"] [role="radiogroup"] {
          width:max-content; max-width:100%; gap:.1rem; padding:.24rem; border-radius:11px; background:#e9eff2;
        }
        [data-testid="stMain"] [role="radiogroup"] label {
          padding:.42rem .78rem; border-radius:8px; color:var(--hmi-muted); cursor:pointer;
        }
        [data-testid="stMain"] [role="radiogroup"] label > div:first-child { display:none !important; }
        [data-testid="stMain"] [role="radiogroup"] label > div:last-child > div:first-child > div:first-child { display:none !important; }
        [data-testid="stMain"] [role="radiogroup"] label:has(input:checked) {
          background:#fff; color:var(--hmi-navy); box-shadow:0 2px 8px rgba(11,41,66,.09);
        }
        [data-testid="stMain"] [data-testid="stVegaLiteChart"] {
          background:#fff; border:1px solid var(--hmi-line); border-radius:var(--hmi-radius);
          padding:.7rem .8rem .4rem; box-shadow:var(--hmi-shadow);
        }
        .hmi-brand { padding:.15rem 0 .45rem; }
        .hmi-brand-lockup { display:flex; align-items:center; gap:.72rem; }
        .hmi-logo {
          position:relative; flex:0 0 42px; width:42px; height:42px; border-radius:12px;
          background:linear-gradient(145deg, rgba(101,208,229,.24), rgba(255,255,255,.06));
          border:1px solid rgba(141,224,239,.28); box-shadow:inset 0 1px 0 rgba(255,255,255,.1), 0 8px 22px rgba(0,0,0,.12);
        }
        .hmi-logo::before, .hmi-logo::after { content:""; position:absolute; background:#71d3e4; border-radius:3px; }
        .hmi-logo::before { width:20px; height:6px; left:10px; top:17px; }
        .hmi-logo::after { width:6px; height:20px; left:17px; top:10px; }
        .hmi-brand-kicker { color:#75d1e4; font-size:.66rem; font-weight:750; letter-spacing:.11em; text-transform:uppercase; }
        .hmi-brand-title { color:#f6fbfd; font-size:1.06rem; font-weight:730; line-height:1.18; margin:.13rem 0 0; letter-spacing:-.015em; }
        .hmi-brand-subtitle { color:rgba(238,246,250,.7); font-size:.73rem; line-height:1.45; margin-top:.65rem; max-width:245px; }
        .hmi-eyebrow { color: var(--hmi-blue); font-weight: 750; font-size: .72rem; letter-spacing: .095em; text-transform: uppercase; }
        .hmi-page-hero {
          position:relative; overflow:hidden; margin:.05rem 0 .85rem; padding:1.35rem 1.45rem 1.25rem;
          border:1px solid #d7e4e9; border-radius:18px;
          background:
            radial-gradient(circle at 91% 16%, rgba(72,182,200,.18), transparent 15rem),
            linear-gradient(118deg, #ffffff 0%, #f9fcfd 64%, #edf8fa 100%);
          box-shadow:0 1px 2px rgba(11,41,66,.04), 0 16px 42px rgba(11,41,66,.055);
        }
        .hmi-page-hero::after {
          content:""; position:absolute; right:2rem; bottom:-4rem; width:12rem; height:12rem;
          border:1px solid rgba(11,117,149,.12); border-radius:50%; box-shadow:0 0 0 2.2rem rgba(72,182,200,.035), 0 0 0 4.4rem rgba(72,182,200,.022);
        }
        .hmi-page-hero h1 { position:relative; z-index:1; margin:.28rem 0 .3rem !important; max-width:920px; }
        .hmi-subtitle { position:relative; z-index:1; color: var(--hmi-muted); font-size: .96rem; max-width: 880px; margin: 0; line-height:1.52; }
        .hmi-section { position:relative; display:flex; align-items:baseline; justify-content:space-between; gap:1rem; margin:1.7rem 0 .7rem; padding-left:.72rem; }
        .hmi-section::before { content:""; position:absolute; left:0; top:.14rem; bottom:.12rem; width:3px; border-radius:99px; background:linear-gradient(180deg,var(--hmi-blue),var(--hmi-cyan)); }
        .hmi-section h2 { margin:0 !important; }
        .hmi-section span { color:var(--hmi-muted); font-size:.82rem; }
        .hmi-kpi { position:relative; overflow:hidden; background:var(--hmi-surface); border:1px solid var(--hmi-line); border-radius:var(--hmi-radius); padding:1.02rem 1.08rem; box-shadow:var(--hmi-shadow); min-height:112px; transition:transform .15s ease, box-shadow .15s ease; }
        .hmi-kpi::before { content:""; position:absolute; left:0; top:0; right:0; height:3px; background:linear-gradient(90deg,var(--hmi-blue),var(--hmi-cyan)); opacity:.86; }
        .hmi-kpi:hover { transform:translateY(-2px); box-shadow:var(--hmi-shadow-hover); }
        .hmi-kpi-label { color:var(--hmi-muted); font-size:.78rem; font-weight:650; text-transform:uppercase; letter-spacing:.045em; }
        .hmi-kpi-value { color:var(--hmi-navy); font-size:1.75rem; font-weight:730; line-height:1.25; margin:.25rem 0 .1rem; font-variant-numeric:tabular-nums; }
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
        .hmi-context { display:flex; flex-wrap:wrap; gap:.45rem; align-items:center; margin:.15rem 0 1rem; }
        .hmi-context-item { background:var(--hmi-surface); border:1px solid var(--hmi-line); border-radius:999px; padding:.32rem .62rem; color:var(--hmi-muted); font-size:.72rem; font-weight:650; }
        .hmi-context-item strong { color:var(--hmi-navy); }
        .hmi-priority { background:var(--hmi-surface); border:1px solid var(--hmi-line); border-left:4px solid var(--hmi-info); border-radius:var(--hmi-radius); padding:.9rem 1rem; min-height:116px; box-shadow:var(--hmi-shadow); }
        .hmi-priority-danger { border-left-color:var(--hmi-danger); background:linear-gradient(110deg,#fff 0,#fff 70%,var(--hmi-danger-soft)); }
        .hmi-priority-warning { border-left-color:#d0952f; background:linear-gradient(110deg,#fff 0,#fff 70%,var(--hmi-warning-soft)); }
        .hmi-priority-success { border-left-color:var(--hmi-success); background:linear-gradient(110deg,#fff 0,#fff 70%,var(--hmi-success-soft)); }
        .hmi-priority-label { color:var(--hmi-muted); font-size:.7rem; font-weight:750; letter-spacing:.055em; text-transform:uppercase; }
        .hmi-priority-value { color:var(--hmi-navy); font-size:1.45rem; font-weight:730; margin:.2rem 0 .1rem; }
        .hmi-priority-body { color:var(--hmi-muted); font-size:.78rem; line-height:1.4; }
        .hmi-progress { background:var(--hmi-surface); border:1px solid var(--hmi-line); border-radius:var(--hmi-radius); padding:.85rem .95rem; box-shadow:var(--hmi-shadow); }
        .hmi-progress-head { display:flex; align-items:center; justify-content:space-between; gap:.6rem; }
        .hmi-progress-label { color:var(--hmi-navy); font-size:.8rem; font-weight:700; }
        .hmi-progress-value { color:var(--hmi-blue); font-size:.82rem; font-weight:750; }
        .hmi-progress-track { height:7px; background:#e7edf0; border-radius:999px; margin:.55rem 0 .4rem; overflow:hidden; }
        .hmi-progress-fill { height:100%; border-radius:999px; background:linear-gradient(90deg, var(--hmi-blue), #4fb3c8); }
        .hmi-progress-note { color:var(--hmi-muted); font-size:.72rem; line-height:1.35; }
        .hmi-signal { background:var(--hmi-surface); border:1px solid var(--hmi-line); border-radius:var(--hmi-radius); padding:.9rem 1rem; box-shadow:var(--hmi-shadow); margin-bottom:.58rem; transition:transform .15s ease, border-color .15s ease, box-shadow .15s ease; }
        .hmi-signal:hover { transform:translateY(-1px); border-color:#b9ccd5; box-shadow:var(--hmi-shadow-hover); }
        .hmi-signal-head { display:flex; justify-content:space-between; gap:1rem; align-items:flex-start; }
        .hmi-signal-title { color:var(--hmi-navy); font-weight:720; line-height:1.35; }
        .hmi-signal-meta { color:var(--hmi-muted); font-size:.72rem; margin:.28rem 0 .45rem; }
        .hmi-signal-body { color:var(--hmi-ink); font-size:.86rem; line-height:1.48; }
        .hmi-workflow { display:grid; grid-template-columns:repeat(5,1fr); gap:.52rem; margin:.55rem 0 1.1rem; }
        .hmi-workflow-step { position:relative; background:rgba(255,255,255,.9); border:1px solid var(--hmi-line); border-radius:11px; padding:.72rem .78rem .72rem 2.45rem; color:var(--hmi-muted); font-size:.72rem; min-height:70px; box-shadow:0 5px 14px rgba(11,41,66,.025); }
        .hmi-workflow-index { position:absolute; left:.72rem; top:.72rem; width:1.28rem; height:1.28rem; display:grid; place-items:center; border-radius:50%; background:var(--hmi-blue-soft); color:var(--hmi-blue); font-size:.66rem; font-weight:800; }
        .hmi-workflow-step strong { display:block; color:var(--hmi-navy); font-size:.78rem; margin-bottom:.12rem; }
        .hmi-state { border:1px dashed #bdcbd4; border-radius:var(--hmi-radius); background:#fbfcfd; padding:1.15rem; margin:.5rem 0; }
        .hmi-state-title { color:var(--hmi-navy); font-weight:700; }
        .hmi-state-body { color:var(--hmi-muted); margin-top:.25rem; font-size:.88rem; }
        .hmi-demo { border:1px solid #c8e5eb; border-left:4px solid var(--hmi-blue); background:linear-gradient(90deg,var(--hmi-blue-soft),#f4fbfc); border-radius:10px; padding:.68rem .9rem; color:#21485d; margin:.15rem 0 .85rem; font-size:.82rem; box-shadow:0 5px 15px rgba(11,117,149,.035); }
        .hmi-sidebar-status { margin-top:.75rem; padding:.68rem .72rem; border:1px solid rgba(255,255,255,.11); border-radius:10px; background:rgba(255,255,255,.045); color:rgba(238,246,250,.72); font-size:.7rem; line-height:1.4; }
        .hmi-live-dot { display:inline-block; width:7px; height:7px; border-radius:50%; background:#68d4a8; box-shadow:0 0 0 4px rgba(104,212,168,.1); margin-right:.45rem; }
        .hmi-callout-evidence { border-left:4px solid var(--hmi-success); }
        .hmi-callout-inference { border-left:4px solid var(--hmi-info); }
        .hmi-callout-recommendation { border-left:4px solid var(--hmi-warning); }
        .hmi-divider { border-top:1px solid var(--hmi-line); margin:1rem 0; }
        [data-testid="stMain"] div[data-baseweb="tab-list"] { width:max-content; gap:.12rem; padding:.24rem; background:#e9eff2; border-radius:11px; }
        [data-testid="stMain"] button[data-baseweb="tab"] { border-radius:8px; padding-left:.9rem; padding-right:.9rem; color:var(--hmi-muted); }
        [data-testid="stMain"] button[data-baseweb="tab"][aria-selected="true"] { background:#fff; color:var(--hmi-navy); box-shadow:0 2px 8px rgba(11,41,66,.09); }
        [data-testid="stMain"] div[data-baseweb="tab-highlight"],
        [data-testid="stMain"] div[data-baseweb="tab-border"] { display:none; }

        /* Analyst workspace: compact, restrained, and data-first. */
        :root {
          --hmi-radius: 9px;
          --hmi-canvas: #f5f7f8;
          --hmi-line: #d8e0e5;
          --hmi-shadow: 0 1px 2px rgba(11,41,66,.035);
          --hmi-shadow-hover: 0 1px 3px rgba(11,41,66,.06);
        }
        .stApp { background:var(--hmi-canvas); }
        [data-testid="stHeader"] { background:rgba(245,247,248,.94); backdrop-filter:blur(10px); }
        [data-testid="stToolbar"],
        [data-testid="stElementToolbar"] { display:none !important; }
        [data-testid="stSidebar"] { background:#0b3048; }
        [data-testid="stSidebar"] [role="radiogroup"] label {
          border-radius:7px; transition:background .12s ease; font-weight:540;
        }
        [data-testid="stSidebar"] [role="radiogroup"] label:hover { transform:none; background:rgba(255,255,255,.065); }
        [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
          background:rgba(105,202,220,.12); box-shadow:inset 2px 0 0 #68c8da;
        }
        .block-container { max-width:1430px; padding-top:1rem; }
        h1 { font-size:1.9rem !important; letter-spacing:-.025em; }
        h2 { font-size:1.22rem !important; }
        [data-testid="stVerticalBlockBorderWrapper"], [data-testid="stMetric"] {
          border-radius:var(--hmi-radius); box-shadow:none;
        }
        .stButton > button, .stDownloadButton > button {
          min-height:2.35rem; border-radius:7px; box-shadow:none; transition:background .12s ease, border-color .12s ease;
        }
        .stButton > button:hover, .stDownloadButton > button:hover { transform:none; box-shadow:none; }
        [data-testid="stDataFrame"], [data-testid="stTable"] { border-radius:8px; box-shadow:none; }
        [data-testid="stExpander"] { border-radius:8px; box-shadow:none; }
        [data-testid="stMain"] [data-baseweb="input"] > div,
        [data-testid="stMain"] [data-baseweb="select"] > div,
        [data-testid="stMain"] [data-baseweb="textarea"] > div { border-radius:7px; }
        [data-testid="stMain"] [data-testid="stVegaLiteChart"] { border-radius:9px; box-shadow:none; }
        .hmi-logo {
          display:grid; place-items:center; flex-basis:36px; width:36px; height:36px; border-radius:7px;
          background:#0f7892; border:1px solid rgba(255,255,255,.14); box-shadow:none;
          color:#fff; font-size:.66rem; font-weight:800; letter-spacing:.08em;
        }
        .hmi-logo::before, .hmi-logo::after { display:none; }
        .hmi-brand-lockup { gap:.65rem; }
        .hmi-brand-kicker { color:#7bc8d8; font-size:.61rem; letter-spacing:.09em; }
        .hmi-brand-title { font-size:1rem; font-weight:680; }
        .hmi-brand-subtitle { margin-top:.55rem; }
        .hmi-page-hero {
          overflow:visible; margin:0 0 .78rem; padding:.35rem 0 1rem;
          border:0; border-bottom:1px solid var(--hmi-line); border-radius:0;
          background:transparent; box-shadow:none;
        }
        .hmi-page-hero::after { display:none; }
        .hmi-page-hero h1 { margin:.2rem 0 .22rem !important; }
        .hmi-subtitle { max-width:980px; font-size:.91rem; line-height:1.45; }
        .hmi-eyebrow { font-size:.66rem; letter-spacing:.085em; }
        .hmi-section {
          margin:1.55rem 0 .7rem; padding:0 0 .5rem; border-bottom:1px solid var(--hmi-line);
        }
        .hmi-section::before { display:none; }
        .hmi-section span { font-size:.76rem; }
        .hmi-kpi {
          min-height:98px; padding:.88rem .95rem; border-radius:9px; box-shadow:none;
          transition:border-color .12s ease;
        }
        .hmi-kpi::before { display:none; }
        .hmi-kpi:hover { transform:none; box-shadow:none; border-color:#bfcdd4; }
        .hmi-kpi-label { font-size:.7rem; letter-spacing:.04em; }
        .hmi-kpi-value { font-size:1.62rem; margin:.18rem 0 .06rem; }
        .hmi-badge { border-radius:4px; padding:.18rem .42rem; font-size:.64rem; }
        .hmi-card { border-radius:9px; box-shadow:none; }
        .hmi-context { gap:0; margin:.05rem 0 .8rem; border:1px solid var(--hmi-line); border-radius:7px; width:max-content; max-width:100%; background:#fff; overflow:hidden; }
        .hmi-context-item { border:0; border-right:1px solid var(--hmi-line); border-radius:0; padding:.34rem .62rem; background:transparent; font-weight:560; }
        .hmi-context-item:last-child { border-right:0; }
        .hmi-priority { min-height:105px; border-radius:9px; box-shadow:none; }
        .hmi-priority-danger, .hmi-priority-warning, .hmi-priority-success { background:#fff; }
        .hmi-progress { border-radius:9px; box-shadow:none; }
        .hmi-progress-fill { background:var(--hmi-blue); }
        .hmi-signal { border-radius:8px; box-shadow:none; transition:background .12s ease, border-color .12s ease; }
        .hmi-signal:hover { transform:none; box-shadow:none; background:#fbfcfd; }
        .hmi-workflow { gap:0; border:1px solid var(--hmi-line); border-radius:9px; overflow:hidden; background:#fff; }
        .hmi-workflow-step { min-height:64px; border:0; border-right:1px solid var(--hmi-line); border-radius:0; box-shadow:none; background:#fff; }
        .hmi-workflow-step:last-child { border-right:0; }
        .hmi-workflow-index { border-radius:4px; background:#edf4f6; }
        .hmi-state { border-radius:9px; }
        .hmi-demo {
          border:1px solid #d4e0e5; border-radius:6px; padding:.55rem .75rem;
          background:#eef3f5; color:#405968; box-shadow:none; font-size:.76rem;
        }
        .hmi-sidebar-status { border-radius:7px; background:rgba(255,255,255,.035); }
        [data-testid="stMain"] [role="radiogroup"],
        [data-testid="stMain"] div[data-baseweb="tab-list"] { border-radius:8px; background:#e8edef; }
        [data-testid="stMain"] button[data-baseweb="tab"],
        [data-testid="stMain"] [role="radiogroup"] label { border-radius:6px; }

        /* Readability pass for Chinese-language enterprise use. */
        html, body, [class*="css"] { font-size:17px; }
        .block-container { max-width:1430px; }
        h1 { font-size:2.12rem !important; line-height:1.2 !important; }
        h2 { font-size:1.38rem !important; }
        h3 { font-size:1.12rem !important; }
        p, li, label { font-size:1rem; }
        [data-testid="stSidebar"] [role="radiogroup"] label { font-size:1rem; padding:.66rem .76rem; }
        [data-testid="stSidebar"] .stCaption { font-size:.86rem !important; }
        .hmi-brand-title { font-size:1.12rem; }
        .hmi-brand-subtitle { font-size:.88rem; line-height:1.55; }
        .hmi-eyebrow { font-size:.74rem; }
        .hmi-subtitle { font-size:1rem; line-height:1.6; }
        .hmi-section span { font-size:.9rem; }
        .hmi-kpi-label { font-size:.86rem; }
        .hmi-kpi-value { font-size:1.78rem; }
        .hmi-kpi-note, .hmi-progress-note, .hmi-signal-meta, .hmi-card-meta { font-size:.88rem; }
        .hmi-priority-label { font-size:.82rem; }
        .hmi-priority-body, .hmi-workflow-step, .hmi-context-item { font-size:.9rem; }
        .hmi-progress-label, .hmi-progress-value { font-size:.94rem; }
        .hmi-signal-title, .hmi-card-title { font-size:1.02rem; }
        .hmi-signal-body, .hmi-card-body, .hmi-state-body { font-size:.98rem; }
        .hmi-badge { font-size:.76rem; }
        .hmi-demo { font-size:.9rem; }
        .stButton > button, .stDownloadButton > button { font-size:.96rem; }
        [data-testid="stDataFrame"], [data-testid="stTable"] { font-size:.94rem; }
        [data-testid="stMain"] input,
        [data-testid="stMain"] textarea,
        [data-testid="stMain"] [role="combobox"] { font-size:.96rem !important; }
        [data-testid="stMain"] input::placeholder,
        [data-testid="stMain"] textarea::placeholder { color:#778894; opacity:1; }
        [data-testid="stMain"] button:focus-visible,
        [data-testid="stMain"] input:focus-visible,
        [data-testid="stMain"] textarea:focus-visible,
        [data-testid="stMain"] [role="combobox"]:focus-visible,
        [data-testid="stSidebar"] label:has(input:focus-visible) {
          outline:3px solid rgba(11,117,149,.28) !important;
          outline-offset:2px;
        }
        [data-testid="stMain"] div[data-baseweb="tab-list"] {
          max-width:100%; overflow-x:auto; scrollbar-width:thin;
        }
        [data-testid="stMain"] button[data-baseweb="tab"] { white-space:nowrap; }
        [data-testid="stMain"] [data-testid="stCaptionContainer"] { color:#526572; }
        [data-testid="stMain"] [data-testid="stAlert"] { border:1px solid rgba(96,113,127,.18); }
        [data-testid="stMain"] [data-testid="stDataFrame"] { min-height:120px; }
        ::selection { background:#cdebf1; color:var(--hmi-navy); }
        @media (max-width: 900px) {
          .block-container { padding-left:1rem; padding-right:1rem; }
          .hmi-page-hero { padding:.35rem 0 .9rem; border-radius:0; }
          .hmi-page-hero::after { display:none; }
          .hmi-kpi { min-height:96px; }
          .hmi-kpi-value { font-size:1.45rem; }
          .hmi-workflow { grid-template-columns:1fr 1fr; }
          .hmi-section { align-items:flex-start; flex-direction:column; gap:.15rem; }
          .hmi-context { width:100%; flex-direction:column; align-items:stretch; }
          .hmi-context-item { border-right:0; border-bottom:1px solid var(--hmi-line); }
          .hmi-context-item:last-child { border-bottom:0; }
        }
        @media (max-width: 560px) {
          html, body, [class*="css"] { font-size:16px; }
          h1 { font-size:1.72rem !important; }
          .hmi-workflow { grid-template-columns:1fr; }
          .hmi-workflow-step { border-right:0; border-bottom:1px solid var(--hmi-line); }
          .hmi-workflow-step:last-child { border-bottom:0; }
        }
        @media (prefers-reduced-motion: reduce) {
          *, *::before, *::after { scroll-behavior:auto !important; transition:none !important; animation:none !important; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(eyebrow: str, title: str, subtitle: str) -> None:
    st.markdown(
        '<section class="hmi-page-hero">'
        f'<div class="hmi-eyebrow">{escape(eyebrow)}</div>'
        f'<h1>{escape(title)}</h1>'
        f'<div class="hmi-subtitle">{escape(subtitle)}</div>'
        '</section>',
        unsafe_allow_html=True,
    )


def section_header(title: str, context: str = "") -> None:
    suffix = f"<span>{escape(context)}</span>" if context else ""
    st.markdown(
        f'<div class="hmi-section"><h2>{escape(title)}</h2>{suffix}</div>',
        unsafe_allow_html=True,
    )


def status_badge(label: str) -> str:
    raw = str(label or "Unknown")
    shown = STATUS_LABELS_ZH.get(raw.upper(), raw.replace("_", " "))
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


def workspace_context(*items: tuple[str, Any]) -> None:
    """Render compact source, scope, and freshness context."""
    content = "".join(
        f'<span class="hmi-context-item">{escape(str(label))}: <strong>{escape(str(value))}</strong></span>'
        for label, value in items
    )
    st.markdown(f'<div class="hmi-context">{content}</div>', unsafe_allow_html=True)


def priority_card(label: str, value: Any, body: str, tone: str = "info") -> None:
    safe_tone = tone if tone in {"info", "danger", "warning", "success"} else "info"
    st.markdown(
        f'<div class="hmi-priority hmi-priority-{safe_tone}">'
        f'<div class="hmi-priority-label">{escape(label)}</div>'
        f'<div class="hmi-priority-value">{escape(str(value))}</div>'
        f'<div class="hmi-priority-body">{escape(body)}</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def progress_card(label: str, percent: float, note: str = "") -> None:
    value = max(0.0, min(100.0, float(percent)))
    shown = f"{value:.0f}%"
    st.markdown(
        '<div class="hmi-progress">'
        f'<div class="hmi-progress-head"><span class="hmi-progress-label">{escape(label)}</span>'
        f'<span class="hmi-progress-value">{shown}</span></div>'
        f'<div class="hmi-progress-track"><div class="hmi-progress-fill" style="width:{value:.3f}%"></div></div>'
        f'<div class="hmi-progress-note">{escape(note)}</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def signal_card(title: str, body: str, meta: str, importance: str = "MEDIUM") -> None:
    badge = status_badge(importance)
    st.markdown(
        '<div class="hmi-signal">'
        f'<div class="hmi-signal-head"><div class="hmi-signal-title">{escape(title)}</div>{badge}</div>'
        f'<div class="hmi-signal-meta">{escape(meta)}</div>'
        f'<div class="hmi-signal-body">{escape(body)}</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def workflow_steps(steps: list[tuple[str, str]]) -> None:
    content = "".join(
        f'<div class="hmi-workflow-step"><span class="hmi-workflow-index">{index}</span>'
        f'<strong>{escape(title)}</strong>{escape(body)}</div>'
        for index, (title, body) in enumerate(steps, start=1)
    )
    st.markdown(f'<div class="hmi-workflow">{content}</div>', unsafe_allow_html=True)


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
    action = f" 下一步：{next_step}" if next_step else ""
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
        with st.expander("技术详情", expanded=False):
            st.code(detail, language="text")


def demo_banner() -> None:
    st.markdown(
        '<div class="hmi-demo"><strong>评估工作区</strong> · 仅使用模拟记录 · '
        '不可用于外部市场判断或采购决策。</div>',
        unsafe_allow_html=True,
    )
