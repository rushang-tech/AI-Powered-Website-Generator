import json
import time
import unittest
from io import BytesIO
from unittest.mock import Mock, patch
from zipfile import ZipFile

from app import create_app
from app.services.ai_engine import (
    ProjectManifest,
    _validate_content,
    apply_canvas_command_to_manifest,
    generate_project_manifest,
)
from app.services.ai_provider import (
    AIProviderRequestError,
    RotatingGeminiAIProvider,
    _resolve_api_keys,
)
from app.services.contracts import BriefInput
from app.services.export_service import build_export_bundle
from app.services.preview_store import InMemoryPreviewStore
from app.services.published_site_service import PublishedSiteService
from app.services.server_runtime import gunicorn_worker_count, resolve_bind_port
from app.services.taste_engine import (
    RenderPlan,
    build_render_variants,
    clean_json_response,
    normalize_brief,
)

# Mock data for creating test manifests
from tests.test_routes import _payload


class TestUnitPlan(unittest.TestCase):
    def setUp(self):
        """Set up a Flask app context for tests that need it."""
        self.app = create_app({"TESTING": True, "SECRET_KEY": "test-secret"})
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        """Clean up the app context."""
        self.app_context.pop()

    # Test Cases based on the Unit Testing Test Plan (UTP-01 to UTP-15)

    def test_utp_01_taste_engine_prompt_analysis(self):
        """UTP-01: Verifies prompt analysis classifies a restaurant prompt into the 'retail' industry."""
        plans = build_render_variants(
            "A website for a modern Italian restaurant in New York.",
            brief={
                "goal": "A website for a modern Italian restaurant in New York.",
                "audience": "Foodies and locals",
            },
        )
        # The primary variant's industry should be correctly identified.
        self.assertEqual(plans[0].industry, "retail")

    def test_utp_02_taste_engine_brief_normalization(self):
        """UTP-02: Verifies that a partial brief is safely normalized with default values."""
        normalized = normalize_brief(
            "A site.",
            {
                "goal": "A site.",
                "audience": "  ",  # Intentionally blank
            },
        )
        self.assertEqual(normalized.goal, "A site.")
        self.assertEqual(normalized.audience, "General audience")  # Should fall back to default
        self.assertEqual(normalized.content_density, "balanced") # Should have a default

    @patch.dict("os.environ", {"GEMINI_API_KEY": "key-single", "GEMINI_API_KEYS": "key-multi-1,key-multi-2"}, clear=True)
    def test_utp_03_ai_provider_api_key_initialization(self):
        """UTP-03: Verifies that API keys are loaded correctly from environment variables."""
        keys = _resolve_api_keys()
        # The multi-key variable (GEMINI_API_KEYS) should take precedence and be parsed correctly.
        self.assertEqual(len(keys), 2)
        self.assertEqual(keys, ("key-multi-1", "key-multi-2"))

    @patch("app.services.ai_provider.genai.GenerativeModel")
    def test_utp_04_ai_provider_key_rotation(self, mock_generative_model):
        """UTP-04: Verifies the system rotates to a new API key after a quota error."""
        # Simulate the first key getting a quota error and the second succeeding
        mock_model_key1 = Mock()
        mock_model_key1.generate_content.side_effect = AIProviderRequestError(
            "429 quota exhausted", retryable=True, quota_error=True
        )
        mock_model_key2 = Mock()
        mock_model_key2.generate_content.return_value = Mock(text="Success from key 2")

        # The side_effect list maps to calls for key1, then key2
        mock_generative_model.side_effect = [mock_model_key1, mock_model_key2]

        provider = RotatingGeminiAIProvider(["key-quota-exceeded", "key-ok"])
        result = provider.generate_text("test prompt")

        self.assertEqual(result, "Success from key 2")
        self.assertEqual(mock_generative_model.call_count, 2)

    def test_utp_05_json_sanitizer_response_cleanup(self):
        """UTP-05: Verifies that markdown code fences and filler text are stripped from an AI response."""
        raw_response = 'Here is the JSON you requested:\n```json\n{"key": "value", "valid": true}\n```\nLet me know if you need anything else.'
        cleaned = clean_json_response(raw_response)
        self.assertEqual(cleaned, '{"key": "value", "valid": true}')

    def test_utp_06_content_validator_fallback_injection(self):
        """UTP-06: Verifies that missing fields in an AI response are filled with fallback data."""
        # A mock render plan defining what slots are expected.
        mock_plan = RenderPlan(
            template_key="landing",
            slot_schema={
                "text_slots": ["hero_title", "hero_subtitle"],
                "list_slots": {},
            },
        )
        mock_brief = normalize_brief("test")

        # Incomplete content from the AI
        incomplete_content = {"hero_title": "Valid Title"}

        validated_content = _validate_content(incomplete_content, brief=mock_brief, render_plan=mock_plan)

        self.assertTrue(validated_content.validation.fallback_used)
        self.assertIn("hero_title", validated_content.data)
        self.assertIn("hero_subtitle", validated_content.data) # This field was missing
        self.assertEqual(validated_content.data["hero_title"], "Valid Title")
        self.assertIn("Filled fallback text for 'hero_subtitle'", validated_content.validation.warnings)

    @patch("app.services.ai_engine.build_render_variants")
    @patch("app.services.ai_engine._generate_content")
    def test_utp_07_manifest_generator_manifest_generation(self, mock_generate_content, mock_build_variants):
        """UTP-07: Verifies that a valid ProjectManifest is created from a generation request."""
        mock_build_variants.return_value = [Mock(spec=RenderPlan)]
        mock_generate_content.return_value = Mock(validation=Mock(fallback_used=False))

        manifest = generate_project_manifest("A test prompt")

        self.assertIsInstance(manifest, ProjectManifest)
        self.assertIsNotNone(manifest.preview_id)
        self.assertEqual(len(manifest.variants), 1)
        self.assertEqual(manifest.selected_variant_id, manifest.variants[0].variant_id)

    @patch("app.services.ai_engine._rewrite_text_value")
    def test_utp_08_continue_manifest_follow_up_refinement(self, mock_rewrite):
        """UTP-08: Verifies that a follow-up instruction correctly updates an existing manifest."""
        mock_rewrite.return_value = "A new, improved headline"
        manifest = ProjectManifest.from_dict(_payload("preview-123"))
        instruction = "Make the hero title punchier"

        # Simulate a command to rewrite a specific text field
        updated_manifest, _ = apply_canvas_command_to_manifest(
            manifest,
            action="rewrite_text",
            edit_path="hero_title",
            instruction=instruction,
        )
        
        # Check that an override was created for the specified field
        self.assertEqual(updated_manifest.variants[0].content_overrides["hero_title"], "A new, improved headline")

    def test_utp_09_preview_store_save_and_retrieve(self):
        """UTP-09: Verifies that preview data can be saved and retrieved from the in-memory store."""
        store = InMemoryPreviewStore()
        payload = {"data": "test"}
        store.set(preview_id="test-id", prompt="A test", payload=payload)
        retrieved = store.get("test-id")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["payload"], payload)

    @patch("time.time")
    def test_utp_10_preview_store_ttl_expiration(self, mock_time):
        """UTP-10: Verifies that expired previews are correctly invalidated by the store."""
        store = InMemoryPreviewStore(ttl_seconds=60)
        
        # 1. Set an item at time=1000
        mock_time.return_value = 1000.0
        store.set(preview_id="test-ttl", prompt="TTL test", payload={"key": "val"})
        
        # 2. Try to get it 70 seconds later (1000 + 60 + 10)
        mock_time.return_value = 1070.0
        retrieved = store.get("test-ttl")
        
        # get() runs a cleanup first, so the expired item should be gone
        self.assertIsNone(retrieved)

    def test_utp_11_export_service_zip_generation(self):
        """UTP-11: Verifies that the export service correctly bundles website files into a ZIP."""
        manifest = ProjectManifest.from_dict(_payload("export-test"))
        buffer, filename = build_export_bundle(manifest)

        self.assertIsInstance(buffer, BytesIO)
        self.assertTrue(filename.endswith(".zip"))

        # Verify the contents of the ZIP file in memory
        with ZipFile(buffer, 'r') as zip_file:
            self.assertIn("index.html", zip_file.namelist())
            self.assertIn("assets/export-frame.css", zip_file.namelist())
            self.assertIn("manifest.json", zip_file.namelist())

    def test_utp_12_publish_service_link_creation(self):
        """UTP-12: Verifies that the publish service can create a record for a live link."""
        mock_store = Mock()
        service = PublishedSiteService(mock_store, ttl_seconds=3600)
        
        service.save("publish-id-123", {"html": "<html>...</html>", "css": "body {}"})
        
        # Verify that the store's `set` method was called with the correct data
        mock_store.set.assert_called_once()
        args, kwargs = mock_store.set.call_args
        self.assertEqual(kwargs["preview_id"], "publish-id-123")
        self.assertIn("published_at", kwargs["payload"])

    def test_utp_13_flask_routes_input_validation(self):
        """UTP-13: Verifies that a route (e.g., /generate) safely handles invalid input."""
        # This is an integration test, but we can test the specific case from the plan
        with self.app.test_client() as client:
            # Missing JSON body
            response = client.post("/generate", content_type="application/json")
            self.assertEqual(response.status_code, 400) # Expecting bad request
            
            # Blank prompt
            response = client.post("/generate", json={"prompt": ""})
            self.assertEqual(response.status_code, 400)
            self.assertIn("error", response.get_json())
            self.assertIn("required", response.get_json()["error"])

    def test_utp_14_runtime_manager_startup_fallback(self):
        """UTP-14: Verifies safe runtime behavior without Redis or with a busy port."""
        # Test gunicorn worker fallback without Redis
        with patch.dict("os.environ", {"REDIS_URL": ""}, clear=True):
            self.assertEqual(gunicorn_worker_count(), 1)

        # Test port fallback when the default is busy
        def mock_can_bind(host, port):
            return port == 5002 # Simulate that only port 5002 is free

        with patch("app.server_runtime._can_bind", side_effect=mock_can_bind):
            selection = resolve_bind_port(default_port=5001, search_limit=5)
            self.assertEqual(selection.port, 5002)
            self.assertTrue(selection.auto_selected)

    def test_utp_15_health_check_route(self):
        """UTP-15: Verifies the application's /healthz endpoint responds correctly."""
        with self.app.test_client() as client:
            response = client.get("/healthz")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.get_json(), {"ok": True, "service": "velosite-ai"})

if __name__ == "__main__":
    unittest.main()