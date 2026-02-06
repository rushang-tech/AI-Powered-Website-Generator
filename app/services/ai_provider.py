from __future__ import annotations

import json
import os
import re
import time
from collections.abc import Iterable
from pathlib import Path
from threading import Lock
from typing import Protocol

from dotenv import load_dotenv

from app.services.taste_engine import clean_json_response

try:
    import google.generativeai as genai
except Exception:  # pragma: no cover - dependency may be unavailable in test env
    genai = None


def _load_environment_files() -> None:
    project_root = Path(__file__).resolve().parents[2]
    env_path = project_root / ".env"
    example_env_path = project_root / ".env.example"

    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=False)
    elif example_env_path.exists():
        load_dotenv(dotenv_path=example_env_path, override=False)


_load_environment_files()

_API_KEY_ROTATION_LOCK = Lock()
_API_KEY_ROTATION_CURSOR = 0
_GENAI_REQUEST_LOCK = Lock()


class AIProvider(Protocol):
    def generate_text(self, prompt: str) -> str:
        ...

    def generate_json(self, prompt: str) -> dict[str, object]:
        ...


class AIProviderUnavailableError(RuntimeError):
    pass


class AIProviderRequestError(AIProviderUnavailableError):
    def __init__(
        self,
        message: str,
        *,
        retryable: bool | None = None,
        quota_error: bool | None = None,
        hard_quota_error: bool | None = None,
    ) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.quota_error = quota_error
        self.hard_quota_error = hard_quota_error


class NullAIProvider:
    def generate_text(self, prompt: str) -> str:
        raise RuntimeError("AI provider unavailable.")

    def generate_json(self, prompt: str) -> dict[str, object]:
        raise RuntimeError("AI provider unavailable.")


class GeminiAIProvider:
    DEFAULT_MODEL = "gemini-2.5-flash-lite"
    DEFAULT_FALLBACK_MODELS = (
        "gemini-2.5-flash",
        "gemini-flash-lite-latest",
        "gemini-3-flash-preview",
    )

    def __init__(
        self,
        api_key: str,
        *,
        model_name: str | None = None,
        fallback_models: Iterable[str] | None = None,
    ) -> None:
        if genai is None:
            raise RuntimeError("google.generativeai is unavailable.")
        self._api_key = api_key.strip()
        if not self._api_key:
            raise RuntimeError("Gemini API key is empty.")
        self._model_names = _resolve_model_names(model_name=model_name, fallback_models=fallback_models)
        self._models: dict[str, object] = {}

    def _model_for(self, model_name: str) -> object:
        model = self._models.get(model_name)
        if model is None:
            model = genai.GenerativeModel(model_name)
            self._models[model_name] = model
        return model

    def _promote_model(self, model_name: str) -> None:
        self._model_names = (model_name,) + tuple(name for name in self._model_names if name != model_name)

    def generate_text(self, prompt: str, *, stop_on_quota_error: bool = False) -> str:
        _ = stop_on_quota_error
        errors: list[tuple[str, Exception]] = []
        for model_name in self._model_names:
            try:
                # google.generativeai keeps the API key in global module state, so
                # we serialize configure+request to avoid cross-request key bleed.
                with _GENAI_REQUEST_LOCK:
                    genai.configure(api_key=self._api_key)
                    response = self._model_for(model_name).generate_content(prompt)
                text = str(getattr(response, "text", "")).strip()
                if not text:
                    raise ValueError("Gemini returned an empty response.")
                self._promote_model(model_name)
                return text
            except Exception as exc:
                errors.append((model_name, exc))

        raise AIProviderRequestError(
            _format_generation_error(errors),
            retryable=any(_is_retryable_error(exc) for _, exc in errors),
            quota_error=any(_is_quota_error(exc) for _, exc in errors),
            hard_quota_error=bool(errors) and all(_is_hard_quota_error(exc) for _, exc in errors),
        )

    def generate_json(self, prompt: str) -> dict[str, object]:
        raw = self.generate_text(prompt)
        cleaned = clean_json_response(raw)
        parsed = json.loads(cleaned)
        if not isinstance(parsed, dict):
            raise ValueError("AI response did not decode to a JSON object.")
        return parsed


