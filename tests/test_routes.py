import unittest
from unittest.mock import patch

from app import create_app
from app.services.contracts import ProjectManifest
from app.services.preview_store import PREVIEW_STORE


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

    def test_generate_accepts_prompt_only(self):
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

    def test_export_returns_zip(self):
        PREVIEW_STORE.set(preview_id="preview-export", prompt="Some prompt", payload=_payload("preview-export"))
        response = self.client.post("/preview/preview-export/export")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/zip")
        self.assertIn("attachment;", response.headers.get("Content-Disposition", ""))

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

    @patch("app.services.ai_engine.get_default_provider")
    def test_generate_handles_unavailable_ai_by_falling_back(self, mocked_provider):
        mocked_provider.return_value = None
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
        preview_url = response.get_json()["preview_url"]
        preview_response = self.client.get(preview_url)
        self.assertEqual(preview_response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
