import unittest

from app.services.ai_engine import TEMPLATE_CATALOG, THEME_MAP
from app.services.taste_engine import build_render_plan, build_render_variants


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


if __name__ == "__main__":
    unittest.main()
