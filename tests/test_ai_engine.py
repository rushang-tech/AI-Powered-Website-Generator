import unittest
from unittest.mock import patch

from app.services.ai_engine import THEME_MAP, build_preview_variant, continue_project_manifest, generate_project_manifest, regenerate_manifest
from app.services.ai_provider import AIProviderUnavailableError
from app.services.taste_engine import RenderPlan


class _FailingProvider:
    def generate_text(self, prompt: str) -> str:
        raise AIProviderUnavailableError("Gemini generation is unavailable because the configured API key is out of quota or rate-limited.")

    def generate_json(self, prompt: str) -> dict[str, object]:
        raise AIProviderUnavailableError("Gemini generation is unavailable because the configured API key is out of quota or rate-limited.")


class _JSONProvider:
    def __init__(self, *responses: dict[str, object]) -> None:
        self._responses = list(responses)

    def generate_text(self, prompt: str) -> str:
        return "ok"

    def generate_json(self, prompt: str) -> dict[str, object]:
        if not self._responses:
            raise AssertionError("No stub response available for generate_json().")
        return self._responses.pop(0)


def _content(*, hero_title: str, feature_title: str) -> dict[str, object]:
    return {
        "hero_eyebrow": "Playful Blocks",
        "hero_title": hero_title,
        "hero_subtitle": "Weekend coding adventures for curious kids.",
        "cta_text": "Join now",
        "cta_note": "Reserve a seat for the next cohort.",
        "proof_quote": "It feels vivid and easy to trust.",
        "proof_author": "Parent review",
        "features": [
            {"title": feature_title, "desc": "Turn learning into a memorable mission."},
            {"title": "Creative projects", "desc": "Build games, stories, and experiments."},
            {"title": "Parent updates", "desc": "See steady progress each week."},
        ],
    }


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
        self.assertEqual(manifest.variants[0].visuals["hero_image"]["source"], "unsplash-source")
        self.assertIn(
            "Gemini was unavailable during generation",
            manifest.variants[0].content.validation.warnings[0],
        )
        generate_stage = next(stage for stage in manifest.statuses if stage.key == "generate")
        self.assertIn("Gemini was unavailable", generate_stage.detail)

    @patch("app.services.ai_engine.build_render_variants")
    def test_continue_project_manifest_refreshes_visuals(self, mocked_build_render_variants):
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
            provider=_JSONProvider(_content(hero_title="Coding Coding Coding Camp", feature_title="Creative badges")),
        )

        updated_manifest, assistant_reply = continue_project_manifest(
            manifest,
            "Make it feel more space-focused",
            provider=_JSONProvider(
                {
                    "assistant_reply": "Shifted the direction toward a playful space mission.",
                    "content": _content(hero_title="Orbit Orbit Orbit Robotics", feature_title="Rocket launch"),
                }
            ),
        )

        self.assertEqual(assistant_reply, "Shifted the direction toward a playful space mission.")
        self.assertIn("orbit", updated_manifest.variants[0].visuals["hero_image"]["query"])
        self.assertEqual(updated_manifest.variants[0].visuals["feature_icons"][0]["name"], "rocket")

    @patch("app.services.ai_engine.build_render_variants")
    def test_continue_project_manifest_applies_theme_changes_to_the_variant(self, mocked_build_render_variants):
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
            provider=_JSONProvider(_content(hero_title="Coding Coding Coding Camp", feature_title="Creative badges")),
        )

        original_title = manifest.variants[0].content.data["hero_title"]
        themed_manifest, assistant_reply = continue_project_manifest(
            manifest,
            "Use purple and black theme",
            provider=_JSONProvider({}),
        )

        self.assertIn("purple and black", assistant_reply.lower())
        self.assertEqual(themed_manifest.variants[0].content.data["hero_title"], original_title)
        self.assertEqual(themed_manifest.variants[0].theme["accent"], "#8b5cf6")
        self.assertTrue(themed_manifest.variants[0].theme["surface"].startswith("#"))
        self.assertNotEqual(themed_manifest.variants[0].theme["surface"], manifest.variants[0].theme["surface"])

        revised_manifest, _ = continue_project_manifest(
            themed_manifest,
            "Make the headline feel more space-focused",
            provider=_JSONProvider(
                {
                    "assistant_reply": "Refined the headline and supporting copy.",
                    "content": _content(hero_title="Orbit Orbit Orbit Robotics", feature_title="Rocket launch"),
                }
            ),
        )

        self.assertEqual(revised_manifest.variants[0].theme["accent"], "#8b5cf6")

    @patch("app.services.ai_engine.build_render_variants")
    def test_build_preview_variant_uses_the_override_theme(self, mocked_build_render_variants):
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
            provider=_JSONProvider(_content(hero_title="Coding Coding Coding Camp", feature_title="Creative badges")),
        )

        remixed = build_preview_variant(
            manifest,
            variant_id="variant-1",
            overrides={"art_direction": "cyber_signal"},
        )

        self.assertEqual(remixed["render_plan"]["art_direction"], "cyber_signal")
        self.assertEqual(remixed["theme"]["key"], "cyber_signal")
        self.assertEqual(remixed["theme"]["accent"], THEME_MAP["cyber_signal"]["accent"])

    @patch("app.services.ai_engine.build_render_variants")
    def test_regenerate_manifest_refreshes_visuals(self, mocked_build_render_variants):
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
            provider=_JSONProvider(_content(hero_title="Coding Coding Coding Camp", feature_title="Creative badges")),
        )

        refreshed = regenerate_manifest(
            manifest,
            scope="variant",
            variant_id="variant-1",
            provider=_JSONProvider(_content(hero_title="Analytics Analytics Analytics Lab", feature_title="Revenue analytics")),
        )

        self.assertIn("analytics", refreshed.variants[0].visuals["hero_image"]["query"])
        self.assertEqual(refreshed.variants[0].visuals["feature_icons"][0]["name"], "bar-chart-3")


if __name__ == "__main__":
    unittest.main()
