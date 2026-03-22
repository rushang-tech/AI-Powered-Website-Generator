from __future__ import annotations

import json
import re
from dataclasses import replace
from copy import deepcopy
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

from app.services.ai_provider import AIProvider, AIProviderUnavailableError, get_default_provider, require_default_provider
from app.services.contracts import (
    GeneratedContent,
    GenerationStage,
    ProjectManifest,
    ValidationResult,
    VariantPayload,
)
from app.services.taste_engine import (
    BriefInput,
    LAYOUT_LIBRARY,
    NAVIGATION_PATTERNS,
    PagePlan,
    RenderPlan,
    build_render_variants,
    normalize_brief,
    remix_render_plan,
)
from app.services.visual_asset_service import build_variant_visuals

THEME_MAP: dict[str, dict[str, str]] = {
    "modern_editorial": {
        "key": "modern_editorial",
        "name": "Modern Editorial",
        "canvas_background": "linear-gradient(180deg, #eff3f8 0%, #dde4ec 100%)",
        "panel_background": "rgba(252, 254, 255, 0.88)",
        "surface": "#fbfdff",
        "surface_alt": "#eef3f8",
        "text": "#111827",
        "muted": "#586273",
        "accent": "#88d92f",
        "accent_soft": "rgba(136, 217, 47, 0.16)",
        "border": "rgba(17, 24, 39, 0.12)",
        "button_bg": "#111827",
        "button_text": "#f7fafc",
        "shadow": "0 22px 60px rgba(29, 45, 68, 0.12)",
        "display_font": "'Cormorant Garamond', serif",
        "body_font": "'Space Grotesk', sans-serif",
        "frame_background": "linear-gradient(180deg, rgba(244, 248, 252, 0.98) 0%, rgba(224, 232, 241, 0.98) 100%)",
        "frame_border": "rgba(17, 24, 39, 0.1)",
        "frame_glow": "0 24px 80px rgba(39, 54, 74, 0.14)",
        "backdrop_overlay": "linear-gradient(135deg, rgba(255, 255, 255, 0.34), rgba(136, 217, 47, 0.05))",
        "spotlight": "radial-gradient(circle at 18% 12%, rgba(255, 255, 255, 0.82), transparent 34%)",
        "card_fill": "rgba(255, 255, 255, 0.9)",
        "card_stroke": "rgba(17, 24, 39, 0.08)",
        "pill_background": "rgba(249, 252, 255, 0.86)",
        "button_shadow": "0 16px 36px rgba(17, 24, 39, 0.16)",
        "section_radius": "22px",
        "card_radius": "18px",
    },
    "luxury_serif": {
        "key": "luxury_serif",
        "name": "Luxury Serif",
        "canvas_background": "radial-gradient(circle at top, rgba(228, 190, 121, 0.18), transparent 36%), linear-gradient(180deg, #161110 0%, #261a14 100%)",
        "panel_background": "rgba(28, 20, 16, 0.78)",
        "surface": "#1d1512",
        "surface_alt": "#2d211b",
        "text": "#f7ead7",
        "muted": "#c1aa8f",
        "accent": "#dfb36c",
        "accent_soft": "rgba(223, 179, 108, 0.18)",
        "border": "rgba(223, 179, 108, 0.16)",
        "button_bg": "#dfb36c",
        "button_text": "#17110d",
        "shadow": "0 30px 80px rgba(0, 0, 0, 0.34)",
        "display_font": "'Cormorant Garamond', serif",
        "body_font": "'Manrope', sans-serif",
        "frame_background": "linear-gradient(180deg, rgba(24, 17, 15, 0.98) 0%, rgba(40, 29, 23, 0.98) 100%)",
        "frame_border": "rgba(223, 179, 108, 0.14)",
        "frame_glow": "0 28px 82px rgba(4, 2, 1, 0.4)",
        "backdrop_overlay": "linear-gradient(160deg, rgba(255, 245, 230, 0.06), rgba(223, 179, 108, 0.12))",
        "spotlight": "radial-gradient(circle at 78% 4%, rgba(255, 232, 198, 0.16), transparent 28%)",
        "card_fill": "rgba(31, 23, 18, 0.86)",
        "card_stroke": "rgba(223, 179, 108, 0.12)",
        "pill_background": "rgba(40, 29, 23, 0.9)",
        "button_shadow": "0 18px 42px rgba(223, 179, 108, 0.14)",
        "section_radius": "18px",
        "card_radius": "16px",
    },
    "playful_blocks": {
        "key": "playful_blocks",
        "name": "Playful Blocks",
        "canvas_background": "linear-gradient(135deg, #fff4bf 0%, #ffd1cb 46%, #c9f4ff 100%)",
        "panel_background": "rgba(255, 250, 240, 0.92)",
        "surface": "#fffdf8",
        "surface_alt": "#ffe79b",
        "text": "#172b57",
        "muted": "#395c92",
        "accent": "#ff5a36",
        "accent_soft": "rgba(255, 90, 54, 0.18)",
        "border": "rgba(23, 43, 87, 0.18)",
        "button_bg": "#2251d1",
        "button_text": "#fff7d6",
        "shadow": "10px 10px 0 rgba(23, 43, 87, 0.2)",
        "display_font": "'Bricolage Grotesque', sans-serif",
        "body_font": "'Manrope', sans-serif",
        "frame_background": "linear-gradient(135deg, rgba(255, 247, 220, 0.98) 0%, rgba(255, 209, 203, 0.98) 56%, rgba(201, 244, 255, 0.98) 100%)",
        "frame_border": "rgba(23, 43, 87, 0.14)",
        "frame_glow": "0 22px 58px rgba(23, 43, 87, 0.16)",
        "backdrop_overlay": "linear-gradient(145deg, rgba(255, 255, 255, 0.24), rgba(34, 81, 209, 0.08))",
        "spotlight": "radial-gradient(circle at 12% 18%, rgba(255, 255, 255, 0.82), transparent 26%)",
        "card_fill": "rgba(255, 254, 248, 0.92)",
        "card_stroke": "rgba(23, 43, 87, 0.14)",
        "pill_background": "rgba(255, 255, 255, 0.72)",
        "button_shadow": "8px 10px 0 rgba(23, 43, 87, 0.16)",
        "section_radius": "28px",
        "card_radius": "22px",
    },
    "cyber_signal": {
        "key": "cyber_signal",
        "name": "Cyber Signal",
        "canvas_background": "radial-gradient(circle at top right, rgba(0, 227, 204, 0.2), transparent 32%), linear-gradient(180deg, #08121f 0%, #050b13 100%)",
        "panel_background": "rgba(8, 18, 31, 0.82)",
        "surface": "#0b1624",
        "surface_alt": "#102235",
        "text": "#dafbff",
        "muted": "#89b6c7",
        "accent": "#39e0c9",
        "accent_soft": "rgba(57, 224, 201, 0.16)",
        "border": "rgba(57, 224, 201, 0.18)",
        "button_bg": "#39e0c9",
        "button_text": "#041016",
        "shadow": "0 26px 80px rgba(1, 15, 26, 0.55)",
        "display_font": "'Space Grotesk', sans-serif",
        "body_font": "'Manrope', sans-serif",
        "frame_background": "linear-gradient(180deg, rgba(8, 18, 31, 0.98) 0%, rgba(5, 11, 19, 0.98) 100%)",
        "frame_border": "rgba(57, 224, 201, 0.16)",
        "frame_glow": "0 32px 96px rgba(0, 14, 28, 0.6)",
        "backdrop_overlay": "linear-gradient(145deg, rgba(8, 18, 31, 0.1), rgba(57, 224, 201, 0.08))",
        "spotlight": "radial-gradient(circle at 84% 14%, rgba(57, 224, 201, 0.2), transparent 24%)",
        "card_fill": "rgba(11, 22, 36, 0.78)",
        "card_stroke": "rgba(57, 224, 201, 0.12)",
        "pill_background": "rgba(8, 18, 31, 0.64)",
        "button_shadow": "0 18px 42px rgba(0, 227, 204, 0.18)",
        "section_radius": "28px",
        "card_radius": "22px",
    },
    "brutalist_poster": {
        "key": "brutalist_poster",
        "name": "Brutalist Poster",
        "canvas_background": "linear-gradient(135deg, #fff7ec 0%, #f0eadf 100%)",
        "panel_background": "rgba(255, 249, 239, 0.94)",
        "surface": "#fff8ee",
        "surface_alt": "#efe1cd",
        "text": "#121212",
        "muted": "#565656",
        "accent": "#ff4a1f",
        "accent_soft": "rgba(255, 74, 31, 0.16)",
        "border": "rgba(18, 18, 18, 0.18)",
        "button_bg": "#121212",
        "button_text": "#fff7ec",
        "shadow": "12px 12px 0 rgba(18, 18, 18, 0.18)",
        "display_font": "'Bricolage Grotesque', sans-serif",
        "body_font": "'Space Grotesk', sans-serif",
        "frame_background": "linear-gradient(135deg, rgba(255, 247, 236, 0.98) 0%, rgba(240, 234, 223, 0.98) 100%)",
        "frame_border": "rgba(18, 18, 18, 0.14)",
        "frame_glow": "12px 14px 0 rgba(18, 18, 18, 0.12)",
        "backdrop_overlay": "linear-gradient(135deg, rgba(255, 255, 255, 0.18), rgba(255, 74, 31, 0.1))",
        "spotlight": "radial-gradient(circle at 16% 14%, rgba(255, 255, 255, 0.62), transparent 24%)",
        "card_fill": "rgba(255, 250, 242, 0.94)",
        "card_stroke": "rgba(18, 18, 18, 0.12)",
        "pill_background": "rgba(255, 250, 242, 0.88)",
        "button_shadow": "8px 10px 0 rgba(18, 18, 18, 0.18)",
        "section_radius": "14px",
        "card_radius": "12px",
    },
    "warm_gradient": {
        "key": "warm_gradient",
        "name": "Warm Gradient",
        "canvas_background": "radial-gradient(circle at top left, rgba(255, 174, 120, 0.34), transparent 30%), linear-gradient(180deg, #fff1d7 0%, #ffc9b7 46%, #ffd9d5 100%)",
        "panel_background": "rgba(255, 247, 238, 0.9)",
        "surface": "#fff8f1",
        "surface_alt": "#ffd9c9",
        "text": "#3a231f",
        "muted": "#85584f",
        "accent": "#f26d3d",
        "accent_soft": "rgba(242, 109, 61, 0.16)",
        "border": "rgba(58, 35, 31, 0.12)",
        "button_bg": "#f26d3d",
        "button_text": "#fff8f1",
        "shadow": "0 24px 68px rgba(178, 94, 59, 0.2)",
        "display_font": "'Fraunces', serif",
        "body_font": "'Manrope', sans-serif",
        "frame_background": "linear-gradient(180deg, rgba(255, 241, 215, 0.98) 0%, rgba(255, 215, 201, 0.98) 58%, rgba(255, 224, 219, 0.98) 100%)",
        "frame_border": "rgba(145, 75, 48, 0.1)",
        "frame_glow": "0 26px 72px rgba(178, 94, 59, 0.18)",
        "backdrop_overlay": "linear-gradient(135deg, rgba(255, 255, 255, 0.3), rgba(242, 109, 61, 0.1))",
        "spotlight": "radial-gradient(circle at 14% 12%, rgba(255, 255, 255, 0.82), transparent 28%)",
        "card_fill": "rgba(255, 251, 245, 0.88)",
        "card_stroke": "rgba(133, 88, 79, 0.1)",
        "pill_background": "rgba(255, 244, 235, 0.84)",
        "button_shadow": "0 18px 42px rgba(242, 109, 61, 0.2)",
        "section_radius": "32px",
        "card_radius": "26px",
    },
    "coastal_breeze": {
        "key": "coastal_breeze",
        "name": "Coastal Breeze",
        "canvas_background": "radial-gradient(circle at top right, rgba(122, 210, 227, 0.26), transparent 30%), linear-gradient(180deg, #f4fbff 0%, #e7f7f7 52%, #f6f1e8 100%)",
        "panel_background": "rgba(247, 252, 253, 0.84)",
        "surface": "#f7fdff",
        "surface_alt": "#e3f3f2",
        "text": "#103549",
        "muted": "#4f7081",
        "accent": "#0ea5b7",
        "accent_soft": "rgba(14, 165, 183, 0.14)",
        "border": "rgba(16, 53, 73, 0.12)",
        "button_bg": "#103549",
        "button_text": "#eefcfe",
        "shadow": "0 26px 72px rgba(28, 82, 102, 0.14)",
        "display_font": "'Fraunces', serif",
        "body_font": "'Space Grotesk', sans-serif",
        "frame_background": "linear-gradient(180deg, rgba(244, 251, 255, 0.98) 0%, rgba(230, 246, 245, 0.98) 60%, rgba(245, 239, 231, 0.98) 100%)",
        "frame_border": "rgba(16, 53, 73, 0.1)",
        "frame_glow": "0 30px 82px rgba(21, 84, 109, 0.16)",
        "backdrop_overlay": "linear-gradient(145deg, rgba(255, 255, 255, 0.32), rgba(14, 165, 183, 0.06))",
        "spotlight": "radial-gradient(circle at 86% 10%, rgba(255, 255, 255, 0.74), transparent 26%)",
        "card_fill": "rgba(248, 253, 254, 0.82)",
        "card_stroke": "rgba(16, 53, 73, 0.08)",
        "pill_background": "rgba(255, 255, 255, 0.7)",
        "button_shadow": "0 18px 44px rgba(14, 165, 183, 0.18)",
        "section_radius": "34px",
        "card_radius": "26px",
    },
    "mono_signal": {
        "key": "mono_signal",
        "name": "Mono Signal",
        "canvas_background": "linear-gradient(180deg, #f4f4f1 0%, #e9e9e4 100%)",
        "panel_background": "rgba(252, 252, 248, 0.86)",
        "surface": "#fbfbf7",
        "surface_alt": "#ecece6",
        "text": "#0e0f0d",
        "muted": "#4e524b",
        "accent": "#9de43a",
        "accent_soft": "rgba(157, 228, 58, 0.16)",
        "border": "rgba(14, 15, 13, 0.14)",
        "button_bg": "#0e0f0d",
        "button_text": "#f5f7ef",
        "shadow": "0 24px 64px rgba(23, 25, 19, 0.12)",
        "display_font": "'Space Grotesk', sans-serif",
        "body_font": "'Manrope', sans-serif",
        "frame_background": "linear-gradient(180deg, rgba(244, 244, 241, 0.98) 0%, rgba(233, 233, 228, 0.98) 100%)",
        "frame_border": "rgba(14, 15, 13, 0.12)",
        "frame_glow": "0 28px 78px rgba(23, 25, 19, 0.14)",
        "backdrop_overlay": "linear-gradient(135deg, rgba(255, 255, 255, 0.22), rgba(157, 228, 58, 0.04))",
        "spotlight": "radial-gradient(circle at 18% 10%, rgba(255, 255, 255, 0.64), transparent 28%)",
        "card_fill": "rgba(252, 252, 248, 0.84)",
        "card_stroke": "rgba(14, 15, 13, 0.1)",
        "pill_background": "rgba(247, 248, 242, 0.76)",
        "button_shadow": "0 18px 40px rgba(14, 15, 13, 0.18)",
        "section_radius": "18px",
        "card_radius": "14px",
    },
    "botanical_noir": {
        "key": "botanical_noir",
        "name": "Botanical Noir",
        "canvas_background": "radial-gradient(circle at top left, rgba(123, 168, 118, 0.18), transparent 28%), linear-gradient(180deg, #10231f 0%, #0d1a18 100%)",
        "panel_background": "rgba(15, 31, 27, 0.84)",
        "surface": "#122924",
        "surface_alt": "#17352e",
        "text": "#ecf4e8",
        "muted": "#a6b7a4",
        "accent": "#91c36f",
        "accent_soft": "rgba(145, 195, 111, 0.16)",
        "border": "rgba(145, 195, 111, 0.16)",
        "button_bg": "#91c36f",
        "button_text": "#10231f",
        "shadow": "0 28px 84px rgba(4, 12, 10, 0.44)",
        "display_font": "'Cormorant Garamond', serif",
        "body_font": "'Manrope', sans-serif",
        "frame_background": "linear-gradient(180deg, rgba(16, 35, 31, 0.98) 0%, rgba(13, 26, 24, 0.98) 100%)",
        "frame_border": "rgba(145, 195, 111, 0.14)",
        "frame_glow": "0 32px 92px rgba(3, 10, 8, 0.52)",
        "backdrop_overlay": "linear-gradient(145deg, rgba(16, 35, 31, 0.14), rgba(145, 195, 111, 0.06))",
        "spotlight": "radial-gradient(circle at 82% 12%, rgba(145, 195, 111, 0.16), transparent 24%)",
        "card_fill": "rgba(18, 41, 36, 0.8)",
        "card_stroke": "rgba(145, 195, 111, 0.1)",
        "pill_background": "rgba(18, 34, 29, 0.78)",
        "button_shadow": "0 18px 44px rgba(145, 195, 111, 0.16)",
        "section_radius": "30px",
        "card_radius": "22px",
    },
    "studio_pop": {
        "key": "studio_pop",
        "name": "Studio Pop",
        "canvas_background": "radial-gradient(circle at top left, rgba(255, 125, 87, 0.22), transparent 30%), linear-gradient(135deg, #f7f2e8 0%, #e8eeff 48%, #fff2cf 100%)",
        "panel_background": "rgba(252, 249, 242, 0.88)",
        "surface": "#fffaf1",
        "surface_alt": "#e7edff",
        "text": "#13254d",
        "muted": "#4b5d84",
        "accent": "#2451ff",
        "accent_soft": "rgba(36, 81, 255, 0.14)",
        "border": "rgba(19, 37, 77, 0.14)",
        "button_bg": "#2451ff",
        "button_text": "#fff8ee",
        "shadow": "0 26px 70px rgba(36, 81, 255, 0.16)",
        "display_font": "'Bricolage Grotesque', sans-serif",
        "body_font": "'Space Grotesk', sans-serif",
        "frame_background": "linear-gradient(135deg, rgba(247, 242, 232, 0.98) 0%, rgba(231, 237, 255, 0.98) 52%, rgba(255, 242, 207, 0.98) 100%)",
        "frame_border": "rgba(19, 37, 77, 0.12)",
        "frame_glow": "0 28px 80px rgba(28, 44, 113, 0.18)",
        "backdrop_overlay": "linear-gradient(145deg, rgba(255, 255, 255, 0.16), rgba(36, 81, 255, 0.08))",
        "spotlight": "radial-gradient(circle at 14% 12%, rgba(255, 255, 255, 0.78), transparent 28%)",
        "card_fill": "rgba(255, 250, 241, 0.86)",
        "card_stroke": "rgba(19, 37, 77, 0.1)",
        "pill_background": "rgba(255, 255, 255, 0.72)",
        "button_shadow": "0 18px 46px rgba(36, 81, 255, 0.2)",
        "section_radius": "22px",
        "card_radius": "18px",
    },
}

