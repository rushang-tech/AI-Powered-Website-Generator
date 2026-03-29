from __future__ import annotations

import time
from collections import defaultdict
from datetime import UTC, datetime
from functools import wraps
from threading import Lock
from typing import Any, Callable
from uuid import uuid4

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    g,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    session,
    send_file,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models import User, UserOnboarding
from app.services.ai_provider import AIProviderUnavailableError, configured_api_key_count
from app.services.ai_engine import (
    TEMPLATE_CATALOG,
    THEME_MAP,
    apply_canvas_command_to_manifest,
    apply_variant_override_to_manifest,
    build_preview_variant,
    continue_project_manifest,
    generate_project_manifest,
    regenerate_manifest,
    selected_preview_data,
    status_blueprint,
)
from app.services.contracts import ProjectManifest
from app.services.conversation_service import (
    append_message,
    create_conversation,
    delete_conversation,
    get_conversation_by_preview,
    get_conversation_for_user,
    history_messages,
    list_recent_conversations,
    manifest_from_conversation,
    record_system_event,
    rename_conversation,
    save_manifest,
    serialize_conversation_summary,
    visible_messages,
)
from app.services.export_service import build_export_bundle, render_export_site
from app.services.published_site_service import PUBLISHED_SITE_SERVICE
from app.services.taste_engine import LAYOUT_LIBRARY, normalize_brief

main = Blueprint("main", __name__)

_ROUTE_METRICS: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "errors": 0})
_ROUTE_METRICS_LOCK = Lock()
_MARKETING_NAV_ITEMS: tuple[dict[str, str], ...] = (
    {"slug": "home", "label": "Home", "endpoint": "main.marketing_home"},
    {"slug": "product", "label": "Product", "endpoint": "main.product"},
    {"slug": "showcase", "label": "Showcase", "endpoint": "main.showcase"},
    {"slug": "pricing", "label": "Pricing", "endpoint": "main.pricing"},
)
_DENSITY_CHOICES: tuple[str, ...] = ("airy", "balanced", "dense")
_MOTION_CHOICES: tuple[str, ...] = ("calm", "moderate", "energetic")
_DENSITY_OPTION_CARDS: tuple[dict[str, str], ...] = (
    {
        "value": "airy",
        "label": "Airy",
        "icon": "○",
        "description": "More whitespace with room to breathe.",
    },
    {
        "value": "balanced",
        "label": "Balanced",
        "icon": "◎",
        "description": "A middle ground for most pages.",
    },
    {
        "value": "dense",
        "label": "Dense",
        "icon": "●",
        "description": "Fits more information above the fold.",
    },
)
_MOTION_OPTION_CARDS: tuple[dict[str, str], ...] = (
    {
        "value": "calm",
        "label": "Calm",
        "icon": "☾",
        "description": "Subtle transitions with minimal movement.",
    },
    {
        "value": "moderate",
        "label": "Moderate",
        "icon": "◒",
        "description": "Light motion to guide attention.",
    },
    {
        "value": "energetic",
        "label": "Energetic",
        "icon": "⚡",
        "description": "Bolder motion for high visual impact.",
    },
)
_USER_TYPE_OPTION_CARDS: tuple[dict[str, str], ...] = (
    {"value": "student", "label": "Student", "icon": "student", "description": "Learning and building projects."},
    {"value": "office", "label": "Office", "icon": "office", "description": "Working inside an organization."},
    {"value": "founder", "label": "Founder", "icon": "founder", "description": "Launching or growing a business."},
    {"value": "freelancer", "label": "Freelancer", "icon": "freelancer", "description": "Shipping work for multiple clients."},
    {"value": "agency", "label": "Agency", "icon": "agency", "description": "Building sites as a team service."},
    {"value": "other", "label": "Other", "icon": "other", "description": "Something else that fits you best."},
)
_DISCOVERY_SOURCE_OPTION_CARDS: tuple[dict[str, str], ...] = (
    {"value": "search", "label": "Search", "icon": "search", "description": "Found us from web search."},
    {"value": "social", "label": "Social", "icon": "social", "description": "Saw us on social media."},
    {"value": "youtube", "label": "YouTube", "icon": "youtube", "description": "Discovered us from a video."},
    {"value": "friend", "label": "Friend", "icon": "friend", "description": "Referred by someone you know."},
    {"value": "community", "label": "Community", "icon": "community", "description": "Found us in a group or forum."},
    {"value": "other", "label": "Other", "icon": "other", "description": "Another source not listed here."},
)
_USER_TYPE_VALUES = {item["value"] for item in _USER_TYPE_OPTION_CARDS}
_DISCOVERY_SOURCE_VALUES = {item["value"] for item in _DISCOVERY_SOURCE_OPTION_CARDS}
_ONBOARDING_HTML_ENDPOINTS = {
    "main.index",
    "main.dashboard",
    "main.settings",
    "main.preview",
    "main.preview_studio",
    "main.preview_frame",
}
_ONBOARDING_API_ENDPOINTS = {
    "main.conversations",
    "main.rename_user_conversation",
    "main.delete_user_conversation",
    "main.continue_conversation",
    "main.generate",
    "main.update_branding",
    "main.override_preview",
    "main.canvas_command",
    "main.regenerate_preview",
    "main.publish_preview",
    "main.export_preview",
}
_ONBOARDING_PROTECTED_ENDPOINTS = _ONBOARDING_HTML_ENDPOINTS | _ONBOARDING_API_ENDPOINTS
_ONBOARDING_TOTAL_STEPS = 3
_ONBOARDING_DRAFT_SESSION_KEY = "onboarding_draft"
_ONBOARDING_NEXT_SESSION_KEY = "onboarding_next"


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


