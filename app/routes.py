from __future__ import annotations

from flask import Blueprint, abort, jsonify, render_template, request, send_file, url_for

from app.services.ai_engine import (
    TEMPLATE_CATALOG,
    THEME_MAP,
    apply_variant_override_to_manifest,
    generate_project_manifest,
    regenerate_manifest,
    selected_preview_data,
)
from app.services.export_service import build_export_bundle
from app.services.manifest_service import MANIFEST_SERVICE
from app.services.taste_engine import LAYOUT_LIBRARY

main = Blueprint("main", __name__)


def _example_prompts() -> list[str]:
    return [
        "A luxury skincare product launch page with soft tone and premium feel",
        "A personal developer portfolio with clean case-study sections",
        "A playful landing page for a kids coding workshop",
    ]


def _brief_payload(body: dict[str, object]) -> dict[str, object]:
    brief = body.get("brief")
    if isinstance(brief, dict):
        return brief
    return {}


def _clean_text(value: object, *, max_length: int = 600) -> str:
    text = str(value).strip() if value is not None else ""
    text = " ".join(text.split())
    return text[:max_length]


def _normalized_brief(body: dict[str, object]) -> tuple[str, dict[str, object]]:
    prompt = _clean_text(body.get("prompt"), max_length=800)
    raw_brief = _brief_payload(body)
    brief = {
        "goal": _clean_text(raw_brief.get("goal"), max_length=300),
        "audience": _clean_text(raw_brief.get("audience"), max_length=160),
        "brand_tone": _clean_text(raw_brief.get("brand_tone"), max_length=160),
        "content_density": _clean_text(raw_brief.get("content_density"), max_length=24).lower(),
        "motion_level": _clean_text(raw_brief.get("motion_level"), max_length=24).lower(),
        "name": _clean_text(raw_brief.get("name"), max_length=120),
        "notes": _clean_text(raw_brief.get("notes"), max_length=600),
    }
    return prompt, brief


@main.route("/", methods=["GET"])
def index():
    return render_template(
        "home.html",
        examples=_example_prompts(),
        density_options=["airy", "balanced", "dense"],
        motion_options=["calm", "moderate", "energetic"],
    )


@main.route("/generate", methods=["POST"])
def generate():
    body = request.get_json(silent=True) or {}
    user_prompt, brief = _normalized_brief(body)
    if not user_prompt and not any(str(value).strip() for value in brief.values()):
        return jsonify({"error": "Prompt or brief is required."}), 400

    manifest = generate_project_manifest(user_prompt, brief=brief)
    preview_id = manifest.preview_id
    if not preview_id:
        return jsonify({"error": "Failed to generate preview ID."}), 500

    MANIFEST_SERVICE.save(manifest)
    preview_url = url_for("main.preview", preview_id=preview_id)
    return jsonify(
        {
            "preview_id": preview_id,
            "preview_url": preview_url,
            "frame_url": url_for("main.preview_frame", preview_id=preview_id),
            "selected_variant_id": manifest.selected_variant_id,
            "variants": [
                {
                    "variant_id": item.variant_id,
                    "label": item.label,
                    "summary": item.summary,
                    "render_plan": item.render_plan.to_dict(),
                }
                for item in manifest.variants
            ],
            "statuses": [stage.to_dict() for stage in manifest.statuses],
        }
    )


@main.route("/preview/<preview_id>", methods=["GET"])
def preview(preview_id: str):
    manifest = MANIFEST_SERVICE.get(preview_id)
    if not manifest:
        abort(404)

    studio = selected_preview_data(manifest)
    selected_variant = studio.get("selected_variant") or {}
    render_plan = selected_variant.get("render_plan", {})
    current_template = str(render_plan.get("template_key", "landing"))

    return render_template(
        "preview_shell.html",
        preview_id=preview_id,
        prompt=manifest.prompt,
        brief=studio.get("brief", {}),
        selected_variant=selected_variant,
        selected_variant_id=studio.get("selected_variant_id", ""),
        variants=studio.get("variants", []),
        statuses=studio.get("statuses", []),
        frame_url=url_for("main.preview_frame", preview_id=preview_id),
        template_keys=list(TEMPLATE_CATALOG.keys()),
        art_direction_keys=list(THEME_MAP.keys()),
        layout_modes=list(LAYOUT_LIBRARY.get(current_template, {}).keys()),
        layout_library={key: list(value.keys()) for key, value in LAYOUT_LIBRARY.items()},
        density_options=["airy", "balanced", "dense"],
        motion_options=["calm", "moderate", "energetic"],
    )


