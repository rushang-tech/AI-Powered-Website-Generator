import os
import tempfile
import unittest

from flask import render_template

from app import create_app
from app.extensions import db


class VisualRenderingTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = os.path.join(self.temp_dir.name, "rendering-test.db")
        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-secret",
                "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}",
            }
        )
        with self.app.app_context():
            db.drop_all()
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
        self.temp_dir.cleanup()

    def _brief(self) -> dict[str, object]:
        return {
            "goal": "A product landing page",
            "audience": "Founders",
            "brand_tone": "Bold, clear, premium",
            "content_density": "balanced",
            "motion_level": "moderate",
            "name": "Northstar",
            "notes": "Lead with proof.",
            "prompt": "A product landing page",
            "brand_assets": [],
            "icon_style": "Rounded editorial product icons",
        }

    def _selected_variant(self, visuals: dict[str, object]) -> dict[str, object]:
        return {
            "variant_id": "variant-1",
            "label": "Variant 1",
            "summary": "A routed design direction.",
            "render_plan": {
                "template_key": "landing",
                "template_file": "generated/site_builder.html",
                "theme_key": "modern_editorial",
                "art_direction": "modern_editorial",
                "layout_mode": "split_hero",
                "density": "balanced",
                "motion_level": "moderate",
                "section_order": ["hero", "features", "projects", "capabilities", "cta"],
                "section_visibility": {"hero": True, "features": True, "projects": True, "capabilities": True, "cta": True},
                "hero_variant": "split",
                "industry": "technology",
                "vibe": "clean",
                "keywords": ["product", "analytics", "growth"],
                "confidence": 0.88,
                "reasons": ["test payload"],
                "slot_schema": {
                    "text_slots": ["hero_eyebrow", "hero_title", "hero_subtitle", "cta_text", "cta_note"],
                    "list_slots": {
                        "features": {"item_fields": ["title", "desc"], "min_items": 3, "max_items": 6},
                        "projects": {"item_fields": ["title", "desc", "meta"], "min_items": 3, "max_items": 6},
                        "capabilities": {"item_fields": ["title", "desc"], "min_items": 3, "max_items": 6},
                    },
                },
            },
            "theme": {
                "canvas_background": "linear-gradient(180deg, #eff3f8 0%, #dde4ec 100%)",
                "panel_background": "rgba(252, 254, 255, 0.88)",
                "surface": "#fbfdff",
                "surface_alt": "#eef3f8",
                "text": "#111827",
                "muted": "#586273",
                "accent": "#88d92f",
                "accent_soft": "rgba(136, 217, 47, 0.16)",
                "border": "rgba(17, 24, 39, 0.12)",
                "button_bg": "#111827",
                "button_text": "#f7fafc",
                "shadow": "0 22px 60px rgba(29, 45, 68, 0.12)",
                "display_font": "'Cormorant Garamond', serif",
                "body_font": "'Space Grotesk', sans-serif",
            },
            "content": {
                "hero_eyebrow": "Northstar Analytics",
                "hero_title": "Find product lift",
                "hero_subtitle": "A cleaner way to see what really drives adoption.",
                "cta_text": "Start now",
                "cta_note": "Launch a sharper concept quickly.",
                "features": [
                    {"title": "Growth dashboard", "desc": "See adoption, retention, and revenue together."},
                    {"title": "Workflow automation", "desc": "Reduce the manual work behind each launch."},
                    {"title": "Team alignment", "desc": "Share one clear source of product truth."},
                ],
                "projects": [
                    {"title": "Northstar Mobile", "desc": "A mobile analytics refresh.", "meta": "Product design"},
                    {"title": "Signal Board", "desc": "A cleaner metrics story.", "meta": "Dashboard"},
                    {"title": "Launch Pulse", "desc": "A growth reporting layer.", "meta": "Growth"},
                ],
                "capabilities": [
                    {"title": "Workflow systems", "desc": "Ship repeatable product operations."},
                    {"title": "Brand design", "desc": "Make the interface feel authored."},
                    {"title": "Growth reporting", "desc": "Tie decisions to real performance."},
                ],
            },
            "visuals": visuals,
        }

    def test_preview_frame_renders_visual_assets(self):
        visuals = {
            "hero_image": {
                "url": "https://source.unsplash.com/featured/1600x900/?analytics,product",
                "query": "analytics,product",
                "alt": "Analytics Product visual for hero section",
                "source": "unsplash-source",
            },
            "project_images": [
                {
                    "url": "https://source.unsplash.com/featured/800x600/?dashboard,product",
                    "query": "dashboard,product",
                    "alt": "Northstar Mobile project preview",
                    "source": "unsplash-source",
                },
                {
                    "url": "https://source.unsplash.com/featured/800x600/?metrics,signal",
                    "query": "metrics,signal",
                    "alt": "Signal Board project preview",
                    "source": "unsplash-source",
                },
            ],
            "feature_icons": [
                {
                    "library": "lucide",
                    "name": "bar-chart-3",
                    "url": "https://cdn.jsdelivr.net/npm/lucide-static@0.577.0/icons/bar-chart-3.svg",
                    "label": "Bar Chart 3",
                },
                {
                    "library": "lucide",
                    "name": "workflow",
                    "url": "https://cdn.jsdelivr.net/npm/lucide-static@0.577.0/icons/workflow.svg",
                    "label": "Workflow",
                },
                {
                    "library": "lucide",
                    "name": "users",
                    "url": "https://cdn.jsdelivr.net/npm/lucide-static@0.577.0/icons/users.svg",
                    "label": "Users",
                },
            ],
            "capability_icons": [
                {
                    "library": "lucide",
                    "name": "workflow",
                    "url": "https://cdn.jsdelivr.net/npm/lucide-static@0.577.0/icons/workflow.svg",
                    "label": "Workflow",
                },
                {
                    "library": "lucide",
                    "name": "palette",
                    "url": "https://cdn.jsdelivr.net/npm/lucide-static@0.577.0/icons/palette.svg",
                    "label": "Palette",
                },
                {
                    "library": "lucide",
                    "name": "bar-chart-3",
                    "url": "https://cdn.jsdelivr.net/npm/lucide-static@0.577.0/icons/bar-chart-3.svg",
                    "label": "Bar Chart 3",
                },
            ],
        }

        with self.app.test_request_context("/"):
            body = render_template(
                "preview_frame.html",
                page_title="Northstar",
                brief=self._brief(),
                selected_variant=self._selected_variant(visuals),
                studio_mode=False,
                consumer_mode=True,
            )

        self.assertIn('data-visual-role="hero-image"', body)
        self.assertIn('data-visual-role="project-image"', body)
        self.assertIn("source.unsplash.com/featured/1600x900/?analytics,product", body)
        self.assertIn("lucide-static@0.577.0/icons/workflow.svg", body)
        self.assertIn("lucide-static@0.577.0/icons/palette.svg", body)

    def test_preview_frame_renders_without_visuals(self):
        with self.app.test_request_context("/"):
            body = render_template(
                "preview_frame.html",
                page_title="Northstar",
                brief=self._brief(),
                selected_variant=self._selected_variant({}),
                studio_mode=False,
                consumer_mode=True,
            )

        self.assertIn("Find product lift", body)
        self.assertNotIn('data-visual-role="hero-image"', body)


if __name__ == "__main__":
    unittest.main()
