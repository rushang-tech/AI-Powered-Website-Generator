from __future__ import annotations

import json
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
    RenderPlan,
    build_render_plan,
    build_render_variants,
    normalize_brief,
    remix_render_plan,
)

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

PALETTE_MOOD_OVERRIDES: dict[str, dict[str, str]] = {
    "neutral": {
        "canvas_background": "linear-gradient(180deg, #eef3f8 0%, #dde5ee 100%)",
        "panel_background": "rgba(251, 253, 255, 0.9)",
        "surface": "#fbfdff",
        "surface_alt": "#edf2f7",
        "text": "#111827",
        "muted": "#5c6678",
        "accent": "#82cf2d",
        "accent_soft": "rgba(130, 207, 45, 0.16)",
        "border": "rgba(17, 24, 39, 0.12)",
        "button_bg": "#111827",
        "button_text": "#f8fbff",
        "frame_background": "linear-gradient(180deg, rgba(242, 247, 252, 0.98) 0%, rgba(224, 232, 241, 0.98) 100%)",
        "frame_border": "rgba(17, 24, 39, 0.1)",
        "backdrop_overlay": "linear-gradient(145deg, rgba(255, 255, 255, 0.3), rgba(130, 207, 45, 0.06))",
        "spotlight": "radial-gradient(circle at 18% 12%, rgba(255, 255, 255, 0.8), transparent 34%)",
        "card_fill": "rgba(255, 255, 255, 0.9)",
        "card_stroke": "rgba(17, 24, 39, 0.08)",
        "pill_background": "rgba(248, 252, 255, 0.82)",
    },
    "warm": {
        "canvas_background": "radial-gradient(circle at top left, rgba(255, 188, 131, 0.3), transparent 30%), linear-gradient(180deg, #fff0db 0%, #ffd9cc 52%, #ffe7e1 100%)",
        "panel_background": "rgba(255, 247, 239, 0.9)",
        "surface": "#fff8f2",
        "surface_alt": "#ffe0d1",
        "text": "#3b241f",
        "muted": "#8d6054",
        "accent": "#f16b44",
        "accent_soft": "rgba(241, 107, 68, 0.16)",
        "border": "rgba(59, 36, 31, 0.12)",
        "button_bg": "#f16b44",
        "button_text": "#fff7f2",
        "frame_background": "linear-gradient(180deg, rgba(255, 240, 219, 0.98) 0%, rgba(255, 217, 204, 0.98) 100%)",
        "frame_border": "rgba(145, 85, 63, 0.12)",
        "backdrop_overlay": "linear-gradient(145deg, rgba(255, 255, 255, 0.28), rgba(241, 107, 68, 0.08))",
        "spotlight": "radial-gradient(circle at 14% 12%, rgba(255, 255, 255, 0.8), transparent 30%)",
        "card_fill": "rgba(255, 251, 246, 0.9)",
        "card_stroke": "rgba(141, 96, 84, 0.1)",
        "pill_background": "rgba(255, 244, 236, 0.84)",
    },
    "earthy": {
        "canvas_background": "radial-gradient(circle at top left, rgba(151, 188, 126, 0.22), transparent 30%), linear-gradient(180deg, #f4f1e8 0%, #e7e1d2 100%)",
        "panel_background": "rgba(248, 245, 237, 0.88)",
        "surface": "#f9f6ef",
        "surface_alt": "#ebe5d6",
        "text": "#213126",
        "muted": "#647265",
        "accent": "#789a54",
        "accent_soft": "rgba(120, 154, 84, 0.16)",
        "border": "rgba(33, 49, 38, 0.12)",
        "button_bg": "#22342a",
        "button_text": "#f7f5ef",
        "frame_background": "linear-gradient(180deg, rgba(245, 242, 233, 0.98) 0%, rgba(232, 226, 210, 0.98) 100%)",
        "frame_border": "rgba(33, 49, 38, 0.1)",
        "backdrop_overlay": "linear-gradient(145deg, rgba(255, 255, 255, 0.22), rgba(120, 154, 84, 0.08))",
        "spotlight": "radial-gradient(circle at 18% 10%, rgba(255, 255, 255, 0.72), transparent 28%)",
        "card_fill": "rgba(250, 247, 240, 0.88)",
        "card_stroke": "rgba(33, 49, 38, 0.08)",
        "pill_background": "rgba(248, 245, 239, 0.8)",
    },
    "coastal": {
        "canvas_background": "radial-gradient(circle at top right, rgba(114, 210, 226, 0.24), transparent 30%), linear-gradient(180deg, #f2fbff 0%, #e6f5f4 55%, #f4f0e8 100%)",
        "panel_background": "rgba(246, 252, 253, 0.86)",
        "surface": "#f7fdff",
        "surface_alt": "#e2f2f1",
        "text": "#11374b",
        "muted": "#557686",
        "accent": "#0ea4b6",
        "accent_soft": "rgba(14, 164, 182, 0.14)",
        "border": "rgba(17, 55, 75, 0.12)",
        "button_bg": "#11374b",
        "button_text": "#eefcff",
        "frame_background": "linear-gradient(180deg, rgba(242, 251, 255, 0.98) 0%, rgba(231, 246, 245, 0.98) 100%)",
        "frame_border": "rgba(17, 55, 75, 0.1)",
        "backdrop_overlay": "linear-gradient(145deg, rgba(255, 255, 255, 0.3), rgba(14, 164, 182, 0.06))",
        "spotlight": "radial-gradient(circle at 84% 10%, rgba(255, 255, 255, 0.76), transparent 28%)",
        "card_fill": "rgba(248, 253, 254, 0.84)",
        "card_stroke": "rgba(17, 55, 75, 0.08)",
        "pill_background": "rgba(255, 255, 255, 0.74)",
    },
    "luxury": {
        "canvas_background": "radial-gradient(circle at top, rgba(225, 190, 126, 0.18), transparent 34%), linear-gradient(180deg, #161110 0%, #2a1c16 100%)",
        "panel_background": "rgba(30, 22, 18, 0.8)",
        "surface": "#1d1512",
        "surface_alt": "#2f211b",
        "text": "#f5e8d7",
        "muted": "#c2ab92",
        "accent": "#dcb069",
        "accent_soft": "rgba(220, 176, 105, 0.18)",
        "border": "rgba(220, 176, 105, 0.16)",
        "button_bg": "#dcb069",
        "button_text": "#17110d",
        "frame_background": "linear-gradient(180deg, rgba(24, 17, 15, 0.98) 0%, rgba(42, 30, 24, 0.98) 100%)",
        "frame_border": "rgba(220, 176, 105, 0.14)",
        "backdrop_overlay": "linear-gradient(160deg, rgba(255, 245, 230, 0.06), rgba(220, 176, 105, 0.12))",
        "spotlight": "radial-gradient(circle at 78% 4%, rgba(255, 235, 205, 0.16), transparent 28%)",
        "card_fill": "rgba(31, 23, 18, 0.86)",
        "card_stroke": "rgba(220, 176, 105, 0.12)",
        "pill_background": "rgba(40, 29, 23, 0.9)",
    },
    "electric": {
        "canvas_background": "radial-gradient(circle at top right, rgba(64, 231, 255, 0.22), transparent 30%), linear-gradient(180deg, #08121f 0%, #040913 100%)",
        "panel_background": "rgba(7, 18, 32, 0.82)",
        "surface": "#0a1625",
        "surface_alt": "#102338",
        "text": "#ddfbff",
        "muted": "#8eb7cb",
        "accent": "#33e7e0",
        "accent_soft": "rgba(51, 231, 224, 0.16)",
        "border": "rgba(51, 231, 224, 0.18)",
        "button_bg": "#2af0d0",
        "button_text": "#041017",
        "frame_background": "linear-gradient(180deg, rgba(8, 18, 31, 0.98) 0%, rgba(4, 9, 19, 0.98) 100%)",
        "frame_border": "rgba(51, 231, 224, 0.16)",
        "backdrop_overlay": "linear-gradient(145deg, rgba(8, 18, 31, 0.1), rgba(51, 231, 224, 0.08))",
        "spotlight": "radial-gradient(circle at 84% 14%, rgba(51, 231, 224, 0.2), transparent 24%)",
        "card_fill": "rgba(10, 22, 37, 0.8)",
        "card_stroke": "rgba(51, 231, 224, 0.12)",
        "pill_background": "rgba(7, 18, 32, 0.66)",
    },
    "mono": {
        "canvas_background": "linear-gradient(180deg, #f2f2ee 0%, #e7e7e1 100%)",
        "panel_background": "rgba(252, 252, 248, 0.88)",
        "surface": "#fbfbf8",
        "surface_alt": "#edede7",
        "text": "#0d0f0d",
        "muted": "#51554d",
        "accent": "#98e23d",
        "accent_soft": "rgba(152, 226, 61, 0.16)",
        "border": "rgba(13, 15, 13, 0.14)",
        "button_bg": "#0d0f0d",
        "button_text": "#f5f7ef",
        "frame_background": "linear-gradient(180deg, rgba(242, 242, 238, 0.98) 0%, rgba(231, 231, 225, 0.98) 100%)",
        "frame_border": "rgba(13, 15, 13, 0.12)",
        "backdrop_overlay": "linear-gradient(135deg, rgba(255, 255, 255, 0.22), rgba(152, 226, 61, 0.04))",
        "spotlight": "radial-gradient(circle at 18% 10%, rgba(255, 255, 255, 0.62), transparent 28%)",
        "card_fill": "rgba(252, 252, 248, 0.86)",
        "card_stroke": "rgba(13, 15, 13, 0.1)",
        "pill_background": "rgba(247, 248, 242, 0.76)",
    },
    "playful": {
        "canvas_background": "linear-gradient(135deg, #fff4bc 0%, #ffd2cb 46%, #c9f3ff 100%)",
        "panel_background": "rgba(255, 250, 241, 0.92)",
        "surface": "#fffdf8",
        "surface_alt": "#ffe79d",
        "text": "#182a58",
        "muted": "#3c5e93",
        "accent": "#ff5a38",
        "accent_soft": "rgba(255, 90, 56, 0.18)",
        "border": "rgba(24, 42, 88, 0.18)",
        "button_bg": "#2550d6",
        "button_text": "#fff8dc",
        "frame_background": "linear-gradient(135deg, rgba(255, 247, 220, 0.98) 0%, rgba(255, 210, 203, 0.98) 56%, rgba(201, 243, 255, 0.98) 100%)",
        "frame_border": "rgba(24, 42, 88, 0.14)",
        "backdrop_overlay": "linear-gradient(145deg, rgba(255, 255, 255, 0.24), rgba(37, 80, 214, 0.08))",
        "spotlight": "radial-gradient(circle at 12% 18%, rgba(255, 255, 255, 0.82), transparent 26%)",
        "card_fill": "rgba(255, 254, 248, 0.92)",
        "card_stroke": "rgba(24, 42, 88, 0.14)",
        "pill_background": "rgba(255, 255, 255, 0.72)",
    },
}

