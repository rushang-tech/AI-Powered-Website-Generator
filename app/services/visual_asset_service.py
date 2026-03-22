from __future__ import annotations

import re
from collections import defaultdict
from typing import Any
from urllib.parse import quote

from app.services.taste_engine import BriefInput, RenderPlan

LUCIDE_STATIC_VERSION = "0.577.0"
LUCIDE_STATIC_BASE_URL = f"https://cdn.jsdelivr.net/npm/lucide-static@{LUCIDE_STATIC_VERSION}/icons"
UNSPLASH_SOURCE_BASE_URL = "https://source.unsplash.com/featured"
LUCIDE_FALLBACK_ORDER = (
    "sparkles",
    "layers-3",
    "workflow",
    "zap",
    "shield",
    "palette",
    "bar-chart-3",
    "users",
    "rocket",
    "globe",
    "circle",
)
SECTION_MEDIA_SPECS: dict[str, dict[str, object]] = {
    "collections": {"width": 1200, "height": 900, "minimum": 2, "maximum": 4, "alt_suffix": "collection feature"},
    "products": {"width": 900, "height": 1080, "minimum": 6, "maximum": 8, "alt_suffix": "product preview"},
    "projects": {"width": 800, "height": 600, "minimum": 3, "maximum": 6, "alt_suffix": "project preview"},
    "workflows": {"width": 1280, "height": 860, "minimum": 2, "maximum": 4, "alt_suffix": "workflow visual"},
    "services": {"width": 1040, "height": 820, "minimum": 2, "maximum": 4, "alt_suffix": "service visual"},
}
_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "brand",
    "build",
    "built",
    "button",
    "by",
    "card",
    "clear",
    "cta",
    "for",
    "from",
    "hero",
    "in",
    "into",
    "is",
    "it",
    "its",
    "launch",
    "landing",
    "modern",
    "note",
    "of",
    "on",
    "or",
    "page",
    "pricing",
    "proof",
    "section",
    "site",
    "startup",
    "that",
    "the",
    "their",
    "this",
    "to",
    "turn",
    "users",
    "website",
    "with",
    "work",
}
_ICON_KEYWORDS = {
    "sparkles": {"bright", "creative", "delight", "editorial", "glow", "luxury", "magic", "polish", "spark", "sparkles"},
    "layers-3": {"architecture", "depth", "framework", "geometric", "grid", "layer", "layers", "minimal", "system", "stack"},
    "workflow": {"automation", "dashboard", "flow", "interface", "journey", "ops", "pipeline", "process", "product", "workflow"},
    "zap": {"agile", "energy", "fast", "instant", "momentum", "quick", "rapid", "speed", "zap"},
    "shield": {"compliance", "protection", "reliable", "safe", "safety", "secure", "security", "shield", "trust"},
    "palette": {"art", "brand", "branding", "color", "craft", "design", "identity", "palette", "style", "visual"},
    "bar-chart-3": {"analytics", "data", "forecast", "growth", "insight", "kpi", "metric", "performance", "reporting", "revenue"},
    "users": {"audience", "client", "clients", "collaboration", "community", "customer", "customers", "people", "team", "teams"},
    "rocket": {"accelerate", "ambition", "launch", "lift", "orbit", "release", "rocket", "scale", "ship", "trajectory"},
    "globe": {"around", "global", "globe", "market", "reach", "world", "worldwide"},
    "circle": {"calm", "focus", "mono", "monochrome", "simple", "steady"},
}
_ICON_STYLE_BIASES = {
    "rounded": ("sparkles", "users", "globe"),
    "soft": ("sparkles", "palette", "users"),
    "editorial": ("sparkles", "layers-3", "palette"),
    "sharp": ("layers-3", "shield", "circle"),
    "monochrome": ("circle", "layers-3", "shield"),
    "geometric": ("layers-3", "workflow", "circle"),
    "product": ("workflow", "zap", "layers-3"),
    "interface": ("workflow", "layers-3", "zap"),
    "luxury": ("sparkles", "palette", "shield"),
    "playful": ("sparkles", "users", "rocket"),
}


def _coerce_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()



def _tokenize(raw_text: str) -> list[str]:
    return re.findall(r"[a-z0-9][a-z0-9\-]*", raw_text.lower())



