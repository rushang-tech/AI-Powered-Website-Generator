from __future__ import annotations

import time
from collections import defaultdict
from functools import wraps
from threading import Lock
from typing import Any, Callable
from uuid import uuid4

from flask import Blueprint, abort, current_app, g, jsonify, make_response, render_template, request, send_file, url_for

from app.services.ai_provider import AIProviderUnavailableError, configured_api_key_count
from app.services.ai_engine import (
    TEMPLATE_CATALOG,
    THEME_MAP,
    apply_canvas_command_to_manifest,
    apply_variant_override_to_manifest,
    build_preview_variant,
    generate_project_manifest,
    regenerate_manifest,
    selected_preview_data,
    status_blueprint,
)
from app.services.contracts import ProjectManifest
from app.services.export_service import build_export_bundle, render_export_site
from app.services.manifest_service import MANIFEST_SERVICE
from app.services.published_site_service import PUBLISHED_SITE_SERVICE
from app.services.taste_engine import LAYOUT_LIBRARY, normalize_brief

main = Blueprint("main", __name__)

_ROUTE_METRICS: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "errors": 0})
_ROUTE_METRICS_LOCK = Lock()


def _public_ai_error_message(exc: AIProviderUnavailableError) -> str:
    message = str(exc).strip()
    lowered = message.lower()
    if any(token in lowered for token in ("resourceexhausted", "429", "quota", "rate-limited", "rate limit")):
        if configured_api_key_count() <= 1:
            return (
                "Gemini generation is temporarily unavailable because the only configured API key is out of quota. "
                "Add another Gemini key to enable rotation, or try again after the quota resets."
            )
        return (
            "Gemini generation is temporarily unavailable because all configured API keys are out of quota. "
            "Add another Gemini key or try again after the quota resets."
        )
    return message


def _service_unavailable_response(exc: AIProviderUnavailableError) -> tuple[dict[str, str], int]:
    current_app.logger.warning("ai.unavailable id=%s error=%s", getattr(g, "request_id", ""), exc)
    return {"error": _public_ai_error_message(exc)}, 503


