"""HTML component builders — hero, cards, chat, stats, and more."""

import html as html_mod
from src.ui.helpers import fmt_time
from src.ui.particles import particle_starfield


__all__ = [
    "hero_header", "sidebar_brand", "sidebar_footer", "section_header",
    "gradient_divider", "llm_status_pill", "entity_card_html", "neighbor_row_html",
    "doc_card_html", "citation_card", "keypoints_box", "chat_bubble", "stats_grid",
    "info_banner", "settings_section", "typing_indicator", "skeleton_loader",
    "skeleton_card", "neon_stat_card", "animated_counter_html", "glow_button",
    "particle_background_js", "pipeline_trace", "evidence_stats_row",
]



def hero_header(
    title: str, subtitle: str, badge_text: str = "v4.0",
    stats: list = None, extra_right: str = "", show_starfield: bool = True,
) -> None:
    """Render the cinematic hero header with optional embedded particle starfield."""
    import streamlit as st
    import streamlit.components.v1 as components
    import uuid

    stats_html = ""
    if stats:
        cards = "".join(
            f'<div class="stat-counter-card" style="flex:1;"><div style="font-size:1.5rem;font-weight:800;color:{s.get("color","#818cf8")};">{s["value"]}</div>'
            f'<div style="font-size:0.72rem;color:#64748b;text-transform:uppercase;letter-spacing:0.06em;">{s["label"]}</div></div>'
            for s in stats
        )
        stats_html = f'<div style="display:flex;gap:0.8rem;margin-top:1rem;">{cards}</div>'

    right_section = extra_right or (
        '<div class="stat-counter-card" style="min-width:80px;">'
        '<div style="font-size:1.3rem;font-weight:800;color:#818cf8;">Platform</div>'
        '<div style="font-size:0.68rem;color:#64748b;text-transform:uppercase;letter-spacing:0.06em;">Status</div></div>'
    )

    starfield_html = particle_starfield(f"hero-{uuid.uuid4().hex[:6]}") if show_starfield else ""

    hero_html = f"""
<div style="position:relative;padding:2rem 2.5rem;margin-bottom:2rem;
            background:linear-gradient(135deg,rgba(99,102,241,0.08) 0%,rgba(10,14,26,0.9) 40%,rgba(139,92,246,0.06) 100%);
            border:1px solid rgba(99,102,241,0.2); border-radius:20px;
            backdrop-filter:blur(20px) saturate(180%);
            box-shadow:0 20px 60px rgba(0,0,0,0.3),0 0 40px rgba(99,102,241,0.06);
            overflow:hidden;">

    {starfield_html}

    <div style="position:absolute;top:0;left:0;right:0;height:2px;z-index:1;
                background:linear-gradient(90deg,transparent,#818cf8,#a78bfa,#818cf8,transparent);
                animation:gradientSlide 4s linear infinite;"></div>

    <div style="position:absolute;top:-40px;right:60px;width:120px;height:120px;z-index:1;
                background:radial-gradient(circle,rgba(99,102,241,0.15) 0%,transparent 70%);
                border-radius:50%;filter:blur(30px);"></div>

    <div style="position:relative;z-index:2;display:flex;justify-content:space-between;align-items:center;">
        <div>
            <div style="display:flex;align-items:center;gap:0.8rem;margin-bottom:0.5rem;">
                <span class="version-badge">{badge_text}</span>
            </div>
            <h1 style="margin:0;font-size:2.2rem;font-weight:800;letter-spacing:-0.03em;
                        background:linear-gradient(135deg,#ffffff 0%,#c7d2fe 40%,#818cf8 100%);
                        -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                        font-family:'Space Grotesk',sans-serif;">
                {title}
            </h1>
            <p style="margin:0.4rem 0 0 0;font-size:0.95rem;color:#94a3b8;font-weight:500;">{subtitle}</p>
            {stats_html}
        </div>
        <div style="display:flex;gap:1.2rem;align-items:center;">{right_section}</div>
    </div>
</div>
"""
    components.html(hero_html, height=400, scrolling=False)