TEMPLATE_CATALOG: dict[str, dict[str, str]] = {
    "store": {"template_file": "generated/store_builder.html"},
    "saas": {"template_file": "generated/saas_builder.html"},
    "business": {"template_file": "generated/business_builder.html"},
    "portfolio": {"template_file": "generated/portfolio_builder.html"},
    "landing": {"template_file": "generated/site_builder.html"},
    "product": {"template_file": "generated/site_builder.html"},
}

STATUS_BLUEPRINT = (
    ("validate", "Validating prompt", "Brief normalized and request sanitized."),
    ("classify", "Classifying intent", "Choosing deterministic structure and layout candidates."),
    ("generate", "Generating content", "Requesting structured JSON content for the selected render plans."),
    ("validate_schema", "Validating schema", "Filling defaults, stripping unsupported fields, and recording fallbacks."),
    ("render", "Rendering preview", "Preparing iframe-ready HTML and studio metadata."),
    ("export", "Export ready", "Project can be exported as source ZIP at any time."),
)

SECTION_CONTENT_MAP: dict[str, tuple[str, ...]] = {
    "hero": ("hero_eyebrow", "hero_title", "hero_subtitle", "cta_text", "cta_note", "price_badge", "about_text"),
    "collections": ("collections_title", "collections_intro", "collections"),
    "products": ("products_title", "products_intro", "products"),
    "metrics": (
        "metrics_title",
        "metrics_intro",
        "stat_1_value",
        "stat_1_label",
        "stat_2_value",
        "stat_2_label",
        "stat_3_value",
        "stat_3_label",
    ),
    "features": ("features_title", "features_intro", "features"),
    "workflows": ("workflows_title", "workflows_intro", "workflows"),
    "projects": ("projects_title", "projects_intro", "projects"),
    "pricing": ("pricing_title", "pricing_intro", "offers"),
    "proof": ("proof_quote", "proof_author"),
    "cta": ("cta_text", "cta_note"),
    "about": ("about_title", "about_intro", "about_text"),
    "capabilities": ("capabilities_title", "capabilities_intro", "capabilities"),
    "services": ("services_title", "services_intro", "services"),
    "process": ("process_title", "process_intro", "process_steps"),
}

COLOR_HEX_MAP: dict[str, str] = {
    "black": "#05060a",
    "white": "#f8fafc",
    "gray": "#6b7280",
    "grey": "#6b7280",
    "silver": "#cbd5e1",
    "cream": "#f5efe3",
    "beige": "#e9ddcb",
    "brown": "#8b5e3c",
    "gold": "#d4a24c",
    "amber": "#f59e0b",
    "yellow": "#facc15",
    "orange": "#f97316",
    "red": "#ef4444",
    "pink": "#ec4899",
    "magenta": "#d946ef",
    "purple": "#8b5cf6",
    "violet": "#7c3aed",
    "indigo": "#6366f1",
    "blue": "#3b82f6",
    "cyan": "#22d3ee",
    "teal": "#14b8a6",
    "green": "#22c55e",
    "lime": "#84cc16",
}

NEUTRAL_COLOR_KEYS = {"black", "white", "gray", "grey", "silver", "cream", "beige", "brown"}

THEME_REQUEST_HINTS = (
    "theme",
    "palette",
    "color",
    "colors",
    "colour",
    "colours",
    "background",
    "accent",
    "dark mode",
    "light mode",
)

ART_DIRECTION_HINTS: dict[str, tuple[str, ...]] = {
    "modern_editorial": ("editorial", "clean", "minimal", "professional", "sleek"),
    "luxury_serif": ("luxury", "premium", "elegant", "serif", "timeless"),
    "playful_blocks": ("playful", "fun", "friendly", "quirky", "vibrant"),
    "cyber_signal": ("cyber", "futuristic", "neon", "tech noir", "hacker", "glow"),
    "brutalist_poster": ("brutalist", "poster", "graphic", "raw", "experimental"),
    "warm_gradient": ("warm", "gradient", "sunset", "approachable", "optimistic"),
    "coastal_breeze": ("coastal", "ocean", "sea", "breeze", "resort"),
    "mono_signal": ("monochrome", "black and white", "swiss", "grid", "minimalist"),
    "botanical_noir": ("botanical", "organic", "earthy", "forest", "garden", "noir"),
    "studio_pop": ("studio", "magazine", "expressive", "electric", "cobalt", "pop"),
}

DENSITY_HINTS: dict[str, tuple[str, ...]] = {
    "airy": ("airy", "spacious", "more whitespace", "more white space", "less dense", "less crowded"),
    "balanced": ("balanced",),
    "dense": ("dense", "denser", "more detailed", "more information", "more content", "tighter"),
}

MOTION_HINTS: dict[str, tuple[str, ...]] = {
    "calm": ("calm", "subtle motion", "less motion", "less animation", "minimal motion", "static"),
    "moderate": ("moderate motion",),
    "energetic": ("energetic", "more motion", "more animation", "kinetic", "dynamic", "animated"),
}

COPY_CHANGE_HINTS = (
    "copy",
    "headline",
    "subheadline",
    "title",
    "subtitle",
    "text",
    "wording",
    "message",
    "messaging",
    "cta",
    "rewrite",
    "reword",
)

ART_DIRECTION_COPY_GUIDES: dict[str, str] = {
    "modern_editorial": "Write with composed precision and clear sequencing. Let the copy feel sharp, spacious, and deliberate.",
    "luxury_serif": "Write with restraint, texture, and premium confidence. Favor sensory details and elegant understatement.",
    "playful_blocks": "Write with bright momentum and human warmth. Keep the energy upbeat without becoming childish filler.",
    "cyber_signal": "Write with punch, contrast, and a sense of forward motion. Use crisp verbs and specific stakes.",
    "brutalist_poster": "Write with tension and conviction. Prefer cut-down, decisive lines over polished corporate phrasing.",
    "warm_gradient": "Write with optimism and emotional clarity. Make the brand feel welcoming, modern, and easy to trust.",
    "coastal_breeze": "Write with lightness and clarity. Keep the tone fresh, breathable, and quietly premium.",
    "mono_signal": "Write with precision and restraint. Favor short, exact phrasing with strong contrast and no fluff.",
    "botanical_noir": "Write with calm confidence and tactile detail. Let the copy feel grounded, natural, and premium without drifting into cliches.",
    "studio_pop": "Write with expressive rhythm and confident creative energy. Make the language feel designed, not merely descriptive.",
}

