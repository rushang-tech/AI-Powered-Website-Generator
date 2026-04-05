import unittest

from app.services.ai_engine import TEMPLATE_CATALOG, THEME_MAP
from app.services.taste_engine import build_render_plan, build_render_variants, normalize_brief


class TasteEngineTests(unittest.TestCase):
    def test_builds_three_variants(self):
        plans = build_render_variants(
            "Create a portfolio for a freelance photographer showcasing recent projects.",
            brief={
                "goal": "Create a portfolio for a freelance photographer showcasing recent projects.",
                "audience": "Art directors and clients",
                "brand_tone": "Confident and editorial",
                "content_density": "balanced",
                "motion_level": "moderate",
            },
            model=None,
            theme_catalog=THEME_MAP,
            template_catalog=TEMPLATE_CATALOG,
        )
        self.assertEqual(len(plans), 3)
        self.assertTrue(all(plan.template_key == "portfolio" for plan in plans))

    def test_variants_differ_in_layout_or_art_direction(self):
        plans = build_render_variants(
            "A startup landing page for founders",
            brief={
                "goal": "A startup landing page for founders",
                "audience": "Seed-stage founders",
                "brand_tone": "Bold and warm",
                "content_density": "balanced",
                "motion_level": "moderate",
            },
            model=None,
            theme_catalog=THEME_MAP,
            template_catalog=TEMPLATE_CATALOG,
        )
        identities = {(plan.layout_mode, plan.art_direction, plan.density, plan.motion_level) for plan in plans}
        self.assertGreaterEqual(len(identities), 2)
        self.assertGreaterEqual(len({plan.art_direction for plan in plans}), 3)

    def test_low_confidence_falls_back_to_safe_profile(self):
        plan = build_render_plan(
            "hello",
            brief={
                "goal": "hello",
                "audience": "General audience",
                "brand_tone": "Clear and modern",
                "content_density": "balanced",
                "motion_level": "moderate",
            },
            model=None,
            theme_catalog=THEME_MAP,
            template_catalog=TEMPLATE_CATALOG,
        )
        self.assertEqual(plan.template_key, "landing")
        self.assertGreaterEqual(plan.confidence, 0.55)
        self.assertIn(plan.art_direction, THEME_MAP.keys())

    def test_brief_fields_influence_layout_and_art_direction(self):
        plans = build_render_variants(
            "Launch page",
            brief={
                "goal": "Launch page for a luxury skincare product",
                "audience": "High-intent premium shoppers",
                "brand_tone": "Elegant, refined, premium",
                "content_density": "dense",
                "motion_level": "calm",
            },
            model=None,
            theme_catalog=THEME_MAP,
            template_catalog=TEMPLATE_CATALOG,
        )
        primary = plans[0]
        self.assertEqual(primary.template_key, "product")
        self.assertEqual(primary.art_direction, "luxury_serif")
        self.assertEqual(primary.density, "dense")
        self.assertEqual(primary.motion_level, "calm")

    def test_contextual_art_biases_reduce_same_theme_fallbacks(self):
        healthcare = build_render_plan(
            "Build a website for a pediatric clinic",
            brief={
                "goal": "Build a website for a pediatric clinic",
                "audience": "Parents seeking care",
                "brand_tone": "Clear and trustworthy",
                "content_density": "balanced",
                "motion_level": "calm",
            },
            model=None,
            theme_catalog=THEME_MAP,
            template_catalog=TEMPLATE_CATALOG,
        )
        creative = build_render_plan(
            "Create a portfolio for a tattoo artist",
            brief={
                "goal": "Create a portfolio for a tattoo artist",
                "audience": "Collectors and collaborators",
                "brand_tone": "Direct and confident",
                "content_density": "balanced",
                "motion_level": "moderate",
            },
            model=None,
            theme_catalog=THEME_MAP,
            template_catalog=TEMPLATE_CATALOG,
        )
        self.assertEqual(healthcare.art_direction, "warm_gradient")
        self.assertEqual(creative.art_direction, "brutalist_poster")

    def test_bakery_prompts_do_not_fall_back_to_general_industry(self):
        plan = build_render_plan(
            "Create a website for a neighborhood bakery with fresh bread, pastries, and coffee.",
            brief={
                "goal": "Create a website for a neighborhood bakery with fresh bread, pastries, and coffee.",
                "audience": "Local walk-in customers and custom cake buyers",
                "brand_tone": "Warm and inviting",
                "content_density": "balanced",
                "motion_level": "calm",
            },
            model=None,
            theme_catalog=THEME_MAP,
            template_catalog=TEMPLATE_CATALOG,
        )
        self.assertEqual(plan.industry, "retail")
        self.assertEqual(plan.motion_level, "calm")

    def test_swiss_minimal_prompts_can_route_to_mono_signal(self):
        plan = build_render_plan(
            "Build a black and white Swiss grid website for a minimalist SaaS launch.",
            brief={
                "goal": "Build a black and white Swiss grid website for a minimalist SaaS launch.",
                "audience": "Design-conscious product teams",
                "brand_tone": "Precise and minimal",
                "content_density": "balanced",
                "motion_level": "calm",
            },
            model=None,
            theme_catalog=THEME_MAP,
            template_catalog=TEMPLATE_CATALOG,
        )
        self.assertEqual(plan.art_direction, "mono_signal")

    def test_product_plans_include_media_direction_for_mockups(self):
        plan = build_render_plan(
            "Create a SaaS launch page with pricing, dashboard previews, and workflow screenshots.",
            brief={
                "goal": "Create a SaaS launch page with pricing, dashboard previews, and workflow screenshots.",
                "audience": "Operations teams evaluating software",
                "brand_tone": "Clear, modern, product-focused",
                "content_density": "balanced",
                "motion_level": "moderate",
            },
            model=None,
            theme_catalog=THEME_MAP,
            template_catalog=TEMPLATE_CATALOG,
        )
        self.assertEqual(plan.template_key, "product")
        self.assertEqual(plan.template_file, "generated/product.html")
        self.assertEqual(plan.media_direction, "interface_mockups")
        self.assertEqual(plan.shell_variant, "workflow_console")
        self.assertEqual(plan.navigation_style, "product_tabs")

    def test_normalize_brief_preserves_brand_assets_and_icon_style(self):
        brief = normalize_brief(
            "Create a landing page",
            {
                "goal": "Create a landing page",
                "audience": "Founders",
                "brand_tone": "Clear and modern",
                "content_density": "balanced",
                "motion_level": "moderate",
                "brand_assets": [
                    {
                        "id": "brand-asset-1",
                        "name": "logo.svg",
                        "alt": "Logo",
                        "mime_type": "image/svg+xml",
                        "data_url": "data:image/svg+xml;base64,PHN2Zz48L3N2Zz4=",
                    }
                ],
                "icon_style": "Rounded interface icons",
            },
        )
        self.assertEqual(brief.icon_style, "Rounded interface icons")
        self.assertEqual(len(brief.brand_assets), 1)
        self.assertEqual(brief.brand_assets[0]["name"], "logo.svg")


if __name__ == "__main__":
    unittest.main()