def _marketing_nav(active_slug: str) -> list[dict[str, str | bool]]:
    return [{**item, "is_active": item["slug"] == active_slug} for item in _MARKETING_NAV_ITEMS]


def _marketing_ctas() -> dict[str, dict[str, str]]:
    if getattr(current_user, "is_authenticated", False):
        return {
            "primary": {"label": "Open App", "href": url_for("main.index")},
            "secondary": {"label": "Settings", "href": url_for("main.settings")},
        }
    return {
        "primary": {"label": "Open App", "href": url_for("main.login")},
        "secondary": {"label": "Sign Up", "href": url_for("main.signup")},
    }


def _render_marketing_page(template_name: str, *, page_title: str, active_slug: str):
    return render_template(
        template_name,
        page_title=page_title,
        marketing_nav=_marketing_nav(active_slug),
        marketing_ctas=_marketing_ctas(),
    )


@main.app_context_processor
def inject_public_nav_defaults() -> dict[str, object]:
    return {
        "marketing_nav": _marketing_nav(""),
        "marketing_ctas": _marketing_ctas(),
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


def _safe_next_url(raw_value: object, *, fallback_endpoint: str = "main.index") -> str:
    value = str(raw_value or "").strip()
    if value.startswith("/") and not value.startswith("//"):
        return value
    return url_for(fallback_endpoint)


def _safe_next_or_none(raw_value: object) -> str | None:
    value = str(raw_value or "").strip()
    if value.startswith("/") and not value.startswith("//"):
        return value
    return None


def _normalize_density_choice(value: object, *, default: str = "balanced") -> str:
    candidate = _clean_text(value, max_length=24).lower()
    if candidate in _DENSITY_CHOICES:
        return candidate
    return default


def _normalize_motion_choice(value: object, *, default: str = "moderate") -> str:
    candidate = _clean_text(value, max_length=24).lower()
    if candidate in _MOTION_CHOICES:
        return candidate
    return default


def _requires_onboarding(user: User) -> bool:
    onboarding = getattr(user, "onboarding", None)
    if onboarding is None:
        return False
    return onboarding.completed_at is None


def _onboarding_redirect_url(raw_next: object) -> str:
    safe_next = _safe_next_or_none(raw_next)
    if safe_next:
        return url_for("main.onboarding", next=safe_next)
    return url_for("main.onboarding")


def _post_auth_destination(user: User, raw_next: object) -> str:
    safe_next = _safe_next_or_none(raw_next)
    if _requires_onboarding(user):
        return _onboarding_redirect_url(safe_next)
    return safe_next or url_for("main.index")


def _onboarding_draft() -> dict[str, str]:
    payload = session.get(_ONBOARDING_DRAFT_SESSION_KEY)
    if not isinstance(payload, dict):
        return {}
    return {str(key): str(value) for key, value in payload.items()}


def _save_onboarding_draft(draft: dict[str, str]) -> None:
    session[_ONBOARDING_DRAFT_SESSION_KEY] = dict(draft)
    session.modified = True


def _clear_onboarding_draft() -> None:
    session.pop(_ONBOARDING_DRAFT_SESSION_KEY, None)
    session.pop(_ONBOARDING_NEXT_SESSION_KEY, None)


def _coerce_onboarding_step(raw_value: object, *, default: int = 1) -> int:
    try:
        return int(str(raw_value).strip())
    except (TypeError, ValueError):
        return default


def _next_required_onboarding_step(draft: dict[str, str]) -> int:
    if not _clean_text(draft.get("user_type"), max_length=40):
        return 1
    if not _clean_text(draft.get("discovery_source"), max_length=40):
        return 2
    return 3


def _onboarding_step_url(step: int, *, next_url: str | None, direction: str | None = None) -> str:
    args: dict[str, object] = {"step": step}
    if next_url:
        args["next"] = next_url
    if direction:
        args["dir"] = direction
    return url_for("main.onboarding", **args)


def _user_defaults() -> dict[str, str]:
    return {
        "brand_tone": _clean_text(getattr(current_user, "default_brand_tone", ""), max_length=160),
        "content_density": _normalize_density_choice(getattr(current_user, "default_content_density", "balanced")),
        "motion_level": _normalize_motion_choice(getattr(current_user, "default_motion_level", "moderate")),
        "icon_style": _clean_text(getattr(current_user, "default_icon_style", ""), max_length=220),
    }


def _apply_user_defaults_to_brief(raw_brief: dict[str, object]) -> dict[str, object]:
    brief = dict(raw_brief)
    defaults = _user_defaults()
    if not _clean_text(brief.get("brand_tone"), max_length=160):
        brief["brand_tone"] = defaults["brand_tone"]
    if not _clean_text(brief.get("content_density"), max_length=24):
        brief["content_density"] = defaults["content_density"]
    if not _clean_text(brief.get("motion_level"), max_length=24):
        brief["motion_level"] = defaults["motion_level"]
    if not _clean_text(brief.get("icon_style"), max_length=220):
        brief["icon_style"] = defaults["icon_style"]
    return brief


def _normalized_brief(body: dict[str, object]) -> tuple[str, dict[str, object]]:
    prompt = _clean_text(body.get("prompt"), max_length=800)
    raw_brief = _apply_user_defaults_to_brief(_brief_payload(body))
    brief = {
        "goal": _clean_text(raw_brief.get("goal"), max_length=300),
        "audience": _clean_text(raw_brief.get("audience"), max_length=160),
        "brand_tone": _clean_text(raw_brief.get("brand_tone"), max_length=160),
        "content_density": _normalize_density_choice(raw_brief.get("content_density")),
        "motion_level": _normalize_motion_choice(raw_brief.get("motion_level")),
        "name": _clean_text(raw_brief.get("name"), max_length=120),
        "notes": _clean_text(raw_brief.get("notes"), max_length=600),
        "brand_assets": raw_brief.get("brand_assets") if isinstance(raw_brief.get("brand_assets"), list) else [],
        "icon_style": _clean_text(raw_brief.get("icon_style"), max_length=220),
    }
    return prompt, brief


@main.before_app_request
def enforce_onboarding_gate():
    if not getattr(current_user, "is_authenticated", False):
        return None

    endpoint = request.endpoint or ""
    if endpoint not in _ONBOARDING_PROTECTED_ENDPOINTS:
        return None
    if not _requires_onboarding(current_user):
        return None

    onboarding_url = _onboarding_redirect_url(request.path)
    if endpoint in _ONBOARDING_HTML_ENDPOINTS:
        return redirect(onboarding_url)
    return jsonify({"error": "Onboarding required.", "onboarding_url": onboarding_url}), 403


def _recent_conversation_payload(*, active_conversation_id: int | None = None, limit: int = 12) -> list[dict[str, Any]]:
    if not getattr(current_user, "is_authenticated", False):
        return []

    payload: list[dict[str, Any]] = []
    for conversation in list_recent_conversations(current_user, limit=limit):
        item = serialize_conversation_summary(conversation)
        item["is_active"] = conversation.id == active_conversation_id
        payload.append(item)
    return payload


def _conversation_for_preview(preview_id: str):
    return get_conversation_by_preview(_clean_text(preview_id, max_length=80), current_user)


def _conversation_for_preview_or_404(preview_id: str):
    conversation = _conversation_for_preview(preview_id)
    if not conversation:
        abort(404)
    return conversation


def _conversation_for_preview_or_json(preview_id: str):
    conversation = _conversation_for_preview(preview_id)
    if not conversation:
        return None, (jsonify({"error": "Preview not found."}), 404)
    return conversation, None


def _conversation_by_id_or_json(conversation_id: int):
    conversation = get_conversation_for_user(conversation_id, current_user)
    if not conversation:
        return None, (jsonify({"error": "Conversation not found."}), 404)
    return conversation, None


def _preview_urls(preview_id: str) -> dict[str, str]:
    return {
        "preview_url": url_for("main.preview", preview_id=preview_id),
        "studio_url": url_for("main.preview_studio", preview_id=preview_id),
        "frame_url": url_for("main.preview_frame", preview_id=preview_id),
    }


def _preview_page_context(conversation, manifest):
    studio = selected_preview_data(manifest)
    selected_variant = studio.get("selected_variant") or {}
    render_plan = selected_variant.get("render_plan", {})
    current_template = str(render_plan.get("template_key", "landing"))

    return {
        "preview_id": manifest.preview_id,
        "conversation_id": conversation.id,
        "conversation": serialize_conversation_summary(conversation),
        "conversation_messages": visible_messages(conversation),
        "recent_conversations": _recent_conversation_payload(active_conversation_id=conversation.id),
        "prompt": manifest.prompt,
        "brief": studio.get("brief", {}),
        "selected_variant": selected_variant,
        "selected_variant_id": studio.get("selected_variant_id", ""),
        "variants": studio.get("variants", []),
        "statuses": studio.get("statuses", []),
        "template_keys": list(TEMPLATE_CATALOG.keys()),
        "art_direction_keys": list(THEME_MAP.keys()),
        "layout_modes": list(LAYOUT_LIBRARY.get(current_template, {}).keys()),
        "layout_library": {key: list(value.keys()) for key, value in LAYOUT_LIBRARY.items()},
        "density_options": list(_DENSITY_CHOICES),
        "motion_options": list(_MOTION_CHOICES),
        **_preview_urls(manifest.preview_id),
    }


def _initial_generation_message(prompt: str, brief: dict[str, object]) -> str:
    goal = _clean_text(brief.get("goal"), max_length=220) or prompt
    audience = _clean_text(brief.get("audience"), max_length=120)
    tone = _clean_text(brief.get("brand_tone"), max_length=120)
    pieces = [goal or "Create a new website project."]
    if audience:
        pieces.append(f"Audience: {audience}.")
    if tone:
        pieces.append(f"Tone: {tone}.")
    return " ".join(piece for piece in pieces if piece)


@main.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(_post_auth_destination(current_user, request.args.get("next")))

    if request.method == "POST":
        email = _clean_text(request.form.get("email"), max_length=255).lower()
        password = str(request.form.get("password", ""))
        display_name = _clean_text(request.form.get("display_name"), max_length=120)

        if not email:
            flash("Email is required.", "error")
        elif len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
        elif User.query.filter_by(email=email).first():
            flash("That email is already registered.", "error")
        else:
            user = User(
                email=email,
                password_hash=generate_password_hash(password),
                display_name=display_name,
            )
            db.session.add(user)
            db.session.flush()
            db.session.add(UserOnboarding(user_id=user.id))
            db.session.commit()
            login_user(user)
            return redirect(_onboarding_redirect_url(request.args.get("next")))

    return render_template("signup.html")


@main.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(_post_auth_destination(current_user, request.args.get("next")))

    if request.method == "POST":
        email = _clean_text(request.form.get("email"), max_length=255).lower()
        password = str(request.form.get("password", ""))
        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password_hash, password):
            flash("Email or password is incorrect.", "error")
        else:
            login_user(user)
            flash("Welcome back.", "success")
            return redirect(_post_auth_destination(user, request.args.get("next")))

    return render_template("login.html")


