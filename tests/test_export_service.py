import unittest

from app import create_app
from app.services.ai_engine import generate_project_manifest
from app.services.ai_provider import AIProviderUnavailableError
from app.services.contracts import ProjectManifest
from app.services.export_service import render_export_site


def _manifest() -> ProjectManifest:
    return ProjectManifest.from_dict(
        {
            "preview_id": "preview-export-1",
            "prompt": "Create a polished SaaS product page",
            "brief": {
                "goal": "Create a polished SaaS product page",
                "audience": "Operations teams",
                "brand_tone": "Clear and modern",
                "content_density": "balanced",
                "motion_level": "moderate",
                "name": "Northstar OS",
                "notes": "Lean into stronger visual rhythm and product proof.",
                "prompt": "Create a polished SaaS product page",
                "brand_assets": [],
                "icon_style": "",
            },
            "selected_variant_id": "variant-1",
            "variants": [
                {
                    "variant_id": "variant-1",
                    "label": "Variant 1",
                    "summary": "A routed product direction.",
                    "render_plan": {
                        "template_key": "product",
                        "template_file": "generated/product.html",
                        "theme_key": "modern_editorial",
                        "art_direction": "modern_editorial",
                        "layout_mode": "feature_scroll",
                        "density": "balanced",
                        "motion_level": "moderate",
                        "section_order": ["hero", "features", "pricing", "proof", "cta"],
                        "section_visibility": {
                            "hero": True,
                            "features": True,
                            "pricing": True,
                            "proof": True,
                            "cta": True,
                        },
                        "hero_variant": "feature-led",
                        "industry": "technology",
                        "vibe": "clean",
                        "keywords": ["saas", "workflow", "dashboard"],
                        "confidence": 0.86,
                        "reasons": ["test payload"],
                        "slot_schema": {
                            "text_slots": [
                                "hero_eyebrow",
                                "hero_title",
                                "hero_subtitle",
                                "price_badge",
                                "cta_text",
                                "cta_note",
                                "features_title",
                                "features_intro",
                                "pricing_title",
                                "pricing_intro",
                                "stat_1_value",
                                "stat_1_label",
                                "stat_2_value",
                                "stat_2_label",
                                "proof_quote",
                                "proof_author",
                            ],
                            "list_slots": {
                                "features": {"item_fields": ["title", "desc"], "min_items": 3, "max_items": 6},
                                "offers": {"item_fields": ["title", "desc", "meta"], "min_items": 3, "max_items": 4},
                            },
                        },
                        "media_direction": "interface_mockups",
                        "shell_variant": "workflow_console",
                        "navigation_style": "product_tabs",
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
                        "hero_eyebrow": "Northstar OS",
                        "hero_title": "Run operations without the scramble",
                        "hero_subtitle": "See projects, approvals, and blockers in one sharper product flow.",
                        "price_badge": "Plans from $49/mo",
                        "cta_text": "Book demo",
                        "cta_note": "A cleaner launch story with space for UI proof.",
                        "features_title": "Where the workflow gets clearer",
                        "features_intro": "Each block should feel ready for a product screenshot or supporting visual.",
                        "pricing_title": "Choose the rollout pace",
                        "pricing_intro": "Tiers stay simple so the product can do the convincing.",
                        "stat_1_value": "42%",
                        "stat_1_label": "Fewer status meetings",
                        "stat_2_value": "3.1x",
                        "stat_2_label": "Faster approvals",
                        "proof_quote": "The story feels product-led before you even reach the pricing.",
                        "proof_author": "Operations lead",
                        "features": [
                            {"title": "Signal-first dashboard", "desc": "Bring blockers and priorities into one visual control room."},
                            {"title": "Shared approvals", "desc": "Give every step a clear owner and next action."},
                            {"title": "Rollout visibility", "desc": "Track launches, dependencies, and deadlines without spreadsheet drift."},
                        ],
                        "offers": [
                            {"title": "Starter", "desc": "For lean teams replacing manual status threads.", "meta": "$49"},
                            {"title": "Growth", "desc": "For multi-team planning with stronger reporting and review flows.", "meta": "$129"},
                            {"title": "Scale", "desc": "For larger orgs that need governance, auditability, and rollout clarity.", "meta": "$249"},
                        ],
                    },
                    "validation": {"valid": True, "errors": [], "warnings": [], "fallback_used": False},
                }
            ],
            "statuses": [],
        }
    )


class ExportServiceTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            }
        )

    def test_render_export_site_includes_visual_placeholders(self):
        manifest = _manifest()
        with self.app.test_request_context("/"):
            html, _, selected_variant = render_export_site(manifest)

        self.assertEqual(selected_variant["render_plan"]["media_direction"], "interface_mockups")
        self.assertEqual(selected_variant["render_plan"]["template_file"], "generated/product.html")
        self.assertIn("media-interface_mockups", html)
        self.assertIn("shell-workflow_console", html)
        self.assertIn("product-dashboard-main", html)
        self.assertIn("product-feature-step", html)
        self.assertIn("product-pricing-grid", html)

    def test_render_generated_landing_and_portfolio_shells(self):
        class _FailingProvider:
            def generate_text(self, prompt: str) -> str:
                raise AIProviderUnavailableError("offline")

            def generate_json(self, prompt: str) -> dict[str, object]:
                raise AIProviderUnavailableError("offline")

        cases = [
            (
                "Build a startup landing page for founders",
                {
                    "goal": "Build a startup landing page for founders",
                    "audience": "Seed-stage founders",
                    "brand_tone": "Confident and clear",
                    "content_density": "balanced",
                    "motion_level": "moderate",
                    "name": "Northstar",
                },
                "generated/landing.html",
                "landing-preview",
            ),
            (
                "Create a portfolio for a freelance creative studio",
                {
                    "goal": "Create a portfolio for a freelance creative studio",
                    "audience": "Creative directors and collaborators",
                    "brand_tone": "Editorial and refined",
                    "content_density": "balanced",
                    "motion_level": "calm",
                    "name": "Aster Studio",
                },
                "generated/portfolio.html",
                "portfolio-preview",
            ),
        ]

        with self.app.test_request_context("/"):
            for prompt, brief, template_file, shell_class in cases:
                manifest = generate_project_manifest(prompt, brief=brief, provider=_FailingProvider())
                html, _, selected_variant = render_export_site(manifest)
                self.assertEqual(selected_variant["render_plan"]["template_file"], template_file)
                self.assertIn(shell_class, html)


if __name__ == "__main__":
    unittest.main()
