import os
import tempfile
import unittest

from flask import render_template

from app import create_app
from app.extensions import db


class ArchetypeRenderingTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = os.path.join(self.temp_dir.name, "archetype-rendering.db")
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
            "goal": "A generated website",
            "audience": "Design-conscious buyers",
            "brand_tone": "Clear, modern, premium",
            "content_density": "balanced",
            "motion_level": "moderate",
            "name": "Northstar",
            "notes": "Use strong visual hierarchy.",
            "prompt": "A generated website",
            "brand_assets": [],
            "icon_style": "Rounded interface icons",
        }

    def _theme(self) -> dict[str, object]:
        return {
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
        }

    def _render(self, selected_variant: dict[str, object]) -> str:
        with self.app.test_request_context("/"):
            return render_template(
                "preview_frame.html",
                page_title="Northstar",
                brief=self._brief(),
                selected_variant=selected_variant,
                studio_mode=False,
                consumer_mode=True,
            )

    def test_store_builder_renders_multi_image_storefront(self):
        body = self._render(
            {
                "variant_id": "variant-store",
                "label": "Store Variant",
                "summary": "Editorial storefront.",
                "render_plan": {
                    "template_key": "store",
                    "template_file": "generated/store_builder.html",
                    "theme_key": "modern_editorial",
                    "art_direction": "modern_editorial",
                    "layout_mode": "editorial_lookbook",
                    "density": "balanced",
                    "motion_level": "moderate",
                    "section_order": ["hero", "collections", "products", "proof", "cta"],
                    "section_visibility": {"hero": True, "collections": True, "products": True, "proof": True, "cta": True},
                    "hero_variant": "lookbook",
                    "industry": "retail",
                    "vibe": "premium",
                    "keywords": ["store", "retail", "collection"],
                    "confidence": 0.9,
                    "reasons": ["test payload"],
                    "slot_schema": {"text_slots": [], "list_slots": {}},
                },
                "theme": self._theme(),
                "content": {
                    "hero_eyebrow": "Northstar Mart",
                    "hero_title": "A storefront worth opening first",
                    "hero_subtitle": "Collections and products arranged like a real shop.",
                    "cta_text": "Shop now",
                    "cta_note": "Browse the new drop.",
                    "collections_title": "Collections",
                    "collections_intro": "Start with the edit.",
                    "products_title": "Products",
                    "products_intro": "Shop the grid.",
                    "proof_quote": "It finally feels like a real store.",
                    "proof_author": "Launch customer",
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
                        {"title": "Archive hoodie", "desc": "Statement piece.", "meta": "$78"},
                    ],
                },
                "visuals": {
                    "hero_image": {
                        "url": "https://source.unsplash.com/featured/1600x900/?store,retail",
                        "query": "store,retail",
                        "alt": "Store Retail visual for hero section",
                        "source": "unsplash-source",
                    },
                    "project_images": [],
                    "feature_icons": [],
                    "capability_icons": [],
                    "section_media": {
                        "collections": [
                            {"url": "https://source.unsplash.com/featured/1200x900/?fashion,collection", "query": "fashion,collection", "alt": "New season collection feature", "source": "unsplash-source"},
                            {"url": "https://source.unsplash.com/featured/1200x900/?retail,drop", "query": "retail,drop", "alt": "Best sellers collection feature", "source": "unsplash-source"},
                        ],
                        "products": [
                            {"url": "https://source.unsplash.com/featured/900x1080/?jacket,fashion", "query": "jacket,fashion", "alt": "Studio jacket product preview", "source": "unsplash-source"},
                            {"url": "https://source.unsplash.com/featured/900x1080/?shirt,retail", "query": "shirt,retail", "alt": "Signal tee product preview", "source": "unsplash-source"},
                            {"url": "https://source.unsplash.com/featured/900x1080/?bag,canvas", "query": "bag,canvas", "alt": "Field tote product preview", "source": "unsplash-source"},
                            {"url": "https://source.unsplash.com/featured/900x1080/?cap,streetwear", "query": "cap,streetwear", "alt": "Canvas cap product preview", "source": "unsplash-source"},
                            {"url": "https://source.unsplash.com/featured/900x1080/?set,apparel", "query": "set,apparel", "alt": "Weekend set product preview", "source": "unsplash-source"},
                            {"url": "https://source.unsplash.com/featured/900x1080/?hoodie,archive", "query": "hoodie,archive", "alt": "Archive hoodie product preview", "source": "unsplash-source"},
                        ],
                    },
                },
            }
        )

        self.assertIn('data-visual-role="hero-image"', body)
        self.assertIn('data-visual-role="collection-image"', body)
        self.assertGreaterEqual(body.count('data-visual-role="product-image"'), 6)
        self.assertIn("store-product-grid", body)

    def test_saas_builder_renders_workflow_media_and_icons(self):
        body = self._render(
            {
                "variant_id": "variant-saas",
                "label": "SaaS Variant",
                "summary": "Workflow-first SaaS.",
                "render_plan": {
                    "template_key": "saas",
                    "template_file": "generated/saas_builder.html",
                    "theme_key": "cyber_signal",
                    "art_direction": "cyber_signal",
                    "layout_mode": "workflow_first",
                    "density": "balanced",
                    "motion_level": "moderate",
                    "section_order": ["hero", "workflows", "features", "pricing", "proof", "cta"],
                    "section_visibility": {"hero": True, "workflows": True, "features": True, "pricing": True, "proof": True, "cta": True},
                    "hero_variant": "workflow",
                    "industry": "technology",
                    "vibe": "futuristic",
                    "keywords": ["saas", "workflow", "copilot"],
                    "confidence": 0.91,
                    "reasons": ["test payload"],
                    "slot_schema": {"text_slots": [], "list_slots": {}},
                },
                "theme": self._theme(),
                "content": {
                    "hero_eyebrow": "Northstar Copilot",
                    "hero_title": "See the workflow before the sale",
                    "hero_subtitle": "Make the product feel tangible in the first scroll.",
                    "cta_text": "Start trial",
                    "cta_note": "Bring your team into one flow.",
                    "workflows_title": "Workflow scenes",
                    "workflows_intro": "Show how the product moves.",
                    "features_title": "Highlights",
                    "features_intro": "Short reasons to care.",
                    "pricing_title": "Plans",
                    "pricing_intro": "Choose the fit.",
                    "proof_quote": "The workflows are doing the selling.",
                    "proof_author": "Beta team",
                    "workflows": [
                        {"title": "Capture the signal", "desc": "Collect the important inputs.", "meta": "Step 01"},
                        {"title": "Align the team", "desc": "Reduce handoff friction.", "meta": "Step 02"},
                        {"title": "Ship with proof", "desc": "Make outcomes visible.", "meta": "Step 03"},
                    ],
                    "features": [
                        {"title": "Workflow automation", "desc": "Move faster with less manual overhead."},
                        {"title": "Shared dashboards", "desc": "One operating view for the whole team."},
                        {"title": "Team alignment", "desc": "Keep decisions connected to the plan."},
                    ],
                    "offers": [
                        {"title": "Starter", "desc": "One team workspace.", "meta": "$29/mo"},
                        {"title": "Growth", "desc": "Cross-functional rollout.", "meta": "$79/mo"},
                        {"title": "Scale", "desc": "Multi-team operations.", "meta": "$149/mo"},
                    ],
                },
                "visuals": {
                    "hero_image": {"url": "https://source.unsplash.com/featured/1600x900/?dashboard,product", "query": "dashboard,product", "alt": "Dashboard Product visual for hero section", "source": "unsplash-source"},
                    "project_images": [],
                    "feature_icons": [
                        {"library": "lucide", "name": "workflow", "url": "https://cdn.jsdelivr.net/npm/lucide-static@0.577.0/icons/workflow.svg", "label": "Workflow"},
                        {"library": "lucide", "name": "layers-3", "url": "https://cdn.jsdelivr.net/npm/lucide-static@0.577.0/icons/layers-3.svg", "label": "Layers 3"},
                        {"library": "lucide", "name": "users", "url": "https://cdn.jsdelivr.net/npm/lucide-static@0.577.0/icons/users.svg", "label": "Users"},
                    ],
                    "capability_icons": [],
                    "section_media": {
                        "workflows": [
                            {"url": "https://source.unsplash.com/featured/1280x860/?workflow,automation", "query": "workflow,automation", "alt": "Capture workflow visual", "source": "unsplash-source"},
                            {"url": "https://source.unsplash.com/featured/1280x860/?dashboard,team", "query": "dashboard,team", "alt": "Align workflow visual", "source": "unsplash-source"},
                            {"url": "https://source.unsplash.com/featured/1280x860/?analytics,proof", "query": "analytics,proof", "alt": "Ship workflow visual", "source": "unsplash-source"},
                        ],
                    },
                },
            }
        )

        self.assertIn('data-visual-role="workflow-image"', body)
        self.assertIn("lucide-static@0.577.0/icons/workflow.svg", body)
        self.assertIn("saas-workflow-grid", body)

    def test_portfolio_builder_renders_project_gallery(self):
        body = self._render(
            {
                "variant_id": "variant-portfolio",
                "label": "Portfolio Variant",
                "summary": "Casebook portfolio.",
                "render_plan": {
                    "template_key": "portfolio",
                    "template_file": "generated/portfolio_builder.html",
                    "theme_key": "studio_pop",
                    "art_direction": "studio_pop",
                    "layout_mode": "casebook_editorial",
                    "density": "balanced",
                    "motion_level": "moderate",
                    "section_order": ["hero", "projects", "about", "capabilities", "proof", "cta"],
                    "section_visibility": {"hero": True, "projects": True, "about": True, "capabilities": True, "proof": True, "cta": True},
                    "hero_variant": "editorial",
                    "industry": "creative",
                    "vibe": "bold",
                    "keywords": ["portfolio", "projects", "editorial"],
                    "confidence": 0.89,
                    "reasons": ["test payload"],
                    "slot_schema": {"text_slots": [], "list_slots": {}},
                },
                "theme": self._theme(),
                "content": {
                    "hero_eyebrow": "Northstar Studio",
                    "hero_title": "Work with a point of view",
                    "hero_subtitle": "Projects arranged like a real body of work.",
                    "cta_text": "View work",
                    "cta_note": "Start with the strongest cases.",
                    "projects_title": "Selected work",
                    "projects_intro": "A curated set of recent projects.",
                    "about_title": "About",
                    "about_intro": "A short practice note.",
                    "about_text": "Built around strategy, image-making, and interface craft.",
                    "capabilities_title": "Capabilities",
                    "capabilities_intro": "The system behind the work.",
                    "proof_quote": "It feels authored, not templated.",
                    "proof_author": "Creative director",
                    "projects": [
                        {"title": "Signal Shift", "desc": "A redesign with stronger recall.", "meta": "Brand system"},
                        {"title": "Launch Sequence", "desc": "A sharper launch story.", "meta": "Web launch"},
                        {"title": "Archive Motion", "desc": "A visual identity refresh.", "meta": "Identity"},
                        {"title": "Frame Study", "desc": "An editorial gallery site.", "meta": "Portfolio"},
                    ],
                    "capabilities": [
                        {"title": "Positioning", "desc": "Turn strategy into a page architecture."},
                        {"title": "Art direction", "desc": "Build a visual language with authorship."},
                        {"title": "Delivery", "desc": "Ship systems that still feel intentional."},
                    ],
                },
                "visuals": {
                    "hero_image": {"url": "https://source.unsplash.com/featured/1600x900/?studio,portfolio", "query": "studio,portfolio", "alt": "Studio Portfolio visual for hero section", "source": "unsplash-source"},
                    "project_images": [
                        {"url": "https://source.unsplash.com/featured/900x720/?branding,design", "query": "branding,design", "alt": "Signal Shift project preview", "source": "unsplash-source"},
                        {"url": "https://source.unsplash.com/featured/900x720/?launch,editorial", "query": "launch,editorial", "alt": "Launch Sequence project preview", "source": "unsplash-source"},
                        {"url": "https://source.unsplash.com/featured/900x720/?identity,archive", "query": "identity,archive", "alt": "Archive Motion project preview", "source": "unsplash-source"},
                        {"url": "https://source.unsplash.com/featured/900x720/?gallery,portfolio", "query": "gallery,portfolio", "alt": "Frame Study project preview", "source": "unsplash-source"},
                    ],
                    "feature_icons": [],
                    "capability_icons": [
                        {"library": "lucide", "name": "layers-3", "url": "https://cdn.jsdelivr.net/npm/lucide-static@0.577.0/icons/layers-3.svg", "label": "Layers 3"},
                        {"library": "lucide", "name": "palette", "url": "https://cdn.jsdelivr.net/npm/lucide-static@0.577.0/icons/palette.svg", "label": "Palette"},
                        {"library": "lucide", "name": "rocket", "url": "https://cdn.jsdelivr.net/npm/lucide-static@0.577.0/icons/rocket.svg", "label": "Rocket"},
                    ],
                    "section_media": {"projects": []},
                },
            }
        )

        self.assertGreaterEqual(body.count('data-visual-role="project-image"'), 4)
        self.assertIn("portfolio-capability-grid", body)
        self.assertIn("lucide-static@0.577.0/icons/palette.svg", body)

    def test_business_builder_renders_services_and_process_without_product_grid(self):
        body = self._render(
            {
                "variant_id": "variant-business",
                "label": "Business Variant",
                "summary": "Trust-first business site.",
                "render_plan": {
                    "template_key": "business",
                    "template_file": "generated/business_builder.html",
                    "theme_key": "modern_editorial",
                    "art_direction": "modern_editorial",
                    "layout_mode": "service_story",
                    "density": "balanced",
                    "motion_level": "calm",
                    "section_order": ["hero", "services", "process", "proof", "cta"],
                    "section_visibility": {"hero": True, "services": True, "process": True, "proof": True, "cta": True},
                    "hero_variant": "service",
                    "industry": "healthcare",
                    "vibe": "clean",
                    "keywords": ["business", "services", "trust"],
                    "confidence": 0.9,
                    "reasons": ["test payload"],
                    "slot_schema": {"text_slots": [], "list_slots": {}},
                },
                "theme": self._theme(),
                "content": {
                    "hero_eyebrow": "Northstar Clinic",
                    "hero_title": "Care that is easier to trust",
                    "hero_subtitle": "A clearer local business story with services and process.",
                    "cta_text": "Book now",
                    "cta_note": "Start the conversation in one step.",
                    "services_title": "Services",
                    "services_intro": "Clear offers for local clients.",
                    "process_title": "Process",
                    "process_intro": "How we work from first contact onward.",
                    "proof_quote": "It finally feels like a real business website.",
                    "proof_author": "Patient review",
                    "services": [
                        {"title": "Consultation", "desc": "A focused first appointment.", "meta": "Core service"},
                        {"title": "Ongoing care", "desc": "Structured follow-up support.", "meta": "Retention"},
                        {"title": "Virtual check-ins", "desc": "Flexible access for busy clients.", "meta": "Access"},
                    ],
                    "process_steps": [
                        {"title": "Reach out", "desc": "Book the first conversation."},
                        {"title": "Get a clear plan", "desc": "Understand the next steps quickly."},
                        {"title": "Move forward", "desc": "Stay supported after the first visit."},
                    ],
                },
                "visuals": {
                    "hero_image": {"url": "https://source.unsplash.com/featured/1600x900/?clinic,care", "query": "clinic,care", "alt": "Clinic Care visual for hero section", "source": "unsplash-source"},
                    "project_images": [],
                    "feature_icons": [],
                    "capability_icons": [],
                    "section_media": {
                        "services": [
                            {"url": "https://source.unsplash.com/featured/1040x820/?consultation,care", "query": "consultation,care", "alt": "Consultation service visual", "source": "unsplash-source"},
                            {"url": "https://source.unsplash.com/featured/1040x820/?support,clinic", "query": "support,clinic", "alt": "Ongoing service visual", "source": "unsplash-source"},
                        ],
                    },
                },
            }
        )

        self.assertIn('data-visual-role="service-image"', body)
        self.assertIn("business-process-grid", body)
        self.assertNotIn('data-visual-role="product-image"', body)


if __name__ == "__main__":
    unittest.main()
