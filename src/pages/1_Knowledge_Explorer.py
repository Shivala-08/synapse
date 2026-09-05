"""Knowledge Explorer — Interactive graph visualization page.

An Obsidian-style graph view over the existing NetworkX knowledge graph.
Users browse entities (equipment, permits, regulations, SOPs, incidents, documents)
and their relationships visually.

Refactored to use the shared design system module.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import streamlit.components.v1 as components
import requests
import json
import os
from urllib.parse import quote

try:
    from streamlit_agraph import agraph, Node, Edge, Config
    AGRAPH_AVAILABLE = True
except ImportError:
    AGRAPH_AVAILABLE = False

from src.ui.design_system import (
    inject_global_css, hero_header, gradient_divider, section_header,
    stats_grid, entity_card_html, neighbor_row_html,
)

# ── Page Config ──
st.set_page_config(
    page_title="Knowledge Explorer — Synapse",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_URL = os.getenv("API_URL", "http://localhost:8000")

# ── Node type definitions ──
ALL_NODE_TYPES = [
    "equipment", "regulation", "plant", "permit", "work_order",
    "incident", "inspection", "person", "hazard", "permit_type", "incident_type",
]

NODE_TYPE_LABELS = {
    "equipment": "🔵 ⚙️ Equipment",
    "regulation": "🔴 📜 Regulation",
    "plant": "🟢 🏭 Plant / Location",
    "permit": "🟡 🎫 Permit",
    "work_order": "🟣 📋 Work Order",
    "incident": "🌸 🚨 Incident",
    "inspection": "🌐 🔍 Inspection",
    "person": "🟠 👤 Person",
    "hazard": "🔴 ⚠️ Hazard",
    "permit_type": "🟡 🏷️ Permit Type",
    "incident_type": "🌸 🏷️ Incident Type",
}

NODE_TYPE_COLORS = {
    "equipment": "#3b82f6", "regulation": "#ef4444", "plant": "#10b981",
    "permit": "#f59e0b", "work_order": "#8b5cf6", "incident": "#ec4899",
    "inspection": "#06b6d4", "person": "#f97316", "hazard": "#dc2626",
    "permit_type": "#d97706", "incident_type": "#db2777",
}

# ══════════════════════════════════════════════════════════════════════════════
# INJECT SHARED DESIGN SYSTEM CSS
# ══════════════════════════════════════════════════════════════════════════════
inject_global_css(
    page_title="Knowledge Explorer — Synapse",
    description="Interactive knowledge explorer: Visualise and navigate complex relationships between equipment, safety regulations, plants, permits, and incidents.",
    keywords="Knowledge Graph, 3D Graph, Safety Regulations, Interactive Visualisation, NetworkX, Synapse, Streamlit",
    canonical_path="/1_Knowledge_Explorer"
)

# ── Initialize session state ──
defaults = {
    "ke_visible_nodes": set(), "ke_visible_edges": [], "ke_expanded_nodes": set(),
    "ke_selected_node": None, "ke_node_metadata_cache": {}, "ke_graph_data_cache": None,
    "ke_ai_query": None, "ke_ai_show_result": False, "ke_breadcrumb": [],
    "ke_graph_stats": None, "ke_show_table": False, "ke_path_source": "",
    "ke_path_target": "", "ke_path_result": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── Helper functions ──
def fetch_json(url, timeout=10, use_cache=True):
    if use_cache and hasattr(st.session_state, '_fetch_cache'):
        if url in st.session_state._fetch_cache:
            return st.session_state._fetch_cache[url]
    elif use_cache:
        st.session_state._fetch_cache = {}
    try:
        resp = requests.get(url, timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            if use_cache:
                if not hasattr(st.session_state, '_fetch_cache'):
                    st.session_state._fetch_cache = {}
                st.session_state._fetch_cache[url] = data
            return data
    except Exception:
        pass
    return None


def load_initial_graph():
    data = fetch_json(f"{API_URL}/graph/top?n=100")
    if data and data.get("nodes"):
        st.session_state.ke_visible_nodes = {n["id"] for n in data["nodes"]}
        st.session_state.ke_visible_edges = data.get("edges", [])
        st.session_state.ke_graph_data_cache = data
        for n in data["nodes"]:
            st.session_state.ke_expanded_nodes.add(n["id"])
            st.session_state.ke_node_metadata_cache[n["id"]] = n


def expand_node(node_id):
    if node_id in st.session_state.ke_expanded_nodes:
        return
    data = fetch_json(f"{API_URL}/graph/node/{quote(node_id)}")
    if not data or "error" in data:
        return
    st.session_state.ke_node_metadata_cache[node_id] = data
    st.session_state.ke_visible_nodes.add(node_id)
    for n in data.get("neighbors", []):
        st.session_state.ke_visible_nodes.add(n["id"])
    existing_edge_keys = {(e.get("from", ""), e.get("to", "")) for e in st.session_state.ke_visible_edges}
    for n in data.get("neighbors", []):
        key, rev_key = (node_id, n["id"]), (n["id"], node_id)
        if key not in existing_edge_keys and rev_key not in existing_edge_keys:
            st.session_state.ke_visible_edges.append({"from": node_id, "to": n["id"], "relation": n.get("relation", "related_to")})
            existing_edge_keys.add(key)
    st.session_state.ke_expanded_nodes.add(node_id)


def focus_on_node(node_id):
    data = fetch_json(f"{API_URL}/graph/node/{quote(node_id)}")
    if not data or "error" in data:
        return
    st.session_state.ke_node_metadata_cache[node_id] = data
    st.session_state.ke_visible_nodes = {node_id}
    st.session_state.ke_visible_edges = []
    for n in data.get("neighbors", []):
        st.session_state.ke_visible_nodes.add(n["id"])
        st.session_state.ke_node_metadata_cache[n["id"]] = {
            "id": n["id"], "type": n.get("type", "unknown"),
            "color": n.get("color", "#6b7280"), "degree": 0,
        }
        st.session_state.ke_visible_edges.append({
            "from": node_id, "to": n["id"], "relation": n.get("relation", "related_to"),
        })
    st.session_state.ke_expanded_nodes = {node_id}
    st.session_state.ke_selected_node = node_id
    bc = st.session_state.ke_breadcrumb
    if not bc or bc[-1] != node_id:
        bc.append(node_id)
        if len(bc) > 15:
            bc.pop(0)


def load_graph_stats():
    stats = fetch_json(f"{API_URL}/graph/stats", use_cache=False)
    if stats:
        st.session_state.ke_graph_stats = stats


# ── Handle query parameter node focusing ──
if "focus_node" in st.query_params:
    focus_node = st.query_params["focus_node"]
    st.query_params.clear()
    focus_on_node(focus_node)
    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# CINEMATIC HERO HEADER (via design_system)
# ══════════════════════════════════════════════════════════════════════════════
hero_header(
    title="Knowledge Explorer",
    subtitle="Interactive graph visualization of industrial entities and their relationships",
    badge_text="v4.0",
    stats=[{"value": "🧠", "label": "Graph View", "color": "#818cf8"}],
)

if not hasattr(st.session_state, '_fetch_cache'):
    st.session_state._fetch_cache = {}

health = fetch_json(f"{API_URL}/health", timeout=3, use_cache=False)
if not health:
    st.error("⚠️ Cannot connect to the FastAPI backend. Please start the server first.")
    st.stop()

if not st.session_state.ke_visible_nodes:
    with st.spinner("Loading initial graph..."):
        load_initial_graph()

if not st.session_state.ke_graph_stats:
    load_graph_stats()


# ══════════════════════════════════════════════════════════════════════════════
# MAIN LAYOUT: Graph Canvas & Detail Panel
# ══════════════════════════════════════════════════════════════════════════════

graph_col, detail_col = st.columns([3.5, 1.5])

# ── SIDEBAR CONTROLS ──
with st.sidebar:
    section_header("🔍", "Search & Filter", "Find entities and filter by type")

    with st.form("ke_search_form", clear_on_submit=False):
        search_query = st.text_input("Search entity", placeholder="e.g. P-101, OISD-118...", key="ke_search")
        search_submitted = st.form_submit_button("🔍 Search")

    # Interactive color legend
    st.markdown("#### 🎨 Node Types")
    enabled_types = []
    for ntype in ALL_NODE_TYPES:
        label = NODE_TYPE_LABELS.get(ntype, ntype)
        color = NODE_TYPE_COLORS.get(ntype, "#6b7280")
        if st.checkbox(label, value=True, key=f"ke_filter_{ntype}"):
            enabled_types.append(ntype)

    gradient_divider()

    num_nodes = len(st.session_state.ke_visible_nodes)
    num_edges = len(st.session_state.ke_visible_edges)
    c1, c2 = st.columns(2)
    c1.metric("Visible Nodes", num_nodes)
    c2.metric("Visible Edges", num_edges)

    gradient_divider()

    # Stacked View Actions to prevent vertical text wrapping
    if st.button("🔄 Reset View", use_container_width=True, key="ke_reset_btn"):
        for k in defaults:
            st.session_state[k] = defaults[k] if not isinstance(defaults[k], set) else set()
        st.session_state.ke_breadcrumb = []
        st.session_state.ke_path_result = None
        if hasattr(st.session_state, '_fetch_cache'):
            st.session_state._fetch_cache = {}
        st.rerun()

    if st.button("📥 Load Complete Network", use_container_width=True, key="ke_full_btn"):
        if hasattr(st.session_state, '_fetch_cache'):
            st.session_state._fetch_cache = {}
        data = fetch_json(f"{API_URL}/graph?max_nodes=500", use_cache=False)
        if data and data.get("nodes"):
            st.session_state.ke_visible_nodes = {n["id"] for n in data["nodes"]}
            st.session_state.ke_visible_edges = data.get("edges", [])
            for n in data["nodes"]:
                st.session_state.ke_expanded_nodes.add(n["id"])
            st.rerun()


    # ── Path Finding Panel ──
    gradient_divider()
    section_header("🔗", "Path Finder", "Find shortest path between two entities")

    path_source = st.text_input("From entity", placeholder="e.g. COMP-C01", key="ke_path_src")
    path_target = st.text_input("To entity", placeholder="e.g. OISD-116", key="ke_path_tgt")

    if st.button("🔍 Find Path", use_container_width=True, key="ke_find_path_btn"):
        if path_source and path_target:
            with st.spinner(f"Finding path: {path_source} → {path_target}..."):
                path_result = fetch_json(
                    f"{API_URL}/graph/path?source={quote(path_source)}&target={quote(path_target)}",
                    use_cache=False, timeout=10,
                )
                st.session_state.ke_path_result = path_result
        else:
            st.warning("Please enter both source and target entity IDs.")

    pr = st.session_state.ke_path_result
    if pr:
        if "error" in pr:
            st.error(pr["error"])
            if st.button("✕ Clear result", use_container_width=True, key="ke_clear_path_err"):
                st.session_state.ke_path_result = None
                st.rerun()
        elif pr.get("path"):
            path_len = pr.get("length", 0)
            path_nodes = pr.get("path", [])
            st.success(f"✅ Path found! **{path_len} hop(s)**")
            st.markdown('<div class="path-result">', unsafe_allow_html=True)
            for i, node_id in enumerate(path_nodes):
                color = "#6b7280"
                for pn in pr.get("path_nodes", []):
                    if pn["id"] == node_id:
                        color = pn.get("color", "#6b7280")
                        break
                st.markdown(
                    f'<span class="path-node">'
                    f'<span style="width:8px;height:8px;border-radius:50%;background:{color};display:inline-block;box-shadow:0 0 6px {color};"></span>'
                    f'{node_id}</span>',
                    unsafe_allow_html=True,
                )
                if i < len(path_nodes) - 1:
                    st.markdown('<span class="path-arrow">→</span>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            path_edges = pr.get("path_edges", [])
            if path_edges:
                with st.expander("🔗 Relationship details"):
                    for pe in path_edges:
                        st.markdown(f"**{pe['from']}** — *{pe['relation']}* → **{pe['to']}**")

            col_path_viz, col_path_clear = st.columns(2)
            with col_path_viz:
                if st.button("📊 Visualize Path", use_container_width=True, key="ke_viz_path_btn"):
                    st.session_state.ke_visible_nodes = set(path_nodes)
                    st.session_state.ke_visible_edges = []
                    for pe in path_edges:
                        st.session_state.ke_visible_edges.append(pe)
                    for node_id in path_nodes:
                        st.session_state.ke_expanded_nodes.add(node_id)
                        meta = fetch_json(f"{API_URL}/graph/node/{quote(node_id)}", timeout=5)
                        if meta and "error" not in meta:
                            st.session_state.ke_node_metadata_cache[node_id] = meta
                    st.rerun()
            with col_path_clear:
                if st.button("✕ Clear", use_container_width=True, key="ke_clear_path_result"):
                    st.session_state.ke_path_result = None
                    st.rerun()
        else:
            st.info("No path found between these entities.")
            if st.button("✕ Clear", key="ke_clear_path_notfound"):
                st.session_state.ke_path_result = None
                st.rerun()

    # ── Export Graph ──
    gradient_divider()
    st.markdown("#### 📤 Export")
    filtered_nodes = []
    for nid in st.session_state.ke_visible_nodes:
        meta = st.session_state.ke_node_metadata_cache.get(nid, {})
        ntype = meta.get("type", "unknown")
        if ntype in enabled_types:
            filtered_nodes.append({"id": nid, **meta})
    filtered_node_ids = {n["id"] for n in filtered_nodes}
    filtered_edges = [
        e for e in st.session_state.ke_visible_edges
        if e.get("from") in filtered_node_ids and e.get("to") in filtered_node_ids
    ]
    export_data = {
        "nodes": filtered_nodes,
        "edges": filtered_edges,
        "applied_filters": {"enabled_types": enabled_types, "total_visible": len(st.session_state.ke_visible_nodes)},
    }
    st.download_button(
        "📥 Export Graph (JSON)",
        data=json.dumps(export_data, indent=2, default=str),
        file_name="knowledge_graph_export.json",
        mime="application/json",
        use_container_width=True,
    )
    st.caption(f"Exporting {len(filtered_nodes)} nodes / {len(filtered_edges)} edges")


# ── Handle search ──
if search_query and search_submitted:
    st.session_state.ke_ai_query = None
    st.session_state.ke_ai_show_result = False
    search_data = fetch_json(f"{API_URL}/graph/search?q={quote(search_query)}&limit=20")
    if search_data and search_data.get("results"):
        top_result = search_data["results"][0]
        with st.spinner(f"Focusing on {top_result['id']}..."):
            focus_on_node(top_result["id"])
        if len(search_data["results"]) > 1:
            with st.sidebar:
                st.markdown("#### 🎯 Search Results")
                for r in search_data["results"][:10]:
                    if st.button(f"{r['id']} ({r['type']}, ⬡ {r['degree']})", key=f"ke_sr_{r['id']}"):
                        focus_on_node(r["id"])
                        st.rerun()
    elif search_data and search_data.get("count", 0) == 0:
        st.info(f"No entities found matching '{search_query}'")


# ── Breadcrumb Trail ──
with graph_col:
    if st.session_state.ke_breadcrumb:
        bc_html = ""
        for i, bid in enumerate(st.session_state.ke_breadcrumb):
            bc_html += f'<span class="breadcrumb-item" onclick="">{bid}</span>'
            if i < len(st.session_state.ke_breadcrumb) - 1:
                bc_html += '<span class="breadcrumb-sep"> › </span>'
        st.markdown(f'<div class="breadcrumb-trail">📍 {bc_html}</div>', unsafe_allow_html=True)


# ── GRAPH CANVAS ──
with graph_col:
    if not st.session_state.ke_visible_nodes:
        st.info("Use the sidebar to search, or click **Full Graph** to start.")
    elif not AGRAPH_AVAILABLE:
        st.warning("streamlit-agraph is not installed. Showing data as table.")
        visible_list = list(st.session_state.ke_visible_nodes)
        st.write(f"**{len(visible_list)} visible nodes**")
        st.dataframe([{"id": nid} for nid in sorted(visible_list)[:50]], use_container_width=True, height=400)
    else:
        all_nodes_data = {}
        if st.session_state.ke_graph_data_cache:
            for n in st.session_state.ke_graph_data_cache.get("nodes", []):
                all_nodes_data[n["id"]] = n

        nodes_list = []
        for nid in st.session_state.ke_visible_nodes:
            ndata = all_nodes_data.get(nid)
            if not ndata and nid in st.session_state.ke_node_metadata_cache:
                meta = st.session_state.ke_node_metadata_cache[nid]
                ndata = {"id": nid, "type": meta.get("type", "unknown"), "color": meta.get("color", "#6b7280"), "size": meta.get("degree", 5) + 5}
            if not ndata:
                ndata = {"id": nid, "type": "unknown", "color": "#6b7280", "size": 10}

            ntype = ndata.get("type", "unknown")
            if ntype not in enabled_types:
                continue

            color = ndata.get("color", NODE_TYPE_COLORS.get(ntype, "#6b7280"))
            if nid == st.session_state.ke_selected_node:
                color = "#fbbf24"  # Gold for selected node

            nodes_list.append({
                "id": nid,
                "type": ntype,
                "color": color,
                "degree": ndata.get("size", 10) - 5 if isinstance(ndata.get("size"), (int, float)) else 5
            })

        edges_list = []
        displayed_node_ids = {n["id"] for n in nodes_list}
        for edge in st.session_state.ke_visible_edges:
            src, tgt = edge.get("from", ""), edge.get("to", "")
            if src in displayed_node_ids and tgt in displayed_node_ids:
                edges_list.append({
                    "from": src,
                    "to": tgt,
                    "relation": edge.get("relation", "related_to")
                })

        if not nodes_list:
            st.info("No nodes match the current filters. Adjust filters in the sidebar.")
        else:
            st.caption(f"Showing **{len(nodes_list)}** nodes · **{len(edges_list)}** edges  ·  Click a node to expand & focus")

            # Load both 3D and 2D script files
            js_3d = ""
            js_2d = ""
            try:
                js_3d_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "static", "js", "3d-force-graph.js")
                if os.path.exists(js_3d_path):
                    with open(js_3d_path, "r", encoding="utf-8") as f:
                        js_3d = f.read()
                js_2d_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "static", "js", "force-graph.js")
                if os.path.exists(js_2d_path):
                    with open(js_2d_path, "r", encoding="utf-8") as f:
                        js_2d = f.read()
            except Exception as err:
                st.error(f"Error loading inline script: {err}")

            nodes_json = json.dumps(nodes_list)
            edges_json = json.dumps(edges_list)

            html_code = """
            <div id="3d-graph" style="width:100%;height:620px;border-radius:16px;overflow:hidden;border:1px solid rgba(99,102,241,0.25);background:#060813;position:relative;box-shadow:0 20px 60px rgba(0,0,0,0.4),0 0 30px rgba(99,102,241,0.05);"></div>
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
                const nodes = rawNodes.map(n => ({
                  id: n.id, 
                  label: n.id, 
                  type: n.type, 
                  color: n.color || '#6366f1', 
                  val: Math.max(Math.sqrt(degrees[n.id] || 1) * 1.5, 1.5)
                }));
                
                const Graph = GraphConstructor()(elem).graphData({nodes, links}).backgroundColor('#060813')
                  .nodeColor(node => node.color).nodeVal(node => node.val)
                  .nodeLabel(node => {
                    const t = (node.type || 'unknown').replace('_',' ').toUpperCase(); const c = node.color || '#6366f1'; const d = degrees[node.id] || 0;
                    return `<div style="background:rgba(9,13,22,0.96);backdrop-filter:blur(12px);border:1px solid ${c};box-shadow:0 10px 25px rgba(0,0,0,0.6),0 0 12px ${c}33;border-radius:10px;padding:12px 16px;min-width:180px;color:#f1f5f9;font-family:sans-serif;font-size:12px;pointer-events:none;line-height:1.5;"><div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;border-bottom:1px solid rgba(255,255,255,0.08);padding-bottom:6px;"><span style="width:8px;height:8px;border-radius:50%;background:${c};box-shadow:0 0 8px ${c};"></span><strong style="color:#fff;font-size:13px;">${node.id}</strong></div><div style="color:#94a3b8;font-size:10px;margin-bottom:4px;">CLASS: <span style="color:${c};font-weight:700;letter-spacing:0.03em;">${t}</span></div><div style="color:#cbd5e1;font-size:10px;">CONNECTIONS: <strong style="color:#fff;">${d}</strong></div></div>`;
                  })
                  .linkLabel(link => `<div style="background:rgba(15,23,42,0.9);border:1px solid rgba(255,255,255,0.1);border-radius:4px;padding:4px 8px;color:#cbd5e1;font-family:sans-serif;font-size:11px;">${link.relation}</div>`)
                  .linkWidth(use3D ? 0.8 : 1.2).linkColor(() => 'rgba(255, 255, 255, 0.15)');
                
                // Adjust layout forces to spread nodes out (Obsidian look)
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
                    Graph.cameraPosition({x:node.x*dr,y:node.y*dr,z:node.z*dr}, node, 1500);
                  } else {
                    Graph.centerAt(node.x, node.y, 1000);
                    Graph.zoom(2.2, 1000);
                  }
                  
                  // Notify Streamlit after animation
                  setTimeout(() => {
                    try {
                      window.parent.location.search = "?focus_node=" + encodeURIComponent(node.id);
                    } catch(e) {
                      console.warn("Failed to set query param on parent:", e);
                    }
                  }, 1200);
                });
              }
              initGraph();
            </script>
            """.replace("{nodes_json}", nodes_json).replace("{edges_json}", edges_json).replace("{js_3d}", js_3d).replace("{js_2d}", js_2d)

            components.html(html_code, height=640)

    # ── Toggle Relationship Table View ──
    if st.session_state.ke_visible_edges:
        gradient_divider()
        if st.button("📋 Toggle Relationship Table", key="ke_toggle_table"):
            st.session_state.ke_show_table = not st.session_state.ke_show_table

        if st.session_state.ke_show_table:
            st.markdown("#### 📋 Relationships")
            edge_data = []
            for e in st.session_state.ke_visible_edges:
                edge_data.append({
                    "Source": e.get("from", ""),
                    "Relation": e.get("relation", ""),
                    "Target": e.get("to", ""),
                })
            if edge_data:
                st.dataframe(edge_data, use_container_width=True, height=300)


# ── DETAIL PANEL ──
with detail_col:
    selected = st.session_state.ke_selected_node

    if selected:
        section_header("📋", "Entity Details", "Connections and metadata")

        meta = st.session_state.ke_node_metadata_cache.get(selected)
        if not meta:
            with st.spinner("Loading details..."):
                meta = fetch_json(f"{API_URL}/graph/node/{quote(selected)}")
                if meta and "error" not in meta:
                    st.session_state.ke_node_metadata_cache[selected] = meta

        if meta and "error" not in meta:
            ntype = meta.get("type", "unknown")
            color = meta.get("color", NODE_TYPE_COLORS.get(ntype, "#6b7280"))
            degree = meta.get("degree", 0)
            doc_id = meta.get("doc_id")

            st.markdown(entity_card_html(selected, ntype, color, degree), unsafe_allow_html=True)

            if doc_id:
                st.markdown(f"**📄 Source Document:** `{doc_id}`")

            gradient_divider()

            st.markdown("#### 🔗 Connected Entities")
            neighbor_types = meta.get("neighbor_types", {})
            if neighbor_types:
                for ntype_key, nids in sorted(neighbor_types.items()):
                    ncolor = NODE_TYPE_COLORS.get(ntype_key, "#6b7280")
                    label = NODE_TYPE_LABELS.get(ntype_key, ntype_key)
                    st.markdown(f"**{label}** ({len(nids)})")
                    for nid in nids[:15]:
                        relation = ""
                        for nb in meta.get("neighbors", []):
                            if nb["id"] == nid:
                                relation = nb.get("relation", "")
                                break
                        st.markdown(neighbor_row_html(nid, ncolor, relation), unsafe_allow_html=True)
                        if st.button(f"→ {nid}", key=f"ke_nav_{nid}", help=f"Focus on {nid}"):
                            focus_on_node(nid)
                            st.rerun()
                    if len(nids) > 15:
                        st.caption(f"...and {len(nids) - 15} more")
            else:
                st.info("No direct connections found.")

            gradient_divider()

            # Quick path
            st.markdown("#### 🔗 Quick Path")
            path_target_quick = st.text_input("Find path to...", placeholder="e.g. OISD-116", key="ke_quick_path")
            if st.button("🔍 Find Path", key="ke_quick_path_btn", use_container_width=True):
                if path_target_quick:
                    with st.spinner(f"Finding path: {selected} → {path_target_quick}..."):
                        pr = fetch_json(
                            f"{API_URL}/graph/path?source={quote(selected)}&target={quote(path_target_quick)}",
                            use_cache=False, timeout=10,
                        )
                        if pr and "error" not in pr and pr.get("path"):
                            st.success(f"✅ Path: **{pr['length']} hop(s)**")
                            path_display = " → ".join(pr["path"])
                            st.markdown(f"`{path_display}`")
                        elif pr:
                            st.error(pr.get("error", "No path found"))

            gradient_divider()

            # Ask AI
            st.markdown("#### 🤖 Ask AI")
            entity_context = f"Tell me about {selected} ({ntype}). What are its relationships, regulations, and history?"
            if st.button("🤖 Ask AI about this", key="ke_ask_ai", use_container_width=True):
                st.session_state.ke_ai_query = entity_context
                st.session_state.ke_ai_show_result = True
                st.rerun()

            if st.session_state.get("ke_ai_show_result") and st.session_state.get("ke_ai_query"):
                ai_query = st.session_state.ke_ai_query
                st.info(f"**Querying:** {ai_query}")
                with st.spinner("AI is analyzing this entity..."):
                    try:
                        payload = {"question": ai_query, "top_k": 5}
                        doc_type_map = {
                            "regulation": "regulation",
                            "work_order": "work_order",
                            "permit": "permit",
                            "incident": "incident_report",
                            "sop": "sop"
                        }
                        if ntype in doc_type_map:
                            payload["filters"] = {"doc_type": doc_type_map[ntype]}
                            st.caption(f"⚡ Applying metadata pre-filter: `doc_type` = `{doc_type_map[ntype]}`")
                        
                        resp = requests.post(f"{API_URL}/query", json=payload, timeout=120)
                        if resp.status_code == 200:
                            data = resp.json()
                            st.markdown(f"**Confidence:** `{data.get('confidence', 'Unknown')}`")
                            if data.get("entities_used"):
                                st.markdown(f"**Entities referenced:** {', '.join(data['entities_used'][:5])}")
                            st.markdown(data.get("answer", "No answer found."))
                            if data.get("sources"):
                                with st.expander("📚 View Sources"):
                                    for idx, src in enumerate(data["sources"]):
                                        st.markdown(f"**[{idx+1}] {src['citation']}** (Distance: `{src.get('distance', 0):.4f}`)")
                                        st.caption(f'Excerpt: *"{src.get("excerpt", "")[:200]}..."*')
                        else:
                            st.error(f"Query failed (Status {resp.status_code})")
                    except Exception as e:
                        st.error(f"Failed to query AI: {e}")

                if st.button("Clear", key="ke_ai_clear"):
                    st.session_state.ke_ai_query = None
                    st.session_state.ke_ai_show_result = False
                    st.rerun()

        elif meta and "error" in meta:
            st.error(f"Entity not found: {meta['error']}")
        else:
            st.warning("Could not load entity details.")
    else:
        section_header("📋", "Entity Details", "Click a node to explore")
        st.info("Click a node in the graph to see its details here.")
        gradient_divider()
        st.markdown("""
**How to use Knowledge Explorer:**

1. 🔍 **Search** for an entity by name in the sidebar
2. ☑️ **Filter** by node type using the color legend checkboxes
3. 🖱️ **Click** a node to expand its neighbors and see details
4. 🔗 **Path Finder** — find shortest path between any two entities
5. 📊 **Stats** — view graph statistics in the sidebar
6. 📋 **Relationship Table** — toggle to see all edges in a table
7. 📤 **Export** — download the visible graph as JSON
8. 📍 **Breadcrumbs** — navigate back through your exploration trail
        """)