LAYOUT_COPY_GUIDES: dict[str, str] = {
    "editorial_lookbook": "Let the hero and collection frames feel styled and image-led before the product grid takes over.",
    "conversion_storefront": "Move quickly from product promise to shoppable grid and proof without losing momentum.",
    "catalog_first": "Make browsing feel easy, abundant, and structured around products instead of brand monologue.",
    "product_story": "Introduce the software through a clear narrative arc, then ground it in visible workflows.",
    "dashboard_proof": "Lead with product evidence and tangible outputs before feature explanation.",
    "workflow_first": "Make the workflow the star so the product feels concrete before pricing or proof.",
    "split_hero": "Open with a clear point of view, then let the supporting content widen the case.",
    "staggered_bands": "Let each section shift the rhythm slightly so the page feels paced instead of repetitive.",
    "immersive_layers": "Use more atmospheric and cinematic phrasing that rewards scrolling.",
    "proof_first": "Earn trust immediately, then bring the pitch in after credibility is established.",
    "casebook_editorial": "Treat the work like a curated body of projects with enough framing to feel authored.",
    "gallery_wall": "Let the projects behave like a visual wall first, with short framing that supports the imagery.",
    "minimal_identity": "Keep the portfolio lean, authored, and identity-led instead of overexplained.",
    "editorial_casebook": "Treat the page like a curated body of work with a strong editorial spine.",
    "masonry_showcase": "Let each project feel visually distinct and collectible rather than part of a flat list.",
    "minimal_cv": "Stay precise and useful. Keep the language lean and grounded.",
    "story_panels": "Make each section feel like a scene that adds a different layer to the narrative.",
    "service_story": "Frame the offer as a clear service narrative: what you do, how you work, and why trust is deserved.",
    "trust_first": "Use proof to earn attention early, then let services and process explain the delivery.",
    "offer_stack": "Make the offer structure easy to scan and compare while still feeling premium and current.",
    "pricing_first": "Frame the buying decision clearly and make the offer structure easy to compare.",
    "feature_scroll": "Reveal the product through workflow-oriented sections, not a generic feature dump.",
    "contrast_split": "Balance premium positioning with practical proof so the page feels both elevated and usable.",
    "launch_countdown": "Lean into urgency, anticipation, and release energy without sounding gimmicky.",
}

TEMPLATE_COPY_GUIDES: dict[str, str] = {
    "store": "The page should feel like a modern storefront with collections, product abundance, and clear shoppable hierarchy.",
    "saas": "The page should make the software feel tangible through workflows, interface proof, and decisive product framing.",
    "business": "The page should make the services, trust signals, and delivery process feel current, clear, and credible.",
    "landing": "The page should feel like a focused argument for one offer and one next step.",
    "portfolio": "The page should feel like authored work with perspective, curation, and memorable framing.",
    "product": "The page should make the product and pricing feel tangible fast, then deepen trust through proof.",
}

TEMPLATE_CONTENT_GUIDES: dict[str, str] = {
    "store": "Write image-forward collection copy, product names, and short merch-style descriptions that support browsing.",
    "saas": "Write product marketing copy that references workflows, dashboards, proofs, and practical adoption value.",
    "portfolio": "Write with authorship, curation, and strong project framing rather than generic creator bio filler.",
    "business": "Write like a modern service company: clear offers, trust, process, and outcome-oriented messaging.",
}


def _taste_model(provider: AIProvider | None) -> object | None:
    if provider is None:
        return None

    class ProviderModelAdapter:
        def __init__(self, inner: AIProvider) -> None:
            self._inner = inner

        def generate_content(self, prompt: str) -> SimpleNamespace:
            return SimpleNamespace(text=self._inner.generate_text(prompt))

    return ProviderModelAdapter(provider)


def _require_provider(provider: AIProvider | None, *, action: str) -> AIProvider:
    if provider is not None:
        return provider
    return require_default_provider(action=action)


def _slot_fallback(slot_name: str, *, render_plan: RenderPlan, brief: BriefInput) -> str:
    name = (brief.name or "your brand").strip()
    industry = render_plan.industry.replace("_", " ").title()
    audience = (brief.audience or "general audiences").strip().lower()
    tone = (brief.brand_tone or render_plan.art_direction.replace("_", " ")).strip().lower()
    art_direction = render_plan.art_direction.replace("_", " ")
    template_defaults: dict[str, dict[str, str]] = {
        "store": {
            "hero_title": f"{name.title()} turns browsing into a visual event." if brief.name else "A storefront built to be explored.",
            "hero_subtitle": f"Designed for {audience} with a {tone} merchandising rhythm, sharper product framing, and a more current storefront feel.",
            "cta_text": "Shop now",
            "cta_note": "Lead with the collection story, then make the product grid feel irresistible.",
            "collections_title": f"The {name.title()} edit." if brief.name else "Collections worth opening first.",
            "collections_intro": "Frame the collection blocks like curated shop moments, not generic promo cards.",
            "products_title": "A grid with real momentum.",
            "products_intro": "Make the product list feel abundant, scannable, and ready to browse.",
            "proof_quote": "It feels like a modern storefront, not a brochure pretending to sell products.",
            "proof_author": "Store review",
        },
        "saas": {
            "hero_title": f"{name.title()} makes workflows feel visible." if brief.name else "Software people can understand in one screen.",
            "hero_subtitle": f"Built for {audience} with a {tone} product story, clearer workflow proof, and a modern SaaS rhythm.",
            "cta_text": "Start trial",
            "cta_note": "Make the workflow tangible fast, then let proof and pricing support the decision.",
            "workflows_title": f"How {name.title()} actually runs." if brief.name else "What the workflow looks like in practice.",
            "workflows_intro": "Explain the operating flow in concrete, dashboard-friendly language rather than abstract feature claims.",
            "features_title": f"What {name.title()} unlocks." if brief.name else "What the product unlocks.",
            "features_intro": "Keep the feature layer sharp and practical after the workflow story is clear.",
            "pricing_title": f"Choose the {name.title()} fit." if brief.name else "Pick the right plan fast.",
            "pricing_intro": "Make plans feel easy to compare once the value is already tangible.",
            "proof_quote": "The product feels real before the reader even reaches pricing.",
            "proof_author": "Product reviewer",
        },
        "landing": {
            "hero_title": f"{name.title()} makes {industry.lower()} feel considered." if brief.name else f"A sharper story for {industry}",
            "hero_subtitle": f"A conversion-focused experience for {audience} with a {tone} rhythm and a clearer point of view.",
            "cta_text": "See the Story",
            "cta_note": "Lead with conviction, then let the details earn trust.",
            "metrics_title": "Proof that gives the promise some weight.",
            "metrics_intro": f"Ground the story with a few signals that help {audience} trust the next step.",
            "features_title": f"Why {name.title()} lands." if brief.name else "Why the offer lands.",
            "features_intro": f"Give {audience} concrete reasons to care, not a recycled feature list.",
            "proof_quote": "It feels designed around the promise, not just arranged into sections.",
            "proof_author": "Launch review",
        },
        "portfolio": {
            "hero_title": f"{name.title()} builds work with a point of view." if brief.name else "A portfolio with editorial gravity.",
            "hero_subtitle": f"Curated for {audience} with a {tone} voice that turns process into a memorable narrative.",
            "cta_text": "View Projects",
            "cta_note": "Let the craft feel authored before anyone reads the case studies.",
            "projects_title": f"Selected work from {name.title()}." if brief.name else "Selected work with a point of view.",
            "projects_intro": "Each project should show a different kind of judgment so the body of work feels memorable.",
            "about_title": f"The practice behind {name.title()}." if brief.name else "The practice behind the work.",
            "about_intro": "A short narrative that adds perspective and authorship beyond the project grid.",
            "about_text": "A practice shaped by strategy, visual tension, and the patience to make digital work feel intentional.",
            "capabilities_title": "Capabilities that hold the work together.",
            "capabilities_intro": "Frame the supporting strengths like a system, not a generic services menu.",
            "proof_quote": "It reads like a real body of work instead of a generic template fill.",
            "proof_author": "Portfolio review",
        },
        "business": {
            "hero_title": f"{name.title()} makes the service easier to trust." if brief.name else "A service business with sharper structure.",
            "hero_subtitle": f"Built for {audience} with a {tone} voice, clearer offers, and a more current delivery story.",
            "cta_text": "Book now",
            "cta_note": "Show the offer, explain the process, and make trust impossible to miss.",
            "services_title": f"What {name.title()} actually delivers." if brief.name else "Services with enough shape to feel current.",
            "services_intro": "Make the offer list concrete, scannable, and outcome-aware instead of generic service filler.",
            "process_title": "A process people can picture.",
            "process_intro": "Lay out the steps clearly so the service feels easy to start and easy to trust.",
            "proof_quote": "It feels like a real modern business site, not a recycled marketing layout.",
            "proof_author": "Client note",
        },
        "product": {
            "hero_title": f"{name.title()} gives {industry.lower()} teams a cleaner operating surface." if brief.name else f"An easier way to launch {industry.lower()} workflows.",
            "hero_subtitle": f"Built for {audience} with a {tone} launch story, sharper proof, and a product-first rhythm.",
            "cta_text": "Start Free",
            "cta_note": "Show the value quickly, then let pricing and proof carry the close.",
            "metrics_title": "Signals that sharpen the buying decision.",
            "metrics_intro": f"Show {audience} why the product matters before they compare the details.",
            "features_title": f"What {name.title()} unlocks." if brief.name else "What the product unlocks.",
            "features_intro": "Reveal the workflow, the advantage, and the payoff instead of listing generic functionality.",
            "pricing_title": f"Pick the {name.title()} path." if brief.name else "Pick the right plan fast.",
            "pricing_intro": "Make the tier story feel clear, credible, and easy to act on.",
            "price_badge": "Launch pricing from $29/mo",
            "proof_quote": "The product feels differentiated before the features even begin.",
            "proof_author": "Beta tester",
        },
    }
    defaults = {
        "hero_eyebrow": brief.brand_tone or f"{art_direction.title()} system",
        "hero_title": f"{name.title()} for {industry}" if brief.name else f"Move faster in {industry}",
        "hero_subtitle": f"Built for {audience} with a {tone} voice.".strip(),
        "cta_text": "Start Now",
        "cta_note": "Generated as a studio-ready concept with editable sections.",
        "metrics_title": "A few numbers with real signal.",
        "metrics_intro": "Use concise proof points that reinforce the main story.",
        "features_title": "Reasons to lean in.",
        "features_intro": "Let each section build a different part of the case.",
        "collections_title": "Collections worth browsing.",
        "collections_intro": "Use curated groupings to create momentum before the product grid.",
        "products_title": "Featured products.",
        "products_intro": "Give the product selection enough range to feel real.",
        "workflows_title": "Workflow scenes.",
        "workflows_intro": "Show the operating flow in a way that feels tangible.",
        "projects_title": "Selected work.",
        "projects_intro": "Show range without losing the through-line.",
        "pricing_title": "Clear paths forward.",
        "pricing_intro": "Frame the options so the next move is obvious.",
        "about_title": "A bit of context.",
        "about_intro": "Add perspective without rehashing the hero.",
        "capabilities_title": "The system behind it.",
        "capabilities_intro": "Give the supporting strengths a coherent shape.",
        "services_title": "What we do.",
        "services_intro": "Make the service list feel specific and current.",
        "process_title": "How it works.",
        "process_intro": "Show a process people can understand in seconds.",
        "about_text": "A focused practice that blends strategy, design, and delivery into a coherent digital story.",
        "price_badge": "Plans from $29/mo",
        "proof_quote": "This concept feels distinct, confident, and easy to build on.",
        "proof_author": "Internal review",
        "stat_1_value": "42%",
        "stat_1_label": "Faster launch path",
        "stat_2_value": "3x",
        "stat_2_label": "More visual range",
        "stat_3_value": "1",
        "stat_3_label": "Studio workflow",
    }
    defaults.update(template_defaults.get(render_plan.template_key, {}))
    return defaults.get(slot_name, slot_name.replace("_", " ").title())