def sidebar_brand(name: str = "IND-KNOWLEDGE", badge: str = "", icon_url: str = "https://img.icons8.com/isometric-line/100/factory.png"):
    import streamlit as st
    badge_html = f'<div style="margin-top:0.4rem;"><span class="version-badge">{badge}</span></div>' if badge else ""
    st.markdown(f"""
<div class="sidebar-brand">
    <img src="{icon_url}" width="50" style="margin-bottom:0.6rem;filter:drop-shadow(0 0 12px rgba(99,102,241,0.4));">
    <h2 style="margin:0;font-size:1.15rem;font-weight:800;background:linear-gradient(90deg,#818cf8,#c7d2fe,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent;letter-spacing:-0.02em;">{name}</h2>
    {badge_html}
</div>
""", unsafe_allow_html=True)


def section_header(icon: str, title: str, subtitle: str = ""):
    import streamlit as st
    sub_html = f'<div style="font-size:0.82rem;color:#94a3b8;">{subtitle}</div>' if subtitle else ""
    st.markdown(f"""
<div style="display:flex;align-items:center;gap:0.6rem;margin-bottom:1rem;">
    <span style="font-size:1.4rem;">{icon}</span>
    <div><div style="font-size:1.1rem;font-weight:700;color:#f1f5f9;font-family:'Space Grotesk',sans-serif;">{title}</div>{sub_html}</div>
</div>
""", unsafe_allow_html=True)


def gradient_divider():
    import streamlit as st
    st.markdown('<div class="gradient-divider"></div>', unsafe_allow_html=True)


def sidebar_footer(text: str = "2026 Industrial Knowledge Engine", subtext: str = "Open Source RAG Platform"):
    import streamlit as st
    st.markdown(f'<div style="text-align:center;padding:0.8rem;font-size:0.68rem;color:#475569;">&copy; {text}<br><span style="color:#6366f1;">{subtext}</span></div>', unsafe_allow_html=True)


def llm_status_pill(model: str, available: bool, mode: str = "ollama"):
    import streamlit as st
    if available:
        label = {"nvidia": "NVIDIA API", "ollama": "Ollama"}.get(mode, mode)
        st.markdown(f'<div class="llm-pill-on">Connected &nbsp;|&nbsp; <b>{model}</b></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="llm-pill-off">Smart-Context fallback<br><small style="color:#94a3b8;">Set NVIDIA_API_KEY or start Ollama</small></div>', unsafe_allow_html=True)


def entity_card_html(entity_id: str, entity_type: str, color: str, degree: int) -> str:
    eid = html_mod.escape(str(entity_id))
    etype = html_mod.escape(entity_type.replace('_',' ').title())
    return f"""<div class="entity-card"><div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.5rem;"><span style="width:14px;height:14px;border-radius:50%;background:{color};display:inline-block;box-shadow:0 0 8px {color};"></span><strong style="font-size:1.1rem;">{eid}</strong></div><div style="display:flex;gap:0.5rem;flex-wrap:wrap;"><span class="stat-chip"><span class="dot" style="background:{color};"></span>{etype}</span><span class="stat-chip">{degree} connections</span></div></div>"""


def neighbor_row_html(nid: str, color: str, relation: str) -> str:
    nid_safe = html_mod.escape(str(nid))
    rel_safe = html_mod.escape(str(relation))
    return f"""<div class="neighbor-row"><span class="n-dot" style="background:{color};"></span><span><strong>{nid_safe}</strong></span><span class="n-relation">{rel_safe}</span></div>"""


def doc_card_html(filename: str, doc_type: str, chunk_count: int, upload_date: str, entities_found: int) -> str:
    fname_safe = html_mod.escape(str(filename))
    dtype_safe = html_mod.escape(str(doc_type.upper()))
    return f"""<div class="doc-card"><h4 style="margin:0;color:#c7d2fe;">{fname_safe}</h4><div style="margin-top:0.6rem;display:flex;flex-wrap:wrap;gap:0.4rem;"><span class="badge badge-purple">{dtype_safe}</span><span class="badge badge-blue">{chunk_count} chunks</span><span class="badge badge-gray">{fmt_time(upload_date)}</span><span class="badge badge-green">{entities_found} entities</span></div></div>"""


