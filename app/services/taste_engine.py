from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, replace
from typing import Any


DEFAULT_TEMPLATE_SIGNALS: dict[str, dict[str, tuple[str, ...]]] = {
    "landing": {
        "phrases": (
            "landing page",
            "marketing page",
            "campaign page",
            "lead generation",
            "waitlist page",
            "event page",
        ),
        "strong_terms": (
            "landing",
            "startup",
            "agency",
            "service",
            "business",
            "brand",
            "campaign",
            "conversion",
            "book",
            "appointment",
        ),
        "support_terms": (
            "company",
            "audience",
            "offer",
            "growth",
            "lead",
            "cta",
            "headline",
        ),
    },
    "portfolio": {
        "phrases": (
            "personal website",
            "case study",
            "case studies",
            "my portfolio",
            "about me",
        ),
        "strong_terms": (
            "portfolio",
            "resume",
            "cv",
            "designer",
            "developer",
            "photographer",
            "artist",
            "freelance",
            "freelancer",
            "showcase",
        ),
        "support_terms": (
            "projects",
            "experience",
            "work",
            "skills",
            "bio",
            "profile",
        ),
    },
    "product": {
        "phrases": (
            "product launch",
            "pricing page",
            "online store",
            "ecommerce store",
            "saas product",
            "app landing",
        ),
        "strong_terms": (
            "product",
            "store",
            "shop",
            "ecommerce",
            "saas",
            "app",
            "pricing",
            "subscription",
            "checkout",
            "trial",
        ),
        "support_terms": (
            "launch",
            "feature",
            "features",
            "plan",
            "plans",
            "demo",
            "growth",
            "retention",
        ),
    },
}

ART_DIRECTION_SIGNALS: dict[str, dict[str, tuple[str, ...]]] = {
    "modern_editorial": {
        "phrases": ("clean layout", "minimal style", "professional look", "editorial look"),
        "strong_terms": ("clean", "minimal", "professional", "simple", "sleek", "editorial"),
        "support_terms": ("balanced", "structured", "neutral", "refined", "b2b"),
    },
    "luxury_serif": {
        "phrases": ("premium feel", "high end", "editorial luxury", "quiet luxury"),
        "strong_terms": ("premium", "elegant", "luxury", "exclusive", "refined", "timeless"),
        "support_terms": ("polished", "crafted", "serif", "soft", "rich"),
    },
    "playful_blocks": {
        "phrases": ("kid friendly", "children friendly", "fun vibe", "bright colors"),
        "strong_terms": ("fun", "colorful", "friendly", "quirky", "vibrant", "playful"),
        "support_terms": ("kids", "children", "joyful", "bold", "cartoon"),
    },
    "cyber_signal": {
        "phrases": ("futuristic neon", "sci fi", "tech noir", "hacker vibe"),
        "strong_terms": ("neon", "futuristic", "cyber", "cyberpunk", "glow", "techno"),
        "support_terms": ("matrix", "electric", "night", "gaming", "hologram"),
    },
    "brutalist_poster": {
        "phrases": ("poster style", "raw design", "graphic design system"),
        "strong_terms": ("brutalist", "poster", "graphic", "raw", "sharp", "experimental"),
        "support_terms": ("loud", "contrast", "angular", "bold", "print"),
    },
    "warm_gradient": {
        "phrases": ("warm gradient", "soft startup", "friendly tech"),
        "strong_terms": ("warm", "gradient", "sunset", "approachable", "optimistic"),
        "support_terms": ("soft", "welcoming", "uplifting", "bright", "human"),
    },
}

INDUSTRY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "fitness": ("fitness", "gym", "workout", "yoga", "coach"),
    "technology": ("tech", "ai", "saas", "software", "app", "developer"),
    "retail": ("shop", "store", "product", "ecommerce", "fashion"),
    "creative": ("designer", "artist", "photography", "portfolio", "studio"),
    "finance": ("finance", "bank", "investment", "fintech", "accounting"),
    "healthcare": ("health", "clinic", "medical", "wellness", "doctor"),
}

VIBE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "minimal": ("minimal", "clean", "simple"),
    "bold": ("bold", "loud", "strong", "poster"),
    "playful": ("playful", "fun", "friendly", "quirky"),
    "premium": ("luxury", "premium", "exclusive", "elegant"),
    "futuristic": ("futuristic", "cyber", "neon", "techno"),
    "warm": ("warm", "approachable", "soft", "friendly"),
}

DENSITY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "airy": ("airy", "minimal", "breathing", "spacious", "light"),
    "balanced": ("balanced", "clear", "focused", "structured"),
    "dense": ("dense", "information", "detailed", "rich", "packed"),
}

