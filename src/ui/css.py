"""Global CSS — single source of truth for the design system."""

import streamlit as st


GLOBAL_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&family=Outfit:wght@300;400;500;600;700;800&display=swap');

    /* Capitalize page names in the sidebar */
    div[data-testid="stSidebarNav"] span,
    span[data-testid="stSidebarNavLinkText"],
    [data-testid="stSidebarNavLink"] span,
    .e1dbuyne5 span,
    .e1dbuyne8 span,
    a[href$="/app"] span {
        text-transform: capitalize !important;
        text-transform: capitalize !important;
    }

    :root {
        --bg-primary: #060813;
        --bg-secondary: #0a0e1a;
        --bg-glass: rgba(10, 14, 26, 0.72);
        --border-glass: rgba(99, 102, 241, 0.18);
        --accent-primary: #818cf8;
        --accent-secondary: #6366f1;
        --accent-glow: rgba(99, 102, 241, 0.35);
        --accent-neon: #a5b4fc;
        --text-primary: #f1f5f9;
        --text-secondary: #94a3b8;
        --text-muted: #64748b;
        --success: #10b981;
        --warning: #f59e0b;
        --danger: #ef4444;
        --radius-sm: 8px;
        --radius-md: 12px;
        --radius-lg: 16px;
        --radius-xl: 20px;
        --radius-full: 9999px;
    }

    html, body, [class*="css"], .stApp {
        font-family: 'Space Grotesk', 'Outfit', sans-serif !important;
    }

    .stApp::before {
        content: '';
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background:
            radial-gradient(ellipse 80% 50% at 20% 20%, rgba(99, 102, 241, 0.08) 0%, transparent 60%),
            radial-gradient(ellipse 60% 40% at 80% 80%, rgba(139, 92, 246, 0.06) 0%, transparent 50%),
            radial-gradient(ellipse 50% 50% at 50% 50%, rgba(14, 165, 233, 0.04) 0%, transparent 60%);
        animation: bgShift 20s ease-in-out infinite;
        z-index: -1;
        pointer-events: none;
    }
    @keyframes bgShift { 0%, 100% { opacity: 1; } 50% { opacity: 0.7; } }

    div[data-testid="stHeader"] {
        background-color: rgba(6, 8, 19, 0.6) !important;
        backdrop-filter: blur(20px) saturate(180%) !important;
        border-bottom: 1px solid rgba(99, 102, 241, 0.1) !important;
    }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #04050b 0%, #080c18 50%, #0a0e1a 100%) !important;
        border-right: 1px solid rgba(99, 102, 241, 0.15) !important;
        box-shadow: 5px 0 40px rgba(0, 0, 0, 0.5) !important;
    }
    section[data-testid="stSidebar"] .stMarkdown h3 {
        font-weight: 700 !important; letter-spacing: -0.02em; color: #f1f5f9 !important;
        margin-top: 1.5rem !important; border-left: 3px solid var(--accent-primary);
        padding-left: 0.6rem !important; font-size: 0.95rem !important;
    }

    .stTextInput input, .stSelectbox div[data-baseweb="select"], .stNumberInput input, .stTextArea textarea {
        background-color: rgba(13, 17, 33, 0.75) !important;
        border: 1px solid rgba(99, 102, 241, 0.18) !important;
        border-radius: var(--radius-md) !important; color: var(--text-primary) !important;
        font-weight: 500 !important; font-family: 'Space Grotesk', sans-serif !important;
        padding: 0.55rem 0.9rem !important;
        transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1) !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15) !important;
    }
    .stTextInput input:focus, .stSelectbox div[data-baseweb="select"]:focus-within,
    .stNumberInput input:focus, .stTextArea textarea:focus {
        border-color: var(--accent-primary) !important;
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15), 0 0 20px rgba(99, 102, 241, 0.1) !important;
    }

    ul[data-baseweb="menu"] {
        background-color: #0f172a !important;
        border: 1px solid rgba(99, 102, 241, 0.25) !important;
        border-radius: var(--radius-md) !important;
        box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5) !important;
    }
    li[role="option"] { color: #e2e8f0 !important; font-family: 'Space Grotesk', sans-serif !important; }
    li[role="option"]:hover { background-color: rgba(99, 102, 241, 0.15) !important; }

    div[data-role="tablist"] {
        border-bottom: 1px solid rgba(255, 255, 255, 0.04) !important;
        gap: 0.35rem !important; padding: 0.3rem !important;
        background: rgba(10, 14, 26, 0.5) !important;
        border-radius: var(--radius-lg) var(--radius-lg) 0 0 !important;
    }
    button[data-baseweb="tab"] {
        font-family: 'Space Grotesk', sans-serif !important;
        font-size: 0.88rem !important; font-weight: 600 !important;
        color: var(--text-muted) !important; background-color: transparent !important;
        border: none !important; padding: 0.7rem 1.3rem !important;
        border-radius: var(--radius-md) !important;
        transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1) !important;
        margin-bottom: 0 !important; letter-spacing: 0.01em !important;
    }
    button[data-baseweb="tab"]:hover { color: #cbd5e1 !important; background-color: rgba(99, 102, 241, 0.08) !important; }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #fff !important;
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.2) 0%, rgba(139, 92, 246, 0.12) 100%) !important;
        border: 1px solid rgba(99, 102, 241, 0.3) !important;
        box-shadow: 0 4px 15px rgba(99, 102, 241, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.06) !important;
    }

    div[data-testid="stMetricValue"] {
        font-weight: 800 !important; font-size: 2rem !important; letter-spacing: -0.03em !important;
        background: linear-gradient(135deg, #ffffff 0%, #a5b4fc 100%) !important;
        -webkit-background-clip: text !important; -webkit-text-fill-color: transparent !important;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.72rem !important; text-transform: uppercase !important;
        letter-spacing: 0.08em !important; color: var(--text-muted) !important; font-weight: 600 !important;
    }
    div[data-testid="metric-container"] {
        background: rgba(13, 17, 33, 0.6) !important;
        border: 1px solid rgba(99, 102, 241, 0.12) !important;
        border-radius: var(--radius-lg) !important; padding: 1.2rem 1.5rem !important;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2) !important;
        backdrop-filter: blur(12px) !important; transition: all 0.3s ease !important;
    }
    div[data-testid="metric-container"]:hover { border-color: rgba(99, 102, 241, 0.3) !important; transform: translateY(-2px) !important; }

    .doc-card {
        background: rgba(13, 17, 33, 0.65); backdrop-filter: blur(16px) saturate(150%);
        border: 1px solid rgba(99, 102, 241, 0.15); border-radius: var(--radius-lg);
        padding: 1.4rem 1.8rem; margin-bottom: 1.2rem;
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.25);
        transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1); color: var(--text-primary);
        position: relative; overflow: hidden;
    }
    .doc-card::before {
        content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px;
        background: linear-gradient(90deg, transparent, rgba(99, 102, 241, 0.4), transparent);
    }
    .doc-card:hover { transform: translateY(-4px) scale(1.005); border-color: rgba(99, 102, 241, 0.45); box-shadow: 0 20px 60px rgba(99, 102, 241, 0.12); }

    .citation-card {
        background: rgba(10, 12, 22, 0.75); backdrop-filter: blur(12px);
        border: 1px solid rgba(99, 102, 241, 0.18); border-left: 3px solid var(--accent-primary);
        border-radius: var(--radius-md); padding: 1.1rem 1.4rem; margin-bottom: 0.85rem;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15); transition: all 0.3s ease;
    }
    .citation-card:hover { border-left-color: var(--accent-neon); box-shadow: 0 8px 25px rgba(99, 102, 241, 0.1); }
    .citation-card .cite-header { font-size: 0.82rem; color: var(--accent-primary); font-weight: 600; margin-bottom: 0.5rem; display: flex; justify-content: space-between; }
    .citation-card .cite-text { font-size: 0.88rem; color: var(--text-secondary); line-height: 1.65; }

    .keypoints-box { background: rgba(16, 185, 129, 0.04); border: 1px solid rgba(16, 185, 129, 0.2); border-radius: var(--radius-md); padding: 1rem 1.4rem; margin-top: 1rem; }
    .keypoints-box ul { margin: 0; padding-left: 1.2rem; }
    .keypoints-box li { color: #a7f3d0; font-size: 0.9rem; line-height: 1.7; }

    .badge { display: inline-flex; align-items: center; gap: 0.3rem; padding: 0.3rem 0.75rem; border-radius: var(--radius-full); font-size: 0.72rem; font-weight: 600; margin-right: 0.4rem; margin-bottom: 0.4rem; border: 1px solid rgba(255, 255, 255, 0.06); letter-spacing: 0.03em; transition: all 0.2s ease; }
    .badge:hover { transform: scale(1.05); }
    .badge-blue   { background: rgba(59,130,246,0.12)!important; color: #93c5fd!important; border-color: rgba(59,130,246,0.25)!important; }
    .badge-green  { background: rgba(16,185,129,0.12)!important; color: #6ee7b7!important; border-color: rgba(16,185,129,0.25)!important; }
    .badge-purple { background: rgba(139,92,246,0.12)!important; color: #c4b5fd!important; border-color: rgba(139,92,246,0.25)!important; }
    .badge-yellow { background: rgba(245,158,11,0.12)!important; color: #fde047!important; border-color: rgba(245,158,11,0.25)!important; }
    .badge-red    { background: rgba(239,68,68,0.12)!important; color: #fca5a5!important; border-color: rgba(239,68,68,0.25)!important; }
    .badge-gray   { background: rgba(107,114,128,0.12)!important;color: #d1d5db!important; border-color: rgba(107,114,128,0.25)!important; }
    .badge-teal   { background: rgba(6,182,212,0.12)!important;  color: #67e8f9!important; border-color: rgba(6,182,212,0.25)!important; }

    .chat-bubble { border-radius: var(--radius-xl) !important; padding: 1.3rem 1.8rem !important; margin-bottom: 1.2rem !important; font-size: 0.95rem; line-height: 1.7; animation: fadeSlideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1); }
    @keyframes fadeSlideUp { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
    .chat-user { background: linear-gradient(135deg, rgba(30,41,59,0.5) 0%, rgba(15,23,42,0.7) 100%) !important; border: 1px solid rgba(99, 102, 241, 0.15) !important; border-left: 3px solid var(--accent-secondary) !important; color: var(--text-primary); }
    .chat-assistant { background: linear-gradient(135deg, rgba(79,70,229,0.06) 0%, rgba(10,12,22,0.88) 100%) !important; border: 1px solid rgba(99, 102, 241, 0.18) !important; border-left: 3px solid var(--accent-primary) !important; color: var(--text-primary); }

    section[data-testid="stFileUploader"] { background-color: rgba(13, 17, 33, 0.5) !important; border: 2px dashed rgba(99, 102, 241, 0.25) !important; border-radius: var(--radius-lg) !important; padding: 1.8rem !important; }
    section[data-testid="stFileUploader"]:hover { border-color: rgba(99, 102, 241, 0.6) !important; background-color: rgba(15, 23, 42, 0.7) !important; }

    ::-webkit-scrollbar { width: 5px; height: 5px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(156, 163, 175, 0.2); border-radius: var(--radius-full); }

    div.stButton > button {
        background: linear-gradient(135deg, #4f46e5 0%, #6366f1 50%, #7c3aed 100%) !important;
        color: white !important; border: 1px solid rgba(99, 102, 241, 0.3) !important;
        border-radius: var(--radius-md) !important; font-weight: 600 !important;
        font-size: 0.88rem !important; font-family: 'Space Grotesk', sans-serif !important;
        padding: 0.6rem 1.5rem !important;
        transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1) !important;
        box-shadow: 0 4px 15px rgba(79, 70, 229, 0.25) !important;
        position: relative; overflow: hidden;
    }
    div.stButton > button::before { content: ''; position: absolute; top: 0; left: -100%; width: 100%; height: 100%; background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent); transition: left 0.5s ease; }
    div.stButton > button:hover { transform: translateY(-2px) !important; box-shadow: 0 8px 30px rgba(79, 70, 229, 0.4) !important; }
    div.stButton > button:hover::before { left: 100%; }
    div.stButton > button:active { transform: translateY(0) scale(0.98) !important; }

    div.stDownloadButton > button { background: rgba(30, 41, 59, 0.7) !important; color: #e2e8f0 !important; border: 1px solid rgba(99, 102, 241, 0.2) !important; border-radius: var(--radius-md) !important; }
    div.stDownloadButton > button:hover { background: rgba(99, 102, 241, 0.15) !important; }

    div[data-testid="stProgress"] > div > div { background: linear-gradient(90deg, #4f46e5, #818cf8, #a78bfa) !important; border-radius: var(--radius-full) !important; }

    details { background: rgba(13, 17, 33, 0.5) !important; border: 1px solid rgba(99, 102, 241, 0.12) !important; border-radius: var(--radius-md) !important; margin-bottom: 0.8rem !important; }
    details:hover { border-color: rgba(99, 102, 241, 0.25) !important; }
    details summary { font-weight: 600 !important; color: var(--text-primary) !important; }

    .llm-pill-on { background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: var(--radius-md); padding: 0.6rem 1rem; color: #6ee7b7; font-size: 0.82rem; animation: statusPulse 3s ease-in-out infinite; }
    @keyframes statusPulse { 0%, 100% { box-shadow: 0 4px 15px rgba(16, 185, 129, 0.06); } 50% { box-shadow: 0 4px 25px rgba(16, 185, 129, 0.15); } }
    .llm-pill-off { background: rgba(245, 158, 11, 0.08); border: 1px solid rgba(245, 158, 11, 0.25); border-radius: var(--radius-md); padding: 0.6rem 1rem; color: #fde047; font-size: 0.82rem; }

    .sidebar-brand { text-align: center; margin-bottom: 1.5rem; padding: 1.4rem 1.2rem; background: linear-gradient(135deg, rgba(99, 102, 241, 0.08) 0%, rgba(139, 92, 246, 0.05) 50%, rgba(17, 24, 39, 0.8) 100%); border-radius: var(--radius-lg); border: 1px solid rgba(99, 102, 241, 0.2); position: relative; overflow: hidden; }
    .sidebar-brand::before { content: ''; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%; background: conic-gradient(from 0deg, transparent, rgba(99, 102, 241, 0.06), transparent, rgba(139, 92, 246, 0.04), transparent); animation: rotateBg 12s linear infinite; }
    @keyframes rotateBg { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
    .sidebar-brand > * { position: relative; z-index: 1; }

    .version-badge { display: inline-flex; align-items: center; gap: 0.4rem; background: linear-gradient(135deg, rgba(245, 158, 11, 0.12) 0%, rgba(239, 68, 68, 0.08) 100%); border: 1px solid rgba(245, 158, 11, 0.25); border-radius: var(--radius-full); padding: 0.25rem 0.7rem; font-size: 0.68rem; font-weight: 700; color: #fcd34d; letter-spacing: 0.05em; text-transform: uppercase; animation: badgeGlow 4s ease-in-out infinite; }
    @keyframes badgeGlow { 0%, 100% { box-shadow: 0 0 8px rgba(245, 158, 11, 0.1); } 50% { box-shadow: 0 0 16px rgba(245, 158, 11, 0.2); } }

    .gradient-divider { height: 1px; background: linear-gradient(90deg, transparent, rgba(99, 102, 241, 0.3), transparent); margin: 1.5rem 0; border: none; }

    .stat-counter-card { background: rgba(13, 17, 33, 0.6); border: 1px solid rgba(99, 102, 241, 0.12); border-radius: var(--radius-lg); padding: 1rem; text-align: center; transition: all 0.3s ease; backdrop-filter: blur(8px); }
    .stat-counter-card:hover { border-color: rgba(99, 102, 241, 0.3); transform: translateY(-2px); }

    .entity-card { background: rgba(13, 17, 33, 0.65); backdrop-filter: blur(16px); border: 1px solid rgba(99, 102, 241, 0.15); border-left: 3px solid var(--accent-primary); border-radius: var(--radius-lg); padding: 1.25rem 1.5rem; margin-bottom: 1rem; box-shadow: 0 12px 40px rgba(0, 0, 0, 0.2); transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1); color: var(--text-primary); position: relative; overflow: hidden; }
    .entity-card:hover { transform: translateY(-3px) scale(1.005); border-color: rgba(99, 102, 241, 0.45); }

    .stat-chip { display: inline-flex; align-items: center; gap: 0.45rem; background: rgba(30, 41, 59, 0.6); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: var(--radius-full); padding: 0.35rem 0.8rem; font-size: 0.8rem; font-weight: 600; color: var(--text-secondary); transition: all 0.25s ease; }
    .stat-chip:hover { background: rgba(99, 102, 241, 0.12); color: var(--text-primary); transform: scale(1.03); }
    .stat-chip .dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; box-shadow: 0 0 8px currentColor; }

    .neighbor-row { padding: 0.65rem 0.85rem; border-radius: var(--radius-md); margin-bottom: 0.4rem; font-size: 0.85rem; display: flex; align-items: center; gap: 0.6rem; background: rgba(30, 41, 59, 0.3); border: 1px solid rgba(255, 255, 255, 0.04); transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1); color: var(--text-secondary); }
    .neighbor-row:hover { background: rgba(99, 102, 241, 0.1); border-color: rgba(99, 102, 241, 0.25); transform: translateX(4px); }
    .neighbor-row .n-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; box-shadow: 0 0 8px currentColor; }
    .neighbor-row .n-relation { color: var(--text-muted); font-size: 0.72rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-left: auto; background: rgba(30, 41, 59, 0.8); padding: 0.15rem 0.5rem; border-radius: var(--radius-sm); }

    .stats-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.6rem; margin-bottom: 1rem; }
    .stats-card { background: rgba(13, 17, 33, 0.6); backdrop-filter: blur(10px); border: 1px solid rgba(99, 102, 241, 0.12); border-radius: var(--radius-md); padding: 0.75rem 1rem; text-align: center; }
    .stats-card:hover { border-color: rgba(99, 102, 241, 0.3); transform: translateY(-2px); }
    .stats-card .stats-value { font-size: 1.35rem; font-weight: 800; background: linear-gradient(135deg, #a5b4fc 0%, #818cf8 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .stats-card .stats-label { font-size: 0.68rem; color: var(--text-muted); margin-top: 0.2rem; text-transform: uppercase; letter-spacing: 0.06em; font-weight: 600; }

    .path-result { background: rgba(16, 185, 129, 0.04); border: 1px solid rgba(16, 185, 129, 0.2); border-radius: var(--radius-md); padding: 1rem 1.25rem; margin-top: 0.75rem; }
    .path-node { display: inline-flex; align-items: center; gap: 0.3rem; background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: var(--radius-sm); padding: 0.25rem 0.65rem; font-size: 0.82rem; font-weight: 600; color: var(--text-secondary); }
    .path-arrow { color: var(--accent-primary); font-size: 1.1rem; margin: 0 0.2rem; }

    .pipe-row { display: flex; flex-wrap: wrap; align-items: center; gap: 0.35rem; margin: 0.6rem 0 0.9rem 0; font-family: 'JetBrains Mono', monospace; }
    .pipe-step { padding: 0.28rem 0.6rem; border-radius: 6px; font-size: 0.7rem; font-weight: 600; letter-spacing: 0.02em; border: 1px solid rgba(255, 255, 255, 0.08); background: rgba(13, 17, 33, 0.7); color: #94a3b8; white-space: nowrap; }
    .pipe-step.pipe-done { color: #6ee7b7; border-color: rgba(16, 185, 129, 0.35); background: rgba(16, 185, 129, 0.07); }
    .pipe-step.pipe-hit { color: #fde047; border-color: rgba(245, 158, 11, 0.4); background: rgba(245, 158, 11, 0.08); }
    .pipe-step.pipe-warn { color: #fca5a5; border-color: rgba(239, 68, 68, 0.3); background: rgba(239, 68, 68, 0.06); }
    .pipe-step.pipe-skip { color: #64748b; border-color: rgba(107, 114, 128, 0.25); background: rgba(107, 114, 128, 0.05); }
    .pipe-arrow { color: #475569; font-size: 0.7rem; }

    .breadcrumb-trail { display: flex; flex-wrap: wrap; gap: 0.3rem; margin-bottom: 1rem; padding: 0.5rem 0.8rem; background: rgba(13, 17, 33, 0.5); border-radius: var(--radius-md); border: 1px solid rgba(255, 255, 255, 0.04); }
    .breadcrumb-item { font-size: 0.76rem; color: var(--text-muted); cursor: pointer; }
    .breadcrumb-item:hover { color: var(--accent-primary); }

    .bench-pass { color: #34d399 !important; font-weight: 700; }
    .bench-fail { color: #f87171 !important; font-weight: 700; }

    code { font-family: 'JetBrains Mono', monospace !important; font-size: 0.85em !important; background: rgba(99, 102, 241, 0.08) !important; color: var(--accent-neon) !important; padding: 0.15em 0.4em !important; border-radius: 4px !important; border: 1px solid rgba(99, 102, 241, 0.12) !important; }

    [data-testid="stSpinner"] > div { border-top-color: var(--accent-primary) !important; }

    .stCheckbox label { font-family: 'Space Grotesk', sans-serif !important; font-weight: 500 !important; font-size: 0.85rem !important; color: var(--text-secondary) !important; }

    .main .block-container { padding-top: 1.5rem !important; padding-bottom: 3rem !important; max-width: 100% !important; }

    @keyframes gradientSlide { 0% { background-position: -200% 0; } 100% { background-position: 200% 0; } }

    /* ═══ PREMIUM ANIMATIONS & MICRO-INTERACTIONS ═══ */

    /* ── Page Load Fade-In ── */
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
    @keyframes slideInLeft {
        from { opacity: 0; transform: translateX(-20px); }
        to { opacity: 1; transform: translateX(0); }
    }
    @keyframes slideInRight {
        from { opacity: 0; transform: translateX(20px); }
        to { opacity: 1; transform: translateX(0); }
    }
    @keyframes scaleIn {
        from { opacity: 0; transform: scale(0.95); }
        to { opacity: 1; transform: scale(1); }
    }

    .stApp > div > div > div { animation: fadeIn 0.6s ease-out; }
    section[data-testid="stSidebar"] > div { animation: slideInLeft 0.4s cubic-bezier(0.16, 1, 0.3, 1); }

    /* ── Button Ripple Effect ── */
    div.stButton > button {
        position: relative; overflow: hidden;
    }
    div.stButton > button::after {
        content: '';
        position: absolute;
        top: 50%; left: 50%;
        width: 0; height: 0;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.15);
        transform: translate(-50%, -50%);
        transition: width 0.6s ease, height 0.6s ease, opacity 0.6s ease;
        opacity: 0;
    }
    div.stButton > button:active::after {
        width: 300px; height: 300px;
        opacity: 0;
        transition: 0s;
    }

    /* ── Typing Indicator ── */
    .typing-indicator {
        display: inline-flex; align-items: center; gap: 0.4rem;
        padding: 0.8rem 1.2rem;
        background: rgba(99, 102, 241, 0.06);
        border: 1px solid rgba(99, 102, 241, 0.15);
        border-radius: var(--radius-lg);
        margin-bottom: 1rem;
    }
    .typing-dot {
        width: 8px; height: 8px;
        border-radius: 50%;
        background: var(--accent-primary);
        animation: typingBounce 1.4s ease-in-out infinite;
    }
    .typing-dot:nth-child(2) { animation-delay: 0.2s; }
    .typing-dot:nth-child(3) { animation-delay: 0.4s; }
    @keyframes typingBounce {
        0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
        30% { transform: translateY(-8px); opacity: 1; }
    }

    /* ── Skeleton Loading ── */
    .skeleton {
        background: linear-gradient(90deg, rgba(99, 102, 241, 0.06) 25%, rgba(99, 102, 241, 0.12) 50%, rgba(99, 102, 241, 0.06) 75%);
        background-size: 200% 100%;
        animation: skeletonShimmer 1.5s ease-in-out infinite;
        border-radius: var(--radius-md);
        min-height: 20px;
    }
    @keyframes skeletonShimmer {
        0% { background-position: 200% 0; }
        100% { background-position: -200% 0; }
    }
    .skeleton-line { height: 14px; margin-bottom: 0.5rem; }
    .skeleton-line:last-child { width: 60%; }
    .skeleton-circle { width: 40px; height: 40px; border-radius: 50%; }

    /* ── Neon Glow Pulse ── */
    .neon-glow {
        animation: neonPulse 2s ease-in-out infinite;
    }
    @keyframes neonPulse {
        0%, 100% { box-shadow: 0 0 5px rgba(99, 102, 241, 0.2), 0 0 10px rgba(99, 102, 241, 0.1); }
        50% { box-shadow: 0 0 10px rgba(99, 102, 241, 0.4), 0 0 20px rgba(99, 102, 241, 0.2), 0 0 30px rgba(99, 102, 241, 0.1); }
    }

    /* ── Stat Counter Animation ── */
    .stat-counter-animated .stats-value {
        animation: countFadeIn 0.8s ease-out;
    }
    @keyframes countFadeIn {
        from { opacity: 0; transform: scale(0.8); }
        to { opacity: 1; transform: scale(1); }
    }

    /* ── Card Hover Glow ── */
    .entity-card::after, .doc-card::after, .citation-card::after {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        border-radius: inherit;
        opacity: 0;
        transition: opacity 0.4s ease;
        pointer-events: none;
    }
    .entity-card:hover::after {
        background: radial-gradient(circle at var(--mouse-x, 50%) var(--mouse-y, 50%), rgba(99, 102, 241, 0.08) 0%, transparent 60%);
        opacity: 1;
    }
    .doc-card:hover::after {
        background: radial-gradient(circle at var(--mouse-x, 50%) var(--mouse-y, 50%), rgba(99, 102, 241, 0.06) 0%, transparent 60%);
        opacity: 1;
    }

    /* ── Smooth Scroll ── */
    html { scroll-behavior: smooth; }

    /* ── Tab Transition ── */
    div[data-baseweb="tab-panel"] {
        animation: fadeInUp 0.3s ease-out;
    }

    /* ── Badge Hover Effects ── */
    .badge {
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .badge:hover {
        transform: translateY(-1px) scale(1.05);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }

    /* ── Neighbor Row Slide ── */
    .neighbor-row {
        animation: fadeInUp 0.3s ease-out backwards;
    }
    .neighbor-row:nth-child(1) { animation-delay: 0.05s; }
    .neighbor-row:nth-child(2) { animation-delay: 0.1s; }
    .neighbor-row:nth-child(3) { animation-delay: 0.15s; }
    .neighbor-row:nth-child(4) { animation-delay: 0.2s; }
    .neighbor-row:nth-child(5) { animation-delay: 0.25s; }

    /* ── Success/Error Flash ── */
    @keyframes successFlash {
        0% { background-color: rgba(16, 185, 129, 0.1); }
        100% { background-color: transparent; }
    }
    @keyframes errorFlash {
        0% { background-color: rgba(239, 68, 68, 0.1); }
        100% { background-color: transparent; }
    }
    .stAlert[data-testid="stAlert"] {
        animation: fadeInUp 0.3s ease-out;
    }

    /* ── Progress Bar Glow ── */
    div[data-testid="stProgress"] > div > div {
        box-shadow: 0 0 10px rgba(99, 102, 241, 0.4);
    }

    /* ── Sidebar Item Hover ── */
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] .stMarkdown li {
        transition: color 0.2s ease, transform 0.2s ease;
    }
    section[data-testid="stSidebar"] .stMarkdown p:hover,
    section[data-testid="stSidebar"] .stMarkdown li:hover {
        color: var(--text-primary) !important;
        transform: translateX(2px);
    }

    /* ── Metric Container Glow on Hover ── */
    div[data-testid="metric-container"]:hover {
        box-shadow: 0 12px 40px rgba(99, 102, 241, 0.08), 0 0 20px rgba(99, 102, 241, 0.05) !important;
    }

    /* ── File Uploader Drag Animation ── */
    section[data-testid="stFileUploader"]:hover {
        animation: scaleIn 0.2s ease-out;
    }

    /* ── Expander Smooth Transition ── */
    details > summary {
        transition: all 0.3s ease;
        cursor: pointer;
    }
    details > summary:hover {
        color: var(--accent-neon) !important;
    }
    details[open] > summary {
        border-bottom: 1px solid rgba(99, 102, 241, 0.1);
        padding-bottom: 0.5rem;
    }
</style>
"""


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS


def inject_global_css() -> None:
    """Inject the global CSS and SEO metadata into the Streamlit page."""
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
    
    # Inject SEO meta tags and OG tags dynamically via parent document manipulation
    seo_html = """
    <script>
    try {
        const p = window.parent.document;
        
        // 1. Meta Description
        let d = p.querySelector('meta[name="description"]');
        if (!d) {
            d = p.createElement('meta');
            d.setAttribute('name', 'description');
            p.head.appendChild(d);
        }
        d.setAttribute('content', 'Synapse — AI-powered knowledge intelligence combining RAG, Hybrid Search, and Knowledge Graphs for real-time regulatory intelligence.');

        // 2. Meta Keywords
        let k = p.querySelector('meta[name="keywords"]');
        if (!k) {
            k = p.createElement('meta');
            k.setAttribute('name', 'keywords');
            p.head.appendChild(k);
        }
        k.setAttribute('content', 'RAG, Industrial Intelligence, Safety Regulations, Knowledge Graph, Hybrid Search, BM25, ChromaDB, FastAPI, Streamlit');

        // 3. Open Graph Title
        let o = p.querySelector('meta[property="og:title"]');
        if (!o) {
            o = p.createElement('meta');
            o.setAttribute('property', 'og:title');
            p.head.appendChild(o);
        }
        o.setAttribute('content', 'Synapse — AI-Powered Knowledge Intelligence');
    } catch (e) {
        console.error('SEO injection failed:', e);
    }
    </script>
    """
    st.components.v1.html(seo_html, height=0, width=0)