@main.route("/onboarding", methods=["GET", "POST"])
@login_required
def onboarding():
    onboarding_record = current_user.onboarding
    if onboarding_record is None or onboarding_record.completed_at is not None:
        _clear_onboarding_draft()
        return redirect(_safe_next_url(request.args.get("next")))

    draft = _onboarding_draft()
    safe_next = _safe_next_or_none(
        request.args.get("next") or request.form.get("next_url") or session.get(_ONBOARDING_NEXT_SESSION_KEY)
    )
    if safe_next:
        session[_ONBOARDING_NEXT_SESSION_KEY] = safe_next

    if request.method == "POST":
        step = _coerce_onboarding_step(request.form.get("step"), default=1)
        step = max(1, min(_ONBOARDING_TOTAL_STEPS, step))
        next_required = _next_required_onboarding_step(draft)
        if step > next_required:
            direction = "back"
            return redirect(_onboarding_step_url(next_required, next_url=safe_next, direction=direction))

        if step == 1:
            user_type = _clean_text(request.form.get("user_type"), max_length=40).lower()
            if user_type not in _USER_TYPE_VALUES:
                flash("Choose the option that best describes you.", "error")
                return redirect(_onboarding_step_url(1, next_url=safe_next, direction="back"))
            draft["user_type"] = user_type
        elif step == 2:
            discovery_source = _clean_text(request.form.get("discovery_source"), max_length=40).lower()
            if discovery_source not in _DISCOVERY_SOURCE_VALUES:
                flash("Choose how you heard about VeloSite.", "error")
                return redirect(_onboarding_step_url(2, next_url=safe_next, direction="back"))
            draft["discovery_source"] = discovery_source
        else:
            draft["discovery_note"] = _clean_text(request.form.get("discovery_note"), max_length=220)

        _save_onboarding_draft(draft)
        if step < _ONBOARDING_TOTAL_STEPS:
            return redirect(_onboarding_step_url(step + 1, next_url=safe_next, direction="forward"))

        onboarding_record.user_type = _clean_text(draft.get("user_type"), max_length=40).lower()
        onboarding_record.discovery_source = _clean_text(draft.get("discovery_source"), max_length=40).lower()
        onboarding_record.discovery_note = _clean_text(draft.get("discovery_note"), max_length=220)
        onboarding_record.completed_at = datetime.now(UTC)
        db.session.add(onboarding_record)
        db.session.commit()
        _clear_onboarding_draft()
        flash("Great — onboarding complete.", "success")
        return redirect(_safe_next_url(safe_next))

    requested_step = _coerce_onboarding_step(request.args.get("step"), default=1)
    requested_step = max(1, min(_ONBOARDING_TOTAL_STEPS, requested_step))
    next_required = _next_required_onboarding_step(draft)
    if requested_step > next_required:
        return redirect(_onboarding_step_url(next_required, next_url=safe_next, direction="forward"))

    transition_dir = _clean_text(request.args.get("dir"), max_length=12).lower()
    if transition_dir not in {"forward", "back"}:
        transition_dir = "forward"

    step_configs = {
        1: {
            "title": "Which best describes you?",
            "description": "Choose one so we can tailor your starting flow.",
            "field_name": "user_type",
            "selected_value": _clean_text(draft.get("user_type"), max_length=40).lower(),
            "options": _USER_TYPE_OPTION_CARDS,
        },
        2: {
            "title": "How did you hear about us?",
            "description": "This helps us prioritize the channels that work.",
            "field_name": "discovery_source",
            "selected_value": _clean_text(draft.get("discovery_source"), max_length=40).lower(),
            "options": _DISCOVERY_SOURCE_OPTION_CARDS,
        },
        3: {
            "title": "Anything else to share? (optional)",
            "description": "Add details if you want a more personalized start.",
            "field_name": "discovery_note",
            "selected_value": _clean_text(draft.get("discovery_note"), max_length=220),
            "options": (),
        },
    }
    current_step = step_configs.get(requested_step, step_configs[1])
    back_step = requested_step - 1 if requested_step > 1 else None

    return render_template(
        "onboarding.html",
        hide_site_nav=True,
        step=requested_step,
        total_steps=_ONBOARDING_TOTAL_STEPS,
        step_title=current_step["title"],
        step_description=current_step["description"],
        step_field_name=current_step["field_name"],
        step_selected=current_step["selected_value"],
        step_options=current_step["options"],
        back_step=back_step,
        transition_dir=transition_dir,
        next_url=safe_next,
    )