MOTION_KEYWORDS: dict[str, tuple[str, ...]] = {
    "calm": ("calm", "quiet", "subtle", "steady", "slow"),
    "moderate": ("dynamic", "lively", "animated", "interactive"),
    "energetic": ("energetic", "fast", "bold", "kinetic", "immersive"),
}

STOPWORDS = {
    "a",
    "an",
    "the",
    "for",
    "with",
    "and",
    "that",
    "this",
    "from",
    "your",
    "our",
    "into",
    "like",
    "need",
    "build",
    "make",
    "website",
    "page",
    "site",
}

LAYOUT_LIBRARY: dict[str, dict[str, dict[str, Any]]] = {
    "landing": {
        "split_hero": {
            "hero_variant": "split",
            "section_order": ["hero", "metrics", "features", "proof", "cta"],
            "keywords": ("split", "conversion", "clarity", "editorial"),
            "density_bias": "balanced",
            "motion_bias": "moderate",
        },
        "staggered_bands": {
            "hero_variant": "banded",
            "section_order": ["hero", "features", "metrics", "cta"],
            "keywords": ("campaign", "service", "story", "sectioned"),
            "density_bias": "balanced",
            "motion_bias": "calm",
        },
        "immersive_layers": {
            "hero_variant": "immersive",
            "section_order": ["hero", "proof", "features", "cta"],
            "keywords": ("immersive", "layered", "visual", "launch"),
            "density_bias": "airy",
            "motion_bias": "energetic",
        },
        "proof_first": {
            "hero_variant": "statement",
            "section_order": ["proof", "hero", "features", "cta"],
            "keywords": ("trust", "proof", "testimonial", "credibility"),
            "density_bias": "dense",
            "motion_bias": "calm",
        },
    },
    "portfolio": {
        "editorial_casebook": {
            "hero_variant": "editorial",
            "section_order": ["hero", "projects", "about", "proof", "cta"],
            "keywords": ("editorial", "case study", "story", "curated"),
            "density_bias": "balanced",
            "motion_bias": "calm",
        },
        "masonry_showcase": {
            "hero_variant": "gallery",
            "section_order": ["hero", "projects", "capabilities", "cta"],
            "keywords": ("showcase", "gallery", "visual", "masonry"),
            "density_bias": "airy",
            "motion_bias": "moderate",
        },
        "minimal_cv": {
            "hero_variant": "resume",
            "section_order": ["hero", "about", "capabilities", "projects", "cta"],
            "keywords": ("resume", "cv", "professional", "clean"),
            "density_bias": "dense",
            "motion_bias": "calm",
        },
        "story_panels": {
            "hero_variant": "panels",
            "section_order": ["hero", "proof", "projects", "about", "cta"],
            "keywords": ("panels", "narrative", "story", "sequence"),
            "density_bias": "balanced",
            "motion_bias": "moderate",
        },
    },
    "product": {
        "pricing_first": {
            "hero_variant": "pricing",
            "section_order": ["hero", "pricing", "features", "proof", "cta"],
            "keywords": ("pricing", "plans", "subscription", "trial"),
            "density_bias": "dense",
            "motion_bias": "calm",
        },
        "feature_scroll": {
            "hero_variant": "feature-led",
            "section_order": ["hero", "features", "pricing", "proof", "cta"],
            "keywords": ("features", "demo", "workflow", "product"),
            "density_bias": "balanced",
            "motion_bias": "moderate",
        },
        "contrast_split": {
            "hero_variant": "contrast",
            "section_order": ["hero", "proof", "features", "pricing", "cta"],
            "keywords": ("contrast", "split", "premium", "positioning"),
            "density_bias": "balanced",
            "motion_bias": "moderate",
        },
        "launch_countdown": {
            "hero_variant": "countdown",
            "section_order": ["hero", "metrics", "pricing", "features", "cta"],
            "keywords": ("launch", "countdown", "beta", "release"),
            "density_bias": "airy",
            "motion_bias": "energetic",
        },
    },
}


