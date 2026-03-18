from __future__ import annotations

import json
from dataclasses import replace
from copy import deepcopy
from types import SimpleNamespace
from uuid import uuid4

from app.services.ai_provider import AIProvider, get_default_provider
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
    build_render_variants,
    normalize_brief,
    remix_render_plan,
)

THEME_MAP: dict[str, dict[str, str]] = {
    "modern_editorial": {
        "key": "modern_editorial",
        "name": "Modern Editorial",
        "canvas_background": "linear-gradient(180deg, #f7f4ee 0%, #f1ede4 100%)",
        "panel_background": "rgba(255, 252, 247, 0.88)",
        "surface": "#fffaf2",
        "surface_alt": "#f2ece1",
        "text": "#191816",
        "muted": "#645e56",
        "accent": "#a16e36",
        "accent_soft": "rgba(161, 110, 54, 0.12)",
        "border": "rgba(25, 24, 22, 0.12)",
        "button_bg": "#191816",
        "button_text": "#fdf9f2",
        "shadow": "0 22px 60px rgba(44, 36, 23, 0.12)",
        "display_font": "'Cormorant Garamond', serif",
        "body_font": "'Space Grotesk', sans-serif",
    },
    "luxury_serif": {
        "key": "luxury_serif",
        "name": "Luxury Serif",
        "canvas_background": "radial-gradient(circle at top, rgba(186, 151, 98, 0.22), transparent 40%), linear-gradient(180deg, #f5eee5 0%, #efe2d2 100%)",
        "panel_background": "rgba(253, 247, 240, 0.9)",
        "surface": "#fdf5eb",
        "surface_alt": "#f2e5d4",
        "text": "#33261a",
        "muted": "#735b47",
        "accent": "#9c7448",
        "accent_soft": "rgba(156, 116, 72, 0.12)",
        "border": "rgba(51, 38, 26, 0.12)",
        "button_bg": "#33261a",
        "button_text": "#f8f0e4",
        "shadow": "0 26px 60px rgba(60, 40, 17, 0.15)",
        "display_font": "'Cormorant Garamond', serif",
        "body_font": "'Manrope', sans-serif",
    },
    "playful_blocks": {
        "key": "playful_blocks",
        "name": "Playful Blocks",
        "canvas_background": "linear-gradient(135deg, #fff8dc 0%, #fde8c8 35%, #fff2f7 100%)",
        "panel_background": "rgba(255, 252, 244, 0.9)",
        "surface": "#fffef8",
        "surface_alt": "#fff1cf",
        "text": "#1f2f49",
        "muted": "#48658c",
        "accent": "#ff9f1c",
        "accent_soft": "rgba(255, 159, 28, 0.18)",
        "border": "rgba(31, 47, 73, 0.16)",
        "button_bg": "#1f2f49",
        "button_text": "#fff7dd",
        "shadow": "8px 8px 0 rgba(31, 47, 73, 0.18)",
        "display_font": "'Bricolage Grotesque', sans-serif",
        "body_font": "'Manrope', sans-serif",
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
    },
    "brutalist_poster": {
        "key": "brutalist_poster",
        "name": "Brutalist Poster",
        "canvas_background": "linear-gradient(135deg, #f4f1ea 0%, #e5e1d9 100%)",
        "panel_background": "rgba(247, 243, 234, 0.92)",
        "surface": "#f6f2ea",
        "surface_alt": "#e8dfd0",
        "text": "#121212",
        "muted": "#565656",
        "accent": "#e04b21",
        "accent_soft": "rgba(224, 75, 33, 0.12)",
        "border": "rgba(18, 18, 18, 0.18)",
        "button_bg": "#121212",
        "button_text": "#f9f4ec",
        "shadow": "10px 10px 0 rgba(18, 18, 18, 0.16)",
        "display_font": "'Bricolage Grotesque', sans-serif",
        "body_font": "'Space Grotesk', sans-serif",
    },
    "warm_gradient": {
        "key": "warm_gradient",
        "name": "Warm Gradient",
        "canvas_background": "radial-gradient(circle at top left, rgba(255, 204, 120, 0.28), transparent 30%), linear-gradient(180deg, #fff4e7 0%, #ffe2db 50%, #ffeef2 100%)",
        "panel_background": "rgba(255, 248, 241, 0.9)",
        "surface": "#fff8f1",
        "surface_alt": "#ffe8de",
        "text": "#2c1e1f",
        "muted": "#715154",
        "accent": "#ee7d57",
        "accent_soft": "rgba(238, 125, 87, 0.13)",
        "border": "rgba(44, 30, 31, 0.12)",
        "button_bg": "#2c1e1f",
        "button_text": "#fff5ef",
        "shadow": "0 24px 68px rgba(126, 70, 45, 0.16)",
        "display_font": "'Fraunces', serif",
        "body_font": "'Manrope', sans-serif",
    },
}