class RotatingGeminiAIProvider:
    def __init__(
        self,
        api_keys: Iterable[str],
        *,
        model_name: str | None = None,
        fallback_models: Iterable[str] | None = None,
    ) -> None:
        keys = tuple(str(item).strip() for item in api_keys if str(item).strip())
        if not keys:
            raise RuntimeError("No Gemini API keys were configured.")
        self._api_keys = keys
        self._model_name = model_name
        self._fallback_models = tuple(fallback_models or ())
        self._providers: dict[int, GeminiAIProvider] = {}
        self._rotation_lock = Lock()
        self._rotation_cursor = _next_api_key_rotation_start(len(self._api_keys))

    def _provider_for(self, key_index: int) -> GeminiAIProvider:
        provider = self._providers.get(key_index)
        if provider is None:
            provider = GeminiAIProvider(
                self._api_keys[key_index],
                model_name=self._model_name,
                fallback_models=self._fallback_models,
            )
            self._providers[key_index] = provider
        return provider

    def _next_start_index(self) -> int:
        with self._rotation_lock:
            start = self._rotation_cursor % len(self._api_keys)
            self._rotation_cursor = (self._rotation_cursor + 1) % len(self._api_keys)
            return start

    def _api_label(self, key_index: int) -> str:
        return f"api#{key_index + 1}"

    def _rotation_order(self) -> tuple[int, ...]:
        start = self._next_start_index()
        return tuple((start + offset) % len(self._api_keys) for offset in range(len(self._api_keys)))

    def _generate_with_key_rotation(self, callback) -> object:
        errors: list[tuple[str, Exception]] = []
        next_round_candidates: tuple[int, ...] | None = None
        retry_rounds = _rotation_retry_rounds()

        for round_index in range(retry_rounds):
            round_errors: list[tuple[int, Exception]] = []
            rotation_order = self._rotation_order()
            if next_round_candidates is not None:
                allowed = set(next_round_candidates)
                rotation_order = tuple(key_index for key_index in rotation_order if key_index in allowed)
                if not rotation_order:
                    break

            for key_index in rotation_order:
                try:
                    return callback(self._provider_for(key_index))
                except Exception as exc:
                    errors.append((self._api_label(key_index), exc))
                    round_errors.append((key_index, exc))

            if round_index + 1 >= retry_rounds:
                break

            retryable_candidates = tuple(
                key_index for key_index, exc in round_errors if _should_retry_key(exc)
            )
            if not retryable_candidates:
                break

            next_round_candidates = retryable_candidates
            time.sleep(_rotation_retry_backoff_seconds(round_index))

        raise AIProviderRequestError(
            _format_rotating_generation_error(errors),
            retryable=any(_is_retryable_error(exc) for _, exc in errors),
            quota_error=any(_is_quota_error(exc) for _, exc in errors),
            hard_quota_error=bool(errors) and all(_is_hard_quota_error(exc) for _, exc in errors),
        )

    def generate_text(self, prompt: str) -> str:
        result = self._generate_with_key_rotation(
            lambda provider: provider.generate_text(prompt, stop_on_quota_error=False)
        )
        return str(result)

    def generate_json(self, prompt: str) -> dict[str, object]:
        result = self._generate_with_key_rotation(lambda provider: provider.generate_json(prompt))
        if not isinstance(result, dict):
            raise ValueError("AI response did not decode to a JSON object.")
        return result


def _api_key_env_names() -> tuple[str, ...]:
    return ("GEMINI_API_KEY", "GOOGLE_API_KEY")


def _api_keys_env_names() -> tuple[str, ...]:
    return ("GEMINI_API_KEYS", "GOOGLE_API_KEYS")


def _parse_csv_values(raw_value: str) -> tuple[str, ...]:
    items: list[str] = []
    seen: set[str] = set()
    # Support comma, whitespace, and newline separated key lists.
    for raw_item in re.split(r"[,\s]+", raw_value.strip()):
        item = raw_item.strip()
        if not item or item in seen:
            continue
        seen.add(item)
        items.append(item)
    return tuple(items)


def _is_placeholder_api_key(value: str) -> bool:
    normalized = value.strip().lower()
    if not normalized:
        return True
    if normalized in {"your_gemini_api_key_here", "your_google_api_key_here", "changeme"}:
        return True
    return normalized.startswith("your_") and normalized.endswith("_here")