def extract_visual_keywords(*raw_texts: str | tuple[str, float], limit: int = 8) -> list[str]:
    scores: dict[str, float] = defaultdict(float)
    first_seen: dict[str, int] = {}
    cursor = 0

    for raw_item in raw_texts:
        if isinstance(raw_item, tuple):
            raw_text, weight = raw_item
        else:
            raw_text, weight = raw_item, 1.0
        for token in _tokenize(_coerce_text(raw_text)):
            if token in _STOPWORDS or len(token) < 3:
                continue
            if token not in first_seen:
                first_seen[token] = cursor
                cursor += 1
            scores[token] += float(weight)

    ranked = sorted(scores, key=lambda token: (-scores[token], first_seen[token]))
    return ranked[:limit]



def sanitize_visual_query(keywords: list[str], *, minimum: int = 2, maximum: int = 4) -> str:
    cleaned: list[str] = []
    seen: set[str] = set()
    for token in keywords:
        normalized = re.sub(r"[^a-z0-9\-]", "", token.lower()).strip("-")
        if not normalized or normalized in seen or normalized in _STOPWORDS:
            continue
        seen.add(normalized)
        cleaned.append(normalized)
        if len(cleaned) >= maximum:
            break
    if len(cleaned) < minimum:
        return ""
    return ",".join(cleaned)



def _fallback_keywords(*groups: list[str], minimum: int = 2, maximum: int = 4) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for token in group:
            normalized = re.sub(r"[^a-z0-9\-]", "", token.lower()).strip("-")
            if not normalized or normalized in seen or normalized in _STOPWORDS:
                continue
            seen.add(normalized)
            merged.append(normalized)
            if len(merged) >= maximum:
                return merged
    return merged[:maximum] if len(merged) >= minimum else []



def _icon_url(icon_name: str) -> str:
    return f"{LUCIDE_STATIC_BASE_URL}/{icon_name}.svg"



def _icon_label(icon_name: str) -> str:
    return icon_name.replace("-", " ").title()



def resolve_lucide_icon(text: str, *, icon_style: str = "", fallback_index: int = 0) -> dict[str, str]:
    tokens = set(_tokenize(text))
    scores: dict[str, float] = defaultdict(float)

    for icon_name, keywords in _ICON_KEYWORDS.items():
        scores[icon_name] += sum(2.0 for token in tokens if token in keywords)

    bias_order = list(LUCIDE_FALLBACK_ORDER)
    for token in _tokenize(icon_style):
        for icon_name in _ICON_STYLE_BIASES.get(token, ()):
            scores[icon_name] += 0.75
            if icon_name in bias_order:
                bias_order.remove(icon_name)
            bias_order.insert(0, icon_name)

    ranked = sorted(
        LUCIDE_FALLBACK_ORDER,
        key=lambda icon_name: (-scores[icon_name], bias_order.index(icon_name)),
    )
    icon_name = ranked[0] if scores[ranked[0]] > 0 else bias_order[fallback_index % len(bias_order)]
    return {
        "library": "lucide",
        "name": icon_name,
        "url": _icon_url(icon_name),
        "label": _icon_label(icon_name),
    }



def _build_unsplash_url(query: str, *, width: int, height: int) -> str:
    encoded_query = quote(query, safe=",")
    return f"{UNSPLASH_SOURCE_BASE_URL}/{width}x{height}/?{encoded_query}"



def _hero_visual(brief: BriefInput, render_plan: RenderPlan, content: dict[str, Any]) -> dict[str, str]:
    hero_support = []
    for key in ("collections", "products", "projects", "workflows", "services"):
        items = content.get(key) if isinstance(content.get(key), list) else []
        if items and isinstance(items[0], dict):
            hero_support.extend(
                [
                    _coerce_text(items[0].get("title")),
                    _coerce_text(items[0].get("meta")),
                    _coerce_text(items[0].get("desc")),
                ]
            )
    primary_keywords = extract_visual_keywords(
        (brief.goal, 3.0),
        (brief.audience, 1.4),
        (brief.brand_tone, 1.2),
        (brief.notes, 1.6),
        (brief.icon_style, 0.8),
        (render_plan.template_key, 1.8),
        (render_plan.industry, 2.4),
        (render_plan.vibe, 1.1),
        (render_plan.art_direction.replace("_", " "), 1.0),
        (_coerce_text(content.get("hero_title")), 3.0),
        (_coerce_text(content.get("hero_subtitle")), 1.4),
        (" ".join(hero_support), 1.2),
        limit=10,
    )
    query_keywords = _fallback_keywords(
        primary_keywords,
        extract_visual_keywords(render_plan.template_key, render_plan.industry, render_plan.vibe, render_plan.art_direction.replace("_", " "), limit=4),
    )
    query = sanitize_visual_query(query_keywords)
    if not query:
        return {}

    alt_tokens = query.split(",")[:3]
    alt_subject = " ".join(token.title() for token in alt_tokens)
    return {
        "url": _build_unsplash_url(query, width=1600, height=900),
        "query": query,
        "alt": f"{alt_subject} visual for hero section",
        "source": "unsplash-source",
    }