def citation_card(index: int, citation: str, distance: float, excerpt: str) -> str:
    score = round(1 - distance, 3)
    cite_safe = html_mod.escape(str(citation))
    exc_safe = html_mod.escape(str(excerpt[:350]))
    return f"""<div class="citation-card"><div class="cite-header">[{index}] <b>{cite_safe}</b> &nbsp;|&nbsp; relevance: {score}</div><div class="cite-text">{exc_safe}...</div></div>"""


def keypoints_box(key_points: list) -> str:
    bullets = "".join(f"<li>{html_mod.escape(str(p))}</li>" for p in key_points)
    return f"""<div class="keypoints-box"><b style="color:#a7f3d0">Key Points</b><ul>{bullets}</ul></div>"""


def chat_bubble(role: str, content: str, label: str = None) -> str:
    css_class = "chat-user" if role == "user" else "chat-assistant"
    label = label or ("You" if role == "user" else "System")
    safe_content = html_mod.escape(str(content))
    safe_label = html_mod.escape(str(label))
    return f"""<div class="chat-bubble {css_class}"><div style="font-size:0.72rem;color:#64748b;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.4rem;">{safe_label}</div>{safe_content}</div>"""


def stats_grid(stats: dict) -> str:
    cards = [("total_nodes","Total Nodes","#818cf8"),("total_edges","Total Edges","#a78bfa"),("avg_degree","Avg Connections","#6ee7b7"),("connected_components","Components","#f59e0b")]
    items = ""
    for key, label, color in cards:
        value = stats.get(key, 0)
        items += f'<div class="stats-card"><div class="stats-value" style="background:linear-gradient(135deg,{color},{color}cc);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">{value}</div><div class="stats-label">{label}</div></div>'
    return f'<div class="stats-grid">{items}</div>'


def info_banner(icon: str, title: str, description: str) -> str:
    t = html_mod.escape(str(title))
    d = html_mod.escape(str(description))
    return f"""<div style="display:flex;align-items:center;gap:0.6rem;margin-bottom:1rem;padding:0.8rem 1.2rem;background:rgba(99,102,241,0.04);border:1px solid rgba(99,102,241,0.1);border-radius:12px;"><span style="font-size:1.2rem;">{icon}</span><div><div style="font-size:0.95rem;font-weight:700;color:#f1f5f9;">{t}</div><div style="font-size:0.8rem;color:#94a3b8;">{d}</div></div></div>"""


def settings_section(title: str, description: str = "") -> str:
    t = html_mod.escape(str(title))
    d = html_mod.escape(str(description)) if description else ""
    desc_html = f'<div style="font-size:0.78rem;color:#94a3b8;margin-top:0.3rem;">{d}</div>' if description else ""
    return f"""<div style="padding:1.2rem;background:rgba(13,17,33,0.5);border:1px solid rgba(99,102,241,0.12);border-radius:12px;margin-bottom:1rem;"><div style="font-size:0.95rem;font-weight:700;color:#f1f5f9;">{t}</div>{desc_html}</div>"""


def typing_indicator(label: str = "AI is thinking") -> str:
    """Render an animated typing indicator with bouncing dots."""
    return f"""<div class="typing-indicator"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div><span style="font-size:0.78rem;color:#64748b;margin-left:0.3rem;">{label}...</span></div>"""


def skeleton_loader(lines: int = 3, height: str = "14px") -> str:
    """Render a skeleton loading placeholder with shimmer animation."""
    line_html = "".join(
        f'<div class="skeleton skeleton-line" style="height:{height};"></div>'
        for _ in range(lines)
    )
    return f"""<div style="padding:1rem;">{line_html}</div>"""