def _resolve_numbered_api_key_entries() -> tuple[tuple[str, str], ...]:
    numbered: list[tuple[int, str, str]] = []
    for prefix in ("GEMINI_API_KEY_", "GOOGLE_API_KEY_"):
        for env_name, raw_value in os.environ.items():
            if not env_name.startswith(prefix):
                continue
            suffix = env_name[len(prefix) :].strip()
            if not suffix.isdigit():
                continue
            value = raw_value.strip()
            if _is_placeholder_api_key(value):
                continue
            numbered.append((int(suffix), env_name, value))
    numbered.sort(key=lambda item: item[0])
    return tuple((env_name, value) for _, env_name, value in numbered)


def _resolve_api_key_entries() -> tuple[tuple[str, str], ...]:
    entries: list[tuple[str, str]] = []
    seen: set[str] = set()

    for env_name in _api_keys_env_names():
        for index, item in enumerate(_parse_csv_values(os.getenv(env_name, "")), start=1):
            if _is_placeholder_api_key(item) or item in seen:
                continue
            seen.add(item)
            entries.append((f"{env_name}[{index}]", item))

    for env_name, item in _resolve_numbered_api_key_entries():
        if item in seen:
            continue
        seen.add(item)
        entries.append((env_name, item))

    for env_name in _api_key_env_names():
        value = os.getenv(env_name, "").strip()
        if _is_placeholder_api_key(value) or value in seen:
            continue
        seen.add(value)
        entries.append((env_name, value))

    return tuple(entries)


def _resolve_api_keys() -> tuple[str, ...]:
    return tuple(value for _, value in _resolve_api_key_entries())


def configured_api_key_sources() -> tuple[str, ...]:
    return tuple(env_name for env_name, _ in _resolve_api_key_entries())


def _resolve_api_key() -> str:
    return next(iter(_resolve_api_keys()), "")


def configured_api_key_count() -> int:
    return len(_resolve_api_keys())


def _parse_model_names(raw_value: str) -> tuple[str, ...]:
    return _parse_csv_values(raw_value)


def _parse_int_env(name: str, default: int, *, minimum: int = 1, maximum: int = 10) -> int:
    raw_value = os.getenv(name, "").strip()
    if not raw_value:
        return default
    try:
        parsed = int(raw_value)
    except ValueError:
        return default
    return max(minimum, min(parsed, maximum))


def _parse_float_env(name: str, default: float, *, minimum: float = 0.0, maximum: float = 5.0) -> float:
    raw_value = os.getenv(name, "").strip()
    if not raw_value:
        return default
    try:
        parsed = float(raw_value)
    except ValueError:
        return default
    return max(minimum, min(parsed, maximum))


def _rotation_retry_rounds() -> int:
    return _parse_int_env("GEMINI_ROTATION_RETRY_ROUNDS", default=2, minimum=1, maximum=5)


def _rotation_retry_backoff_seconds(round_index: int) -> float:
    base_delay = _parse_float_env("GEMINI_ROTATION_RETRY_BACKOFF_SECONDS", default=0.35, minimum=0.0, maximum=5.0)
    return base_delay * (round_index + 1)


def _resolve_model_names(
    *,
    model_name: str | None,
    fallback_models: Iterable[str] | None,
) -> tuple[str, ...]:
    candidates: list[str] = []
    seen: set[str] = set()
    configured_fallbacks = _parse_model_names(os.getenv("GEMINI_FALLBACK_MODELS", ""))
    source_models = (
        (model_name or "").strip(),
        os.getenv("GEMINI_MODEL", "").strip(),
        GeminiAIProvider.DEFAULT_MODEL,
        *(fallback_models or ()),
        *configured_fallbacks,
        *GeminiAIProvider.DEFAULT_FALLBACK_MODELS,
    )
    for candidate in source_models:
        item = str(candidate).strip()
        if not item or item in seen:
            continue
        seen.add(item)
        candidates.append(item)
    return tuple(candidates)


def _exception_text(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc}".lower()


def _is_hard_quota_error(exc: Exception) -> bool:
    if isinstance(exc, AIProviderRequestError) and exc.hard_quota_error is not None:
        return exc.hard_quota_error
    text = _exception_text(exc)
    return "resourceexhausted" in text or "quota" in text or "insufficient_quota" in text