@main.route("/preview/<preview_id>/frame", methods=["GET"])
def preview_frame(preview_id: str):
    manifest = MANIFEST_SERVICE.get(preview_id)
    if not manifest:
        abort(404)

    studio = selected_preview_data(manifest)
    return render_template(
        "preview_frame.html",
        page_title=manifest.brief.name or "VeloSite Preview",
        brief=studio.get("brief", {}),
        selected_variant=studio.get("selected_variant", {}),
    )


@main.route("/preview/<preview_id>/override", methods=["POST"])
def override_preview(preview_id: str):
    manifest = MANIFEST_SERVICE.get(preview_id)
    if not manifest:
        return jsonify({"error": "Preview not found."}), 404

    body = request.get_json(silent=True) or {}
    variant_id = str(body.get("variant_id", "")).strip() or None

    overrides: dict[str, object] = {}
    for key in ("template_key", "layout_mode", "art_direction", "theme_key", "density", "motion_level"):
        value = str(body.get(key, "")).strip().lower()
        if value:
            overrides[key] = value

    raw_visibility = body.get("section_visibility")
    if isinstance(raw_visibility, dict):
        overrides["section_visibility"] = {str(key): bool(value) for key, value in raw_visibility.items()}

    updated = apply_variant_override_to_manifest(
        manifest,
        variant_id=variant_id,
        overrides=overrides or None,
    )
    MANIFEST_SERVICE.save(updated)
    selected = selected_preview_data(updated).get("selected_variant", {})

    return jsonify(
        {
            "ok": True,
            "preview_id": preview_id,
            "preview_url": url_for("main.preview", preview_id=preview_id),
            "frame_url": url_for("main.preview_frame", preview_id=preview_id),
            "selected_variant_id": updated.selected_variant_id,
            "render_plan": selected.get("render_plan", {}),
        }
    )


@main.route("/preview/<preview_id>/regenerate", methods=["POST"])
def regenerate_preview(preview_id: str):
    manifest = MANIFEST_SERVICE.get(preview_id)
    if not manifest:
        return jsonify({"error": "Preview not found."}), 404

    body = request.get_json(silent=True) or {}
    scope = _clean_text(body.get("scope"), max_length=32).lower() or "all"
    variant_id = _clean_text(body.get("variant_id"), max_length=64) or None
    section_name = _clean_text(body.get("section_name"), max_length=64) or None
    if scope not in {"all", "copy", "section"}:
        return jsonify({"error": "Invalid regenerate scope."}), 400
    if scope == "section" and not section_name:
        return jsonify({"error": "Section name is required for section regeneration."}), 400

    updated = regenerate_manifest(
        manifest,
        scope=scope,
        variant_id=variant_id,
        section_name=section_name,
    )
    MANIFEST_SERVICE.save(updated)
    selected = selected_preview_data(updated).get("selected_variant", {})
    return jsonify(
        {
            "ok": True,
            "preview_id": preview_id,
            "preview_url": url_for("main.preview", preview_id=preview_id),
            "frame_url": url_for("main.preview_frame", preview_id=preview_id),
            "selected_variant_id": updated.selected_variant_id,
            "selected_variant": selected,
        }
    )


@main.route("/preview/<preview_id>/export", methods=["POST"])
def export_preview(preview_id: str):
    manifest = MANIFEST_SERVICE.get(preview_id)
    if not manifest:
        return jsonify({"error": "Preview not found."}), 404

    archive, filename = build_export_bundle(manifest)
    return send_file(
        archive,
        mimetype="application/zip",
        as_attachment=True,
        download_name=filename,
    )