def _section_alt_subject(item: dict[str, Any], *, list_name: str, render_plan: RenderPlan) -> str:
    title = _coerce_text(item.get("title"))
    meta = _coerce_text(item.get("meta"))
    if title:
        return title
    if meta:
        return meta
    return f"{render_plan.template_key.replace('_', ' ').title()} {list_name.replace('_', ' ').title()}"



def _list_media(list_name: str, items: Any, *, brief: BriefInput, render_plan: RenderPlan) -> list[dict[str, str]]:
    spec = SECTION_MEDIA_SPECS.get(list_name)
    if not spec or not isinstance(items, list):
        return []

    width = int(spec["width"])
    height = int(spec["height"])
    maximum = int(spec["maximum"])
    alt_suffix = str(spec["alt_suffix"])
    output: list[dict[str, str]] = []

    for item in items[:maximum]:
        if not isinstance(item, dict):
            continue
        title = _coerce_text(item.get("title"))
        meta = _coerce_text(item.get("meta"))
        desc = _coerce_text(item.get("desc"))
        primary_keywords = extract_visual_keywords(
            (title, 3.0),
            (meta, 1.8),
            (desc, 1.2),
            (brief.goal, 1.4),
            (brief.audience, 0.8),
            (brief.icon_style, 0.5),
            (render_plan.template_key, 1.5),
            (render_plan.industry, 2.0),
            (render_plan.vibe, 1.0),
            (list_name.replace("_", " "), 1.2),
            limit=10,
        )
        query_keywords = _fallback_keywords(
            primary_keywords,
            extract_visual_keywords(render_plan.template_key, render_plan.industry, list_name.replace("_", " "), render_plan.vibe, limit=4),
        )
        query = sanitize_visual_query(query_keywords)
        if not query:
            continue
        output.append(
            {
                "url": _build_unsplash_url(query, width=width, height=height),
                "query": query,
                "alt": f"{_section_alt_subject(item, list_name=list_name, render_plan=render_plan)} {alt_suffix}",
                "source": "unsplash-source",
            }
        )
    return output



def _list_icons(items: Any, *, brief: BriefInput, render_plan: RenderPlan) -> list[dict[str, str]]:
    if not isinstance(items, list):
        return []

    icons: list[dict[str, str]] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        icon_text = " ".join(
            part
            for part in (
                _coerce_text(item.get("title")),
                _coerce_text(item.get("desc")),
                brief.icon_style,
                brief.brand_tone,
                render_plan.vibe,
                render_plan.art_direction.replace("_", " "),
            )
            if part
        )
        icons.append(resolve_lucide_icon(icon_text, icon_style=brief.icon_style, fallback_index=index))
    return icons



def build_variant_visuals(*, brief: BriefInput, render_plan: RenderPlan, content: dict[str, Any]) -> dict[str, Any]:
    section_media = {
        section_name: _list_media(section_name, content.get(section_name), brief=brief, render_plan=render_plan)
        for section_name in SECTION_MEDIA_SPECS
    }
    section_media = {key: value for key, value in section_media.items() if value}
    project_images = list(section_media.get("projects", []))
    return {
        "hero_image": _hero_visual(brief, render_plan, content),
        "project_images": project_images,
        "feature_icons": _list_icons(content.get("features"), brief=brief, render_plan=render_plan),
        "capability_icons": _list_icons(content.get("capabilities"), brief=brief, render_plan=render_plan),
        "section_media": section_media,
    }