def skeleton_card() -> str:
    """Render a skeleton card placeholder."""
    return f"""<div style="padding:1.2rem;background:rgba(13,17,33,0.4);border:1px solid rgba(99,102,241,0.08);border-radius:var(--radius-lg);"><div style="display:flex;align-items:center;gap:0.8rem;margin-bottom:0.8rem;"><div class="skeleton skeleton-circle"></div><div style="flex:1;"><div class="skeleton skeleton-line" style="width:70%;height:16px;"></div><div class="skeleton skeleton-line" style="width:40%;height:12px;margin-top:0.4rem;"></div></div></div><div class="skeleton skeleton-line" style="height:12px;"></div><div class="skeleton skeleton-line" style="height:12px;"></div><div class="skeleton skeleton-line" style="height:12px;width:50%;"></div></div>"""


def neon_stat_card(value: str, label: str, color: str = "#818cf8", icon: str = "") -> str:
    """Render a neon-glowing stat card with animation."""
    icon_html = f'<div style="font-size:1.8rem;margin-bottom:0.3rem;">{icon}</div>' if icon else ""
    v = html_mod.escape(str(value))
    l = html_mod.escape(str(label))
    return f"""<div class="stat-counter-card neon-glow" style="min-width:100px;">{icon_html}<div style="font-size:1.8rem;font-weight:800;background:linear-gradient(135deg,{color},{color}aa);-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-family:'Space Grotesk',sans-serif;">{v}</div><div style="font-size:0.72rem;color:#64748b;text-transform:uppercase;letter-spacing:0.06em;font-weight:600;">{l}</div></div>"""


def animated_counter_html(value: int, label: str, color: str = "#818cf8") -> str:
    """Render a stat counter with count-up animation via CSS."""
    v = html_mod.escape(str(value))
    l = html_mod.escape(str(label))
    return f"""<div class="stat-counter-animated stat-counter-card" style="flex:1;"><div class="stats-value" style="font-size:1.8rem;font-weight:800;background:linear-gradient(135deg,{color},{color}aa);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">{v}</div><div style="font-size:0.72rem;color:#64748b;text-transform:uppercase;letter-spacing:0.06em;font-weight:600;">{l}</div></div>"""


def glow_button(label: str, key: str = None, icon: str = "", color: str = "#6366f1") -> str:
    """Return HTML for a premium glowing button with ripple effect."""
    safe_label = html_mod.escape(str(label))
    safe_key = html_mod.escape(str(key)) if key else ""
    key_attr = f' key="{safe_key}"' if key else ""
    icon_html = f'{icon} ' if icon else ""
    return f"""<div style="margin-bottom:0.5rem;"><div class="glow-btn-wrap"><button class="glow-btn"{key_attr} style="width:100%;padding:0.7rem 1.2rem;background:linear-gradient(135deg,{color} 0%,{color}cc 100%);color:white;border:1px solid {color}44;border-radius:var(--radius-md);font-weight:600;font-size:0.88rem;font-family:'Space Grotesk',sans-serif;cursor:pointer;transition:all 0.3s cubic-bezier(0.16,1,0.3,1);box-shadow:0 4px 15px {color}33;">{icon_html}{safe_label}</button></div></div>"""


def pipeline_trace(trace: dict) -> str:
    """Render the retrieval-pipeline step indicator (Phase 5.2).

    A horizontal Query → Cache → Hybrid Retrieve → Rerank → Graph → LLM → Answer
    row where each stage reflects what actually happened in the request. On a
    cache hit the row short-circuits (only Query / Cache / Answer ran).
    """
    t = trace or {}
    safe = lambda s: html_mod.escape(str(s))

    def _step(label: str, kind: str = "skip") -> str:
        return f'<span class="pipe-step pipe-{kind}">{safe(label)}</span>'

    if t.get("cache") == "hit":
        parts = [
            _step("✓ Query", "done"),
            '<span class="pipe-arrow">→</span>',
            _step("⚡ Cache HIT", "hit"),
            '<span class="pipe-arrow">→</span>',
            _step(f"Answer · {int(t.get('latency_ms', 0))} ms", "done"),
        ]
    else:
        model = str(t.get("model", "")).replace("nvidia/", "").replace("meta/", "").split(" /")[0]
        parts = [
            _step("✓ Query", "done"),
            '<span class="pipe-arrow">→</span>',
            _step("Cache miss", "skip"),
            '<span class="pipe-arrow">→</span>',
            _step("Hybrid Retrieve" if t.get("hybrid") else "Vector only", "done" if t.get("hybrid") else "warn"),
            '<span class="pipe-arrow">→</span>',
            _step("Rerank" if t.get("reranker") else "No rerank", "done" if t.get("reranker") else "warn"),
            '<span class="pipe-arrow">→</span>',
            _step(f"Graph · {int(t.get('graph_entities', 0))} entities", "done" if t.get("graph_entities") else "warn"),
            '<span class="pipe-arrow">→</span>',
            _step(f"LLM · {safe(model) if model else 'fallback'}", "done" if t.get("model") else "warn"),
            '<span class="pipe-arrow">→</span>',
            _step(f"Answer · {int(t.get('latency_ms', 0))} ms", "done"),
        ]
    return f'<div class="pipe-row">{"".join(parts)}</div>'