def _is_rate_limit_error(exc: Exception) -> bool:
    text = _exception_text(exc)
    return "rate limit" in text or "rate-limited" in text or "too many requests" in text or "429" in text


def _is_quota_error(exc: Exception) -> bool:
    if isinstance(exc, AIProviderRequestError) and exc.quota_error is not None:
        return exc.quota_error
    return _is_hard_quota_error(exc) or _is_rate_limit_error(exc)


def _is_retryable_error(exc: Exception) -> bool:
    if isinstance(exc, AIProviderRequestError) and exc.retryable is not None:
        return exc.retryable
    text = _exception_text(exc)
    if _is_quota_error(exc):
        return True
    return any(
        token in text
        for token in (
            "timeout",
            "deadline exceeded",
            "temporarily unavailable",
            "temporarilyunavailable",
            "service unavailable",
            "internal server error",
            "connection reset",
            "bad gateway",
            "gateway timeout",
            "503",
            "502",
            "504",
        )
    )


def _should_retry_key(exc: Exception) -> bool:
    return _is_retryable_error(exc) and not _is_hard_quota_error(exc)


def _summarize_generation_exception(exc: Exception) -> str:
    if isinstance(exc, AIProviderRequestError) and _is_quota_error(exc):
        return "quota or rate limit exceeded"
    return f"{type(exc).__name__}: {exc}"


def _format_generation_error(errors: list[tuple[str, Exception]]) -> str:
    tried_models = ", ".join(model_name for model_name, _ in errors) or GeminiAIProvider.DEFAULT_MODEL
    last_exc = errors[-1][1] if errors else RuntimeError("Gemini request failed.")
    last_summary = _summarize_generation_exception(last_exc)

    if any(_is_quota_error(exc) for _, exc in errors):
        return (
            "Gemini generation is unavailable because the configured API key is out of quota or rate-limited. "
            f"Tried models: {tried_models}. Set GEMINI_MODEL to a model with available quota or try again after the quota resets. "
            f"Last error: {last_summary}"
        )

    return f"Gemini generation failed after trying models: {tried_models}. Last error: {last_summary}"


def _format_rotating_generation_error(errors: list[tuple[str, Exception]]) -> str:
    tried_apis = ", ".join(api_label for api_label, _ in errors) or "api#1"
    last_exc = errors[-1][1] if errors else RuntimeError("Gemini request failed.")
    last_summary = _summarize_generation_exception(last_exc)
    if any(_is_quota_error(exc) for _, exc in errors):
        return (
            "Gemini generation is unavailable because all configured API keys are out of quota or rate-limited. "
            f"Tried APIs: {tried_apis}. Add more keys via GEMINI_API_KEYS or GEMINI_API_KEY_1/GEMINI_API_KEY_2, "
            f"or try again after quota resets. Last error: {last_summary}"
        )
    return f"Gemini generation failed after trying APIs: {tried_apis}. Last error: {last_summary}"


def _next_api_key_rotation_start(total_keys: int) -> int:
    if total_keys <= 1:
        return 0

    global _API_KEY_ROTATION_CURSOR
    with _API_KEY_ROTATION_LOCK:
        start = _API_KEY_ROTATION_CURSOR % total_keys
        _API_KEY_ROTATION_CURSOR = (_API_KEY_ROTATION_CURSOR + 1) % total_keys
        return start


def require_default_provider(*, action: str = "AI generation") -> AIProvider:
    api_keys = _resolve_api_keys()
    if not api_keys:
        env_names = " or ".join((*_api_keys_env_names(), "GEMINI_API_KEY_1", "GOOGLE_API_KEY_1", *_api_key_env_names()))
        raise AIProviderUnavailableError(
            f"{action} is unavailable because {env_names} is not configured."
        )
    try:
        if len(api_keys) == 1:
            return GeminiAIProvider(api_keys[0])
        return RotatingGeminiAIProvider(api_keys)
    except Exception as exc:
        raise AIProviderUnavailableError(
            f"{action} is unavailable because the Gemini provider could not start."
        ) from exc


def get_default_provider() -> AIProvider | None:
    try:
        return require_default_provider()
    except AIProviderUnavailableError:
        return None
