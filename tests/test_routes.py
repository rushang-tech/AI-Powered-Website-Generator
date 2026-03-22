import os
import tempfile
import unittest
from unittest.mock import patch

from app import create_app
from app.extensions import db
from app.models import Conversation, Message, User
from app.services.contracts import ProjectManifest
from app.services.conversation_service import create_conversation, manifest_from_conversation
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
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = os.path.join(self.temp_dir.name, "routes-test.db")
        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-secret",
                "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}",
            }
        )
        self.client = self.app.test_client()
        PUBLISHED_SITE_SERVICE.clear()
        with self.app.app_context():
            db.drop_all()
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
        self.temp_dir.cleanup()

    def _signup_and_login(self, *, email: str = "rush@example.com", password: str = "password123", display_name: str = "Rush"):
        response = self.client.post(
            "/signup",
            data={
                "email": email,
                "password": password,
                "display_name": display_name,
            },
        )
        self.assertEqual(response.status_code, 302)
        return email, password

    def _logout(self):
        response = self.client.post("/logout")
        self.assertEqual(response.status_code, 302)

    def _seed_conversation(self, *, email: str = "rush@example.com", preview_id: str = "preview-123", title: str | None = None):
        with self.app.app_context():
            user = User.query.filter_by(email=email).first()
            manifest = ProjectManifest.from_dict(_payload(preview_id))
            conversation = create_conversation(
                user,
                manifest=manifest,
                user_message="Create a startup landing page for founders.",
            )
            if title:
                conversation.title = title
                db.session.add(conversation)
                db.session.commit()
            return conversation.id

    def test_home_requires_login_and_generate_requires_auth_json(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

        generate_response = self.client.post("/generate", json={"prompt": "A product launch page"})
        self.assertEqual(generate_response.status_code, 401)
        self.assertEqual(generate_response.get_json()["error"], "Authentication required.")

    def test_signup_login_logout_and_duplicate_email(self):
        email, password = self._signup_and_login()
        self._logout()

        bad_login = self.client.post("/login", data={"email": email, "password": "wrong-pass"}, follow_redirects=True)
        self.assertEqual(bad_login.status_code, 200)
        self.assertIn("Email or password is incorrect.", bad_login.get_data(as_text=True))

        good_login = self.client.post("/login", data={"email": email, "password": password})
        self.assertEqual(good_login.status_code, 302)

        self._logout()
        duplicate = self.client.post(
            "/signup",
            data={"email": email, "password": "password123", "display_name": "Rush"},
            follow_redirects=True,
        )
        self.assertEqual(duplicate.status_code, 200)
        self.assertIn("already registered", duplicate.get_data(as_text=True))

    @patch("app.routes.generate_project_manifest")
    def test_generate_returns_variant_metadata_and_creates_conversation(self, mocked_generate):
        self._signup_and_login()
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
        self.assertTrue(data["conversation_id"])
        self.assertEqual(data["selected_variant_id"], "variant-1")
        self.assertEqual(len(data["variants"]), 3)

        preview_response = self.client.get(data["preview_url"])
        self.assertEqual(preview_response.status_code, 200)
        body = preview_response.get_data(as_text=True)
        self.assertIn("Conversation", body)
        self.assertIn("Recent chats", body)
        self.assertIn('data-workspace-nav', body)
        self.assertIn('id="workspace-conversation-list"', body)
        self.assertNotIn("data-workspace-shell", body)

        with self.app.app_context():
            conversation = db.session.get(Conversation, data["conversation_id"])
            self.assertIsNotNone(conversation)
            self.assertEqual(conversation.preview_id, "preview-123")
            self.assertEqual(Message.query.filter_by(conversation_id=conversation.id).count(), 2)

    def test_workspace_nav_only_renders_for_dashboard_and_studio(self):
        login_response = self.client.get("/login")
        self.assertEqual(login_response.status_code, 200)
        self.assertNotIn("data-workspace-nav", login_response.get_data(as_text=True))

        signup_response = self.client.get("/signup")
        self.assertEqual(signup_response.status_code, 200)
        self.assertNotIn("data-workspace-nav", signup_response.get_data(as_text=True))

        self._signup_and_login()

        home_response = self.client.get("/")
        self.assertEqual(home_response.status_code, 200)
        home_body = home_response.get_data(as_text=True)
        self.assertIn("data-workspace-nav", home_body)
        self.assertIn("data-nav-toggle", home_body)
        self.assertNotIn("data-workspace-shell", home_body)

        settings_response = self.client.get("/settings")
        self.assertEqual(settings_response.status_code, 200)
        self.assertNotIn("data-workspace-nav", settings_response.get_data(as_text=True))

    @patch("app.routes.generate_project_manifest")
    def test_generate_forwards_brand_assets_and_icon_style(self, mocked_generate):
        self._signup_and_login()
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

    def test_conversation_list_rename_and_delete(self):
        self._signup_and_login()
        conversation_id = self._seed_conversation(title="Original title")

        list_response = self.client.get("/conversations")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.get_json()["conversations"]), 1)

        rename_response = self.client.post(f"/conversations/{conversation_id}/rename", json={"title": "Renamed thread"})
        self.assertEqual(rename_response.status_code, 200)
        self.assertEqual(rename_response.get_json()["conversation"]["title"], "Renamed thread")

        delete_response = self.client.delete(f"/conversations/{conversation_id}")
        self.assertEqual(delete_response.status_code, 200)
        self.assertTrue(delete_response.get_json()["ok"])

        with self.app.app_context():
            self.assertEqual(Conversation.query.count(), 0)
            self.assertEqual(Message.query.count(), 0)

    @patch("app.routes.continue_project_manifest")
    def test_continue_conversation_updates_manifest_and_messages(self, mocked_continue):
        self._signup_and_login()
        conversation_id = self._seed_conversation(preview_id="preview-continue")
        updated_payload = _payload("preview-continue")
        updated_payload["variants"][0]["content"]["hero_title"] = "A refined headline"
        mocked_continue.return_value = (ProjectManifest.from_dict(updated_payload), "Updated the hero direction.")

        response = self.client.post(
            f"/conversations/{conversation_id}/messages",
            json={"message": "Make the hero punchier", "variant_id": "variant-1"},
        )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["preview_id"], "preview-continue")
        self.assertEqual(data["selected_variant"]["content"]["hero_title"], "A refined headline")
        self.assertEqual(len(data["messages"]), 4)
        self.assertEqual(data["messages"][-1]["role"], "assistant")

        with self.app.app_context():
            conversation = db.session.get(Conversation, conversation_id)
            manifest = manifest_from_conversation(conversation)
            self.assertEqual(manifest.preview_id, "preview-continue")
            self.assertEqual(manifest.variants[0].content.data["hero_title"], "A refined headline")
            self.assertEqual(Message.query.filter_by(conversation_id=conversation_id).count(), 4)

    def test_settings_updates_defaults_password_and_delete_account(self):
        email, password = self._signup_and_login()
        self._seed_conversation(email=email, preview_id="preview-settings")

        profile_response = self.client.post(
            "/settings",
            data={
                "action": "profile",
                "display_name": "Updated Rush",
                "email": email,
                "default_brand_tone": "Bold and clear",
                "default_content_density": "dense",
                "default_motion_level": "energetic",
                "default_icon_style": "Sharp monochrome symbols",
            },
            follow_redirects=True,
        )
        self.assertEqual(profile_response.status_code, 200)
        self.assertIn("Settings updated.", profile_response.get_data(as_text=True))

        password_response = self.client.post(
            "/settings",
            data={
                "action": "password",
                "current_password": password,
                "new_password": "newpassword123",
                "confirm_password": "newpassword123",
            },
            follow_redirects=True,
        )
        self.assertEqual(password_response.status_code, 200)
        self.assertIn("Password updated.", password_response.get_data(as_text=True))

        self._logout()
        relogin = self.client.post("/login", data={"email": email, "password": "newpassword123"})
        self.assertEqual(relogin.status_code, 302)

        delete_response = self.client.post(
            "/settings",
            data={"action": "delete", "current_password": "newpassword123"},
            follow_redirects=True,
        )
        self.assertEqual(delete_response.status_code, 200)
        self.assertIn("deleted", delete_response.get_data(as_text=True).lower())

        with self.app.app_context():
            self.assertEqual(User.query.count(), 0)
            self.assertEqual(Conversation.query.count(), 0)
            self.assertEqual(Message.query.count(), 0)

    def test_other_users_cannot_access_owned_preview_or_conversation(self):
        owner_email, _ = self._signup_and_login(email="owner@example.com")
        conversation_id = self._seed_conversation(email=owner_email, preview_id="preview-owner")
        self._logout()
        self._signup_and_login(email="other@example.com")

        preview_response = self.client.get("/preview/preview-owner")
        self.assertEqual(preview_response.status_code, 404)

        override_response = self.client.post("/preview/preview-owner/override", json={"variant_id": "variant-2"})
        self.assertEqual(override_response.status_code, 404)

        rename_response = self.client.post(f"/conversations/{conversation_id}/rename", json={"title": "Nope"})
        self.assertEqual(rename_response.status_code, 404)

    def test_publish_stays_public_but_creation_requires_login(self):
        self._signup_and_login()
        self._seed_conversation(preview_id="preview-publish")

        response = self.client.post("/preview/preview-publish/publish", json={"variant_id": "variant-2"})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["ok"])
        self.assertIn("/published/", data["public_path"])

        public_client = self.app.test_client()
        site_response = public_client.get(data["public_path"])
        self.assertEqual(site_response.status_code, 200)
        site_html = site_response.get_data(as_text=True)
        self.assertIn("<!DOCTYPE html>", site_html)
        self.assertIn("Build momentum", site_html)

        contact_response = public_client.get(f"/published/{data['publish_id']}/contact")
        self.assertEqual(contact_response.status_code, 200)
        self.assertIn("Current page", contact_response.get_data(as_text=True))

        css_response = public_client.get(f"/published/{data['publish_id']}/assets/export-frame.css")
        self.assertEqual(css_response.status_code, 200)
        self.assertEqual(css_response.mimetype, "text/css")

    def test_export_returns_zip_for_owned_preview(self):
        self._signup_and_login()
        self._seed_conversation(preview_id="preview-export")

        response = self.client.post("/preview/preview-export/export")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/zip")
        self.assertIn("attachment;", response.headers.get("Content-Disposition", ""))

    def test_preview_frame_accepts_query_overrides_for_remix(self):
        self._signup_and_login()
        self._seed_conversation(preview_id="preview-frame")

        response = self.client.get(
            "/preview/preview-frame/frame?variant_id=variant-1&layout_mode=proof_first&art_direction=warm_gradient&remix_label=Remix+1"
        )
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Remix 1", body)
        self.assertIn("--theme-frame-background", body)
        self.assertIn("Contact", body)

    def test_preview_frame_can_render_secondary_pages(self):
        self._signup_and_login()
        self._seed_conversation(preview_id="preview-pages")

        response = self.client.get("/preview/preview-pages/frame?page_slug=contact")
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Current page", body)
        self.assertIn("Contact", body)

    def test_branding_and_canvas_actions_persist_to_conversation(self):
        self._signup_and_login()
        self._seed_conversation(preview_id="preview-branding")

        branding_response = self.client.post(
            "/preview/preview-branding/branding",
            json={"brief": {"brand_assets": [_brand_asset()], "icon_style": "Rounded interface icons"}},
        )
        self.assertEqual(branding_response.status_code, 200)

        command_response = self.client.post(
            "/preview/preview-branding/command",
            json={
                "variant_id": "variant-1",
                "action": "set_text",
                "node_id": "hero-title",
                "edit_path": "hero_title",
                "value": "A sharper hero headline",
            },
        )
        self.assertEqual(command_response.status_code, 200)
        self.assertEqual(command_response.get_json()["selected_variant"]["content"]["hero_title"], "A sharper hero headline")

        with self.app.app_context():
            conversation = Conversation.query.filter_by(preview_id="preview-branding").first()
            manifest = manifest_from_conversation(conversation)
            self.assertEqual(manifest.brief.icon_style, "Rounded interface icons")
            self.assertEqual(manifest.variants[0].content_overrides["hero_title"], "A sharper hero headline")
            self.assertEqual(Message.query.filter_by(conversation_id=conversation.id, role="system").count(), 2)


if __name__ == "__main__":
    unittest.main()