@main.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("main.login"))


@main.route("/", methods=["GET"])
def marketing_home():
    return _render_marketing_page(
        "marketing/home.html",
        page_title="VeloSite | AI Website Generator for Product Teams",
        active_slug="home",
    )


@main.route("/product", methods=["GET"])
def product():
    return _render_marketing_page(
        "marketing/product.html",
        page_title="Product | VeloSite",
        active_slug="product",
    )


@main.route("/showcase", methods=["GET"])
def showcase():
    return _render_marketing_page(
        "marketing/showcase.html",
        page_title="Showcase | VeloSite",
        active_slug="showcase",
    )


@main.route("/solutions", methods=["GET"])
def solutions():
    return _render_marketing_page(
        "marketing/solutions.html",
        page_title="Solutions | VeloSite",
        active_slug="solutions",
    )


@main.route("/how-it-works", methods=["GET"])
def how_it_works():
    return _render_marketing_page(
        "marketing/how_it_works.html",
        page_title="How It Works | VeloSite",
        active_slug="how-it-works",
    )


@main.route("/pricing", methods=["GET"])
def pricing():
    return _render_marketing_page(
        "marketing/pricing.html",
        page_title="Pricing | VeloSite",
        active_slug="pricing",
    )


@main.route("/resources", methods=["GET"])
def resources():
    return _render_marketing_page(
        "marketing/resources.html",
        page_title="Resources | VeloSite",
        active_slug="resources",
    )