def observe_route(route_key: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(view: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(view)
        def wrapped(*args: Any, **kwargs: Any):
            start = time.perf_counter()
            status_code = 500
            failed = False
            try:
                response = make_response(view(*args, **kwargs))
                status_code = int(response.status_code)
                failed = status_code >= 400
                return response
            except Exception:
                failed = True
                status_code = 500
                raise
            finally:
                elapsed_ms = (time.perf_counter() - start) * 1000
                with _ROUTE_METRICS_LOCK:
                    metric = _ROUTE_METRICS[route_key]
                    metric["total"] += 1
                    if failed:
                        metric["errors"] += 1
                    total = metric["total"]
                    errors = metric["errors"]
                error_rate = (errors / total) * 100 if total else 0.0
                current_app.logger.info(
                    "route.metric id=%s route=%s status=%s latency_ms=%.2f total=%s errors=%s error_rate_pct=%.2f",
                    getattr(g, "request_id", ""),
                    route_key,
                    status_code,
                    elapsed_ms,
                    total,
                    errors,
                    error_rate,
                )

        return wrapped

    return decorator


def _example_prompts() -> list[str]:
    return [
        "A luxury skincare product launch page with soft tone and premium feel",
        "A personal developer portfolio with clean case-study sections",
        "A playful landing page for a kids coding workshop",
    ]


def _demo_brief() -> dict[str, str]:
    return {
        "goal": "Launch a startup landing page for a B2B AI co-pilot product",
        "audience": "Seed-stage founders and product leads",
        "brand_tone": "Bold, clear, confident",
        "content_density": "balanced",
        "motion_level": "moderate",
        "name": "Northstar Copilot",
        "notes": "Lead with proof and include a strong pricing narrative.",
    }


def _collect_overrides(body: dict[str, object]) -> dict[str, object]:
    overrides: dict[str, object] = {}
    for key in ("template_key", "layout_mode", "art_direction", "theme_key", "density", "motion_level"):
        value = str(body.get(key, "")).strip().lower()
        if value:
            overrides[key] = value

    raw_visibility = body.get("section_visibility")
    if isinstance(raw_visibility, dict):
        overrides["section_visibility"] = {str(key): bool(value) for key, value in raw_visibility.items()}
    return overrides


def _brief_payload(body: dict[str, object]) -> dict[str, object]:
    brief = body.get("brief")
    if isinstance(brief, dict):
        return brief
    return {}


def _clean_text(value: object, *, max_length: int = 600) -> str:
    text = str(value).strip() if value is not None else ""
    text = " ".join(text.split())
    return text[:max_length]


def _clean_bool(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "on"}:
            return True
        if lowered in {"false", "0", "no", "off"}:
            return False
    return None


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
        "brand_assets": raw_brief.get("brand_assets") if isinstance(raw_brief.get("brand_assets"), list) else [],
        "icon_style": _clean_text(raw_brief.get("icon_style"), max_length=220),
    }
    return prompt, brief


@main.route("/", methods=["GET"])
def index():
    return render_template(
        "home.html",
        examples=_example_prompts(),
        demo_brief=_demo_brief(),
        status_blueprint=status_blueprint(),
        density_options=["airy", "balanced", "dense"],
        motion_options=["calm", "moderate", "energetic"],
    )


@main.route("/healthz", methods=["GET"])
def healthz():
    return jsonify({"ok": True, "service": "velosite-ai"}), 200


@main.route("/generate", methods=["POST"])
@observe_route("generate")
def generate():
    body = request.get_json(silent=True) or {}
    user_prompt, brief = _normalized_brief(body)
    has_brand_assets = bool(brief.get("brand_assets"))
    has_text_brief = any(str(value).strip() for key, value in brief.items() if key != "brand_assets")
    if not user_prompt and not has_text_brief and not has_brand_assets:
        return jsonify({"error": "Prompt or brief is required."}), 400

    try:
        manifest = generate_project_manifest(user_prompt, brief=brief)
    except AIProviderUnavailableError as exc:
        body, status_code = _service_unavailable_response(exc)
        return jsonify(body), status_code
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


@main.route("/preview/<preview_id>/branding", methods=["POST"])
def update_branding(preview_id: str):
    manifest = MANIFEST_SERVICE.get(preview_id)
    if not manifest:
        return jsonify({"error": "Preview not found."}), 404

    body = request.get_json(silent=True) or {}
    incoming = _brief_payload(body) if isinstance(body.get("brief"), dict) else body

    merged_brief = manifest.brief.to_dict()
    if "brand_assets" in incoming:
        merged_brief["brand_assets"] = incoming.get("brand_assets")
    if "icon_style" in incoming:
        merged_brief["icon_style"] = incoming.get("icon_style")

    normalized = normalize_brief(manifest.prompt, merged_brief)
    updated = ProjectManifest(
        preview_id=manifest.preview_id,
        prompt=manifest.prompt,
        brief=normalized,
        selected_variant_id=manifest.selected_variant_id,
        variants=manifest.variants,
        statuses=manifest.statuses,
    )
    MANIFEST_SERVICE.save(updated)
    selected = selected_preview_data(updated).get("selected_variant", {})

    return jsonify(
        {
            "ok": True,
            "preview_id": preview_id,
            "selected_variant_id": updated.selected_variant_id,
            "selected_variant": selected,
            "brief": updated.brief.to_dict(),
            "frame_url": url_for("main.preview_frame", preview_id=preview_id),
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

    variant_id = _clean_text(request.args.get("variant_id"), max_length=64) or None
    remix_label = _clean_text(request.args.get("remix_label"), max_length=80) or None
    overrides = _collect_overrides(request.args.to_dict(flat=True))

    if overrides or variant_id:
        selected_variant = build_preview_variant(
            manifest,
            variant_id=variant_id,
            overrides=overrides or None,
            remix_label=remix_label,
        )
    else:
        studio = selected_preview_data(manifest)
        selected_variant = studio.get("selected_variant", {})

    return render_template(
        "preview_frame.html",
        page_title=manifest.brief.name or "VeloSite Preview",
        brief=manifest.brief.to_dict(),
        selected_variant=selected_variant,
        studio_mode=request.args.get("studio", "").strip() == "1",
        consumer_mode=True,
    )


@main.route("/preview/<preview_id>/override", methods=["POST"])
def override_preview(preview_id: str):
    manifest = MANIFEST_SERVICE.get(preview_id)
    if not manifest:
        return jsonify({"error": "Preview not found."}), 404

    body = request.get_json(silent=True) or {}
    variant_id = str(body.get("variant_id", "")).strip() or None

    overrides = _collect_overrides(body)

    try:
        updated = apply_variant_override_to_manifest(
            manifest,
            variant_id=variant_id,
            overrides=overrides or None,
        )
    except AIProviderUnavailableError as exc:
        body, status_code = _service_unavailable_response(exc)
        return jsonify(body), status_code
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


@main.route("/preview/<preview_id>/command", methods=["POST"])
def canvas_command(preview_id: str):
    manifest = MANIFEST_SERVICE.get(preview_id)
    if not manifest:
        return jsonify({"error": "Preview not found."}), 404

    body = request.get_json(silent=True) or {}
    action = _clean_text(body.get("action"), max_length=64).lower()
    variant_id = _clean_text(body.get("variant_id"), max_length=64) or None
    node_id = _clean_text(body.get("node_id"), max_length=120) or None
    edit_path = _clean_text(body.get("edit_path"), max_length=160) or None
    section_name = _clean_text(body.get("section_name"), max_length=64) or None
    direction = _clean_text(body.get("direction"), max_length=12).lower()
    instruction = _clean_text(body.get("instruction"), max_length=220)
    value = body.get("value")

    if isinstance(value, str):
        value = _clean_text(value, max_length=600)
    elif isinstance(value, dict):
        value = {str(key): _clean_text(item, max_length=280) for key, item in value.items()}

    bool_value = _clean_bool(value)
    if action == "toggle_section" and bool_value is not None:
        value = bool_value

    try:
        updated, changed_paths = apply_canvas_command_to_manifest(
            manifest,
            action=action,
            variant_id=variant_id,
            node_id=node_id,
            edit_path=edit_path,
            section_name=section_name,
            value=value,
            instruction=instruction,
            direction=direction,
        )
    except AIProviderUnavailableError as exc:
        body, status_code = _service_unavailable_response(exc)
        return jsonify(body), status_code
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    MANIFEST_SERVICE.save(updated)
    selected = selected_preview_data(updated).get("selected_variant", {})
    return jsonify(
        {
            "ok": True,
            "preview_id": preview_id,
            "selected_variant_id": updated.selected_variant_id,
            "selected_variant": selected,
            "frame_url": url_for("main.preview_frame", preview_id=preview_id),
            "changed_paths": changed_paths,
        }
    )


@main.route("/preview/<preview_id>/regenerate", methods=["POST"])
@observe_route("regenerate")
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

    try:
        updated = regenerate_manifest(
            manifest,
            scope=scope,
            variant_id=variant_id,
            section_name=section_name,
        )
    except AIProviderUnavailableError as exc:
        body, status_code = _service_unavailable_response(exc)
        return jsonify(body), status_code
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


@main.route("/preview/<preview_id>/publish", methods=["POST"])
@observe_route("publish")
def publish_preview(preview_id: str):
    manifest = MANIFEST_SERVICE.get(preview_id)
    if not manifest:
        return jsonify({"error": "Preview not found."}), 404

    body = request.get_json(silent=True) or {}
    variant_id = _clean_text(body.get("variant_id"), max_length=64) or manifest.selected_variant_id
    publish_id = uuid4().hex[:12]
    css_href = url_for("main.published_site_css", publish_id=publish_id)
    rendered_html, css_text, selected_variant = render_export_site(
        manifest,
        variant_id=variant_id,
        css_href=css_href,
    )
    PUBLISHED_SITE_SERVICE.save(
        publish_id,
        {
            "preview_id": preview_id,
            "variant_id": selected_variant.get("variant_id"),
            "page_title": manifest.brief.name or "VeloSite Export",
            "html": rendered_html,
            "css": css_text,
        },
    )
    public_path = url_for("main.published_site", publish_id=publish_id)
    return jsonify(
        {
            "ok": True,
            "publish_id": publish_id,
            "public_path": public_path,
            "public_url": url_for("main.published_site", publish_id=publish_id, _external=True),
            "expires_in_seconds": PUBLISHED_SITE_SERVICE.ttl_seconds,
        }
    )


@main.route("/published/<publish_id>", methods=["GET"])
def published_site(publish_id: str):
    payload = PUBLISHED_SITE_SERVICE.get(_clean_text(publish_id, max_length=80))
    if not payload:
        abort(404)

    html = payload.get("html")
    if not isinstance(html, str) or not html.strip():
        abort(404)

    response = make_response(html)
    response.headers["Content-Type"] = "text/html; charset=utf-8"
    response.headers["Cache-Control"] = "public, max-age=120"
    return response


@main.route("/published/<publish_id>/assets/export-frame.css", methods=["GET"])
def published_site_css(publish_id: str):
    payload = PUBLISHED_SITE_SERVICE.get(_clean_text(publish_id, max_length=80))
    if not payload:
        abort(404)

    css = payload.get("css")
    if not isinstance(css, str) or not css.strip():
        abort(404)

    response = make_response(css)
    response.headers["Content-Type"] = "text/css; charset=utf-8"
    response.headers["Cache-Control"] = "public, max-age=120"
    return response


@main.route("/preview/<preview_id>/export", methods=["POST"])
@observe_route("export")
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
