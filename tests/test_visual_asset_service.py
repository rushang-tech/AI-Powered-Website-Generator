import unittest

from app.services.taste_engine import BriefInput, RenderPlan
from app.services.visual_asset_service import (
    build_variant_visuals,
    extract_visual_keywords,
    resolve_lucide_icon,
    sanitize_visual_query,
)


class VisualAssetServiceTests(unittest.TestCase):
    def _brief(self) -> BriefInput:
        return BriefInput(
            goal="Launch a luxury hotel website with strong booking momentum",
            audience="Design-conscious travelers",
            brand_tone="Elegant, warm, premium",
            content_density="balanced",
            motion_level="moderate",
            name="Aurora House",
            notes="Lead with interiors, hospitality, and a polished editorial feel.",
            prompt="A luxury hotel booking website",
            brand_assets=[],
            icon_style="Rounded editorial product icons",
        )

    def _plan(self) -> RenderPlan:
        return RenderPlan(
            template_key="landing",
            template_file="generated/site_builder.html",
            theme_key="luxury_serif",
            art_direction="luxury_serif",
            layout_mode="split_hero",
            density="balanced",
            motion_level="moderate",
            section_order=["hero", "features", "projects", "capabilities", "cta"],
            section_visibility={"hero": True, "features": True, "projects": True, "capabilities": True, "cta": True},
            hero_variant="split",
            industry="hospitality",
            vibe="editorial",
            keywords=["luxury", "hotel", "interior"],
            confidence=0.9,
            reasons=["test"],
            slot_schema={
                "text_slots": ["hero_title", "hero_subtitle", "cta_text", "cta_note"],
                "list_slots": {
                    "features": {"item_fields": ["title", "desc"], "min_items": 3, "max_items": 6},
                    "projects": {"item_fields": ["title", "desc", "meta"], "min_items": 3, "max_items": 6},
                    "capabilities": {"item_fields": ["title", "desc"], "min_items": 3, "max_items": 6},
                },
            },
        )

    def test_extract_visual_keywords_prioritizes_weighted_terms(self):
        keywords = extract_visual_keywords(
            ("luxury hotel retreat", 3.0),
            ("hotel spa stay", 1.0),
            ("the website and page", 5.0),
        )

        self.assertEqual(keywords[:3], ["hotel", "luxury", "retreat"])
        self.assertNotIn("website", keywords)

    def test_sanitize_visual_query_deduplicates_and_limits_keywords(self):
        query = sanitize_visual_query(["Luxury", "Hotel", "hotel", "spa!", "design", "extra"])

        self.assertEqual(query, "luxury,hotel,spa,design")

    def test_resolve_lucide_icon_maps_semantic_terms(self):
        icon = resolve_lucide_icon("analytics growth dashboard", icon_style="sharp monochrome")

        self.assertEqual(icon["name"], "bar-chart-3")
        self.assertIn("lucide-static@0.577.0", icon["url"])

    def test_build_variant_visuals_returns_expected_shapes(self):
        visuals = build_variant_visuals(
            brief=self._brief(),
            render_plan=self._plan(),
            content={
                "hero_title": "Luxury hotel stories worth booking",
                "hero_subtitle": "Show interiors, hospitality, and calm confidence.",
                "features": [
                    {"title": "Editorial Booking Flow", "desc": "A premium reservation path with fast decisions."},
                    {"title": "Guest Analytics", "desc": "Track occupancy and revenue in one clean dashboard."},
                ],
                "projects": [
                    {"title": "Penthouse Suite", "desc": "A warm interior story.", "meta": "Interior design"},
                ],
                "capabilities": [
                    {"title": "Workflow Automation", "desc": "Keep ops and guest requests moving."},
                ],
            },
        )

        self.assertEqual(visuals["hero_image"]["source"], "unsplash-source")
        self.assertIn("source.unsplash.com/featured/1600x900", visuals["hero_image"]["url"])
        self.assertIn("luxury", visuals["hero_image"]["query"])
        self.assertEqual(len(visuals["project_images"]), 1)
        self.assertIn("source.unsplash.com/featured/800x600", visuals["project_images"][0]["url"])
        self.assertEqual(visuals["feature_icons"][0]["library"], "lucide")
        self.assertEqual(visuals["capability_icons"][0]["name"], "workflow")
        self.assertIn("section_media", visuals)
        self.assertIn("projects", visuals["section_media"])

    def test_build_variant_visuals_generates_section_media_for_storefront_lists(self):
        store_plan = RenderPlan(
            template_key="store",
            template_file="generated/store_builder.html",
            theme_key="luxury_serif",
            art_direction="luxury_serif",
            layout_mode="editorial_lookbook",
            density="balanced",
            motion_level="moderate",
            section_order=["hero", "collections", "products", "proof", "cta"],
            section_visibility={"hero": True, "collections": True, "products": True, "proof": True, "cta": True},
            hero_variant="lookbook",
            industry="retail",
            vibe="premium",
            keywords=["store", "collection", "retail"],
            confidence=0.92,
            reasons=["test"],
            slot_schema={
                "text_slots": ["hero_title", "hero_subtitle", "cta_text", "cta_note"],
                "list_slots": {
                    "collections": {"item_fields": ["title", "desc", "meta"], "min_items": 2, "max_items": 4},
                    "products": {"item_fields": ["title", "desc", "meta"], "min_items": 6, "max_items": 8},
                },
            },
        )
        visuals = build_variant_visuals(
            brief=self._brief(),
            render_plan=store_plan,
            content={
                "hero_title": "A storefront worth opening first",
                "hero_subtitle": "Collections and products built to browse.",
                "collections": [
                    {"title": "New season", "desc": "Fresh arrivals.", "meta": "Collection"},
                    {"title": "Best sellers", "desc": "Customer favorites.", "meta": "Popular"},
                ],
                "products": [
                    {"title": "Studio jacket", "desc": "Editorial outerwear.", "meta": "$68"},
                    {"title": "Signal tee", "desc": "Daily uniform.", "meta": "$34"},
                    {"title": "Field tote", "desc": "Structured carry.", "meta": "$52"},
                    {"title": "Canvas cap", "desc": "Lightweight staple.", "meta": "$26"},
                    {"title": "Weekend set", "desc": "Bundled offer.", "meta": "$84"},
                    {"title": "Archive hoodie", "desc": "Heavier statement piece.", "meta": "$78"},
                ],
            },
        )

        self.assertEqual(len(visuals["section_media"]["collections"]), 2)
        self.assertEqual(len(visuals["section_media"]["products"]), 6)
        self.assertTrue(all("source.unsplash.com/featured/900x1080" in item["url"] for item in visuals["section_media"]["products"]))


if __name__ == "__main__":
    unittest.main()
