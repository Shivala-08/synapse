"""Synapse — AI-Powered Knowledge Intelligence UI.

Features:
  • Cinematic animated hero header with gradient glow
  • Glassmorphism cards and panels
  • Neon glow accents and animated borders
  • Real-time streaming chat interface
  • Interactive 3D knowledge graph visualization
  • Adaptive query routing with complexity classification
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import streamlit.components.v1 as components
import requests
import json
import os
from src.ui.design_system import (
    inject_global_css, hero_header, gradient_divider, section_header,
    sidebar_brand, sidebar_footer, llm_status_pill, confidence_badge,
    fmt_time, post_feedback, chat_bubble, citation_card, keypoints_box,
    info_banner, settings_section, doc_card_html, skeleton_card,
    pipeline_trace, evidence_stats_row,
)

try:
    from streamlit_agraph import agraph, Node, Edge, Config
    AGRAPH_AVAILABLE = True
except ImportError:
    AGRAPH_AVAILABLE = False

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Synapse — AI-Powered Knowledge Intelligence",
    page_icon="K",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_URL = os.getenv("API_URL", "http://localhost:8000")

# ── Inject shared design system CSS ────────────────────────────────────────────
inject_global_css()


@st.dialog("Knowledge Graph Subgraph", width="large")
def show_entity_graph(entity_id: str):
    st.markdown(f"### Subgraph for **{entity_id}**")
    try:
        r = requests.get(f"{API_URL}/graph/entity/{entity_id}?depth=1", timeout=15)
        if r.status_code == 200:
            data = r.json()
            center = data.get("center", {})
            neighbors = data.get("neighbors", [])
            edges = data.get("edges", [])

            def get_color(t):
                t = t.lower() if t else ""
                if t == "equipment": return "#ef4444"
                if t == "permit": return "#8b5cf6"
                if t == "regulation": return "#10b981"
                return "#6b7280"

            ag_nodes = [Node(
                id=center["id"],
                label=center.get("label", center["id"]),
                size=25,
                color=get_color(center.get("type")),
                title=f"{center['id']} ({center.get('type')})"
            )]

            for n in neighbors:
                ag_nodes.append(Node(
                    id=n["id"],
                    label=n.get("label", n["id"]),
                    size=15,
                    color=get_color(n.get("type")),
                    title=f"{n['id']} ({n.get('type')})"
                ))

            ag_edges = [Edge(
                source=e["source"],
                target=e["target"],
                label=e.get("relation_type", ""),
                title=e.get("relation_type", "")
            ) for e in edges]

            config = Config(
                width="100%", height=400, directed=False, hierarchical=False,
                node={"font": {"size": 12}},
                physics={
                    "enabled": True, "solver": "barnesHut",
                    "barnesHut": {"gravitationalConstant": -2000, "centralGravity": 0.3, "springLength": 95},
                },
            )

            if AGRAPH_AVAILABLE:
                agraph(nodes=ag_nodes, edges=ag_edges, config=config)
            else:
                st.warning("streamlit-agraph not installed")
        else:
            st.error(f"Entity not found: {r.json().get('detail', 'Unknown error')}")
    except Exception as e:
        st.error(f"Error loading graph: {e}")


# ── Evidence trace block (Phase 5.1 / 5.2) ─────────────────────────────────
def render_evidence_block(trace, sources, expanded: bool = False):
    """Collapsible 'Why this answer?' panel: pipeline visual + retrieval stats + citations."""
    srcs = sources or []
    tr = trace or {}
    n = len(srcs)
    if not srcs and not tr:
        return
    label = f"🔍 Why this answer? — {n} source(s)" if srcs else "🔍 Why this answer?"
    with st.expander(label, expanded=expanded):
        if tr:
            st.markdown(pipeline_trace(tr), unsafe_allow_html=True)
            stats_html = evidence_stats_row(tr)
            if stats_html:
                st.markdown(stats_html, unsafe_allow_html=True)
        for si, src in enumerate(srcs, 1):
            cite = src.get("citation") or src.get("doc_id", "Unknown")
            st.markdown(
                citation_card(si, cite, src.get("distance", 0), src.get("excerpt", "")),
                unsafe_allow_html=True,
            )


# ══════════════════════════════════════════════════════════════════════════════
# HERO HEADER
# ══════════════════════════════════════════════════════════════════════════════
# Live system status badge (Phase 4.3) — reassures visitors the app is live.
try:
    _health = requests.get(f"{API_URL}/health", timeout=5)
    _online = _health.status_code == 200
except Exception:
    _online = False

_status_color = "#10b981" if _online else "#ef4444"
_status_text = "● System Online" if _online else "○ Backend Offline"
status_html = (
    '<div class="stat-counter-card" style="min-width:130px;text-align:center;">'
    f'<div style="font-size:0.95rem;font-weight:800;color:{_status_color};">{_status_text}</div>'
    '<div style="font-size:0.68rem;color:#64748b;text-transform:uppercase;letter-spacing:0.06em;">Live</div>'
    '</div>'
)

hero_header(
    title="Synapse",
    subtitle="AI-Powered Knowledge Intelligence",
    badge_text="",
    extra_right=status_html,
)


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    sidebar_brand(name="SYNAPSE")

    st.markdown("### **System Status**")
    try:
        h = requests.get(f"{API_URL}/health", timeout=15)
        if h.status_code == 200:
            st.success("FastAPI: Connected")
        else:
            st.warning("FastAPI: Unhealthy")
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        st.error("FastAPI: Offline")

    gradient_divider()
    st.markdown("### **LLM Engine**")
    try:
        llm_resp = requests.get(f"{API_URL}/llm/status", timeout=10)
        if llm_resp.status_code == 200:
            ls = llm_resp.json()
            st.session_state["llm_status"] = ls
            nvidia_on = ls.get("nvidia_available", False)
            ollama_on = ls.get("ollama_available", False)
            if nvidia_on:
                model_name = ls.get("model", "nemotron").replace("nvidia/", "").replace("meta/", "")
                llm_status_pill(model_name, available=True, mode="nvidia")
            elif ollama_on:
                llm_status_pill(ls["model"], available=True, mode="ollama")
            else:
                llm_status_pill("", available=False)
    except Exception:
        st.caption("LLM status unavailable")

    gradient_divider()
    try:
        gr = requests.get(f"{API_URL}/entities", timeout=15)
        if gr.status_code == 200:
            gd = gr.json()
            stats = gd.get("stats", {})
            st.markdown("### **Knowledge Graph**")
            c1, c2 = st.columns(2)
            c1.metric("Nodes", stats.get("total_nodes", 0))
            c2.metric("Edges", stats.get("total_edges", 0))
            nt = stats.get("node_types", {})
            if nt:
                with st.expander("Entity Breakdown"):
                    for etype, cnt in sorted(nt.items(), key=lambda x: -x[1]):
                        color_map = {
                            "equipment": "#ef4444", "regulation": "#10b981",
                            "plant": "#3b82f6", "permit": "#f59e0b",
                            "work_order": "#8b5cf6", "incident": "#ec4899",
                        }
                        color = color_map.get(etype, "#6b7280")
                        st.markdown(
                            f'<span style="display:flex;align-items:center;gap:0.4rem;margin-bottom:0.3rem;">'
                            f'<span style="width:8px;height:8px;border-radius:50%;background:{color};display:inline-block;"></span>'
                            f'<span style="font-size:0.82rem;color:#e2e8f0;">{etype.replace("_", " ").title()}: <strong>{cnt}</strong></span></span>',
                            unsafe_allow_html=True,
                        )
    except Exception:
        pass

    gradient_divider()


# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
tab_chat, tab_docs, tab_graph, tab_entities, tab_bench, tab_setup = st.tabs([
    "Query Console", "Documents", "Knowledge Network",
    "Entity Explorer", "Evaluation", "Settings",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — CHAT Q&A
# ══════════════════════════════════════════════════════════════════════════════
with tab_chat:
    llm_status = st.session_state.get("llm_status", {})
    if llm_status.get("nvidia_available"):
        caption_text = "Powered by **Vector Search + Knowledge Graph + NVIDIA LLM API**"
        caption_icon = "*"
    elif llm_status.get("ollama_available"):
        caption_text = "Powered by **Vector Search + Knowledge Graph + Local LLM (Ollama)** — no API key required"
        caption_icon = "~"
    else:
        caption_text = "Powered by **Vector Search + Knowledge Graph + Smart Context Fallback**"
        caption_icon = ">"

    st.markdown(info_banner(caption_icon, "Interactive Query Console", caption_text), unsafe_allow_html=True)

    # Model Routing Controls
    st.write("")
    c_route_1, c_route_2 = st.columns([2, 8])
    with c_route_1:
        st.markdown("<div style='padding-top: 10px; font-weight: 600; font-size: 1.05rem;'>⚡ Router Control:</div>", unsafe_allow_html=True)
    with c_route_2:
        routing_mode_label = st.radio(
            label="Router Mode Selection",
            options=["🤖 Auto Classifier", "⚡ Fast Answer (8B)", "🧠 Deep Reasoning (550B)"],
            index=0,
            horizontal=True,
            label_visibility="collapsed"
        )
        routing_mode = {
            "🤖 Auto Classifier": "auto",
            "⚡ Fast Answer (8B)": "fast",
            "🧠 Deep Reasoning (550B)": "deep"
        }[routing_mode_label]

    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "last_answer" not in st.session_state:
        st.session_state.last_answer = None

    # Chat history
    for idx, msg in enumerate(st.session_state.messages):
        if msg["role"] == "user":
            st.markdown(chat_bubble("user", msg["content"]), unsafe_allow_html=True)
        else:
            with st.container():
                conf_badge = confidence_badge(msg.get("confidence", "Medium"))
                model_badge = f'<span class="badge badge-teal"> {msg.get("model_used","")}</span>'
                latency_badge = f'<span class="badge badge-gray">⏱ {msg.get("latency_ms", 0)} ms</span>'
                st.markdown(
                    chat_bubble("assistant", f'{conf_badge} {model_badge} {latency_badge}'),
                    unsafe_allow_html=True,
                )
                st.markdown(msg["content"])

                kp = msg.get("key_points", [])
                if kp:
                    st.markdown(keypoints_box(kp), unsafe_allow_html=True)

                ents = msg.get("entities_used", [])
                if ents:
                    st.markdown("<small><b>Entities mentioned (click to view graph):</b></small>", unsafe_allow_html=True)
                    cols = st.columns(min(len(ents[:6]), 6))
                    for i, e in enumerate(ents[:6]):
                        with cols[i]:
                            if st.button(f"{e}", key=f"ent_btn_{idx}_{i}", use_container_width=True):
                                show_entity_graph(e)

                render_evidence_block(msg.get("trace"), msg.get("sources"), expanded=False)

                c1, c2, _ = st.columns([1, 1, 8])
                if c1.button("Good", key=f"up_{idx}", help="Good answer"):
                    post_feedback(msg.get("question", ""), msg["content"][:300], +1, API_URL)
                    st.toast("Thanks for the feedback!", icon="👍")
                if c2.button("Poor", key=f"dn_{idx}", help="Poor answer"):
                    post_feedback(msg.get("question", ""), msg["content"][:300], -1, API_URL)
                    st.toast("Feedback logged. We'll improve!", icon="👎")

    # Example queries (Phase 4.1) — a visitor never faces a blank text box
    with st.expander("💡 Try these questions", expanded=not st.session_state.get("messages")):
        _examples = [
            ("⚡ Simple lookup", "What are the electrical safety requirements per OISD-130?"),
            ("🔗 Multi-hop", "Which regulation applies to work order WO-2026-1001?"),
            ("⚖️ Contradiction", "Do the safety manual and OISD-117 disagree on the internal inspection frequency for tank TNK-T03?"),
            ("📋 Compliance gap", "Is there a documented requirement for lockout/tagout procedures?"),
            ("🗂️ Record lookup", "What is the current status of permit PRM-2026-5000?"),
        ]
        _ex_cols = st.columns(len(_examples))
        for _i, (_label, _question) in enumerate(_examples):
            with _ex_cols[_i]:
                if st.button(_label, key=f"ex_q_{_i}", help=_question, use_container_width=True):
                    st.session_state.pending_query = _question
                    st.rerun()

    # Input
    user_query = st.chat_input(
        "Ask a safety or regulatory question… (e.g. 'What PPE is required for hot work near COMP-C01?')"
    )

    # An example-query button supplies the question on the next rerun
    if user_query is None and st.session_state.get("pending_query"):
        user_query = st.session_state.pop("pending_query")

    if user_query:
        st.markdown(chat_bubble("user", user_query), unsafe_allow_html=True)
        st.session_state.messages.append({"role": "user", "content": user_query})

        answer = ""; sources = []; confidence = "Medium"; key_points = []; entities = []; model_used = "unknown"; latency_ms = 0; trace = {}
        stream_placeholder = st.empty(); streaming_text = ""

        # Phase 4.2 — visible cold-start state instead of a silent hang
        stream_placeholder.markdown("_⏳ Warming up models — the first query can take a few seconds…_")

        try:
            import httpx
            with httpx.Client(timeout=120) as client:
                with client.stream("POST", f"{API_URL}/query/stream", json={"question": user_query, "top_k": 5, "routing_mode": routing_mode}, headers={"Accept": "text/event-stream"}) as resp:
                    if resp.status_code != 200:
                        st.error(f"API error {resp.status_code}")
                    else:
                        for line in resp.iter_lines():
                            line = line.strip()
                            if not line or not line.startswith("data:"):
                                continue
                            payload_str = line[5:].strip()
                            if not payload_str:
                                continue
                            try:
                                event = json.loads(payload_str)
                            except json.JSONDecodeError:
                                continue
                            etype = event.get("type")
                            content = event.get("content", "")
                            if etype == "token":
                                streaming_text += content
                                stream_placeholder.markdown(streaming_text)
                            elif etype == "metadata":
                                answer = content.get("answer", streaming_text)
                                sources = content.get("sources", [])
                                confidence = content.get("confidence", "Medium")
                                key_points = content.get("key_points", [])
                                entities = content.get("entities_used", [])
                                model_used = content.get("model_used", "unknown")
                                latency_ms = content.get("latency_ms", 0)
                                trace = content.get("trace", {})
                            elif etype == "error":
                                st.error(f"LLM error: {content}")
        except ImportError:
            with st.spinner("Generating answer..."):
                try:
                    resp = requests.post(f"{API_URL}/query", json={"question": user_query, "top_k": 5, "routing_mode": routing_mode}, timeout=120)
                    if resp.status_code == 200:
                        data = resp.json()
                        answer = data.get("answer", ""); sources = data.get("sources", [])
                        confidence = data.get("confidence", "Medium"); key_points = data.get("key_points", [])
                        entities = data.get("entities_used", []); model_used = data.get("model_used", "unknown")
                        latency_ms = data.get("latency_ms", 0)
                        stream_placeholder.markdown(answer)
                    else:
                        st.error(f"API error {resp.status_code}: {resp.text[:200]}")
                except Exception as e:
                    st.error(f"Error: {e}")
        except requests.exceptions.Timeout:
            st.error("⏳ Request timed out (>120 s). If using Ollama for the first time, it may be loading the model — please try again in a moment.")
        except requests.exceptions.ConnectionError:
            st.error(" Cannot reach the FastAPI server at `localhost:8000`. Start it with: `PYTHONPATH=. uvicorn src.main:app --reload`")
        except Exception as e:
            st.error(f"Unexpected error: {e}")

        if answer:
            stream_placeholder.markdown(answer)
            conf_badge = confidence_badge(confidence)
            model_badge = f'<span class="badge badge-teal"> {model_used}</span>'
            latency_badge = f'<span class="badge badge-gray">⏱ {latency_ms} ms</span>'
            st.markdown(chat_bubble("assistant", f'{conf_badge} {model_badge} {latency_badge}'), unsafe_allow_html=True)

            if key_points:
                st.markdown(keypoints_box(key_points), unsafe_allow_html=True)

            if entities:
                st.markdown("<small><b>Entities mentioned (click to view graph):</b></small>", unsafe_allow_html=True)
                cols = st.columns(min(len(entities[:6]), 6))
                for i, e in enumerate(entities[:6]):
                    with cols[i]:
                        if st.button(f"{e}", key=f"ent_btn_live_{i}", use_container_width=True):
                            show_entity_graph(e)

            render_evidence_block(trace, sources, expanded=True)

            st.session_state.messages.append({
                "role": "assistant", "content": answer, "confidence": confidence,
                "key_points": key_points, "entities_used": entities, "model_used": model_used,
                "latency_ms": latency_ms, "sources": sources, "question": user_query,
                "trace": trace,
            })
            st.session_state.last_answer = answer

    if st.session_state.messages:
        if st.button("Clear Chat", use_container_width=False):
            st.session_state.messages = []; st.session_state.last_answer = None; st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — DOCUMENT LIBRARY
# ══════════════════════════════════════════════════════════════════════════════
with tab_docs:
    section_header("Documents", "Document Repository", "Browse indexed regulatory documents and structured plant logs")
    docs_skeleton = st.empty()
    docs_skeleton.markdown(skeleton_card(), unsafe_allow_html=True)

    try:
        docs_resp = requests.get(f"{API_URL}/documents", timeout=25)
        if docs_resp.status_code == 200:
            docs_skeleton.empty()
            docs = docs_resp.json()
            if not docs:
                st.info("No documents indexed yet. Go to the **Settings** tab to initialise.")
            else:
                file_types = sorted(set(d["type"] for d in docs))
                sel_types = st.multiselect("Filter by Type", file_types, default=file_types)
                search_q = st.text_input("Search document names", "")
                filtered = [d for d in docs if d["type"] in sel_types and (not search_q or search_q.lower() in d["filename"].lower())]

                c1, c2, c3 = st.columns(3)
                c1.metric("Total Documents", len(docs))
                c2.metric("Showing", len(filtered))
                c3.metric("Types", len(file_types))

                gradient_divider()

                for doc in filtered:
                    with st.container():
                        st.markdown(
                            doc_card_html(doc['filename'], doc['type'], doc['chunk_count'], doc['upload_date'], doc.get('entities_found', 0)),
                            unsafe_allow_html=True,
                        )
                        with st.expander(f" Inspect chunks — {doc['filename']}"):
                            if st.button("Load Chunks", key=f"btn_{doc['doc_id']}"):
                                try:
                                    cr = requests.get(f"{API_URL}/documents/{doc['doc_id']}", timeout=25)
                                    if cr.status_code == 200:
                                        cd = cr.json()
                                        st.write(f"**{len(cd['chunks'])} chunks**")
                                        for c in cd["chunks"]:
                                            st.info(f"Chunk {c['metadata'].get('chunk_index',0)} · `{c['chunk_id']}`")
                                            st.code(c["text"], language=None)
                                    else:
                                        st.error(cr.text)
                                except Exception as err:
                                    st.error(str(err))
        else:
            docs_skeleton.empty()
            st.error(f"Failed to fetch documents: {docs_resp.status_code}")
    except Exception as e:
        docs_skeleton.empty()
        st.error(f"Could not connect to API: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — KNOWLEDGE GRAPH (3D WebGL)
# ══════════════════════════════════════════════════════════════════════════════
with tab_graph:
    section_header("Knowledge", "Knowledge Network", "Interactive 3D entity-relationship graph with force-directed layout")
    graph_skeleton = st.empty()
    graph_skeleton.markdown(skeleton_card(), unsafe_allow_html=True)

    try:
        gr = requests.get(f"{API_URL}/graph?max_nodes=200", timeout=25)
        if gr.status_code == 200:
            graph_skeleton.empty()
            gd = gr.json(); nodes = gd.get("nodes", []); edges = gd.get("edges", [])
            if not nodes:
                st.info("Graph is empty. Initialise the corpus first.")
            else:
                total_n = len(nodes)
                total_e = len(edges)
                try:
                    stats_resp = requests.get(f"{API_URL}/entities", timeout=5)
                    if stats_resp.status_code == 200:
                        stats_data = stats_resp.json().get("stats", {})
                        total_n = stats_data.get("total_nodes", total_n)
                        total_e = stats_data.get("total_edges", total_e)
                except Exception:
                    pass

                st.markdown(f"""
                <div style="display:flex;gap:0.8rem;margin-bottom:1rem;">
                    <div class="stat-counter-card" style="flex:1;">
                        <div style="font-size:1.5rem;font-weight:800;color:#818cf8;">{total_n}</div>
                        <div style="font-size:0.72rem;color:#64748b;text-transform:uppercase;letter-spacing:0.06em;">Nodes</div>
                    </div>
                    <div class="stat-counter-card" style="flex:1;">
                        <div style="font-size:1.5rem;font-weight:800;color:#a78bfa;">{total_e}</div>
                        <div style="font-size:0.72rem;color:#64748b;text-transform:uppercase;letter-spacing:0.06em;">Edges</div>
                    </div>
                    <div class="stat-counter-card" style="flex:1;">
                        <div style="font-size:1.5rem;font-weight:800;color:#6ee7b7;">3D</div>
                        <div style="font-size:0.72rem;color:#64748b;text-transform:uppercase;letter-spacing:0.06em;">Interactive</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                js_3d = ""
                js_2d = ""
                try:
                    js_3d_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static", "js", "3d-force-graph.js")
                    if os.path.exists(js_3d_path):
                        with open(js_3d_path, "r", encoding="utf-8") as f:
                            js_3d = f.read()
                    js_2d_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static", "js", "force-graph.js")
                    if os.path.exists(js_2d_path):
                        with open(js_2d_path, "r", encoding="utf-8") as f:
                            js_2d = f.read()
                except Exception as err:
                    st.error(f"Error loading inline script: {err}")

                nodes_json = json.dumps(nodes); edges_json = json.dumps(edges)

                html_code = """
                <div id="3d-graph" style="width:100%;height:620px;border-radius:16px;overflow:hidden;border:1px solid rgba(99,102,241,0.25);background:#090d16;position:relative;box-shadow:0 20px 60px rgba(0,0,0,0.3),0 0 30px rgba(99,102,241,0.05);"></div>
                <script>
                   window.addEventListener('error', function(e) {
                     const elem = document.getElementById('3d-graph');
                     if (elem) {
                       elem.style.background = '#1e1b4b';
                       elem.innerHTML = `<div style="color:#fca5a5;padding:20px;font-family:monospace;font-size:12px;white-space:pre-wrap;line-height:1.5;">
                         <strong style="font-size:14px;color:#ef4444;">❌ JavaScript Error Detected:</strong><br/><br/>
                         <strong>Message:</strong> ${e.message}<br/>
                         <strong>File:</strong> ${e.filename}<br/>
                         <strong>Line:</strong> ${e.lineno}:${e.colno}<br/><br/>
                         <strong>Stack Trace:</strong><br/>${e.error ? e.error.stack : 'N/A'}
                       </div>`;
                     }
                   });
                 </script>
                 <script>
                   function isWebGLSupported() {
                     try {
                       const canvas = document.createElement('canvas');
                       return !!(window.WebGLRenderingContext && (canvas.getContext('webgl') || canvas.getContext('experimental-webgl')));
                     } catch (e) {
                       return false;
                     }
                   }
                 </script>
                 <script>
                   {js_3d}
                 </script>
                 <script>
                   {js_2d}
                 </script>
                  <script>
                    function initGraph() {
                      const use3D = isWebGLSupported() && (typeof ForceGraph3D !== 'undefined');
                      const GraphConstructor = use3D ? ForceGraph3D : ForceGraph;
                     
                     if (typeof GraphConstructor === 'undefined') {
                       setTimeout(initGraph, 50);
                       return;
                     }
                     const elem = document.getElementById('3d-graph');
                     if (!elem) { setTimeout(initGraph, 50); return; }
                     const rawNodes = {nodes_json}; const rawEdges = {edges_json};
                     const links = rawEdges.map(e => ({source: e.from, target: e.to, relation: e.relation || 'linked_to'}));
                     const degrees = {};
                     links.forEach(l => { degrees[l.source] = (degrees[l.source] || 0) + 1; degrees[l.target] = (degrees[l.target] || 0) + 1; });
                     const nodes = rawNodes.map(n => ({id: n.id, label: n.id, type: n.type, color: n.color || '#6366f1', val: Math.max(Math.sqrt(degrees[n.id] || 1) * 1.5, 1.5)}));
                     
                     const Graph = GraphConstructor()(elem).graphData({nodes, links}).backgroundColor('#090d16')
                       .nodeColor(node => node.color).nodeVal(node => node.val)
                       .nodeLabel(node => {
                         const t = (node.type || 'unknown').replace('_',' ').toUpperCase(); const c = node.color || '#6366f1'; const d = degrees[node.id] || 0;
                         return `<div style="background:rgba(9,13,22,0.96);backdrop-filter:blur(12px);border:1px solid ${c};box-shadow:0 10px 25px rgba(0,0,0,0.6),0 0 12px ${c}33;border-radius:10px;padding:12px 16px;min-width:180px;color:#f1f5f9;font-family:sans-serif;font-size:12px;pointer-events:none;line-height:1.5;;"><div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;border-bottom:1px solid rgba(255,255,255,0.08);padding-bottom:6px;"><span style="width:8px;height:8px;border-radius:50%;background:${c};box-shadow:0 0 8px ${c};"></span><strong style="color:#fff;font-size:13px;">${node.id}</strong></div><div style="color:#94a3b8;font-size:10px;margin-bottom:4px;">CLASS: <span style="color:${c};font-weight:700;letter-spacing:0.03em;">${t}</span></div><div style="color:#cbd5e1;font-size:10px;">CONNECTIONS: <strong style="color:#fff;">${d}</strong></div></div>`;
                       })
                       .linkLabel(link => `<div style="background:rgba(15,23,42,0.9);border:1px solid rgba(255,255,255,0.1);border-radius:4px;padding:4px 8px;color:#cbd5e1;font-family:sans-serif;font-size:11px;">${link.relation}</div>`)
                       .linkWidth(use3D ? 0.8 : 1.2).linkColor(() => 'rgba(255, 255, 255, 0.15)');
                     
                     setTimeout(() => {
                       try {
                         const chargeForce = Graph.d3Force('charge');
                         if (chargeForce && typeof chargeForce.strength === 'function') {
                             chargeForce.strength(use3D ? -25 : -15);
                         }
                         const linkForce = Graph.d3Force('link');
                         if (linkForce && typeof linkForce.distance === 'function') {
                             linkForce.distance(use3D ? 25 : 18);
                         }
                       } catch(err) {
                         console.warn("Failed to apply layout forces:", err);
                       }
                     }, 150);
                     
                     Graph.onNodeClick(node => {
                       if (use3D) {
                         const d = 50; const dr = 1 + d/Math.hypot(node.x,node.y,node.z);
                         Graph.cameraPosition({x:node.x*dr,y:node.y*dr,z:node.z*dr}, node, 2000);
                       } else {
                         Graph.centerAt(node.x, node.y, 1000);
                         Graph.zoom(2.2, 1000);
                       }
                       let ov = document.getElementById('node-info-overlay');
                       if (!ov) { ov = document.createElement('div'); ov.id='node-info-overlay'; ov.style.cssText='position:absolute;bottom:15px;right:15px;background:rgba(15,23,42,0.95);backdrop-filter:blur(10px);border:1px solid rgba(99,102,241,0.4);border-radius:12px;padding:15px;width:240px;color:#fff;font-family:sans-serif;font-size:12px;box-shadow:0 10px 30px rgba(0,0,0,0.5);pointer-events:auto;z-index:999;'; elem.appendChild(ov); }
                       ov.innerHTML = `<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;"><strong style="font-size:14px;color:#818cf8;">${node.id}</strong><span style="font-size:10px;font-weight:600;text-transform:uppercase;padding:2px 6px;background:rgba(99,102,241,0.2);border-radius:4px;color:#a5b4fc;">${node.type}</span></div><div style="border-top:1px solid rgba(255,255,255,0.08);padding-top:8px;color:#94a3b8;line-height:1.5;">Connections: <strong>${degrees[node.id]||0}</strong><br>Status: <span style="color:#10b981;">CONNECTED</span></div><div style="margin-top:8px;text-align:right;"><button onclick="document.getElementById('node-info-overlay').remove()" style="background:transparent;border:none;color:#ef4444;font-size:10px;font-weight:600;cursor:pointer;">Dismiss</button></div>`;
                     });
                   }
                   initGraph();
                 </script>
                 """.replace("{nodes_json}", nodes_json).replace("{edges_json}", edges_json).replace("{js_3d}", js_3d).replace("{js_2d}", js_2d)

                components.html(html_code, height=640)
        else:
            graph_skeleton.empty()
            st.error(f"Graph API error {gr.status_code}")
    except requests.exceptions.ConnectionError:
        graph_skeleton.empty()
        st.error("Cannot reach FastAPI server.")
    except Exception as e:
        graph_skeleton.empty()
        st.error(f"Error: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — ENTITY EXPLORER
# ══════════════════════════════════════════════════════════════════════════════
with tab_entities:
    entities_skeleton = st.empty()
    entities_skeleton.markdown(skeleton_card() + skeleton_card() + skeleton_card(), unsafe_allow_html=True)

    section_header("Entities", "Entity Explorer", "Browse entities extracted from the document corpus")

    try:
        er = requests.get(f"{API_URL}/entities", timeout=25)
        if er.status_code == 200:
            entities_skeleton.empty()
            ed = er.json(); ebt = ed.get("entities", {}); stats = ed.get("stats", {})
            if not ebt:
                entities_skeleton.empty()
                st.info("No entities found. Initialise the corpus first.")
            else:
                c1, c2, c3 = st.columns(3)
                c1.metric("Total Nodes", stats.get("total_nodes", 0))
                c2.metric("Total Edges", stats.get("total_edges", 0))
                c3.metric("Graph Density", f"{stats.get('density', 0):.4f}")
                gradient_divider()

                sel = st.selectbox("Filter by Entity Type", sorted(ebt.keys()), format_func=lambda x: x.replace("_", " ").title())
                if sel:
                    elist = ebt[sel]
                    srch = st.text_input("Search entities", "", key="ent_srch")
                    if srch:
                        elist = [e for e in elist if srch.lower() in e.lower()]
                    st.markdown(info_banner("", f"{len(elist)} {sel.replace('_',' ').title()} entities", ""), unsafe_allow_html=True)

                    for eid in elist[:50]:
                        with st.container():
                            st.markdown(f"**{eid}**")
                            if st.button("View relationships", key=f"sub_{eid}"):
                                try:
                                    sr = requests.get(f"{API_URL}/graph/entity/{eid}?depth=1", timeout=25)
                                    if sr.status_code == 200:
                                        sd = sr.json(); nb = sd.get("neighbors", [])
                                        if nb:
                                            st.write(f"**{len(nb)} connections:**")
                                            for n in nb:
                                                st.markdown(f"• *{n['relation']}* → **{n['id']}** ({n['type']})")
                                        else:
                                            st.info("No direct connections.")
                                except Exception as ex:
                                    st.error(str(ex))
                            gradient_divider()

                    if len(elist) > 50:
                        st.info(f"Showing first 50 of {len(elist)} entities.")
        else:
            entities_skeleton.empty()
            st.error(f"Entities API error {er.status_code}")
    except requests.exceptions.ConnectionError:
        entities_skeleton.empty()
        st.error("Cannot reach FastAPI server.")
    except Exception as e:
        entities_skeleton.empty()
        st.error(f"Error: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — BENCHMARK
# ══════════════════════════════════════════════════════════════════════════════
with tab_bench:
    section_header("Evaluation", "System Evaluation", "Ground-truth accuracy & latency metrics for the active RAG pipeline")

    col_run, col_n = st.columns([3, 1])
    with col_n:
        max_q = st.number_input("Questions to run", min_value=1, max_value=40, value=40, step=1)
    with col_run:
        run_btn = st.button("Run Verification Suite", use_container_width=True)

    if run_btn:
        prog_bar = st.progress(0, text="Starting benchmark…")
        with st.spinner(f"Running {max_q} questions against the RAG engine…"):
            try:
                resp = requests.get(f"{API_URL}/benchmark/run?max_questions={max_q}", timeout=600)
                if resp.status_code == 200:
                    bdata = resp.json(); total = bdata["total"]; correct = bdata["correct"]
                    acc = bdata["accuracy_pct"]; avg_ms = bdata["avg_latency_ms"]
                    model = bdata.get("model_used", "unknown"); results = bdata.get("results", [])
                    prog_bar.progress(1.0, text="Done!")
                    gradient_divider()

                    mc1, mc2, mc3, mc4 = st.columns(4)
                    mc1.metric("Accuracy", f"{acc}%"); mc2.metric("Correct", f"{correct} / {total}")
                    mc3.metric("⏱ Avg Latency", f"{avg_ms} ms"); mc4.metric(" Model", model)
                    gradient_divider()

                    st.markdown("### Detailed Results")
                    for r in results:
                        icon = "PASS" if r["passed"] else ""
                        sim_info = f" · Sim: {r['similarity']:.2f}" if "similarity" in r else ""
                        with st.expander(f"{icon} [{r['id']}] {r['question']}{sim_info} · {r['latency_ms']} ms", expanded=False):
                            st.markdown(f"**Category:** `{r.get('category','')}`")
                            st.markdown(f"**Expected:** {r['expected']}")
                            st.markdown(f"**Got:** {r['got']}")
                            cols = st.columns(2)
                            with cols[0]:
                                if "similarity" in r:
                                    st.markdown(f"**Embedding Similarity:** `{r['similarity']:.3f}`")
                            with cols[1]:
                                if "passed_keyword" in r:
                                    kw_pass = " Pass" if r["passed_keyword"] else " Fail"
                                    st.markdown(f"**Keyword Overlap:** {kw_pass}")
                            conf_col = "green" if r["confidence"] in ["High", 0.85] else "blue"
                            st.markdown(f'<span class="badge badge-{conf_col}">Confidence: {r["confidence"]}</span>', unsafe_allow_html=True)

                    st.markdown("### Category Breakdown")
                    from collections import defaultdict
                    cat_stats: dict = defaultdict(lambda: {"pass": 0, "fail": 0})
                    for r in results:
                        cat = r.get("category", "other")
                        if r["passed"]: cat_stats[cat]["pass"] += 1
                        else: cat_stats[cat]["fail"] += 1
                    for cat, s in sorted(cat_stats.items()):
                        total_cat = s["pass"] + s["fail"]
                        pct = round(s["pass"] / total_cat * 100)
                        st.markdown(f"**{cat.replace('_',' ').title()}** — {s['pass']}/{total_cat} ({pct}%)")
                else:
                    prog_bar.empty()
                    st.error(f"Benchmark API error {resp.status_code}: {resp.text[:300]}")
            except requests.exceptions.Timeout:
                st.error("Benchmark timed out — reduce question count or check Ollama.")
            except requests.exceptions.ConnectionError:
                st.error("Cannot reach FastAPI server.")
            except Exception as e:
                st.error(f"Error: {e}")

    gradient_divider()
    st.info("**Scoring method:** Embedding similarity (semantic match) via `all-MiniLM-L6-v2`. A question passes if the cosine similarity is ≥ 0.55 and the expected source documents are retrieved. Keyword-overlap stats are also tracked for comparison.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — SETTINGS
# ══════════════════════════════════════════════════════════════════════════════
with tab_setup:
    section_header("Settings", "Settings & Control Panel", "Manage vector database, ingest documents, and debug retrieval")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(settings_section("Core Corpus Initialisation"), unsafe_allow_html=True)
        st.write("Index all pre-bundled files: OISD / DGMS / Factory Act regulatory docs plus synthetic work orders, permits, and incident reports.")
        if st.button(" Scan & Index Default Corpus", use_container_width=True):
            with st.spinner("Parsing, embedding, and building knowledge graph… (~60 s)"):
                try:
                    r = requests.post(f"{API_URL}/ingest/initialize", timeout=180)
                    if r.status_code == 200:
                        s = r.json()["stats"]
                        st.success(f" Indexed **{s['files_ingested']}** documents · **{s['total_chunks']}** chunks")
                        st.rerun()
                    else:
                        st.error(f"Error: {r.text}")
                except Exception as e:
                    st.error(str(e))

    with col2:
        st.markdown(settings_section("Upload New Documents"), unsafe_allow_html=True)
        st.write("Upload PDF, DOCX, CSV, or TXT files to add to the live search index.")
        uploaded = st.file_uploader("Select Files", type=["txt", "pdf", "docx", "csv"], accept_multiple_files=True)
        if uploaded:
            if st.button("Ingest Selected Files", use_container_width=True):
                files_payload = [("files", (uf.name, uf.getvalue(), uf.type)) for uf in uploaded]
                with st.spinner(f"Ingesting {len(uploaded)} files…"):
                    try:
                        r = requests.post(f"{API_URL}/ingest/upload", files=files_payload, timeout=120)
                        if r.status_code == 200:
                            results = r.json()["results"]
                            ok = sum(1 for x in results if x.get("status") == "success")
                            st.success(f" Uploaded and ingested {ok} file(s)")
                            for x in results:
                                if x.get("status") == "success":
                                    st.write(f" **{x['doc_id']}** · {x['chunk_count']} chunks")
                                else:
                                    st.error(f" **{x['doc_id']}**: {x.get('error')}")
                            st.rerun()
                        else:
                            st.error(f"Upload failed: {r.text}")
                    except Exception as e:
                        st.error(str(e))

    gradient_divider()
    st.markdown(settings_section(" Debug: Raw Vector Search", "Test retrieval quality without LLM — great for tuning chunk size / top-k"), unsafe_allow_html=True)

    dq = st.text_input("Search query (raw vector similarity)", "quarterly inspection")
    dn = st.slider("Top-k", 1, 10, 5)
    if st.button(" Run Debug Search"):
        try:
            dr = requests.get(f"{API_URL}/debug/search?q={dq}&n={dn}", timeout=15)
            if dr.status_code == 200:
                dd = dr.json()
                st.write(f"**{len(dd['hits'])} hits** (total in DB: {dd['total_in_db']})")
                for h in dd["hits"]:
                    st.markdown(f"**[{h['rank']}]** `{h['doc_id']}` — score: **{h['score']}**")
                    st.caption(h["excerpt"])
                    gradient_divider()
            else:
                st.error(dr.text)
        except Exception as e:
            st.error(str(e))