def _default_list_items(list_name: str, *, render_plan: RenderPlan) -> list[dict[str, str]]:
    industry = render_plan.industry.title()
    defaults = {
        "collections": [
            {"title": "Signature Edit", "desc": "A curated collection framed as the fastest way into the catalog.", "meta": "Collection"},
            {"title": "New Season Drop", "desc": "Fresh arrivals organized like a launch instead of a shelf dump.", "meta": "New in"},
            {"title": "Best Sellers", "desc": "High-intent picks that make the storefront feel active and proven.", "meta": "Popular"},
        ],
        "products": [
            {"title": "Studio Jacket", "desc": "A hero product with enough story to stop the scroll.", "meta": "$68"},
            {"title": "Signal Tee", "desc": "An easy entry item that keeps the grid feeling accessible.", "meta": "$34"},
            {"title": "Field Tote", "desc": "Utility-forward merchandising with a more editorial finish.", "meta": "$52"},
            {"title": "Canvas Cap", "desc": "A clean impulse item that rounds out the collection.", "meta": "$26"},
            {"title": "Weekend Set", "desc": "A paired offer that makes the assortment feel intentional.", "meta": "$84"},
            {"title": "Archive Hoodie", "desc": "A heavier statement piece with stronger perceived value.", "meta": "$78"},
        ],
        "workflows": [
            {"title": "Capture the signal", "desc": "Pull the right product and team inputs into one visible flow.", "meta": "Step 01"},
            {"title": "Coordinate the work", "desc": "Turn scattered handoffs into one operating rhythm.", "meta": "Step 02"},
            {"title": "Ship with proof", "desc": "Surface the outcomes fast enough to guide the next release.", "meta": "Step 03"},
        ],
        "features": [
            {"title": "Sharper hook", "desc": f"Frame the {industry.lower()} promise with a stronger first impression and less generic copy."},
            {"title": "Narrative sections", "desc": "Give each block a role in the story so the page feels authored, not assembled."},
            {"title": "Visual range", "desc": "Use layout, pacing, and emphasis shifts so every section earns its space."},
        ],
        "offers": [
            {"title": "Starter", "desc": "A focused launch with the key story beats and one clear conversion path.", "meta": "$29"},
            {"title": "Growth", "desc": "Richer proof, stronger positioning, and a more persuasive page rhythm.", "meta": "$79"},
            {"title": "Signature", "desc": "A deeper experience with fuller storytelling, stronger systems, and more personality.", "meta": "$149"},
        ],
        "projects": [
            {"title": "Signal Shift", "desc": "A system-level redesign that gave the work more tension, clarity, and recall.", "meta": "Brand system"},
            {"title": "Launch Sequence", "desc": "A narrative-heavy site where structure, motion, and proof all reinforced the same promise.", "meta": "Web launch"},
            {"title": "Conversion Story", "desc": "Messaging, hierarchy, and interaction rebuilt into one coherent decision path.", "meta": "Growth design"},
        ],
        "capabilities": [
            {"title": "Positioning", "desc": "Turn strategy into a page architecture people can feel immediately."},
            {"title": "Art direction", "desc": "Build a visual language that belongs to the brand instead of the template."},
            {"title": "Delivery", "desc": "Ship polished systems that still respect practical product constraints."},
        ],
        "services": [
            {"title": "Offer design", "desc": "Clarify the main service so it reads instantly and feels easy to trust.", "meta": "Core service"},
            {"title": "Experience polish", "desc": "Turn the delivery into a cleaner, more current customer experience.", "meta": "Delivery"},
            {"title": "Growth support", "desc": "Frame the business for repeat demand and stronger word of mouth.", "meta": "Retention"},
        ],
        "process_steps": [
            {"title": "Discover the real need", "desc": "Start by clarifying the goal, audience, and buying friction."},
            {"title": "Shape the best path", "desc": "Translate the offer into a structure people can understand quickly."},
            {"title": "Launch with confidence", "desc": "Deliver a polished system that is easy to maintain and extend."},
        ],
    }
    return defaults.get(list_name, [{"title": "Value", "desc": "Practical results for the audience."}])


def _brand_asset_prompt_block(brief: BriefInput) -> str:
    assets = brief.brand_assets or []
    if not assets and not brief.icon_style:
        return "- uploaded brand assets: none provided\n- icon direction: none provided"

    asset_lines: list[str] = []
    for asset in assets[:4]:
        name = str(asset.get("name", "Brand asset")).strip() or "Brand asset"
        mime_type = str(asset.get("mime_type", "image")).strip() or "image"
        asset_lines.append(f"  - {name} ({mime_type})")

    lines = [
        "- uploaded brand assets:",
        *(asset_lines or ["  - none provided"]),
        f"- icon direction: {brief.icon_style or 'none provided'}",
        "- Treat uploaded assets as implementation references in the final site. If their visual details are not explicitly described, do not invent exact colors or shapes.",
        "- When useful, make feature or capability titles compact enough to work as badge or icon labels.",
    ]
    return "\n".join(lines)


def _build_content_prompt(*, brief: BriefInput, render_plan: RenderPlan, theme_name: str) -> str:
    schema_example: dict[str, object] = {}
    text_slots = render_plan.slot_schema.get("text_slots", [])
    list_slots = render_plan.slot_schema.get("list_slots", {})

    for slot in text_slots:
        schema_example[slot] = _slot_fallback(slot, render_plan=render_plan, brief=brief)
    for slot_name, slot_cfg in list_slots.items():
        item_fields = slot_cfg.get("item_fields", [])
        item_example = {field: f"{field.title()} text" for field in item_fields}
        schema_example[slot_name] = [item_example, item_example, item_example]

    schema_blob = json.dumps(schema_example, indent=2)
    keywords = ", ".join(render_plan.keywords)
    art_guide = ART_DIRECTION_COPY_GUIDES.get(render_plan.art_direction, "")
    layout_guide = LAYOUT_COPY_GUIDES.get(render_plan.layout_mode, "")
    template_guide = TEMPLATE_COPY_GUIDES.get(render_plan.template_key, "")
    content_guide = TEMPLATE_CONTENT_GUIDES.get(render_plan.template_key, "")
    brand_guidance = _brand_asset_prompt_block(brief)

    return f"""
You generate website copy as JSON only. No markdown.

Context:
- intent: {render_plan.template_key}
- layout: {render_plan.layout_mode}
- art direction: {render_plan.art_direction}
- density: {render_plan.density}
- motion level: {render_plan.motion_level}
- sections: {", ".join(render_plan.section_order)}
- industry: {render_plan.industry}
- vibe: {render_plan.vibe}
- keywords: {keywords}
- visual theme: {theme_name}
- narrative goal: {template_guide}
- archetype writing guide: {content_guide}
- art direction writing guide: {art_guide}
- layout writing guide: {layout_guide}
- project name: {brief.name or "Not provided"}
- audience: {brief.audience}
- tone: {brief.brand_tone}
- branding guidance:
{brand_guidance}
- request: {brief.to_prompt_text()}

Writing rules:
- Make the site feel authored for this exact brand and audience, not like generic startup filler.
- The finished result should read like a real launched website with clear hierarchy, not like a moodboard, poster, or abstract brand poem.
- Think in website modules that match the intent: storefronts need collections and product grids, SaaS pages need workflows and proof, portfolios need curated projects, and business sites need services and process.
- Avoid empty phrases such as "innovative solutions", "cutting-edge", "seamless experience", "world-class", or "next-generation".
- Let the art direction influence the language: editorial should feel composed, brutalist should feel decisive, cyber should feel electric, warm should feel human.
- Write section titles and intros like real page copy, not placeholder labels. Avoid default headings like "Features", "Pricing", "Projects", or "About Us" unless the brief clearly calls for plain language.
- Every section title slot must feel like a strong web headline with a distinct job to do: frame proof, introduce benefits, reduce friction, or tee up the next action.
- Section titles should usually be 2 to 7 words, concrete, and easy to scan in a navigation-style website layout.
- Make section intros do different jobs across the page: one can frame proof, another can create intrigue, another can reduce purchase friction.
- Give each list item a distinct angle. Do not repeat the same idea with synonyms.
- Keep hero titles punchy, memorable, and under 10 words when possible.
- Keep CTA text short and active, usually 2 to 4 words.
- Use concrete nouns, outcomes, and imagery instead of vague claims.
- If uploaded brand assets or icon notes exist, keep the naming system compatible with a cohesive branded icon treatment.

Return only JSON matching this schema shape:
{schema_blob}
""".strip()


def _validate_content(content: object, *, brief: BriefInput, render_plan: RenderPlan) -> GeneratedContent:
    if not isinstance(content, dict):
        content = {}

    validated: dict[str, object] = {}
    text_slots: list[str] = render_plan.slot_schema.get("text_slots", [])
    list_slots: dict[str, dict] = render_plan.slot_schema.get("list_slots", {})
    warnings: list[str] = []
    fallback_used = False

    for slot in text_slots:
        value = content.get(slot)
        if isinstance(value, str) and value.strip():
            validated[slot] = value.strip()
        else:
            validated[slot] = _slot_fallback(slot, render_plan=render_plan, brief=brief)
            warnings.append(f"Filled fallback text for '{slot}'.")
            fallback_used = True

    for list_name, list_cfg in list_slots.items():
        items = content.get(list_name)
        min_items = int(list_cfg.get("min_items", 1))
        max_items = int(list_cfg.get("max_items", 6))
        item_fields = list_cfg.get("item_fields", [])
        valid_items: list[dict[str, str]] = []

        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    fallback_used = True
                    continue
                item_data: dict[str, str] = {}
                for field in item_fields:
                    value = item.get(field)
                    if isinstance(value, str) and value.strip():
                        item_data[field] = value.strip()
                if len(item_data) == len(item_fields):
                    valid_items.append(item_data)
                else:
                    fallback_used = True
                if len(valid_items) >= max_items:
                    break
        elif items is not None:
            fallback_used = True

        if len(valid_items) < min_items:
            warnings.append(f"Filled fallback items for '{list_name}'.")
            valid_items = _default_list_items(list_name, render_plan=render_plan)[:max_items]
            fallback_used = True

        validated[list_name] = valid_items

    return GeneratedContent(
        data=validated,
        validation=ValidationResult(
            valid=True,
            warnings=warnings,
            fallback_used=fallback_used,
        ),
    )


def _generate_content(
    *,
    provider: AIProvider | None,
    brief: BriefInput,
    render_plan: RenderPlan,
    seed_content: dict[str, object] | None = None,
    action: str = "Website generation",
    allow_fallback_on_error: bool = False,
) -> GeneratedContent:
    fallback_warning: str | None = None
    if provider is None:
        content = _validate_content(seed_content or {}, brief=brief, render_plan=render_plan)
        if action == "Website generation":
            return _with_validation_warning(
                content,
                "Gemini was unavailable, so Studio generated local fallback copy for this concept.",
            )
        return content

    prompt = _build_content_prompt(
        brief=brief,
        render_plan=render_plan,
        theme_name=THEME_MAP[render_plan.art_direction]["name"],
    )
    try:
        parsed = provider.generate_json(prompt)
    except Exception as exc:
        if allow_fallback_on_error:
            parsed = seed_content or {}
            fallback_warning = (
                "Gemini was unavailable during generation, so Studio filled this concept with local fallback copy."
            )
        elif isinstance(exc, AIProviderUnavailableError):
            raise
        else:
            raise AIProviderUnavailableError(
                f"{action} is unavailable because the Gemini request failed."
            ) from exc
    content = _validate_content(parsed, brief=brief, render_plan=render_plan)
    if fallback_warning:
        return _with_validation_warning(content, fallback_warning)
    return content


def _with_validation_warning(content: GeneratedContent, warning: str) -> GeneratedContent:
    normalized_warning = warning.strip()
    if not normalized_warning:
        return content

    validation = content.validation
    warnings = list(validation.warnings)
    if normalized_warning not in warnings:
        warnings.insert(0, normalized_warning)

    return GeneratedContent(
        data=content.data,
        validation=ValidationResult(
            valid=validation.valid,
            errors=list(validation.errors),
            warnings=warnings,
            fallback_used=True,
        ),
    )


def _variant_label(index: int, render_plan: RenderPlan) -> str:
    layout_name = render_plan.layout_mode.replace("_", " ").title()
    navigation_name = render_plan.navigation_mode.replace("_", " ").title()
    return f"Variant {index}: {layout_name} / {navigation_name}"


def _variant_summary(render_plan: RenderPlan) -> str:
    return (
        f"{render_plan.art_direction.replace('_', ' ').title()} with "
        f"{render_plan.layout_mode.replace('_', ' ')} structure, "
        f"{render_plan.navigation_mode.replace('_', ' ')} navigation, "
        f"{render_plan.page_shell.replace('_', ' ')}, "
        f"{render_plan.density} density, and {render_plan.motion_level} motion."
    )


