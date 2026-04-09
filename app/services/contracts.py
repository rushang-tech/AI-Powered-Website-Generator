from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from app.services.taste_engine import BriefInput, RenderPlan, normalize_brief


@dataclass(frozen=True)
class GenerationStage:
    key: str
    label: str
    state: str
    detail: str = ""

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    fallback_used: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GeneratedContent:
    data: dict[str, Any]
    validation: ValidationResult

    def to_dict(self) -> dict[str, Any]:
        return {
            "data": self.data,
            "validation": self.validation.to_dict(),
        }


@dataclass(frozen=True)
class VariantPayload:
    variant_id: str
    label: str
    summary: str
    render_plan: RenderPlan
    content: GeneratedContent
    theme: dict[str, Any]
    content_overrides: dict[str, Any] = field(default_factory=dict)
    layout_overrides: dict[str, Any] = field(default_factory=dict)
    edited_nodes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "variant_id": self.variant_id,
            "label": self.label,
            "summary": self.summary,
            "render_plan": self.render_plan.to_dict(),
            "content": self.content.data,
            "validation": self.content.validation.to_dict(),
            "theme": self.theme,
            "content_overrides": self.content_overrides,
            "layout_overrides": self.layout_overrides,
            "edited_nodes": self.edited_nodes,
        }


@dataclass(frozen=True)
class ProjectManifest:
    preview_id: str
    prompt: str
    brief: BriefInput
    selected_variant_id: str
    variants: list[VariantPayload]
    statuses: list[GenerationStage] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "preview_id": self.preview_id,
            "prompt": self.prompt,
            "brief": self.brief.to_dict(),
            "selected_variant_id": self.selected_variant_id,
            "variants": [variant.to_dict() for variant in self.variants],
            "statuses": [stage.to_dict() for stage in self.statuses],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ProjectManifest":
        brief_payload = payload.get("brief") if isinstance(payload.get("brief"), dict) else {}
        brief = normalize_brief(str(payload.get("prompt", "")).strip(), brief_payload)
        variants: list[VariantPayload] = []
        for raw_variant in payload.get("variants", []):
            if not isinstance(raw_variant, dict):
                continue
            validation_payload = raw_variant.get("validation") if isinstance(raw_variant.get("validation"), dict) else {}
            validation = ValidationResult(
                valid=bool(validation_payload.get("valid", True)),
                errors=[str(item) for item in validation_payload.get("errors", []) if isinstance(item, str)],
                warnings=[str(item) for item in validation_payload.get("warnings", []) if isinstance(item, str)],
                fallback_used=bool(validation_payload.get("fallback_used", False)),
            )
            render_plan_payload = raw_variant.get("render_plan") if isinstance(raw_variant.get("render_plan"), dict) else {}
            render_plan_payload = {
                **render_plan_payload,
                "palette_mood": str(render_plan_payload.get("palette_mood", "")).strip(),
                "typography_vibe": str(render_plan_payload.get("typography_vibe", "")).strip(),
            }
            variants.append(
                VariantPayload(
                    variant_id=str(raw_variant.get("variant_id", "")).strip() or "variant-1",
                    label=str(raw_variant.get("label", "")).strip() or "Variant",
                    summary=str(raw_variant.get("summary", "")).strip(),
                    render_plan=RenderPlan(**render_plan_payload),
                    content=GeneratedContent(
                        data=raw_variant.get("content") if isinstance(raw_variant.get("content"), dict) else {},
                        validation=validation,
                    ),
                    theme=raw_variant.get("theme") if isinstance(raw_variant.get("theme"), dict) else {},
                    content_overrides=raw_variant.get("content_overrides")
                    if isinstance(raw_variant.get("content_overrides"), dict)
                    else {},
                    layout_overrides=raw_variant.get("layout_overrides")
                    if isinstance(raw_variant.get("layout_overrides"), dict)
                    else {},
                    edited_nodes=[
                        str(item)
                        for item in raw_variant.get("edited_nodes", [])
                        if isinstance(item, str) and item.strip()
                    ],
                )
            )

        statuses: list[GenerationStage] = []
        for raw_stage in payload.get("statuses", []):
            if not isinstance(raw_stage, dict):
                continue
            statuses.append(
                GenerationStage(
                    key=str(raw_stage.get("key", "")).strip() or "unknown",
                    label=str(raw_stage.get("label", "")).strip() or "Unknown",
                    state=str(raw_stage.get("state", "")).strip() or "pending",
                    detail=str(raw_stage.get("detail", "")).strip(),
                )
            )

        return cls(
            preview_id=str(payload.get("preview_id", "")).strip(),
            prompt=str(payload.get("prompt", "")).strip(),
            brief=brief,
            selected_variant_id=str(payload.get("selected_variant_id", "")).strip(),
            variants=variants,
            statuses=statuses,
        )
