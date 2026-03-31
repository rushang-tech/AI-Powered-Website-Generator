from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token

_DEFAULT_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"
_GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}


class GoogleOAuthError(RuntimeError):
    pass


@dataclass(frozen=True)
class GoogleOAuthProfile:
    sub: str
    email: str
    email_verified: bool
    name: str
    picture: str


def google_oauth_enabled(client_id: str | None, client_secret: str | None) -> bool:
    return bool((client_id or "").strip() and (client_secret or "").strip())


@lru_cache(maxsize=4)
def _discovery_document(discovery_url: str = _DEFAULT_DISCOVERY_URL) -> dict[str, Any]:
    request = Request(discovery_url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=10) as response:
            payload = response.read().decode("utf-8")
    except (HTTPError, URLError) as exc:
        raise GoogleOAuthError("Could not load Google's sign-in configuration.") from exc

    try:
        document = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise GoogleOAuthError("Google sign-in configuration returned invalid JSON.") from exc

    if not isinstance(document, dict):
        raise GoogleOAuthError("Google sign-in configuration returned an unexpected response.")
    return document


def build_google_authorization_url(
    *,
    client_id: str,
    redirect_uri: str,
    state: str,
    nonce: str,
    prompt: str = "select_account",
    discovery_url: str = _DEFAULT_DISCOVERY_URL,
) -> str:
    document = _discovery_document(discovery_url)
    auth_endpoint = str(document.get("authorization_endpoint", "")).strip()
    if not auth_endpoint:
        raise GoogleOAuthError("Google sign-in is missing an authorization endpoint.")

    query = urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "nonce": nonce,
            "prompt": prompt,
        }
    )
    return f"{auth_endpoint}?{query}"


def exchange_google_code_for_tokens(
    *,
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    discovery_url: str = _DEFAULT_DISCOVERY_URL,
) -> dict[str, Any]:
    document = _discovery_document(discovery_url)
    token_endpoint = str(document.get("token_endpoint", "")).strip()
    if not token_endpoint:
        raise GoogleOAuthError("Google sign-in is missing a token endpoint.")

    body = urlencode(
        {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
    ).encode("utf-8")
    request = Request(
        token_endpoint,
        data=body,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:
            payload = response.read().decode("utf-8")
    except HTTPError as exc:
        message = "Google sign-in token exchange failed."
        try:
            error_payload = json.loads(exc.read().decode("utf-8"))
        except (OSError, json.JSONDecodeError):
            error_payload = {}
        if isinstance(error_payload, dict):
            description = str(error_payload.get("error_description") or error_payload.get("error") or "").strip()
            if description:
                message = f"{message} {description}"
        raise GoogleOAuthError(message) from exc
    except URLError as exc:
        raise GoogleOAuthError("Google sign-in token exchange could not be completed.") from exc

    try:
        token_response = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise GoogleOAuthError("Google sign-in token response was invalid.") from exc

    if not isinstance(token_response, dict):
        raise GoogleOAuthError("Google sign-in token response was invalid.")
    return token_response


def verify_google_id_token(
    *,
    token_response: dict[str, Any],
    client_id: str,
    expected_nonce: str,
) -> GoogleOAuthProfile:
    raw_id_token = str(token_response.get("id_token", "")).strip()
    if not raw_id_token:
        raise GoogleOAuthError("Google sign-in did not return an ID token.")

    try:
        token_payload = id_token.verify_oauth2_token(raw_id_token, GoogleRequest(), client_id)
    except ValueError as exc:
        raise GoogleOAuthError("Google sign-in token validation failed.") from exc

    issuer = str(token_payload.get("iss", "")).strip()
    if issuer not in _GOOGLE_ISSUERS:
        raise GoogleOAuthError("Google sign-in token came from an unexpected issuer.")

    nonce = str(token_payload.get("nonce", "")).strip()
    if expected_nonce and nonce != expected_nonce:
        raise GoogleOAuthError("Google sign-in could not be verified. Please try again.")

    return GoogleOAuthProfile(
        sub=str(token_payload.get("sub", "")).strip(),
        email=str(token_payload.get("email", "")).strip().lower(),
        email_verified=bool(token_payload.get("email_verified")),
        name=str(token_payload.get("name", "")).strip(),
        picture=str(token_payload.get("picture", "")).strip(),
    )