def _conversation_history_block(messages: list[dict[str, Any]] | None) -> str:
    if not messages:
        return "- no prior conversation history"

    lines: list[str] = []
    for item in messages[-12:]:
        role = str(item.get("role", "system")).strip().lower() or "system"
        body = " ".join(str(item.get("body", "")).split()).strip()
        if not body:
            continue
        lines.append(f"- {role}: {body[:320]}")
    return "\n".join(lines) if lines else "- no prior conversation history"


def _base_theme(art_direction: str) -> dict[str, Any]:
    return deepcopy(THEME_MAP.get(art_direction, THEME_MAP["modern_editorial"]))


def _theme_customizations(theme: dict[str, Any], art_direction: str) -> dict[str, Any]:
    base_theme = _base_theme(art_direction)
    delta: dict[str, Any] = {}
    for key, value in theme.items():
        if base_theme.get(key) != value:
            delta[key] = deepcopy(value)
    return delta


def _merged_theme_for_variant(source_variant: VariantPayload | None, render_plan: RenderPlan) -> dict[str, Any]:
    theme = _base_theme(render_plan.art_direction)
    if source_variant is None or render_plan.art_direction != source_variant.render_plan.art_direction:
        return theme
    theme.update(_theme_customizations(source_variant.theme, source_variant.render_plan.art_direction))
    return theme


def _variant_payload(
    *,
    brief: BriefInput,
    index: int,
    render_plan: RenderPlan,
    content: GeneratedContent,
    variant_id: str | None = None,
    content_overrides: dict[str, Any] | None = None,
    layout_overrides: dict[str, Any] | None = None,
    edited_nodes: list[str] | None = None,
    source_variant: VariantPayload | None = None,
    theme: dict[str, Any] | None = None,
) -> VariantPayload:
    variant = VariantPayload(
        variant_id=variant_id or f"variant-{index}",
        label=_variant_label(index, render_plan),
        summary=_variant_summary(render_plan),
        render_plan=render_plan,
        content=content,
        theme=deepcopy(theme if isinstance(theme, dict) else _merged_theme_for_variant(source_variant, render_plan)),
        visuals={},
        content_overrides=deepcopy(content_overrides or {}),
        layout_overrides=deepcopy(layout_overrides or {}),
        edited_nodes=list(edited_nodes or []),
    )
    resolved_content = _resolved_content(variant, brief=brief, render_plan=render_plan)
    return replace(
        variant,
        visuals=build_variant_visuals(
            brief=brief,
            render_plan=render_plan,
            content=resolved_content.data,
        ),
    )


def _selected_variant(manifest: ProjectManifest) -> VariantPayload | None:
    for variant in manifest.variants:
        if variant.variant_id == manifest.selected_variant_id:
            return variant
    return manifest.variants[0] if manifest.variants else None


def _default_statuses() -> list[GenerationStage]:
    return [
        GenerationStage(key=key, label=label, state="complete", detail=detail)
        for key, label, detail in STATUS_BLUEPRINT
    ]


def status_blueprint() -> list[dict[str, str]]:
    return [
        {"key": key, "label": label, "detail": detail}
        for key, label, detail in STATUS_BLUEPRINT
    ]


def _path_tokens(path: str) -> list[str | int]:
    tokens: list[str | int] = []
    for raw_part in str(path).split("."):
        part = raw_part.strip()
        if not part:
            continue
        tokens.append(int(part) if part.isdigit() else part)
    return tokens


def _path_root(path: str) -> str:
    tokens = _path_tokens(path)
    if not tokens:
        return ""
    head = tokens[0]
    return str(head) if isinstance(head, str) else ""


def _get_path_value(payload: Any, path: str) -> Any:
    current = payload
    for token in _path_tokens(path):
        if isinstance(token, int):
            if not isinstance(current, list) or token < 0 or token >= len(current):
                raise ValueError(f"Invalid list path: {path}")
            current = current[token]
            continue
        if not isinstance(current, dict) or token not in current:
            raise ValueError(f"Invalid object path: {path}")
        current = current[token]
    return current


def _set_path_value(payload: Any, path: str, value: Any) -> None:
    tokens = _path_tokens(path)
    if not tokens:
        raise ValueError("Edit path is required.")

    current = payload
    for token in tokens[:-1]:
        if isinstance(token, int):
            if not isinstance(current, list) or token < 0 or token >= len(current):
                raise ValueError(f"Invalid list path: {path}")
            current = current[token]
            continue
        if not isinstance(current, dict) or token not in current:
            raise ValueError(f"Invalid object path: {path}")
        current = current[token]

    last = tokens[-1]
    if isinstance(last, int):
        if not isinstance(current, list) or last < 0 or last >= len(current):
            raise ValueError(f"Invalid list path: {path}")
        current[last] = value
        return
    if not isinstance(current, dict):
        raise ValueError(f"Invalid object path: {path}")
    current[last] = value


def _normalized_section_order(base_order: list[str], override: object) -> list[str]:
    order = [str(item) for item in base_order if str(item).strip()]
    if not isinstance(override, list):
        return order

    next_order: list[str] = []
    seen: set[str] = set()
    for raw_item in override:
        item = str(raw_item).strip()
        if item and item in order and item not in seen:
            next_order.append(item)
            seen.add(item)
    for item in order:
        if item not in seen:
            next_order.append(item)
    return next_order


def _normalized_section_visibility(base_visibility: dict[str, bool], override: object) -> dict[str, bool]:
    visibility = {str(key): bool(value) for key, value in base_visibility.items()}
    if not isinstance(override, dict):
        return visibility
    for raw_key, raw_value in override.items():
        key = str(raw_key).strip()
        if key in visibility:
            visibility[key] = bool(raw_value)
    return visibility


def _page_by_slug(pages: list[PagePlan], slug: str | None, *, fallback_slug: str) -> PagePlan:
    target_slug = str(slug or fallback_slug).strip() or fallback_slug
    return next((page for page in pages if page.slug == target_slug), pages[0])


def _apply_page_override(page: PagePlan, override: object) -> PagePlan:
    if not isinstance(override, dict):
        return page
    section_order = _normalized_section_order(page.section_order, override.get("section_order"))
    base_visibility = {section: bool(page.section_visibility.get(section, True)) for section in section_order}
    section_visibility = _normalized_section_visibility(base_visibility, override.get("section_visibility"))
    return replace(page, section_order=section_order, section_visibility=section_visibility)


def _normalized_pages(
    base_pages: list[PagePlan],
    *,
    primary_page_slug: str,
    override: object,
    legacy_section_order: object = None,
    legacy_section_visibility: object = None,
) -> list[PagePlan]:
    pages = [page for page in base_pages]
    override_map = override if isinstance(override, dict) else {}
    updated_pages: list[PagePlan] = []
    for page in pages:
        page_override = override_map.get(page.slug)
        if page.slug == primary_page_slug and (
            isinstance(legacy_section_order, list) or isinstance(legacy_section_visibility, dict)
        ):
            merged_override: dict[str, Any] = dict(page_override) if isinstance(page_override, dict) else {}
            if isinstance(legacy_section_order, list):
                merged_override["section_order"] = legacy_section_order
            if isinstance(legacy_section_visibility, dict):
                merged_override["section_visibility"] = legacy_section_visibility
            page_override = merged_override
        updated_pages.append(_apply_page_override(page, page_override))
    return updated_pages


def _apply_layout_overrides_to_plan(render_plan: RenderPlan, layout_overrides: dict[str, Any] | None = None) -> RenderPlan:
    next_layout_overrides = layout_overrides or {}
    pages = _normalized_pages(
        render_plan.pages,
        primary_page_slug=render_plan.primary_page_slug,
        override=next_layout_overrides.get("pages"),
        legacy_section_order=next_layout_overrides.get("section_order"),
        legacy_section_visibility=next_layout_overrides.get("section_visibility"),
    )
    primary_page = _page_by_slug(pages, render_plan.primary_page_slug, fallback_slug=render_plan.primary_page_slug)
    navigation_mode = render_plan.navigation_mode
    raw_navigation_mode = next_layout_overrides.get("navigation_mode")
    if isinstance(raw_navigation_mode, str):
        allowed_navigation_modes = {
            str(item).strip()
            for item in _recipe_navigation_modes(render_plan.template_key, render_plan.layout_mode)
            if str(item).strip()
        }
        candidate = raw_navigation_mode.strip().lower()
        if candidate in allowed_navigation_modes:
            navigation_mode = candidate
    return replace(
        render_plan,
        section_order=list(primary_page.section_order),
        section_visibility=dict(primary_page.section_visibility),
        navigation_mode=navigation_mode,
        pages=pages,
    )


def _recipe_navigation_modes(template_key: str, layout_mode: str) -> list[str]:
    recipe = LAYOUT_LIBRARY.get(template_key, {}).get(layout_mode, {})
    values = recipe.get("navigation_modes")
    if isinstance(values, list):
        return [str(item).strip().lower() for item in values if str(item).strip()]
    return list(NAVIGATION_PATTERNS)


def _record_edited_node(existing: list[str], node_id: str | None) -> list[str]:
    if not node_id:
        return list(existing)
    updated = [item for item in existing if item != node_id]
    updated.append(node_id)
    return updated[-60:]


def _remove_override_prefix(overrides: dict[str, Any], path_prefix: str) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    prefix = path_prefix.strip(".")
    for key, value in overrides.items():
        if key == prefix or key.startswith(f"{prefix}."):
            continue
        cleaned[key] = value
    return cleaned


def _contains_phrase(text: str, phrase: str) -> bool:
    normalized = phrase.strip().lower()
    if not normalized:
        return False
    if " " in normalized or "-" in normalized:
        return normalized in text
    return bool(re.search(rf"\b{re.escape(normalized)}\b", text))


def _has_any_phrase(text: str, phrases: tuple[str, ...] | list[str]) -> bool:
    return any(_contains_phrase(text, phrase) for phrase in phrases)


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    hex_value = str(value or "").strip().lstrip("#")
    if len(hex_value) == 3:
        hex_value = "".join(char * 2 for char in hex_value)
    if len(hex_value) != 6 or any(char not in "0123456789abcdefABCDEF" for char in hex_value):
        raise ValueError(f"Invalid hex color: {value}")
    return tuple(int(hex_value[index : index + 2], 16) for index in range(0, 6, 2))


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    red, green, blue = (max(0, min(int(channel), 255)) for channel in rgb)
    return f"#{red:02x}{green:02x}{blue:02x}"


def _mix_hex(first: str, second: str, ratio: float) -> str:
    mix = max(0.0, min(float(ratio), 1.0))
    first_rgb = _hex_to_rgb(first)
    second_rgb = _hex_to_rgb(second)
    mixed = tuple(round(a + (b - a) * mix) for a, b in zip(first_rgb, second_rgb))
    return _rgb_to_hex(mixed)


def _rgba(value: str, alpha: float) -> str:
    red, green, blue = _hex_to_rgb(value)
    return f"rgba({red}, {green}, {blue}, {max(0.0, min(float(alpha), 1.0)):.2f})"


def _is_dark_hex(value: str) -> bool:
    red, green, blue = _hex_to_rgb(value)
    luminance = (0.2126 * red + 0.7152 * green + 0.0722 * blue) / 255
    return luminance < 0.55


def _extract_requested_colors(text: str) -> list[str]:
    matches: list[str] = []
    for color_name in sorted(COLOR_HEX_MAP.keys(), key=len, reverse=True):
        if _contains_phrase(text, color_name) and color_name not in matches:
            matches.append(color_name)
    return matches


def _theme_request_details(text: str) -> dict[str, Any] | None:
    colors = _extract_requested_colors(text)
    wants_theme_change = bool(colors) or _has_any_phrase(text, THEME_REQUEST_HINTS)
    if not wants_theme_change:
        return None

    accent_name = next((color for color in colors if color not in NEUTRAL_COLOR_KEYS), "")
    dark_requested = _has_any_phrase(text, ("dark", "darker", "black", "night", "noir"))
    light_requested = _has_any_phrase(text, ("light", "lighter", "bright", "brighter", "white", "cream", "beige"))
    wants_dark = dark_requested or ("black" in colors and "white" not in colors)
    wants_light = light_requested and not wants_dark
    ordered_colors = colors or (["dark"] if wants_dark else ["light"] if wants_light else [])
    return {
        "accent_name": accent_name,
        "accent_hex": COLOR_HEX_MAP.get(accent_name, ""),
        "colors": ordered_colors,
        "dark": wants_dark,
        "light": wants_light,
    }