def evidence_stats_row(trace: dict) -> str:
    """Render compact monospace retrieval stats for the evidence panel (Phase 5.1)."""
    t = trace or {}
    safe = lambda s: html_mod.escape(str(s))
    chips = []
    if t.get("candidates") is not None:
        chips.append(f"candidates: {int(t['candidates'])}")
    if t.get("chunks_used") is not None:
        chips.append(f"chunks used: {int(t['chunks_used'])}")
    if t.get("graph_entities") is not None:
        chips.append(f"graph entities: {int(t['graph_entities'])}")
    if t.get("graph_relations") is not None:
        chips.append(f"graph relations: {int(t['graph_relations'])}")
    if t.get("complexity") is not None:
        chips.append(f"complexity: {'complex' if t['complexity'] else 'simple'}")
    if t.get("thinking") is not None:
        chips.append(f"thinking: {'on' if t['thinking'] else 'off'}")
    if t.get("routing_mode"):
        chips.append(f"router: {safe(t['routing_mode'])}")
    if not chips:
        return ""
    inner = "".join(f'<span class="stat-chip" style="font-family:JetBrains Mono,monospace;font-size:0.7rem;">{safe(c)}</span>' for c in chips)
    return f'<div style="display:flex;flex-wrap:wrap;gap:0.4rem;margin:0.4rem 0 0.9rem 0;">{inner}</div>'


def particle_background_js(container_id: str = "particles-bg", count: int = 50) -> str:
    """Return HTML+JS for a subtle floating particle background effect."""
    return f"""
<div id="{container_id}" style="position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:-1;overflow:hidden;">
<script>
(function() {{
    var c = document.getElementById('{container_id}');
    if (!c) return;
    var canvas = document.createElement('canvas');
    canvas.style.cssText = 'width:100%;height:100%;';
    c.appendChild(canvas);
    var ctx = canvas.getContext('2d');
    var w, h, dots = [];
    function resize() {{ w = canvas.width = window.innerWidth; h = canvas.height = window.innerHeight; }}
    resize(); window.addEventListener('resize', resize);
    for (var i = 0; i < {count}; i++) {{
        dots.push({{ x: Math.random()*w, y: Math.random()*h, r: 0.5+Math.random()*1.5, vx: (Math.random()-0.5)*0.15, vy: (Math.random()-0.5)*0.15, a: 0.1+Math.random()*0.2 }});
    }}
    function draw() {{
        ctx.clearRect(0,0,w,h);
        for (var i=0;i<dots.length;i++) {{ var d=dots[i]; d.x+=d.vx; d.y+=d.vy;
            if(d.x<0) d.x=w; if(d.x>w) d.x=0; if(d.y<0) d.y=h; if(d.y>h) d.y=0;
            ctx.beginPath(); ctx.arc(d.x,d.y,d.r,0,Math.PI*2);
            ctx.fillStyle='rgba(99,102,241,'+d.a+')'; ctx.fill();
        }}
        requestAnimationFrame(draw);
    }}
    draw();
}})();
</script>
</div>
"""