@main.route("/about", methods=["GET"])
def about():
    return _render_marketing_page(
        "marketing/about.html",
        page_title="About | VeloSite",
        active_slug="about",
    )


@main.route("/contact", methods=["GET"])
def contact():
    return _render_marketing_page(
        "marketing/contact.html",
        page_title="Contact | VeloSite",
        active_slug="contact",
    )


@main.route("/app", methods=["GET"])
@login_required
def index():
    return render_template(
        "home.html",
        page_title="VeloSite Studio",
        hide_site_nav=True,
        examples=_example_prompts(),
        demo_brief=_demo_brief(),
        status_blueprint=status_blueprint(),
        density_options=list(_DENSITY_CHOICES),
        motion_options=list(_MOTION_CHOICES),
        recent_conversations=_recent_conversation_payload(),
        user_defaults=_user_defaults(),
    )


@main.route("/dashboard", methods=["GET"])
@login_required
def dashboard():
    return redirect(url_for("main.index"))


@main.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    if request.method == "POST":
        action = _clean_text(request.form.get("action"), max_length=24).lower()

        if action == "profile":
            email = _clean_text(request.form.get("email"), max_length=255).lower()
            display_name = _clean_text(request.form.get("display_name"), max_length=120)
            brand_tone = _clean_text(request.form.get("default_brand_tone"), max_length=160)
            density = _normalize_density_choice(request.form.get("default_content_density"))
            motion = _normalize_motion_choice(request.form.get("default_motion_level"))
            icon_style = _clean_text(request.form.get("default_icon_style"), max_length=220)

            existing = User.query.filter_by(email=email).first() if email else None
            if not email:
                flash("Email is required.", "error")
            elif existing and existing.id != current_user.id:
                flash("That email is already in use.", "error")
            else:
                current_user.email = email
                current_user.display_name = display_name
                current_user.default_brand_tone = brand_tone
                current_user.default_content_density = density
                current_user.default_motion_level = motion
                current_user.default_icon_style = icon_style
                db.session.add(current_user)
                db.session.commit()
                flash("Settings updated.", "success")
                return redirect(url_for("main.settings"))

        elif action == "password":
            current_password = str(request.form.get("current_password", ""))
            next_password = str(request.form.get("new_password", ""))
            confirm_password = str(request.form.get("confirm_password", ""))

            if not check_password_hash(current_user.password_hash, current_password):
                flash("Current password is incorrect.", "error")
            elif len(next_password) < 8:
                flash("New password must be at least 8 characters.", "error")
            elif next_password != confirm_password:
                flash("New password confirmation does not match.", "error")
            else:
                current_user.password_hash = generate_password_hash(next_password)
                db.session.add(current_user)
                db.session.commit()
                flash("Password updated.", "success")
                return redirect(url_for("main.settings"))

        elif action == "delete":
            current_password = str(request.form.get("current_password", ""))
            if not check_password_hash(current_user.password_hash, current_password):
                flash("Current password is incorrect.", "error")
            else:
                user_id = current_user.id
                logout_user()
                user = db.session.get(User, user_id)
                if user is not None:
                    db.session.delete(user)
                    db.session.commit()
                flash("Your account and conversations were deleted.", "success")
                return redirect(url_for("main.signup"))

    conversation_count = len(list_recent_conversations(current_user, limit=500))
    return render_template(
        "settings.html",
        density_option_cards=_DENSITY_OPTION_CARDS,
        motion_option_cards=_MOTION_OPTION_CARDS,
        conversation_count=conversation_count,
        user_defaults=_user_defaults(),
    )