def _requested_density(text: str) -> str:
    for density, hints in DENSITY_HINTS.items():
        if _has_any_phrase(text, hints):
            return density
    return ""


def _requested_motion(text: str) -> str:
    for motion_level, hints in MOTION_HINTS.items():
        if _has_any_phrase(text, hints):
            return motion_level
    return ""


def _requests_art_direction_change(text: str) -> bool:
    return any(_has_any_phrase(text, hints) for hints in ART_DIRECTION_HINTS.values())


def _requests_copy_change(text: str, *, design_change_requested: bool) -> bool:
    if _has_any_phrase(text, COPY_CHANGE_HINTS):
        return True
    return not design_change_requested


def _palette_label(theme_request: dict[str, Any]) -> str:
    colors = [str(color).replace("_", " ") for color in theme_request.get("colors", []) if str(color).strip()]
    if colors:
        if len(colors) == 1:
            return colors[0]
        if len(colors) == 2:
            return f"{colors[0]} and {colors[1]}"
        return ", ".join(colors[:-1]) + f", and {colors[-1]}"
    if theme_request.get("dark"):
        return "darker"
    if theme_request.get("light"):
        return "lighter"
    return "refined"


def _build_custom_theme(base_theme: dict[str, Any], theme_request: dict[str, Any]) -> dict[str, Any]:
    accent = theme_request.get("accent_hex") or base_theme.get("accent") or "#8b5cf6"
    dark_theme = bool(theme_request.get("dark"))
    light_theme = bool(theme_request.get("light"))
    label = _palette_label(theme_request).title()
    theme = deepcopy(base_theme)

    if dark_theme:
        surface = _mix_hex("#09090d", accent, 0.08)
        surface_alt = _mix_hex("#14121c", accent, 0.18)
        frame_background = (
            f"radial-gradient(circle at top right, {_rgba(accent, 0.24)}, transparent 30%), "
            f"linear-gradient(180deg, {surface_alt} 0%, #040408 100%)"
        )
        theme.update(
            {
                "name": f"{label} Noir",
                "canvas_background": frame_background,
                "panel_background": _rgba(surface_alt, 0.84),
                "surface": surface,
                "surface_alt": surface_alt,
                "text": _mix_hex("#f8f6ff", accent, 0.08),
                "muted": _mix_hex("#b7b1c7", accent, 0.35),
                "accent": accent,
                "accent_soft": _rgba(accent, 0.18),
                "border": _rgba(accent, 0.18),
                "button_bg": accent,
                "button_text": "#05060a" if not _is_dark_hex(accent) else "#f8f6ff",
                "shadow": f"0 28px 84px {_rgba(accent, 0.18)}",
                "frame_background": frame_background,
                "frame_border": _rgba(accent, 0.16),
                "frame_glow": f"0 30px 92px {_rgba('#05060a', 0.58)}",
                "backdrop_overlay": f"linear-gradient(145deg, rgba(8, 8, 14, 0.14), {_rgba(accent, 0.08)})",
                "spotlight": f"radial-gradient(circle at 84% 14%, {_rgba(accent, 0.18)}, transparent 24%)",
                "card_fill": _rgba(surface_alt, 0.8),
                "card_stroke": _rgba(accent, 0.12),
                "pill_background": _rgba(surface, 0.74),
                "button_shadow": f"0 18px 44px {_rgba(accent, 0.18)}",
            }
        )
        return theme

    if light_theme:
        surface = _mix_hex("#ffffff", accent, 0.04)
        surface_alt = _mix_hex("#f7f4ff", accent, 0.12)
    else:
        surface = _mix_hex(base_theme.get("surface", "#ffffff"), accent, 0.08)
        surface_alt = _mix_hex(base_theme.get("surface_alt", "#f3f4f6"), accent, 0.16)

    frame_background = (
        f"radial-gradient(circle at top left, {_rgba(accent, 0.22)}, transparent 28%), "
        f"linear-gradient(180deg, {surface} 0%, {surface_alt} 100%)"
    )
    theme.update(
        {
            "name": f"{label} Studio",
            "canvas_background": frame_background,
            "panel_background": _rgba(surface, 0.9),
            "surface": surface,
            "surface_alt": surface_alt,
            "text": _mix_hex(base_theme.get("text", "#111827"), "#111827", 0.88),
            "muted": _mix_hex(base_theme.get("muted", "#586273"), accent, 0.18),
            "accent": accent,
            "accent_soft": _rgba(accent, 0.16),
            "border": _rgba(accent, 0.12),
            "button_bg": accent if _is_dark_hex(accent) else _mix_hex(accent, "#111827", 0.12),
            "button_text": "#f8fafc" if _is_dark_hex(accent) else "#05060a",
            "shadow": f"0 24px 72px {_rgba(accent, 0.14)}",
            "frame_background": frame_background,
            "frame_border": _rgba(accent, 0.12),
            "frame_glow": f"0 26px 80px {_rgba(accent, 0.16)}",
            "backdrop_overlay": f"linear-gradient(145deg, rgba(255, 255, 255, 0.24), {_rgba(accent, 0.08)})",
            "spotlight": f"radial-gradient(circle at 16% 12%, rgba(255, 255, 255, 0.76), transparent 28%)",
            "card_fill": _rgba(surface, 0.86),
            "card_stroke": _rgba(accent, 0.1),
            "pill_background": _rgba(surface, 0.76),
            "button_shadow": f"0 18px 42px {_rgba(accent, 0.18)}",
        }
    )
    return theme


def _conversation_plan_overrides(
    instruction: str,
    *,
    brief: BriefInput,
    current_plan: RenderPlan,
) -> dict[str, Any]:
    art_direction_requested = _requests_art_direction_change(instruction)
    density = _requested_density(instruction)
    motion_level = _requested_motion(instruction)
    if not art_direction_requested and not density and not motion_level:
        return {}

    routed = build_render_variants(
        instruction,
        brief=brief,
        overrides={
            "template_key": current_plan.template_key,
            "layout_mode": current_plan.layout_mode,
        },
        theme_catalog=THEME_MAP,
        template_catalog=TEMPLATE_CATALOG,
    )[0]
    overrides: dict[str, Any] = {}
    if art_direction_requested:
        overrides["art_direction"] = routed.art_direction
    if density:
        overrides["density"] = density
    if motion_level:
        overrides["motion_level"] = motion_level
    return overrides


def _visual_update_reply(
    *,
    previous_plan: RenderPlan,
    next_plan: RenderPlan,
    theme_request: dict[str, Any] | None = None,
    copy_changed: bool,
) -> str:
    changes: list[str] = []
    if theme_request:
        changes.append(f"shifted the palette toward {_palette_label(theme_request)}")
    if previous_plan.art_direction != next_plan.art_direction:
        changes.append(f"leaned the art direction into {next_plan.art_direction.replace('_', ' ')}")
    if previous_plan.density != next_plan.density:
        changes.append(f"set the density to {next_plan.density}")
    if previous_plan.motion_level != next_plan.motion_level:
        changes.append(f"set the motion to {next_plan.motion_level}")

    if not changes:
        return "Updated the current direction and kept the existing project context intact."

    detail = changes[0] if len(changes) == 1 else ", ".join(changes[:-1]) + f", and {changes[-1]}"
    if copy_changed:
        return f"Updated the current direction, {detail}, and refreshed the copy to match."
    return f"Updated the visual direction, {detail}, while keeping the existing copy and structure intact."


def _resolved_render_plan(variant: VariantPayload) -> RenderPlan:
    return _apply_layout_overrides_to_plan(variant.render_plan, variant.layout_overrides)


def _resolved_content(
    variant: VariantPayload,
    *,
    brief: BriefInput,
    render_plan: RenderPlan | None = None,
) -> GeneratedContent:
    effective_plan = render_plan or _resolved_render_plan(variant)
    content_data = deepcopy(variant.content.data)
    for path, value in variant.content_overrides.items():
        try:
            _set_path_value(content_data, path, deepcopy(value))
        except ValueError:
            continue
    return _validate_content(content_data, brief=brief, render_plan=effective_plan)


def _resolved_visuals(
    variant: VariantPayload,
    *,
    brief: BriefInput,
    render_plan: RenderPlan,
    content: GeneratedContent,
) -> dict[str, Any]:
    return build_variant_visuals(
        brief=brief,
        render_plan=render_plan,
        content=content.data,
    )


def _resolved_variant_payload(
    variant: VariantPayload,
    *,
    brief: BriefInput,
    remix_label: str | None = None,
    override_plan: RenderPlan | None = None,
    page_slug: str | None = None,
) -> dict[str, object]:
    effective_plan = override_plan or _resolved_render_plan(variant)
    effective_content = _resolved_content(variant, brief=brief, render_plan=effective_plan)
    active_page = effective_plan.page(page_slug)
    payload = variant.to_dict()
    payload["render_plan"] = effective_plan.to_dict()
    payload["theme"] = _merged_theme_for_variant(variant, effective_plan)
    payload["content"] = effective_content.data
    payload["validation"] = effective_content.validation.to_dict()
    payload["visuals"] = _resolved_visuals(
        variant,
        brief=brief,
        render_plan=effective_plan,
        content=effective_content,
    )
    payload["label"] = remix_label or variant.label
    payload["summary"] = _variant_summary(effective_plan)
    payload["page_slug"] = active_page.slug
    payload["active_page"] = active_page.to_dict()
    return payload


def _section_paths(section_name: str) -> tuple[str, ...]:
    return SECTION_CONTENT_MAP.get(section_name, ())


def _prune_section_overrides(overrides: dict[str, Any], section_name: str) -> dict[str, Any]:
    pruned = dict(overrides)
    for path in _section_paths(section_name):
        pruned = _remove_override_prefix(pruned, path)
    return pruned


