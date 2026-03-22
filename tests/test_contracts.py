import unittest

from app.services.contracts import ProjectManifest


class ContractTests(unittest.TestCase):
    def test_project_manifest_round_trips_variant_visuals(self):
        payload = {
            "preview_id": "preview-visuals",
            "prompt": "A luxury hotel website",
            "brief": {
                "goal": "A luxury hotel website",
                "audience": "Travelers",
                "brand_tone": "Elegant",
                "content_density": "balanced",
                "motion_level": "moderate",
                "name": "Aurora House",
                "notes": "Lead with interiors.",
                "prompt": "A luxury hotel website",
                "brand_assets": [],
                "icon_style": "Rounded editorial icons",
            },
            "selected_variant_id": "variant-1",
            "variants": [
                {
                    "variant_id": "variant-1",
                    "label": "Variant 1",
                    "summary": "A routed design direction.",
                    "render_plan": {
                        "template_key": "landing",
                        "template_file": "generated/site_builder.html",
                        "theme_key": "luxury_serif",
                        "art_direction": "luxury_serif",
                        "layout_mode": "split_hero",
                        "density": "balanced",
                        "motion_level": "moderate",
                        "section_order": ["hero", "features", "cta"],
                        "section_visibility": {"hero": True, "features": True, "cta": True},
                        "hero_variant": "split",
                        "industry": "hospitality",
                        "vibe": "editorial",
                        "keywords": ["luxury", "hotel"],
                        "confidence": 0.9,
                        "reasons": ["test payload"],
                        "slot_schema": {
                            "text_slots": ["hero_title", "hero_subtitle", "cta_text", "cta_note"],
                            "list_slots": {
                                "features": {"item_fields": ["title", "desc"], "min_items": 3, "max_items": 6},
                            },
                        },
                    },
                    "content": {
                        "hero_title": "Stay somewhere worth remembering",
                        "hero_subtitle": "A premium booking experience.",
                        "cta_text": "Book now",
                        "cta_note": "Plan your arrival.",
                        "features": [
                            {"title": "Editorial booking", "desc": "Move from browse to booking fast."},
                            {"title": "Guest analytics", "desc": "See demand and revenue clearly."},
                            {"title": "Suite stories", "desc": "Make rooms feel distinct."},
                        ],
                    },
                    "validation": {"valid": True, "errors": [], "warnings": [], "fallback_used": False},
                    "theme": {"name": "Luxury Serif"},
                    "visuals": {
                        "hero_image": {
                            "url": "https://source.unsplash.com/featured/1600x900/?luxury,hotel",
                            "query": "luxury,hotel",
                            "alt": "Luxury Hotel visual for hero section",
                            "source": "unsplash-source",
                        },
                        "project_images": [],
                        "feature_icons": [
                            {
                                "library": "lucide",
                                "name": "sparkles",
                                "url": "https://cdn.jsdelivr.net/npm/lucide-static@0.577.0/icons/sparkles.svg",
                                "label": "Sparkles",
                            }
                        ],
                        "capability_icons": [],
                        "section_media": {
                            "projects": [
                                {
                                    "url": "https://source.unsplash.com/featured/900x720/?suite,interior",
                                    "query": "suite,interior",
                                    "alt": "Suite Interior project preview",
                                    "source": "unsplash-source",
                                }
                            ]
                        },
                    },
                }
            ],
            "statuses": [],
        }

        manifest = ProjectManifest.from_dict(payload)

        self.assertEqual(manifest.variants[0].visuals["hero_image"]["query"], "luxury,hotel")
        self.assertEqual(manifest.variants[0].visuals["section_media"]["projects"][0]["query"], "suite,interior")
        self.assertEqual(manifest.variants[0].render_plan.primary_page_slug, "home")
        self.assertTrue(manifest.variants[0].render_plan.pages)
        self.assertEqual(manifest.variants[0].render_plan.pages[0].slug, "home")
        self.assertEqual(
            manifest.to_dict()["variants"][0]["visuals"]["feature_icons"][0]["name"],
            "sparkles",
        )


if __name__ == "__main__":
    unittest.main()
