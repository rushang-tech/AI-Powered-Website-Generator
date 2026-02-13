import unittest
from unittest.mock import patch

from app.services.ai_engine import generate_project_manifest
from app.services.ai_provider import AIProviderUnavailableError
from app.services.taste_engine import RenderPlan


class _FailingProvider:
    def generate_text(self, prompt: str) -> str:
        raise AIProviderUnavailableError("Gemini generation is unavailable because the configured API key is out of quota or rate-limited.")

    def generate_json(self, prompt: str) -> dict[str, object]:
        raise AIProviderUnavailableError("Gemini generation is unavailable because the configured API key is out of quota or rate-limited.")


def _plan() -> RenderPlan:
    return RenderPlan(
        template_key="landing",
        template_file="generated/site_builder.html",
        theme_key="playful_blocks",
        art_direction="playful_blocks",
        layout_mode="split_hero",
        density="balanced",
        motion_level="moderate",
        section_order=["hero", "features", "proof", "cta"],
        section_visibility={"hero": True, "features": True, "proof": True, "cta": True},
        hero_variant="split",
        industry="education",
        vibe="playful",
        keywords=["kids", "coding", "workshop"],
        confidence=0.88,
        reasons=["test route"],
        slot_schema={
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
    )


class AIEngineTests(unittest.TestCase):
    @patch("app.services.ai_engine.build_render_variants")
    def test_generate_project_manifest_falls_back_when_provider_generation_fails(self, mocked_build_render_variants):
        mocked_build_render_variants.return_value = [_plan()]

        manifest = generate_project_manifest(
            "A playful landing page for a kids coding workshop",
            brief={
                "goal": "Get parents to sign up their kids for weekend coding classes",
                "audience": "Parents of kids age 7 to 12",
                "brand_tone": "Playful, encouraging, imaginative",
                "name": "CodeSprouts",
                "notes": "Make it feel kid-friendly and colorful, not corporate.",
            },
            provider=_FailingProvider(),
        )

        self.assertEqual(len(manifest.variants), 1)
        self.assertTrue(manifest.variants[0].content.validation.fallback_used)
        self.assertIn(
            "Gemini was unavailable during generation",
            manifest.variants[0].content.validation.warnings[0],
        )
        generate_stage = next(stage for stage in manifest.statuses if stage.key == "generate")
        self.assertIn("Gemini was unavailable", generate_stage.detail)
