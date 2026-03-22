import json
import os
import tempfile
import unittest
from zipfile import ZipFile

from app import create_app
from app.extensions import db
from app.services.contracts import ProjectManifest
from app.services.export_service import build_export_bundle


class ExportServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = os.path.join(self.temp_dir.name, "export-service-test.db")
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

    def test_build_export_bundle_resolves_visuals_into_manifest_json(self):
        payload = {
            "preview_id": "preview-export-visuals",
            "prompt": "Launch a landing page for a mart e commerce",
            "brief": {
                "goal": "Launch a landing page for a mart e commerce",
                "audience": "Seed-stage founders and product leads",
                "brand_tone": "Bold, clear, confident",
                "content_density": "balanced",
                "motion_level": "moderate",
                "name": "small mart",
                "notes": "Lead with proof and include a strong pricing narrative.",
                "prompt": "Launch a landing page for a mart e commerce",
                "brand_assets": [],
                "icon_style": "",
            },
            "selected_variant_id": "variant-1",
            "variants": [
                {
                    "variant_id": "variant-1",
                    "label": "Variant 1: Feature Scroll",
                    "summary": "Modern Editorial with feature scroll structure.",
                    "render_plan": {
                        "template_key": "landing",
                        "template_file": "generated/site_builder.html",
                        "theme_key": "modern_editorial",
                        "art_direction": "modern_editorial",
                        "layout_mode": "feature_scroll",
                        "density": "balanced",
                        "motion_level": "moderate",
                        "section_order": ["hero", "proof", "features", "cta"],
                        "section_visibility": {"hero": True, "proof": True, "features": True, "cta": True},
                        "hero_variant": "immersive",
                        "industry": "e-commerce",
                        "vibe": "bold",
                        "keywords": ["mart", "ecommerce", "launch"],
                        "confidence": 0.95,
                        "reasons": ["test payload"],
                        "slot_schema": {
                            "text_slots": [
                                "hero_eyebrow",
                                "hero_title",
                                "hero_subtitle",
                                "cta_text",
                                "cta_note",
                                "proof_quote",
                                "proof_author",
                            ],
                            "list_slots": {
                                "features": {"item_fields": ["title", "desc"], "min_items": 3, "max_items": 6},
                            },
                        },
                    },
                    "content": {
                        "hero_eyebrow": "Bold. Clear. Confident.",
                        "hero_title": "Small Mart: E-commerce, Reconsidered.",
                        "hero_subtitle": "Launch with a distinct point of view.",
                        "cta_text": "Launch Your Mart",
                        "cta_note": "Focus on the core offer. Details build trust.",
                        "proof_quote": "Finally, an e-commerce platform that feels as deliberate as our product.",
                        "proof_author": "Seed-stage Founder",
                        "features": [
                            {"title": "Curated Product Presentation", "desc": "Showcase your offerings."},
                            {"title": "Conversion-Optimized Flow", "desc": "Guide customers to purchase."},
                            {"title": "Flexible Pricing Architect", "desc": "Communicate pricing with clarity."},
                        ],
                    },
                    "validation": {"valid": True, "errors": [], "warnings": [], "fallback_used": False},
                    "theme": {"key": "modern_editorial", "name": "Modern Editorial"},
                    "content_overrides": {},
                    "layout_overrides": {},
                    "edited_nodes": [],
                }
            ],
            "statuses": [],
        }
        manifest = ProjectManifest.from_dict(payload)

        with self.app.app_context():
            archive, _filename = build_export_bundle(manifest)

        with ZipFile(archive) as zip_file:
            exported_manifest = json.loads(zip_file.read("manifest.json"))
            exported_html = zip_file.read("index.html").decode("utf-8")
            contact_html = zip_file.read("contact.html").decode("utf-8")

        variant = exported_manifest["variants"][0]
        self.assertIn("visuals", variant)
        self.assertEqual(variant["visuals"]["hero_image"]["source"], "unsplash-source")
        self.assertTrue(variant["visuals"]["feature_icons"])
        self.assertIn("data-visual-role=\"hero-image\"", exported_html)
        self.assertIn("Current page", contact_html)


if __name__ == "__main__":
    unittest.main()
