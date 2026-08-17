"""Shared UI components and design system for Synapse.

Re-exports everything from sub-modules so existing imports like
``from src.ui.design_system import inject_global_css`` keep working.
"""

from src.ui.css import GLOBAL_CSS, inject_global_css
from src.ui.helpers import fmt_time, confidence_badge, post_feedback
from src.ui.particles import _starfield_js, particle_starfield
from src.ui.components import (
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