TYPOGRAPHY_VIBE_OVERRIDES: dict[str, dict[str, str]] = {
    "editorial": {
        "display_font": "'Cormorant Garamond', serif",
        "body_font": "'Space Grotesk', sans-serif",
    },
    "geometric": {
        "display_font": "'Bricolage Grotesque', sans-serif",
        "body_font": "'Space Grotesk', sans-serif",
    },
    "friendly": {
        "display_font": "'Bricolage Grotesque', sans-serif",
        "body_font": "'Manrope', sans-serif",
    },
    "classic": {
        "display_font": "'Fraunces', serif",
        "body_font": "'Manrope', sans-serif",
    },
    "tech": {
        "display_font": "'Space Grotesk', sans-serif",
        "body_font": "'Manrope', sans-serif",
    },
}

TEMPLATE_CATALOG: dict[str, dict[str, str]] = {
    "landing": {"template_file": "generated/landing.html"},
    "portfolio": {"template_file": "generated/portfolio.html"},
    "product": {"template_file": "generated/product.html"},
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
    "projects": ("projects_title", "projects_intro", "projects"),
    "pricing": ("pricing_title", "pricing_intro", "offers"),
    "proof": ("proof_quote", "proof_author"),
    "cta": ("cta_text", "cta_note"),
    "about": ("about_title", "about_intro", "about_text"),
    "capabilities": ("capabilities_title", "capabilities_intro", "capabilities"),
}

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
    "split_hero": "Open with a clear point of view, then let the supporting content widen the case.",
    "staggered_bands": "Let each section shift the rhythm slightly so the page feels paced instead of repetitive.",
    "immersive_layers": "Use more atmospheric and cinematic phrasing that rewards scrolling.",
    "proof_first": "Earn trust immediately, then bring the pitch in after credibility is established.",
    "editorial_casebook": "Treat the page like a curated body of work with a strong editorial spine.",
    "masonry_showcase": "Let each project feel visually distinct and collectible rather than part of a flat list.",
    "minimal_cv": "Stay precise and useful. Keep the language lean and grounded.",
    "story_panels": "Make each section feel like a scene that adds a different layer to the narrative.",
    "pricing_first": "Frame the buying decision clearly and make the offer structure easy to compare.",
    "feature_scroll": "Reveal the product through workflow-oriented sections, not a generic feature dump.",
    "contrast_split": "Balance premium positioning with practical proof so the page feels both elevated and usable.",
    "launch_countdown": "Lean into urgency, anticipation, and release energy without sounding gimmicky.",
}

