"""Backward-compatibility shim — all logic now lives in:

  src/ui/css.py        → GLOBAL_CSS, inject_global_css
  src/ui/helpers.py    → fmt_time, confidence_badge, post_feedback
  src/ui/particles.py  → _starfield_js, particle_starfield
  src/ui/components.py → hero_header, sidebar_brand, …

Existing imports like ``from src.ui.design_system import X`` keep working.
"""

# Re-export every public symbol from the new modules
from src.ui.css import GLOBAL_CSS, inject_global_css  # noqa: F401
from src.ui.helpers import fmt_time, confidence_badge, post_feedback  # noqa: F401
from src.ui.particles import _starfield_js, particle_starfield  # noqa: F401
from src.ui.components import (  # noqa: F401
    hero_header,
    sidebar_brand,
    sidebar_footer,
    section_header,
    gradient_divider,
    llm_status_pill,
    entity_card_html,
    neighbor_row_html,
    doc_card_html,
    citation_card,
    keypoints_box,
    chat_bubble,
    stats_grid,
    info_banner,
    settings_section,
    typing_indicator,
    skeleton_loader,
    skeleton_card,
    neon_stat_card,
    animated_counter_html,
    glow_button,
    particle_background_js,
    pipeline_trace,
    evidence_stats_row,
)