def _fallback_text_rewrite(current_value: str, *, instruction: str = "", is_cta: bool = False) -> str:
    source = " ".join(current_value.split()).strip()
    if not source:
        return current_value

    instruction_lower = instruction.lower()
    if is_cta:
        action_words = source.replace(".", "").split()
        if "short" in instruction_lower:
            return " ".join(action_words[:2]) or source
        return " ".join(word.capitalize() for word in action_words[:3]) or source

    if "short" in instruction_lower:
        words = source.split()
        return " ".join(words[: max(4, len(words) // 2)])
    if "improve" in instruction_lower:
        return source.rstrip(".!") + " with a clearer, sharper angle."
    if "punch" in instruction_lower:
        return source.rstrip(".!") + "."
    if "rewrite" in instruction_lower or "improve" in instruction_lower:
        return source
    return source


def _rewrite_text_value(
    *,
    provider: AIProvider | None,
    brief: BriefInput,
    render_plan: RenderPlan,
    current_value: str,
    instruction: str,
    is_cta: bool = False,
) -> str:
    safe_instruction = instruction.strip() or ("Rewrite this CTA" if is_cta else "Rewrite this website copy")
    if provider is None:
        return _fallback_text_rewrite(current_value, instruction=safe_instruction, is_cta=is_cta)

    prompt = f"""
Rewrite this website copy for the current generated page.

Context:
- audience: {brief.audience or "general audiences"}
- tone: {brief.brand_tone or render_plan.art_direction.replace("_", " ")}
- template: {render_plan.template_key}
- art direction: {render_plan.art_direction}
- layout: {render_plan.layout_mode}
- branding guidance:
{_brand_asset_prompt_block(brief)}
- instruction: {safe_instruction}

Rules:
- Keep the rewrite specific and brandable, not generic.
- Match the cadence to the art direction and the structure to the layout.
- Prefer vivid, concrete language over vague marketing filler.
- Preserve the role of the original text so it still fits the design slot.
- Keep the rewrite compatible with any uploaded brand assets and icon-direction notes.

Return only the rewritten copy.
Current copy:
{current_value}
""".strip()
    try:
        rewritten = provider.generate_text(prompt).strip()
    except Exception:
        return _fallback_text_rewrite(current_value, instruction=safe_instruction, is_cta=is_cta)
    return rewritten or _fallback_text_rewrite(current_value, instruction=safe_instruction, is_cta=is_cta)


def _improve_section_content(
    *,
    provider: AIProvider | None,
    brief: BriefInput,
    render_plan: RenderPlan,
    section_name: str,
    content: dict[str, Any],
) -> dict[str, Any]:
    section_paths = _section_paths(section_name)
    if not section_paths:
        return {}

    current_slice: dict[str, Any] = {}
    for path in section_paths:
        if path in content:
            current_slice[path] = deepcopy(content[path])

    if provider is None:
        improved: dict[str, Any] = {}
        for path, value in current_slice.items():
            if isinstance(value, str):
                improved[path] = _fallback_text_rewrite(value, instruction="Improve this section")
            elif isinstance(value, list):
                improved[path] = deepcopy(value)
        return improved

    schema_blob = json.dumps(current_slice, indent=2)
    prompt = f"""
You are improving one section of a generated website. Return JSON only with the same keys as the input.

Context:
- section: {section_name}
- template: {render_plan.template_key}
- audience: {brief.audience or "general audiences"}
- tone: {brief.brand_tone or render_plan.art_direction.replace("_", " ")}
- motion: {render_plan.motion_level}
- density: {render_plan.density}
- branding guidance:
{_brand_asset_prompt_block(brief)}

Rules:
- Make the section feel more intentional and visually suggestive.
- Keep each item distinct and avoid generic B2B filler.
- Stay concise enough to fit a designed layout.
- Keep labels and phrasing compatible with a branded icon or badge system when the brief asks for it.

Current section JSON:
{schema_blob}
""".strip()
    try:
        raw = provider.generate_json(prompt)
    except Exception:
        improved: dict[str, Any] = {}
        for path, value in current_slice.items():
            if isinstance(value, str):
                improved[path] = _fallback_text_rewrite(value, instruction="Improve this section")
            elif isinstance(value, list):
                improved[path] = deepcopy(value)
        return improved

    improved = deepcopy(current_slice)
    if isinstance(raw, dict):
        for path in section_paths:
            if path not in current_slice or path not in raw:
                continue
            candidate = raw[path]
            if isinstance(current_slice[path], str) and isinstance(candidate, str) and candidate.strip():
                improved[path] = candidate.strip()
            elif isinstance(current_slice[path], list) and isinstance(candidate, list):
                improved[path] = candidate
    return improved


def _replace_variant(
    manifest: ProjectManifest,
    *,
    target_variant: VariantPayload,
    next_variant: VariantPayload,
    selected_variant_id: str | None = None,
) -> ProjectManifest:
    variants = list(manifest.variants)
    variants[variants.index(target_variant)] = next_variant
    return ProjectManifest(
        preview_id=manifest.preview_id,
        prompt=manifest.prompt,
        brief=manifest.brief,
        selected_variant_id=selected_variant_id or next_variant.variant_id,
        variants=variants,
        statuses=manifest.statuses,
    )


def generate_project_manifest(
    user_prompt: str,
    *,
    brief: dict[str, object] | BriefInput | None = None,
    overrides: dict[str, object] | None = None,
    preview_id: str | None = None,
    provider: AIProvider | None = None,
) -> ProjectManifest:
    preview_id = preview_id or str(uuid4())
    brief_input = brief if isinstance(brief, BriefInput) else normalize_brief(user_prompt, brief)
    provider = provider if provider is not None else get_default_provider()
    plans = build_render_variants(
        user_prompt,
        brief=brief_input,
        model=_taste_model(provider),
        overrides=overrides,
        theme_catalog=THEME_MAP,
        template_catalog=TEMPLATE_CATALOG,
    )

    variants: list[VariantPayload] = []
    for index, plan in enumerate(plans, start=1):
        content = _generate_content(
            provider=provider,
            brief=brief_input,
            render_plan=plan,
            action="Website generation",
            allow_fallback_on_error=True,
        )
        variants.append(_variant_payload(brief=brief_input, index=index, render_plan=plan, content=content))

    statuses = _default_statuses()
    if any(variant.content.validation.fallback_used for variant in variants):
        statuses = [
            GenerationStage(
                key=stage.key,
                label=stage.label,
                state=stage.state,
                detail=(
                    "Gemini was unavailable, so Studio used deterministic routing and local fallback copy."
                    if stage.key == "generate"
                    else stage.detail
                ),
            )
            for stage in statuses
        ]

    return ProjectManifest(
        preview_id=preview_id,
        prompt=user_prompt,
        brief=brief_input,
        selected_variant_id=variants[0].variant_id if variants else "",
        variants=variants,
        statuses=statuses,
    )


def generate_website_content(
    user_prompt: str,
    *,
    brief: dict[str, object] | BriefInput | None = None,
    overrides: dict[str, object] | None = None,
) -> dict[str, object]:
    return generate_project_manifest(user_prompt, brief=brief, overrides=overrides).to_dict()


def continue_project_manifest(
    current_manifest: ProjectManifest,
    instruction: str,
    variant_id: str | None = None,
    *,
    messages: list[dict[str, Any]] | None = None,
    provider: AIProvider | None = None,
) -> tuple[ProjectManifest, str]:
    if not current_manifest.variants:
        raise ValueError("Preview does not contain editable variants.")

    target_variant_id = variant_id or current_manifest.selected_variant_id
    target_variant = next(
        (item for item in current_manifest.variants if item.variant_id == target_variant_id),
        current_manifest.variants[0],
    )
    cleaned_instruction = " ".join(str(instruction or "").split()).strip()
    if not cleaned_instruction:
        raise ValueError("A follow-up message is required.")

    instruction_text = cleaned_instruction.lower()
    current_plan = _resolved_render_plan(target_variant)
    plan_overrides = _conversation_plan_overrides(
        instruction_text,
        brief=current_manifest.brief,
        current_plan=current_plan,
    )
    theme_request = _theme_request_details(instruction_text)
    design_change_requested = bool(plan_overrides or theme_request)
    copy_change_requested = _requests_copy_change(
        instruction_text,
        design_change_requested=design_change_requested,
    )
    provider = provider if provider is not None else get_default_provider()

    next_plan = target_variant.render_plan
    if plan_overrides:
        try:
            next_plan = remix_render_plan(
                target_variant.render_plan,
                overrides=plan_overrides,
                theme_catalog=THEME_MAP,
                template_catalog=TEMPLATE_CATALOG,
            )
        except Exception:
            next_plan = target_variant.render_plan

    effective_plan = _apply_layout_overrides_to_plan(next_plan, target_variant.layout_overrides)
    resolved_content = _resolved_content(
        target_variant,
        brief=current_manifest.brief,
        render_plan=current_plan,
    ).data
    updated_content = deepcopy(resolved_content)
    assistant_reply = _visual_update_reply(
        previous_plan=current_plan,
        next_plan=effective_plan,
        theme_request=theme_request,
        copy_changed=copy_change_requested,
    )

    if copy_change_requested and provider is None:
        for slot_name in effective_plan.slot_schema.get("text_slots", []):
            current_value = updated_content.get(slot_name)
            if isinstance(current_value, str) and current_value.strip():
                updated_content[slot_name] = _fallback_text_rewrite(
                    current_value,
                    instruction=cleaned_instruction,
                    is_cta="cta" in slot_name,
                )
        if not design_change_requested:
            assistant_reply = "Applied a local revision pass to the current direction using your latest note."
    elif copy_change_requested:
        content_schema = json.dumps(resolved_content, indent=2)
        prompt = f"""
You are continuing an existing website-generation conversation.
Return JSON only with this exact top-level shape:
{{
  "assistant_reply": "short explanation of what changed",
  "content": {content_schema}
}}

Context:
- project name: {current_manifest.brief.name or "Not provided"}
- audience: {current_manifest.brief.audience or "General audience"}
- tone: {current_manifest.brief.brand_tone or effective_plan.art_direction.replace("_", " ")}
- template: {effective_plan.template_key}
- art direction: {effective_plan.art_direction}
- layout: {effective_plan.layout_mode}
- density: {effective_plan.density}
- motion: {effective_plan.motion_level}
- branding guidance:
{_brand_asset_prompt_block(current_manifest.brief)}
- recent conversation:
{_conversation_history_block(messages)}
- latest instruction: {cleaned_instruction}

Rules:
- Update only the current selected design direction.
- Keep the result compatible with the same layout and slot structure.
- Preserve what is already working unless the instruction clearly asks to change it.
- Keep copy concrete, concise, and suitable for a designed website.
- Keep CTA text short and active.
- Do not add or remove JSON keys.
""".strip()
        try:
            raw = provider.generate_json(prompt)
            if not design_change_requested and isinstance(raw.get("assistant_reply"), str) and raw["assistant_reply"].strip():
                assistant_reply = raw["assistant_reply"].strip()
            candidate_content = raw.get("content")
            if isinstance(candidate_content, dict):
                updated_content = candidate_content
        except Exception:
            for slot_name in effective_plan.slot_schema.get("text_slots", []):
                current_value = updated_content.get(slot_name)
                if isinstance(current_value, str) and current_value.strip():
                    updated_content[slot_name] = _fallback_text_rewrite(
                        current_value,
                        instruction=cleaned_instruction,
                        is_cta="cta" in slot_name,
                    )
            if not design_change_requested:
                assistant_reply = "Applied a best-effort local revision because the live AI continuation step was unavailable."

    next_content = _validate_content(updated_content, brief=current_manifest.brief, render_plan=effective_plan)
    next_theme = _merged_theme_for_variant(target_variant, next_plan)
    if theme_request:
        next_theme = _build_custom_theme(next_theme, theme_request)
    next_variant = _variant_payload(
        brief=current_manifest.brief,
        index=current_manifest.variants.index(target_variant) + 1,
        render_plan=next_plan,
        content=next_content,
        variant_id=target_variant.variant_id,
        content_overrides={},
        layout_overrides=target_variant.layout_overrides,
        edited_nodes=target_variant.edited_nodes,
        source_variant=target_variant,
        theme=next_theme,
    )
    updated_manifest = _replace_variant(
        current_manifest,
        target_variant=target_variant,
        next_variant=next_variant,
        selected_variant_id=target_variant.variant_id,
    )
    return updated_manifest, assistant_reply


def apply_variant_override_to_manifest(
    manifest: ProjectManifest,
    *,
    variant_id: str | None = None,
    overrides: dict[str, object] | None = None,
    provider: AIProvider | None = None,
) -> ProjectManifest:
    if not manifest.variants:
        return manifest

    target_variant_id = variant_id or manifest.selected_variant_id
    target_variant = next((item for item in manifest.variants if item.variant_id == target_variant_id), manifest.variants[0])
    selected_variant_id = target_variant.variant_id
    if not overrides:
        return ProjectManifest(
            preview_id=manifest.preview_id,
            prompt=manifest.prompt,
            brief=manifest.brief,
            selected_variant_id=selected_variant_id,
            variants=manifest.variants,
            statuses=manifest.statuses,
        )

    provider = provider if provider is not None else get_default_provider()
    try:
        remixed_plan = remix_render_plan(
            target_variant.render_plan,
            overrides=overrides,
            theme_catalog=THEME_MAP,
            template_catalog=TEMPLATE_CATALOG,
        )
    except Exception:
        remixed_plan = target_variant.render_plan

    content = _generate_content(
        provider=provider,
        brief=manifest.brief,
        render_plan=remixed_plan,
        seed_content=_resolved_content(target_variant, brief=manifest.brief).data,
        action="Website remix",
        allow_fallback_on_error=True,
    )

    next_variant = _variant_payload(
        brief=manifest.brief,
        index=manifest.variants.index(target_variant) + 1,
        render_plan=remixed_plan,
        content=content,
        variant_id=selected_variant_id,
        content_overrides=target_variant.content_overrides,
        layout_overrides=target_variant.layout_overrides,
        edited_nodes=target_variant.edited_nodes,
        source_variant=target_variant,
    )
    return _replace_variant(
        manifest,
        target_variant=target_variant,
        next_variant=next_variant,
        selected_variant_id=selected_variant_id,
    )


def apply_variant_override(
    payload: dict[str, object],
    *,
    variant_id: str | None = None,
    overrides: dict[str, object] | None = None,
) -> dict[str, object]:
    manifest = ProjectManifest.from_dict(payload)
    return apply_variant_override_to_manifest(manifest, variant_id=variant_id, overrides=overrides).to_dict()


def regenerate_manifest(
    manifest: ProjectManifest,
    *,
    scope: str,
    variant_id: str | None = None,
    section_name: str | None = None,
    provider: AIProvider | None = None,
) -> ProjectManifest:
    provider = provider if provider is not None else get_default_provider()
    if scope == "all":
        if provider is None:
            refreshed_variants: list[VariantPayload] = []
            for index, variant in enumerate(manifest.variants, start=1):
                effective_plan = _resolved_render_plan(variant)
                refreshed_content = _generate_content(
                    provider=None,
                    brief=manifest.brief,
                    render_plan=effective_plan,
                    seed_content=_resolved_content(variant, brief=manifest.brief, render_plan=effective_plan).data,
                )
                refreshed_variants.append(
                    _variant_payload(
                        brief=manifest.brief,
                        index=index,
                        render_plan=variant.render_plan,
                        content=refreshed_content,
                        variant_id=variant.variant_id,
                        content_overrides=variant.content_overrides,
                        layout_overrides=variant.layout_overrides,
                        edited_nodes=variant.edited_nodes,
                        source_variant=variant,
                    )
                )
            return ProjectManifest(
                preview_id=manifest.preview_id,
                prompt=manifest.prompt,
                brief=manifest.brief,
                selected_variant_id=manifest.selected_variant_id,
                variants=refreshed_variants,
                statuses=_default_statuses(),
            )

        fresh_manifest = generate_project_manifest(
            manifest.prompt,
            brief=manifest.brief,
            preview_id=manifest.preview_id,
            provider=provider,
        )
        old_variants = {variant.variant_id: variant for variant in manifest.variants}
        merged_variants: list[VariantPayload] = []
        for fresh_variant in fresh_manifest.variants:
            old_variant = old_variants.get(fresh_variant.variant_id)
            if not old_variant:
                merged_variants.append(fresh_variant)
                continue
            merged_variants.append(
                _variant_payload(
                    brief=fresh_manifest.brief,
                    index=fresh_manifest.variants.index(fresh_variant) + 1,
                    render_plan=fresh_variant.render_plan,
                    content=fresh_variant.content,
                    variant_id=fresh_variant.variant_id,
                    content_overrides=old_variant.content_overrides,
                    layout_overrides=old_variant.layout_overrides,
                    edited_nodes=old_variant.edited_nodes,
                    source_variant=old_variant,
                )
            )
        return ProjectManifest(
            preview_id=fresh_manifest.preview_id,
            prompt=fresh_manifest.prompt,
            brief=fresh_manifest.brief,
            selected_variant_id=manifest.selected_variant_id or fresh_manifest.selected_variant_id,
            variants=merged_variants,
            statuses=fresh_manifest.statuses,
        )

    if not manifest.variants:
        return manifest

    target_variant_id = variant_id or manifest.selected_variant_id
    target_variant = next((item for item in manifest.variants if item.variant_id == target_variant_id), manifest.variants[0])
    resolved_content = _resolved_content(target_variant, brief=manifest.brief).data
    if provider is None:
        fresh_content = _generate_content(
            provider=None,
            brief=manifest.brief,
            render_plan=_resolved_render_plan(target_variant),
            seed_content=resolved_content,
        )
    else:
        fresh_content = _generate_content(
            provider=provider,
            brief=manifest.brief,
            render_plan=_resolved_render_plan(target_variant),
            seed_content=resolved_content,
            action="Website regeneration",
            allow_fallback_on_error=True,
        )
    next_content = fresh_content.data
    next_overrides = dict(target_variant.content_overrides)

    if scope == "section" and section_name:
        next_content = deepcopy(target_variant.content.data)
        for path in _section_paths(section_name):
            if path in fresh_content.data:
                next_content[path] = deepcopy(fresh_content.data[path])
        next_overrides = _prune_section_overrides(next_overrides, section_name)
        fresh_content = GeneratedContent(data=next_content, validation=fresh_content.validation)

    next_variant = _variant_payload(
        brief=manifest.brief,
        index=manifest.variants.index(target_variant) + 1,
        render_plan=target_variant.render_plan,
        content=fresh_content,
        variant_id=target_variant.variant_id,
        content_overrides=next_overrides,
        layout_overrides=target_variant.layout_overrides,
        edited_nodes=target_variant.edited_nodes,
        source_variant=target_variant,
    )
    return _replace_variant(
        manifest,
        target_variant=target_variant,
        next_variant=next_variant,
        selected_variant_id=target_variant.variant_id,
    )


def selected_preview_data(payload: dict[str, object] | ProjectManifest, *, page_slug: str | None = None) -> dict[str, object]:
    manifest = payload if isinstance(payload, ProjectManifest) else ProjectManifest.from_dict(payload)
    selected = _selected_variant(manifest)
    return {
        "brief": manifest.brief.to_dict(),
        "selected_variant_id": manifest.selected_variant_id,
        "selected_variant": _resolved_variant_payload(selected, brief=manifest.brief, page_slug=page_slug) if selected else {},
        "variants": [_resolved_variant_payload(variant, brief=manifest.brief, page_slug=page_slug) for variant in manifest.variants],
        "statuses": [stage.to_dict() for stage in manifest.statuses],
    }


def build_preview_variant(
    manifest: ProjectManifest,
    *,
    variant_id: str | None = None,
    overrides: dict[str, object] | None = None,
    remix_label: str | None = None,
    page_slug: str | None = None,
) -> dict[str, object]:
    if not manifest.variants:
        return {}

    target_variant_id = variant_id or manifest.selected_variant_id
    target_variant = next((item for item in manifest.variants if item.variant_id == target_variant_id), manifest.variants[0])
    plan = _resolved_render_plan(target_variant)
    if overrides:
        try:
            plan = remix_render_plan(
                plan,
                overrides=overrides,
                theme_catalog=THEME_MAP,
                template_catalog=TEMPLATE_CATALOG,
            )
        except Exception:
            plan = _resolved_render_plan(target_variant)

    return _resolved_variant_payload(
        target_variant,
        brief=manifest.brief,
        remix_label=remix_label,
        override_plan=plan,
        page_slug=page_slug,
    )


def apply_canvas_command_to_manifest(
    manifest: ProjectManifest,
    *,
    action: str,
    variant_id: str | None = None,
    page_slug: str | None = None,
    node_id: str | None = None,
    edit_path: str | None = None,
    section_name: str | None = None,
    value: Any = None,
    instruction: str = "",
    direction: str = "",
    provider: AIProvider | None = None,
) -> tuple[ProjectManifest, list[str]]:
    if not manifest.variants:
        raise ValueError("Preview does not contain editable variants.")

    target_variant_id = variant_id or manifest.selected_variant_id
    target_variant = next((item for item in manifest.variants if item.variant_id == target_variant_id), manifest.variants[0])
    effective_plan = _resolved_render_plan(target_variant)
    active_page = effective_plan.page(page_slug)
    resolved_content = _resolved_content(target_variant, brief=manifest.brief, render_plan=effective_plan).data
    next_content_overrides = dict(target_variant.content_overrides)
    next_layout_overrides = dict(target_variant.layout_overrides)
    next_page_overrides = deepcopy(next_layout_overrides.get("pages")) if isinstance(next_layout_overrides.get("pages"), dict) else {}
    next_edited_nodes = _record_edited_node(target_variant.edited_nodes, node_id)
    changed_paths: list[str] = []
    provider = provider

    if action == "set_text":
        if not edit_path:
            raise ValueError("Edit path is required.")
        root = _path_root(edit_path)
        if root not in effective_plan.slot_schema.get("text_slots", []) and root not in effective_plan.slot_schema.get("list_slots", {}):
            raise ValueError("Unsupported edit path.")
        next_content_overrides = _remove_override_prefix(next_content_overrides, edit_path)
        if isinstance(value, dict):
            sanitized = {str(key): " ".join(str(item).split())[:240] for key, item in value.items()}
        else:
            sanitized = " ".join(str(value or "").split())[:600]
        next_content_overrides[edit_path] = sanitized
        changed_paths = [edit_path]
    elif action in {"rewrite_text", "rewrite_cta"}:
        provider = _require_provider(provider, action="Copy rewrite")
        if not edit_path:
            raise ValueError("Edit path is required.")
        current_value = _get_path_value(resolved_content, edit_path)
        if isinstance(current_value, str):
            next_content_overrides[edit_path] = _rewrite_text_value(
                provider=provider,
                brief=manifest.brief,
                render_plan=effective_plan,
                current_value=current_value,
                instruction=instruction,
                is_cta=action == "rewrite_cta",
            )
        elif isinstance(current_value, dict):
            rewritten_item: dict[str, Any] = {}
            for key, item in current_value.items():
                if isinstance(item, str):
                    rewritten_item[key] = _rewrite_text_value(
                        provider=provider,
                        brief=manifest.brief,
                        render_plan=effective_plan,
                        current_value=item,
                        instruction=instruction,
                        is_cta=False,
                    )
            if not rewritten_item:
                raise ValueError("Only text-based cards can be rewritten.")
            next_content_overrides = _remove_override_prefix(next_content_overrides, edit_path)
            next_content_overrides[edit_path] = rewritten_item
        else:
            raise ValueError("Only text nodes can be rewritten.")
        changed_paths = [edit_path]
    elif action == "improve_section":
        provider = _require_provider(provider, action="Section improvement")
        if not section_name:
            raise ValueError("Section name is required.")
        improved = _improve_section_content(
            provider=provider,
            brief=manifest.brief,
            render_plan=effective_plan,
            section_name=section_name,
            content=resolved_content,
        )
        if not improved:
            raise ValueError("Section cannot be improved.")
        for path, item in improved.items():
            next_content_overrides = _remove_override_prefix(next_content_overrides, path)
            next_content_overrides[path] = item
            changed_paths.append(path)
    elif action == "move_section":
        if not section_name:
            raise ValueError("Section name is required.")
        section_order = list(active_page.section_order)
        if section_name not in section_order:
            raise ValueError("Section is not part of this layout.")
        offset = -1 if direction == "up" else 1 if direction == "down" else 0
        if offset == 0:
            raise ValueError("Direction must be up or down.")
        current_index = section_order.index(section_name)
        next_index = current_index + offset
        if next_index < 0 or next_index >= len(section_order):
            raise ValueError("Section cannot move further.")
        section_order[current_index], section_order[next_index] = section_order[next_index], section_order[current_index]
        page_override = dict(next_page_overrides.get(active_page.slug, {}))
        page_override["section_order"] = section_order
        next_page_overrides[active_page.slug] = page_override
        next_layout_overrides["pages"] = next_page_overrides
        if active_page.slug == effective_plan.primary_page_slug:
            next_layout_overrides["section_order"] = section_order
        changed_paths = [f"render_plan.pages.{active_page.slug}.section_order"]
    elif action == "toggle_section":
        if not section_name:
            raise ValueError("Section name is required.")
        visibility = _normalized_section_visibility(
            active_page.section_visibility,
            (next_page_overrides.get(active_page.slug) or {}).get("section_visibility"),
        )
        visibility[section_name] = bool(value) if isinstance(value, bool) else not bool(visibility.get(section_name, True))
        page_override = dict(next_page_overrides.get(active_page.slug, {}))
        page_override["section_visibility"] = visibility
        next_page_overrides[active_page.slug] = page_override
        next_layout_overrides["pages"] = next_page_overrides
        if active_page.slug == effective_plan.primary_page_slug:
            next_layout_overrides["section_visibility"] = visibility
        changed_paths = [f"render_plan.pages.{active_page.slug}.section_visibility.{section_name}"]
    elif action in {"move_item", "delete_item"}:
        if not edit_path:
            raise ValueError("Edit path is required.")
        tokens = _path_tokens(edit_path)
        if len(tokens) < 2 or not isinstance(tokens[0], str) or not isinstance(tokens[1], int):
            raise ValueError("List item edit path must target an item.")
        list_name = tokens[0]
        item_index = tokens[1]
        items = deepcopy(resolved_content.get(list_name))
        if not isinstance(items, list) or item_index < 0 or item_index >= len(items):
            raise ValueError("List item not found.")
        if action == "move_item":
            offset = -1 if direction == "up" else 1 if direction == "down" else 0
            if offset == 0:
                raise ValueError("Direction must be up or down.")
            target_index = item_index + offset
            if target_index < 0 or target_index >= len(items):
                raise ValueError("Item cannot move further.")
            items[item_index], items[target_index] = items[target_index], items[item_index]
        else:
            list_cfg = effective_plan.slot_schema.get("list_slots", {}).get(list_name, {})
            min_items = int(list_cfg.get("min_items", 1))
            if len(items) <= min_items:
                raise ValueError("This section needs at least one more item.")
            items.pop(item_index)
        next_content_overrides = _remove_override_prefix(next_content_overrides, list_name)
        next_content_overrides[list_name] = items
        changed_paths = [list_name]
    else:
        raise ValueError("Unsupported canvas action.")

    next_variant = _variant_payload(
        brief=manifest.brief,
        index=manifest.variants.index(target_variant) + 1,
        render_plan=target_variant.render_plan,
        content=target_variant.content,
        variant_id=target_variant.variant_id,
        content_overrides=next_content_overrides,
        layout_overrides=next_layout_overrides,
        edited_nodes=next_edited_nodes,
        source_variant=target_variant,
    )
    updated_manifest = _replace_variant(
        manifest,
        target_variant=target_variant,
        next_variant=next_variant,
        selected_variant_id=target_variant.variant_id,
    )
    return updated_manifest, changed_paths