@main.route("/healthz", methods=["GET"])
def healthz():
    return jsonify({"ok": True, "service": "velosite-ai"}), 200


@main.route("/conversations", methods=["GET"])
@login_required
def conversations():
    return jsonify({"conversations": _recent_conversation_payload()})


@main.route("/conversations/<int:conversation_id>/rename", methods=["POST"])
@login_required
def rename_user_conversation(conversation_id: int):
    conversation, error = _conversation_by_id_or_json(conversation_id)
    if error:
        return error

    body = request.get_json(silent=True) or {}
    title = _clean_text(body.get("title"), max_length=120)
    if not title:
        return jsonify({"error": "Title is required."}), 400

    rename_conversation(conversation, title)
    return jsonify({"ok": True, "conversation": serialize_conversation_summary(conversation)})


@main.route("/conversations/<int:conversation_id>", methods=["DELETE"])
@login_required
def delete_user_conversation(conversation_id: int):
    conversation, error = _conversation_by_id_or_json(conversation_id)
    if error:
        return error

    deleted_id = conversation.id
    delete_conversation(conversation)
    return jsonify({"ok": True, "deleted_id": deleted_id, "redirect_url": url_for("main.index")})


@main.route("/conversations/<int:conversation_id>/messages", methods=["POST"])
@login_required
def continue_conversation(conversation_id: int):
    conversation, error = _conversation_by_id_or_json(conversation_id)
    if error:
        return error

    body = request.get_json(silent=True) or {}
    instruction = _clean_text(body.get("message") or body.get("prompt"), max_length=1200)
    variant_id = _clean_text(body.get("variant_id"), max_length=64) or None
    if not instruction:
        return jsonify({"error": "A follow-up message is required."}), 400

    manifest = manifest_from_conversation(conversation)
    try:
        updated_manifest, assistant_reply = continue_project_manifest(
            manifest,
            instruction,
            variant_id=variant_id,
            messages=history_messages(conversation),
        )
    except AIProviderUnavailableError as exc:
        body, status_code = _service_unavailable_response(exc)
        return jsonify(body), status_code
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    save_manifest(conversation, updated_manifest, commit=False)
    append_message(conversation, role="user", body=instruction, preview_id=updated_manifest.preview_id, commit=False)
    append_message(
        conversation,
        role="assistant",
        body=assistant_reply,
        preview_id=updated_manifest.preview_id,
        commit=False,
    )
    db.session.commit()

    studio = selected_preview_data(updated_manifest)
    return jsonify(
        {
            "ok": True,
            "conversation_id": conversation.id,
            "preview_id": updated_manifest.preview_id,
            "selected_variant_id": updated_manifest.selected_variant_id,
            "selected_variant": studio.get("selected_variant", {}),
            "messages": visible_messages(conversation),
            "conversation": serialize_conversation_summary(conversation),
            "recent_conversations": _recent_conversation_payload(active_conversation_id=conversation.id),
            **_preview_urls(updated_manifest.preview_id),
        }
    )


