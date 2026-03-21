import unittest
from io import BytesIO
from unittest.mock import patch
from zipfile import ZipFile

from app import create_app
from app.services.ai_provider import AIProviderUnavailableError
from app.services.contracts import ProjectManifest
from app.services.manifest_service import MANIFEST_SERVICE
from app.services.preview_store import PREVIEW_STORE
from app.services.published_site_service import PUBLISHED_SITE_SERVICE


def _brand_asset(name: str = "logo.svg", data_url: str | None = None):
    return {
        "id": "brand-asset-1",
        "name": name,
        "alt": "Northstar logo",
        "mime_type": "image/svg+xml",
        "data_url": data_url
        or "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPjwvc3ZnPg==",
    }


def _variant(variant_id: str, template_key: str = "landing", art_direction: str = "modern_editorial", layout_mode: str = "split_hero"):
    return {
        "variant_id": variant_id,
        "label": f"Variant {variant_id}",
        "summary": "A routed design direction.",
        "render_plan": {
            "template_key": template_key,
            "template_file": "generated/site_builder.html",
            "theme_key": art_direction,
            "art_direction": art_direction,
            "layout_mode": layout_mode,
            "density": "balanced",
            "motion_level": "moderate",
            "section_order": ["hero", "features", "proof", "cta"] if template_key != "portfolio" else ["hero", "projects", "about", "cta"],
            "section_visibility": {"hero": True, "features": True, "proof": True, "cta": True, "projects": True, "about": True},
            "hero_variant": "split",
            "industry": "technology",
            "vibe": "clean",
            "keywords": ["tech", "startup", "growth"],
            "confidence": 0.82,
            "reasons": ["test payload"],
            "slot_schema": {
                "text_slots": ["hero_eyebrow", "hero_title", "hero_subtitle", "cta_text", "cta_note", "proof_quote", "proof_author"],
                "list_slots": {
                    "features": {"item_fields": ["title", "desc"], "min_items": 3, "max_items": 6},
                    "projects": {"item_fields": ["title", "desc", "meta"], "min_items": 3, "max_items": 6},
                },
            },
        },
        "theme": {
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
        "content": {
            "hero_eyebrow": "Modern Editorial",
            "hero_title": "Build momentum",
            "hero_subtitle": "Turn visitors into users.",
            "cta_text": "Start now",
            "cta_note": "Launch a sharper concept quickly.",
            "proof_quote": "This direction feels distinct.",
            "proof_author": "Test reviewer",
            "about_text": "A focused practice.",
            "features": [
                {"title": "A", "desc": "A desc"},
                {"title": "B", "desc": "B desc"},
                {"title": "C", "desc": "C desc"},
            ],
            "projects": [
                {"title": "A", "desc": "A desc", "meta": "Brand"},
                {"title": "B", "desc": "B desc", "meta": "Web"},
                {"title": "C", "desc": "C desc", "meta": "Growth"},
            ],
        },
    }


def _payload(preview_id: str):
    return {
        "preview_id": preview_id,
        "prompt": "A startup landing page",
        "brief": {
            "goal": "A startup landing page",
            "audience": "Founders",
            "brand_tone": "Clear and modern",
            "content_density": "balanced",
            "motion_level": "moderate",
            "name": "Northstar",
            "notes": "Lead with proof.",
            "prompt": "A startup landing page",
            "brand_assets": [],
            "icon_style": "",
        },
        "selected_variant_id": "variant-1",
        "variants": [
            _variant("variant-1", template_key="landing", art_direction="modern_editorial", layout_mode="split_hero"),
            _variant("variant-2", template_key="landing", art_direction="warm_gradient", layout_mode="immersive_layers"),
            _variant("variant-3", template_key="landing", art_direction="brutalist_poster", layout_mode="proof_first"),
        ],
        "statuses": [
            {"key": "validate", "label": "Validating prompt", "state": "complete", "detail": "Brief normalized and request sanitized."},
            {"key": "classify", "label": "Classifying intent", "state": "complete", "detail": "Choosing deterministic structure and layout candidates."},
            {"key": "generate", "label": "Generating content", "state": "complete", "detail": "Requesting structured JSON content for selected render plans."},
            {"key": "validate_schema", "label": "Validating schema", "state": "complete", "detail": "Filling defaults and recording fallbacks."},
            {"key": "render", "label": "Rendering preview", "state": "complete", "detail": "Preparing iframe-ready HTML and studio metadata."},
            {"key": "export", "label": "Export ready", "state": "complete", "detail": "Project can be exported at any time."},
        ],
    }


class RouteTests(unittest.TestCase):
    def setUp(self):
        PREVIEW_STORE.clear()
        PUBLISHED_SITE_SERVICE.clear()
        self.app = create_app()
        self.client = self.app.test_client()

    def test_get_home_renders_guided_brief(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Guided brief", body)
        self.assertIn("Generate Studio", body)
        self.assertIn("Try Demo Prompt", body)
        self.assertIn("Pipeline progress", body)

    def test_healthz_returns_ok(self):
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["ok"], True)
        self.assertEqual(data["service"], "velosite-ai")

    @patch("app.routes.generate_project_manifest")
    def test_generate_returns_variant_metadata(self, mocked_generate):
        mocked_generate.return_value = ProjectManifest.from_dict(_payload("preview-123"))
        response = self.client.post(
            "/generate",
            json={
                "prompt": "A startup landing page",
                "brief": {
                    "goal": "A startup landing page",
                    "audience": "Founders",
                    "brand_tone": "Clear and modern",
                    "content_density": "balanced",
                    "motion_level": "moderate",
                },
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["preview_id"], "preview-123")
        self.assertEqual(data["selected_variant_id"], "variant-1")
        self.assertEqual(len(data["variants"]), 3)
        self.assertIn("frame_url", data)

        preview_response = self.client.get(data["preview_url"])
        self.assertEqual(preview_response.status_code, 200)
        body = preview_response.get_data(as_text=True)
        self.assertIn("Preview canvas", body)
        self.assertIn("Section layers", body)
        self.assertIn("Generation states", body)

    @patch("app.routes.generate_project_manifest")
    def test_generate_forwards_brand_assets_and_icon_style(self, mocked_generate):
        mocked_generate.return_value = ProjectManifest.from_dict(_payload("preview-branding"))
        brand_asset = _brand_asset()
        response = self.client.post(
            "/generate",
            json={
                "prompt": "A startup landing page",
                "brief": {
                    "goal": "A startup landing page",
                    "audience": "Founders",
                    "brand_tone": "Clear and modern",
                    "content_density": "balanced",
                    "motion_level": "moderate",
                    "brand_assets": [brand_asset],
                    "icon_style": "Rounded product icons",
                },
            },
        )
        self.assertEqual(response.status_code, 200)
        forwarded_brief = mocked_generate.call_args.kwargs["brief"]
        self.assertEqual(forwarded_brief["icon_style"], "Rounded product icons")
        self.assertEqual(len(forwarded_brief["brand_assets"]), 1)
        self.assertEqual(forwarded_brief["brand_assets"][0]["data_url"], brand_asset["data_url"])

    @patch("app.routes.generate_project_manifest")
    def test_generate_accepts_prompt_only(self, mocked_generate):
        mocked_generate.return_value = ProjectManifest.from_dict(_payload("preview-prompt-only"))
        response = self.client.post("/generate", json={"prompt": "A product launch page"})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data["variants"]), 3)
        self.assertTrue(data["selected_variant_id"])
        self.assertGreaterEqual(len(data["statuses"]), 5)

    def test_override_can_switch_selected_variant(self):
        PREVIEW_STORE.set(preview_id="preview-456", prompt="Some prompt", payload=_payload("preview-456"))
        response = self.client.post("/preview/preview-456/override", json={"variant_id": "variant-2"})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["selected_variant_id"], "variant-2")
        updated = PREVIEW_STORE.get("preview-456")
        self.assertEqual(updated["payload"]["selected_variant_id"], "variant-2")

    def test_override_can_apply_layout_changes(self):
        PREVIEW_STORE.set(preview_id="preview-789", prompt="Some prompt", payload=_payload("preview-789"))
        response = self.client.post(
            "/preview/preview-789/override",
            json={
                "variant_id": "variant-1",
                "layout_mode": "immersive_layers",
                "art_direction": "warm_gradient",
                "section_visibility": {"proof": False},
            },
        )
        self.assertEqual(response.status_code, 200)
        updated = PREVIEW_STORE.get("preview-789")
        variant = updated["payload"]["variants"][0]
        self.assertEqual(variant["render_plan"]["layout_mode"], "immersive_layers")
        self.assertEqual(variant["render_plan"]["art_direction"], "warm_gradient")
        self.assertFalse(variant["render_plan"]["section_visibility"]["proof"])

    def test_preview_404_when_id_missing(self):
        response = self.client.get("/preview/does-not-exist")
        self.assertEqual(response.status_code, 404)

    def test_preview_frame_accepts_query_overrides_for_remix(self):
        PREVIEW_STORE.set(preview_id="preview-frame", prompt="Some prompt", payload=_payload("preview-frame"))
        response = self.client.get(
            "/preview/preview-frame/frame?variant_id=variant-1&layout_mode=proof_first&art_direction=warm_gradient&remix_label=Remix+1"
        )
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Remix 1", body)
        self.assertIn("--theme-frame-background", body)
        self.assertIn("Contact", body)
        self.assertNotIn("Explore Flow", body)
        self.assertNotIn("Distinct sections with actual jobs to do.", body)

    def test_preview_frame_renders_uploaded_brand_asset(self):
        payload = _payload("preview-brand-asset")
        payload["brief"]["brand_assets"] = [_brand_asset()]
        PREVIEW_STORE.set(preview_id="preview-brand-asset", prompt="Some prompt", payload=payload)
        response = self.client.get("/preview/preview-brand-asset/frame")
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("frame-brand-logo", body)
        self.assertIn("data:image/svg+xml;base64", body)

    def test_preview_frame_uses_top_anchor_for_brand_navigation(self):
        PREVIEW_STORE.set(preview_id="preview-nav", prompt="Some prompt", payload=_payload("preview-nav"))
        response = self.client.get("/preview/preview-nav/frame")
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn('id="page-top"', body)
        self.assertIn('href="#page-top"', body)
        self.assertIn('data-site-nav-link="true"', body)

    def test_export_returns_zip(self):
        PREVIEW_STORE.set(preview_id="preview-export", prompt="Some prompt", payload=_payload("preview-export"))
        response = self.client.post("/preview/preview-export/export")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/zip")
        self.assertIn("attachment;", response.headers.get("Content-Disposition", ""))

    def test_publish_returns_public_link_and_content(self):
        PREVIEW_STORE.set(preview_id="preview-publish", prompt="Some prompt", payload=_payload("preview-publish"))
        response = self.client.post("/preview/preview-publish/publish", json={"variant_id": "variant-2"})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["ok"])
        self.assertTrue(data["publish_id"])
        self.assertIn("/published/", data["public_path"])
        self.assertIn("http://localhost/published/", data["public_url"])

        site_response = self.client.get(data["public_path"])
        self.assertEqual(site_response.status_code, 200)
        site_html = site_response.get_data(as_text=True)
        self.assertIn("<!DOCTYPE html>", site_html)
        self.assertIn("Build momentum", site_html)
        self.assertNotIn("Variant variant-2", site_html)
        self.assertNotIn("Open Project", site_html)
        self.assertNotIn("Share Concept", site_html)

        css_response = self.client.get(f"/published/{data['publish_id']}/assets/export-frame.css")
        self.assertEqual(css_response.status_code, 200)
        self.assertEqual(css_response.mimetype, "text/css")

    def test_regenerate_section_returns_updated_preview(self):
        PREVIEW_STORE.set(preview_id="preview-regen", prompt="Some prompt", payload=_payload("preview-regen"))
        response = self.client.post(
            "/preview/preview-regen/regenerate",
            json={"scope": "section", "variant_id": "variant-1", "section_name": "hero"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["selected_variant_id"], "variant-1")

    def test_canvas_command_can_update_text_override(self):
        PREVIEW_STORE.set(preview_id="preview-command", prompt="Some prompt", payload=_payload("preview-command"))
        response = self.client.post(
            "/preview/preview-command/command",
            json={
                "variant_id": "variant-1",
                "action": "set_text",
                "node_id": "hero-title",
                "edit_path": "hero_title",
                "value": "A sharper hero headline",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["selected_variant"]["content"]["hero_title"], "A sharper hero headline")
        updated = PREVIEW_STORE.get("preview-command")
        variant = updated["payload"]["variants"][0]
        self.assertEqual(variant["content_overrides"]["hero_title"], "A sharper hero headline")

    def test_canvas_command_can_move_and_toggle_section(self):
        PREVIEW_STORE.set(preview_id="preview-layout", prompt="Some prompt", payload=_payload("preview-layout"))
        move_response = self.client.post(
            "/preview/preview-layout/command",
            json={
                "variant_id": "variant-1",
                "action": "move_section",
                "section_name": "proof",
                "direction": "up",
            },
        )
        self.assertEqual(move_response.status_code, 200)
        toggle_response = self.client.post(
            "/preview/preview-layout/command",
            json={
                "variant_id": "variant-1",
                "action": "toggle_section",
                "section_name": "proof",
                "value": False,
            },
        )
        self.assertEqual(toggle_response.status_code, 200)
        updated = PREVIEW_STORE.get("preview-layout")
        variant = updated["payload"]["variants"][0]
        self.assertEqual(variant["layout_overrides"]["section_order"][1], "proof")
        self.assertFalse(variant["layout_overrides"]["section_visibility"]["proof"])

    def test_canvas_command_rejects_invalid_path(self):
        PREVIEW_STORE.set(preview_id="preview-invalid", prompt="Some prompt", payload=_payload("preview-invalid"))
        response = self.client.post(
            "/preview/preview-invalid/command",
            json={
                "variant_id": "variant-1",
                "action": "set_text",
                "edit_path": "nonexistent_slot",
                "value": "Nope",
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_branding_route_updates_brief_assets_and_icon_style(self):
        PREVIEW_STORE.set(preview_id="preview-branding-update", prompt="Some prompt", payload=_payload("preview-branding-update"))
        response = self.client.post(
            "/preview/preview-branding-update/branding",
            json={
                "brief": {
                    "brand_assets": [_brand_asset("brand-mark.svg")],
                    "icon_style": "Sharp monochrome icons",
                }
            },
        )
        self.assertEqual(response.status_code, 200)
        updated = PREVIEW_STORE.get("preview-branding-update")
        brief = updated["payload"]["brief"]
        self.assertEqual(brief["icon_style"], "Sharp monochrome icons")
        self.assertEqual(len(brief["brand_assets"]), 1)
        self.assertEqual(brief["brand_assets"][0]["name"], "brand-mark.svg")

    def test_export_applies_saved_overrides(self):
        PREVIEW_STORE.set(preview_id="preview-export-edit", prompt="Some prompt", payload=_payload("preview-export-edit"))
        self.client.post(
            "/preview/preview-export-edit/command",
            json={
                "variant_id": "variant-1",
                "action": "set_text",
                "node_id": "hero-title",
                "edit_path": "hero_title",
                "value": "Exported headline",
            },
        )
        response = self.client.post("/preview/preview-export-edit/export")
        self.assertEqual(response.status_code, 200)
        archive = ZipFile(BytesIO(response.data))
        index_html = archive.read("index.html").decode("utf-8")
        self.assertIn("Exported headline", index_html)

    def test_regenerate_all_preserves_content_overrides(self):
        PREVIEW_STORE.set(preview_id="preview-regen-all", prompt="Some prompt", payload=_payload("preview-regen-all"))
        self.client.post(
            "/preview/preview-regen-all/command",
            json={
                "variant_id": "variant-1",
                "action": "set_text",
                "node_id": "hero-title",
                "edit_path": "hero_title",
                "value": "Sticky override",
            },
        )
        response = self.client.post(
            "/preview/preview-regen-all/regenerate",
            json={"scope": "all", "variant_id": "variant-1"},
        )
        self.assertEqual(response.status_code, 200)
        updated = PREVIEW_STORE.get("preview-regen-all")
        variant = updated["payload"]["variants"][0]
        self.assertEqual(variant["content_overrides"]["hero_title"], "Sticky override")

    @patch("app.services.ai_engine.get_default_provider", return_value=None)
    def test_generate_falls_back_when_ai_is_missing(self, mocked_provider):
        response = self.client.post(
            "/generate",
            json={
                "prompt": "A startup landing page",
                "brief": {
                    "goal": "A startup landing page",
                    "audience": "Founders",
                    "brand_tone": "Clear and modern",
                    "content_density": "balanced",
                    "motion_level": "moderate",
                },
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["preview_id"])
        generate_stage = next(stage for stage in data["statuses"] if stage["key"] == "generate")
        self.assertIn("Gemini was unavailable", generate_stage["detail"])
        manifest = MANIFEST_SERVICE.get(data["preview_id"])
        self.assertIsNotNone(manifest)
        self.assertTrue(manifest.variants[0].content.validation.fallback_used)

    @patch("app.routes.configured_api_key_count", return_value=1)
    @patch("app.routes.generate_project_manifest")
    def test_generate_sanitizes_quota_errors_for_single_key(self, mocked_generate, mocked_key_count):
        mocked_generate.side_effect = AIProviderUnavailableError(
            "Gemini generation is unavailable because the configured API key is out of quota or rate-limited. "
            "Tried models: gemini-2.5-flash-lite, gemini-2.5-flash. Set GEMINI_MODEL to a model with available quota. "
            "Last error: ResourceExhausted: 429 quota exceeded."
        )
        response = self.client.post(
            "/generate",
            json={
                "prompt": "A startup landing page",
                "brief": {
                    "goal": "A startup landing page",
                    "audience": "Founders",
                    "brand_tone": "Clear and modern",
                    "content_density": "balanced",
                    "motion_level": "moderate",
                },
            },
        )

        self.assertEqual(response.status_code, 503)
        data = response.get_json()
        self.assertEqual(
            data["error"],
            "Gemini generation is temporarily unavailable because the only configured API key is out of quota. Add another Gemini key to enable rotation, or try again after the quota resets.",
        )
        self.assertNotIn("Tried models", data["error"])
        self.assertNotIn("ResourceExhausted", data["error"])
        self.assertNotIn("GEMINI_MODEL", data["error"])

    @patch("app.routes.configured_api_key_count", return_value=3)
    @patch("app.routes.generate_project_manifest")
    def test_generate_sanitizes_quota_errors_for_multiple_keys(self, mocked_generate, mocked_key_count):
        mocked_generate.side_effect = AIProviderUnavailableError(
            "Gemini generation is unavailable because all configured API keys are out of quota or rate-limited. "
            "Tried APIs: api#1, api#2, api#3. Last error: ResourceExhausted: 429 quota exceeded."
        )
        response = self.client.post(
            "/generate",
            json={
                "prompt": "A startup landing page",
                "brief": {
                    "goal": "A startup landing page",
                    "audience": "Founders",
                    "brand_tone": "Clear and modern",
                    "content_density": "balanced",
                    "motion_level": "moderate",
                },
            },
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.get_json()["error"],
            "Gemini generation is temporarily unavailable because all configured API keys are out of quota. Add another Gemini key or try again after the quota resets.",
        )


class AppStartupLoggingTests(unittest.TestCase):
    @patch("app.services.ai_provider.configured_api_key_sources", return_value=("GEMINI_API_KEY",))
    @patch("app.services.ai_provider.configured_api_key_count", return_value=1)
    def test_create_app_logs_warning_when_only_one_key_is_configured(self, mocked_count, mocked_sources):
        with self.assertLogs("app", level="WARNING") as captured:
            create_app()

        self.assertIn(
            "ai.provider.startup configured_gemini_keys=1 sources=GEMINI_API_KEY",
            "\n".join(captured.output),
        )
        mocked_count.assert_called_once_with()
        mocked_sources.assert_called_once_with()

    @patch(
        "app.services.ai_provider.configured_api_key_sources",
        return_value=("GEMINI_API_KEY_1", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3"),
    )
    @patch("app.services.ai_provider.configured_api_key_count", return_value=3)
    def test_create_app_logs_info_when_multiple_keys_are_configured(self, mocked_count, mocked_sources):
        with self.assertLogs("app", level="INFO") as captured:
            create_app()

        self.assertIn(
            "ai.provider.startup configured_gemini_keys=3 sources=GEMINI_API_KEY_1, GEMINI_API_KEY_2, GEMINI_API_KEY_3",
            "\n".join(captured.output),
        )
        mocked_count.assert_called_once_with()
        mocked_sources.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