TEMPLATE_CATALOG: dict[str, dict[str, str]] = {
    "landing": {"template_file": "generated/site_builder.html"},
    "portfolio": {"template_file": "generated/site_builder.html"},
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
    "metrics": (
        "stat_1_value",
        "stat_1_label",
        "stat_2_value",
        "stat_2_label",
        "stat_3_value",
        "stat_3_label",
    ),
    "features": ("features",),
    "projects": ("projects",),
    "pricing": ("offers",),
    "proof": ("proof_quote", "proof_author"),
    "cta": ("cta_text", "cta_note"),
    "about": ("about_text",),
    "capabilities": ("capabilities",),
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


def _slot_fallback(slot_name: str, *, render_plan: RenderPlan, brief: BriefInput) -> str:
    name = brief.name or "your brand"
    industry = render_plan.industry.title()
    audience = (brief.audience or "general audiences").strip().lower()
    tone = (brief.brand_tone or render_plan.art_direction.replace("_", " ")).strip().lower()
    defaults = {
        "hero_eyebrow": brief.brand_tone or render_plan.art_direction.replace("_", " ").title(),
        "hero_title": f"{name.title()} for {industry}" if brief.name else f"Move faster in {industry}",
        "hero_subtitle": f"Built for {audience} with a {tone} voice.".strip(),
        "cta_text": "Start Now",
        "cta_note": "Generated as a studio-ready concept with editable sections.",
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
    return defaults.get(slot_name, slot_name.replace("_", " ").title())


def _default_list_items(list_name: str, *, render_plan: RenderPlan) -> list[dict[str, str]]:
    industry = render_plan.industry.title()
    defaults = {
        "features": [
            {"title": "Clear narrative", "desc": f"Frame {industry.lower()} value in a sharper story."},
            {"title": "Adaptive sections", "desc": "Swap structure without rebuilding the whole page."},
            {"title": "Studio controls", "desc": "Tune layout, motion, density, and section visibility quickly."},
        ],
        "offers": [
            {"title": "Starter", "desc": "Essential structure for a fast launch.", "meta": "$29"},
            {"title": "Growth", "desc": "More sections, richer proof, stronger conversion framing.", "meta": "$79"},
            {"title": "Studio", "desc": "Full design-system range with layered storytelling.", "meta": "$149"},
        ],
        "projects": [
            {"title": "Identity Refresh", "desc": "A system-level redesign focused on clarity and confidence.", "meta": "Brand system"},
            {"title": "Launch Experience", "desc": "A narrative-heavy site designed to win attention quickly.", "meta": "Web launch"},
            {"title": "Conversion Narrative", "desc": "Messaging, structure, and proof aligned into one funnel.", "meta": "Growth design"},
        ],
        "capabilities": [
            {"title": "Strategy", "desc": "Translate positioning into structure and language."},
            {"title": "Systems", "desc": "Build reusable patterns instead of one-off screens."},
            {"title": "Execution", "desc": "Ship polished work with practical constraints in mind."},
        ],
    }
    return defaults.get(list_name, [{"title": "Value", "desc": "Practical results for the audience."}])


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
- project name: {brief.name or "Not provided"}
- audience: {brief.audience}
- tone: {brief.brand_tone}
- request: {brief.to_prompt_text()}

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
) -> GeneratedContent:
    if provider is None:
        return _validate_content(seed_content or {}, brief=brief, render_plan=render_plan)

    prompt = _build_content_prompt(
        brief=brief,
        render_plan=render_plan,
        theme_name=THEME_MAP[render_plan.art_direction]["name"],
    )
    try:
        parsed = provider.generate_json(prompt)
    except Exception:
        parsed = seed_content or {}
    return _validate_content(parsed, brief=brief, render_plan=render_plan)


def _variant_label(index: int, render_plan: RenderPlan) -> str:
    layout_name = render_plan.layout_mode.replace("_", " ").title()
    return f"Variant {index}: {layout_name}"


def _variant_summary(render_plan: RenderPlan) -> str:
    return (
        f"{render_plan.art_direction.replace('_', ' ').title()} with "
        f"{render_plan.layout_mode.replace('_', ' ')} structure, "
        f"{render_plan.density} density, and {render_plan.motion_level} motion."
    )


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
        theme=deepcopy(THEME_MAP.get(render_plan.art_direction, THEME_MAP["modern_editorial"])),
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
- instruction: {safe_instruction}

Return only the rewritten copy.
Current copy:
{current_value}
""".strip()
    try:
        rewritten = provider.generate_text(prompt).strip()
    except Exception:
        rewritten = ""
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

Current section JSON:
{schema_blob}
""".strip()
    try:
        raw = provider.generate_json(prompt)
    except Exception:
        raw = {}

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
        content = _generate_content(provider=provider, brief=brief_input, render_plan=plan)
        variants.append(_variant_payload(index=index, render_plan=plan, content=content))

    return ProjectManifest(
        preview_id=preview_id,
        prompt=user_prompt,
        brief=brief_input,
        selected_variant_id=variants[0].variant_id if variants else "",
        variants=variants,
        statuses=_default_statuses(),
    )


def generate_website_content(
    user_prompt: str,
    *,
    brief: dict[str, object] | BriefInput | None = None,
    overrides: dict[str, object] | None = None,
) -> dict[str, object]:
    return generate_project_manifest(user_prompt, brief=brief, overrides=overrides).to_dict()


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
    fresh_content = _generate_content(
        provider=provider,
        brief=manifest.brief,
        render_plan=_resolved_render_plan(target_variant),
        seed_content=resolved_content,
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
    provider = provider if provider is not None else get_default_provider()

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