def _slot_schema(
    *,
    text_slots: tuple[str, ...],
    list_slots: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    return {
        "text_slots": list(text_slots),
        "list_slots": list_slots,
    }


SECTION_SCHEMAS: dict[str, dict[str, Any]] = {
    "landing": _slot_schema(
        text_slots=(
            "hero_eyebrow",
            "hero_title",
            "hero_subtitle",
            "cta_text",
            "cta_note",
            "stat_1_value",
            "stat_1_label",
            "stat_2_value",
            "stat_2_label",
            "stat_3_value",
            "stat_3_label",
            "proof_quote",
            "proof_author",
        ),
        list_slots={
            "features": {"item_fields": ["title", "desc"], "min_items": 3, "max_items": 6},
            "offers": {"item_fields": ["title", "desc", "meta"], "min_items": 2, "max_items": 4},
        },
    ),
    "portfolio": _slot_schema(
        text_slots=(
            "hero_eyebrow",
            "hero_title",
            "hero_subtitle",
            "cta_text",
            "cta_note",
            "about_text",
            "proof_quote",
            "proof_author",
        ),
        list_slots={
            "projects": {"item_fields": ["title", "desc", "meta"], "min_items": 3, "max_items": 6},
            "capabilities": {"item_fields": ["title", "desc"], "min_items": 3, "max_items": 5},
        },
    ),
    "product": _slot_schema(
        text_slots=(
            "hero_eyebrow",
            "hero_title",
            "hero_subtitle",
            "price_badge",
            "cta_text",
            "cta_note",
            "stat_1_value",
            "stat_1_label",
            "stat_2_value",
            "stat_2_label",
            "stat_3_value",
            "stat_3_label",
            "proof_quote",
            "proof_author",
        ),
        list_slots={
            "features": {"item_fields": ["title", "desc"], "min_items": 3, "max_items": 6},
            "offers": {"item_fields": ["title", "desc", "meta"], "min_items": 3, "max_items": 4},
        },
    ),
}


@dataclass(frozen=True)
class BriefInput:
    goal: str
    audience: str
    brand_tone: str
    content_density: str
    motion_level: str
    name: str
    notes: str
    prompt: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)

    def to_prompt_text(self) -> str:
        pieces = [
            self.goal,
            self.audience,
            self.brand_tone,
            self.name,
            self.notes,
            self.prompt,
        ]
        return ". ".join(item.strip() for item in pieces if item and item.strip())


@dataclass(frozen=True)
class RenderPlan:
    template_key: str
    template_file: str
    theme_key: str
    art_direction: str
    layout_mode: str
    density: str
    motion_level: str
    section_order: list[str]
    section_visibility: dict[str, bool]
    hero_variant: str
    industry: str
    vibe: str
    keywords: list[str]
    confidence: float
    reasons: list[str]
    slot_schema: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def clean_json_response(raw_text: str) -> str:
    cleaned = raw_text.replace("```json", "").replace("```", "").strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}") + 1
    if start != -1 and end != -1:
        return cleaned[start:end]
    return cleaned


def _coerce_str(value: Any, default: str = "") -> str:
    if isinstance(value, str):
        text = value.strip()
        return text if text else default
    return default


