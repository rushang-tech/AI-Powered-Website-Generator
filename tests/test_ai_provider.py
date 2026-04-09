import os
import unittest
from unittest.mock import patch

from app.services.ai_provider import (
    AIProviderRequestError,
    GeminiAIProvider,
    RotatingGeminiAIProvider,
    _resolve_api_keys,
    require_default_provider,
)


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeModelsAPI:
    def __init__(self, responses: dict[str, object]) -> None:
        self._responses = responses

    def generate_content(self, *, model: str, contents: str):
        _ = contents
        result = self._responses[model]
        if isinstance(result, Exception):
            raise result
        return _FakeResponse(str(result))


class _FakeClient:
    def __init__(self, responses: dict[str, object]) -> None:
        self.models = _FakeModelsAPI(responses)


class _FakeKeyProvider:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def generate_text(self, prompt: str, *, stop_on_quota_error: bool = False) -> str:
        if self._api_key == "key-1":
            raise RuntimeError("429 quota exceeded")
        return f"ok-{self._api_key}"

    def generate_json(self, prompt: str) -> dict[str, object]:
        return {"result": self.generate_text(prompt)}


class AIProviderTests(unittest.TestCase):
    @patch("app.services.ai_provider.genai")
    def test_provider_falls_back_to_next_model_when_primary_is_rate_limited(self, mocked_genai):
        responses = {
            "gemini-3-flash-preview": RuntimeError("429 quota exceeded"),
            "gemini-2.5-flash-lite": '{"hero_title":"Kid-powered coding"}',
        }
        mocked_genai.Client.return_value = _FakeClient(responses)

        provider = GeminiAIProvider(
            "test-key",
            model_name="gemini-3-flash-preview",
            fallback_models=("gemini-2.5-flash-lite",),
        )

        result = provider.generate_text("Return JSON only.")

        self.assertEqual(result, '{"hero_title":"Kid-powered coding"}')
        mocked_genai.Client.assert_called_once_with(api_key="test-key")
        self.assertEqual(provider._model_names[0], "gemini-2.5-flash-lite")

    @patch("app.services.ai_provider.genai")
    def test_provider_falls_back_to_next_model_when_primary_reports_quota_exhausted(self, mocked_genai):
        responses = {
            "gemini-3-flash-preview": RuntimeError("ResourceExhausted: quota exceeded"),
            "gemini-2.5-flash-lite": '{"hero_title":"Kid-powered coding"}',
        }
        mocked_genai.Client.return_value = _FakeClient(responses)

        provider = GeminiAIProvider(
            "test-key",
            model_name="gemini-3-flash-preview",
            fallback_models=("gemini-2.5-flash-lite",),
        )

        result = provider.generate_text("Return JSON only.", stop_on_quota_error=True)

        self.assertEqual(result, '{"hero_title":"Kid-powered coding"}')
        mocked_genai.Client.assert_called_once_with(api_key="test-key")

    @patch("app.services.ai_provider.genai")
    def test_provider_raises_helpful_error_when_all_models_fail(self, mocked_genai):
        responses = {
            "gemini-2.5-flash-lite": RuntimeError("429 quota exceeded"),
            "gemini-2.5-flash": RuntimeError("429 quota exceeded"),
        }
        mocked_genai.Client.return_value = _FakeClient(responses)

        provider = GeminiAIProvider(
            "test-key",
            model_name="gemini-2.5-flash-lite",
            fallback_models=("gemini-2.5-flash",),
        )

        with self.assertRaises(AIProviderRequestError) as context:
            provider.generate_text("Return JSON only.")

        self.assertIn("rate-limited", str(context.exception))
        self.assertIn("gemini-2.5-flash-lite", str(context.exception))
        self.assertIn("gemini-2.5-flash", str(context.exception))

    @patch.dict(os.environ, {"GOOGLE_API_KEY": "google-key"}, clear=True)
    @patch("app.services.ai_provider.GeminiAIProvider")
    def test_require_default_provider_accepts_google_api_key_alias(self, mocked_provider):
        require_default_provider(action="Website generation")

        mocked_provider.assert_called_once_with("google-key")

    @patch.dict(
        os.environ,
        {"GEMINI_API_KEY_2": "key-two", "GEMINI_API_KEY_1": "key-one", "GEMINI_API_KEY": "key-one"},
        clear=True,
    )
    def test_resolve_api_keys_accepts_numbered_values_in_order(self):
        self.assertEqual(_resolve_api_keys(), ("key-one", "key-two"))

    @patch.dict(os.environ, {"GEMINI_API_KEYS": "key-1,key-2"}, clear=True)
    @patch("app.services.ai_provider.GeminiAIProvider")
    @patch("app.services.ai_provider.RotatingGeminiAIProvider")
    def test_require_default_provider_uses_rotating_provider_for_multiple_keys(
        self, mocked_rotating_provider, mocked_single_provider
    ):
        require_default_provider(action="Website generation")

        mocked_single_provider.assert_not_called()
        mocked_rotating_provider.assert_called_once_with(("key-1", "key-2"))

    @patch.dict(os.environ, {"GEMINI_API_KEYS": "key-1\nkey-2 key-3"}, clear=True)
    def test_resolve_api_keys_accepts_whitespace_and_newline_separators(self):
        self.assertEqual(_resolve_api_keys(), ("key-1", "key-2", "key-3"))

    @patch.dict(os.environ, {"GEMINI_API_KEY": "your_gemini_api_key_here"}, clear=True)
    def test_resolve_api_keys_ignores_placeholder_template_values(self):
        self.assertEqual(_resolve_api_keys(), ())

    @patch("app.services.ai_provider.GeminiAIProvider")
    def test_rotating_provider_tries_next_key_when_first_is_rate_limited(self, mocked_provider):
        mocked_provider.side_effect = lambda api_key, **kwargs: _FakeKeyProvider(api_key)

        provider = RotatingGeminiAIProvider(("key-1", "key-2"))
        provider._rotation_cursor = 0

        result = provider.generate_text("Return JSON only.")

        self.assertEqual(result, "ok-key-2")

    @patch("app.services.ai_provider.GeminiAIProvider")
    def test_rotating_provider_fast_fails_over_to_next_key_on_quota(self, mocked_provider):
        first_provider = unittest.mock.Mock()
        first_provider.generate_text.side_effect = AIProviderRequestError(
            "Gemini generation is unavailable because the configured API key is out of quota or rate-limited."
        )
        second_provider = unittest.mock.Mock()
        second_provider.generate_text.return_value = "ok-key-2"
        mocked_provider.side_effect = [first_provider, second_provider]

        provider = RotatingGeminiAIProvider(("key-1", "key-2"))
        provider._rotation_cursor = 0

        result = provider.generate_text("Return JSON only.")

        self.assertEqual(result, "ok-key-2")
        first_provider.generate_text.assert_called_once_with("Return JSON only.", stop_on_quota_error=False)
        second_provider.generate_text.assert_called_once_with("Return JSON only.", stop_on_quota_error=False)

    @patch.dict(
        os.environ,
        {"GEMINI_ROTATION_RETRY_ROUNDS": "2", "GEMINI_ROTATION_RETRY_BACKOFF_SECONDS": "0"},
        clear=False,
    )
    @patch("app.services.ai_provider.GeminiAIProvider")
    def test_rotating_provider_retries_only_transient_keys_in_later_rounds(self, mocked_provider):
        first_provider = unittest.mock.Mock()
        first_provider.generate_text.side_effect = AIProviderRequestError(
            "Gemini generation is unavailable because the configured API key is out of quota or rate-limited.",
            retryable=True,
            quota_error=True,
            hard_quota_error=True,
        )
        second_provider = unittest.mock.Mock()
        second_provider.generate_text.side_effect = [
            AIProviderRequestError(
                "Gemini generation is unavailable because the configured API key is out of quota or rate-limited.",
                retryable=True,
                quota_error=True,
                hard_quota_error=False,
            ),
            "ok-key-2",
        ]
        mocked_provider.side_effect = [first_provider, second_provider]

        provider = RotatingGeminiAIProvider(("key-1", "key-2"))
        provider._rotation_cursor = 0

        result = provider.generate_text("Return JSON only.")

        self.assertEqual(result, "ok-key-2")
        first_provider.generate_text.assert_called_once_with("Return JSON only.", stop_on_quota_error=False)
        self.assertEqual(second_provider.generate_text.call_count, 2)

    @patch("app.services.ai_provider.GeminiAIProvider")
    def test_rotating_provider_does_not_repeat_nested_model_debug_details(self, mocked_provider):
        mocked_provider.side_effect = [
            AIProviderRequestError(
                "Gemini generation is unavailable because the configured API key is out of quota or rate-limited. "
                "Tried models: gemini-2.5-flash-lite, gemini-2.5-flash. "
                "Last error: ResourceExhausted: 429 quota exceeded."
            ),
            AIProviderRequestError(
                "Gemini generation is unavailable because the configured API key is out of quota or rate-limited. "
                "Tried models: gemini-flash-lite-latest, gemini-3-flash-preview. "
                "Last error: ResourceExhausted: 429 quota exceeded."
            ),
        ]

        provider = RotatingGeminiAIProvider(("key-1", "key-2"))

        with self.assertRaises(AIProviderRequestError) as context:
            provider.generate_text("Return JSON only.")

        message = str(context.exception)
        self.assertIn("Tried APIs: api#1, api#2", message)
        self.assertIn("quota or rate limit exceeded", message)
        self.assertNotIn("Tried models", message)