TEMPLATE_COPY_GUIDES: dict[str, str] = {
    "landing": "The page should feel like a focused argument for one offer and one next step.",
    "portfolio": "The page should feel like authored work with perspective, curation, and memorable framing.",
    "product": "The page should make the product and pricing feel tangible fast, then deepen trust through proof.",
}

MEDIA_DIRECTION_COPY_GUIDES: dict[str, str] = {
    "editorial_collage": "Assume layered editorial imagery and branded detail shots sit beside the copy. Make headlines and labels strong enough to share space with visuals.",
    "case_study_frames": "Assume the layout includes case-study imagery, thumbnails, or project photography. Let titles and captions feel curated rather than generic.",
    "interface_mockups": "Assume screenshots or UI mockups appear throughout. Keep copy concrete, workflow-aware, and easy to pair with product visuals.",
    "soft_focus_frames": "Assume the page uses atmospheric photography, portraits, or brand still life moments. Write with sensory clarity and tasteful restraint.",
    "playful_stickers": "Assume the layout uses cheerful illustrated frames and sticker-like visual accents. Keep language compact, bright, and human.",
    "poster_panels": "Assume bold graphic panels and image blocks help carry the rhythm. Use punchy lines that read well in short visual compositions.",
    "glow_grid": "Assume the design includes glowing interface plates, dashboards, or neon visual tiles. Favor crisp, specific phrasing over abstract mood words.",
    "cinematic_layers": "Assume large immersive visuals and layered scenes drive the pacing. Make each section feel like a distinct scroll moment.",
}