def _coerce_list_of_str(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    output: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            continue
        normalized = item.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        output.append(normalized)
    return output


def _normalize_prompt(prompt: str) -> str:
    return re.sub(r"\s+", " ", prompt.lower()).strip()


def _tokenize(prompt: str) -> list[str]:
    return re.findall(r"[a-z0-9][a-z0-9\-]*", prompt.lower())


def _stem_token(token: str) -> str:
    if token.endswith("ies") and len(token) > 4:
        return f"{token[:-3]}y"
    if token.endswith("s") and len(token) > 3 and not token.endswith("ss"):
        return token[:-1]
    return token


def _build_token_set(tokens: list[str]) -> set[str]:
    token_set: set[str] = set()
    for token in tokens:
        token_set.add(token)
        token_set.add(_stem_token(token))
    return token_set


def _signal_match(signal: str, *, prompt: str, token_set: set[str]) -> bool:
    normalized = signal.lower().strip()
    if not normalized:
        return False
    if " " in normalized:
        return normalized in prompt
    if "-" in normalized and normalized.replace("-", " ") in prompt:
        return True
    return normalized in token_set


def _score_signal_groups(
    prompt: str,
    token_set: set[str],
    signal_map: dict[str, dict[str, tuple[str, ...]]],
    *,
    phrase_weight: float,
    strong_weight: float,
    support_weight: float,
) -> tuple[dict[str, float], dict[str, int]]:
    scores: dict[str, float] = {}
    hits: dict[str, int] = {}

    for key, rules in signal_map.items():
        score = 0.0
        hit_count = 0
        for phrase in rules.get("phrases", ()):
            if _signal_match(phrase, prompt=prompt, token_set=token_set):
                score += phrase_weight
                hit_count += 1
        for term in rules.get("strong_terms", ()):
            if _signal_match(term, prompt=prompt, token_set=token_set):
                score += strong_weight
                hit_count += 1
        for term in rules.get("support_terms", ()):
            if _signal_match(term, prompt=prompt, token_set=token_set):
                score += support_weight
                hit_count += 1
        scores[key] = round(score, 4)
        hits[key] = hit_count

    return scores, hits


def _score_by_keywords(prompt: str, token_set: set[str], keyword_map: dict[str, tuple[str, ...]]) -> dict[str, float]:
    scores: dict[str, float] = {}
    for key, words in keyword_map.items():
        score = 0.0
        for word in words:
            if _signal_match(word, prompt=prompt, token_set=token_set):
                score += 1.0
        scores[key] = score
    return scores


def _top_two(scores: dict[str, float]) -> tuple[tuple[str, float], tuple[str, float]]:
    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    if not ordered:
        return ("landing", 0.0), ("landing", 0.0)
    if len(ordered) == 1:
        return ordered[0], ordered[0]
    return ordered[0], ordered[1]


def _extract_keywords(prompt: str) -> list[str]:
    terms = re.findall(r"[a-z0-9][a-z0-9\-]+", prompt.lower())
    output: list[str] = []
    seen: set[str] = set()
    for term in terms:
        if term in STOPWORDS or len(term) < 3 or term in seen:
            continue
        output.append(term)
        seen.add(term)
        if len(output) >= 8:
            break
    return output


def _safe_default_key(allowed_keys: set[str], preferred: str) -> str:
    if preferred in allowed_keys:
        return preferred
    if not allowed_keys:
        return preferred
    return sorted(allowed_keys)[0]


def _resolve_choice(value: Any, *, allowed: set[str], default: str) -> str:
    chosen = _coerce_str(value, default).lower()
    if chosen not in allowed:
        return default
    return chosen


def _infer_category(prompt: str, token_set: set[str], keyword_map: dict[str, tuple[str, ...]], default: str) -> str:
    scores = _score_by_keywords(prompt, token_set, keyword_map)
    winner, score = _top_two(scores)[0]
    return winner if score > 0 else default


def _compute_rule_confidence(top_score: float, gap: float, signal_hits: int) -> float:
    if top_score <= 0:
        return 0.24
    confidence = 0.34 + min(top_score, 10.0) * 0.055 + min(gap, 3.0) * 0.12 + min(signal_hits, 7) * 0.03
    return max(0.0, min(0.97, confidence))


def _normalize_density(value: str) -> str:
    return value if value in {"airy", "balanced", "dense"} else "balanced"


def _normalize_motion(value: str) -> str:
    return value if value in {"calm", "moderate", "energetic"} else "moderate"


def normalize_brief(raw_prompt: str = "", raw_brief: dict[str, Any] | None = None) -> BriefInput:
    raw_brief = raw_brief or {}
    goal = _coerce_str(raw_brief.get("goal"), raw_prompt)
    audience = _coerce_str(raw_brief.get("audience"), "General audience")
    brand_tone = _coerce_str(raw_brief.get("brand_tone"), "Clear and modern")
    content_density = _normalize_density(_coerce_str(raw_brief.get("content_density"), "balanced").lower())
    motion_level = _normalize_motion(_coerce_str(raw_brief.get("motion_level"), "moderate").lower())
    name = _coerce_str(raw_brief.get("name"))
    notes = _coerce_str(raw_brief.get("notes"), raw_prompt if raw_prompt and raw_prompt != goal else "")
    prompt = _coerce_str(raw_prompt)
    return BriefInput(
        goal=goal,
        audience=audience,
        brand_tone=brand_tone,
        content_density=content_density,
        motion_level=motion_level,
        name=name,
        notes=notes,
        prompt=prompt,
    )


def _apply_intent_boosts(
    *,
    token_set: set[str],
    template_scores: dict[str, float],
    template_hits: dict[str, int],
    art_scores: dict[str, float],
    art_hits: dict[str, int],
) -> list[str]:
    reasons: list[str] = []

    personal_words = {"my", "me", "personal", "i"}
    creator_words = {"developer", "designer", "photographer", "artist", "freelancer", "portfolio"}
    if personal_words.intersection(token_set) and creator_words.intersection(token_set):
        template_scores["portfolio"] = template_scores.get("portfolio", 0.0) + 1.9
        template_hits["portfolio"] = template_hits.get("portfolio", 0) + 1
        reasons.append("Intent boost favored portfolio.")

    product_words = {"pricing", "plan", "plans", "subscription", "checkout", "trial", "saas", "store", "shop"}
    launch_words = {"launch", "preorder", "beta", "release", "roadmap"}
    if product_words.intersection(token_set):
        template_scores["product"] = template_scores.get("product", 0.0) + 1.9
        template_hits["product"] = template_hits.get("product", 0) + 1
        reasons.append("Intent boost favored product.")
    if launch_words.intersection(token_set):
        template_scores["product"] = template_scores.get("product", 0.0) + 1.1
        template_hits["product"] = template_hits.get("product", 0) + 1

    campaign_words = {"campaign", "lead", "service", "agency", "book", "appointment", "consulting"}
    if campaign_words.intersection(token_set):
        template_scores["landing"] = template_scores.get("landing", 0.0) + 1.4
        template_hits["landing"] = template_hits.get("landing", 0) + 1
        reasons.append("Intent boost favored landing.")

    kids_words = {"kids", "kid", "children", "child", "school", "classroom", "workshop"}
    if kids_words.intersection(token_set):
        art_scores["playful_blocks"] = art_scores.get("playful_blocks", 0.0) + 2.2
        art_hits["playful_blocks"] = art_hits.get("playful_blocks", 0) + 1
        reasons.append("Youth audience boosted playful art direction.")

    premium_words = {"luxury", "premium", "exclusive", "high-end", "upscale", "elegant", "refined"}
    if premium_words.intersection(token_set):
        art_scores["luxury_serif"] = art_scores.get("luxury_serif", 0.0) + 2.0
        art_hits["luxury_serif"] = art_hits.get("luxury_serif", 0) + 1
        reasons.append("Premium language boosted luxury art direction.")

    cyber_words = {"cyber", "neon", "futuristic", "hacker", "matrix", "gaming", "dark"}
    if cyber_words.intersection(token_set):
        art_scores["cyber_signal"] = art_scores.get("cyber_signal", 0.0) + 2.1
        art_hits["cyber_signal"] = art_hits.get("cyber_signal", 0) + 1
        reasons.append("Futuristic language boosted cyber art direction.")

    warm_words = {"approachable", "friendly", "warm", "welcoming", "human"}
    if warm_words.intersection(token_set):
        art_scores["warm_gradient"] = art_scores.get("warm_gradient", 0.0) + 1.7
        art_hits["warm_gradient"] = art_hits.get("warm_gradient", 0) + 1

    graphic_words = {"poster", "graphic", "raw", "brutalist", "contrast"}
    if graphic_words.intersection(token_set):
        art_scores["brutalist_poster"] = art_scores.get("brutalist_poster", 0.0) + 1.8
        art_hits["brutalist_poster"] = art_hits.get("brutalist_poster", 0) + 1

    return reasons[:4]


def _rank_layouts(
    template_key: str,
    *,
    prompt: str,
    token_set: set[str],
    density: str,
    motion_level: str,
    vibe: str,
) -> list[str]:
    recipes = LAYOUT_LIBRARY.get(template_key, {})
    scores: list[tuple[str, float]] = []
    for layout_mode, recipe in recipes.items():
        score = 0.0
        for hint in recipe.get("keywords", ()):
            if _signal_match(hint, prompt=prompt, token_set=token_set):
                score += 1.1
        if recipe.get("density_bias") == density:
            score += 0.8
        if recipe.get("motion_bias") == motion_level:
            score += 0.8
        if vibe in recipe.get("keywords", ()):
            score += 0.6
        scores.append((layout_mode, score))

    scores.sort(key=lambda item: item[1], reverse=True)
    ordered = [item[0] for item in scores]
    if ordered:
        return ordered
    return list(recipes.keys())


def _section_visibility(section_order: list[str], overrides: dict[str, bool] | None = None) -> dict[str, bool]:
    visibility = {section: True for section in section_order}
    for key, value in (overrides or {}).items():
        if key in visibility:
            visibility[key] = bool(value)
    return visibility


def _template_file_for(template_key: str, template_catalog: dict[str, dict[str, Any]]) -> str:
    template_config = template_catalog.get(template_key, {})
    return _coerce_str(template_config.get("template_file"), "generated/site_builder.html")


def _recipe_for(template_key: str, layout_mode: str) -> dict[str, Any]:
    recipes = LAYOUT_LIBRARY.get(template_key, {})
    if layout_mode in recipes:
        return recipes[layout_mode]
    if recipes:
        return recipes[sorted(recipes.keys())[0]]
    return {"hero_variant": "statement", "section_order": ["hero", "cta"], "keywords": ()}


def _make_plan(
    *,
    template_key: str,
    art_direction: str,
    layout_mode: str,
    density: str,
    motion_level: str,
    industry: str,
    vibe: str,
    keywords: list[str],
    confidence: float,
    reasons: list[str],
    template_catalog: dict[str, dict[str, Any]],
    section_visibility: dict[str, bool] | None = None,
) -> RenderPlan:
    recipe = _recipe_for(template_key, layout_mode)
    section_order = list(recipe.get("section_order", ["hero", "cta"]))
    slot_schema = SECTION_SCHEMAS.get(template_key, {"text_slots": [], "list_slots": {}})
    return RenderPlan(
        template_key=template_key,
        template_file=_template_file_for(template_key, template_catalog),
        theme_key=art_direction,
        art_direction=art_direction,
        layout_mode=layout_mode,
        density=density,
        motion_level=motion_level,
        section_order=section_order,
        section_visibility=_section_visibility(section_order, section_visibility),
        hero_variant=_coerce_str(recipe.get("hero_variant"), "statement"),
        industry=industry,
        vibe=vibe,
        keywords=keywords[:8],
        confidence=round(confidence, 3),
        reasons=reasons[:5],
        slot_schema=slot_schema,
    )


def _llm_override_profile(
    model: Any,
    *,
    brief: BriefInput,
    template_keys: list[str],
    art_keys: list[str],
    layout_keys: list[str],
) -> dict[str, Any] | None:
    prompt = f"""
You are a website taste-routing assistant.
Return VALID JSON ONLY.

Choose exactly one template_key from {template_keys}.
Choose exactly one art_direction from {art_keys}.
Choose exactly one layout_mode from {layout_keys}.
Choose exactly one density from ["airy", "balanced", "dense"].
Choose exactly one motion_level from ["calm", "moderate", "energetic"].

JSON schema:
{{
  "template_key": "landing",
  "art_direction": "modern_editorial",
  "layout_mode": "split_hero",
  "density": "balanced",
  "motion_level": "moderate",
  "industry": "technology",
  "vibe": "bold",
  "keywords": ["launch", "startup", "demo"],
  "confidence": 0.78,
  "reason": "Clear launch framing with premium positioning"
}}

BRIEF:
{brief.to_prompt_text()}
""".strip()
    response = model.generate_content(prompt)
    raw = clean_json_response(getattr(response, "text", ""))
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        return None
    return {
        "template_key": _coerce_str(parsed.get("template_key")).lower(),
        "art_direction": _coerce_str(parsed.get("art_direction")).lower(),
        "layout_mode": _coerce_str(parsed.get("layout_mode")).lower(),
        "density": _normalize_density(_coerce_str(parsed.get("density")).lower()),
        "motion_level": _normalize_motion(_coerce_str(parsed.get("motion_level")).lower()),
        "industry": _coerce_str(parsed.get("industry"), "general"),
        "vibe": _coerce_str(parsed.get("vibe"), "clean"),
        "keywords": _coerce_list_of_str(parsed.get("keywords")),
        "confidence": max(0.0, min(1.0, float(parsed.get("confidence", 0.0)))),
        "reason": _coerce_str(parsed.get("reason"), "LLM routing"),
    }


def build_render_variants(
    user_prompt: str,
    *,
    brief: BriefInput | dict[str, Any] | None = None,
    model: Any | None = None,
    overrides: dict[str, Any] | None = None,
    theme_catalog: dict[str, Any] | None = None,
    template_catalog: dict[str, dict[str, Any]] | None = None,
) -> list[RenderPlan]:
    if theme_catalog is None:
        theme_catalog = {"modern_editorial": {}}
    if template_catalog is None:
        template_catalog = {"landing": {"template_file": "generated/site_builder.html", "slot_schema": {}}}

    brief_input = brief if isinstance(brief, BriefInput) else normalize_brief(user_prompt, brief)
    prompt = _normalize_prompt(brief_input.to_prompt_text())
    tokens = _tokenize(prompt)
    token_set = _build_token_set(tokens)

    template_keys = list(template_catalog.keys())
    art_keys = list(theme_catalog.keys())

    template_scores, template_hits = _score_signal_groups(
        prompt,
        token_set,
        DEFAULT_TEMPLATE_SIGNALS,
        phrase_weight=2.8,
        strong_weight=1.7,
        support_weight=0.9,
    )
    art_scores, art_hits = _score_signal_groups(
        prompt,
        token_set,
        ART_DIRECTION_SIGNALS,
        phrase_weight=2.4,
        strong_weight=1.6,
        support_weight=0.8,
    )
    reasons = _apply_intent_boosts(
        token_set=token_set,
        template_scores=template_scores,
        template_hits=template_hits,
        art_scores=art_scores,
        art_hits=art_hits,
    )

    ranked_template_scores = {key: template_scores.get(key, 0.0) for key in template_keys}
    ranked_art_scores = {key: art_scores.get(key, 0.0) for key in art_keys}
    for key in template_keys:
        template_hits.setdefault(key, 0)

    (best_template, top_template_score), (_, second_template_score) = _top_two(ranked_template_scores)
    (best_art, _), _ = _top_two(ranked_art_scores)
    template_gap = max(0.0, top_template_score - second_template_score)
    confidence = _compute_rule_confidence(top_template_score, template_gap, template_hits.get(best_template, 0))

    density = brief_input.content_density or _infer_category(prompt, token_set, DENSITY_KEYWORDS, "balanced")
    motion_level = brief_input.motion_level or _infer_category(prompt, token_set, MOTION_KEYWORDS, "moderate")
    industry = _infer_category(prompt, token_set, INDUSTRY_KEYWORDS, "general")
    vibe = _infer_category(prompt, token_set, VIBE_KEYWORDS, "clean")
    keywords = _extract_keywords(prompt)
    reasons = [f"Rule routing picked '{best_template}' with layout diversity enabled."] + reasons

    layout_ranking = _rank_layouts(
        best_template,
        prompt=prompt,
        token_set=token_set,
        density=density,
        motion_level=motion_level,
        vibe=vibe,
    )
    best_layout = layout_ranking[0] if layout_ranking else _safe_default_key(set(LAYOUT_LIBRARY.get(best_template, {})), "split_hero")

    should_use_llm = model is not None and (template_gap <= 0.75 or top_template_score < 2.6)
    if should_use_llm:
        try:
            llm_result = _llm_override_profile(
                model,
                brief=brief_input,
                template_keys=template_keys,
                art_keys=art_keys,
                layout_keys=list(LAYOUT_LIBRARY.get(best_template, {}).keys()) or [best_layout],
            )
            if llm_result:
                best_template = _resolve_choice(llm_result["template_key"], allowed=set(template_keys), default=best_template)
                best_art = _resolve_choice(llm_result["art_direction"], allowed=set(art_keys), default=best_art)
                layout_choices = set(LAYOUT_LIBRARY.get(best_template, {}).keys())
                best_layout = _resolve_choice(llm_result["layout_mode"], allowed=layout_choices, default=best_layout)
                density = llm_result["density"] or density
                motion_level = llm_result["motion_level"] or motion_level
                industry = llm_result["industry"] or industry
                vibe = llm_result["vibe"] or vibe
                if llm_result["keywords"]:
                    keywords = llm_result["keywords"]
                confidence = max(confidence, llm_result["confidence"])
                reasons.append(f"LLM routing used: {llm_result['reason']}.")
        except Exception:
            reasons.append("LLM routing failed; kept rule routing.")

    if not keywords:
        keywords = [industry, vibe, best_template, best_art]

    if confidence < 0.55:
        best_template = _safe_default_key(set(template_keys), "landing")
        best_art = _safe_default_key(set(art_keys), "modern_editorial")
        density = "balanced"
        motion_level = "moderate"
        confidence = 0.55
        reasons.append("Confidence low; applied safe fallback profile.")

    if overrides:
        template_override = overrides.get("template_key")
        art_override = overrides.get("art_direction") or overrides.get("theme_key")
        layout_override = overrides.get("layout_mode")
        density_override = overrides.get("density")
        motion_override = overrides.get("motion_level")

        best_template = _resolve_choice(template_override, allowed=set(template_keys), default=best_template)
        best_art = _resolve_choice(art_override, allowed=set(art_keys), default=best_art)
        layout_choices = set(LAYOUT_LIBRARY.get(best_template, {}).keys())
        best_layout = _resolve_choice(layout_override, allowed=layout_choices, default=best_layout)
        density = _normalize_density(_coerce_str(density_override, density).lower())
        motion_level = _normalize_motion(_coerce_str(motion_override, motion_level).lower())

    layout_ranking = _rank_layouts(
        best_template,
        prompt=prompt,
        token_set=token_set,
        density=density,
        motion_level=motion_level,
        vibe=vibe,
    )
    if best_layout in layout_ranking:
        layout_ranking.remove(best_layout)
    layout_ranking.insert(0, best_layout)

    art_ranking = [key for key, _ in sorted(ranked_art_scores.items(), key=lambda item: item[1], reverse=True) if key in art_keys]
    if best_art in art_ranking:
        art_ranking.remove(best_art)
    art_ranking.insert(0, best_art)
    if not art_ranking:
        art_ranking = art_keys

    variants: list[RenderPlan] = []
    used_pairs: set[tuple[str, str, str, str, str]] = set()
    section_override = overrides.get("section_visibility") if isinstance(overrides, dict) else None

    candidate_specs = [
        (best_layout, best_art, density, motion_level, confidence, list(reasons)),
    ]

    alt_layouts = [item for item in layout_ranking if item != best_layout]
    alt_arts = [item for item in art_ranking if item != best_art]
    candidate_specs.append(
        (
            alt_layouts[0] if alt_layouts else best_layout,
            alt_arts[0] if alt_arts else best_art,
            density,
            motion_level,
            max(0.55, confidence - 0.05),
            [f"Variant explores alternate layout '{alt_layouts[0]}'." if alt_layouts else "Variant explores alternate art direction."],
        )
    )
    density_variant = "dense" if density == "balanced" else "airy"
    motion_variant = "energetic" if motion_level != "energetic" else "calm"
    candidate_specs.append(
        (
            alt_layouts[1] if len(alt_layouts) > 1 else (alt_layouts[0] if alt_layouts else best_layout),
            alt_arts[1] if len(alt_arts) > 1 else (alt_arts[0] if alt_arts else best_art),
            density_variant,
            motion_variant,
            max(0.55, confidence - 0.08),
            ["Variant pushes density/motion to widen design range."],
        )
    )

    for layout_mode, art_direction, variant_density, variant_motion, variant_confidence, variant_reasons in candidate_specs:
        identity = (best_template, layout_mode, art_direction, variant_density, variant_motion)
        if identity in used_pairs:
            continue
        used_pairs.add(identity)
        variants.append(
            _make_plan(
                template_key=best_template,
                art_direction=art_direction,
                layout_mode=layout_mode,
                density=variant_density,
                motion_level=variant_motion,
                industry=industry,
                vibe=vibe,
                keywords=keywords,
                confidence=variant_confidence,
                reasons=variant_reasons,
                template_catalog=template_catalog,
                section_visibility=section_override if isinstance(section_override, dict) else None,
            )
        )

    while len(variants) < 3:
        variants.append(
            _make_plan(
                template_key=best_template,
                art_direction=best_art,
                layout_mode=best_layout,
                density=density,
                motion_level=motion_level,
                industry=industry,
                vibe=vibe,
                keywords=keywords,
                confidence=confidence,
                reasons=reasons,
                template_catalog=template_catalog,
            )
        )

    return variants[:3]


def build_render_plan(
    user_prompt: str,
    *,
    brief: BriefInput | dict[str, Any] | None = None,
    model: Any | None = None,
    overrides: dict[str, Any] | None = None,
    theme_catalog: dict[str, Any] | None = None,
    template_catalog: dict[str, dict[str, Any]] | None = None,
) -> RenderPlan:
    return build_render_variants(
        user_prompt,
        brief=brief,
        model=model,
        overrides=overrides,
        theme_catalog=theme_catalog,
        template_catalog=template_catalog,
    )[0]


def remix_render_plan(
    plan: RenderPlan,
    *,
    overrides: dict[str, Any] | None = None,
    theme_catalog: dict[str, Any] | None = None,
    template_catalog: dict[str, dict[str, Any]] | None = None,
) -> RenderPlan:
    if theme_catalog is None:
        theme_catalog = {plan.art_direction: {}}
    if template_catalog is None:
        template_catalog = {plan.template_key: {"template_file": plan.template_file}}
    overrides = overrides or {}

    template_key = _resolve_choice(
        overrides.get("template_key"),
        allowed=set(template_catalog.keys()),
        default=plan.template_key,
    )
    art_direction = _resolve_choice(
        overrides.get("art_direction") or overrides.get("theme_key"),
        allowed=set(theme_catalog.keys()),
        default=plan.art_direction,
    )
    layout_choices = set(LAYOUT_LIBRARY.get(template_key, {}).keys())
    layout_mode = _resolve_choice(overrides.get("layout_mode"), allowed=layout_choices, default=plan.layout_mode)
    density = _normalize_density(_coerce_str(overrides.get("density"), plan.density).lower())
    motion_level = _normalize_motion(_coerce_str(overrides.get("motion_level"), plan.motion_level).lower())
    section_visibility = plan.section_visibility.copy()
    raw_visibility = overrides.get("section_visibility")
    if isinstance(raw_visibility, dict):
        for key, value in raw_visibility.items():
            if key in section_visibility:
                section_visibility[key] = bool(value)

    remixed = _make_plan(
        template_key=template_key,
        art_direction=art_direction,
        layout_mode=layout_mode,
        density=density,
        motion_level=motion_level,
        industry=plan.industry,
        vibe=plan.vibe,
        keywords=plan.keywords,
        confidence=max(plan.confidence, 0.7),
        reasons=plan.reasons + ["Studio override applied."],
        template_catalog=template_catalog,
        section_visibility=section_visibility,
    )
    return replace(remixed, keywords=plan.keywords[:8])
