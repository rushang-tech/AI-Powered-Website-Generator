from __future__ import annotations

import json
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
) -> VariantPayload:
    return VariantPayload(
        variant_id=variant_id or f"variant-{index}",
        label=_variant_label(index, render_plan),
        summary=_variant_summary(render_plan),
        render_plan=render_plan,
        content=content,
        theme=deepcopy(THEME_MAP.get(render_plan.art_direction, THEME_MAP["modern_editorial"])),
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
        seed_content=target_variant.content.data,
    )

    variants = list(manifest.variants)
    index = variants.index(target_variant)
    variants[index] = _variant_payload(
        index=index + 1,
        render_plan=remixed_plan,
        content=content,
        variant_id=selected_variant_id,
    )
    return ProjectManifest(
        preview_id=manifest.preview_id,
        prompt=manifest.prompt,
        brief=manifest.brief,
        selected_variant_id=selected_variant_id,
        variants=variants,
        statuses=manifest.statuses,
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
        return generate_project_manifest(
            manifest.prompt,
            brief=manifest.brief,
            preview_id=manifest.preview_id,
            provider=provider,
        )

    if not manifest.variants:
        return manifest

    target_variant_id = variant_id or manifest.selected_variant_id
    target_variant = next((item for item in manifest.variants if item.variant_id == target_variant_id), manifest.variants[0])
    fresh_content = _generate_content(
        provider=provider,
        brief=manifest.brief,
        render_plan=target_variant.render_plan,
        seed_content=target_variant.content.data,
    )
    next_content = fresh_content.data

    if scope == "section" and section_name:
        next_content = deepcopy(target_variant.content.data)
        if section_name in fresh_content.data:
            next_content[section_name] = fresh_content.data[section_name]
        fresh_content = GeneratedContent(data=next_content, validation=fresh_content.validation)

    variants = list(manifest.variants)
    index = variants.index(target_variant)
    variants[index] = _variant_payload(
        index=index + 1,
        render_plan=target_variant.render_plan,
        content=fresh_content,
        variant_id=target_variant.variant_id,
    )
    return ProjectManifest(
        preview_id=manifest.preview_id,
        prompt=manifest.prompt,
        brief=manifest.brief,
        selected_variant_id=target_variant.variant_id,
        variants=variants,
        statuses=manifest.statuses,
    )


def selected_preview_data(payload: dict[str, object] | ProjectManifest) -> dict[str, object]:
    manifest = payload if isinstance(payload, ProjectManifest) else ProjectManifest.from_dict(payload)
    selected = _selected_variant(manifest)
    return {
        "brief": manifest.brief.to_dict(),
        "selected_variant_id": manifest.selected_variant_id,
        "selected_variant": selected.to_dict() if selected else {},
        "variants": [variant.to_dict() for variant in manifest.variants],
        "statuses": [stage.to_dict() for stage in manifest.statuses],
    }