def _theme_for_render_plan(render_plan: RenderPlan) -> dict[str, str]:
    theme = deepcopy(THEME_MAP.get(render_plan.art_direction, THEME_MAP["modern_editorial"]))
    theme.update(PALETTE_MOOD_OVERRIDES.get(render_plan.palette_mood, {}))
    theme.update(TYPOGRAPHY_VIBE_OVERRIDES.get(render_plan.typography_vibe, {}))
    theme["palette_mood"] = render_plan.palette_mood
    theme["typography_vibe"] = render_plan.typography_vibe
    return theme


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
        "projects_title": "Selected work.",
        "projects_intro": "Show range without losing the through-line.",
        "pricing_title": "Clear paths forward.",
        "pricing_intro": "Frame the options so the next move is obvious.",
        "about_title": "A bit of context.",
        "about_intro": "Add perspective without rehashing the hero.",
        "capabilities_title": "The system behind it.",
        "capabilities_intro": "Give the supporting strengths a coherent shape.",
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
    }
    return defaults.get(list_name, [{"title": "Value", "desc": "Practical results for the audience."}])


def _brand_asset_prompt_block(brief: BriefInput) -> str:
    assets = brief.brand_assets or []
    if not assets and not brief.icon_style and not brief.palette_mood and not brief.typography_vibe and not brief.taste_keywords:
        return "\n".join(
            [
                "- uploaded brand assets: none provided",
                "- icon direction: none provided",
                "- palette mood: auto",
                "- typography vibe: auto",
                "- taste keywords: none provided",
            ]
        )

    asset_lines: list[str] = []
    for asset in assets[:4]:
        name = str(asset.get("name", "Brand asset")).strip() or "Brand asset"
        mime_type = str(asset.get("mime_type", "image")).strip() or "image"
        asset_lines.append(f"  - {name} ({mime_type})")

    lines = [
        "- uploaded brand assets:",
        *(asset_lines or ["  - none provided"]),
        f"- icon direction: {brief.icon_style or 'none provided'}",
        f"- palette mood: {brief.palette_mood or 'auto'}",
        f"- typography vibe: {brief.typography_vibe or 'auto'}",
        f"- taste keywords: {', '.join(brief.taste_keywords) if brief.taste_keywords else 'none provided'}",
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
    media_guide = MEDIA_DIRECTION_COPY_GUIDES.get(render_plan.media_direction, "")
    brand_guidance = _brand_asset_prompt_block(brief)

    return f"""
You generate website copy as JSON only. No markdown.

Context:
- intent: {render_plan.template_key}
- layout: {render_plan.layout_mode}
- art direction: {render_plan.art_direction}
- density: {render_plan.density}
- motion level: {render_plan.motion_level}
- palette mood: {render_plan.palette_mood or "auto"}
- typography vibe: {render_plan.typography_vibe or "auto"}
- media direction: {render_plan.media_direction}
- shell variant: {render_plan.shell_variant}
- navigation style: {render_plan.navigation_style}
- sections: {", ".join(render_plan.section_order)}
- industry: {render_plan.industry}
- vibe: {render_plan.vibe}
- keywords: {keywords}
- explicit taste keywords: {", ".join(brief.taste_keywords) if brief.taste_keywords else "none"}
- visual theme: {theme_name}
- narrative goal: {template_guide}
- art direction writing guide: {art_guide}
- layout writing guide: {layout_guide}
- media writing guide: {media_guide}
- project name: {brief.name or "Not provided"}
- audience: {brief.audience}
- tone: {brief.brand_tone}
- branding guidance:
{brand_guidance}
- request: {brief.to_prompt_text()}

Writing rules:
- Make the site feel authored for this exact brand and audience, not like generic startup filler.
- The finished result should read like a real launched website with clear hierarchy, not like a moodboard, poster, or abstract brand poem.
- Think in website modules: a confident hero, a scannable proof or metrics block, a clear highlights/features section, and a decisive CTA.
- Write with visual anchors in mind: headings, labels, and short supporting lines should pair naturally with image holders, screenshots, or editorial photography.
- Some sections will reserve image space, so avoid relying on long paragraphs to make the page feel complete.
- Match the shell: portfolio routes should feel authored and curated, landing routes should feel conversion-aware and persuasive, and product routes should feel like real software or launch experiences.
- Avoid empty phrases such as "innovative solutions", "cutting-edge", "seamless experience", "world-class", or "next-generation".
- Let the art direction influence the language: editorial should feel composed, brutalist should feel decisive, cyber should feel electric, warm should feel human.
- Let palette mood and typography vibe subtly shape the rhythm, naming, and texture so the copy feels visually aligned with the design direction.
- Write section titles and intros like real page copy, not placeholder labels. Avoid default headings like "Features", "Pricing", "Projects", or "About Us" unless the brief clearly calls for plain language.
- Every section title slot must feel like a strong web headline with a distinct job to do: frame proof, introduce benefits, reduce friction, or tee up the next action.
- Section titles should usually be 2 to 7 words, concrete, and easy to scan in a navigation-style website layout.
- Make section intros do different jobs across the page: one can frame proof, another can create intrigue, another can reduce purchase friction.
- Give each list item a distinct angle. Do not repeat the same idea with synonyms.
- Keep list item titles compact enough to sit inside designed cards that may also carry imagery or UI thumbnails.
- Keep hero titles punchy, memorable, and under 10 words when possible.
- Keep CTA text short and active, usually 2 to 4 words.
- Use concrete nouns, outcomes, and imagery instead of vague claims.
- Treat taste keywords as real creative direction. If they imply a tactile, editorial, technical, playful, or premium system, reflect that in section naming and microcopy.
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
        theme_name=_theme_for_render_plan(render_plan)["name"],
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
    return f"Variant {index}: {layout_name}"


def _variant_summary(render_plan: RenderPlan) -> str:
    return (
        f"{render_plan.art_direction.replace('_', ' ').title()} with "
        f"{render_plan.layout_mode.replace('_', ' ')} structure, "
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


def _variant_payload(
    *,
    index: int,
    render_plan: RenderPlan,
    content: GeneratedContent,
    variant_id: str | None = None,
    content_overrides: dict[str, Any] | None = None,
    layout_overrides: dict[str, Any] | None = None,
    edited_nodes: list[str] | None = None,
) -> VariantPayload:
    return VariantPayload(
        variant_id=variant_id or f"variant-{index}",
        label=_variant_label(index, render_plan),
        summary=_variant_summary(render_plan),
        render_plan=render_plan,
        content=content,
        theme=_theme_for_render_plan(render_plan),
        content_overrides=deepcopy(content_overrides or {}),
        layout_overrides=deepcopy(layout_overrides or {}),
        edited_nodes=list(edited_nodes or []),
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


def _resolved_render_plan(variant: VariantPayload) -> RenderPlan:
    base_plan = variant.render_plan
    section_order = _normalized_section_order(base_plan.section_order, variant.layout_overrides.get("section_order"))
    section_visibility = _normalized_section_visibility(
        base_plan.section_visibility,
        variant.layout_overrides.get("section_visibility"),
    )
    return replace(base_plan, section_order=section_order, section_visibility=section_visibility)


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


def _resolved_variant_payload(
    variant: VariantPayload,
    *,
    brief: BriefInput,
    remix_label: str | None = None,
    override_plan: RenderPlan | None = None,
) -> dict[str, object]:
    effective_plan = override_plan or _resolved_render_plan(variant)
    effective_content = _resolved_content(variant, brief=brief, render_plan=effective_plan)
    payload = variant.to_dict()
    payload["render_plan"] = effective_plan.to_dict()
    payload["content"] = effective_content.data
    payload["validation"] = effective_content.validation.to_dict()
    payload["theme"] = _theme_for_render_plan(effective_plan)
    payload["label"] = remix_label or variant.label
    payload["summary"] = _variant_summary(effective_plan)
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
        variants.append(_variant_payload(index=index, render_plan=plan, content=content))

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
    effective_plan = _resolved_render_plan(target_variant)
    resolved_content = _resolved_content(
        target_variant,
        brief=current_manifest.brief,
        render_plan=effective_plan,
    ).data
    provider = provider if provider is not None else get_default_provider()
    cleaned_instruction = " ".join(str(instruction or "").split()).strip()
    if not cleaned_instruction:
        raise ValueError("A follow-up message is required.")

    updated_content = deepcopy(resolved_content)
    assistant_reply = "Updated the current direction and kept the existing project context intact."

    if provider is None:
        for slot_name in effective_plan.slot_schema.get("text_slots", []):
            current_value = updated_content.get(slot_name)
            if isinstance(current_value, str) and current_value.strip():
                updated_content[slot_name] = _fallback_text_rewrite(
                    current_value,
                    instruction=cleaned_instruction,
                    is_cta="cta" in slot_name,
                )
        assistant_reply = "Applied a local revision pass to the current direction using your latest note."
    else:
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
            if isinstance(raw.get("assistant_reply"), str) and raw["assistant_reply"].strip():
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
            assistant_reply = "Applied a best-effort local revision because the live AI continuation step was unavailable."

    next_content = _validate_content(updated_content, brief=current_manifest.brief, render_plan=effective_plan)
    next_variant = _variant_payload(
        index=current_manifest.variants.index(target_variant) + 1,
        render_plan=target_variant.render_plan,
        content=next_content,
        variant_id=target_variant.variant_id,
        content_overrides={},
        layout_overrides=target_variant.layout_overrides,
        edited_nodes=target_variant.edited_nodes,
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
        locked_overrides: dict[str, object] = {
            "template_key": overrides.get("template_key", target_variant.render_plan.template_key),
            "art_direction": overrides.get("art_direction", target_variant.render_plan.art_direction),
            "layout_mode": overrides.get("layout_mode", target_variant.render_plan.layout_mode),
            "density": overrides.get("density", target_variant.render_plan.density),
            "motion_level": overrides.get("motion_level", target_variant.render_plan.motion_level),
        }
        if "palette_mood" in overrides:
            locked_overrides["palette_mood"] = overrides.get("palette_mood")
        if "typography_vibe" in overrides:
            locked_overrides["typography_vibe"] = overrides.get("typography_vibe")
        if "taste_keywords" in overrides:
            locked_overrides["taste_keywords"] = overrides.get("taste_keywords")
        if "keywords" in overrides:
            locked_overrides["keywords"] = overrides.get("keywords")
        raw_visibility = overrides.get("section_visibility")
        if isinstance(raw_visibility, dict):
            locked_overrides["section_visibility"] = raw_visibility

        remixed_plan = build_render_plan(
            manifest.prompt,
            brief=manifest.brief,
            model=None,
            overrides=locked_overrides,
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
        index=manifest.variants.index(target_variant) + 1,
        render_plan=remixed_plan,
        content=content,
        variant_id=selected_variant_id,
        content_overrides=target_variant.content_overrides,
        layout_overrides=target_variant.layout_overrides,
        edited_nodes=target_variant.edited_nodes,
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
                        index=index,
                        render_plan=variant.render_plan,
                        content=refreshed_content,
                        variant_id=variant.variant_id,
                        content_overrides=variant.content_overrides,
                        layout_overrides=variant.layout_overrides,
                        edited_nodes=variant.edited_nodes,
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
                    index=fresh_manifest.variants.index(fresh_variant) + 1,
                    render_plan=fresh_variant.render_plan,
                    content=fresh_variant.content,
                    variant_id=fresh_variant.variant_id,
                    content_overrides=old_variant.content_overrides,
                    layout_overrides=old_variant.layout_overrides,
                    edited_nodes=old_variant.edited_nodes,
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
        index=manifest.variants.index(target_variant) + 1,
        render_plan=target_variant.render_plan,
        content=fresh_content,
        variant_id=target_variant.variant_id,
        content_overrides=next_overrides,
        layout_overrides=target_variant.layout_overrides,
        edited_nodes=target_variant.edited_nodes,
    )
    return _replace_variant(
        manifest,
        target_variant=target_variant,
        next_variant=next_variant,
        selected_variant_id=target_variant.variant_id,
    )


def selected_preview_data(payload: dict[str, object] | ProjectManifest) -> dict[str, object]:
    manifest = payload if isinstance(payload, ProjectManifest) else ProjectManifest.from_dict(payload)
    selected = _selected_variant(manifest)
    return {
        "brief": manifest.brief.to_dict(),
        "selected_variant_id": manifest.selected_variant_id,
        "selected_variant": _resolved_variant_payload(selected, brief=manifest.brief) if selected else {},
        "variants": [_resolved_variant_payload(variant, brief=manifest.brief) for variant in manifest.variants],
        "statuses": [stage.to_dict() for stage in manifest.statuses],
    }


def build_preview_variant(
    manifest: ProjectManifest,
    *,
    variant_id: str | None = None,
    overrides: dict[str, object] | None = None,
    remix_label: str | None = None,
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
    )


def apply_canvas_command_to_manifest(
    manifest: ProjectManifest,
    *,
    action: str,
    variant_id: str | None = None,
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
    resolved_content = _resolved_content(target_variant, brief=manifest.brief, render_plan=effective_plan).data
    next_content_overrides = dict(target_variant.content_overrides)
    next_layout_overrides = dict(target_variant.layout_overrides)
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
        section_order = list(effective_plan.section_order)
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
        next_layout_overrides["section_order"] = section_order
        changed_paths = ["render_plan.section_order"]
    elif action == "toggle_section":
        if not section_name:
            raise ValueError("Section name is required.")
        visibility = _normalized_section_visibility(
            effective_plan.section_visibility,
            next_layout_overrides.get("section_visibility"),
        )
        visibility[section_name] = bool(value) if isinstance(value, bool) else not bool(visibility.get(section_name, True))
        next_layout_overrides["section_visibility"] = visibility
        changed_paths = [f"render_plan.section_visibility.{section_name}"]
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
        index=manifest.variants.index(target_variant) + 1,
        render_plan=target_variant.render_plan,
        content=target_variant.content,
        variant_id=target_variant.variant_id,
        content_overrides=next_content_overrides,
        layout_overrides=next_layout_overrides,
        edited_nodes=next_edited_nodes,
    )
    updated_manifest = _replace_variant(
        manifest,
        target_variant=target_variant,
        next_variant=next_variant,
        selected_variant_id=target_variant.variant_id,
    )
    return updated_manifest, changed_paths