@main.route("/generate", methods=["POST"])
@login_required
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

    conversation = create_conversation(
        current_user,
        manifest=manifest,
        user_message=_initial_generation_message(user_prompt, brief),
    )

    urls = _preview_urls(manifest.preview_id)
    return jsonify(
        {
            "conversation_id": conversation.id,
            "preview_id": manifest.preview_id,
            **urls,
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
@login_required
def update_branding(preview_id: str):
    conversation, error = _conversation_for_preview_or_json(preview_id)
    if error:
        return error

    manifest = manifest_from_conversation(conversation)
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
    save_manifest(conversation, updated)
    record_system_event(conversation, "Updated brand assets or icon direction notes.")
    selected = selected_preview_data(updated).get("selected_variant", {})

    return jsonify(
        {
            "ok": True,
            "preview_id": preview_id,
            "selected_variant_id": updated.selected_variant_id,
            "selected_variant": selected,
            "brief": updated.brief.to_dict(),
            **_preview_urls(preview_id),
        }
    )


@main.route("/preview/<preview_id>", methods=["GET"])
@login_required
def preview(preview_id: str):
    conversation = _conversation_for_preview_or_404(preview_id)
    manifest = manifest_from_conversation(conversation)

    return render_template(
        "preview_shell.html",
        hide_site_nav=True,
        **_preview_page_context(conversation, manifest),
    )


@main.route("/preview/<preview_id>/studio", methods=["GET"])
@login_required
def preview_studio(preview_id: str):
    conversation = _conversation_for_preview_or_404(preview_id)
    manifest = manifest_from_conversation(conversation)

    return render_template(
        "studio_shell.html",
        hide_site_nav=True,
        **_preview_page_context(conversation, manifest),
    )


@main.route("/preview/<preview_id>/frame", methods=["GET"])
@login_required
def preview_frame(preview_id: str):
    conversation = _conversation_for_preview_or_404(preview_id)
    manifest = manifest_from_conversation(conversation)

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
        embedded_mode=request.args.get("embed", "").strip() == "1",
        consumer_mode=True,
    )


@main.route("/preview/<preview_id>/override", methods=["POST"])
@login_required
def override_preview(preview_id: str):
    conversation, error = _conversation_for_preview_or_json(preview_id)
    if error:
        return error

    manifest = manifest_from_conversation(conversation)
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

    save_manifest(conversation, updated)
    record_system_event(conversation, "Applied layout or style overrides in Studio.")
    selected = selected_preview_data(updated).get("selected_variant", {})

    return jsonify(
        {
            "ok": True,
            "preview_id": preview_id,
            "selected_variant_id": updated.selected_variant_id,
            "selected_variant": selected,
            "render_plan": selected.get("render_plan", {}),
            **_preview_urls(preview_id),
        }
    )


@main.route("/preview/<preview_id>/command", methods=["POST"])
@login_required
def canvas_command(preview_id: str):
    conversation, error = _conversation_for_preview_or_json(preview_id)
    if error:
        return error

    manifest = manifest_from_conversation(conversation)
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

    save_manifest(conversation, updated)
    record_system_event(conversation, f"Applied Studio action: {action or 'edit'}.")
    selected = selected_preview_data(updated).get("selected_variant", {})
    return jsonify(
        {
            "ok": True,
            "preview_id": preview_id,
            "selected_variant_id": updated.selected_variant_id,
            "selected_variant": selected,
            "changed_paths": changed_paths,
            **_preview_urls(preview_id),
        }
    )


@main.route("/preview/<preview_id>/regenerate", methods=["POST"])
@login_required
@observe_route("regenerate")
def regenerate_preview(preview_id: str):
    conversation, error = _conversation_for_preview_or_json(preview_id)
    if error:
        return error

    manifest = manifest_from_conversation(conversation)
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

    save_manifest(conversation, updated)
    record_system_event(conversation, f"Regenerated {scope} for the current design direction.")
    selected = selected_preview_data(updated).get("selected_variant", {})
    return jsonify(
        {
            "ok": True,
            "preview_id": preview_id,
            "selected_variant_id": updated.selected_variant_id,
            "selected_variant": selected,
            **_preview_urls(preview_id),
        }
    )


@main.route("/preview/<preview_id>/publish", methods=["POST"])
@login_required
@observe_route("publish")
def publish_preview(preview_id: str):
    conversation, error = _conversation_for_preview_or_json(preview_id)
    if error:
        return error

    manifest = manifest_from_conversation(conversation)
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
@login_required
@observe_route("export")
def export_preview(preview_id: str):
    conversation, error = _conversation_for_preview_or_json(preview_id)
    if error:
        return error

    manifest = manifest_from_conversation(conversation)
    archive, filename = build_export_bundle(manifest)
    return send_file(
        archive,
        mimetype="application/zip",
        as_attachment=True,
        download_name=filename,
    )
